import pandas as pd

# 读取CSV文件
file_path = '/home/gaoyuchen/Molecular_generation/compare/3_ep_data_clean_20241222_filled.csv'  # 替换为你的CSV文件路径
data = pd.read_csv(file_path)

# 打印基本信息
print("数据的基本信息：")
print(data.info())  # 打印数据的结构信息

# 打印前几行数据
print("\n数据的前五行：")
print(data.head())

# 打印数据的统计信息
print("\n数据的统计描述：")
print(data.describe())
