import pandas as pd
from rdkit import Chem
from rdkit.Chem import Draw
import os

def generate_molecule_images(excel_file, output_folder='molecule_images'):
    """
    从Excel文件中读取分子SMILES并生成2D结构图
    
    参数:
    excel_file (str): Excel文件路径
    output_folder (str): 输出图片的文件夹路径
    
    返回:
    int: 成功生成的图片数量
    """
    # 创建输出文件夹（如果不存在）
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # 读取Excel文件
    df = pd.read_excel(excel_file)
    
    # 检查必要的列是否存在
    required_columns = ['Smiles', 'Index']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Excel文件中缺少'{col}'列")
    
    count_success = 0
    count_error = 0
    error_indices = []
    
    # 遍历每一行
    for i, row in df.iterrows():
        smiles = row['Smiles']
        index = row['Index']
        
        try:
            # 将SMILES转换为RDKit分子对象
            mol = Chem.MolFromSmiles(smiles)
            
            if mol is None:
                count_error += 1
                error_indices.append(index)
                continue
            
            # 生成2D图像并保存
            img = Draw.MolToImage(mol, size=(300, 300))
            image_path = os.path.join(output_folder, f"{index}.png")
            img.save(image_path)
            
            count_success += 1
            
        except Exception as e:
            print(f"处理分子(索引:{index})时出错: {e}")
            count_error += 1
            error_indices.append(index)
    
    # 打印结果摘要
    print(f"成功生成: {count_success}个分子图像")
    if count_error > 0:
        print(f"失败: {count_error}个分子")
        print(f"失败的索引: {error_indices}")
    
    return count_success

# 使用示例
if __name__ == "__main__":
    excel_file = "D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\electrolyte_all\\mol_info_backup2.xlsx"  # 替换为你的Excel文件路径
    output_folder='D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\electrolyte_all\\molecule_images'
    num_generated = generate_molecule_images(excel_file,output_folder)
    print(f"总共生成了{num_generated}个分子图像")