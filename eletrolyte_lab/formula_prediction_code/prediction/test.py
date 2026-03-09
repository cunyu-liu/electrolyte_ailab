import pandas as pd
import numpy as np
import pickle
from collections import defaultdict
from xgboost import XGBRegressor
from rdkit import Chem
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import GridSearchCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsRegressor
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import KFold
from sklearn.model_selection import GridSearchCV
from sklearn.neural_network import MLPRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.svm import SVR
from sklearn.metrics import make_scorer
from sklearn.neighbors import KNeighborsRegressor


class MolReprAccessor:
    def __init__(self, pkl_path):
        """
        初始化分子表示访问器
        
        Parameters:
        pkl_path (str): ckp_get_mol_repr.out.pkl 文件的路径
        """
        self.mol_repr_dict = {}
        self._load_pkl(pkl_path)
        
    def _load_pkl(self, pkl_path):
        """加载和处理pkl文件"""
        with open(pkl_path, 'rb') as f:
            predict = pickle.load(f)
            
        # 使用临时字典收集所有构象的表示
        temp_dict = defaultdict(list)
        
        # 处理每个batch
        for batch in predict:
            sz = batch["bsz"]
            for i in range(sz):
                smi = batch["data_name"][i]
                temp_dict[smi].append(batch["mol_repr_cls"][i])
        
        # 计算平均表示
        for smi, repr_list in temp_dict.items():
            self.mol_repr_dict[smi] = np.mean(repr_list, axis=0)

    def get_mol_repr(self, smiles):
        """
        获取指定SMILES的分子表示
        
        Parameters:
        smiles (str): 分子的SMILES字符串
        
        Returns:
        np.array: 分子的向量表示，如果不存在则返回None
        """
        return self.mol_repr_dict.get(smiles, None)

    def list_available_smiles(self):
        """
        列出所有可用的SMILES
        
        Returns:
        list: 所有可用的SMILES字符串列表
        """
        return list(self.mol_repr_dict.keys())

    def __contains__(self, smiles):
        """检查是否存在某个SMILES的表示"""
        return smiles in self.mol_repr_dict

# 使用示例
"""
# 初始化访问器
accessor = MolReprAccessor('path/to/ckp_get_mol_repr.out.pkl')

# 获取某个分子的表示
smiles = "你的SMILES字符串"
mol_repr = accessor.get_mol_repr(smiles)

if mol_repr is not None:
    print(f"分子表示维度: {mol_repr.shape}")
    print(f"分子表示: {mol_repr}")
"""

def replace_names_with_smiles(data, mol_info):
    """
    将分子名称替换为标准化后的SMILES。
    
    参数：
    data: pandas DataFrame，包含分子名称的列，如 'Salt1_name', 'Solvent1_name' 等。
    mol_info: pandas DataFrame，包含分子名称和对应的SMILES列。
    
    返回：
    pandas DataFrame，数据中分子名称被替换为标准化的SMILES。
    """
    # 创建一个字典，键为分子名称，值为标准化后的SMILES
    name_to_smiles = {}
    for _, row in mol_info.iterrows():
        name = row['Name']
        if pd.notnull(name):  # 忽略NaN值
            mol = Chem.MolFromSmiles(row['Smiles'])
            if mol:
                smi = Chem.MolToSmiles(mol)
                name_to_smiles[name] = smi

    # 定义一个替换函数，处理每个单元格
    def replace_with_smiles(cell):
        if pd.notnull(cell) and cell in name_to_smiles:
            return name_to_smiles[cell]
        return cell

    # 对所有包含名称的列进行替换
    name_cols = [
        'Salt1_name', 'Salt2_name', 'Salt3_name',
        'Solvent1_name', 'Solvent2_name', 'Solvent3_name',
        'Additive1_name', 'Additive2_name', 'Additive3_name'
    ]
    
    # 替换每一列的名称为SMILES
    for col in name_cols:
        if col in data.columns:
            data[col] = data[col].apply(replace_with_smiles)
    
    return data


def extract_feature_vectors(data, accessor):
    """
    提取特征向量并将其与目标值LCE合并。
    
    参数：
    data: pandas DataFrame，包含SMILES和MR列，以及目标值LCE。
    accessor: 用于获取分子表示的对象，应该具有`get_mol_repr`方法。
    
    返回：
    pandas DataFrame，包含特征向量和目标值LCE。
    """
    # 提取列名
    name_cols = ['Salt1_name','Salt2_name','Salt3_name',	
                 'Solvent1_name','Solvent2_name','Solvent3_name',	
                 'Additive1_name','Additive2_name','Additive3_name']
    mr_cols = ['Salt1_moles','Salt2_moles','Salt3_moles',	
               'Solvent1_moles','Solvent2_moles','Solvent3_moles',
               'Additive1_moles','Additive2_moles','Additive3_moles']

    # 收集特征向量
    feature_vectors = []
    for index, row in data.iterrows():
        # 获取SMILES和摩尔比列，去除NaN值
        smiles_list = row[name_cols].dropna().astype(str).tolist()
        mr_list = row[mr_cols].dropna().astype(float).tolist()

        # 如果没有有效的smiles，跳过该行
        if len(smiles_list) == 0:
            continue

        # 摩尔比归一化
        total_moles = sum(mr_list)
        if total_moles > 0:
            mr_list = [mole / total_moles for mole in mr_list]  # 归一化摩尔比

        feature_vector = np.zeros(512)  # 假设特征向量长度为512
        
        # 遍历每个有效的SMILES和摩尔比
        for smile, weight in zip(smiles_list, mr_list):
            try:
                # 获取分子表示，并按权重累加
                vector = accessor.get_mol_repr(smile)  # 使用accessor获取分子表示
                if vector is not None:  # 确保获取的vector有效
                    feature_vector += vector * weight
                else:
                    print(f"Invalid SMILES {smile}: Unable to generate molecular representation.")
            except Exception as e:
                # 记录错误或执行其他错误处理逻辑
                print(f"Error processing SMILES {smile}: {e}")
        
        feature_vectors.append(feature_vector)

    # 将特征向量与目标值LCE合并
    feature_df = pd.DataFrame(feature_vectors)
    result_df = pd.concat([feature_df, data[['LCE']]], axis=1)
    
    return result_df


# 实例化MolReprAccessor（确保ckp_get_mol_repr.out.pkl文件存在且格式正确）
accessor_train = MolReprAccessor('ckp_train.out.pkl')
accessor_prediction = MolReprAccessor('ckp_prediction.out.pkl')

# 加载数据
data=pd.read_excel('electrolyte.xlsx')
mol_info=pd.read_excel('mol_info.xlsx')
data=replace_names_with_smiles(data,mol_info)
data['LCE'] = -np.log10(100 - data['CE (%)'])

# 数据清洗
data=data[(data['Cycle number']<30) &
          (data['Cycle number']>5) &
          (data['CE (%)']>80) &
          (data['Current density']<=1) &
          (data['Capacity']<=1) ].reset_index(drop=True)

data=extract_feature_vectors(data,accessor_train).reset_index(drop=True)
feature=data.columns.to_list()
del feature[512]


# 定义所有模型的超参数网格
param_grids = {
    'MLP': {
        'hidden_layer_sizes': [(256,), (512,), (256, 128), (512, 256)],  # 减少层数,确保层大小合理递减
        'activation': ['relu'],  # relu通常最稳定
        'solver': ['adam'],  # adam通常收敛更好
        'alpha': [0.001, 0.01, 0.1],  # 增大正则化强度防止过拟合
        'learning_rate': ['adaptive'],  # 自适应学习率更稳定
        'max_iter': [500, 1000],  # 增加迭代次数确保收敛
        'early_stopping': [True],  # 启用早停
        'validation_fraction': [0.2]  # 设置验证集比例
    },
    
    'XGBoost': {
        'n_estimators': [100, 200],  # 增加树的数量提高稳定性
        'max_depth': [3, 4, 5],  # 限制树深度防止过拟合
        'learning_rate': [0.01, 0.05],  # 降低学习率
        'subsample': [0.7, 0.8],  # 子采样防止过拟合
        'colsample_bytree': [0.6, 0.7],  # 特征采样防止过拟合
        'gamma': [0.1, 0.2],  # 增加最小分裂增益阈值
        'min_child_weight': [3, 5],  # 添加最小子节点权重要求
        'reg_alpha': [0.1, 1],  # 添加L1正则化
        'reg_lambda': [1, 10]  # 添加L2正则化
    },
    
    'RandomForest': {
        'n_estimators': [200, 300],  # 增加树数量提高稳定性
        'max_depth': [5, 7],  # 限制深度
        'min_samples_split': [5, 10],  # 增加分裂所需样本数
        'min_samples_leaf': [3, 5],  # 增加叶节点最小样本数
        'max_features': ['sqrt', 'log2'],  # 特征选择策略
        'bootstrap': [True],  # 启用bootstrap
        'oob_score': [True]  # 启用袋外评估
    },
    
    'SVR': {
        'kernel': ['rbf'],  # 对高维数据,rbf核通常效果最好
        'C': [0.1, 1.0, 10.0],  # 正则化参数范围
        'gamma': ['scale', 'auto'],  # 自适应gamma
        'epsilon': [0.1, 0.2],  # 增大容许误差
        'shrinking': [True]  # 启用收缩启发式
    },
    
    'KNN': {
        'n_neighbors': [7, 11, 15],  # 增加邻居数提高稳定性
        'weights': ['distance'],  # 使用距离权重
        'algorithm': ['auto'],  # 自动选择最优算法
        'p': [2],  # 使用欧氏距离
        'leaf_size': [30, 50]  # 添加叶大小参数
    },
    
    'GradientBoosting': {
        'n_estimators': [200, 300],  # 增加树数量
        'max_depth': [3, 4],  # 限制深度
        'learning_rate': [0.01, 0.05],  # 降低学习率
        'min_samples_split': [5, 10],  # 增加分裂所需样本数
        'min_samples_leaf': [3, 5],  # 增加叶节点最小样本数
        'subsample': [0.7, 0.8],  # 添加子采样
        'max_features': ['sqrt', 'log2'],  # 特征选择策略
        'validation_fraction': [0.2]  # 设置验证集比例
    }
}


models = {
    'MLP': MLPRegressor(),
    'XGBoost': XGBRegressor(),
    'RandomForest': RandomForestRegressor(),
    'DecisionTree': DecisionTreeRegressor(),
    'SVR': SVR(),
    'KNN': KNeighborsRegressor(),
    'GradientBoosting': GradientBoostingRegressor()
}


# 自定义 RMSE 评分函数
def rmse(y_true, y_pred):
    return np.sqrt(np.mean((y_true - y_pred) ** 2))

# 将 RMSE 转换为 scorer 对象
rmse_scorer = make_scorer(rmse, greater_is_better=False)  # greater_is_better=False 表示越小越好

def grid_search_model(X_train, y_train, model, param_grid, cv=5):
    grid_search = GridSearchCV(
        estimator=model,
        param_grid=param_grid,
        cv=cv,
        scoring=rmse_scorer,  # 可以根据任务选择其他评分指标
        n_jobs=-1  # 使用所有可用的CPU核心
    )
    grid_search.fit(X_train, y_train)
    return grid_search.best_params_, grid_search.best_score_

# 假设你有训练数据 X_train 和 y_train
# 划分训练集和测试集
train_x, test_x, train_y, test_y = train_test_split(
    data[feature], data['LCE'], test_size=0.25, random_state=42
)
best_params = {}
best_scores = {}

for model_name, model in models.items():
    param_grid = param_grids[model_name]  # 从字典中获取超参数网格
    best_params[model_name], best_scores[model_name] = grid_search_model(train_x, train_y, model, param_grid)
    # print(f"Best parameters for {model_name}: {best_params[model_name]}")
    # print(f"Best score for {model_name}: {best_scores[model_name]}")

# 将结果转换为 DataFrame
results = []
for model_name in best_params.keys():
    results.append({
        'Model': model_name,
        'Best Parameters': str(best_params[model_name]),  # 将字典转换为字符串
        'Best RMSE': -best_scores[model_name]  # 如果评分是负的 MSE，取负值得到 RMSE
    })

results_df = pd.DataFrame(results)

# 保存到 CSV 文件
results_df.to_csv('best_model_results.csv', index=False)



