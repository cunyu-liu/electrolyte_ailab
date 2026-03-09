import pandas as pd
import numpy as np
import os
import pickle
import numpy as np
from collections import defaultdict
import xgboost as xgb
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import GridSearchCV
import matplotlib.pyplot as plt
from rdkit import Chem
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsRegressor
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import KFold


folder_path ='D:\\2025\CE数据挖掘\\2014-2024\\analysis\prediction'
os.chdir(folder_path)


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


def extract_feature_vectors_for_prediction(data, accessor1, accessor2):
    """
    提取特征向量用于预测数据。
    
    参数：
    data: pandas DataFrame，包含SMILES和MR列。
    accessor1: 第一个用于获取分子表示的对象，应该具有`get_mol_repr`方法。
    accessor2: 第二个用于获取分子表示的对象，应该具有`get_mol_repr`方法。
    
    返回：
    pandas DataFrame，包含特征向量。
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
                # 先尝试使用accessor1获取分子表示
                vector = accessor1.get_mol_repr(smile)
                if vector is None:
                    # 如果accessor1返回None，则尝试使用accessor2
                    vector = accessor2.get_mol_repr(smile)
                
                if vector is not None:  # 确保获取的vector有效
                    feature_vector += vector * weight
                else:
                    print(f"Invalid SMILES {smile}: Unable to generate molecular representation with both accessors.")
            except Exception as e:
                # 记录错误或执行其他错误处理逻辑
                print(f"Error processing SMILES {smile}: {e}")
        
        feature_vectors.append(feature_vector)

    # 将特征向量转换为DataFrame
    feature_df = pd.DataFrame(feature_vectors)
    
    return feature_df


def plot_predictions_vs_true(train_pred, train_y, test_pred, test_y, save_path):
    """
    绘制训练集和测试集的预测值与真实值之间的散点图

    参数：
    train_pred : array-like
        训练集预测值
    train_y : array-like
        训练集真实值
    test_pred : array-like
        测试集预测值
    test_y : array-like
        测试集真实值
    """
    # 创建图形
    plt.figure(figsize=(8, 6))
    # 绘制训练集的散点图
    plt.scatter(train_y, train_pred, color='blue', alpha=0.6, label='Train Data', edgecolors='k')
    # 绘制测试集的散点图
    plt.scatter(test_y, test_pred, color='red', alpha=0.6, label='Test Data', edgecolors='k')
    # 添加标题和坐标轴标签
    plt.title('Xgboost',fontsize=18)
    plt.xlabel('True Values',fontsize=18)
    plt.ylabel('Predictions',fontsize=18)
    # 设置坐标轴范围
    plt.xlim(0.4, 2.8)  # 横坐标范围0.4-2.8
    plt.ylim(0.4, 2.8)  # 纵坐标范围
    # 显示图例
    plt.legend(fontsize=18)
    # 调整坐标轴刻度的字体大小
    plt.tick_params(axis='both', labelsize=16)  # 'both' 表示同时调整x和y轴的刻度标签大小
    # 保存图片
    plt.savefig(save_path)
    # 关闭图形
    plt.close()
    # print(f"图表已保存到 {save_path}")

# save_path='picture\\Xgboost.png'
# plot_predictions_vs_true(train_pred, train_y, test_pred, test_y,save_path)

def mlp(data, feature, target_column='LCE', test_size=0.25, random_state=42, cv_folds=5, predict_data=None):
    # 划分训练集和测试集
    train_x, test_x, train_y, test_y = train_test_split(
        data[feature], data[target_column], test_size=test_size, random_state=random_state
    )
    
    # 创建MLP回归模型
    mlp = MLPRegressor(hidden_layer_sizes=[256], activation='tanh', solver='adam', alpha=0.1,
                       max_iter=1000, random_state=random_state)

    # 使用交叉验证进行训练
    kf = KFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    cross_val_rmse = []

    # 对每一折进行训练与验证
    for train_index, val_index in kf.split(train_x):
        # 获取训练集和验证集
        X_train, X_val = train_x.iloc[train_index], train_x.iloc[val_index]
        y_train, y_val = train_y.iloc[train_index], train_y.iloc[val_index]
        
        # 训练模型
        mlp.fit(X_train, y_train)
        
        # 预测验证集
        val_pred = mlp.predict(X_val)
        
        # 计算验证集RMSE
        val_rmse = np.sqrt(mean_squared_error(y_val, val_pred))
        cross_val_rmse.append(val_rmse)
    
    # 计算五折交叉验证的平均RMSE
    avg_cross_val_rmse = np.mean(cross_val_rmse)

    # 在全训练集上训练并预测
    mlp.fit(train_x, train_y)
    train_pred = mlp.predict(train_x)
    test_pred = mlp.predict(test_x)
    
    # 计算训练集和测试集的RMSE
    train_rmse = np.sqrt(mean_squared_error(train_y, train_pred))
    test_rmse = np.sqrt(mean_squared_error(test_y, test_pred))
    
    # 如果有预测数据，进行预测
    LCE_pre = None
    if predict_data is not None:
        LCE_pre = mlp.predict(predict_data)
    
    return train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse, train_y, train_pred, test_y, test_pred, LCE_pre


def xgboost(data, feature, target_column='LCE', test_size=0.25, random_state=42, cv_folds=5, predict_data=None):
    # 划分训练集和测试集
    train_x, test_x, train_y, test_y = train_test_split(
        data[feature], data[target_column], test_size=test_size, random_state=random_state
    )

    # 创建XGBoost回归模型
    xg_reg = xgb.XGBRegressor(
        objective='reg:squarederror', 
        eval_metric='rmse', 
        random_state=random_state,
        max_depth=5,
        min_child_weight=10,
        n_estimators=20, 
        eta=0.5,
        gamma=0.5,
        learning_rate=0.1,
        reg_alpha=0.1,  
        reg_lambda=0.1
    )

    # 使用交叉验证进行训练
    kf = KFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    cross_val_rmse = []

    # 对每一折进行训练与验证
    for train_index, val_index in kf.split(train_x):
        # 获取训练集和验证集
        X_train, X_val = train_x.iloc[train_index], train_x.iloc[val_index]
        y_train, y_val = train_y.iloc[train_index], train_y.iloc[val_index]
        
        # 训练模型
        xg_reg.fit(X_train, y_train)
        
        # 预测验证集
        val_pred = xg_reg.predict(X_val)
        
        # 计算验证集RMSE
        val_rmse = np.sqrt(mean_squared_error(y_val, val_pred))
        cross_val_rmse.append(val_rmse)
    
    # 计算五折交叉验证的平均RMSE
    avg_cross_val_rmse = np.mean(cross_val_rmse)

    # 在全训练集上训练并预测
    xg_reg.fit(train_x, train_y)
    train_pred = xg_reg.predict(train_x)
    test_pred = xg_reg.predict(test_x)
    
    # 计算训练集和测试集的RMSE
    train_rmse = np.sqrt(mean_squared_error(train_y, train_pred))
    test_rmse = np.sqrt(mean_squared_error(test_y, test_pred))

    # 如果有预测数据，进行预测
    LCE_pre = None
    if predict_data is not None:
        LCE_pre = xg_reg.predict(predict_data)
    
    return train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse, train_y, train_pred, test_y, test_pred, LCE_pre


def random_forest(data, feature, target_column='LCE', test_size=0.25, random_state=42, cv_folds=5, predict_data=None):
    """
    随机森林回归模型，支持训练、验证和预测。
    
    参数：
    data: pandas DataFrame，包含特征和目标值。
    feature: list，特征列名。
    target_column: str，目标值列名，默认为 'LCE'。
    test_size: float，测试集比例，默认为 0.25。
    random_state: int，随机种子，默认为 42。
    cv_folds: int，交叉验证折数，默认为 5。
    predict_data: pandas DataFrame，用于预测的数据，包含 512 个特征。
    
    返回：
    train_rmse: float，训练集 RMSE。
    test_rmse: float，测试集 RMSE。
    cross_val_rmse: list，交叉验证每折的 RMSE。
    avg_cross_val_rmse: float，交叉验证平均 RMSE。
    train_y: array，训练集真实值。
    train_pred: array，训练集预测值。
    test_y: array，测试集真实值。
    test_pred: array，测试集预测值。
    LCE_pre: array，预测数据的预测结果（如果 predict_data 不为 None）。
    """
    # 划分训练集和测试集
    train_x, test_x, train_y, test_y = train_test_split(
        data[feature], data[target_column], test_size=test_size, random_state=random_state
    )
    
    # 创建随机森林回归模型
    rf = RandomForestRegressor(n_estimators=60, 
                               max_depth=5,
                               random_state=random_state)

    # 使用交叉验证进行训练
    kf = KFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    cross_val_rmse = []

    # 对每一折进行训练与验证
    for train_index, val_index in kf.split(train_x):
        # 获取训练集和验证集
        X_train, X_val = train_x.iloc[train_index], train_x.iloc[val_index]
        y_train, y_val = train_y.iloc[train_index], train_y.iloc[val_index]
        
        # 训练模型
        rf.fit(X_train, y_train)
        
        # 预测验证集
        val_pred = rf.predict(X_val)
        
        # 计算验证集 RMSE
        val_rmse = np.sqrt(mean_squared_error(y_val, val_pred))
        cross_val_rmse.append(val_rmse)
    
    # 计算五折交叉验证的平均 RMSE
    avg_cross_val_rmse = np.mean(cross_val_rmse)

    # 在全训练集上训练并预测
    rf.fit(train_x, train_y)
    train_pred = rf.predict(train_x)
    test_pred = rf.predict(test_x)
    
    # 计算训练集和测试集的 RMSE
    train_rmse = np.sqrt(mean_squared_error(train_y, train_pred))
    test_rmse = np.sqrt(mean_squared_error(test_y, test_pred))

    # 如果有预测数据，进行预测
    LCE_pre = None
    if predict_data is not None:
        LCE_pre = rf.predict(predict_data)

    return train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse, train_y, train_pred, test_y, test_pred, LCE_pre


def decision_tree(data, feature, target_column='LCE', test_size=0.25, random_state=42, cv_folds=5):
    # 划分训练集和测试集
    train_x, test_x, train_y, test_y = train_test_split(
        data[feature], data[target_column], test_size=test_size, random_state=random_state
    )
    
    # 创建决策树回归模型
    dt = DecisionTreeRegressor(max_depth=5, random_state=random_state)

    # 使用交叉验证进行训练
    kf = KFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    cross_val_rmse = []

    # 对每一折进行训练与验证
    for train_index, val_index in kf.split(train_x):
        # 获取训练集和验证集
        X_train, X_val = train_x.iloc[train_index], train_x.iloc[val_index]
        y_train, y_val = train_y.iloc[train_index], train_y.iloc[val_index]
        
        # 训练模型
        dt.fit(X_train, y_train)
        
        # 预测验证集
        val_pred = dt.predict(X_val)
        
        # 计算验证集RMSE
        val_rmse = np.sqrt(mean_squared_error(y_val, val_pred))
        cross_val_rmse.append(val_rmse)
    
    # 计算五折交叉验证的平均RMSE
    avg_cross_val_rmse = np.mean(cross_val_rmse)

    # 在全训练集上训练并预测
    dt.fit(train_x, train_y)
    train_pred = dt.predict(train_x)
    test_pred = dt.predict(test_x)
    
    # 计算训练集和测试集的RMSE
    train_rmse = np.sqrt(mean_squared_error(train_y, train_pred))
    test_rmse = np.sqrt(mean_squared_error(test_y, test_pred))

    return train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse, train_y, train_pred, test_y, test_pred


def svm_regression(data, feature, target_column='LCE', test_size=0.25, random_state=42, cv_folds=5):
    # 划分训练集和测试集
    train_x, test_x, train_y, test_y = train_test_split(
        data[feature], data[target_column], test_size=test_size, random_state=random_state
    )
    
    # 创建SVM回归模型
    svm = SVR(kernel='poly')

    # 使用交叉验证进行训练
    kf = KFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    cross_val_rmse = []

    # 对每一折进行训练与验证
    for train_index, val_index in kf.split(train_x):
        # 获取训练集和验证集
        X_train, X_val = train_x.iloc[train_index], train_x.iloc[val_index]
        y_train, y_val = train_y.iloc[train_index], train_y.iloc[val_index]
        
        # 训练模型
        svm.fit(X_train, y_train)
        
        # 预测验证集
        val_pred = svm.predict(X_val)
        
        # 计算验证集RMSE
        val_rmse = np.sqrt(mean_squared_error(y_val, val_pred))
        cross_val_rmse.append(val_rmse)
    
    # 计算五折交叉验证的平均RMSE
    avg_cross_val_rmse = np.mean(cross_val_rmse)

    # 在全训练集上训练并预测
    svm.fit(train_x, train_y)
    train_pred = svm.predict(train_x)
    test_pred = svm.predict(test_x)
    
    # 计算训练集和测试集的RMSE
    train_rmse = np.sqrt(mean_squared_error(train_y, train_pred))
    test_rmse = np.sqrt(mean_squared_error(test_y, test_pred))

    return train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse, train_y, train_pred, test_y, test_pred


def knn_regression(data, feature, target_column='LCE', test_size=0.25, random_state=42, cv_folds=5):
    # 划分训练集和测试集
    train_x, test_x, train_y, test_y = train_test_split(
        data[feature], data[target_column], test_size=test_size, random_state=random_state
    )
    
    # 创建KNN回归模型
    knn = KNeighborsRegressor(n_neighbors=5, weights='uniform')

    # 使用交叉验证进行训练
    kf = KFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    cross_val_rmse = []

    # 对每一折进行训练与验证
    for train_index, val_index in kf.split(train_x):
        # 获取训练集和验证集
        X_train, X_val = train_x.iloc[train_index], train_x.iloc[val_index]
        y_train, y_val = train_y.iloc[train_index], train_y.iloc[val_index]
        
        # 训练模型
        knn.fit(X_train, y_train)
        
        # 预测验证集
        val_pred = knn.predict(X_val)
        
        # 计算验证集RMSE
        val_rmse = np.sqrt(mean_squared_error(y_val, val_pred))
        cross_val_rmse.append(val_rmse)
    
    # 计算五折交叉验证的平均RMSE
    avg_cross_val_rmse = np.mean(cross_val_rmse)

    # 在全训练集上训练并预测
    knn.fit(train_x, train_y)
    train_pred = knn.predict(train_x)
    test_pred = knn.predict(test_x)
    
    # 计算训练集和测试集的RMSE
    train_rmse = np.sqrt(mean_squared_error(train_y, train_pred))
    test_rmse = np.sqrt(mean_squared_error(test_y, test_pred))

    return train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse, train_y, train_pred, test_y, test_pred


def gradient_boosting_regression(data, feature, target_column='LCE', test_size=0.25, random_state=42, cv_folds=5):
    # 划分训练集和测试集
    train_x, test_x, train_y, test_y = train_test_split(
        data[feature], data[target_column], test_size=test_size, random_state=random_state
    )
    
    # 创建梯度提升回归模型
    gb = GradientBoostingRegressor(
        n_estimators=20,
        max_depth=3,
        random_state=random_state
    )

    # 使用交叉验证进行训练
    kf = KFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    cross_val_rmse = []

    # 对每一折进行训练与验证
    for train_index, val_index in kf.split(train_x):
        # 获取训练集和验证集
        X_train, X_val = train_x.iloc[train_index], train_x.iloc[val_index]
        y_train, y_val = train_y.iloc[train_index], train_y.iloc[val_index]
        
        # 训练模型
        gb.fit(X_train, y_train)
        
        # 预测验证集
        val_pred = gb.predict(X_val)
        
        # 计算验证集RMSE
        val_rmse = np.sqrt(mean_squared_error(y_val, val_pred))
        cross_val_rmse.append(val_rmse)
    
    # 计算五折交叉验证的平均RMSE
    avg_cross_val_rmse = np.mean(cross_val_rmse)

    # 在全训练集上训练并预测
    gb.fit(train_x, train_y)
    train_pred = gb.predict(train_x)
    test_pred = gb.predict(test_x)
    
    # 计算训练集和测试集的RMSE
    train_rmse = np.sqrt(mean_squared_error(train_y, train_pred))
    test_rmse = np.sqrt(mean_squared_error(test_y, test_pred))

    return train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse, train_y, train_pred, test_y, test_pred


# 实例化MolReprAccessor（确保ckp_get_mol_repr.out.pkl文件存在且格式正确）
accessor_train = MolReprAccessor('data\\ckp_train.out.pkl')
accessor_prediction = MolReprAccessor('data\\ckp_prediction.out.pkl')

# 加载数据
data=pd.read_excel('data\\electrolyte.xlsx')
mol_info=pd.read_excel('data\\mol_info.xlsx')
data=replace_names_with_smiles(data,mol_info)
data['LCE'] = -np.log10(1 - data['CE (%)']/100)

# 数据清洗
data=data[(data['Cycle number']<30) &
          (data['Cycle number']>5) &
          (data['CE (%)']>80) &
          (data['Current density']<=1) &
          (data['Capacity']<=1) ].reset_index(drop=True)

data=extract_feature_vectors(data,accessor_train).reset_index(drop=True)
feature=data.columns.to_list()
del feature[512]

# 预测数据
CE_pre=pd.read_excel('data\\electrolyte_pre.xlsx')
feture_vecture=extract_feature_vectors_for_prediction(CE_pre, accessor_prediction, accessor_train)

train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse, train_y, train_pred, test_y, test_pred, LCE=mlp(data, feature, target_column='LCE', test_size=0.25, random_state=42, cv_folds=5, predict_data=feture_vecture)
CE_pre['LCE']=LCE
CE_pre.to_excel('electrolyte_pre_results.xlsx',index=False)


# train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse, train_y, train_pred, test_y, test_pred = mlp(data, feature)
# print(train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse)

# train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse, train_y, train_pred, test_y, test_pred = xgboost(data, feature)
# print(train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse)

# train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse, train_y, train_pred, test_y, test_pred = random_forest(data, feature)
# print(train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse)

# train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse, train_y, train_pred, test_y, test_pred = decision_tree(data, feature)
# print(train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse)

# train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse, train_y, train_pred, test_y, test_pred = svm_regression(data, feature)
# print(train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse)

# train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse, train_y, train_pred, test_y, test_pred = knn_regression(data, feature)
# print(train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse)

# train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse, train_y, train_pred, test_y, test_pred = gradient_boosting_regression(data, feature)
# print(train_rmse, test_rmse, cross_val_rmse, avg_cross_val_rmse)




