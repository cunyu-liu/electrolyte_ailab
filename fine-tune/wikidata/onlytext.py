import json

def process_jsonl(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        
        for line in f_in:
            if not line.strip():
                continue  # 跳过空行
            
            try:
                # 1. 解析每一行的 JSON
                data = json.loads(line)
                
                # 2. 提取 text 字段并构建新字典
                # 使用 .get() 可以防止某些行缺少 text 字段导致报错
                new_data = {"text": data.get("text", "")}
                
                # 3. 将新对象转回字符串并写入新文件
                f_out.write(json.dumps(new_data, ensure_ascii=False) + '\n')
                
            except json.JSONDecodeError:
                print(f"跳过格式错误行: {line[:50]}...")

# 使用方法
process_jsonl('/home/ChemMind/Allcode/CPTdata/wiki_data_depth1_clean.jsonl', '/home/ChemMind/Allcode/CPTdata/wiki_data_depth1_cleaned_text.jsonl')
print("处理完成！新文件已生成。")