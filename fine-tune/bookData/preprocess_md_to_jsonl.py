import os
import json
import glob
from tqdm import tqdm  # 如果没有安装，运行 pip install tqdm

# ==================== 配置区域 ====================

# 1. 你的 Markdown 文件夹路径 (请修改这里)
INPUT_FOLDER = "/home/ChemMind/Allcode/bookData" 

# 2. 输出的 JSONL 文件路径 (生成的这个文件用于 CPT 训练)
OUTPUT_FILE = "/home/ChemMind/Allcode/CPTdata/cpt_data.jsonl"

# 3. JSONL 中的 Key 名称 (需与 CPT 训练脚本中的 TEXT_COLUMN_NAME 一致)
TEXT_COLUMN = "text"

# ==================== 转换逻辑 ====================

def convert_md_to_jsonl():
    # 检查输入路径是否存在
    if not os.path.exists(INPUT_FOLDER):
        print(f"错误：文件夹 '{INPUT_FOLDER}' 不存在，请检查路径。")
        return

    # 获取所有 .md 文件
    md_files = glob.glob(os.path.join(INPUT_FOLDER, "**/*.md"), recursive=True)
    print(f"发现 {len(md_files)} 个 Markdown 文件，准备开始转换...")

    count = 0
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        # 使用 tqdm 显示进度条
        for file_path in tqdm(md_files, desc="Processing"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                # 跳过空文件
                if not content:
                    continue
                
                # 构造数据对象
                data = {TEXT_COLUMN: content}
                
                # 写入一行 JSON
                outfile.write(json.dumps(data, ensure_ascii=False) + "\n")
                count += 1
                
            except Exception as e:
                print(f"\n警告：处理文件 {file_path} 时出错: {e}")

    print(f"\n转换完成！")
    print(f"- 有效文件数：{count}")
    print(f"- 输出文件：{os.path.abspath(OUTPUT_FILE)}")
    print(f"- 现在的你可以直接运行 CPT 训练脚本了。")

if __name__ == "__main__":
    convert_md_to_jsonl()