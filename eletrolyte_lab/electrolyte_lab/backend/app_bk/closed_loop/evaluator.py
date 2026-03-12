import numpy as np
from typing import Dict, List, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class ExperimentEvaluator:
    """实验评估器 - 评估实验结果是否满足用户需求"""

    def __init__(self):
        # 评估权重配置
        self.evaluation_weights = {
            'energy_density': 0.25,
            'power_density': 0.20,
            'cycle_life': 0.20,
            'safety': 0.20,
            'cost': 0.15
        }

        # 评估阈值配置
        self.evaluation_thresholds = {
            'strict': {
                'energy_density': 0.95,  # 需要达到目标的95%
                'power_density': 0.95,
                'cycle_life': 0.95,
                'safety': 0.90,
                'cost': 0.85
            },
            'moderate': {
                'energy_density': 0.85,
                'power_density': 0.85,
                'cycle_life': 0.85,
                'safety': 0.80,
                'cost': 0.75
            },
            'lenient': {
                'energy_density': 0.70,
                'power_density': 0.70,
                'cycle_life': 0.75,
                'safety': 0.70,
                'cost': 0.60
            }
        }

        # 性能指标映射
        self.performance_mapping = {
            '能量密度': 'energy_density',
            '功率密度': 'power_density',
            '循环寿命': 'cycle_life',
            '安全性': 'safety',
            '成本': 'cost',
            '工作温度': 'operating_temperature',
            '能量效率': 'energy_efficiency'
        }

    def evaluate_experiment(self, experiment_data: Dict, results: List[Dict],
                          requirements: Dict) -> Dict[str, Any]:
        """
        评估实验结果

        Args:
            experiment_data: 实验数据
            results: 实验结果列表
            requirements: 用户需求

        Returns:
            评估结果
        """
        try:
            logger.info(f"开始评估实验 {experiment_data.get('id')}")

            # 提取性能指标
            performance_metrics = self._extract_performance_metrics(results)

            # 评估各项性能指标
            metric_evaluations = self._evaluate_individual_metrics(
                performance_metrics, requirements
            )

            # 计算综合评分
            overall_score, overall_evaluation = self._calculate_overall_evaluation(
                metric_evaluations, requirements
            )

            # 分析失败原因（如果不满足要求）
            failure_analysis = None
            if overall_evaluation['meets_requirements'] is False:
                failure_analysis = self._analyze_failure_reasons(
                    metric_evaluations, requirements
                )

            # 生成改进建议
            improvement_suggestions = self._generate_improvement_suggestions(
                metric_evaluations, requirements
            )

            evaluation_result = {
                'experiment_id': experiment_data.get('id'),
                'evaluation_timestamp': self._get_timestamp(),
                'performance_metrics': performance_metrics,
                'metric_evaluations': metric_evaluations,
                'overall_evaluation': overall_evaluation,
                'failure_analysis': failure_analysis,
                'improvement_suggestions': improvement_suggestions,
                'evaluation_summary': {
                    'meets_requirements': overall_evaluation['meets_requirements'],
                    'overall_score': overall_score,
                    'critical_issues': failure_analysis['critical_issues'] if failure_analysis else [],
                    'recommended_action': self._recommend_action(overall_evaluation, failure_analysis)
                }
            }

            logger.info(f"实验评估完成，满足需求: {evaluation_result['evaluation_summary']['meets_requirements']}")
            return evaluation_result

        except Exception as e:
            logger.error(f"评估实验时出错: {str(e)}")
            raise Exception(f"实验评估失败: {str(e)}")

    def _extract_performance_metrics(self, results: List[Dict]) -> Dict[str, float]:
        """从实验结果中提取性能指标"""
        metrics = {}

        for result in results:
            result_type = result.get('result_type', '')
            data = result.get('data', {})

            if result_type == 'performance_curves':
                # 从性能曲线中提取指标
                charge_discharge = data.get('charge_discharge_curve', {})
                if charge_discharge:
                    metrics['energy_density'] = self._calculate_energy_density(charge_discharge)
                    metrics['energy_efficiency'] = charge_discharge.get('metrics', {}).get('efficiency', 95)

                cycle_life = data.get('cycle_life_curve', {})
                if cycle_life:
                    metrics['cycle_life'] = cycle_life.get('metrics', {}).get('capacity_retention_500', 90)

                rate_performance = data.get('rate_performance', {})
                if rate_performance:
                    metrics['power_density'] = self._calculate_power_density(rate_performance)

                impedance = data.get('impedance_spectrum', {})
                if impedance:
                    metrics['internal_resistance'] = impedance.get('parameters', {}).get('charge_transfer_resistance', 50)

            elif result_type == 'monitoring_data':
                # 从监控数据中提取指标
                temperature_data = data.get('temperature_data', {})
                if temperature_data:
                    temp_stats = temperature_data.get('statistics', {})
                    metrics['operating_temperature'] = temp_stats.get('avg_temperature', 25)
                    metrics['temperature_stability'] = temp_stats.get('temperature_stability', 1.0)

                voltage_data = data.get('voltage_data', {})
                if voltage_data:
                    voltage_stats = voltage_data.get('statistics', {})
                    metrics['voltage_stability'] = voltage_stats.get('voltage_stability', 0.1)

                resistance_data = data.get('resistance_data', {})
                if resistance_data:
                    resistance_stats = resistance_data.get('statistics', {})
                    metrics['resistance_growth'] = resistance_stats.get('resistance_growth', 5)

        # 填充默认值
        default_values = {
            'energy_density': 150,  # Wh/kg
            'power_density': 1000,  # W/kg
            'cycle_life': 500,  # cycles
            'safety': 0.8,  # score 0-1
            'cost': 0.7,  # score 0-1 (1=低成本)
            'energy_efficiency': 95,  # %
            'operating_temperature': 25,  # °C
            'temperature_stability': 1.0,  # °C
            'voltage_stability': 0.1,  # V
            'internal_resistance': 50,  # mΩ
            'resistance_growth': 5  # mΩ
        }

        for metric, default_value in default_values.items():
            if metric not in metrics:
                metrics[metric] = default_value

        return metrics

    def _calculate_energy_density(self, charge_discharge_curve: Dict) -> float:
        """计算能量密度"""
        metrics = charge_discharge_curve.get('metrics', {})
        discharge_capacity = metrics.get('discharge_capacity', 145)  # mAh/g
        avg_voltage = metrics.get('average_discharge_voltage', 3.6)  # V

        # 能量密度 = 容量 × 平均电压 (Wh/kg)
        energy_density = (discharge_capacity * avg_voltage) / 1000
        return energy_density

    def _calculate_power_density(self, rate_performance: Dict) -> float:
        """计算功率密度"""
        metrics = rate_performance.get('metrics', {})
        capacity_1c = metrics.get('capacity_1C', 138)  # mAh/g
        capacity_5c = metrics.get('capacity_5C', 115)  # mAh/g

        # 简化的功率密度计算
        avg_voltage = 3.6  # V
        power_density_1c = (capacity_1c * avg_voltage * 1) / 1000  # kW/kg
        power_density_5c = (capacity_5c * avg_voltage * 5) / 1000  # kW/kg

        # 取平均值作为功率密度指标
        power_density = (power_density_1c + power_density_5c) / 2 * 1000  # W/kg
        return power_density

    def _evaluate_individual_metrics(self, performance_metrics: Dict,
                                   requirements: Dict) -> Dict[str, Dict]:
        """评估各项性能指标"""
        metric_evaluations = {}

        # 获取性能需求
        performance_reqs = requirements.get('performance_requirements', {})

        for chinese_name, target_data in performance_reqs.items():
            metric_name = self.performance_mapping.get(chinese_name)
            if not metric_name:
                continue

            target_value = target_data.get('target_value', 0)
            actual_value = performance_metrics.get(metric_name, 0)

            # 计算达成率
            achievement_rate = actual_value / target_value if target_value > 0 else 0

            # 确定评估等级
            if achievement_rate >= 0.95:
                grade = 'excellent'
            elif achievement_rate >= 0.85:
                grade = 'good'
            elif achievement_rate >= 0.70:
                grade = 'acceptable'
            else:
                grade = 'poor'

            # 判断是否满足要求
            meets_requirement = achievement_rate >= 0.85  # 85%阈值

            metric_evaluations[metric_name] = {
                'chinese_name': chinese_name,
                'target_value': target_value,
                'actual_value': actual_value,
                'achievement_rate': achievement_rate,
                'grade': grade,
                'meets_requirement': meets_requirement,
                'unit': target_data.get('unit', ''),
                'weight': self.evaluation_weights.get(metric_name, 0.1)
            }

        # 评估没有明确要求的指标
        optional_metrics = ['safety', 'cost', 'energy_efficiency']
        for metric in optional_metrics:
            if metric not in metric_evaluations:
                actual_value = performance_metrics.get(metric, 0)

                # 基于行业标准评估
                if metric == 'safety':
                    target_value = 0.9  # 安全评分目标
                elif metric == 'cost':
                    target_value = 0.8  # 成本评分目标
                elif metric == 'energy_efficiency':
                    target_value = 95  # 效率目标

                achievement_rate = min(actual_value / target_value, 1.0)
                meets_requirement = achievement_rate >= 0.8

                metric_evaluations[metric] = {
                    'chinese_name': metric,
                    'target_value': target_value,
                    'actual_value': actual_value,
                    'achievement_rate': achievement_rate,
                    'grade': 'good' if meets_requirement else 'acceptable',
                    'meets_requirement': meets_requirement,
                    'weight': self.evaluation_weights.get(metric, 0.1)
                }

        return metric_evaluations

    def _calculate_overall_evaluation(self, metric_evaluations: Dict,
                                    requirements: Dict) -> Tuple[float, Dict]:
        """计算综合评估"""
        total_weighted_score = 0
        total_weight = 0
        critical_failures = []

        for metric_name, evaluation in metric_evaluations.items():
            weight = evaluation['weight']
            achievement_rate = evaluation['achievement_rate']
            meets_requirement = evaluation['meets_requirement']

            # 关键指标检查
            if metric_name in ['energy_density', 'cycle_life', 'safety'] and not meets_requirement:
                critical_failures.append(metric_name)

            total_weighted_score += achievement_rate * weight
            total_weight += weight

        overall_score = total_weighted_score / total_weight if total_weight > 0 else 0

        # 确定是否满足总体要求
        meets_requirements = (
            len(critical_failures) == 0 and  # 没有关键失败
            overall_score >= 0.85 and  # 综合评分达到85%
            len([e for e in metric_evaluations.values() if not e['meets_requirement']]) <= 1  # 最多一个指标不满足
        )

        # 确定评估等级
        if overall_score >= 0.95:
            overall_grade = 'excellent'
        elif overall_score >= 0.85:
            overall_grade = 'good'
        elif overall_score >= 0.70:
            overall_grade = 'acceptable'
        else:
            overall_grade = 'poor'

        overall_evaluation = {
            'overall_score': overall_score,
            'overall_grade': overall_grade,
            'meets_requirements': meets_requirements,
            'critical_failures': critical_failures,
            'metrics_summary': {
                'total_metrics': len(metric_evaluations),
                'metrics_meeting_requirements': len([e for e in metric_evaluations.values() if e['meets_requirement']]),
                'critical_metrics_failing': len(critical_failures)
            }
        }

        return overall_score, overall_evaluation

    def _analyze_failure_reasons(self, metric_evaluations: Dict,
                               requirements: Dict) -> Dict[str, Any]:
        """分析失败原因"""
        failing_metrics = [name for name, eval in metric_evaluations.items() if not eval['meets_requirement']]
        critical_failures = [name for name in failing_metrics if name in ['energy_density', 'cycle_life', 'safety']]

        failure_analysis = {
            'critical_issues': critical_failures,
            'all_failing_metrics': failing_metrics,
            'root_cause_analysis': {},
            'impact_assessment': {},
            'priority_actions': []
        }

        # 分析每个失败指标的原因
        for metric in failing_metrics:
            evaluation = metric_evaluations[metric]
            actual_value = evaluation['actual_value']
            target_value = evaluation['target_value']
            shortfall = target_value - actual_value

            # 推断可能的原因
            possible_causes = self._infer_possible_causes(metric, shortfall, actual_value)

            failure_analysis['root_cause_analysis'][metric] = {
                'shortfall': shortfall,
                'percentage_shortfall': (shortfall / target_value) * 100,
                'possible_causes': possible_causes,
                'severity': 'critical' if metric in critical_failures else 'moderate'
            }

        # 影响评估
        for metric in critical_failures:
            impact = self._assess_impact(metric, metric_evaluations)
            failure_analysis['impact_assessment'][metric] = impact

        # 优先级行动建议
        failure_analysis['priority_actions'] = self._generate_priority_actions(failure_analysis)

        return failure_analysis

    def _infer_possible_causes(self, metric: str, shortfall: float, actual_value: float) -> List[str]:
        """推断失败的可能原因"""
        causes = []

        if metric == 'energy_density':
            if actual_value < 120:
                causes.extend(['电解液电导率过低', '活性物质利用率低', '界面阻抗过高'])
            else:
                causes.extend(['溶剂比例不理想', '盐浓度需要优化', '添加剂效果不佳'])

        elif metric == 'power_density':
            if actual_value < 800:
                causes.extend(['电解液离子传导慢', '界面阻抗高', '电极极化严重'])
            else:
                causes.extend(['溶剂粘度偏高', '盐浓度偏低', '需要导电添加剂'])

        elif metric == 'cycle_life':
            if actual_value < 300:
                causes.extend(['SEI膜不稳定', '电解液分解严重', '过渡金属溶出'])
            else:
                causes.extend(['界面反应持续', '添加剂不足', '电解液纯度问题'])

        elif metric == 'safety':
            if actual_value < 0.7:
                causes.extend(['热稳定性差', '氧化电位低', '副反应多'])
            else:
                causes.extend(['溶剂热稳定性一般', '需要阻燃添加剂'])

        elif metric == 'cost':
            if actual_value < 0.6:
                causes.extend(['使用昂贵溶剂', '添加剂成本高', '工艺复杂'])
            else:
                causes.extend(['部分材料成本偏高', '可考虑替代材料'])

        return causes

    def _assess_impact(self, metric: str, metric_evaluations: Dict) -> Dict:
        """评估失败的影响"""
        impact_levels = {
            'energy_density': 'high',
            'power_density': 'medium',
            'cycle_life': 'high',
            'safety': 'critical',
            'cost': 'medium'
        }

        affected_applications = {
            'energy_density': ['蓄能', '动力'],
            'power_density': ['动力', '3C'],
            'cycle_life': ['蓄能', '动力'],
            'safety': ['所有应用'],
            'cost': ['3C', '蓄能']
        }

        return {
            'impact_level': impact_levels.get(metric, 'medium'),
            'affected_applications': affected_applications.get(metric, ['部分应用']),
            'business_impact': self._assess_business_impact(metric),
            'technical_challenges': self._identify_technical_challenges(metric)
        }

    def _assess_business_impact(self, metric: str) -> str:
        """评估商业影响"""
        impact_mapping = {
            'energy_density': '影响产品竞争力和市场接受度',
            'power_density': '影响高端应用市场准入',
            'cycle_life': '影响产品寿命和总成本',
            'safety': '影响产品安全认证和市场准入',
            'cost': '影响产品定价和市场竞争力'
        }
        return impact_mapping.get(metric, '影响产品整体性能')

    def _identify_technical_challenges(self, metric: str) -> List[str]:
        """识别技术挑战"""
        challenges = {
            'energy_density': ['材料选择', '界面优化', '工艺控制'],
            'power_density': ['离子传导', '电极设计', '界面工程'],
            'cycle_life': ['稳定性控制', '杂质管理', '界面保护'],
            'safety': ['热稳定性', '化学稳定性', '系统集成'],
            'cost': ['材料成本', '工艺简化', '规模化生产']
        }
        return challenges.get(metric, ['配方优化', '工艺改进'])

    def _generate_priority_actions(self, failure_analysis: Dict) -> List[Dict]:
        """生成优先级行动建议"""
        actions = []

        critical_issues = failure_analysis['critical_issues']
        all_failing = failure_analysis['all_failing_metrics']

        # 关键问题优先
        for metric in critical_issues:
            actions.append({
                'priority': 'high',
                'metric': metric,
                'action': self._get_priority_action_for_metric(metric),
                'timeline': 'immediate',
                'expected_improvement': '15-30%'
            })

        # 非关键问题
        for metric in all_failing:
            if metric not in critical_issues:
                actions.append({
                    'priority': 'medium',
                    'metric': metric,
                    'action': self._get_priority_action_for_metric(metric),
                    'timeline': 'next_iteration',
                    'expected_improvement': '10-20%'
                })

        return actions

    def _get_priority_action_for_metric(self, metric: str) -> str:
        """获取特定指标的优先行动"""
        action_mapping = {
            'energy_density': '优化溶剂体系和盐浓度，提高电导率和电化学窗口',
            'power_density': '降低电解液粘度，添加导电添加剂，优化界面',
            'cycle_life': '增加SEI成膜添加剂，提高电解液纯度和稳定性',
            'safety': '使用高沸点溶剂，添加阻燃剂，提高热稳定性',
            'cost': '替换昂贵组分，优化配方比例，简化工艺流程'
        }
        return action_mapping.get(metric, '优化配方参数')

    def _generate_improvement_suggestions(self, metric_evaluations: Dict,
                                        requirements: Dict) -> List[Dict]:
        """生成改进建议"""
        suggestions = []

        # 基于评估结果生成具体建议
        for metric_name, evaluation in metric_evaluations.items():
            if not evaluation['meets_requirement']:
                suggestion = self._create_improvement_suggestion(metric_name, evaluation)
                suggestions.append(suggestion)

        # 按优先级排序
        suggestions.sort(key=lambda x: x['priority_score'], reverse=True)

        return suggestions

    def _create_improvement_suggestion(self, metric_name: str, evaluation: Dict) -> Dict:
        """为特定指标创建改进建议"""
        chinese_name = evaluation['chinese_name']
        achievement_rate = evaluation['achievement_rate']

        suggestion = {
            'metric': metric_name,
            'chinese_name': chinese_name,
            'current_performance': evaluation['actual_value'],
            'target_performance': evaluation['target_value'],
            'achievement_rate': achievement_rate,
            'improvement_needed': evaluation['target_value'] - evaluation['actual_value'],
            'priority_score': evaluation['weight'] * (1 - achievement_rate),
            'suggested_actions': self._get_suggested_actions(metric_name, achievement_rate),
            'expected_timeline': self._estimate_improvement_timeline(metric_name, achievement_rate),
            'success_probability': self._estimate_success_probability(metric_name, achievement_rate)
        }

        return suggestion

    def _get_suggested_actions(self, metric_name: str, achievement_rate: float) -> List[str]:
        """获取建议的行动"""
        if achievement_rate < 0.5:
            # 严重不足，需要重大改进
            return [
                '重新设计配方体系',
                '考虑替换主要组分',
                '全面优化工艺参数'
            ]
        elif achievement_rate < 0.8:
            # 中等不足，需要针对性改进
            return [
                '调整关键组分比例',
                '添加功能性添加剂',
                '优化工艺条件'
            ]
        else:
            # 轻微不足，需要微调
            return [
                '微调组分浓度',
                '优化添加剂组合',
                '精细调控工艺参数'
            ]

    def _estimate_improvement_timeline(self, metric_name: str, achievement_rate: float) -> str:
        """估算改进时间线"""
        if achievement_rate < 0.5:
            return '4-6 weeks'
        elif achievement_rate < 0.8:
            return '2-4 weeks'
        else:
            return '1-2 weeks'

    def _estimate_success_probability(self, metric_name: str, achievement_rate: float) -> float:
        """估算成功概率"""
        base_probability = {
            'energy_density': 0.7,
            'power_density': 0.8,
            'cycle_life': 0.6,
            'safety': 0.9,
            'cost': 0.8
        }

        base_prob = base_probability.get(metric_name, 0.7)
        # 根据当前达成率调整概率
        adjusted_prob = base_prob * (0.5 + achievement_rate * 0.5)

        return min(0.95, adjusted_prob)

    def _recommend_action(self, overall_evaluation: Dict, failure_analysis: Dict) -> str:
        """推荐下一步行动"""
        meets_requirements = overall_evaluation['meets_requirements']
        overall_score = overall_evaluation['overall_score']
        critical_failures = overall_evaluation['critical_failures']

        if meets_requirements and overall_score >= 0.9:
            return 'proceed_to_optimization'  # 进行贝叶斯优化
        elif meets_requirements and overall_score >= 0.85:
            return 'minor_optimization'  # 小幅优化
        elif critical_failures:
            return 'redesign_required'  # 需要重新设计
        elif overall_score >= 0.7:
            return 'targeted_improvement'  # 针对性改进
        else:
            return 'major_redesign'  # 重大重新设计

    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()