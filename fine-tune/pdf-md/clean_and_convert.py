import os
import json
import re

# ================= 配置区域 =================
INPUT_DIR = "./mineru_output"
OUTPUT_FILE = "cpt_train_data.jsonl"
MIN_LENGTH = 500  # 综述论文通常较长，建议提高阈值
# ===========================================

# --- 修改点 1: 新增化学式修复函数 ---
def fix_chemical_formulas(text):
    """
    专门修复电池领域常见的化学式 OCR 识别错误
    """
    # 1. 修复离子符号（如 Li+ 误转为 Li + 或 Li+）
    text = re.sub(r'Li\s*([\+\-])', r'$Li^\1$', text)
    
    # 2. 基础化学式下标化修复 (仅针对常见的电池材料元素组合)
    # 匹配如 Li2O, LiPF6, LiClO4, Li2CO3 等模式
    compounds = ['Li', 'Na', 'PO', 'SO', 'CO', 'PF', 'ClO', 'FePO']
    for comp in compounds:
        # 寻找后面紧跟数字且不在 $ 符号内的组合
        pattern = rf'({comp})(\d+)'
        text = re.sub(pattern, r'$\1_\2$', text)
    
    # 3. 修复 MinerU 常见的公式截断：如将 \text{...} 误识别
    text = re.sub(r'\\text\s*\{\s*(.*?)\s*\}', r' \1 ', text)
    
    return text

# --- 修改点 2: 嵌入 clean_text 流程 ---
# 在原 clean_text 函数中，第 4 步和第 5 步之间插入：
# text = fix_chemical_formulas(text)

def clean_text(text):
    if not text:
        return ""

    # 1. 语义化处理图表占位符
    text = re.sub(r'!\[.*?\]\(.*?\)', '[FIGURE]', text)
    
    # 2. 移除 Markdown 链接 URL
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

    # 3. 参考文献截断
    patterns = [r'\n#+\s*References\s*\n', r'\n#+\s*Bibliography\s*\n', r'\n#+\s*参考文献\s*\n']
    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            text = text[:match.start()]
            break

    # 4. 【新增】化学式与公式修复
    text = fix_chemical_formulas(text)

    # 5. 清理公式噪音并规整
    text = re.sub(r'\\\(', '$', text)
    text = re.sub(r'\\\)', '$', text)
    
    lines = [line.strip() for line in text.split('\n')]
    lines = [line for line in lines if len(line) > 0 and not re.match(r'^\d+\s*$', line)]
    
    cleaned_text = '\n\n'.join(lines)
    cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
    
    return cleaned_text.strip()

def process_directory():
    if not os.path.exists(INPUT_DIR):
        print(f"[Error] 找不到目录: {INPUT_DIR}")
        return

    print(f"[*] 正在从 {INPUT_DIR} 提取 CPT 语料...")
    valid_count = 0
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        # 获取所有 PDF 转化后的子文件夹
        subfolders = [d for d in os.listdir(INPUT_DIR) if os.path.isdir(os.path.join(INPUT_DIR, d))]
        
        for folder_name in subfolders:
            folder_path = os.path.join(INPUT_DIR, folder_name)
            # 定位主 MD 文件
            md_candidates = [f for f in os.listdir(folder_path) if f.endswith('.md')]
            
            if not md_candidates:
                continue
            
            # 策略：选取文件最大的 md (通常是 full content)
            main_md = max(md_candidates, key=lambda x: os.path.getsize(os.path.join(folder_path, x)))
            full_path = os.path.join(folder_path, main_md)
            
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    raw_content = f.read()
                
                cleaned_content = clean_text(raw_content)
                
                if len(cleaned_content) >= MIN_LENGTH:
                    data = {
                        "text": cleaned_content,
                        "meta": {
                            "folder": folder_name,
                            "char_count": len(cleaned_content)
                        }
                    }
                    f_out.write(json.dumps(data, ensure_ascii=False) + "\n")
                    valid_count += 1
            except Exception as e:
                print(f"[!] 跳过 {folder_name}: {e}")

    print(f"[*] 清洗完成。")
    print(f"[*] 产出文件: {OUTPUT_FILE} (共 {valid_count} 篇文档)")

if __name__ == "__main__":
    process_directory()