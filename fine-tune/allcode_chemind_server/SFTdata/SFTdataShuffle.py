import json
import random
import os

# ================= 配置区域 =================
INPUT_FILE = "/home/ChemMind/Allcode/SFTdata/allsftdata.jsonl"      # 已经汇总好的输入文件
OUTPUT_FILE = "/home/ChemMind/Allcode/SFTdata/allsftdata_shuffled.jsonl"
RANDOM_SEED = 42
# ===========================================

def load_jsonl(file_path):
    """读取 jsonl 文件"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    data = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    print(f"已加载 {len(data)} 条样本")
    return data

def to_sharegpt(sample):
    """
    检查 / 转换为 ShareGPT(messages) 格式
    返回 None 表示样本非法
    """
    # 已经是 ShareGPT
    if "messages" in sample and isinstance(sample["messages"], list):
        return sample

    # Alpaca 格式 → ShareGPT
    if "instruction" in sample and "output" in sample:
        system_prompt = sample.get(
            "system",
            "你是一个在生物信息学、计算化学与药物发现领域具有专业能力的AI助手。"
        )

        user_content = sample["instruction"]
        if sample.get("input"):
            user_content += f"\n{sample['input']}"

        return {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": sample["output"]}
            ]
        }

    # 其他未知格式 → 丢弃
    return None

def main():
    print(">>> 开始 ShareGPT 格式检查与打乱")

    raw_data = load_jsonl(INPUT_FILE)

    # 格式检查 & 转换
    processed = []
    for d in raw_data:
        converted = to_sharegpt(d)
        if converted:
            processed.append(converted)

    print(f"格式合法样本数: {len(processed)} / {len(raw_data)}")

    if not processed:
        print("❌ 没有任何合法样本，终止")
        return

    # 打乱
    random.seed(RANDOM_SEED)
    random.shuffle(processed)

    # 写出
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for item in processed:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"✅ 完成！输出文件: {OUTPUT_FILE}")
    print(f"   总样本数: {len(processed)}")

if __name__ == "__main__":
    main()
