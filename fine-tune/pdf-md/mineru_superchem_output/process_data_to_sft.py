import os
import json
import re
'''
任务范围与计划
目标：遍历 mineru_superchem_output 文件夹，读取所有 full.md，解析出“问题”、“答案”和“详细解析”，生成 sft_train.jsonl。

处理逻辑：

解析 (Extract)：利用正则表达式识别 Markdown 的一级标题（# Question, # Answer, # Detailed Explanation, # CHECKPOINT）。

清洗 (Transform)：

去除图片：Markdown 中的 ![](images/xxx.jpg) 本地路径对于纯文本模型（Text-only LLM）是无效字符，甚至会产生幻觉。脚本将去除图片标签，但保留周围的文本（因为化学式 SMILES 字符串通常在图片下方，是文本形式，很有价值）。

合并答案：将 Answer（通常很短）和 Detailed Explanation（详细推导）合并作为模型的输出（assistant）。CHECKPOINT 内容通常是解析的一部分，也会追加到输出中。

格式化 (Load)：转换为 Qwen/OpenAI 兼容的 ChatML 格式 ({"messages": [...]}).

输出文件：superchem_sft_data.jsonl。
'''



# ================= 配置区 =================
# 输入：MinerU 生成的输出目录
INPUT_DIR = "./mineru_superchem_output"
# 输出：SFT 训练数据文件
OUTPUT_FILE = "./superchem_sft_data.jsonl"
# 系统提示词 (System Prompt)
SYSTEM_PROMPT = "你是一个专业的化学专家。请根据提供的化学问题，分析反应机理，并给出正确的答案和详细解释。"
# =========================================

def clean_text(text):
    """
    清洗文本：
    1. 去除 Markdown 图片标签 ![](...)
    2. 去除多余的空行
    """
    if not text:
        return ""
    
    # 1. 去除图片标签 ![](images/...)
    # 正则解释：! \[ 任意字符 \] ( 任意字符 )
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    
    # 2. 去除可能残留的 "images/xxx.jpg" 文本（有些转换器会把路径漏出来）
    # 如果 MinerU 输出很干净，这一步是防御性的
    
    # 3. 去除首尾空白
    text = text.strip()
    
    # 4. 将连续的多个换行符压缩为两个（保留段落感，但去除过大的空白）
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text

def parse_markdown_content(md_content):
    """
    解析 Markdown 内容，返回字典结构
    """
    sections = {
        "Question": "",
        "Answer": "",
        "Detailed Explanation": "",
        "Extra": [] # 用于存放 CHECKPOINT 等额外信息
    }
    
    # 按一级标题 # 分割
    # 这是一个简单的分割逻辑，假设 MinerU 的输出结构相对固定
    # split 后，第一个元素通常是空的（如果在第一行就有标题）
    parts = re.split(r'(^# .+)', md_content, flags=re.MULTILINE)
    
    current_key = None
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        # 判断是否是标题
        if part.startswith("# "):
            header = part.replace("# ", "").strip()
            if "Question" in header:
                current_key = "Question"
            elif "Answer" in header:
                current_key = "Answer"
            elif "Detailed Explanation" in header:
                current_key = "Detailed Explanation"
            elif "CHECKPOINT" in header:
                current_key = "Extra"
            else:
                # 其他未知的标题，暂时归类到 Extra
                current_key = "Extra"
        else:
            # 这是内容部分
            if current_key == "Extra":
                sections["Extra"].append(part)
            elif current_key in sections:
                # 拼接内容（防止同一个标题下有多段被分割）
                sections[current_key] += part + "\n"

    return sections

def build_sft_entry(file_id, sections):
    """
    构建 Qwen SFT 格式的 JSON 对象
    """
    question = clean_text(sections["Question"])
    answer = clean_text(sections["Answer"])
    explanation = clean_text(sections["Detailed Explanation"])
    
    # 处理 Checkpoints，将其追加到解析后面
    extras = [clean_text(e) for e in sections["Extra"]]
    extra_text = "\n\n".join(extras)
    
    if not question:
        return None

    # 构建完整的 Assistant 回复
    # 格式：
    # Correct Answer: X
    #
    # Detailed Explanation:
    # ...
    #
    # Checkpoints:
    # ...
    full_response = ""
    
    if answer:
        full_response += f"{answer}\n\n"
    
    if explanation:
        full_response += f"### Detailed Explanation\n{explanation}"
    
    if extra_text:
        full_response += f"\n\n### Checkpoints Analysis\n{extra_text}"

    # 构造 JSON
    entry = {
        "custom_id": file_id, # 方便后续追踪是哪个文件的数据
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
            {"role": "assistant", "content": full_response.strip()}
        ]
    }
    return entry

def main():
    if not os.path.exists(INPUT_DIR):
        print(f"[错误] 输入目录不存在: {INPUT_DIR}")
        return

    valid_count = 0
    total_files = 0
    
    print(f"[-] 开始扫描目录: {INPUT_DIR}")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        # 遍历所有子文件夹
        for root, dirs, files in os.walk(INPUT_DIR):
            for file in files:
                if file == "full.md":
                    total_files += 1
                    file_path = os.path.join(root, file)
                    # 获取父文件夹名作为 ID (例如 battery_review_01)
                    folder_name = os.path.basename(root)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f_in:
                            content = f_in.read()
                            
                        parsed_sections = parse_markdown_content(content)
                        sft_entry = build_sft_entry(folder_name, parsed_sections)
                        
                        if sft_entry:
                            # 写入 JSONL (一行一个 JSON)
                            f_out.write(json.dumps(sft_entry, ensure_ascii=False) + "\n")
                            valid_count += 1
                        
                        # 打印进度 (每100个)
                        if total_files % 100 == 0:
                            print(f"    已处理 {total_files} 个文件...")
                            
                    except Exception as e:
                        print(f"[!] 处理文件失败 {file_path}: {e}")

    print("="*30)
    print(f"[完成] 处理结束")
    print(f"[-] 总扫描文件: {total_files}")
    print(f"[-] 有效生成数: {valid_count}")
    print(f"[-] 结果已保存至: {OUTPUT_FILE}")
    print("="*30)
    
    # 预览第一条数据
    if os.path.exists(OUTPUT_FILE):
        print("\n[预览第一条数据]:")
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            if first_line:
                data = json.loads(first_line)
                print(json.dumps(data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()