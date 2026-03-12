import os
import json
import re
from tqdm import tqdm

# ================= 配置区 =================
# 1. MD 文件所在目录
INPUT_DIR = "/home/chemind/allcode_chemind_server/evaluate/eval_dataset/v2/recovered_md_files"
# 2. 输出的 JSONL 文件路径
OUTPUT_FILE = "/home/chemind/allcode_chemind_server/evaluate/eval_dataset/v2/pkuevaluation_data.jsonl"

def clean_text(text):
    if not text: return ""
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = text.strip()
    return text

def extract_options_robust(text):
    """
    强力提取选项：不依赖换行，支持单行混排、括号格式等。
    返回: (去除选项后的题目文本, 选项字典)
    """
    options = {}
    
    # 1. 定义可能的选项头模式
    # 匹配: "A.", "A)", "(A)", "A、" 后面跟空白
    # (?:^|\s) 确保它是单词的开始，防止匹配到单词中间的 A
    pattern = re.compile(r'(?:^|\s|\n)[\(（]?([A-E])[\.\)）\、](?:\s|$)', re.MULTILINE)
    
    # 2. 找到所有匹配项的位置
    matches = list(pattern.finditer(text))
    
    # 如果少于2个选项 (比如只有一个 A.)，或者没有找到，直接返回原文本
    if len(matches) < 2:
        return text, {}
    
    # 3. 校验顺序是否是 A, B, C... 
    # 如果文本里出现了 "A. xxx A. xxx" 或者 "B. xxx A. xxx"，这种可能是误报，放弃提取
    expected_char_code = ord('A')
    valid_matches = []
    
    for m in matches:
        char = m.group(1).upper()
        if ord(char) == expected_char_code:
            valid_matches.append(m)
            expected_char_code += 1
        else:
            # 如果遇到的不是预期的下一个字母（比如期望 B 却遇到了 D），停止查找
            # 或者如果是 A 开头重新开始（视具体情况，这里简单处理：只要不连续就不认）
            pass
    
    # 再次检查有效匹配数量
    if len(valid_matches) < 2:
        return text, {}

    # 4. 根据位置切片提取内容
    # 题目部分 = 第一个选项 A 之前的所有文本
    start_idx = valid_matches[0].start()
    question_part = text[:start_idx].strip()
    
    for i in range(len(valid_matches)):
        current_match = valid_matches[i]
        key = current_match.group(1).upper()
        
        # 内容开始位置 = 当前匹配的结束位置
        content_start = current_match.end()
        
        # 内容结束位置 = 下一个选项的开始位置 (如果是最后一个，就是文本末尾)
        if i < len(valid_matches) - 1:
            content_end = valid_matches[i+1].start()
        else:
            content_end = len(text)
            
        val = text[content_start:content_end].strip()
        options[key] = val

    return question_part, options

def parse_markdown_structure(md_content):
    """解析 MD 结构 (含 Checkpoints)"""
    data = {"Question": "", "Answer": "", "Explanation": "", "Checkpoints": []}
    parts = re.split(r'(^# .+)', md_content, flags=re.MULTILINE)
    current_key = None
    
    for part in parts:
        part = part.strip()
        if not part: continue
        if part.startswith("# "):
            header = part.replace("# ", "").strip()
            if "Question" in header: current_key = "Question"
            elif "Answer" in header: current_key = "Answer"
            elif "Detailed Explanation" in header: current_key = "Explanation"
            elif "CHECKPOINT" in header: current_key = "Checkpoint_Temp"
            else: current_key = None
        else:
            if current_key == "Checkpoint_Temp":
                # 清洗 Checkpoint 里的分数标记 (如 "2 PTS")
                lines = part.split('\n')
                cleaned_lines = []
                for l in lines:
                    # 去掉像 "2 PTS" 这样的行
                    if not re.match(r'^\d+\s*PTS\s*$', l.strip(), re.IGNORECASE):
                        cleaned_lines.append(l)
                content = "\n".join(cleaned_lines).strip()
                if content: data["Checkpoints"].append(content)
            elif current_key and current_key in data:
                data[current_key] += part + "\n"
    return data

def main():
    if not os.path.exists(INPUT_DIR):
        print(f"输入目录不存在: {INPUT_DIR}")
        return

    data_list = []
    files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.md')]
    print(f"开始处理 {len(files)} 个文件...")
    
    # 统计有多少个成功提取了选项
    extracted_options_count = 0 
    
    for file_name in tqdm(files):
        try:
            with open(os.path.join(INPUT_DIR, file_name), 'r', encoding='utf-8') as f:
                content = f.read()
            
            parsed = parse_markdown_structure(content)
            if not parsed["Question"]: continue
                
            # 1. 提取选项
            raw_q = clean_text(parsed["Question"])
            final_q, options_dict = extract_options_robust(raw_q)
            
            if options_dict:
                extracted_options_count += 1
            
            # 2. 构造 Explanation
            gt_text = ""
            if parsed["Answer"]: gt_text += f"[Standard Answer]\n{clean_text(parsed['Answer'])}\n\n"
            if parsed["Explanation"]: gt_text += f"[Detailed Explanation]\n{clean_text(parsed['Explanation'])}\n\n"
            if parsed["Checkpoints"]:
                gt_text += "[Key Checkpoints]\n"
                for i, cp in enumerate(parsed["Checkpoints"], 1):
                    gt_text += f"{i}. {cp}\n"
            
            entry = {
                "uuid": file_name.replace(".md", ""),
                "question_en": final_q,
                "options_en": options_dict,
                "explanation_en": gt_text
            }
            data_list.append(entry)
            
        except Exception as e:
            print(f"Error {file_name}: {e}")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for item in data_list:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
    print(f"处理完成。")
    print(f"总文件数: {len(data_list)}")
    print(f"成功提取选项的文件数: {extracted_options_count}")
    print(f"结果已保存至: {OUTPUT_FILE}")

    # 预览一条有选项的数据
    for item in data_list:
        if item['options_en']:
            print("\n[Preview Entry with Options]:")
            print(f"Question: {item['question_en'][:50]}...")
            print(f"Options: {json.dumps(item['options_en'], ensure_ascii=False)}")
            break

if __name__ == "__main__":
    main()