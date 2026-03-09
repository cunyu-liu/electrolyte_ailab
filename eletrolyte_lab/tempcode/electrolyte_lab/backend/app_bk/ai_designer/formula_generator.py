import random
import numpy as np
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class FormulaGenerator:
    """配方生成器 - 基于贝叶斯优化和重新设计的配方生成"""

    def __init__(self):
        # 贝叶斯优化参数
        self.bayesian_params = {
            'acquisition_function': 'EI',  # Expected Improvement
            'exploration_weight': 0.1,
            'max_iterations': 50,
            'convergence_threshold': 0.01
        }

        # 重新设计策略
        self.redesign_strategies = {
            'component_replacement': 0.3,
            'concentration_adjustment': 0.4,
            'ratio_optimization': 0.3
        }

        # 配方组件库
        self.component_library = {
            'solvents': ['EC', 'DEC', 'DMC', 'EMC', 'PC'],
            'salts': ['LiPF6', 'LiBF4', 'LiClO4', 'LiTFSI'],
            'additives': ['VC', 'FEC', 'PS', 'DTD', 'LiBOB']
        }

    def generate_formula(self, predicted_data: Dict, generation_method: str = 'initial_design') -> Dict:
        """
        生成配方

        Args:
            predicted_data: 预测数据
            generation_method: 生成方法 (initial_design, bayesian_opt, redesign)

        Returns:
            生成的配方
        """
        try:
            logger.info(f"开始生成配方，方法: {generation_method}")

            if generation_method == 'initial_design':
                formula = self._generate_initial_formula(predicted_data)
            elif generation_method == 'bayesian_opt':
                formula = self._generate_bayesian_optimized_formula(predicted_data)
            elif generation_method == 'redesign':
                formula = self._generate_redesigned_formula(predicted_data)
            else:
                raise ValueError(f"未知的生成方法: {generation_method}")

            logger.info(f"配方生成完成: {formula['name']}")
            return formula

        except Exception as e:
            logger.error(f"生成配方时出错: {str(e)}")
            raise Exception(f"配方生成失败: {str(e)}")

    def _generate_initial_formula(self, predicted_data: Dict) -> Dict:
        """生成初始配方"""
        predicted_formulas = predicted_data.get('predicted_formulas', [])

        if not predicted_formulas:
            raise ValueError("没有可用的预测配方数据")

        # 选择评分最高的配方
        best_prediction = max(predicted_formulas, key=lambda x: x['overall_score'])

        # 转换为标准配方格式
        formula = {
            'name': f"初始配方_{self._get_timestamp()}",
            'description': "基于性能预测生成的初始实验配方",
            'system_type': '正极',  # 默认值，可根据实际情况调整
            'application_scenario': '3C',  # 默认值
            'components': [],
            'predicted_properties': best_prediction.get('system_properties', {}),
            'source_data': {
                'prediction_score': best_prediction['overall_score'],
                'confidence': best_prediction['prediction_confidence'],
                'source_formula': best_prediction['formula']
            }
        }

        # 转换组件格式
        original_formula = best_prediction['formula']

        # 溶剂组件
        for solvent_data in original_formula.get('solvent_ratios', []):
            component = {
                'component_type': 'solvent',
                'name': solvent_data['name'],
                'chemical_formula': self._get_chemical_formula(solvent_data['name'], 'solvent'),
                'concentration': round(solvent_data['ratio'] * 100, 2),  # 转换为百分比
                'unit': 'wt%',
                'properties': solvent_data['properties'],
                'source': 'predicted'
            }
            formula['components'].append(component)

        # 盐组件
        salt_data = original_formula.get('salt_concentration', {})
        if salt_data:
            component = {
                'component_type': 'salt',
                'name': salt_data['name'],
                'chemical_formula': self._get_chemical_formula(salt_data['name'], 'salt'),
                'concentration': round(salt_data['concentration'], 2),
                'unit': 'M',
                'properties': salt_data['properties'],
                'source': 'predicted'
            }
            formula['components'].append(component)

        # 添加剂组件
        for additive_data in original_formula.get('additive_concentrations', []):
            component = {
                'component_type': 'additive',
                'name': additive_data['name'],
                'chemical_formula': self._get_chemical_formula(additive_data['name'], 'additive'),
                'concentration': round(additive_data['concentration'], 2),
                'unit': 'wt%',
                'properties': additive_data['properties'],
                'source': 'predicted'
            }
            formula['components'].append(component)

        return formula

    def _generate_bayesian_optimized_formula(self, predicted_data: Dict) -> Dict:
        """生成贝叶斯优化配方"""
        logger.info("执行贝叶斯优化")

        # 获取基准配方
        base_formulas = predicted_data.get('predicted_formulas', [])
        if not base_formulas:
            raise ValueError("没有可用的基准配方数据")

        # 选择前5个最佳配方作为优化起点
        top_formulas = sorted(base_formulas, key=lambda x: x['overall_score'], reverse=True)[:5]

        optimized_formulas = []

        for base_formula in top_formulas:
            # 为每个基准配方生成优化变体
            optimized_variants = self._bayesian_optimize_single(base_formula)
            optimized_formulas.extend(optimized_variants)

        # 选择最佳优化结果
        best_optimized = max(optimized_formulas, key=lambda x: x['score'])

        # 转换为标准格式
        formula = {
            'name': f"贝叶斯优化配方_{self._get_timestamp()}",
            'description': "基于贝叶斯优化算法生成的实验配方",
            'system_type': '正极',
            'application_scenario': '3C',
            'components': [],
            'predicted_properties': best_optimized['properties'],
            'source_data': {
                'optimization_score': best_optimized['score'],
                'improvement': best_optimized['improvement'],
                'base_formula': best_optimized['base_formula']
            }
        }

        # 转换组件（与初始配方相同的逻辑）
        original_formula = best_optimized['formula']
        formula['components'] = self._convert_formula_to_components(original_formula)

        return formula

    def _bayesian_optimize_single(self, base_formula: Dict) -> List[Dict]:
        """对单个配方进行贝叶斯优化"""
        optimized_variants = []

        # 定义优化变量：溶剂比例、盐浓度、添加剂浓度
        original_formulation = base_formula['formula']

        # 生成多个优化候选
        for iteration in range(10):
            # 随机调整参数
            optimized_formulation = self._perturb_formulation(original_formulation)

            # 模拟评估新配方的性能
            new_score = self._evaluate_formulation(optimized_formulation)

            # 计算改进程度
            improvement = new_score - base_formula['overall_score']

            optimized_variants.append({
                'formula': optimized_formulation,
                'score': new_score,
                'improvement': improvement,
                'base_formula': original_formulation,
                'properties': self._predict_properties_for_formulation(optimized_formulation)
            })

        # 按评分排序
        optimized_variants.sort(key=lambda x: x['score'], reverse=True)

        return optimized_variants[:3]  # 返回前3个最佳变体

    def _perturb_formulation(self, original_formulation: Dict) -> Dict:
        """扰动配方参数"""
        perturbed = original_formulation.copy()

        # 扰动溶剂比例
        if 'solvent_ratios' in perturbed:
            new_ratios = []
            total_adjustment = 0

            for i, solvent in enumerate(perturbed['solvent_ratios']):
                if i == len(perturbed['solvent_ratios']) - 1:
                    # 最后一个溶剂确保总和为1
                    adjustment = -total_adjustment
                else:
                    adjustment = np.random.normal(0, 0.1)  # 10%的标准差
                    total_adjustment += adjustment

                new_ratio = max(0.05, solvent['ratio'] + adjustment)
                new_ratios.append({
                    'name': solvent['name'],
                    'ratio': new_ratio,
                    'properties': solvent['properties']
                })

            # 归一化
            total = sum(r['ratio'] for r in new_ratios)
            for r in new_ratios:
                r['ratio'] /= total

            perturbed['solvent_ratios'] = new_ratios

        # 扰动盐浓度
        if 'salt_concentration' in perturbed:
            salt = perturbed['salt_concentration'].copy()
            adjustment = np.random.normal(0, 0.2)
            new_concentration = max(0.5, min(2.0, salt['concentration'] + adjustment))
            salt['concentration'] = new_concentration
            perturbed['salt_concentration'] = salt

        # 扰动添加剂浓度
        if 'additive_concentrations' in perturbed:
            new_concentrations = []
            for additive in perturbed['additive_concentrations']:
                new_additive = additive.copy()
                adjustment = np.random.normal(0, 0.5)
                new_conc = max(0.1, min(10.0, additive['concentration'] + adjustment))
                new_additive['concentration'] = new_conc
                new_concentrations.append(new_additive)
            perturbed['additive_concentrations'] = new_concentrations

        return perturbed

    def _evaluate_formulation(self, formulation: Dict) -> float:
        """评估配方性能（模拟）"""
        # 这里模拟性能评估
        # 实际实现中会调用真正的性能预测模型

        score = 0.5  # 基础分数

        # 根据配方特征计算评分
        # 溶剂比例的影响
        if 'solvent_ratios' in formulation:
            ec_ratio = 0
            for solvent in formulation['solvent_ratios']:
                if solvent['name'] == 'EC':
                    ec_ratio = solvent['ratio']
                    break
            score += ec_ratio * 0.2  # EC比例越高评分越高

        # 盐浓度的影响
        if 'salt_concentration' in formulation:
            salt_conc = formulation['salt_concentration']['concentration']
            optimal_salt = 1.0
            score -= abs(salt_conc - optimal_salt) * 0.1

        # 添加剂的影响
        if 'additive_concentrations' in formulation:
            for additive in formulation['additive_concentrations']:
                if additive['name'] in ['VC', 'FEC']:
                    score += 0.1  # 优质添加剂加分

        # 添加随机性
        score += np.random.normal(0, 0.05)

        return max(0, min(1, score))

    def _predict_properties_for_formulation(self, formulation: Dict) -> Dict:
        """为配方预测性质（简化版）"""
        # 这里简化实现，实际会调用property_predictor
        return {
            'conductivity': 10.0 + np.random.normal(0, 1),
            'viscosity': 2.0 + np.random.normal(0, 0.2),
            'stability': 0.8 + np.random.normal(0, 0.05)
        }

    def _generate_redesigned_formula(self, predicted_data: Dict) -> Dict:
        """生成重新设计的配方"""
        logger.info("执行重新设计")

        # 获取失败的配方信息
        failed_formulas = predicted_data.get('failed_formulas', [])
        if not failed_formulas:
            # 如果没有失败的配方，使用一般重新设计策略
            return self._generate_initial_formula(predicted_data)

        # 分析失败原因
        failure_analysis = self._analyze_failures(failed_formulas)

        # 根据失败原因制定重新设计策略
        redesign_plan = self._create_redesign_plan(failure_analysis)

        # 生成新配方
        new_formulas = []
        for strategy in redesign_plan:
            new_formula = self._apply_redesign_strategy(strategy, failed_formulas)
            new_formulas.append(new_formula)

        # 选择最佳重新设计结果
        best_redesign = max(new_formulas, key=lambda x: x['predicted_score'])

        formula = {
            'name': f"重新设计配方_{self._get_timestamp()}",
            'description': f"基于失败分析重新设计的配方，解决: {', '.join(failure_analysis['main_issues'])}",
            'system_type': '正极',
            'application_scenario': '3C',
            'components': best_redesign['components'],
            'predicted_properties': best_redesign['properties'],
            'source_data': {
                'redesign_strategy': best_redesign['strategy'],
                'failure_analysis': failure_analysis,
                'expected_improvement': best_redesign['improvement']
            }
        }

        return formula

    def _analyze_failures(self, failed_formulas: List[Dict]) -> Dict:
        """分析失败原因"""
        issues = {
            'low_conductivity': 0,
            'poor_stability': 0,
            'high_viscosity': 0,
            'inadequate_sei': 0
        }

        for formula in failed_formulas:
            results = formula.get('results', {})
            if results.get('conductivity', 10) < 8:
                issues['low_conductivity'] += 1
            if results.get('stability', 0.8) < 0.7:
                issues['poor_stability'] += 1
            if results.get('viscosity', 2) > 3:
                issues['high_viscosity'] += 1
            if results.get('sei_quality', 0.8) < 0.7:
                issues['inadequate_sei'] += 1

        # 确定主要问题
        main_issues = [issue for issue, count in issues.items() if count > 0]

        return {
            'issue_counts': issues,
            'main_issues': main_issues,
            'total_failures': len(failed_formulas)
        }

    def _create_redesign_plan(self, failure_analysis: Dict) -> List[Dict]:
        """创建重新设计计划"""
        plan = []
        main_issues = failure_analysis['main_issues']

        if 'low_conductivity' in main_issues:
            plan.append({
                'strategy': 'improve_conductivity',
                'actions': ['increase_salt_concentration', 'add_conductive_solvents']
            })

        if 'poor_stability' in main_issues:
            plan.append({
                'strategy': 'improve_stability',
                'actions': ['add_stable_additives', 'replace_unstable_components']
            })

        if 'high_viscosity' in main_issues:
            plan.append({
                'strategy': 'reduce_viscosity',
                'actions': ['adjust_solvent_ratios', 'add_low_viscosity_components']
            })

        if 'inadequate_sei' in main_issues:
            plan.append({
                'strategy': 'improve_sei_formation',
                'actions': ['add_sei_forming_additives', 'optimize_additive_concentration']
            })

        return plan

    def _apply_redesign_strategy(self, strategy: Dict, failed_formulas: List[Dict]) -> Dict:
        """应用重新设计策略"""
        # 选择一个失败的配方作为基础
        base_formula = failed_formulas[0]['formula']

        redesigned_formulation = base_formula.copy()
        actions = strategy['actions']

        for action in actions:
            if action == 'increase_salt_concentration':
                if 'salt_concentration' in redesigned_formulation:
                    redesigned_formulation['salt_concentration']['concentration'] *= 1.2

            elif action == 'add_conductive_solvents':
                # 添加高导电性溶剂
                if 'solvent_ratios' in redesigned_formulation:
                    for solvent in redesigned_formulation['solvent_ratios']:
                        if solvent['name'] == 'EC':
                            solvent['ratio'] *= 1.1

            elif action == 'add_stable_additives':
                # 添加稳定性添加剂
                if 'additive_concentrations' in redesigned_formulation:
                    new_additive = {
                        'name': 'LiBOB',
                        'concentration': 2.0,
                        'unit': 'wt%',
                        'properties': {'stability': 'excellent'}
                    }
                    redesigned_formulation['additive_concentrations'].append(new_additive)

            elif action == 'adjust_solvent_ratios':
                # 调整溶剂比例以降低粘度
                if 'solvent_ratios' in redesigned_formulation:
                    for solvent in redesigned_formulation['solvent_ratios']:
                        if solvent['name'] in ['DEC', 'DMC']:
                            solvent['ratio'] *= 1.2

        components = self._convert_formula_to_components(redesigned_formulation)

        return {
            'components': components,
            'properties': self._predict_properties_for_formulation(redesigned_formulation),
            'strategy': strategy['strategy'],
            'predicted_score': self._evaluate_formulation(redesigned_formulation),
            'improvement': f"应用策略: {strategy['strategy']}"
        }

    def redesign_formula(self, experiment_data: Dict, results: List[Dict],
                        failure_reasons: List[str], iteration_count: int) -> Dict:
        """为闭环优化重新设计配方"""
        # 构建失败分析数据
        failed_formulas = [{
            'formula': experiment_data.get('formula', {}),
            'results': self._extract_results_from_data(results),
            'failure_reasons': failure_reasons
        }]

        predicted_data = {
            'failed_formulas': failed_formulas,
            'iteration_count': iteration_count
        }

        return self._generate_redesigned_formula(predicted_data)

    def run_bayesian_optimization(self, experiment_data: Dict, results: List[Dict],
                                optimization_target: str, iteration_count: int) -> Dict:
        """为闭环优化运行贝叶斯优化"""
        # 构建优化数据
        base_formulas = [{
            'formula': experiment_data.get('formula', {}),
            'results': self._extract_results_from_data(results),
            'overall_score': self._calculate_score_from_results(results)
        }]

        predicted_data = {
            'predicted_formulas': base_formulas,
            'optimization_target': optimization_target,
            'iteration_count': iteration_count
        }

        return self._generate_bayesian_optimized_formula(predicted_data)

    def _convert_formula_to_components(self, formulation: Dict) -> List[Dict]:
        """将配方转换为组件列表"""
        components = []

        # 溶剂
        for solvent in formulation.get('solvent_ratios', []):
            component = {
                'component_type': 'solvent',
                'name': solvent['name'],
                'chemical_formula': self._get_chemical_formula(solvent['name'], 'solvent'),
                'concentration': round(solvent['ratio'] * 100, 2),
                'unit': 'wt%',
                'properties': solvent['properties'],
                'source': 'optimized'
            }
            components.append(component)

        # 盐
        salt = formulation.get('salt_concentration', {})
        if salt:
            component = {
                'component_type': 'salt',
                'name': salt['name'],
                'chemical_formula': self._get_chemical_formula(salt['name'], 'salt'),
                'concentration': round(salt['concentration'], 2),
                'unit': 'M',
                'properties': salt['properties'],
                'source': 'optimized'
            }
            components.append(component)

        # 添加剂
        for additive in formulation.get('additive_concentrations', []):
            component = {
                'component_type': 'additive',
                'name': additive['name'],
                'chemical_formula': self._get_chemical_formula(additive['name'], 'additive'),
                'concentration': round(additive['concentration'], 2),
                'unit': 'wt%',
                'properties': additive['properties'],
                'source': 'optimized'
            }
            components.append(component)

        return components

    def _get_chemical_formula(self, name: str, component_type: str) -> str:
        """获取化学式"""
        formulas = {
            'solvents': {
                'EC': 'C3H4O3',
                'DEC': 'C5H10O3',
                'DMC': 'C3H6O3',
                'EMC': 'C4H8O3',
                'PC': 'C4H6O3'
            },
            'salts': {
                'LiPF6': 'LiPF6',
                'LiBF4': 'LiBF4',
                'LiClO4': 'LiClO4',
                'LiTFSI': 'LiTFSI'
            },
            'additives': {
                'VC': 'C3H4O3',
                'FEC': 'C3H5FO3',
                'PS': 'C8H8O3S',
                'DTD': 'C4H6O4S2',
                'LiBOB': 'C4BO8Li'
            }
        }

        return formulas.get(component_type, {}).get(name, 'Unknown')

    def _extract_results_from_data(self, results: List[Dict]) -> Dict:
        """从结果数据中提取性能指标"""
        performance_data = {}

        for result in results:
            result_type = result.get('result_type', '')
            data = result.get('data', {})

            if result_type == 'performance_curves':
                performance_data.update(data)

        return performance_data

    def _calculate_score_from_results(self, results: List[Dict]) -> float:
        """根据结果计算评分"""
        # 简化的评分计算
        performance = self._extract_results_from_data(results)

        score = 0.5
        if performance.get('energy_density', 0) > 200:
            score += 0.2
        if performance.get('cycle_life', 0) > 1000:
            score += 0.2
        if performance.get('safety_score', 0) > 0.8:
            score += 0.1

        return min(score, 1.0)

    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime('%Y%m%d_%H%M%S')