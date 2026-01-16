import pandas as pd
import os

# 读取原始CSV文件
original_file = '/Users/rocky/WorkSpace/TsingYu/Molecular_generation/codes/LUMO_1399_Eb_20250313.csv'
output_file = '/Users/rocky/WorkSpace/TsingYu/Molecular_generation/codes/LUMO_1399_Eb_with_index.csv'

# 读取CSV文件
df = pd.read_csv(original_file)

# 只保留EP ID和SMILES列
df_selected = df[['EP ID', 'SMILES']]

# 重置索引，并将索引作为新的一列
df_selected.reset_index(inplace=True)

# 重命名索引列为'Index'
df_selected.rename(columns={'index': 'Index'}, inplace=True)

# 调整列的顺序，使Index列在最前面
cols = df_selected.columns.tolist()
df_selected = df_selected[['Index', 'EP ID', 'SMILES']]

# 保存为新的CSV文件
df_selected.to_csv(output_file, index=False)

print(f'已创建新文件: {output_file}')
print(f'新文件包含 {len(df_selected)} 行数据')
