from rdkit import Chem
from rdkit.Chem import rdMolDescriptors

def smiles_to_formula(smiles):
    # 将 SMILES 转换为 RDKit 分子对象
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError("无效的 SMILES 字符串")
    
    # 使用 RDKit 计算分子式
    formula = rdMolDescriptors.CalcMolFormula(mol)
    return formula

# 示例 SMILES
smiles = "CCO"  # 乙醇
formula = smiles_to_formula(smiles)
print(f"SMILES: {smiles} -> 分子式: {formula}")