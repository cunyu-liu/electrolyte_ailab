import torch
import numpy as np
import json
import os
from typing import Dict, List, Tuple, Any
from botorch.models import SingleTaskGP
from botorch.fit import fit_gpytorch_mll
from gpytorch.mlls import ExactMarginalLogLikelihood
from botorch.sampling import SobolQMCNormalSampler
from botorch.acquisition.monte_carlo import qSimpleRegret
from botorch.optim import optimize_acqf
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

class BayesianOptimizationManager:
    """贝叶斯优化管理器，支持动态指标数量和闭环优化"""

    def __init__(self, data_file: str = "data/experiments.json"):
        self.data_file = data_file
        self.component_names = [
            "溶剂1", "溶剂2", "溶剂3", "溶剂4", "溶剂5",
            "溶剂6", "溶剂7", "溶剂8", "溶剂9", "溶剂10"
        ]
        self.default_metrics = ["retention", "capacity", "impedance"]
        self.ensure_data_directory()
        self.load_data()

    def ensure_data_directory(self):
        """确保数据目录存在"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)

    def load_data(self) -> Dict:
        """加载实验数据"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.experiments = data.get('experiments', [])
                    self.metric_info = data.get('metric_info', {
                        'metrics': self.default_metrics,
                        'descriptions': ['保持率', '容量', '阻抗'],
                        'directions': ['maximize', 'maximize', 'minimize']
                    })
                    self.component_names = data.get('component_names', self.component_names)
            else:
                self.experiments = []
                self.metric_info = {
                    'metrics': self.default_metrics,
                    'descriptions': ['保持率', '容量', '阻抗'],
                    'directions': ['maximize', 'maximize', 'minimize']
                }
        except Exception as e:
            print(f"加载数据失败: {e}")
            self.experiments = []
            self.metric_info = {
                'metrics': self.default_metrics,
                'descriptions': ['保持率', '容量', '阻抗'],
                'directions': ['maximize', 'maximize', 'minimize']
            }

    def save_data(self):
        """保存实验数据"""
        try:
            data = {
                'experiments': self.experiments,
                'metric_info': self.metric_info,
                'component_names': self.component_names,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存数据失败: {e}")

    def get_experiment_tensors(self) -> Tuple[torch.Tensor, torch.Tensor]:
        """将实验数据转换为PyTorch张量"""
        if not self.experiments:
            raise ValueError("没有实验数据")

        X_list = []
        Y_list = []

        for exp in self.experiments:
            # 配方数据（确保归一化到和为1）
            components = exp['components']
            total = sum(components.values())
            x = np.array([components.get(f'solvent_{i+1}', 0.0) / total
                         for i in range(len(self.component_names))])
            X_list.append(x)

            # 指标数据
            y = np.array([exp['metrics'].get(metric, 0.0)
                         for metric in self.metric_info['metrics']])
            Y_list.append(y)

        X = torch.tensor(np.array(X_list), dtype=torch.double)
        Y = torch.tensor(np.array(Y_list), dtype=torch.double)

        return X, Y

    def suggest_new_recipes(self, weights: Dict[str, float], n_candidates: int = 5) -> Dict[str, Any]:
        """
        执行贝叶斯优化以推荐新的实验配方

        Args:
            weights: 指标权重，格式为 {'w_ret': 0.5, 'w_cap': 0.4, 'w_imp': 0.1}
            n_candidates: 需要推荐的新配方数量

        Returns:
            包含新配方和建议信息的字典
        """
        if len(self.experiments) < 3:
            # 如果实验数据不足，返回随机配方
            return self._generate_random_recipes(n_candidates)

        try:
            # 获取数据
            X, Y = self.get_experiment_tensors()

            # 设置设备
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            dtype = torch.double

            X = X.to(device=device, dtype=dtype)
            Y = Y.to(device=device, dtype=dtype)

            # 数据标准化
            Y_norm = self._normalize_metrics(Y)

            # 标量化（计算综合得分）
            s_exp = self._scalarize_objectives(Y_norm, weights, device)

            # 拟合GP模型
            gp = SingleTaskGP(X, s_exp)
            mll = ExactMarginalLogLikelihood(gp.likelihood, gp)
            fit_gpytorch_mll(mll)

            # 优化边界
            d = X.shape[1]
            bounds = torch.stack([
                torch.zeros(d, device=device, dtype=dtype),
                torch.ones(d, device=device, dtype=dtype),
            ])

            # 定义采集函数
            sampler = SobolQMCNormalSampler(sample_shape=torch.Size([256]))
            acq = qSimpleRegret(model=gp, sampler=sampler)

            # 优化采集函数
            X_batch_raw, acq_value = optimize_acqf(
                acq_function=acq,
                bounds=bounds,
                q=n_candidates,
                num_restarts=10,
                raw_samples=256,
            )

            # 投影回单纯形
            X_batch = X_batch_raw.clamp(min=0)
            X_batch = X_batch / X_batch.sum(dim=-1, keepdim=True)

            # 转换为字典格式
            suggestions = self._tensor_to_suggestions(X_batch, acq_value)

            return {
                'success': True,
                'suggestions': suggestions,
                'method': 'bayesian_optimization',
                'data_size': len(X),
                'acq_value': acq_value.item() if acq_value.numel() == 1 else acq_value.tolist()
            }

        except Exception as e:
            print(f"贝叶斯优化失败: {e}")
            return self._generate_random_recipes(n_candidates)

    def _normalize_metrics(self, Y: torch.Tensor) -> torch.Tensor:
        """标准化指标数据"""
        Y_norm = Y.clone()

        for i, direction in enumerate(self.metric_info['directions']):
            if direction == 'maximize':
                # 对于需要最大化的指标，除以最大值
                Y_norm[:, i] = Y_norm[:, i] / (Y_norm[:, i].max() + 1e-8)
            else:
                # 对于需要最小化的指标，反向归一化
                Y_norm[:, i] = 1.0 - (Y_norm[:, i] / (Y_norm[:, i].max() + 1e-8))

        return Y_norm

    def _scalarize_objectives(self, Y_norm: torch.Tensor, weights: Dict[str, float], device) -> torch.Tensor:
        """标量化多目标为单一目标"""
        n_metrics = Y_norm.shape[1]

        # 如果权重数量与指标数量不匹配，使用默认权重
        if len(weights) != n_metrics:
            default_weights = [1.0 / n_metrics] * n_metrics
            weight_values = torch.tensor(default_weights, device=device, dtype=torch.double)
        else:
            # 按权重字典中的顺序提取权重值
            weight_keys = sorted(weights.keys())
            weight_values = torch.tensor([weights[k] for k in weight_keys],
                                       device=device, dtype=torch.double)

        # 计算加权得分
        s_exp = (Y_norm * weight_values).sum(dim=-1)

        return s_exp.unsqueeze(-1)

    def _tensor_to_suggestions(self, X_batch: torch.Tensor, acq_value: torch.Tensor) -> List[Dict]:
        """将张量转换为建议字典列表"""
        suggestions = []
        X_batch_np = X_batch.cpu().numpy()
        acq_value_np = acq_value.cpu().numpy() if acq_value.numel() > 1 else [acq_value.item()]

        for i in range(X_batch_np.shape[0]):
            components = {}
            for j, name in enumerate(self.component_names):
                components[f'solvent_{j+1}'] = round(float(X_batch_np[i, j]), 4)

            suggestion = {
                'id': f'suggestion_{len(self.experiments)}_{i+1}',
                'components': components,
                'total_confidence': float(acq_value_np[i]) if len(acq_value_np) > 1 else float(acq_value_np[0]),
                'created_at': datetime.now().isoformat()
            }
            suggestions.append(suggestion)

        return suggestions

    def _generate_random_recipes(self, n_candidates: int) -> Dict[str, Any]:
        """生成随机配方（用于数据不足时的fallback）"""
        suggestions = []

        for i in range(n_candidates):
            # 生成随机权重并归一化
            weights = np.random.dirichlet(np.ones(len(self.component_names)))

            components = {}
            for j, name in enumerate(self.component_names):
                components[f'solvent_{j+1}'] = round(float(weights[j]), 4)

            suggestion = {
                'id': f'random_{len(self.experiments)}_{i+1}',
                'components': components,
                'total_confidence': 0.5,  # 随机配方的置信度设为中等
                'created_at': datetime.now().isoformat()
            }
            suggestions.append(suggestion)

        return {
            'success': True,
            'suggestions': suggestions,
            'method': 'random_generation',
            'message': f'实验数据不足，生成{len(self.component_names)}组随机配方'
        }

    def add_experiment(self, components: Dict[str, float], metrics: Dict[str, float],
                      notes: str = "") -> bool:
        """添加新的实验数据"""
        try:
            # 验证组件数据
            total = sum(components.values())
            if abs(total - 1.0) > 0.01:  # 允许小的数值误差
                # 归一化到1
                components = {k: v / total for k, v in components.items()}

            experiment = {
                'id': f'exp_{len(self.experiments) + 1}',
                'components': components,
                'metrics': metrics,
                'notes': notes,
                'created_at': datetime.now().isoformat()
            }

            self.experiments.append(experiment)
            self.save_data()
            return True

        except Exception as e:
            print(f"添加实验失败: {e}")
            return False

    def get_experiments(self) -> List[Dict]:
        """获取所有实验数据"""
        return self.experiments

    def get_metric_info(self) -> Dict:
        """获取指标信息"""
        return self.metric_info

    def update_metric_info(self, metrics: List[str], descriptions: List[str],
                          directions: List[str]) -> bool:
        """更新指标信息"""
        try:
            if len(metrics) != len(descriptions) or len(metrics) != len(directions):
                return False

            self.metric_info = {
                'metrics': metrics,
                'descriptions': descriptions,
                'directions': directions
            }
            self.save_data()
            return True

        except Exception as e:
            print(f"更新指标信息失败: {e}")
            return False