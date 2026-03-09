import os
import pandas as pd
from rdkit import Chem

folder_path ='D:\\2025\CE数据挖掘\\2014-2024\\analysis\prediction'
os.chdir(folder_path)

electrolyte=pd.read_excel('data\\electrolyte.xlsx')
mol_info=pd.read_excel('data\\mol_info.xlsx')
# print(electrolyte['Salt3_name'])

name_cols = ['Salt1_name', 'Salt2_name', 'Salt3_name', 'Solvent1_name', 'Solvent2_name', 'Solvent3_name', 
             'Additive1_name', 'Additive2_name', 'Additive3_name']
mr_cols = ['Salt1_moles', 'Salt2_moles', 'Salt3_moles', 'Solvent1_moles', 'Solvent2_moles', 'Solvent3_moles',
           'Additive1_moles', 'Additive2_moles', 'Additive3_moles']




