import os

# 查找指定路径下所有 .smi 文件的路径，递归所有子目录
def find_smi_files(folder_path):
    smi_files = []
    # os.walk 会遍历 folder_path 下的所有目录及子目录
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".smi"):
                smi_files.append(os.path.join(root, file))
    return smi_files

# 合并所有 .smi 文件的内容
def merge_smi_files(smi_files, output_file):
    with open(output_file, 'w') as outfile:
        for smi_file in smi_files:
            with open(smi_file, 'r') as infile:
                # 逐行读取并写入输出文件
                for line in infile:
                    outfile.write(line)

# 所有待查找的路径
path_list = [
    "/home/gaoyuchen/Molecular_generation/test_0325/1_CHO_20250327",
    "/home/gaoyuchen/Molecular_generation/test_0325/2_CH_20250327",
    "/home/gaoyuchen/Molecular_generation/test_0325/3_CHF_20250327",
    "/home/gaoyuchen/Molecular_generation/test_0325/4_CHOF_20250327",
    "/home/gaoyuchen/Molecular_generation/test_0325/5_CHS_20250327"
]


output_file_path = "/home/gaoyuchen/Molecular_generation/compare/merged_data/merged_0406.smi"

# 确保输出目录存在
os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

# 查找所有 .smi 文件的路径
all_smi_files = []
for folder in path_list:
    all_smi_files.extend(find_smi_files(folder))

# 合并所有 .smi 文件
merge_smi_files(all_smi_files, output_file_path)

print(f"合并完成，输出文件路径为：{output_file_path}")
