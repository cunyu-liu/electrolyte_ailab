import numpy as np
import json
import os
from typing import Dict, List, Tuple, Any, Optional, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 尝试导入可选的高级库，如果不可用则使用简化版本
HAS_BO_TORCH = False
HAS_SKLEARN = False

# 尝试导入scikit-learn
try:
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel
    from scipy.optimize import minimize
    HAS_SKLEARN = True
    logger.info("使用scikit-learn进行贝叶斯优化")
except ImportError:
    logger.warning("scikit-learn未安装，将使用随机生成")

# 尝试导入BoTorch（高级版本）
try:
    import torch
    from botorch.models import SingleTaskGP
    from botorch.fit import fit_gpytorch_mll
    from gpytorch.mlls import ExactMarginalLogLikelihood
    from botorch.sampling import SobolQMCNormalSampler
    from botorch.acquisition.monte_carlo import qSimpleRegret
    from botorch.optim import optimize_acqf
    HAS_BO_TORCH = True
    logger.info("使用BoTorch进行高级贝叶斯优化")
except ImportError:
    logger.warning("BoTorch未安装，将使用scikit-learn或随机生成")


class ElectrolyteBayesianOptimizer:
    """电解液配方贝叶斯优化器"""

    def __init__(self, data_file: str = "data/electrolyte_experiments.json"):
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
        data_dir = os.path.dirname(self.data_file)
        if data_dir:  # 只有当目录名不为空时才创建
            os.makedirs(data_dir, exist_ok=True)

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
            logger.error(f"加载数据失败: {e}")
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
            logger.error(f"保存数据失败: {e}")

    def add_formula_data(self, formula_data: Dict, user_requirements: Dict = None) -> bool:
        """添加AI设计员生成的配方数据到优化器"""
        try:
            logger.info("添加AI设计员生成的配方数据到贝叶斯优化器")

            # 从配方数据中提取组分信息
            components = {}

            # 处理标准配方格式
            if 'components' in formula_data:
                for component in formula_data['components']:
                    if component.get('component_type') == 'solvent':
                        # 提取溶剂组分
                        name = component.get('name', f'solvent_{len(components)+1}')
                        concentration = float(component.get('concentration', 0))
                        # 转换百分比到比例
                        ratio = concentration / 100.0
                        components[f'solvent_{len(components)+1}'] = ratio

            # 备用处理：直接从solvent_ratios提取
            elif 'solvent_ratios' in formula_data:
                solvent_ratios = formula_data['solvent_ratios']
                if isinstance(solvent_ratios, dict):
                    components = {f'solvent_{k}': v for k, v in solvent_ratios.items()}
                elif isinstance(solvent_ratios, list):
                    for i, ratio in enumerate(solvent_ratios, 1):
                        components[f'solvent_{i}'] = float(ratio)

            # 如果仍然没有组分数据，从源数据提取
            elif 'source_data' in formula_data and 'source_formula' in formula_data['source_data']:
                source_formula = formula_data['source_data']['source_formula']
                if 'solvent_ratios' in source_formula:
                    for i, solvent_data in enumerate(source_formula['solvent_ratios'], 1):
                        ratio = float(solvent_data.get('ratio', 0))
                        components[f'solvent_{i}'] = ratio

            # 如果仍然没有组分数据，创建默认分布
            if not components:
                logger.warning("配方数据中未找到组分信息，使用默认均匀分布")
                components = {f'solvent_{i}': 0.1 for i in range(1, 11)}

            # 确保所有值都是float类型
            components = {k: float(v) for k, v in components.items()}

            # 验证组分总和并归一化
            total = sum(components.values())
            if abs(total - 1.0) > 0.01:
                logger.warning(f"组分总和不为1.0 (当前: {total:.4f})，将进行归一化")
                if total > 0:
                    components = {k: v/total for k, v in components.items()}

            # 从预测属性或用户需求提取指标数据
            metrics = {}

            # 首先尝试从预测属性提取
            if 'predicted_properties' in formula_data:
                props = formula_data['predicted_properties']
                # 映射预测属性到标准指标
                metrics.update({
                    'energy_density': float(props.get('energy_density', 200)),
                    'power_density': float(props.get('power_density', 1000)),
                    'cycle_life': float(props.get('cycle_life', 1000)),
                    'safety_score': float(props.get('safety_score', 0.8)),
                    'stability_score': float(props.get('stability_score', 0.8))
                })

            # 如果有用户需求，作为优化目标
            if user_requirements:
                logger.info(f"使用用户需求作为优化目标: {user_requirements}")

                # 将用户需求转换为指标
                requirement_metrics = {}
                for key, value in user_requirements.items():
                    if key in ['energy_density', 'power_density', 'cycle_life', 'safety_score']:
                        requirement_metrics[key] = float(value)

                # 如果缺少某些指标，使用用户需求作为目标值
                for metric, value in requirement_metrics.items():
                    if metric not in metrics:
                        metrics[metric] = value * 0.9  # 假设当前配方达到需求的90%

            # 确保至少有基本的指标数据
            basic_metrics = ['energy_density', 'power_density', 'cycle_life', 'safety_score']
            for metric in basic_metrics:
                if metric not in metrics:
                    # 根据用户需求或添加默认值
                    if user_requirements and metric in user_requirements:
                        default_value = float(user_requirements[metric]) * 0.9
                    else:
                        # 智能默认值
                        defaults = {
                            'energy_density': 200.0,
                            'power_density': 1000.0,
                            'cycle_life': 1000.0,
                            'safety_score': 0.8
                        }
                        default_value = defaults.get(metric, 1.0)
                    metrics[metric] = default_value
                    logger.warning(f"添加默认指标 {metric}: {default_value}")

            # 转换为贝叶斯优化器需要的标准指标格式
            standard_metrics = {
                'retention': metrics.get('safety_score', 0.8),      # 安全性作为保持率
                'capacity': metrics.get('energy_density', 200.0),  # 能量密度作为容量
                'impedance': 100.0 - metrics.get('safety_score', 0.8) * 50  # 安全性转换为阻抗（反向指标）
            }

            # 确保所有值都是float类型
            standard_metrics = {k: float(v) for k, v in standard_metrics.items()}

            if not standard_metrics:
                logger.error("无法提取任何指标数据")
                return False

            # 创建配方实验记录
            experiment = {
                'id': formula_data.get('name', f'formula_{len(self.experiments) + 1}'),
                'components': components,
                'metrics': standard_metrics,
                'original_metrics': metrics,  # 保存原始指标
                'notes': formula_data.get('description', ''),
                'source': 'ai_designer',
                'user_requirements': user_requirements or {},
                'created_at': datetime.now().isoformat()
            }

            self.experiments.append(experiment)
            self.save_data()

            logger.info(f"成功添加AI配方数据: {experiment['id']}")
            return True

        except Exception as e:
            logger.error(f"添加AI配方数据失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return False

    def add_experiment_data(self, experiment_data: Dict, results: List[Dict]) -> bool:
        """添加实验数据到优化器（保持向后兼容）"""
        try:
            # 从实验数据中提取配方信息
            formula = experiment_data.get('formula', {})
            components = {}

            # 提取溶剂组分信息
            if 'solvent_ratios' in formula:
                solvent_ratios = formula['solvent_ratios']
                if isinstance(solvent_ratios, dict):
                    # 直接使用solvent_ratios
                    components = {f'solvent_{k}': v for k, v in solvent_ratios.items()}
                else:
                    logger.warning("solvent_ratios不是字典格式")
            elif 'components' in formula:
                components = formula['components']
            else:
                # 尝试从其他字段提取组分信息
                for key, value in formula.items():
                    if 'solvent' in key.lower() and isinstance(value, (int, float)):
                        components[key] = value

            # 如果仍然没有组分数据，创建默认的均匀分布
            if not components:
                logger.warning("实验数据中未找到组分信息，使用默认均匀分布")
                components = {f'solvent_{i}': 0.1 for i in range(1, 11)}  # 10个溶剂，每个0.1

            # 确保所有值都是float类型
            components = {k: float(v) for k, v in components.items()}

            # 验证组分总和
            total = sum(components.values())
            if abs(total - 1.0) > 0.01:
                logger.warning(f"组分总和不为1.0 (当前: {total:.4f})，将进行归一化")
                components = {k: v/total for k, v in components.items()}

            # 提取指标数据
            metrics = {}
            for result in results:
                if 'metric_name' in result and 'value' in result:
                    metrics[result['metric_name']] = float(result['value'])
                elif 'performance_metrics' in result:
                    for metric_name, metric_value in result['performance_metrics'].items():
                        metrics[metric_name] = float(metric_value)

            # 确保至少有基本的指标数据
            required_metrics = ['retention', 'capacity', 'impedance']
            for metric in required_metrics:
                if metric not in metrics:
                    # 添加默认值
                    default_value = 0.8 if metric == 'retention' else 100.0 if metric == 'capacity' else 50.0
                    metrics[metric] = default_value
                    logger.warning(f"添加默认指标 {metric}: {default_value}")

            # 确保所有值都是float类型
            metrics = {k: float(v) for k, v in metrics.items()}

            if not metrics:
                logger.error("无法提取任何指标数据")
                return False

            experiment = {
                'id': experiment_data.get('id', f'exp_{len(self.experiments) + 1}'),
                'components': components,
                'metrics': metrics,
                'notes': experiment_data.get('description', ''),
                'created_at': experiment_data.get('created_at', datetime.now().isoformat())
            }

            self.experiments.append(experiment)
            self.save_data()

            logger.info(f"成功添加实验数据: {experiment['id']}")
            return True

        except Exception as e:
            logger.error(f"添加实验数据失败: {e}")
            return False

    def suggest_optimized_formulas(self, weights: Dict[str, float],
                                 n_candidates: int = 5,
                                 optimization_target: str = 'all',
                                 user_requirements: Dict = None) -> Dict[str, Any]:
        """
        生成优化建议

        Args:
            weights: 指标权重，如 {'w_ret': 0.5, 'w_cap': 0.4, 'w_imp': 0.1}
            n_candidates: 需要推荐的配方数量
            optimization_target: 优化目标 ('all', 'performance', 'stability')
            user_requirements: 用户需求字典，用于动态调整优化目标

        Returns:
            包含优化建议的字典
        """
        if len(self.experiments) < 3:
            logger.warning("实验数据不足，生成随机配方")
            return self._generate_random_formulas(n_candidates)

        try:
            logger.info(f"开始贝叶斯优化，使用{len(self.experiments)}条实验数据")

            if HAS_BO_TORCH:
                return self._optimize_with_botorch(weights, n_candidates, optimization_target, user_requirements)
            elif HAS_SKLEARN:
                return self._optimize_with_sklearn(weights, n_candidates, optimization_target, user_requirements)
            else:
                logger.warning("无可用的优化库，生成随机配方")
                return self._generate_random_formulas(n_candidates, user_requirements)

        except Exception as e:
            logger.error(f"贝叶斯优化失败: {e}")
            return self._generate_random_formulas(n_candidates)

    def _optimize_with_botorch(self, weights: Dict[str, float],
                             n_candidates: int, optimization_target: str, user_requirements: Dict = None) -> Dict[str, Any]:
        """
        使用BoTorch进行配方组分优化

        重要：这个函数专注于优化配方组分，不预测性能
        基于历史实验数据中配方组分的实际表现来优化新的组分比例
        """
        try:
            # 获取数据张量
            X, Y = self._get_data_tensors()

            # 设置设备
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            dtype = torch.double

            X = X.to(device=device, dtype=dtype)

            # 计算每个历史配方的实际得分（基于用户需求）
            scores = []
            for i, exp in enumerate(self.experiments):
                metrics = exp['metrics']
                score = self._calculate_performance_score(metrics, user_requirements)
                scores.append(score)

            # 转换为张量
            Y_scores = torch.tensor(scores, device=device, dtype=dtype).unsqueeze(-1)

            # 拟合GP模型（配方组分 -> 实验得分）
            gp = SingleTaskGP(X, Y_scores)
            mll = ExactMarginalLogLikelihood(gp.likelihood, gp)
            fit_gpytorch_mll(mll)

            # 优化边界（组分比例）
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

            # 投影回单纯形（确保组分比例为1）
            X_batch = X_batch_raw.clamp(min=0)
            X_batch = X_batch / X_batch.sum(dim=-1, keepdim=True)

            # 转换为配方格式
            suggestions = self._tensor_to_formulas(X_batch, acq_value, optimization_target, user_requirements)

            return {
                'success': True,
                'optimized_formulas': suggestions,
                'method': 'botorch_bayesian_optimization',
                'data_size': len(X),
                'optimization_target': optimization_target,
                'user_requirements': user_requirements or {}
            }

        except Exception as e:
            logger.error(f"BoTorch优化失败: {e}")
            return self._generate_random_formulas(n_candidates, user_requirements)

    def _optimize_with_sklearn(self, weights: Dict[str, float],
                             n_candidates: int, optimization_target: str, user_requirements: Dict = None) -> Dict[str, Any]:
        """
        使用scikit-learn进行配方组分优化

        重要：这个函数专注于优化配方组分，不预测性能
        基于历史实验数据中配方组分的实际表现来优化新的组分比例
        """
        try:
            # 获取数据数组
            X, Y = self._get_data_arrays()

            # 计算每个历史配方的实际得分（基于用户需求）
            scores = []
            for exp in self.experiments:
                metrics = exp['metrics']
                score = self._calculate_performance_score(metrics, user_requirements)
                scores.append(score)

            # 转换为numpy数组
            Y_scores = np.array(scores).reshape(-1, 1)

            # 拟合GP模型（配方组分 -> 实验得分）
            kernel = ConstantKernel(1.0) * RBF(length_scale=1.0)
            gp = GaussianProcessRegressor(kernel=kernel, alpha=1e-6, normalize_y=True)
            gp.fit(X, Y_scores.ravel())

            # 优化目标函数（基于采集函数）
            def acquisition(x):
                x = x.reshape(1, -1)
                mean, std = gp.predict(x, return_std=True)
                # Upper Confidence Bound (UCB) 采集函数
                exploration = 1.96 * std
                return -(mean + exploration)  # 最大化UCB

            # 约束条件（组分比例和为1）
            constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
            bounds = [(0, 1) for _ in range(X.shape[1])]

            suggestions = []
            for i in range(n_candidates):
                # 随机初始点
                x0 = np.random.dirichlet(np.ones(X.shape[1]))

                # 优化
                result = minimize(acquisition, x0, method='SLSQP',
                                bounds=bounds, constraints=constraints)

                if result.success:
                    x_opt = result.x
                    x_opt = np.maximum(x_opt, 0)
                    x_opt = x_opt / np.sum(x_opt)

                    # 使用GP模型预测这个配方的潜在得分
                    confidence = gp.predict(x_opt.reshape(1, -1))[0]

                    formula = self._array_to_formula(x_opt, confidence, optimization_target, i, user_requirements)
                    suggestions.append(formula)

            return {
                'success': True,
                'optimized_formulas': suggestions,
                'method': 'sklearn_bayesian_optimization',
                'data_size': len(X),
                'optimization_target': optimization_target,
                'user_requirements': user_requirements or {}
            }

        except Exception as e:
            logger.error(f"Scikit-learn优化失败: {e}")
            return self._generate_random_formulas(n_candidates, user_requirements)

    def _generate_random_formulas(self, n_candidates: int, user_requirements: Dict = None) -> Dict[str, Any]:
        """
        生成随机配方组分

        注意：这个函数不预测性能，只生成配方组分
        实际性能需要通过AI实验员进行实验来获得
        """
        suggestions = []

        for i in range(n_candidates):
            # 生成随机配方组分
            weights = np.random.dirichlet(np.ones(len(self.component_names)))

            # 计算配方的潜在得分（基于历史数据）
            score = self._calculate_formula_score(weights, user_requirements)

            formula = {
                'id': f'random_{len(self.experiments)}_{i+1}',
                'solvent_ratios': {f'solvent_{j+1}': round(float(weights[j]), 4)
                                 for j in range(len(self.component_names))},
                'confidence_score': score,  # 基于历史数据的置信度
                'generation_method': 'random_generation',
                'optimization_target': 'all',
                'formula_score': score,  # 配方基于历史数据的得分
                'user_requirements': user_requirements or {},
                'created_at': datetime.now().isoformat(),
                'description': f'随机生成的配方组分 #{i+1}，需要通过实验验证实际性能'
            }
            suggestions.append(formula)

        return {
            'success': True,
            'optimized_formulas': suggestions,
            'method': 'random_generation',
            'message': f'实验数据不足，生成{len(self.component_names)}组随机配方'
        }

    def _get_data_tensors(self):
        """获取数据张量（用于BoTorch）"""
        if not HAS_BO_TORCH:
            raise ImportError("BoTorch未安装，无法获取数据张量")

        X_list = []
        Y_list = []

        for exp in self.experiments:
            # 配方数据
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

    def _get_data_arrays(self) -> Tuple[np.ndarray, np.ndarray]:
        """获取数据数组（用于scikit-learn）"""
        X_list = []
        Y_list = []

        for exp in self.experiments:
            # 配方数据
            components = exp['components']
            total = sum(components.values())
            x = np.array([components.get(f'solvent_{i+1}', 0.0) / total
                         for i in range(len(self.component_names))])
            X_list.append(x)

            # 指标数据
            y = np.array([exp['metrics'].get(metric, 0.0)
                         for metric in self.metric_info['metrics']])
            Y_list.append(y)

        X = np.array(X_list)
        Y = np.array(Y_list)

        return X, Y

    # 简化的数据获取函数
    def _get_data_arrays(self) -> Tuple[np.ndarray, np.ndarray]:
        """获取数据数组（仅用于获取配方组分）"""
        X_list = []

        for exp in self.experiments:
            # 配方数据
            components = exp["components"]
            total = sum(components.values())
            x = np.array([components.get(f"solvent_{i+1}", 0.0) / total
                         for i in range(len(self.component_names))])
            X_list.append(x)

        return np.array(X_list), np.array([])  # 不需要Y数组，因为我们直接计算得分

    def _calculate_performance_score(self, metrics: Dict[str, float], user_requirements: Dict = None) -> float:
        """
        根据实际实验性能和用户需求计算得分
        """
        if not user_requirements:
            # 如果没有用户需求，使用默认评分
            retention = metrics.get('retention', 0.8)
            capacity = metrics.get('capacity', 150)
            impedance = metrics.get('impedance', 50)

            # 标准化到0-1范围
            retention_score = min(1.0, retention / 0.95)  # 假设95%为满分
            capacity_score = min(1.0, capacity / 300)    # 假设300为满分
            impedance_score = max(0.0, 1.0 - impedance / 100)  # 阻抗越低越好

            return (retention_score * 0.4 + capacity_score * 0.4 + impedance_score * 0.2)

        # 根据用户需求计算得分
        score = 0.0
        total_weight = 0.0

        # 能量密度需求
        if 'energy_density' in user_requirements:
            actual = metrics.get('capacity', 0)  # 这里用capacity作为能量密度的代理
            target = user_requirements['energy_density']
            achievement = min(1.0, actual / target)
            score += achievement * 0.3
            total_weight += 0.3

        # 循环寿命需求
        if 'cycle_life' in user_requirements:
            actual = metrics.get('retention', 0) * 2000  # 假设保持率映射到循环寿命
            target = user_requirements['cycle_life']
            achievement = min(1.0, actual / target)
            score += achievement * 0.3
            total_weight += 0.3

        # 安全评分需求
        if 'safety_score' in user_requirements:
            actual = metrics.get('retention', 0)  # 用保持率作为安全性的代理
            target = user_requirements['safety_score']
            achievement = min(1.0, actual / target)
            score += achievement * 0.2
            total_weight += 0.2

        # 功率密度需求（与阻抗相关）
        if 'power_density' in user_requirements:
            actual = 1000 / (metrics.get('impedance', 100) + 1)  # 简化的功率密度计算
            target = user_requirements['power_density']
            achievement = min(1.0, actual / target)
            score += achievement * 0.2
            total_weight += 0.2

        return score / total_weight if total_weight > 0 else 0.5

    def _calculate_formula_score(self, x: np.ndarray, user_requirements: Dict = None) -> float:
        """
        计算配方的得分（基于用户需求）

        这个函数不预测性能，而是基于历史实验数据评估当前配方组分的质量
        """
        # 基于历史数据计算配方相似度和潜在性能
        if not self.experiments:
            # 如果没有历史数据，返回基础分数
            return 0.5

        # 找到相似的历史配方
        similarities = []
        scores = []

        for exp in self.experiments:
            # 计算配方相似度
            exp_components = exp['components']
            exp_x = np.array([exp_components.get(f'solvent_{i+1}', 0.0)
                            for i in range(len(self.component_names))])

            # 归一化
            exp_x_norm = exp_x / np.sum(exp_x) if np.sum(exp_x) > 0 else exp_x
            x_norm = x / np.sum(x) if np.sum(x) > 0 else x

            # 计算欧氏距离作为相似度度量
            distance = np.linalg.norm(exp_x_norm - x_norm)
            similarity = 1 / (1 + distance)  # 转换为相似度

            # 获取该历史配方的实际性能得分
            actual_metrics = exp['metrics']
            performance_score = self._calculate_performance_score(actual_metrics, user_requirements)

            similarities.append(similarity)
            scores.append(performance_score)

        # 基于相似度加权平均，预测这个配方的潜在性能
        if similarities:
            # 使用加权平均，更相似的配方权重更高
            weighted_score = np.average(scores, weights=similarities)
            return max(0.0, min(1.0, weighted_score))

        return 0.5

    def _array_to_formula(self, x: np.ndarray, confidence: float, optimization_target: str, index: int, user_requirements: Dict = None) -> Dict:
        """将numpy数组转换为配方格式"""
        return {
            'id': f'sklearn_opt_{len(self.experiments)}_{index+1}',
            'solvent_ratios': {f'solvent_{j+1}': round(float(x[j]), 4)
                             for j in range(len(self.component_names))},
            'confidence_score': float(confidence),
            'generation_method': 'sklearn_bayesian_optimization',
            'optimization_target': optimization_target,
            'formula_score': float(confidence),
            'user_requirements': user_requirements or {},
            'created_at': datetime.now().isoformat(),
            'description': f'scikit-learn贝叶斯优化生成的配方组分 #{index+1}'
        }

    def _tensor_to_formulas(self, X_batch, acq_value, optimization_target: str, user_requirements: Dict = None) -> List[Dict]:
        """将张量转换为配方格式"""
        if not HAS_BO_TORCH:
            logger.warning("BoTorch未安装，无法使用张量转换功能")
            return []

        import torch
        suggestions = []
        for i in range(X_batch.shape[0]):
            x = X_batch[i].cpu().numpy()
            confidence = float(acq_value[i].cpu().numpy()) if acq_value.numel() > 0 else 0.5

            formula = {
                'id': f'botorch_opt_{len(self.experiments)}_{i+1}',
                'solvent_ratios': {f'solvent_{j+1}': round(float(x[j]), 4)
                                 for j in range(len(self.component_names))},
                'confidence_score': confidence,
                'generation_method': 'botorch_bayesian_optimization',
                'optimization_target': optimization_target,
                'formula_score': confidence,
                'user_requirements': user_requirements or {},
                'created_at': datetime.now().isoformat(),
                'description': f'BoTorch贝叶斯优化生成的配方组分 #{i+1}'
            }
            suggestions.append(formula)

        return suggestions

    def get_optimization_stats(self) -> Dict:
        """获取优化器统计信息"""
        return {
            'total_experiments': len(self.experiments),
            'metrics_count': len(self.metric_info['metrics']),
            'components_count': len(self.component_names),
            'available_methods': ['botorch' if HAS_BO_TORCH else None, 'sklearn' if HAS_SKLEARN else None, 'random'],
            'last_updated': datetime.now().isoformat()
        } 
