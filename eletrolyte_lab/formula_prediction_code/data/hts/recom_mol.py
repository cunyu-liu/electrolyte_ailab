import os
import pandas as pd
from rdkit import Chem
from rdkit.Chem import Draw
import matplotlib.pyplot as plt


mol=pd.read_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\hts\\5no_ring.xlsx')


# 2. 创建一个文件夹来保存分子图片
output_folder = 'molecule_images'
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# 3. 绘制并保存分子图片
for index, row in mol.iterrows():
    smiles = row['SMILES']
    name = row['EP ID']
    
    # 将 SMILES 转换为 RDKit 分子对象
    molecule = Chem.MolFromSmiles(smiles)
    
    if molecule is not None:
        # 绘制分子结构
        img = Draw.MolToImage(molecule, legend=f'{name}')
        
        # 保存图像
        img_path = os.path.join(output_folder, f'{name}.png')
        img.save(img_path)
        print(f'Saved: {img_path}')
    else:
        print(f'Failed to process SMILES: {smiles} for {name}')

print('All molecules have been processed.')