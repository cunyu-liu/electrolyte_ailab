import os 
import pandas as pd
import numpy as np
import pubchempy as pcp
from rdkit import Chem
from rdkit.Chem import AllChem


folder_path='D:\\2025\CE数据挖掘\\2014-2024\\analysis'
os.chdir(folder_path)

data=pd.read_excel('data\\electrolyte_1\\electrolyte_1.xlsx')
# print(data)
molecule_columns=['Salt1_full name',	'Salt2_full name', 'Salt3_full name', 
               'Solvent1_full name', 'Solvent2_full name', 'Solvent3_full name', 
               'Additive1_full name', 'Additive2_full name', 'Additive3_full name']
molecule=data[molecule_columns]

def Extract_mol_csv(data, output_file='mol_info.csv'):

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
    # 7. 导出为CSV文件
    cleaned_df.to_csv(output_file, index=False)
    
    return cleaned_df

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

def get_compound_info(molecule, attributes=None):

    # 设置默认属性
    if attributes is None:
        attributes = ['smiles', 'weight', 'formula', 'name']
    # 获取化合物信息
    compounds = pcp.get_compounds(molecule, 'name')
    # 如果返回的化合物列表长度为1，提取信息
    if len(compounds) == 1:
        compound = compounds[0]
        # 根据所请求的属性提取相应的信息
        result = []
        if 'smiles' in attributes:
            result.append(compound.isomeric_smiles)
        if 'weight' in attributes:
            result.append(compound.molecular_weight)
        if 'formula' in attributes:
            result.append(compound.molecular_formula)
        if 'name' in attributes:
            result.append(compound.iupac_name)
        
        # 返回一个Series，包含所请求的属性
        return pd.Series(result)
    
    # 如果没有或有多个结果，返回NaN
    else:
        return pd.Series([None] * len(attributes))

def remove_duplicate_molecules(mol_info, output_file):
    # 先创建一个条件：如果'smiles', 'weight', 'formula', 'name'都为NaN时不去重
    condition = ~mol_info[['smiles', 'weight', 'formula', 'name']].isna().all(axis=1)
    # 过滤掉完全为NaN的行
    mol_info_filtered = mol_info[condition]
    # 根据 'smiles', 'weight', 'formula', 'name' 去重（只考虑非NaN行）
    mol_info_unique = mol_info_filtered.drop_duplicates(subset=['smiles', 'weight', 'formula', 'name'], keep='first')
    # 将去重后的结果与原始包含NaN的部分合并
    mol_info_result = pd.concat([mol_info_unique, mol_info[~condition]], ignore_index=True)
    # 输出到 Excel 文件
    mol_info_result.to_excel(output_file, index=False)
    
    return mol_info_result

# mol=Extract_mol_df(molecule)
# # print(mol)
# mol[['smiles', 'weight', 'formula', 'name']] = mol['molecule'].apply(lambda x: get_compound_info(x, attributes=None))
# mol.to_excel('data\\mol_info_1.xlsx',index=False)

# mol_info=pd.read_excel('data\\mol_info_1.xlsx')
# print(mol_info)


# # 创建一个字典，以 molecule 为键，name 为值（如果 name 非空）
# molecule_to_name = {row['molecule']: row['name'] for _, row in mol_info.dropna(subset=['name']).iterrows()}
# # 遍历这些列并进行替换
# for col in molecule_columns:
#     # 对该列中的每个值，检查是否在字典中，如果在则替换
#     data[col] = data[col].apply(lambda x: molecule_to_name.get(x, x) if pd.notna(x) else x)
# # print(data)
# data.to_excel('data\\electrolyte_1_standar.xlsx',index=False)

# mol_info=pd.read_excel('data\\mol_info_1.xlsx')
# remove_duplicate_molecules(mol_info, 'data\\mol_info_1_remove.xlsx')

# data=pd.read_excel('data\\electrolyte_1\\electrolyte_1_IUPACname.xlsx')
# mol_info=pd.read_excel('data\\electrolyte_1\\mol_info_1_remove.xlsx')

def calculate_molar_ratios1(data, mol_info):
    """
    Convert electrolyte composition to molar ratios for all cases
    
    Parameters:
    data: DataFrame containing electrolyte composition
    mol_info: DataFrame containing molecular information
    
    Returns:
    DataFrame with molar numbers for each component
    """
    def get_molecule_info(name, mol_info):
        """
        安全地获取分子信息，处理找不到匹配的情况
        """
        if pd.isna(name):
            return None
        
        matches = mol_info[mol_info['name'] == name]
        if len(matches) == 0:
            print(f"Warning: No molecular information found for {name}")
            return None
        return matches.iloc[0]

    def get_component_moles(row, mol_info):
        results = {}
        total_volume = 1.0  # L
        
        # 1. 处理盐的摩尔数
        total_salt_mass = 0
        for i in range(1, 4):
            salt_name = row[f'Salt{i}_full name']
            salt_conc = row[f'Concentration of Salt{i}']
            
            if pd.notna(salt_name) and pd.notna(salt_conc):
                salt_info = get_molecule_info(salt_name, mol_info)
                if salt_info is not None:
                    results[f'Salt{i}_moles'] = salt_conc
                    salt_mass = salt_conc * salt_info['weight']  # g/L
                    results[f'Salt{i}_mass'] = salt_mass
                    total_salt_mass += salt_mass
        
        # 2. 处理溶剂的摩尔数
        ratio_unit = row['Unit of ratio']
        solvent_ratios = []
        solvent_names = []
        solvent_infos = []
        
        # 收集所有非空的溶剂信息
        for i in range(1, 4):
            solvent_name = row[f'Solvent{i}_full name']
            solvent_ratio = row[f'Ratio of solvent{i}']
            
            if pd.notna(solvent_name):
                solvent_info = get_molecule_info(solvent_name, mol_info)
                if solvent_info is not None:
                    solvent_names.append(solvent_name)
                    solvent_infos.append(solvent_info)
                    solvent_ratios.append(solvent_ratio if pd.notna(solvent_ratio) else 1.0)
        
        # 根据不同情况处理溶剂
        total_solvent_mass = 0
        if len(solvent_names) == 0:
            print(f"Warning: No valid solvent found for row")
            return results
            
        if pd.isna(ratio_unit) or len(solvent_names) == 1:
            # 只有一种溶剂的情况
            solvent_mass = solvent_infos[0]['density'] * total_volume * 1000  # g
            results['Solvent1_moles'] = solvent_mass / solvent_infos[0]['weight']
            results['Solvent1_mass'] = solvent_mass
            total_solvent_mass = solvent_mass
            
        else:
            # 标准化比例
            ratios = np.array(solvent_ratios)
            normalized_ratios = ratios / np.sum(ratios)
            
            for idx, (solvent_name, ratio, solvent_info) in enumerate(zip(solvent_names, normalized_ratios, solvent_infos), 1):
                if ratio_unit == 'volume ratio':
                    # 体积比
                    solvent_volume = ratio * total_volume
                    solvent_mass = solvent_info['density'] * solvent_volume * 1000  # g
                    solvent_moles = solvent_mass / solvent_info['weight']
                    
                elif ratio_unit == 'mass ratio':
                    # 质量比，假设总质量为1kg
                    solvent_mass = ratio * 1000  # g
                    solvent_moles = solvent_mass / solvent_info['weight']
                    
                elif ratio_unit == 'molar ratio':
                    # 摩尔比，假设总摩尔数为1mol
                    solvent_moles = ratio * 1.0  # mol
                    solvent_mass = solvent_moles * solvent_info['weight']
                
                results[f'Solvent{idx}_moles'] = solvent_moles
                results[f'Solvent{idx}_mass'] = solvent_mass
                total_solvent_mass += solvent_mass
        
        # 3. 处理添加剂的摩尔数
        total_system_mass = total_salt_mass + total_solvent_mass
        
        for i in range(1, 4):
            additive_name = row[f'Additive{i}_full name']
            additive_content = row[f'Content of additive{i}']
            
            if pd.notna(additive_name) and pd.notna(additive_content):
                additive_info = get_molecule_info(additive_name, mol_info)
                if additive_info is not None:
                    content_unit = row['Unit of content']
                    
                    if content_unit == 'wt%':
                        # 质量百分比
                        additive_mass = (additive_content/100) * total_system_mass / (1 - additive_content/100)
                        results[f'Additive{i}_moles'] = additive_mass / additive_info['weight']
                    
                    elif content_unit == 'M':
                        # 摩尔浓度
                        results[f'Additive{i}_moles'] = additive_content
                    
                    elif content_unit == 'vol%':
                        # 体积百分比
                        additive_volume = (additive_content/100) * total_volume / (1 - additive_content/100)
                        additive_mass = additive_info['density'] * additive_volume * 1000  # g
                        results[f'Additive{i}_moles'] = additive_mass / additive_info['weight']
        
        return results

    # 处理所有数据
    results_data = []
    for idx, row in data.iterrows():
        try:
            result_row = get_component_moles(row, mol_info)
            results_data.append(result_row)
        except Exception as e:
            print(f"Error processing row {idx}: {str(e)}")
            results_data.append({})  # 添加空字典作为占位符
    
    return pd.DataFrame(results_data)

def calculate_molar_ratios2(data, mol_info):
    """
    Convert electrolyte composition to molar ratios for all cases
    
    Parameters:
    data: DataFrame containing electrolyte composition
    mol_info: DataFrame containing molecular information
    
    Returns:
    DataFrame with 18 columns containing moles and names of components
    """
    def get_molecule_info(name, mol_info):
        """
        安全地获取分子信息，处理找不到匹配的情况
        """
        if pd.isna(name):
            return None
        
        matches = mol_info[mol_info['Name'] == name]
        if len(matches) == 0:
            print(f"Warning: No molecular information found for {name}")
            return None
        return matches.iloc[0]

    def get_component_moles(row, mol_info):
        results = {
            # 初始化所有输出列为0或None
            'Salt1_moles': 0, 'Salt2_moles': 0, 'Salt3_moles': 0,
            'Solvent1_moles': 0, 'Solvent2_moles': 0, 'Solvent3_moles': 0,
            'Additive1_moles': 0, 'Additive2_moles': 0, 'Additive3_moles': 0,
            'Salt1_name': None, 'Salt2_name': None, 'Salt3_name': None,
            'Solvent1_name': None, 'Solvent2_name': None, 'Solvent3_name': None,
            'Additive1_name': None, 'Additive2_name': None, 'Additive3_name': None
        }
        
        total_volume = 1.0  # L
        total_salt_mass = 0
        
        # 1. 处理盐的摩尔数
        for i in range(1, 4):
            salt_name = row[f'Salt{i}_full name']
            salt_conc = row[f'Concentration of Salt{i}']
            
            if pd.notna(salt_name) and pd.notna(salt_conc):
                salt_info = get_molecule_info(salt_name, mol_info)
                if salt_info is not None:
                    results[f'Salt{i}_moles'] = salt_conc
                    results[f'Salt{i}_name'] = salt_info['name']
                    salt_mass = salt_conc * salt_info['weight']
                    total_salt_mass += salt_mass
        
        # 2. 处理溶剂的摩尔数
        ratio_unit = row['Unit of ratio']
        solvent_ratios = []
        solvent_names = []
        solvent_infos = []
        
        # 收集所有非空的溶剂信息
        for i in range(1, 4):
            solvent_name = row[f'Solvent{i}_full name']
            solvent_ratio = row[f'Ratio of solvent{i}']
            
            if pd.notna(solvent_name):
                solvent_info = get_molecule_info(solvent_name, mol_info)
                if solvent_info is not None:
                    solvent_names.append(solvent_name)
                    solvent_infos.append(solvent_info)
                    solvent_ratios.append(solvent_ratio if pd.notna(solvent_ratio) else 1.0)
                    results[f'Solvent{len(solvent_names)}_name'] = solvent_info['name']
        
        # 计算溶剂的摩尔数
        total_solvent_mass = 0
        if len(solvent_names) > 0:
            if pd.isna(ratio_unit) or len(solvent_names) == 1:
                # 单一溶剂
                solvent_mass = solvent_infos[0]['density'] * total_volume * 1000
                results['Solvent1_moles'] = solvent_mass / solvent_infos[0]['weight']
                total_solvent_mass = solvent_mass
            else:
                # 多种溶剂
                ratios = np.array(solvent_ratios)
                normalized_ratios = ratios / np.sum(ratios)
                for idx, (ratio, solvent_info) in enumerate(zip(normalized_ratios, solvent_infos), 1):
                    if ratio_unit == 'volume ratio':
                        # 体积比：直接用比例计算各溶剂的体积
                        solvent_volume = ratio * total_volume  # L
                        solvent_mass = solvent_info['density'] * solvent_volume * 1000  # g
                        solvent_moles = solvent_mass / solvent_info['weight']  # mol
                        
                    elif ratio_unit == 'mass ratio':
                        # 质量比：首先计算总体积对应的质量，然后按比例分配
                        # 1. 计算各溶剂的质量比例
                        # 2. 将1L总体积按质量比例分配给各溶剂
                        total_density = sum(s_info['density'] * r for s_info, r in zip(solvent_infos, normalized_ratios))
                        volume_fraction = (ratio * solvent_info['density']) / total_density
                        solvent_volume = volume_fraction * total_volume  # L
                        solvent_mass = solvent_info['density'] * solvent_volume * 1000  # g
                        solvent_moles = solvent_mass / solvent_info['weight']  # mol
                        
                    elif ratio_unit == 'molar ratio':
                        # 摩尔比：首先计算1L溶液中的总摩尔数，然后按比例分配
                        # 1. 计算各溶剂的摩尔比例
                        # 2. 将1L总体积按摩尔比例分配给各溶剂
                        total_molar_volume = sum(r / s_info['density'] * s_info['weight'] for s_info, r in zip(solvent_infos, normalized_ratios))
                        volume_fraction = (ratio / solvent_info['density'] * solvent_info['weight']) / total_molar_volume
                        solvent_volume = volume_fraction * total_volume  # L
                        solvent_mass = solvent_info['density'] * solvent_volume * 1000  # g
                        solvent_moles = solvent_mass / solvent_info['weight']  # mol
                    
                    results[f'Solvent{idx}_moles'] = solvent_moles
                    total_solvent_mass += solvent_mass
        
        # 3. 处理添加剂的摩尔数
        total_system_mass = total_salt_mass + total_solvent_mass
        
        for i in range(1, 4):
            additive_name = row[f'Additive{i}_full name']
            additive_content = row[f'Content of additive{i}']
            
            if pd.notna(additive_name) and pd.notna(additive_content):
                additive_info = get_molecule_info(additive_name, mol_info)
                if additive_info is not None:
                    results[f'Additive{i}_name'] = additive_info['name']
                    content_unit = row['Unit of content']
                    
                    if content_unit == 'wt%':
                        additive_mass = (additive_content/100) * total_system_mass
                        # additive_mass = (additive_content/100) * total_system_mass / (1 - additive_content/100)
                        results[f'Additive{i}_moles'] = additive_mass / additive_info['weight']
                    elif content_unit == 'M':
                        results[f'Additive{i}_moles'] = additive_content
                    elif content_unit == 'vol%':
                        additive_volume = (additive_content/100) * total_volume
                        # additive_volume = (additive_content/100) * total_volume / (1 - additive_content/100)
                        additive_mass = additive_info['density'] * additive_volume * 1000
                        results[f'Additive{i}_moles'] = additive_mass / additive_info['weight']
        
        return results

    # 处理所有数据
    results_data = []
    for idx, row in data.iterrows():
        try:
            result_row = get_component_moles(row, mol_info)
            results_data.append(result_row)
        except Exception as e:
            print(f"Error processing row {idx}: {str(e)}")
            # 创建一个包含所有必需列的空结果
            empty_result = {
                'Salt1_moles': 0, 'Salt2_moles': 0, 'Salt3_moles': 0,
                'Solvent1_moles': 0, 'Solvent2_moles': 0, 'Solvent3_moles': 0,
                'Additive1_moles': 0, 'Additive2_moles': 0, 'Additive3_moles': 0,
                'Salt1_name': None, 'Salt2_name': None, 'Salt3_name': None,
                'Solvent1_name': None, 'Solvent2_name': None, 'Solvent3_name': None,
                'Additive1_name': None, 'Additive2_name': None, 'Additive3_name': None
            }
            results_data.append(empty_result)
    
    # 创建结果DataFrame并确保列的顺序
    columns = [
        'Salt1_moles', 'Salt2_moles', 'Salt3_moles',
        'Solvent1_moles', 'Solvent2_moles', 'Solvent3_moles',
        'Additive1_moles', 'Additive2_moles', 'Additive3_moles',
        'Salt1_name', 'Salt2_name', 'Salt3_name',
        'Solvent1_name', 'Solvent2_name', 'Solvent3_name',
        'Additive1_name', 'Additive2_name', 'Additive3_name'
    ]
    
    return pd.DataFrame(results_data, columns=columns)

# haha=calculate_molar_ratios2(data,mol_info)
# haha.to_excel('data\\electrolyte_1\\molar_ratio_1.xlsx',index=False)


