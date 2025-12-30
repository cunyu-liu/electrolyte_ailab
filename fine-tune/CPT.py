import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer, DataCollatorForLanguageModeling
from peft import LoraConfig, get_peft_model
from trl import SFTConfig, SFTTrainer # 依然保留 SFTTrainer 作为组件，但配置为“纯文本模式”

# 1. 针对 5090 的 CPT 专用配置
model_id = "Qwen/Qwen3-7B"
MAX_SEQ_LENGTH = 4096  #先小点

# 2. 纯净的数据处理逻辑：将所有文档拼接到一起并按 MAX_SEQ_LENGTH 切分
def tokenize_function(examples, tokenizer):
    # 核心：将文本转化为 input_ids，不添加任何指令模板
    return tokenizer(examples["text"], truncation=False)

# 3. 核心 CPT 方案
def run_cpt():
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        attn_implementation="flash_attention_2"
    )

    # DoRA 配置
    peft_config = LoraConfig(
        r=128, lora_alpha=256,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        use_dora=True,
        task_type="CAUSAL_LM"
    )
    model = get_peft_model(model, peft_config)

    # 4. 训练参数：严格遵循 CPT 范式
    training_args = SFTConfig(
        output_dir="./qwen3-cpt-professional",
        max_seq_length=MAX_SEQ_LENGTH,
        dataset_text_field="text", # 指定纯文本字段
        packing=True,              # CPT 必须开启：将短文本打包以减少 Padding
        neftune_noise_alpha=5,     # NEFTune 注入
        per_device_train_batch_size=16, 
        gradient_accumulation_steps=8,
        learning_rate=5e-5,
        lr_scheduler_type="cosine",
        bf16=True,
        num_train_epochs=1,        # CPT 通常 1-2 epoch 即可，防止过拟合
        save_steps=500,
        logging_steps=10,
        gradient_checkpointing=True,
        # Loss Masking 通过 DataCollator 实现
    )

    # 5. 使用 SFTTrainer 作为 CausalLM 训练器 (最稳妥的 NEFTune 实现方式)
    # 虽然叫 SFTTrainer，但在 packing=True 且无 template 情况下，它就是标准的 CPT 流程
    trainer = SFTTrainer(
        model=model,
        train_dataset=your_dataset, # 包含 text 字段的数据集
        peft_config=peft_config,
        args=training_args,
        # DataCollatorForLanguageModeling 会自动对 pad 进行 loss masking (-100)
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False)
    )

    trainer.train()