import json
import random
from datasets import load_dataset
from tqdm import tqdm


# HF_TOKEN=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 HF_ENDPOINT=https://hf-mirror.com python /Users/liucunyu/Documents/all_code/thu_2025/fine-tune/download_qwen_mix.py

# ================= 配置区域 =================
OUTPUT_FILE = "qwen_sft_mix.jsonl"
SYSTEM_PROMPT = "You are a helpful assistant."

DATA_CONFIG = [
    # 1. WizardLM (Evol-Instruct) - [修复] 改为解析 conversations
    {
        "repo_id": "WizardLM/WizardLM_evol_instruct_V2_196k", 
        "count": 800, 
        "subset": None, 
        "type": "evol_instruct",
        "mapping": "parser_conversations" # 之前是字典映射，现在改用对话解析
    },
    # 2. GSM8K (Math) - [保持不变] 之前是成功的
    {
        "repo_id": "gsm8k", 
        "count": 600, 
        "subset": "main", 
        "type": "math",
        "mapping": {"user": ["question"], "assistant": ["answer"]}
    },
    # 3. Magicoder (Code) - [修复] 允许只使用 problem 字段
    {
        "repo_id": "ise-uiuc/Magicoder-OSS-Instruct-75K", 
        "count": 400, 
        "subset": None, 
        "type": "code",
        "mapping": "parser_magicoder" 
    },
    # 4. ShareGPT (Safety) - [保持不变] 之前是成功的
    {
        "repo_id": "shibing624/sharegpt_gpt4", 
        "count": 200, 
        "subset": None, 
        "type": "safety",
        "mapping": "parser_conversations" 
    }
]

# ================= 核心逻辑 =================

def format_qwen(user, assistant, source):
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant}
        ],
        "source": source
    }

def get_col(row, candidates):
    for key in candidates:
        if key in row and row[key]:
            return row[key]
    return None

def process_dataset():
    all_data = []
    
    for config in DATA_CONFIG:
        print(f"--- 正在处理: {config['repo_id']} ({config['type']}) ---")
        
        try:
            ds = load_dataset(config['repo_id'], config['subset'], split="train", streaming=True)
            ds = ds.shuffle(seed=42, buffer_size=1000)
            
            collected = 0
            iterator = iter(ds)
            pbar = tqdm(total=config['count'])
            
            while collected < config['count']:
                try:
                    row = next(iterator)
                except StopIteration:
                    break
                
                entry = None
                
                # === 策略1: 解析 conversations (WizardLM & ShareGPT) ===
                if config['mapping'] == "parser_conversations":
                    convs = row.get('conversations', [])
                    # 兼容不同格式: 有的是 list[dict], 有的是 list[list]
                    if isinstance(convs, list) and len(convs) >= 2:
                        # 尝试提取第一个 Human 和第一个 GPT
                        u_text, a_text = None, None
                        
                        for turn in convs:
                            # 兼容 {'from': 'human', 'value': '...'} 格式
                            role = turn.get('from', '') or turn.get('role', '')
                            val = turn.get('value', '') or turn.get('content', '')
                            
                            if role in ['human', 'user'] and not u_text:
                                u_text = val
                            elif role in ['gpt', 'assistant', 'model'] and not a_text:
                                a_text = val
                        
                        if u_text and a_text:
                            entry = format_qwen(u_text, a_text, config['type'])

                # === 策略2: 解析 Magicoder (Code) ===
                elif config['mapping'] == "parser_magicoder":
                    # 优先找 instruction，没有则用 problem
                    u_text = row.get('instruction') or row.get('problem')
                    # 优先找 solution，没有则找 response
                    a_text = row.get('solution') or row.get('response')
                    
                    if u_text and a_text:
                        entry = format_qwen(u_text, a_text, config['type'])

                # === 策略3: 简单列映射 (GSM8K) ===
                elif isinstance(config['mapping'], dict):
                    u = get_col(row, config['mapping']['user'])
                    a = get_col(row, config['mapping']['assistant'])
                    if u and a:
                        entry = format_qwen(u, a, config['type'])

                # === 保存 ===
                if entry:
                    all_data.append(entry)
                    collected += 1
                    pbar.update(1)
            
            pbar.close()
            
        except Exception as e:
            print(f"Error processing {config['repo_id']}: {e}")

    # 最终保存
    print(f"\n正在保存 {len(all_data)} 条数据...")
    random.shuffle(all_data)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for item in all_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(f"完成！已生成 {OUTPUT_FILE}")

if __name__ == "__main__":
    process_dataset()