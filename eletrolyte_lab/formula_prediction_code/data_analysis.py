import os 
import pandas as pd
import numpy as np
from rdkit import Chem
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
import seaborn as sns


folder_path='D:\\2025\CE数据挖掘\\2014-2024\\analysis'
os.chdir(folder_path)

def read_excel_file(file_path, sheet_name=None):
    """
    读取Excel文件并返回数据
    :param file_path: Excel文件路径
    :param sheet_name: 要读取的工作表名称，默认为None，表示读取所有工作表
    :return: 如果sheet_name为None，返回一个字典，键为工作表名称，值为对应的DataFrame；
             如果指定了sheet_name，返回对应的DataFrame。
    """
    try:
        if sheet_name:
            data = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            data = pd.read_excel(file_path, sheet_name=None)
        return data
    except Exception as e:
        print(f"读取文件时出错: {e}")
        return None

def standardize_smiles(df, smiles_col='Smiles'):
    """
    将输入的SMILES结构标准化
    
    参数:
    df (pandas.DataFrame): 包含SMILES数据的DataFrame
    smiles_col (str): SMILES列的列名，默认为'smiles'
    
    返回:
    pandas.DataFrame: 包含标准化SMILES的DataFrame
    """
    # 创建DataFrame的副本
    result_df = df.copy()
    
    # 直接在apply中进行转换
    result_df[f'standardized_{smiles_col}'] = result_df[smiles_col].apply(
        lambda x: Chem.MolToSmiles(Chem.MolFromSmiles(x)) 
        if Chem.MolFromSmiles(x) is not None else None
    )
    
    return result_df

def check_elements(mol):
    """检查分子是否有且只有C、H、O、F"""
    allowed_elements = set(['C', 'O', 'F'])
    
    elements_in_mol = {atom.GetSymbol() for atom in mol.GetAtoms()}
    
    # 检查分子中的元素是否正好与允许的元素集合之一匹配
    if elements_in_mol == allowed_elements:
        return True
    else:
        return False

def is_ether(mol):
    """检查分子中是否存在C-O-C醚键"""
    # 检查C-O-C键
    for bond in mol.GetBonds():
        if bond.GetBeginAtom().GetSymbol() == 'C' and bond.GetEndAtom().GetSymbol() == 'O':
            # 检查C-O-C键
            o_atom = bond.GetEndAtom()
            if len(o_atom.GetNeighbors()) == 2:
                if all(neighbor.GetSymbol() == 'C' for neighbor in o_atom.GetNeighbors()):
                    return True
        elif bond.GetBeginAtom().GetSymbol() == 'O' and bond.GetEndAtom().GetSymbol() == 'C':
            # 检查另一种方向
            o_atom = bond.GetBeginAtom()
            if len(o_atom.GetNeighbors()) == 2:
                if all(neighbor.GetSymbol() == 'C' for neighbor in o_atom.GetNeighbors()):
                    return True
    return False

def is_ester(mol):
    """检查分子中是否存在C=O双键"""
    for bond in mol.GetBonds():
        if bond.GetBeginAtom().GetSymbol() == 'C' and bond.GetEndAtom().GetSymbol() == 'O':
            # 检查键是否为双键
            if bond.GetBondTypeAsDouble() == 2.0:  # 双键的键类型为 2
                return True
        elif bond.GetBeginAtom().GetSymbol() == 'O' and bond.GetEndAtom().GetSymbol() == 'C':
            # 检查另一种方向
            if bond.GetBondTypeAsDouble() == 2.0:  # 双键的键类型为 2
                return True
    return False

def filter_dataframe(df, column_name, values):
    """
    根据指定列的多个值筛选DataFrame
    
    参数:
    df (pandas.DataFrame): 输入的DataFrame
    column_name (str): 要筛选的列名
    values: 要筛选的值，可以是单个值或值的列表/集合/元组
    
    返回:
    pandas.DataFrame: 筛选后的DataFrame
    """
    # 如果输入的是单个值，转换为列表
    if not isinstance(values, (list, tuple, set)):
        values = [values]
    
    # 使用isin进行多值筛选
    return df[df[column_name].isin(values)].reset_index(drop=True)

def check_mol(reference_df, query_df, ref_col, query_col, mode=0):
    """
    检查查询数据框中的元素与参考数据框的关系
    
    参数:
    reference_df (pd.DataFrame): 参考库
    query_df (pd.DataFrame): 待查询的DataFrame
    mode (int): 
        0: 检查query_df中哪些元素在reference_df中不存在
        1: 检查query_df中哪些元素在reference_df中存在
    
    返回:
    pd.DataFrame: 根据mode筛选后的DataFrame
    """
    
    # 将参考库转换为集合
    reference_set = set(reference_df[ref_col])
    
    if mode == 0:
        # 找出不在参考库中的元素
        result = query_df[~query_df[query_col].isin(reference_set)]
    elif mode == 1:
        # 找出在参考库中的元素
        result = query_df[query_df[query_col].isin(reference_set)]
    else:
        raise ValueError("mode参数必须为0或1")
    
    # 重置索引
    return result.reset_index(drop=True)

def filter_smiles_df(df):
    """
    根据SMILES列筛选pandas DataFrame
    
    参数:
    df (pandas.DataFrame): 包含SMILES列的DataFrame
    
    返回:
    pandas.DataFrame: 筛选后的DataFrame，只包含满足所有条件的行
    """
    # 创建一个掩码列表来存储每行是否满足所有条件
    mask = []
    
    # 遍历DataFrame中的每一行SMILES
    for smiles in df['SMILES']:

        try:
            # 将SMILES转换为RDKit分子对象
            mol = Chem.MolFromSmiles(smiles)

            if mol is None:
                mask.append(False)
                continue
              
            # 检查所有条件
            conditions_met = (
                check_elements(mol) and 
                is_ether(mol) and 
                not is_ester(mol)
            )
            
            mask.append(conditions_met)
            
        except:
            # 如果处理SMILES时出错，将该行标记为False
            mask.append(False)
        # print(mask)
    
    # 使用掩码筛选DataFrame
    return df[mask].copy()

def has_ring(smiles):
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is not None:
        # 获取分子中的环信息
        ring_info = molecule.GetRingInfo()
        # 如果环的数量大于 0，则存在环状结构
        return ring_info.NumRings() > 0
    return False  # 如果 SMILES 无效，默认返回 False



ep_data=read_excel_file('data\ep_data-20240313.xlsx',sheet_name='Sheet1')
mol_info=read_excel_file('data\electrolyte_all\mol_info_backup2.xlsx',sheet_name='Sheet1')

mol_info=standardize_smiles(mol_info,'Smiles')
mol_info_Fether=filter_dataframe(mol_info,'Solvent class','Fether')
mol_in_ep_data=filter_dataframe(ep_data,'SMILES',mol_info_Fether['standardized_Smiles'].to_list())

# 保存目标分子的结合能、LUMOHOM等性质
# mol_in_ep_data.to_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\hts\\target_mol.xlsx',index=False)

# missing_mol=check_elements(ep_data,mol_info_Fether,'SMILES','standardized_Smiles',mode=0)
# target_mol=check_elements(ep_data,mol_info_Fether,'SMILES','standardized_Smiles',mode=1)

ep_data_Fether=filter_smiles_df(ep_data)
# 保存ep数据库中氟化醚分子
ep_data_Fether.to_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\hts\\1Fether.xlsx',index=False)

ep_data_Fether=ep_data_Fether[(ep_data_Fether['Formation energy in solvent (eV/atom)']<0) &
                              (ep_data_Fether['Formation energy in vaccum (eV/atom)']<0) ]
# 保存ep数据库中形成能小于0的分子
ep_data_Fether.to_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\hts\\2FormationEnergy.xlsx',index=False)

ep_data_Fether=ep_data_Fether[(ep_data_Fether['LUMO_sol (eV)']>5.024309203) &
                              (ep_data_Fether['HOMO_sol (eV)']<-8.064636691) ]
# 保存ep数据库中LUMO在xx-xx、HOMO在xx-xx的分子
ep_data_Fether.to_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\hts\\3LUMOHOMO.xlsx',index=False)

ep_data_Fether=ep_data_Fether[(ep_data_Fether['Binding energy (eV)']<-0.420494734) &
                              (ep_data_Fether['Binding energy (eV)']>-0.979936217) ]
# 保存ep数据库中结合能在-xx的分子
ep_data_Fether.to_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\hts\\4BindingEnergy.xlsx',index=False)

# 应用函数，过滤掉包含环状结构的行
ep_data_Fether = ep_data_Fether[~ep_data_Fether['SMILES'].apply(has_ring)]
# 保存ep数据库中无环状结构的分子
ep_data_Fether.to_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\hts\\5no_ring.xlsx',index=False)















