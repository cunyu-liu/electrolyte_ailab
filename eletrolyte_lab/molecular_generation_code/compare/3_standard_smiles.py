from rdkit import Chem
from rdkit.Chem import rdchem
from rdkit.Chem import AllChem

def standardize_smiles(input_file, output_file):
    """
    使用 RDKit 对输入文件中的 SMILES 进行标准化并保存到新文件。

    Args:
        input_file (str): 输入包含 SMILES 的文件路径。
        output_file (str): 输出标准化 SMILES 的文件路径。

    Returns:
        None
    """
    # 初始化计数器
    total_smiles = 0
    valid_smiles = 0
    invalid_smiles = 0

    # 打开输入文件和输出文件
    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line in infile:
            total_smiles += 1
            smiles = line.strip()  # 去掉行尾的换行符和多余空格

            try:
                # 使用 RDKit 解析 SMILES
                mol = Chem.MolFromSmiles(smiles)
                if mol:
                    # 将分子标准化为规范的 SMILES 格式
                    standardized_smiles = Chem.MolToSmiles(mol, canonical=True)
                    outfile.write(standardized_smiles + '\n')
                    valid_smiles += 1
                else:
                    raise ValueError("Invalid SMILES")
            except Exception as e:
                # 跳过无法解析的 SMILES
                invalid_smiles += 1
                print(f"无效的 SMILES: {smiles}，错误: {e}")

    # 打印统计信息
    print(f"总计处理了 {total_smiles} 条 SMILES")
    print(f"有效的 SMILES: {valid_smiles}")
    print(f"无效的 SMILES: {invalid_smiles}")

# 示例调用
if __name__ == "__main__":
    input_file = r"D:\merged_smiles.csv"
    output_file = r"D:\测试代码\cyc1.csv"
    standardize_smiles(input_file, output_file)
