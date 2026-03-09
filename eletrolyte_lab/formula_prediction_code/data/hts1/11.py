import pandas as pd
import numpy as np
from rdkit import Chem

a=pd.read_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\hts1\\tsne.xlsx')
b=pd.read_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\hts1\\5no_ring.xlsx')
c=pd.read_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\hts1\\mol_info.xlsx')


def standardize_smiles(smiles):
    try:
        # 1. 解析 SMILES
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None  # 无效 SMILES
        
        # 2. 可选：移除手性信息、调整互变异构体等
        # 例如，移除手性标记：
        # Chem.RemoveStereochemistry(mol)
        
        # 3. 重新生成标准化的 SMILES（规范化）
        standardized_smiles = Chem.MolToSmiles(mol, canonical=True)
        return standardized_smiles
    except:
        return None  # 处理异常情况

# 应用标准化函数
c["SMILES"] = c["Smiles"].apply(standardize_smiles)



# Step 1: 如果 b 中的 SMILES 在 a 中，则 a["Category"] = 2
mask_b = a["SMILES"].isin(b["SMILES"])
a.loc[mask_b, "Category"] = 2

# Step 2: 如果 c 中的 SMILES 在 a 中，则 a["Category"] = 3（覆盖之前的 2）
mask_c = a["SMILES"].isin(c["SMILES"])
a.loc[mask_c, "Category"] = 3

# 查看结果
a.to_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\hts1\\tsne1.xlsx')