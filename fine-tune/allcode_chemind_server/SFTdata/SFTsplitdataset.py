import json
import os
import random

# ================= 配置区域 =================
INPUT_FILE = "/home/ChemMind/Allcode/SFTdata/allsftdata_shuffled.jsonl"
OUTPUT_TRAIN = "/home/ChemMind/Allcode/SFTdata/allsftdata_shuffled_train.jsonl"
OUTPUT_TEST = "/home/ChemMind/Allcode/SFTdata/allsftdata_shuffled_test.jsonl"

TRAIN_RATIO = 0.95     # 训练集比例
RANDOM_SEED = 42
# ===========================================

def load_jsonl(file_path):
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
    return data

def main():
    print(">>> 开始划分训练集 / 测试集")

    data = load_jsonl(INPUT_FILE)
    total = len(data)

    if total == 0:
        print("❌ 输入数据为空，终止")
        return

    print(f"总样本数: {total}")

    # 再次打乱（防御式编程，保证完全随机）
    random.seed(RANDOM_SEED)
    random.shuffle(data)

    train_size = int(total * TRAIN_RATIO)
    train_data = data[:train_size]
    test_data = data[train_size:]

    print(f"训练集: {len(train_data)}")
    print(f"测试集: {len(test_data)}")

    # 写出训练集
    with open(OUTPUT_TRAIN, "w", encoding="utf-8") as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # 写出测试集
    with open(OUTPUT_TEST, "w", encoding="utf-8") as f:
        for item in test_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print("✅ 划分完成")
    print(f"   训练集文件: {OUTPUT_TRAIN}")
    print(f"   测试集文件: {OUTPUT_TEST}")

if __name__ == "__main__":
    main()
