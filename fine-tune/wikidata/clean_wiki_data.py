import json
import re
import hashlib
import os

# 配置路径
INPUT_FILE = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/wikidata/wiki_data_depth1.jsonl"
OUTPUT_FILE = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/wikidata/wiki_data_depth1_clean.jsonl"

# 配置清洗阈值
MIN_LENGTH_CHARS = 200  # 文本少于200字符的丢弃（通常是无效页面）

def clean_wiki_text(text):
    """
    清洗核心逻辑：
    1. 截断无效的尾部章节（参考文献、外部链接等）
    2. 移除多余空白
    """
    # 1. 截断尾部噪声章节
    # 匹配常见的 Wikipedia 尾部标题，不区分大小写
    # 格式通常是 "== References ==" 或 "==External links=="
    pattern = r'\n==\s*(References|See also|External links|Further reading|Notes|Bibliography|Sources)\s*=='
    match = re.search(pattern, text, re.IGNORECASE)
    
    if match:
        # 截取匹配点之前的内容
        text = text[:match.start()]

    # 2. 移除一些可能残留的 Wikipedia 伪代码/标记 (视情况而定，Wikipedia-API通常已经处理得不错，这里主要处理空白)
    
    # 3. 规范化空白字符：将连续的换行符替换为两个换行符（段落），连续空格替换为一个
    # 先把所有连续空白(除了换行)变成一个空格
    text = re.sub(r'[ \t\r\f\v]+', ' ', text)
    # 处理换行：保留段落结构，去除过多的空行
    # 将3个以上换行变成2个
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def is_valid_content(title, text):
    """
    过滤逻辑：
    1. 排除消歧义页面
    2. 排除过短内容
    """
    # 检查是否是消歧义页面
    if "disambiguation" in title.lower() or "may refer to:" in text[:200].lower():
        return False
        
    # 长度检查
    if len(text) < MIN_LENGTH_CHARS:
        return False
        
    return True

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    print(f"Processing {INPUT_FILE}...")
    
    seen_hashes = set()
    total_count = 0
    kept_count = 0
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as fin, \
         open(OUTPUT_FILE, 'w', encoding='utf-8') as fout:
        
        for line in fin:
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                raw_text = data.get("text", "")
                
                # 分离标题和正文（假设爬虫存的是 "Title\n\nContent"）
                # 为了更精准清洗，我们主要处理正文，但 text 包含了标题
                # 这里直接对整体进行清洗
                
                # 1. 清洗文本
                cleaned_text = clean_wiki_text(raw_text)
                
                # 获取标题用于判断（API返回的第一行通常是标题，或者从meta里拿url/category，这里简单从text第一行取）
                title = cleaned_text.split('\n')[0] if cleaned_text else ""
                
                # 2. 过滤内容
                if not is_valid_content(title, cleaned_text):
                    continue
                
                # 3. 去重 (计算内容的 hash)
                content_hash = hashlib.md5(cleaned_text.encode('utf-8')).hexdigest()
                if content_hash in seen_hashes:
                    continue
                seen_hashes.add(content_hash)
                
                # 4. 构造 CPT 训练数据格式
                # 对于 CPT，通常只需要纯文本，或者保留 json 结构
                # 这里保留 jsonl 结构，更新 text 字段
                data["text"] = cleaned_text
                
                # 写入
                fout.write(json.dumps(data, ensure_ascii=False) + "\n")
                kept_count += 1
                
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"Error processing line: {e}")
                continue
            
            total_count += 1
            if total_count % 100 == 0:
                print(f"Processed {total_count} lines, kept {kept_count}...")

    print(f"Done. Total processed: {total_count}. Kept: {kept_count}. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()