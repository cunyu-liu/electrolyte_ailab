import torch
import numpy as np
from botorch.models import SingleTaskGP
from botorch.fit import fit_gpytorch_mll
from gpytorch.mlls import ExactMarginalLogLikelihood
from botorch.sampling import SobolQMCNormalSampler
from botorch.acquisition.monte_carlo import qSimpleRegret
from botorch.optim import optimize_acqf
import warnings

# 过滤由于版本兼容性可能产生的警告
warnings.filterwarnings("ignore")

def suggest_new_recipes(
    existing_X: torch.Tensor, 
    existing_Y: torch.Tensor, 
    weights: dict, 
    n_new_candidates: int = 5
):
    """
    执行贝叶斯优化以推荐新的实验配方。
    
    参数:
        existing_X (Tensor): 现有实验配方，形状为 (N, D)，每行和应为 1。
        existing_Y (Tensor): 现有实验对应的多指标结果，形状为 (N, 3)。
                             假设列分别为 [retention, capacity, impedance]。
        weights (dict): 指标权重，需包含 keys: 'w_ret', 'w_cap', 'w_imp'。
        n_new_candidates (int): 需要推荐的新配方数量 (batch size)。
    
    返回:
        Tensor: 建议的新配方，形状为 (n_new_candidates, D)。
    """
    
    # 1. 设置设备
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dtype = torch.double
    
    X = existing_X.to(device=device, dtype=dtype)
    Y = existing_Y.to(device=device, dtype=dtype)
    
    # 2. 数据预处理与标量化 (Scalarization)
    # 复制数据以避免修改原数据
    Y_norm = Y.clone()
    
    # 归一化处理 (参考 Notebook 逻辑)
    # 注意：这里动态获取最大值以适应不同数据集
    Y_norm[:, 0] = Y_norm[:, 0] / 1.0                  # Retention (假设本身是0-1)
    Y_norm[:, 1] = Y_norm[:, 1] / Y_norm[:, 1].max()   # Capacity
    Y_norm[:, 2] = Y_norm[:, 2] / Y_norm[:, 2].max()   # Impedance
    
    w_ret = weights.get('w_ret', 0.5)
    w_cap = weights.get('w_cap', 0.4)
    w_imp = weights.get('w_imp', 0.1)
    
    # 计算综合得分 s_exp (越大越好)
    # 公式: w_ret * ret + w_cap * cap - w_imp * imp
    s_exp = (
        w_ret * Y_norm[:, 0]
        + w_cap * Y_norm[:, 1]
        - w_imp * Y_norm[:, 2]
    ).unsqueeze(-1) # 变成 (N, 1)
    
    print(f"正在拟合高斯过程模型 (样本数: {len(X)})...")
    
    # 3. 拟合 GP 模型
    gp = SingleTaskGP(X, s_exp)
    mll = ExactMarginalLogLikelihood(gp.likelihood, gp)
    fit_gpytorch_mll(mll)
    
    # 4. 定义优化边界
    d = X.shape[1] # 维度 (溶剂数量)
    bounds = torch.stack([
        torch.zeros(d, device=device, dtype=dtype),
        torch.ones(d, device=device, dtype=dtype),
    ])
    
    # 5. 定义采集函数 (qSimpleRegret)
    sampler = SobolQMCNormalSampler(sample_shape=torch.Size([256]))
    acq = qSimpleRegret(
        model=gp,
        sampler=sampler,
    )
    
    print(f"正在优化采集函数以寻找 {n_new_candidates} 个新配方...")
    
    # 6. 优化采集函数
    X_batch_raw, acq_value = optimize_acqf(
        acq_function=acq,
        bounds=bounds,
        q=n_new_candidates,
        num_restarts=10,
        raw_samples=256,
    )
    
    # 7. 后处理：投影回单纯形 (Simplex Projection)
    # 确保非负且和为 1
    X_batch = X_batch_raw.clamp(min=0)
    X_batch = X_batch / X_batch.sum(dim=-1, keepdim=True)
    
    return X_batch

# ==========================================
# 主运行逻辑 (Example Usage)
# ==========================================
if __name__ == "__main__":
    # 1. 准备输入数据 (模拟 Notebook 中的数据)
    # 这里的维度是 10 (d=10)
    X_input = torch.tensor([
        [0.10, 0.05, 0.20, 0.10, 0.05, 0.10, 0.15, 0.10, 0.10, 0.05],
        [0.12, 0.08, 0.18, 0.10, 0.07, 0.10, 0.13, 0.11, 0.08, 0.03],
        [0.08, 0.05, 0.22, 0.12, 0.04, 0.12, 0.14, 0.13, 0.06, 0.04],
    ])

    # 对应指标: [retention, capacity, impedance]
    Y_input = torch.tensor([
        [0.92, 180.0, 50.0],
        [0.88, 175.0, 45.0],
        [0.95, 178.0, 60.0],
    ])

    # 定义权重
    metric_weights = {
        'w_ret': 0.5,
        'w_cap': 0.4,
        'w_imp': 0.1
    }

    # 2. 调用函数
    try:
        new_recipes = suggest_new_recipes(
            existing_X=X_input,
            existing_Y=Y_input,
            weights=metric_weights,
            n_new_candidates=5  # 想要生成的新配方数量
        )

        # 3. 输出结果
        print("\n=== 优化完成 ===")
        print("建议的新配方 (每一行是一个配方):")
        # 设置打印精度以便查看
        torch.set_printoptions(precision=4, sci_mode=False)
        print(new_recipes)
        
        print("\n配方归一化校验 (每行和应为 1):")
        print(new_recipes.sum(dim=-1))
        
    except Exception as e:
        print(f"运行出错: {e}")