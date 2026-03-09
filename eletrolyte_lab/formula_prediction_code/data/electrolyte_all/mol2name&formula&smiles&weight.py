import pandas as pd
import numpy as np
import pubchempy as pcp

def Extract_mol_df(data):

    # 1. 合并所有列为一列
    all_values = pd.concat([data[col] for col in data.columns], ignore_index=True)
    # 2. 转换为DataFrame
    combined_df = pd.DataFrame(all_values, columns=['molecule'])
    # 3. 删除所有包含NaN的行
    cleaned_df = combined_df.dropna()
    # 4. 删除重复值
    cleaned_df = cleaned_df.drop_duplicates()
    # 5. 排序
    cleaned_df = cleaned_df.sort_values(by='molecule')
    # 6. 重置索引
    cleaned_df = cleaned_df.reset_index(drop=True)
    # 7. 转换为列表并返回
    molecule_list = cleaned_df['molecule'].tolist()
    
    return cleaned_df

def get_mol_info(molecule, attributes=None):

    # 设置默认属性
    if attributes is None:
        attributes = ['Name','Formula','Smiles','Weight']
    # 获取化合物信息
    compounds = pcp.get_compounds(molecule, 'name')
    # 如果返回的化合物列表长度为1，提取信息
    if len(compounds) == 1:
        compound = compounds[0]
        # 根据所请求的属性提取相应的信息
        result = []
        if 'Name' in attributes:
            result.append(compound.iupac_name)
        if 'Formula' in attributes:
            result.append(compound.molecular_formula)
        if 'Smiles' in attributes:
            result.append(compound.isomeric_smiles)
        if 'Weight' in attributes:
            result.append(compound.molecular_weight)
        
        # 返回一个Series，包含所请求的属性
        return pd.Series(result)
    
    # 如果没有或有多个结果，返回NaN
    else:
        return pd.Series([None] * len(attributes))

def remove_duplicate_mol(mol_info, output_file):
    # 先创建一个条件：如果'smiles', 'weight', 'formula', 'name'都为NaN时不去重
    condition = ~mol_info[['Name', 'Formula', 'Smiles', 'Weight']].isna().all(axis=1)
    # 过滤掉完全为NaN的行
    mol_info_filtered = mol_info[condition]
    # 根据 'smiles', 'weight', 'formula', 'name' 去重（只考虑非NaN行）
    mol_info_unique = mol_info_filtered.drop_duplicates(subset=['Name', 'Formula', 'Smiles', 'Weight'], keep='first')
    # 将去重后的结果与原始包含NaN的部分合并
    mol_info_result = pd.concat([mol_info_unique, mol_info[~condition]], ignore_index=True)
    # 输出到 Excel 文件
    mol_info_result.to_excel(output_file, index=False)
    
    return mol_info_result

data=pd.read_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\electrolyte_all\electrolyte_all.xlsx')
# print(data)
mol_columns=['Salt1_full name',	'Salt2_full name', 'Salt3_full name', 
               'Solvent1_full name', 'Solvent2_full name', 'Solvent3_full name', 
               'Additive1_full name', 'Additive2_full name', 'Additive3_full name']
mol=data[mol_columns]
# print(mol)
mol=Extract_mol_df(mol)
# print(mol)
# mol[['Name','Formula','Smiles', 'Weight']] = mol['molecule'].apply(lambda x: get_mol_info(x, attributes=None))
# mol.to_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\electrolyte_all\\mol_info.xlsx',index=False)


# mol_info=pd.read_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\electrolyte_all\mol_info_backup1.xlsx')
# print(mol_info)
# 创建一个字典，以 molecule 为键，name 为值（如果 name 非空）
# molecule_to_name = {row['molecule']: row['Name'] for _, row in mol_info.dropna(subset=['Name']).iterrows()}
# 遍历这些列并进行替换
# for col in mol_columns:
#     # 对该列中的每个值，检查是否在字典中，如果在则替换
#     data[col] = data[col].apply(lambda x: molecule_to_name.get(x, x) if pd.notna(x) else x)
# print(data)
# data.to_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\electrolyte_all\\electrolyte_1_standar.xlsx',index=False)

mol_info=pd.read_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\electrolyte_all\\mol_info_backup1.xlsx')
remove_duplicate_mol(mol_info, 'D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\electrolyte_all\\mol_info_1_remove.xlsx')