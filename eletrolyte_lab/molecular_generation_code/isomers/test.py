from rdkit import Chem

content = [
    "CC#N", "N#Cc1ccccc1", "N#CCC#N", "N#CCCC#N", "COC(C)C#N"
]

for smile in content:
    print(f"正在处理: {smile} ...")
    mol = Chem.MolFromSmiles(smile)

    # 原子
    for atom in mol.GetAtoms():
        print(f"原子索引: {atom.GetIdx()}") # 返回原子的索引（在分子中排序）
        print(f"原子符号: {atom.GetSymbol()}") # 返回原子的符号

    # 键
    for bond in mol.GetBonds():
        print(f"索引: {bond.GetBeginAtomIdx()}") # 返回键的第一个原子的索引。
        print(f"索引: {bond.GetEndAtomIdx()}") # 返回键的第一个原子的索引。 #TODO: ?
        print(f"边类型: {bond.GetBondType()}") # 返回边的类型 SINGLE（单键）、DOUBLE（双键）、TRIPLE（三键）、AROMATIC（芳香键）
    

    print("======================================================")

    