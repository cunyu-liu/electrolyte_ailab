import os
import json
import re
import shutil
from tqdm import tqdm  # 如果没有安装，请运行 pip install tqdm

# 从 sft 的 jsonl 格式文件中逆向寻找原始的 md 文件


# ================= 配置区 =================
# 1. 所有的 MD 文件所在的根目录 (搜索范围)
INPUT_MD_DIR = "/home/chemind/allcode_chemind_server/pdf-md/mineru_superchem_output"

# 2. 你的 JSONL 数据文件路径
INPUT_JSONL_PATH = "/home/chemind/allcode_chemind_server/evaluate/eval_dataset/v2/superchem_sft_data_test.jsonl"

# 3. [新] 你希望把找回的 MD 文件存到哪里？
OUTPUT_RECOVERED_DIR = "/home/chemind/allcode_chemind_server/evaluate/eval_dataset/v2/recovered_md_files"
# =========================================

# --- 保持完全一致的清洗逻辑 (指纹算法) ---
def clean_text(text):
    if not text: return ""
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = text.strip()
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text

def parse_markdown_content(md_content):
    sections = {"Question": ""}
    # 我们只需要提取 Question 来做匹配指纹，其他部分不需要完整解析以节省时间
    parts = re.split(r'(^# .+)', md_content, flags=re.MULTILINE)
    
    current_key = None
    for part in parts:
        part = part.strip()
        if not part: continue
        if part.startswith("# "):
            header = part.replace("# ", "").strip()
            if "Question" in header: 
                current_key = "Question"
            else: 
                current_key = "Other"
        else:
            if current_key == "Question":
                sections["Question"] += part + "\n"
    return sections

def build_file_index(root_dir):
    """
    第一步：建立索引。
    遍历所有 MD 文件，计算它们的“问题指纹”，存入字典。
    Returns: Dict { "清洗后的问题文本": "文件完整路径" }
    """
    index_map = {}
    print(f"[-] 正在构建文件索引 (扫描 {root_dir})...")
    
    md_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".md"): # 通常是 full.md
                md_files.append(os.path.join(root, file))
    
    # 使用 tqdm 显示进度
    for file_path in tqdm(md_files, desc="Indexing MD files"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            parsed = parse_markdown_content(content)
            # 计算指纹
            fingerprint = clean_text(parsed["Question"])
            
            if fingerprint:
                # 存入字典。注意：如果不同文件有完全相同的问题，后者会覆盖前者
                # 但在 SFT 数据集中，去重通常是预期的
                index_map[fingerprint] = file_path
                
        except Exception as e:
            # print(f"读取失败: {file_path}")
            continue
            
    print(f"[-] 索引构建完成。内存中记录了 {len(index_map)} 个唯一问题源文件。")
    return index_map

def main():
    # 0. 准备输出目录
    if not os.path.exists(OUTPUT_RECOVERED_DIR):
        os.makedirs(OUTPUT_RECOVERED_DIR)
        print(f"[-] 创建输出目录: {OUTPUT_RECOVERED_DIR}")

    # 1. 建立 MD 文件指纹索引
    md_index = build_file_index(INPUT_MD_DIR)
    
    # 2. 遍历 JSONL 并匹配
    print(f"[-] 开始处理 JSONL: {INPUT_JSONL_PATH}")
    
    found_count = 0
    missing_count = 0
    
    with open(INPUT_JSONL_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    print(f"[-] JSONL 共 {len(lines)} 行，开始匹配并复制...")
    
    for idx, line in enumerate(tqdm(lines, desc="Matching & Copying")):
        try:
            data = json.loads(line)
            target_question = ""
            
            # 提取 User 提问
            for msg in data.get('messages', []):
                if msg['role'] == 'user':
                    target_question = msg['content']
                    break
            
            if not target_question:
                continue
                
            # 这里的 target_question 应该是已经被 clean 过的（因为是从 SFT 数据里读出来的）
            # 但为了保险，可以再 clean 一次，或者直接匹配
            # 因为你生成 JSONL 时已经 clean 过了，理论上这里直接匹配即可
            # 但考虑到从 JSON 读出来可能有细微转义差异，还是保持 Key 的一致性最重要
            # 这里的 target_question已经是生成后的结果，本身就是指纹
            
            # 核心匹配逻辑：O(1) 查找
            source_path = md_index.get(target_question)
            
            if source_path:
                # 找到了！
                # 为了防止文件名冲突 (所有文件都叫 full.md)，我们需要重命名
                # 命名格式: 行号_原文件夹名.md
                parent_folder = os.path.basename(os.path.dirname(source_path))
                new_filename = f"{idx:05d}_{parent_folder}.md"
                dest_path = os.path.join(OUTPUT_RECOVERED_DIR, new_filename)
                
                shutil.copy2(source_path, dest_path)
                found_count += 1
            else:
                missing_count += 1
                # 可选：记录没找到的行号
                # print(f"Line {idx} 未找到匹配源文件")
                
        except json.JSONDecodeError:
            print(f"Line {idx} JSON 解析失败")
            
    print("\n" + "="*30)
    print("处理完成报告")
    print("="*30)
    print(f"JSONL 总行数: {len(lines)}")
    print(f"成功找回并复制: {found_count}")
    print(f"未找到对应文件: {missing_count}")
    print(f"文件保存位置: {OUTPUT_RECOVERED_DIR}")
    
    if missing_count > 0:
        print("\n[注意] 未找到的原因可能是：")
        print("1. MD源文件已被删除或移动。")
        print("2. clean_text 逻辑在生成 JSONL 后被修改过，导致指纹不匹配。")
        print("3. JSONL 中的文本包含特殊转义字符。")

if __name__ == "__main__":
    main()