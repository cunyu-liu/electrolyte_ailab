# import deepchem as dc
# from sklearn.manifold import TSNE
# import matplotlib.pyplot as plt
# import pandas as pd

# 示例 SMILES 列表（你可以替换为你自己的分子列表）
# smis = [
#     'CC',                  # Ethane
#     'CCC',                 # Propane
#     'CCCC',                # Butane
#     'CCO',                 # Ethanol
#     'CCCO',                # Propanol
#     'CC(=O)O',             # Acetic acid
#     'CC(=O)OC',            # Methyl acetate
#     'C1=CC=CC=C1',         # Benzene
#     'CCN(CC)CC',           # Triethylamine
#     'C1=CC=CC=C1O',        # Phenol
#     'C1=CC=C(C=C1)N',      # Aniline
#     'CC(=O)NC1=CC=CC=C1',  # Acetanilide
#     'CC(C)O',              # Isopropanol
#     'CC(C)C',              # Isobutane
#     'CC(C)(C)O',           # tert-Butanol
#     'C1=CC=C2C=CC=CC2=C1', # Naphthalene
#     'O=C(C)Oc1ccccc1C(=O)O', # Aspirin
#     'C1CNCCN1',            # Piperazine
#     'C1CCOC1',             # Tetrahydrofuran (THF)
#     'C1=CN=CN1',           # Imidazole
# ]

# ep_data=pd.read_excel('ep_data-20240313.xlsx')
# smis = ep_data['SMILES'].tolist()

# # 提取 Circular Fingerprint 特征
# featurizer = dc.feat.CircularFingerprint()
# fp = featurizer.featurize(smis)

# # 创建 DeepChem 数据集
# dataset = dc.data.NumpyDataset(fp)

# # 使用 t-SNE 降维
# X_tsne = TSNE(n_components=2, init='pca', perplexity=8, random_state=0).fit_transform(dataset.X)
# df = pd.DataFrame(X_tsne, columns=['t-SNE 1', 't-SNE 2'])
# df.to_excel('tsne.xlsx', index=False)

# # 绘图
# plt.figure(figsize=(6, 5))
# plt.scatter(X_tsne[:, 0], X_tsne[:, 1], s=100, alpha=0.7)
# plt.title('t-SNE of Circular Fingerprints')
# plt.xlabel('t-SNE 1')
# plt.ylabel('t-SNE 2')
# plt.grid(True)
# plt.show()


import pandas as pd
import deepchem as dc
from sklearn.manifold import TSNE
import numpy as np

# 1. 读取 SMILES 列表，清理空值、去空格
ep_data = pd.read_excel('ep_data-20240313.xlsx')
smis_raw = ep_data['SMILES'].dropna().astype(str).str.strip().tolist()

# 2. 检查哪些 SMILES 能够正常 featurize
featurizer = dc.feat.CircularFingerprint()
valid_smis = []
valid_fps = []

for s in smis_raw:
    try:
        fp = featurizer.featurize([s])[0]  # 单个处理
        if isinstance(fp, (np.ndarray, list)) and np.ndim(fp) == 1:
            valid_smis.append(s)
            valid_fps.append(fp)
        else:
            print(f'⚠️ 异常结构: {s}')
    except Exception as e:
        print(f'❌ 无法处理: {s}，原因: {e}')

# 3. 构建 DeepChem 数据集
dataset = dc.data.NumpyDataset(np.array(valid_fps))

# 4. 使用 t-SNE 降维
X_tsne = TSNE(n_components=2, init='pca', perplexity=8, random_state=0).fit_transform(dataset.X)

# 5. 保存降维结果
df = pd.DataFrame(X_tsne, columns=['t-SNE 1', 't-SNE 2'])
df['SMILES'] = valid_smis  # 可选：保存 SMILES 以便追踪
df.to_excel('tsne.xlsx', index=False)

print("✅ 降维完成，结果保存在 tsne.xlsx")
