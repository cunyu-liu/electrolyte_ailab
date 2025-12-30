"""
Qwen模型CPT训练完整脚本 - 无bitsandbytes依赖版
适用于CUDA 12.8等新版本环境
"""

import os
import json
import torch
import math
from datasets import Dataset, load_dataset
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    TrainingArguments, 
    Trainer,
    DataCollatorForLanguageModeling,
    get_linear_schedule_with_warmup
)
from peft import LoraConfig, get_peft_model, TaskType
import glob
from typing import List, Dict, Optional
from dataclasses import dataclass
import gc
from tqdm import tqdm

@dataclass
class PackedDataCollator:
    """
    高级动态打包DataCollator - 显著减少填充浪费
    支持智能长度分桶和动态批处理
    """
    tokenizer: any
    max_length: int = 2048
    packing: bool = True
    padding: bool = True
    
    def __call__(self, features: List[Dict[str, List[int]]]) -> Dict[str, torch.Tensor]:
        # 收集所有input_ids
        all_input_ids = []
        for feature in features:
            input_ids = feature["input_ids"]
            # 添加EOS token并确保不超过最大长度
            if len(input_ids) < self.max_length - 1:
                input_ids = input_ids + [self.tokenizer.eos_token_id]
            all_input_ids.append(input_ids)
        
        if self.packing:
            # 按长度排序以提高打包效率
            all_input_ids.sort(key=len, reverse=True)
            
            # 打包逻辑：将短序列合并成长序列
            packed_sequences = []
            current_sequence = []
            current_length = 0
            
            for seq in all_input_ids:
                seq_len = len(seq)
                if current_length + seq_len <= self.max_length:
                    current_sequence.extend(seq)
                    current_length += seq_len
                else:
                    if current_sequence:  # 保存当前包
                        packed_sequences.append(current_sequence)
                    # 开始新的包
                    current_sequence = seq.copy()
                    current_length = seq_len
            
            # 添加最后一个包
            if current_sequence:
                packed_sequences.append(current_sequence)
            
            # 转换为模型输入格式
            batch_input_ids = []
            batch_attention_masks = []
            
            for packed_seq in packed_sequences:
                # 填充或截断
                if len(packed_seq) < self.max_length:
                    padding_len = self.max_length - len(packed_seq)
                    input_ids = packed_seq + [self.tokenizer.pad_token_id] * padding_len
                    attention_mask = [1] * len(packed_seq) + [0] * padding_len
                else:
                    input_ids = packed_seq[:self.max_length]
                    attention_mask = [1] * self.max_length
                
                batch_input_ids.append(input_ids)
                batch_attention_masks.append(attention_mask)
            
            batch = {
                "input_ids": torch.tensor(batch_input_ids, dtype=torch.long),
                "attention_mask": torch.tensor(batch_attention_masks, dtype=torch.long),
                "labels": torch.tensor(batch_input_ids, dtype=torch.long)  # CPT使用相同标签
            }
            
        else:
            # 传统批处理（带填充）
            batch = self.tokenizer.pad(
                {"input_ids": all_input_ids},
                padding="longest",
                max_length=self.max_length,
                return_tensors="pt"
            )
            batch["labels"] = batch["input_ids"].clone()
        
        return batch

class SmartChunkProcessor:
    """智能文本分块处理器，保持语义完整性"""
    
    def __init__(self, tokenizer, max_chunk_tokens=2048, overlap_tokens=200):
        self.tokenizer = tokenizer
        self.max_chunk_tokens = max_chunk_tokens
        self.overlap_tokens = overlap_tokens
    
    def split_by_sentences(self, text: str) -> List[str]:
        """按句子分割文本（简单实现）"""
        import re
        # 中文句子分割
        sentences = re.split(r'[。！？!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    
    def smart_chunking(self, text: str) -> List[str]:
        """智能分块：优先在句子边界分割"""
        sentences = self.split_by_sentences(text)
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self.tokenizer.encode(sentence, add_special_tokens=False)
            sentence_token_len = len(sentence_tokens)
            
            # 如果单句就超过最大长度，需要硬分割
            if sentence_token_len > self.max_chunk_tokens:
                # 先把当前块保存
                if current_chunk:
                    chunks.append("".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                
                # 对长句进行硬分割
                for i in range(0, sentence_token_len, self.max_chunk_tokens - self.overlap_tokens):
                    chunk_tokens = sentence_tokens[i:i + self.max_chunk_tokens]
                    chunk_text = self.tokenizer.decode(chunk_tokens, skip_special_tokens=True)
                    chunks.append(chunk_text)
            else:
                # 正常添加句子到当前块
                if current_tokens + sentence_token_len > self.max_chunk_tokens:
                    chunks.append("".join(current_chunk))
                    current_chunk = [sentence]
                    current_tokens = sentence_token_len
                else:
                    current_chunk.append(sentence)
                    current_tokens += sentence_token_len
        
        # 添加最后一个块
        if current_chunk:
            chunks.append("".join(current_chunk))
        
        return chunks

def load_data_in_streaming(data_folder: str, max_files: Optional[int] = None):
    """流式加载数据，避免内存爆炸"""
    json_files = glob.glob(os.path.join(data_folder, "*.json"))
    
    if max_files:
        json_files = json_files[:max_files]
    
    print(f"发现 {len(json_files)} 个数据文件")
    
    for file_idx, file_path in enumerate(json_files, 1):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 验证必要字段
            if "main_text" not in data:
                print(f"跳过文件 {file_path}: 缺少main_text字段")
                continue
                
            # 清理文本
            main_text = " ".join(data["main_text"].split())
            abstract = data.get("abstract", "")
            if abstract:
                abstract = " ".join(abstract.split())
            
            yield {
                "file_idx": file_idx,
                "file_path": file_path,
                "main_text": main_text,
                "abstract": abstract,
                "categories": data.get("categories", "")
            }
            
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")
            continue
        
        if file_idx % 100 == 0:
            print(f"已流式加载 {file_idx}/{len(json_files)} 个文件")

def prepare_cpt_dataset_streaming(
    data_folder: str,
    tokenizer,
    max_chunk_tokens: int = 2048,
    max_total_chunks: int = 100000,
    use_abstract: bool = True
) -> Dataset:
    """流式准备数据集，避免内存不足"""
    
    chunk_processor = SmartChunkProcessor(
        tokenizer=tokenizer,
        max_chunk_tokens=max_chunk_tokens,
        overlap_tokens=min(200, max_chunk_tokens // 10)
    )
    
    all_chunks = []
    stats = {"total_tokens": 0, "total_chunks": 0}
    
    print("开始流式处理数据...")
    
    for data_item in tqdm(load_data_in_streaming(data_folder), desc="处理文献"):
        # 构建训练文本
        if use_abstract and data_item["abstract"]:
            full_text = data_item["abstract"] + "\n\n" + data_item["main_text"]
        else:
            full_text = data_item["main_text"]
        
        # 智能分块
        chunks = chunk_processor.smart_chunking(full_text)
        
        for chunk in chunks:
            all_chunks.append(chunk)
            stats["total_chunks"] += 1
            
            # 限制总块数避免内存溢出
            if len(all_chunks) >= max_total_chunks:
                print(f"达到最大块数限制 {max_total_chunks}，停止处理")
                break
        
        if len(all_chunks) >= max_total_chunks:
            break
    
    print(f"处理完成: 共生成 {len(all_chunks)} 个文本块")
    
    # 创建数据集
    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=max_chunk_tokens,
            return_tensors=None,
            padding=False
        )
    
    dataset = Dataset.from_dict({"text": all_chunks})
    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        batch_size=100,
        remove_columns=dataset.column_names,
        desc="Tokenizing chunks"
    )
    
    return tokenized_dataset

def print_memory_stats(label: str = ""):
    """打印详细内存统计"""
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1024**3
        reserved = torch.cuda.memory_reserved() / 1024**3
        max_allocated = torch.cuda.max_memory_allocated() / 1024**3
        
        print(f"{label} - GPU内存统计:")
        print(f"  当前分配: {allocated:.2f}GB")
        print(f"  当前保留: {reserved:.2f}GB")
        print(f"  峰值分配: {max_allocated:.2f}GB")
        
    # 系统内存
    import psutil
    process = psutil.Process()
    mem_info = process.memory_info()
    print(f"  系统内存: {mem_info.rss / 1024**3:.2f}GB")

def setup_model_without_bitsandbytes(
    model_path: str,
    use_lora: bool = True,
    lora_r: int = 8
):
    """
    不使用bitsandbytes的模型加载方案
    使用半精度和梯度检查点优化内存
    """
    
    print(f"加载模型: {model_path}")
    print("警告: 未使用4位量化，显存占用会更高")
    
    # 清理显存
    torch.cuda.empty_cache()
    gc.collect()
    
    # 加载tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        trust_remote_code=True,
        padding_side="right"
    )
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # 加载模型 - 关键：使用float16和低CPU内存模式
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.float16,  # 半精度而非4位量化
        device_map="auto",  # 自动分配设备
        trust_remote_code=True,
        low_cpu_mem_usage=True,
        # 注意：移除了所有bitsandbytes相关参数
    )
    
    # 启用梯度检查点（用时间换空间）
    model.gradient_checkpointing_enable()
    model.config.use_cache = False  # 禁用KV缓存以节省显存
    
    print("模型加载完成")
    print_memory_stats("模型加载后")
    
    # 应用LoRA适配器
    if use_lora:
        print("应用LoRA适配器...")
        
        # 针对Qwen模型的LoRA配置
        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            inference_mode=False,
            r=lora_r,
            lora_alpha=32,
            lora_dropout=0.05,
            # Qwen模型的目标模块
            target_modules=[
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj",
                "w1", "w2", "w3"  # 某些Qwen变体的额外模块
            ],
            bias="none",
        )
        
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()
    
    return model, tokenizer

def train_cpt_qwen():
    """主训练函数"""
    
    # ==================== 配置 ====================
    MODEL_PATH = "/data/qwen"  # 改为你的Qwen模型路径
    DATA_FOLDER = "/data/data_new1"  # 数据文件夹
    OUTPUT_DIR = "/data/qwen_cpt"  # 输出目录
    
    # 训练参数（针对无4位量化优化）
    MAX_LENGTH = 1024  # 减小长度以节省显存
    BATCH_SIZE = 1  # 每个设备batch size
    GRAD_ACCUM_STEPS = 32  # 增加梯度累积步数
    LEARNING_RATE = 3e-5  # 适当的学习率
    NUM_EPOCHS = 3
    MAX_TRAIN_SAMPLES = 50000  # 最大训练样本数
    USE_LORA = True
    LORA_R = 8  # LoRA秩
    
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("=" * 60)
    print("Qwen模型CPT训练（无bitsandbytes版）")
    print("=" * 60)
    
    # ==================== 设置模型和分词器 ====================
    print("\n1. 设置模型和分词器...")
    model, tokenizer = setup_model_without_bitsandbytes(
        model_path=MODEL_PATH,
        use_lora=USE_LORA,
        lora_r=LORA_R
    )
    
    # ==================== 准备数据 ====================
    print("\n2. 准备训练数据...")
    
    # 使用流式处理避免内存溢出
    train_dataset = prepare_cpt_dataset_streaming(
        data_folder=DATA_FOLDER,
        tokenizer=tokenizer,
        max_chunk_tokens=MAX_LENGTH,
        max_total_chunks=MAX_TRAIN_SAMPLES,
        use_abstract=True
    )
    
    if len(train_dataset) == 0:
        print("错误: 没有生成训练数据!")
        return
    
    print(f"训练数据集大小: {len(train_dataset)} 个样本")
    
    # ==================== 配置训练参数 ====================
    print("\n3. 配置训练参数...")
    
    # 计算训练步数
    steps_per_epoch = max(1, len(train_dataset) // (BATCH_SIZE * GRAD_ACCUM_STEPS))
    total_steps = steps_per_epoch * NUM_EPOCHS
    
    print(f"每轮步数: {steps_per_epoch}, 总步数: {total_steps}")
    
    training_args = TrainingArguments(
        # 输出配置
        output_dir=OUTPUT_DIR,
        overwrite_output_dir=True,
        report_to=[],  # 禁用外部日志
        
        # 训练配置
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM_STEPS,
        
        # 优化器配置
        learning_rate=LEARNING_RATE,
        weight_decay=0.01,
        warmup_ratio=0.1,
        warmup_steps=min(500, total_steps // 10),
        
        # 梯度处理
        max_grad_norm=0.5,  # 较小的梯度裁剪
        gradient_checkpointing=True,
        
        # 优化器
        optim="adamw_torch_fused",  # 融合优化器，更高效
        
        # 学习率调度
        lr_scheduler_type="cosine",
        
        # 保存配置
        save_strategy="steps",
        save_steps=max(500, steps_per_epoch // 2),
        save_total_limit=3,
        
        # 日志配置
        logging_strategy="steps",
        logging_steps=20,
        logging_dir=os.path.join(OUTPUT_DIR, "logs"),
        
        # 数据加载配置
        dataloader_drop_last=True,
        dataloader_pin_memory=False,
        group_by_length=True,  # 按长度分组提升效率
        
        # 评估配置
        eval_strategy="no",
        
        # 精度配置
        fp16=True,  # 使用混合精度训练
        # bf16=torch.cuda.is_bf16_supported(),  # 如果支持BF16则启用
        
        # 其他
        remove_unused_columns=False,
        dataloader_num_workers=2,
        seed=42,
        
        # 内存优化
        # gradient_accumulation_steps=GRAD_ACCUM_STEPS,
        eval_accumulation_steps=1,
    )
    
    # ==================== 创建DataCollator ====================
    print("\n4. 创建DataCollator...")
    data_collator = PackedDataCollator(
        tokenizer=tokenizer,
        max_length=MAX_LENGTH,
        packing=True  # 启用打包以节省显存
    )
    
    # ==================== 创建Trainer ====================
    print("\n5. 创建Trainer...")
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        data_collator=data_collator,
        tokenizer=tokenizer,
    )
    
    # ==================== 开始训练 ====================
    print("\n" + "=" * 60)
    print("开始CPT训练")
    print("=" * 60)
    
    print_memory_stats("训练开始前")
    
    try:
        # 训练前最后的显存清理
        torch.cuda.empty_cache()
        gc.collect()
        
        # 开始训练
        print("\n开始训练循环...")
        train_result = trainer.train()
        
        # 保存结果
        trainer.save_metrics("train", train_result.metrics)
        trainer.save_state()
        
        # 保存模型
        print("\n保存模型和分词器...")
        trainer.save_model(OUTPUT_DIR)
        tokenizer.save_pretrained(OUTPUT_DIR)
        
        print(f"\n✅ 训练完成!")
        print(f"输出目录: {OUTPUT_DIR}")
        print(f"最终训练损失: {train_result.metrics.get('train_loss', 'N/A'):.4f}")
        
        # 保存训练配置
        config_summary = {
            "model": MODEL_PATH,
            "data_folder": DATA_FOLDER,
            "max_length": MAX_LENGTH,
            "batch_size": BATCH_SIZE,
            "grad_accum_steps": GRAD_ACCUM_STEPS,
            "learning_rate": LEARNING_RATE,
            "epochs": NUM_EPOCHS,
            "train_samples": len(train_dataset),
            "lora_used": USE_LORA,
            "lora_r": LORA_R if USE_LORA else None,
            "train_loss": train_result.metrics.get('train_loss', 'N/A')
        }
        
        config_path = os.path.join(OUTPUT_DIR, "training_config.json")
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_summary, f, indent=2, ensure_ascii=False)
        
        print(f"训练配置已保存到: {config_path}")
        
    except RuntimeError as e:
        error_msg = str(e)
        print(f"\n❌ 训练出错: {error_msg}")
        
        if "out of memory" in error_msg.lower():
            print("\n💡 GPU内存不足! 建议调整以下参数:")
            print(f"  1. 减小 MAX_LENGTH (当前: {MAX_LENGTH}) -> 尝试 512 或 768")
            print(f"  2. 增加 GRAD_ACCUM_STEPS (当前: {GRAD_ACCUM_STEPS}) -> 尝试 64")
            print(f"  3. 减小 MAX_TRAIN_SAMPLES (当前: {MAX_TRAIN_SAMPLES}) -> 尝试 20000")
            print(f"  4. 减小 LoRA 秩 (当前: {LORA_R}) -> 尝试 4")
            print(f"  5. 关闭 LoRA (当前: {USE_LORA}) -> 设置 USE_LORA=False")
        
        # 尝试保存崩溃前的状态
        try:
            crash_dir = OUTPUT_DIR + "_crash_recovery"
            print(f"\n尝试保存崩溃恢复状态到: {crash_dir}")
            trainer.save_model(crash_dir)
        except:
            pass
        
        raise e
    
    finally:
        print_memory_stats("训练结束后")
        torch.cuda.empty_cache()
    
    print("\n" + "=" * 60)
    print("训练脚本执行完毕")
    print("=" * 60)

def estimate_memory_requirements():
    """估计不同配置下的内存需求"""
    print("内存需求估算 (Qwen-7B模型):")
    print("-" * 50)
    
    configs = [
        {"max_length": 512, "batch_size": 1, "lora_r": 4, "estimated_vram": "6-8GB"},
        {"max_length": 1024, "batch_size": 1, "lora_r": 8, "estimated_vram": "8-12GB"},
        {"max_length": 2048, "batch_size": 1, "lora_r": 8, "estimated_vram": "12-16GB"},
        {"max_length": 1024, "batch_size": 2, "lora_r": 8, "estimated_vram": "14-18GB"},
    ]
    
    for cfg in configs:
        print(f"长度:{cfg['max_length']:4d} | "
              f"批次:{cfg['batch_size']} | "
              f"LoRA秩:{cfg['lora_r']} | "
              f"预估显存:{cfg['estimated_vram']}")
    
    print("\n💡 建议: 从最小配置开始，逐步增加")

if __name__ == "__main__":
    # 显示内存需求估算
    estimate_memory_requirements()
    
    # 确认是否继续
    response = input("\n是否开始训练? (yes/no): ")
    if response.lower() in ["yes", "y"]:
        train_cpt_qwen()
    else:
        print("训练已取消")