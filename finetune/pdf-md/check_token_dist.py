import json
import numpy as np
from transformers import AutoTokenizer
from tqdm import tqdm
import os

'''

如何解读结果
运行脚本后，你会看到类似下面的输出：

P95 / P99 数值：

这是你设置微调参数 model_max_length (或 max_seq_length) 的最重要参考。

如果 P99 是 3500，设为 4096 是最安全的。

如果 P99 是 7800，但你想省显存，可以设为 4096，这意味着你会截断 1% 的长数据（可能会丢失部分答案，需权衡）。

超长样本 (Outliers)：

如果发现有个别样本达到了 20k tokens（通常是因为 MinerU 把整本书的参考文献都识别进去了，或者解析错误导致文本死循环重复），必须剔除。这些脏数据会严重拖慢训练速度并可能导致 OOM。
'''

# ================= 配置区 =================
# 你的 SFT 数据文件路径
DATA_FILE = "/home/ChemMind/Allcode/SFTdata/superchem_sft_data.jsonl"

# Tokenizer 路径
# 如果你本地有 Qwen 模型的权重，请改为本地路径，例如: "/path/to/Qwen2.5-7B-Instruct"
# 如果没有，HuggingFace 在线拉取通常很快（只下 tokenizer 配置，不下载模型权重）
MODEL_ID = "/home/ChemMind/.cache/modelscope/hub/models/Qwen/Qwen3-8B" 
# =========================================

def print_ascii_histogram(data, bins=20):
    """在终端打印字符画直方图"""
    counts, bin_edges = np.histogram(data, bins=bins)
    max_count = max(counts)
    
    print("\n[Token 长度分布直方图]")
    for i in range(len(counts)):
        if counts[i] == 0:
            continue
        
        # 计算条形长度 (最大长度 50 字符)
        bar_len = int(50 * counts[i] / max_count)
        bar = "█" * bar_len
        
        range_str = f"{int(bin_edges[i])}-{int(bin_edges[i+1])}"
        print(f"{range_str:>12} : {bar} ({counts[i]})")

def main():
    if not os.path.exists(DATA_FILE):
        print(f"[!] 找不到文件: {DATA_FILE}")
        return

    print(f"[-] 正在加载 Tokenizer: {MODEL_ID} ...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    except Exception as e:
        print(f"[!] 加载 Tokenizer 失败: {e}")
        print("请检查网络，或将 MODEL_ID 修改为本地已下载的 Qwen 模型路径。")
        return

    print(f"[-] 开始扫描数据: {DATA_FILE}")
    
    lengths = []
    long_samples = [] # 记录过长样本的 ID
    
    # 阈值：用于通过记录超长样本 (例如超过 8192)
    LONG_THRESHOLD = 8192 

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in tqdm(lines, desc="Tokenizing"):
        try:
            item = json.loads(line)
            messages = item["messages"]
            custom_id = item.get("custom_id", "unknown")
            
            # 关键：应用聊天模板，这才是模型真正看到的字符串格式
            # Qwen 的模板通常会添加 <|im_start|>system...<|im_end|> 等
            text = tokenizer.apply_chat_template(
                messages, 
                tokenize=False, 
                add_generation_prompt=False
            )
            
            # 计算 Token 数量
            tokens = tokenizer(text)
            length = len(tokens["input_ids"])
            
            lengths.append(length)
            
            if length > LONG_THRESHOLD:
                long_samples.append((custom_id, length))
                
        except Exception as e:
            print(f"[!] 解析错误: {e}")

    if not lengths:
        print("[!] 没有读取到有效数据。")
        return

    # 转换为 numpy 数组方便统计
    lengths = np.array(lengths)

    print("\n" + "="*40)
    print("       数据集 Token 长度统计报告")
    print("="*40)
    print(f"总样本数      : {len(lengths)}")
    print(f"Min Length    : {np.min(lengths)}")
    print(f"Max Length    : {np.max(lengths)}")
    print(f"Average       : {np.mean(lengths):.2f}")
    print(f"Median (50%)  : {np.median(lengths):.2f}")
    print("-" * 40)
    print(f"P90 (90% cover): {np.percentile(lengths, 90):.0f}")
    print(f"P95 (95% cover): {np.percentile(lengths, 95):.0f}")
    print(f"P99 (99% cover): {np.percentile(lengths, 99):.0f}")
    print("="*40)

    # 打印直方图
    print_ascii_histogram(lengths)

    # 打印超长样本警告
    if long_samples:
        print(f"\n[!] 发现 {len(long_samples)} 个样本超过 {LONG_THRESHOLD} Tokens:")
        # 只打印前 5 个
        for lid, llen in sorted(long_samples, key=lambda x: x[1], reverse=True)[:5]:
            print(f"    - ID: {lid} | Length: {llen}")
        if len(long_samples) > 5:
            print(f"    ... 等 (共 {len(long_samples)} 个)")
            
    print("\n[建议]")
    p95 = np.percentile(lengths, 95)
    if p95 < 2048:
        print(f"-> 数据较短，推荐 max_seq_length 设置为 2048 以节省显存。")
    elif p95 < 4096:
        print(f"-> 推荐 max_seq_length 设置为 4096。")
    elif p95 < 8192:
        print(f"-> 推荐 max_seq_length 设置为 8192。")
    else:
        print(f"-> 数据很长（P95={p95:.0f}），请确保显存充足，或考虑截断超长数据。")

if __name__ == "__main__":
    main()