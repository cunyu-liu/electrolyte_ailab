# 从习题问答对中选择电化学题和计算题。
import json

def transform_to_qwen_sft(item):
    """
    将原始字典转换为 Qwen 期待的 messages 格式
    """
    # 构建用户问题：合并题干、具体问题和单位要求
    stem = item.get("question", {}).get("question_stem", "")
    sub_q = item.get("question", {}).get("question", "")
    unit = item.get("question", {}).get("unit", "")
    
    user_content = f"题目：{stem}\n问：{sub_q}"
    if unit:
        user_content += f"（请以 {unit} 为单位回答）"

    # 构建模型回答：包含解题过程和最终答案
    solution = item.get("solution", "")
    final_answer = item.get("answer", "")
    assistant_content = f"解题过程：\n{solution}\n\n最终答案：{final_answer}"

    # 返回符合 Qwen SFT 规范的结构
    return {
        "messages": [
            {"role": "system", "content": "你是一个电化学专家，请根据题目要求提供详细的计算过程和准确的答案。"},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content}
        ]
    }

def filter_and_convert(input_file, output_file):
    count = 0
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取文件失败: {e}")
        return

    with open(output_file, 'w', encoding='utf-8') as out_f:
        for item in data:
            # 严格匹配：类型为 Calculation 且 领域为 electrochemistry
            if item.get("type") == "Calculation" or item.get("domain") == "electrochemistry":
                # 转换格式
                sft_data = transform_to_qwen_sft(item)
                # 写入 JSONL
                out_f.write(json.dumps(sft_data, ensure_ascii=False) + '\n')
                count += 1
    
    print(f"提取并转换完成！共生成 {count} 条 SFT 数据。")
    print(f"输出文件路径: {output_file}")

# --- 执行区 ---
input_path = '/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/习题问答对.json'
output_path = '/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/习题问答对_qwen_sft.jsonl'

filter_and_convert(input_path, output_path)