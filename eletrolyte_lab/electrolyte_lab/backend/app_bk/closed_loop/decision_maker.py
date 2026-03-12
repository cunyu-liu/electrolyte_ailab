import random
import numpy as np
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class DecisionMaker:
    """决策制定器 - 根据评估结果决定下一步行动"""

    def __init__(self):
        # 决策策略配置
        self.decision_strategies = {
            'conservative': {  # 保守策略
                'optimization_threshold': 0.9,
                'redesign_threshold': 0.7,
                'max_iterations': 5,
                'success_probability_weight': 0.4
            },
            'balanced': {  # 平衡策略
                'optimization_threshold': 0.85,
                'redesign_threshold': 0.75,
                'max_iterations': 8,
                'success_probability_weight': 0.3
            },
            'aggressive': {  # 激进策略
                'optimization_threshold': 0.8,
                'redesign_threshold': 0.7,
                'max_iterations': 10,
                'success_probability_weight': 0.2
            }
        }

        # 默认使用平衡策略
        self.current_strategy = 'balanced'

        # 决策历史
        self.decision_history = []

    def decide_next_step(self, experiment_data: Dict, evaluation_result: Dict,
                        last_results: Dict) -> Dict[str, Any]:
        """
        决定下一步行动

        Args:
            experiment_data: 实验数据
            evaluation_result: 评估结果
            last_results: 上一次结果

        Returns:
            决策结果
        """
        try:
            logger.info(f"开始决策，实验ID: {experiment_data.get('id')}")

            # 获取策略参数
            strategy_params = self.decision_strategies[self.current_strategy]

            # 提取关键信息
            meets_requirements = evaluation_result.get('evaluation_summary', {}).get('meets_requirements', False)
            overall_score = evaluation_result.get('overall_evaluation', {}).get('overall_score', 0)
            critical_failures = evaluation_result.get('overall_evaluation', {}).get('critical_failures', [])
            iteration_count = experiment_data.get('iteration_count', 1)

            # 主要决策逻辑
            decision = self._make_primary_decision(
                meets_requirements, overall_score, critical_failures,
                iteration_count, strategy_params
            )

            # 生成具体行动计划
            action_plan = self._generate_action_plan(decision, evaluation_result, experiment_data)

            # 评估决策风险
            risk_assessment = self._assess_decision_risk(decision, evaluation_result)

            # 预测预期结果
            expected_outcome = self._predict_expected_outcome(decision, evaluation_result)

            decision_result = {
                'experiment_id': experiment_data.get('id'),
                'decision_timestamp': self._get_timestamp(),
                'strategy_used': self.current_strategy,
                'primary_decision': decision,
                'action_plan': action_plan,
                'risk_assessment': risk_assessment,
                'expected_outcome': expected_outcome,
                'decision_context': {
                    'meets_requirements': meets_requirements,
                    'overall_score': overall_score,
                    'critical_failures': critical_failures,
                    'iteration_count': iteration_count,
                    'success_probability': self._calculate_success_probability(decision, evaluation_result)
                },
                'next_experiment_config': self._prepare_next_experiment_config(decision, experiment_data, evaluation_result)
            }

            # 记录决策历史
            self.decision_history.append({
                'timestamp': decision_result['decision_timestamp'],
                'experiment_id': experiment_data.get('id'),
                'decision': decision,
                'success_probability': decision_result['decision_context']['success_probability']
            })

            logger.info(f"决策完成，选择: {decision['action_type']}")
            return decision_result

        except Exception as e:
            logger.error(f"决策时出错: {str(e)}")
            raise Exception(f"决策失败: {str(e)}")

    def _make_primary_decision(self, meets_requirements: bool, overall_score: float,
                              critical_failures: List[str], iteration_count: int,
                              strategy_params: Dict) -> Dict[str, Any]:
        """做出主要决策"""
        decision = {
            'action_type': None,
            'reasoning': [],
            'confidence': 0.0,
            'priority': 'normal'
        }

        # 检查是否达到最大迭代次数
        if iteration_count >= strategy_params['max_iterations']:
            decision['action_type'] = 'terminate'
            decision['reasoning'].append(f'已达到最大迭代次数 {strategy_params["max_iterations"]}')
            decision['confidence'] = 0.9
            decision['priority'] = 'high'
            return decision

        # 情况1: 满足所有要求，且性能优秀
        if meets_requirements and overall_score >= strategy_params['optimization_threshold']:
            decision['action_type'] = 'bayesian_optimization'
            decision['reasoning'].append(f'性能优秀 (评分: {overall_score:.3f})，进行贝叶斯优化')
            decision['confidence'] = 0.85
            decision['priority'] = 'normal'

        # 情况2: 基本满足要求，但有改进空间
        elif meets_requirements and overall_score >= 0.8:
            decision['action_type'] = 'targeted_optimization'
            decision['reasoning'].append(f'基本满足要求 (评分: {overall_score:.3f})，进行针对性优化')
            decision['confidence'] = 0.75
            decision['priority'] = 'normal'

        # 情况3: 有关键失败，需要重新设计
        elif critical_failures:
            decision['action_type'] = 'redesign'
            decision['reasoning'].append(f'存在关键失败: {", ".join(critical_failures)}')
            decision['confidence'] = 0.9
            decision['priority'] = 'high'

        # 情况4: 性能较差，但有关键信息可利用
        elif overall_score >= strategy_params['redesign_threshold']:
            decision['action_type'] = 'iterative_improvement'
            decision['reasoning'].append(f'性能一般 (评分: {overall_score:.3f})，进行迭代改进')
            decision['confidence'] = 0.7
            decision['priority'] = 'normal'

        # 情况5: 性能很差，需要重大重新设计
        else:
            decision['action_type'] = 'major_redesign'
            decision['reasoning'].append(f'性能较差 (评分: {overall_score:.3f})，需要重大重新设计')
            decision['confidence'] = 0.8
            decision['priority'] = 'high'

        return decision

    def _generate_action_plan(self, decision: Dict, evaluation_result: Dict,
                            experiment_data: Dict) -> Dict[str, Any]:
        """生成具体行动计划"""
        action_type = decision['action_type']
        action_plan = {
            'action_type': action_type,
            'steps': [],
            'estimated_duration': self._estimate_action_duration(action_type),
            'required_resources': self._identify_required_resources(action_type),
            'success_criteria': self._define_success_criteria(action_type),
            'monitoring_points': self._define_monitoring_points(action_type)
        }

        if action_type == 'bayesian_optimization':
            action_plan['steps'] = [
                '收集当前实验数据',
                '初始化贝叶斯优化模型',
                '生成候选配方空间',
                '评估和筛选候选配方',
                '选择最优配方进行下一轮实验'
            ]
            action_plan['optimization_target'] = 'all'
            action_plan['expected_improvement'] = '5-15%'

        elif action_type == 'targeted_optimization':
            action_plan['steps'] = [
                '识别性能瓶颈指标',
                '制定针对性优化策略',
                '调整关键配方参数',
                '验证优化效果'
            ]
            action_plan['optimization_focus'] = self._identify_optimization_focus(evaluation_result)
            action_plan['expected_improvement'] = '3-10%'

        elif action_type == 'redesign':
            action_plan['steps'] = [
                '分析失败原因',
                '确定重新设计策略',
                '选择新的组分体系',
                '验证新配方的可行性',
                '生成新实验配方'
            ]
            action_plan['redesign_strategy'] = self._determine_redesign_strategy(evaluation_result)
            action_plan['expected_improvement'] = '15-30%'

        elif action_type == 'iterative_improvement':
            action_plan['steps'] = [
                '分析可改进的方面',
                '进行小幅配方调整',
                '测试改进效果',
                '决定是否继续迭代'
            ]
            action_plan['improvement_areas'] = self._identify_improvement_areas(evaluation_result)
            action_plan['expected_improvement'] = '2-8%'

        elif action_type == 'major_redesign':
            action_plan['steps'] = [
                '全面分析失败原因',
                '重新考虑配方体系',
                '可能更换主要组分',
                '制定全新的实验方案',
                '验证新方案的可行性'
            ]
            action_plan['redesign_scope'] = 'complete'
            action_plan['expected_improvement'] = '20-50%'

        elif action_type == 'terminate':
            action_plan['steps'] = [
                '总结所有实验结果',
                '生成最终报告',
                '确定最佳配方',
                '提供后续建议'
            ]
            action_plan['finalization_type'] = 'completion'

        return action_plan

    def _assess_decision_risk(self, decision: Dict, evaluation_result: Dict) -> Dict[str, Any]:
        """评估决策风险"""
        action_type = decision['action_type']
        overall_score = evaluation_result.get('overall_evaluation', {}).get('overall_score', 0)

        # 风险等级定义
        risk_levels = {
            'bayesian_optimization': 'low',
            'targeted_optimization': 'low',
            'iterative_improvement': 'medium',
            'redesign': 'medium',
            'major_redesign': 'high',
            'terminate': 'none'
        }

        risk_level = risk_levels.get(action_type, 'medium')

        # 计算风险概率
        risk_probability = self._calculate_risk_probability(action_type, overall_score)

        # 识别潜在风险
        potential_risks = self._identify_potential_risks(action_type, evaluation_result)

        # 风险缓解措施
        mitigation_strategies = self._suggest_mitigation_strategies(action_type, potential_risks)

        risk_assessment = {
            'risk_level': risk_level,
            'risk_probability': risk_probability,
            'potential_risks': potential_risks,
            'mitigation_strategies': mitigation_strategies,
            'risk_acceptance_criteria': self._define_risk_acceptance_criteria(action_type)
        }

        return risk_assessment

    def _predict_expected_outcome(self, decision: Dict, evaluation_result: Dict) -> Dict[str, Any]:
        """预测预期结果"""
        action_type = decision['action_type']
        current_score = evaluation_result.get('overall_evaluation', {}).get('overall_score', 0)

        # 预期改进幅度
        improvement_ranges = {
            'bayesian_optimization': (0.05, 0.15),
            'targeted_optimization': (0.03, 0.10),
            'redesign': (0.15, 0.30),
            'iterative_improvement': (0.02, 0.08),
            'major_redesign': (0.20, 0.50),
            'terminate': (0, 0)
        }

        min_improvement, max_improvement = improvement_ranges.get(action_type, (0, 0.1))

        # 预期成功概率
        success_probabilities = {
            'bayesian_optimization': 0.75,
            'targeted_optimization': 0.80,
            'redesign': 0.65,
            'iterative_improvement': 0.70,
            'major_redesign': 0.55,
            'terminate': 1.0
        }

        success_probability = success_probabilities.get(action_type, 0.7)

        # 预测新评分范围
        expected_min_score = current_score + min_improvement
        expected_max_score = current_score + max_improvement
        expected_most_likely = (expected_min_score + expected_max_score) / 2

        # 预测时间需求
        time_requirements = {
            'bayesian_optimization': '2-3 days',
            'targeted_optimization': '1-2 days',
            'redesign': '3-5 days',
            'iterative_improvement': '1-2 days',
            'major_redesign': '5-7 days',
            'terminate': '1 day'
        }

        expected_outcome = {
            'expected_score_range': {
                'min': min(expected_min_score, 1.0),
                'max': min(expected_max_score, 1.0),
                'most_likely': min(expected_most_likely, 1.0)
            },
            'success_probability': success_probability,
            'expected_time_requirement': time_requirements.get(action_type, '2-3 days'),
            'resource_requirements': self._predict_resource_requirements(action_type),
            'potential_benefits': self._identify_potential_benefits(action_type),
            'confidence_in_prediction': decision.get('confidence', 0.7)
        }

        return expected_outcome

    def _prepare_next_experiment_config(self, decision: Dict, experiment_data: Dict,
                                      evaluation_result: Dict) -> Dict[str, Any]:
        """准备下一个实验配置"""
        action_type = decision['action_type']
        config = {
            'experiment_type': action_type,
            'base_formula_id': experiment_data.get('formula_id'),
            'iteration_count': experiment_data.get('iteration_count', 1) + 1,
            'priority': decision.get('priority', 'normal'),
            'special_instructions': []
        }

        if action_type in ['bayesian_optimization', 'targeted_optimization']:
            config['optimization_parameters'] = {
                'target_metrics': self._get_target_metrics(evaluation_result),
                'optimization_method': 'bayesian' if 'bayesian' in action_type else 'gradient',
                'constraint_handling': 'active'
            }

        elif action_type in ['redesign', 'major_redesign']:
            config['redesign_parameters'] = {
                'failed_components': self._identify_failed_components(evaluation_result),
                'replacement_strategy': self._get_replacement_strategy(action_type),
                'design_constraints': self._get_design_constraints()
            }

        elif action_type == 'terminate':
            config['finalization_parameters'] = {
                'include_all_results': True,
                'generate_comprehensive_report': True,
                'provide_recommendations': True
            }

        return config

    def _calculate_success_probability(self, decision: Dict, evaluation_result: Dict) -> float:
        """计算成功概率"""
        action_type = decision['action_type']
        base_probability = {
            'bayesian_optimization': 0.75,
            'targeted_optimization': 0.80,
            'redesign': 0.65,
            'iterative_improvement': 0.70,
            'major_redesign': 0.55,
            'terminate': 1.0
        }

        base_prob = base_probability.get(action_type, 0.7)

        # 根据当前评分调整
        overall_score = evaluation_result.get('overall_evaluation', {}).get('overall_score', 0)
        score_adjustment = (overall_score - 0.5) * 0.3  # 评分越高，成功概率越高

        # 根据决策置信度调整
        confidence_adjustment = (decision.get('confidence', 0.7) - 0.5) * 0.2

        final_probability = base_prob + score_adjustment + confidence_adjustment
        return max(0.1, min(0.95, final_probability))

    def _estimate_action_duration(self, action_type: str) -> str:
        """估算行动持续时间"""
        durations = {
            'bayesian_optimization': '2-3 days',
            'targeted_optimization': '1-2 days',
            'redesign': '3-5 days',
            'iterative_improvement': '1-2 days',
            'major_redesign': '5-7 days',
            'terminate': '1 day'
        }
        return durations.get(action_type, '2-3 days')

    def _identify_required_resources(self, action_type: str) -> List[str]:
        """识别所需资源"""
        resources = {
            'bayesian_optimization': ['计算资源', '数据库访问', '优化算法'],
            'targeted_optimization': ['实验材料', '测试设备', '分析工具'],
            'redesign': ['研发团队', '材料库', '测试设备'],
            'iterative_improvement': ['实验材料', '快速测试设备'],
            'major_redesign': ['跨学科团队', '先进设备', '额外预算'],
            'terminate': ['数据分析工具', '报告生成工具']
        }
        return resources.get(action_type, ['基础资源'])

    def _define_success_criteria(self, action_type: str) -> List[str]:
        """定义成功标准"""
        criteria = {
            'bayesian_optimization': [
                '评分提升 > 5%',
                '关键指标达到目标',
                '稳定性保持或改善'
            ],
            'targeted_optimization': [
                '瓶颈指标改善 > 10%',
                '其他指标不下降',
                '实验可重复性良好'
            ],
            'redesign': [
                '关键失败指标得到解决',
                '整体性能提升 > 15%',
                '新的配方体系可行'
            ],
            'iterative_improvement': [
                '性能有所提升',
                '没有引入新的问题',
                '改进方向正确'
            ],
            'major_redesign': [
                '根本性解决问题',
                '性能显著改善',
                '新体系具有可行性'
            ],
            'terminate': [
                '完成所有实验目标',
                '确定最佳配方',
                '提供完整的技术文档'
            ]
        }
        return criteria.get(action_type, ['基本目标达成'])

    def _define_monitoring_points(self, action_type: str) -> List[str]:
        """定义监控要点"""
        monitoring_points = {
            'bayesian_optimization': [
                '优化收敛情况',
                '预测准确性',
                '计算资源使用'
            ],
            'targeted_optimization': [
                '关键指标变化',
                '副作用监测',
                '实验稳定性'
            ],
            'redesign': [
                '新组分相容性',
                '性能指标变化',
                '潜在风险评估'
            ],
            'iterative_improvement': [
                '改进趋势',
                '累积效果',
                '是否需要转向'
            ],
            'major_redesign': [
                '整体系统表现',
                '关键技术突破',
                '可行性验证'
            ],
            'terminate': [
                '结果完整性',
                '结论准确性',
                '文档质量'
            ]
        }
        return monitoring_points.get(action_type, ['基本监控'])

    def _identify_optimization_focus(self, evaluation_result: Dict) -> List[str]:
        """识别优化重点"""
        failing_metrics = []
        metric_evaluations = evaluation_result.get('metric_evaluations', {})

        for metric_name, evaluation in metric_evaluations.items():
            if not evaluation['meets_requirement']:
                failing_metrics.append(evaluation['chinese_name'])

        return failing_metrics if failing_metrics else ['整体性能优化']

    def _determine_redesign_strategy(self, evaluation_result: Dict) -> str:
        """确定重新设计策略"""
        critical_failures = evaluation_result.get('overall_evaluation', {}).get('critical_failures', [])

        if 'energy_density' in critical_failures and 'cycle_life' in critical_failures:
            return 'complete_system_redesign'
        elif len(critical_failures) == 1:
            return 'targeted_component_redesign'
        else:
            return 'comprehensive_optimization'

    def _identify_improvement_areas(self, evaluation_result: Dict) -> List[str]:
        """识别改进领域"""
        areas = []
        metric_evaluations = evaluation_result.get('metric_evaluations', {})

        for metric_name, evaluation in metric_evaluations.items():
            achievement_rate = evaluation['achievement_rate']
            if achievement_rate < 0.9:
                areas.append(evaluation['chinese_name'])

        return areas if areas else ['微调优化']

    def _calculate_risk_probability(self, action_type: str, overall_score: float) -> float:
        """计算风险概率"""
        base_risks = {
            'bayesian_optimization': 0.2,
            'targeted_optimization': 0.15,
            'redesign': 0.35,
            'iterative_improvement': 0.25,
            'major_redesign': 0.45,
            'terminate': 0.05
        }

        base_risk = base_risks.get(action_type, 0.25)

        # 根据当前评分调整风险
        score_adjustment = (0.8 - overall_score) * 0.3  # 评分越低，风险越高

        final_risk = base_risk + score_adjustment
        return max(0.05, min(0.8, final_risk))

    def _identify_potential_risks(self, action_type: str, evaluation_result: Dict) -> List[str]:
        """识别潜在风险"""
        risk_mapping = {
            'bayesian_optimization': [
                '模型预测不准确',
                '优化收敛缓慢',
                '局部最优解'
            ],
            'targeted_optimization': [
                '改进效果不明显',
                '引入新的问题',
                '优化范围过窄'
            ],
            'redesign': [
                '新方案不可行',
                '性能反而下降',
                '时间和成本超支'
            ],
            'iterative_improvement': [
                '改进效果有限',
                '陷入局部最优',
                '收敛速度慢'
            ],
            'major_redesign': [
                '技术风险高',
                '资源需求大',
                '失败概率高'
            ],
            'terminate': [
                '结论不完整',
                '错失改进机会',
                '数据解释偏差'
            ]
        }
        return risk_mapping.get(action_type, ['一般风险'])

    def _suggest_mitigation_strategies(self, action_type: str, risks: List[str]) -> List[str]:
        """建议风险缓解策略"""
        return [
            '设置检查点和里程碑',
            '进行小规模预实验',
            '准备备选方案',
            '加强监控和评估',
            '及时调整策略'
        ]

    def _define_risk_acceptance_criteria(self, action_type: str) -> Dict[str, Any]:
        """定义风险接受标准"""
        return {
            'max_acceptable_risk': 0.4,
            'required_success_probability': 0.6,
            'max_resource_exposure': 'moderate',
            'time_limit': 'reasonable'
        }

    def _get_target_metrics(self, evaluation_result: Dict) -> List[str]:
        """获取目标指标"""
        target_metrics = []
        metric_evaluations = evaluation_result.get('metric_evaluations', {})

        for metric_name, evaluation in metric_evaluations.items():
            if not evaluation['meets_requirement']:
                target_metrics.append(metric_name)

        return target_metrics if target_metrics else ['overall_performance']

    def _identify_failed_components(self, evaluation_result: Dict) -> List[str]:
        """识别失败组分"""
        # 基于评估结果推断可能的问题组分
        failure_analysis = evaluation_result.get('failure_analysis', {})
        root_causes = failure_analysis.get('root_cause_analysis', {})

        failed_components = []
        for component, analysis in root_causes.items():
            if analysis['severity'] == 'critical':
                failed_components.append(component)

        return failed_components

    def _get_replacement_strategy(self, action_type: str) -> str:
        """获取替换策略"""
        if action_type == 'major_redesign':
            return 'complete_replacement'
        else:
            return 'selective_replacement'

    def _get_design_constraints(self) -> List[str]:
        """获取设计约束"""
        return [
            '成本控制',
            '工艺可行性',
            '材料可获得性',
            '安全性要求',
            '环保要求'
        ]

    def _predict_resource_requirements(self, action_type: str) -> Dict[str, Any]:
        """预测资源需求"""
        requirements = {
            'bayesian_optimization': {
                'compute_time': '2-4 hours',
                'memory': '8-16 GB',
                'storage': 'minimal'
            },
            'targeted_optimization': {
                'materials': 'standard_set',
                'equipment_time': '4-8 hours',
                'personnel': '1-2 people'
            },
            'redesign': {
                'materials': 'extended_set',
                'equipment_time': '8-16 hours',
                'personnel': '2-3 people',
                'budget_increase': '20-30%'
            },
            'major_redesign': {
                'materials': 'comprehensive_set',
                'equipment_time': '16-32 hours',
                'personnel': '3-5 people',
                'budget_increase': '50-100%'
            }
        }
        return requirements.get(action_type, {'standard_requirements': True})

    def _identify_potential_benefits(self, action_type: str) -> List[str]:
        """识别潜在收益"""
        benefits = {
            'bayesian_optimization': [
                '系统性性能提升',
                '理解参数关系',
                '建立预测模型'
            ],
            'targeted_optimization': [
                '快速解决瓶颈',
                '效率高成本低',
                '风险可控'
            ],
            'redesign': [
                '根本性解决问题',
                '可能实现突破',
                '拓展技术路线'
            ],
            'iterative_improvement': [
                '渐进式改进',
                '风险分散',
                '持续优化'
            ],
            'major_redesign': [
                '技术突破可能',
                '跨越式发展',
                '新知识产权'
            ],
            'terminate': [
                '明确项目成果',
                '资源释放',
                '经验总结'
            ]
        }
        return benefits.get(action_type, ['一般性收益'])

    def get_decision_history(self, experiment_id: Optional[int] = None) -> List[Dict]:
        """获取决策历史"""
        if experiment_id:
            return [d for d in self.decision_history if d['experiment_id'] == experiment_id]
        return self.decision_history

    def set_strategy(self, strategy: str) -> bool:
        """设置决策策略"""
        if strategy in self.decision_strategies:
            self.current_strategy = strategy
            logger.info(f"决策策略已设置为: {strategy}")
            return True
        return False

    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()