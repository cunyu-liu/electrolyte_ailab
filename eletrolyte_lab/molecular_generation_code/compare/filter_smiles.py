import pandas as pd
import os

# 读取res文件夹中的所有SMILES，按批次加载到内存
def load_smi_files_in_batches(smi_folder_path, batch_size=100000):
    smiles_from_smi = set()
    total_lines = 0  # 记录.smi文件的总行数
    for file_name in os.listdir(smi_folder_path):
        if file_name.endswith('.smi'):
            with open(os.path.join(smi_folder_path, file_name), 'r') as file:
                batch = []
                for line in file:
                    batch.append(line.strip())
                    total_lines += 1
                    if len(batch) >= batch_size:
                        # 一次性读取batch_size数量的SMILES并返回
                        smiles_from_smi.update(batch)
                        batch.clear()
                # 加载剩余的SMILES
                if batch:
                    smiles_from_smi.update(batch)
    print(f"已加载{smi_folder_path}中的 {total_lines} 行SMILES数据。")
    return smiles_from_smi

# 处理CSV文件的批次，检查每批次的SMILES
def process_batch(batch, smiles_from_smi, batch_num):
    smiles_from_csv = set(batch['SMILES'].dropna())  # 获取当前批次中的SMILES
    smiles_in_smi = smiles_from_csv.intersection(smiles_from_smi)  # 查找出现在.smi文件中的SMILES
    smiles_not_in_smi = smiles_from_csv.difference(smiles_from_smi)  # 查找不在.smi文件中的SMILES
    
    # 输出每个批次的处理情况
    print(f"处理第 {batch_num} 批次，批次大小: {len(batch)}")
    print(f"当前批次中，出现在.smi文件中的SMILES数: {len(smiles_in_smi)}")
    print(f"当前批次中，不在.smi文件中的SMILES数: {len(smiles_not_in_smi)}")
    
    return smiles_in_smi, smiles_not_in_smi

# 分批次处理CSV文件并与.smi文件进行比对
def compare_smiles_in_csv(csv_file_path, smi_folder_path, chunk_size=10000, smi_batch_size=100000):
    # 读取.smi文件的SMILES（按批次）
    smiles_from_smi = load_smi_files_in_batches(smi_folder_path, batch_size=smi_batch_size)
    
    # 用于存储最终结果
    all_smiles_in_smi = set()
    all_smiles_not_in_smi = set()

    # 按批次处理CSV文件
    total_rows = sum(1 for _ in open(csv_file_path))  # 获取CSV文件的总行数
    processed_rows = 0  # 已处理的行数

    for batch_num, chunk in enumerate(pd.read_csv(csv_file_path, chunksize=chunk_size), start=1):
        smiles_in_smi, smiles_not_in_smi = process_batch(chunk, smiles_from_smi, batch_num)
        all_smiles_in_smi.update(smiles_in_smi)
        all_smiles_not_in_smi.update(smiles_not_in_smi)
        
        processed_rows += len(chunk)
        
        # 输出进度
        progress = (processed_rows / total_rows) * 100
        print(f"处理进度：{processed_rows}/{total_rows} 行，完成 {progress:.2f}%\n",flush=True)
    
    return all_smiles_in_smi, all_smiles_not_in_smi


csv_file_path = '/home/gaoyuchen/Molecular_generation/compare/3_ep_data_clean_20241222_filled.csv' 
smi_folder_path = '/home/gaoyuchen/Molecular_generation/compare/res_0404' 


smiles_in_smi, smiles_not_in_smi = compare_smiles_in_csv(csv_file_path, smi_folder_path)

print(f"共有 {len(smiles_in_smi)} 个SMILES出现在.smi文件中。")
print(f"共有 {len(smiles_not_in_smi)} 个SMILES没有出现在.smi文件中。")

print("\n没有出现在.smi文件中的SMILES：",flush=True)
for smile in smiles_not_in_smi:
    print(smile)

# Specify the file path
file_path = "/home/gaoyuchen/Molecular_generation/compare/smiles_not_in_smi.txt"

# Write the SMILES strings to a text file
with open(file_path, "w") as file:
    file.write("没有出现在.smi文件中的SMILES：\n")
    for smile in smiles_not_in_smi:
        file.write(smile + "\n")
