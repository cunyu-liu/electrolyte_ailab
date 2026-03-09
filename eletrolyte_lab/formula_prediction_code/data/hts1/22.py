import pandas as pd
import numpy as np
import seaborn as sns
from scipy.stats import gaussian_kde

df=pd.read_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\hts1\\ep_data-20240313.xlsx')
df=df[['Binding energy (eV)', 'LUMO_sol (eV)', 'HOMO_sol (eV)']]

# # 设置统一的风格
# sns.set(style="whitegrid", font_scale=1.2)

# # 逐列绘图
# for col in a:
#     plt.figure(figsize=(6, 4))
    
#     # 可选：clip 去除极端值（也可以不加）
#     data_clip = a[col].clip(lower=a[col].quantile(0.01), upper=a[col].quantile(0.99))
    
#     sns.kdeplot(data_clip, fill=True, linewidth=2, color="steelblue")
#     plt.title(f'KDE Distribution of {col}')
#     plt.xlabel(col)
#     plt.ylabel('Density')
#     plt.grid(True)
#     plt.tight_layout()
#     plt.show()


# 清洗列名
# df.columns = df.columns.str.strip()
columns = ["Binding energy (eV)", "LUMO_sol (eV)", "HOMO_sol (eV)"]

# 创建一个字典用于存储每列的KDE数据
kde_data_dict = {}

# KDE 分布估计与采样
for col in columns:
    # 去除 NaN 和极端值（可选）
    data = df[col].dropna()
    data_clip = data.clip(lower=data.quantile(0.01), upper=data.quantile(0.99))

    # 拟合 KDE
    kde = gaussian_kde(data_clip)

    # 设置 x 范围（略宽于数据范围）
    x_grid = np.linspace(data_clip.min() - 1, data_clip.max() + 1, 500)
    y_grid = kde(x_grid)

    # 保存到 dict 中
    kde_data_dict[f"{col}_x"] = x_grid
    kde_data_dict[f"{col}_y"] = y_grid

# 转换为 DataFrame 并导出为 Excel
kde_df = pd.DataFrame(kde_data_dict)
kde_df.to_excel("kde_distribution_data.xlsx", index=False)


