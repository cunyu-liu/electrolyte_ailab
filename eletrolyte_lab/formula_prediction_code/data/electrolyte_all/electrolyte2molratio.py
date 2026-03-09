import pandas as pd
import numpy as np

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
                    results[f'Salt{i}_name'] = salt_info['Name']
                    salt_mass = salt_conc * salt_info['Weight']
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
                    results[f'Solvent{len(solvent_names)}_name'] = solvent_info['Name']
        
        # 计算溶剂的摩尔数
        total_solvent_mass = 0
        if len(solvent_names) > 0:
            if pd.isna(ratio_unit) or len(solvent_names) == 1:
                # 单一溶剂
                solvent_mass = solvent_infos[0]['Density'] * total_volume * 1000
                results['Solvent1_moles'] = solvent_mass / solvent_infos[0]['Weight']
                total_solvent_mass = solvent_mass
            else:
                # 多种溶剂
                ratios = np.array(solvent_ratios)
                normalized_ratios = ratios / np.sum(ratios)
                for idx, (ratio, solvent_info) in enumerate(zip(normalized_ratios, solvent_infos), 1):
                    if ratio_unit == 'volume ratio':
                        # 体积比：直接用比例计算各溶剂的体积
                        solvent_volume = ratio * total_volume  # L
                        solvent_mass = solvent_info['Density'] * solvent_volume * 1000  # g
                        solvent_moles = solvent_mass / solvent_info['Weight']  # mol
                        
                    elif ratio_unit == 'mass ratio':
                        # 质量比：首先计算总体积对应的质量，然后按比例分配
                        # 1. 计算各溶剂的质量比例
                        # 2. 将1L总体积按质量比例分配给各溶剂
                        total_density = sum(s_info['Density'] * r for s_info, r in zip(solvent_infos, normalized_ratios))
                        volume_fraction = (ratio * solvent_info['Density']) / total_density
                        solvent_volume = volume_fraction * total_volume  # L
                        solvent_mass = solvent_info['Density'] * solvent_volume * 1000  # g
                        solvent_moles = solvent_mass / solvent_info['Weight']  # mol
                        
                    elif ratio_unit == 'molar ratio':
                        # 摩尔比：首先计算1L溶液中的总摩尔数，然后按比例分配
                        # 1. 计算各溶剂的摩尔比例
                        # 2. 将1L总体积按摩尔比例分配给各溶剂
                        total_molar_volume = sum(r / s_info['Density'] * s_info['Weight'] for s_info, r in zip(solvent_infos, normalized_ratios))
                        volume_fraction = (ratio / solvent_info['Density'] * solvent_info['Weight']) / total_molar_volume
                        solvent_volume = volume_fraction * total_volume  # L
                        solvent_mass = solvent_info['Density'] * solvent_volume * 1000  # g
                        solvent_moles = solvent_mass / solvent_info['Weight']  # mol
                    
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
                    results[f'Additive{i}_name'] = additive_info['Name']
                    content_unit = row['Unit of content']
                    
                    if content_unit == 'wt%':
                        additive_mass = (additive_content/100) * total_system_mass
                        # additive_mass = (additive_content/100) * total_system_mass / (1 - additive_content/100)
                        results[f'Additive{i}_moles'] = additive_mass / additive_info['Weight']
                    elif content_unit == 'M':
                        results[f'Additive{i}_moles'] = additive_content
                    elif content_unit == 'vol%':
                        additive_volume = (additive_content/100) * total_volume
                        # additive_volume = (additive_content/100) * total_volume / (1 - additive_content/100)
                        additive_mass = additive_info['Density'] * additive_volume * 1000
                        results[f'Additive{i}_moles'] = additive_mass / additive_info['Weight']
        
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

data=pd.read_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\electrolyte_all\\electrolyte_all_backup4.xlsx')
mol_info=pd.read_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\electrolyte_all\\mol_info_backup2.xlsx')

mol_ratio=calculate_molar_ratios2(data,mol_info)
mol_ratio.to_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\electrolyte_all\\mol_ratio.xlsx',index=False)
