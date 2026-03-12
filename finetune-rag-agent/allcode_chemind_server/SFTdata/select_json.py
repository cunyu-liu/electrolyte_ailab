import json
import os

def filter_and_save_json(input_file, output_file):
    count = 0
    filtered_data = []
    
    # 1. 读取原始 JSON 文件
    print(f"正在读取文件: {input_file}")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取文件失败: {e}")
        return

    # 2. 遍历并应用“双重否定”排除逻辑
    for item in data:
        # 安全获取字段，防止字段不存在报错
        q_type = item.get("type", "")
        q_domain = item.get("domain", "")

        # =======================================================
        # 核心逻辑：not ... and not ... (排除法)
        # 含义：保留那些【既不是计算题】且【也不是电化学题】的数据
        # =======================================================
        if not q_type == "Calculation" and not "electrochemistry" in q_domain:
            
            # 如果满足条件，将原始 item 加入列表（不做任何 SFT 格式修改）
            filtered_data.append(item)
            count += 1

    # 3. 将筛选后的结果保存为 JSON 文件
    try:
        with open(output_file, 'w', encoding='utf-8') as out_f:
            # indent=4 保持格式美观，ensure_ascii=False 防止中文乱码
            json.dump(filtered_data, out_f, indent=4, ensure_ascii=False)
        
        print(f"筛选完成！")
        print(f"原始数据总数: {len(data)}")
        print(f"保留数据总数: {count} (已排除 计算题 和 电化学题)")
        print(f"结果已保存至: {output_file}")
        
    except Exception as e:
        print(f"写入文件失败: {e}")

# --- 配置与执行 ---
if __name__ == "__main__":
    # 输入文件路径
    input_path = '/home/chemind/allcode_chemind_server/SFTdata/习题问答对.json'
    
    # 输出文件路径 (建议文件名体现“exclude”含义)
    output_path = '/home/chemind/allcode_chemind_server/SFTdata/习题问答对_v1test.json'

    # 执行筛选
    filter_and_save_json(input_path, output_path)