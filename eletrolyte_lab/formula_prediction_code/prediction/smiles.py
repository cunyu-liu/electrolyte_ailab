import os 
import pandas as pd
from rdkit import Chem

folder_path='D:\\2025\CE数据挖掘\\2014-2024\\analysis'
os.chdir(folder_path)

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

train_smi=pd.read_excel('data\\electrolyte_all\\mol_info_backup2.xlsx')
train_smi=standardize_smiles(train_smi,'Smiles')
prediction_smi=pd.read_excel('data\\hts\\4BindingEnergy.xlsx')

train_smi['standardized_Smiles'].to_csv('11.csv',index=False)
prediction_smi['SMILES'].to_csv('22.csv',index=False)