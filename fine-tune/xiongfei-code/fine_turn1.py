import os
import json
import torch
from datasets import Dataset
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    TrainingArguments, 
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, TaskType
import glob
from tqdm import tqdm
import numpy as np

def load_choice_dataset(data_folder, max_samples=None):
    """加载选择题数据集，处理缺失question_stem的情况"""
    json_files = glob.glob(os.path.join(data_folder, "*.json"))
    
    if max_samples:
        json_files = json_files[:max_samples]
    
    print(f"找到 {len(json_files)} 个JSON文件")
    
    all_data = []
    skipped_files = 0
    no_question_stem_count = 0
    
    for file_path in tqdm(json_files, desc="加载数据"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 验证数据结构
            if not isinstance(data, dict):
                print(f"跳过 {file_path}: 不是字典格式")
                skipped_files += 1
                continue
                
            if "question" not in data or "answer" not in data:
                print(f"跳过 {file_path}: 缺少question或answer字段")
                skipped_files += 1
                continue
            
            question_data = data.get("question", {})
            answer_data = data.get("answer", [])
            
            if not isinstance(question_data, dict):
                print(f"跳过 {file_path}: question字段不是字典")
                skipped_files += 1
                continue
            
            # 提取信息 - 处理question_stem可能缺失的情况
            question_stem = question_data.get("question_stem", "").strip()
            question_text = question_data.get("question", "").strip()
            options = question_data.get("options", [])
            
            # 构建组合问题文本
            if question_stem and question_text:
                combined_question = f"{question_stem}\n{question_text}"
            elif question_stem:
                combined_question = question_stem
            elif question_text:
                combined_question = question_text
                no_question_stem_count += 1
            else:
                print(f"跳过 {file_path}: question_stem和question都为空")
                skipped_files += 1
                continue
                
            if not answer_data:
                print(f"跳过 {file_path}: answer为空")
                skipped_files += 1
                continue
            
            # 提取正确答案
            answer_letter = answer_data[0].strip().upper() if answer_data else ""
            if not answer_letter:
                print(f"跳过 {file_path}: 无法提取答案")
                skipped_files += 1
                continue
            
            # 在选项中查找完整答案文本
            answer_text = answer_letter  # 默认使用字母
            for option in options:
                if option.strip().upper().startswith(f"{answer_letter}.") or option.strip().startswith(answer_letter):
                    answer_text = option.strip()
                    break
            
            all_data.append({
                "file": os.path.basename(file_path),
                "question_stem": question_stem,
                "question": question_text,
                "combined_question": combined_question,
                "options": options,
                "answer_letter": answer_letter,
                "answer_text": answer_text,
                "raw_data": data
            })
            
        except Exception as e:
            print(f"处理 {file_path} 时出错: {e}")
            skipped_files += 1
            continue
    
    print(f"\n数据统计:")
    print(f"成功加载: {len(all_data)} 个样本")
    print(f"跳过: {skipped_files} 个文件")
    print(f"缺少question_stem的样本: {no_question_stem_count} 个")
    
    return all_data

def create_choice_prompt(example, instruction=None):
    """创建选择题的训练prompt"""
    
    if instruction is None:
        instruction = "请回答以下选择题："
    
    # 构建选项字符串
    options_text = ""
    for i, option in enumerate(example["options"]):
        options_text += f"{option}\n"
    
    # 构建完整prompt - 极简格式
    prompt = f"问题: {example['combined_question']}"
    
    if example['options']:
        prompt += f"\n选项:\n{options_text.strip()}"
    
    prompt += f"\n答案: {example['answer_text']}"
    
    return prompt

def create_train_test_split(data, test_ratio=0.1):
    """创建训练集和测试集"""
    np.random.seed(42)
    indices = np.random.permutation(len(data))
    
    split_idx = int(len(data) * (1 - test_ratio))
    train_indices = indices[:split_idx]
    test_indices = indices[split_idx:]
    
    train_data = [data[i] for i in train_indices]
    test_data = [data[i] for i in test_indices]
    
    return train_data, test_data

def main():
    # 配置参数 - 大幅减少内存使用
    MODEL_PATH = "/data/qwen"  # Qwen模型路径
    DATA_FOLDER = "/data/dataset"  # 数据文件夹路径
    OUTPUT_DIR = "/data/qwen_choice_finetuned"  # 输出路径
    
    # 训练参数 - 优化以减少内存使用
    MAX_LENGTH = 512  # 大幅减少最大序列长度
    BATCH_SIZE = 1  # 批大小（最小化）
    GRADIENT_ACCUMULATION_STEPS = 16  # 梯度累积步数
    NUM_EPOCHS = 2  # 减少训练轮数
    LEARNING_RATE = 1e-4  # 学习率
    
    print("=" * 80)
    print("选择题LoRA微调脚本 - 稳定版")
    print("=" * 80)
    
    # 1. 只加载部分数据进行测试（避免内存不足）
    print("\n1. 加载数据集（限制样本数量）...")
    all_data = load_choice_dataset(DATA_FOLDER)
    
    # 限制训练数据量，先试用小规模
    if len(all_data) > 1000:
        print(f"\n警告: 数据集较大，只使用前1000个样本进行训练")
        all_data = all_data[:1000]
    
    if len(all_data) == 0:
        print("错误: 没有加载到有效数据!")
        return
    
    # 2. 划分训练集和测试集
    print("\n2. 划分训练集和测试集...")
    train_data, test_data = create_train_test_split(all_data, test_ratio=0.1)
    print(f"训练集: {len(train_data)} 个样本")
    print(f"测试集: {len(test_data)} 个样本")
    
    # 3. 创建prompt
    print("\n3. 创建训练prompt...")
    train_texts = [create_choice_prompt(item) for item in train_data]
    test_texts = [create_choice_prompt(item) for item in test_data]
    
    # 计算平均长度
    avg_train_len = np.mean([len(t) for t in train_texts])
    print(f"平均prompt长度: {avg_train_len:.1f} 字符")
    
    # 4. 加载tokenizer
    print("\n4. 加载tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATH,
        trust_remote_code=True,
        padding_side="right",
    )
    
    # 设置特殊token
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # 5. 数据预处理函数
    def tokenize_function(examples):
        """Tokenize函数"""
        # Tokenize文本 - 使用更短的max_length
        tokenized = tokenizer(
            examples["text"],
            truncation=True,
            padding=False,
            max_length=MAX_LENGTH,
            return_tensors=None
        )
        
        # 设置labels（用于因果语言建模）
        tokenized["labels"] = tokenized["input_ids"].copy()
        
        return tokenized
    
    # 6. 创建数据集
    print("\n5. 创建数据集...")
    train_dataset = Dataset.from_dict({"text": train_texts})
    test_dataset = Dataset.from_dict({"text": test_texts})
    
    print(f"原始训练集大小: {len(train_dataset)}")
    print(f"原始测试集大小: {len(test_dataset)}")
    
    # Tokenize数据集
    tokenized_train = train_dataset.map(
        tokenize_function,
        batched=True,
        batch_size=8,  # 减小batch_size
        remove_columns=train_dataset.column_names,
        desc="Tokenize训练集"
    )
    
    tokenized_test = test_dataset.map(
        tokenize_function,
        batched=True,
        batch_size=20,
        remove_columns=test_dataset.column_names,
        desc="Tokenize测试集"
    )
    
    # 计算平均token数
    avg_train_tokens = np.mean([len(ids) for ids in tokenized_train["input_ids"]])
    print(f"平均训练样本token数: {avg_train_tokens:.1f}")
    
    # 7. 加载模型 - 使用更节省内存的方式
    print("\n6. 加载模型...")
    
    # 清理GPU内存
    torch.cuda.empty_cache()
    
    # 检查可用显存
    if torch.cuda.is_available():
        total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"GPU总显存: {total_memory:.1f} GB")
        
        if total_memory < 16:  # 小于16GB显存
            print("检测到显存较小，使用更激进的优化策略")
            # 进一步减小参数
            MAX_LENGTH = 256
            print(f"调整MAX_LENGTH为: {MAX_LENGTH}")
    
    # 尝试不同的加载方式
    try:
        # 首先尝试不使用梯度检查点加载
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            device_map="auto",
            trust_remote_code=True,
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
        )
        print("✅ 成功加载模型")
    except Exception as e:
        print(f"模型加载失败: {e}")
        return
    
    # 8. 配置LoRA - 使用更小的配置
    print("\n7. 配置LoRA参数...")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        inference_mode=False,
        r=4,  # 使用更小的LoRA秩
        lora_alpha=8,  # 减小alpha
        lora_dropout=0.05,  # 减小dropout
        target_modules=["q_proj", "v_proj"],  # 只针对关键模块
        bias="none",
    )
    
    # 应用LoRA
    model = get_peft_model(model, lora_config)
    
    # 打印可训练参数
    model.print_trainable_parameters()
    
    # 9. 配置训练参数 - 禁用梯度检查点，使用更稳定的设置
    print("\n8. 配置训练参数...")
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        overwrite_output_dir=True,
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        learning_rate=LEARNING_RATE,
        weight_decay=0.01,
        warmup_ratio=0.05,
        lr_scheduler_type="linear",
        eval_strategy="no",  # 不进行评估以节省内存
        save_strategy="epoch",
        save_total_limit=1,  # 只保存一个检查点
        fp16=True,
        logging_steps=5,
        remove_unused_columns=False,
        dataloader_drop_last=True,
        gradient_checkpointing=False,  # 禁用梯度检查点，解决兼容性问题
        optim="adamw_torch",
        group_by_length=False,  # 禁用按长度分组
        report_to=[],
        disable_tqdm=False,
        max_grad_norm=0.3,  # 梯度裁剪
    )
    
    # 10. 创建data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )
    
    # 11. 创建Trainer
    print("\n9. 创建Trainer...")
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train,
        data_collator=data_collator,
        tokenizer=tokenizer,
    )
    
    # 12. 开始训练
    print("\n10. 开始训练...")
    print("=" * 80)
    
    # 训练前GPU内存使用情况
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1024**3
        reserved = torch.cuda.memory_reserved() / 1024**3
        print(f"训练前GPU内存使用: {allocated:.2f} GB (已分配)")
        print(f"训练前GPU内存保留: {reserved:.2f} GB")
    
    try:
        # 训练模型
        print("开始训练循环...")
        train_result = trainer.train()
        
        # 保存模型
        print("\n11. 保存模型...")
        trainer.save_model()
        tokenizer.save_pretrained(OUTPUT_DIR)
        
        print("\n训练完成!")
        print(f"模型已保存到: {OUTPUT_DIR}")
        
        # 最终内存使用情况
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1024**3
            print(f"训练后GPU内存使用: {allocated:.2f} GB")
        
    except torch.cuda.OutOfMemoryError:
        print("\n❌ GPU内存不足! 进一步优化建议:")
        print("=" * 60)
        print("1. 使用更小的模型版本（如Qwen-1.8B或Qwen-0.5B）")
        print("2. 使用CPU进行训练（非常慢）")
        print("3. 使用Google Colab的免费GPU（T4 16GB）")
        print("4. 使用云GPU服务（如Vast.ai、Runpod等）")
        print("5. 使用量化版本模型（如Qwen-7B-Chat-Int4）")
        print("6. 减少训练样本到50个以下")
        print("\n当前配置:")
        print(f"  - 模型: {MODEL_PATH}")
        print(f"  - MAX_LENGTH: {MAX_LENGTH}")
        print(f"  - BATCH_SIZE: {BATCH_SIZE}")
        print(f"  - LoRA秩(r): 4")
        print(f"  - 样本数: {len(train_data)}")
        print("=" * 60)
    except Exception as e:
        print(f"\n训练过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

def test_minimal_training():
    """最小化训练测试，用于诊断问题"""
    print("=" * 80)
    print("最小化训练测试")
    print("=" * 80)
    
    MODEL_PATH = "/data/qwen"
    DATA_FOLDER = "/data/dataset"
    OUTPUT_DIR = "/data/qwenoutput_choice"
    
    # 最小化配置
    MAX_LENGTH = 128
    BATCH_SIZE = 1
    GRADIENT_ACCUMULATION_STEPS = 4
    NUM_EPOCHS = 1
    
    # 加载少量数据
    print("\n1. 加载少量数据...")
    json_files = glob.glob(os.path.join(DATA_FOLDER, "*.json"))[:10]  # 只加载10个文件
    all_data = []
    
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, dict) and "question" in data and "answer" in data:
                question_data = data.get("question", {})
                answer_data = data.get("answer", [])
                
                if isinstance(question_data, dict) and answer_data:
                    question_stem = question_data.get("question_stem", "").strip()
                    question_text = question_data.get("question", "").strip()
                    options = question_data.get("options", [])
                    
                    # 组合问题
                    if question_stem and question_text:
                        combined_question = f"{question_stem}\n{question_text}"
                    elif question_stem:
                        combined_question = question_stem
                    elif question_text:
                        combined_question = question_text
                    else:
                        continue
                    
                    # 提取答案
                    answer_letter = answer_data[0].strip().upper() if answer_data else ""
                    if not answer_letter:
                        continue
                    
                    answer_text = answer_letter
                    for option in options:
                        if option.strip().upper().startswith(f"{answer_letter}.") or option.strip().startswith(answer_letter):
                            answer_text = option.strip()
                            break
                    
                    all_data.append({
                        "combined_question": combined_question,
                        "options": options,
                        "answer_text": answer_text
                    })
        except:
            continue
    
    print(f"加载了 {len(all_data)} 个样本")
    
    if len(all_data) == 0:
        print("没有加载到数据!")
        return
    
    # 创建简单prompt
    train_texts = []
    for item in all_data:
        options_text = "\n".join(item["options"]) if item["options"] else ""
        prompt = f"问题: {item['combined_question']}"
        if options_text:
            prompt += f"\n选项:\n{options_text}"
        prompt += f"\n答案: {item['answer_text']}"
        train_texts.append(prompt)
    
    # 加载tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATH,
        trust_remote_code=True,
    )
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # 创建数据集
    dataset = Dataset.from_dict({"text": train_texts})
    
    def tokenize_function(examples):
        tokenized = tokenizer(
            examples["text"],
            truncation=True,
            padding=False,
            max_length=MAX_LENGTH,
            return_tensors=None
        )
        tokenized["labels"] = tokenized["input_ids"].copy()
        return tokenized
    
    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        batch_size=2,
        remove_columns=dataset.column_names
    )
    
    # 加载模型（不使用梯度检查点）
    torch.cuda.empty_cache()
    
    try:
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            device_map="auto",
            trust_remote_code=True,
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
        )
        print("✅ 成功加载模型")
    except Exception as e:
        print(f"模型加载失败: {e}")
        return
    
    # 配置LoRA（最小化）
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        inference_mode=False,
        r=2,  # 最小秩
        lora_alpha=4,
        lora_dropout=0.05,
        target_modules=["q_proj"],  # 只针对一个模块
        bias="none",
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # 训练参数（最小化）
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        overwrite_output_dir=True,
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        learning_rate=1e-4,
        fp16=True,
        logging_steps=1,
        save_strategy="no",
        remove_unused_columns=False,
        gradient_checkpointing=False,  # 禁用梯度检查点
        optim="adamw_torch",
        report_to=[],
        max_grad_norm=0.5,
    )
    
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=data_collator,
        tokenizer=tokenizer,
    )
    
    print("\n开始最小化训练测试...")
    try:
        trainer.train()
        print("✅ 最小化训练测试成功!")
    except Exception as e:
        print(f"❌ 最小化训练测试失败: {e}")
        import traceback
        traceback.print_exc()

def check_environment():
    """检查环境"""
    print("=" * 80)
    print("环境检查")
    print("=" * 80)
    
    print(f"PyTorch版本: {torch.__version__}")
    print(f"CUDA可用: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"CUDA版本: {torch.version.cuda}")
        print(f"GPU数量: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
            print(f"  - 显存: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.2f} GB")
    
    # 检查关键包版本
    import importlib.metadata
    try:
        print(f"Transformers版本: {importlib.metadata.version('transformers')}")
    except:
        print("Transformers版本: 未知")
    
    try:
        print(f"Accelerate版本: {importlib.metadata.version('accelerate')}")
    except:
        print("Accelerate版本: 未知")
    
    try:
        print(f"Datasets版本: {importlib.metadata.version('datasets')}")
    except:
        print("Datasets版本: 未知")
    
    try:
        print(f"PEFT版本: {importlib.metadata.version('peft')}")
    except:
        print("PEFT版本: 未知")

if __name__ == "__main__":
    # 设置环境变量
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["PYTORCH_ALLOC_CONF"] = "expandable_segments:True"
    
    # 清理GPU内存
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    # 检查环境
    check_environment()
    
    print("\n" + "=" * 80)
    print("选择运行模式:")
    print("1. 完整训练（可能遇到内存问题）")
    print("2. 最小化训练测试（诊断问题）")
    print("=" * 80)
    
    choice = input("请选择模式 (1 或 2): ").strip()
    
    if choice == "2":
        test_minimal_training()
    else:
        main()