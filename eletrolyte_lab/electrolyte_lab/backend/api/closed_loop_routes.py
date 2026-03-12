from flask import Blueprint, request, jsonify
from app_bk.closed_loop.evaluator import ExperimentEvaluator
from app_bk.closed_loop.decision_maker import DecisionMaker
from app_bk.closed_loop.bayesian_optimizer import ElectrolyteBayesianOptimizer
from extensions import db
from models import Experiment, ExperimentResult
from typing import Dict, List, Any
import logging

# 创建蓝图
closed_loop_bp = Blueprint('closed_loop', __name__)
logger = logging.getLogger(__name__)

# 初始化模块组件
evaluator = ExperimentEvaluator()
decision_maker = DecisionMaker()
bayesian_optimizer = ElectrolyteBayesianOptimizer()

@closed_loop_bp.route('/evaluate', methods=['POST'])
def evaluate_experiment():
    """评估实验结果"""
    try:
        data = request.get_json()
        experiment_id = data.get('experiment_id')
        requirements = data.get('requirements', {})

        if not experiment_id:
            return jsonify({'success': False, 'error': '缺少实验ID'}), 400

        # 获取实验和结果
        experiment = Experiment.query.get_or_404(experiment_id)
        results = ExperimentResult.query.filter_by(experiment_id=experiment_id).all()

        if experiment.status.value != 'completed':
            return jsonify({'success': False, 'error': '实验尚未完成，无法评估'}), 400

        if not results:
            return jsonify({'success': False, 'error': '没有找到实验结果'}), 404

        # 执行评估
        evaluation_result = evaluator.evaluate_experiment(
            experiment.to_dict(),
            [result.to_dict() for result in results],
            requirements
        )

        # 保存评估结果（可选）
        # 可以创建一个新的结果记录来保存评估结果

        return jsonify({
            'success': True,
            'evaluation_result': evaluation_result,
            'message': '实验评估完成'
        })

    except Exception as e:
        logger.error(f"评估实验时出错: {str(e)}")
        return jsonify({'success': False, 'error': f'评估失败: {str(e)}'}), 500

@closed_loop_bp.route('/decide', methods=['POST'])
def decide_next_step():
    """决定下一步行动"""
    try:
        data = request.get_json()
        experiment_id = data.get('experiment_id')
        evaluation_result = data.get('evaluation_result', {})
        last_results = data.get('last_results', {})

        if not experiment_id or not evaluation_result:
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400

        # 获取实验信息
        experiment = Experiment.query.get_or_404(experiment_id)

        # 执行决策
        decision = decision_maker.decide_next_step(
            experiment.to_dict(),
            evaluation_result,
            last_results
        )

        return jsonify({
            'success': True,
            'decision': decision,
            'message': '决策完成'
        })

    except Exception as e:
        logger.error(f"决策时出错: {str(e)}")
        return jsonify({'success': False, 'error': f'决策失败: {str(e)}'}), 500

@closed_loop_bp.route('/trigger-redesign', methods=['POST'])
def trigger_redesign():
    """触发重新设计"""
    try:
        data = request.get_json()
        experiment_id = data.get('experiment_id')
        failure_reasons = data.get('failure_reasons', [])
        iteration_count = data.get('iteration_count', 1)

        if not experiment_id:
            return jsonify({'success': False, 'error': '缺少实验ID'}), 400

        # 获取失败的实验信息
        experiment = Experiment.query.get_or_404(experiment_id)
        results = ExperimentResult.query.filter_by(experiment_id=experiment_id).all()

        # 调用AI设计员进行重新设计
        from app_bk.ai_designer.formula_generator import FormulaGenerator
        formula_generator = FormulaGenerator()

        new_formula_spec = formula_generator.redesign_formula(
            experiment.to_dict(),
            [result.to_dict() for result in results],
            failure_reasons,
            iteration_count
        )

        return jsonify({
            'success': True,
            'new_formula_spec': new_formula_spec,
            'message': '重新设计完成'
        })

    except Exception as e:
        logger.error(f"触发重新设计时出错: {str(e)}")
        return jsonify({'success': False, 'error': f'重新设计失败: {str(e)}'}), 500

@closed_loop_bp.route('/run-bayesian-optimization', methods=['POST'])
def run_bayesian_optimization():
    """运行贝叶斯优化"""
    try:
        data = request.get_json()
        experiment_id = data.get('experiment_id')
        optimization_target = data.get('optimization_target', 'all')
        iteration_count = data.get('iteration_count', 1)
        weights = data.get('weights', {'w_ret': 0.5, 'w_cap': 0.4, 'w_imp': 0.1})
        n_candidates = data.get('n_candidates', 5)

        logger.info(f"开始贝叶斯优化: experiment_id={experiment_id}, target={optimization_target}")

        # 如果提供了实验ID，先加载该实验的数据
        if experiment_id:
            try:
                experiment = Experiment.query.get_or_404(experiment_id)
                results = ExperimentResult.query.filter_by(experiment_id=experiment_id).all()

                # 获取用户需求
                user_requirements = experiment.user_requirements or {}

                # 转换实验数据格式
                experiment_data = {
                    'id': str(experiment.id),
                    'formula': {
                        'solvent_ratios': {}
                    },
                    'description': experiment.name if hasattr(experiment, 'name') else f'实验 {experiment.id}'
                }

                # 尝试从实验数据中提取配方信息
                if hasattr(experiment, 'formula') and experiment.formula:
                    if hasattr(experiment.formula, 'components'):
                        # 如果有components字段
                        for i, component in enumerate(experiment.formula.components, 1):
                            if hasattr(component, 'ratio'):
                                experiment_data['formula']['solvent_ratios'][str(i)] = float(component.ratio)
                    elif hasattr(experiment.formula, 'solvent_ratios'):
                        # 如果有solvent_ratios字段
                        experiment_data['formula']['solvent_ratios'] = experiment.formula.solvent_ratios
                    else:
                        # 使用默认的10个溶剂的均匀分布
                        experiment_data['formula']['solvent_ratios'] = {str(i): 0.1 for i in range(1, 11)}
                else:
                    # 如果没有配方信息，使用默认
                    experiment_data['formula']['solvent_ratios'] = {str(i): 0.1 for i in range(1, 11)}

                # 转换结果数据格式
                formatted_results = []
                for result in results:
                    result_dict = result.to_dict()
                    # 标准化指标名称
                    metric_name = result_dict.get('metric_name', 'unknown')
                    value = result_dict.get('value', 0)

                    # 映射常见的指标名称
                    metric_mapping = {
                        'retention_rate': 'retention',
                        'capacity': 'capacity',
                        'impedance': 'impedance',
                        'energy_density': 'retention',  # 可以根据需要调整
                        'power_density': 'capacity',    # 可以根据需要调整
                        'cycle_life': 'retention'        # 可以根据需要调整
                    }

                    standardized_metric = metric_mapping.get(metric_name, metric_name)

                    formatted_results.append({
                        'metric_name': standardized_metric,
                        'value': float(value)
                    })

                # 确保至少有基本的指标数据
                existing_metrics = {r['metric_name'] for r in formatted_results}
                required_metrics = ['retention', 'capacity', 'impedance']

                for metric in required_metrics:
                    if metric not in existing_metrics:
                        # 添加默认值
                        default_value = 0.8 if metric == 'retention' else 100.0 if metric == 'capacity' else 50.0
                        formatted_results.append({
                            'metric_name': metric,
                            'value': default_value
                        })

                # 将实验数据添加到贝叶斯优化器
                success = bayesian_optimizer.add_experiment_data(
                    experiment_data,
                    formatted_results
                )

                if success:
                    logger.info(f"成功加载实验 {experiment_id} 的数据到贝叶斯优化器")
                else:
                    logger.warning(f"实验 {experiment_id} 数据添加失败，使用默认数据")

            except Exception as e:
                logger.error(f"处理实验 {experiment_id} 数据时出错: {str(e)}")
                # 继续执行优化，使用已有的数据

        # 执行贝叶斯优化，传递用户需求
        optimization_result = bayesian_optimizer.suggest_optimized_formulas(
            weights=weights,
            n_candidates=n_candidates,
            optimization_target=optimization_target,
            user_requirements=user_requirements
        )

        return jsonify({
            'success': True,
            'data': {
                'optimization_result': optimization_result,
                'stats': bayesian_optimizer.get_optimization_stats()
            },
            'message': '贝叶斯优化完成'
        })

    except Exception as e:
        logger.error(f"运行贝叶斯优化时出错: {str(e)}")
        logger.error(f"错误详情: {repr(e)}")
        import traceback
        logger.error(f"完整错误堆栈: {traceback.format_exc()}")

        # 提供更友好的错误信息
        error_message = str(e)
        if "No module named" in error_message:
            error_message = "缺少必要的优化库，系统已降级为随机生成模式"
        elif "database" in error_message.lower():
            error_message = "数据库连接问题，请稍后重试"
        elif "value" in error_message.lower():
            error_message = "数据格式问题，请检查实验数据完整性"

        return jsonify({
            'success': False,
            'error': f'贝叶斯优化失败: {error_message}'
        }), 500


@closed_loop_bp.route('/run-requirement-based-optimization', methods=['POST'])
def run_requirement_based_optimization():
    """基于用户需求的贝叶斯优化 - 从AI设计员配方开始优化"""
    try:
        data = request.get_json()
        experiment_id = data.get('experiment_id')
        formula_data = data.get('formula_data')  # AI设计员生成的配方数据
        user_requirements = data.get('user_requirements', {})  # 解析的用户需求
        n_candidates = data.get('n_candidates', 5)
        optimization_target = data.get('optimization_target', 'requirement_based')

        logger.info(f"开始基于用户需求的贝叶斯优化: experiment_id={experiment_id}")

        # 优先使用提供的配方数据，否则从实验ID获取
        if formula_data:
            logger.info("使用提供的AI设计员配方数据")
            # 将AI设计员生成的配方添加到贝叶斯优化器
            success = bayesian_optimizer.add_formula_data(formula_data, user_requirements)

            if not success:
                logger.warning("AI配方数据添加失败，尝试使用实验数据")
                # 降级到实验数据
                if experiment_id:
                    success = _load_experiment_data(experiment_id)
        elif experiment_id:
            logger.info("从实验ID加载数据")
            success = _load_experiment_data(experiment_id)
        else:
            logger.warning("没有提供配方数据或实验ID，使用默认数据")
            success = True

        # 根据用户需求调整权重
        weights = _calculate_weights_from_requirements(user_requirements)

        # 执行贝叶斯优化，传递用户需求
        optimization_result = bayesian_optimizer.suggest_optimized_formulas(
            weights=weights,
            n_candidates=n_candidates,
            optimization_target=optimization_target,
            user_requirements=user_requirements
        )

        # 将优化结果保存为新的配方记录
        saved_formulas = _save_optimized_formulas(optimization_result, user_requirements, experiment_id)

        return jsonify({
            'success': True,
            'data': {
                'optimization_result': optimization_result,
                'saved_formulas': saved_formulas,  # 保存的配方记录
                'user_requirements': user_requirements,
                'stats': bayesian_optimizer.get_optimization_stats()
            },
            'message': '基于用户需求的贝叶斯优化完成'
        })

    except Exception as e:
        logger.error(f"运行基于用户需求的贝叶斯优化时出错: {str(e)}")
        import traceback
        logger.error(f"完整错误堆栈: {traceback.format_exc()}")

        error_message = str(e)
        if "No module named" in error_message:
            error_message = "缺少必要的优化库，系统已降级为随机生成模式"
        elif "database" in error_message.lower():
            error_message = "数据库连接问题，请稍后重试"

        return jsonify({
            'success': False,
            'error': f'基于用户需求的贝叶斯优化失败: {error_message}'
        }), 500


def _load_experiment_data(experiment_id: int) -> bool:
    """加载实验数据的辅助函数"""
    try:
        experiment = Experiment.query.get_or_404(experiment_id)
        results = ExperimentResult.query.filter_by(experiment_id=experiment_id).all()

        # 获取用户需求
        user_requirements = experiment.user_requirements or {}

        # 转换实验数据格式
        experiment_data = {
            'id': str(experiment.id),
            'name': experiment.name,
            'description': experiment.description or '',
            'predicted_properties': {},
            'components': []
        }

        # 尝试从实验的配方中提取组件信息
        if hasattr(experiment, 'formula') and experiment.formula:
            if hasattr(experiment.formula, 'components'):
                experiment_data['components'] = experiment.formula.components

        # 转换结果数据为预测属性
        if results:
            predicted_props = {}
            for result in results:
                metric_name = result.metric_name
                value = float(result.value)

                # 映射指标名称
                if metric_name == 'energy_density':
                    predicted_props['energy_density'] = value
                elif metric_name == 'power_density':
                    predicted_props['power_density'] = value
                elif metric_name == 'cycle_life':
                    predicted_props['cycle_life'] = value
                elif metric_name in ['safety_score', 'retention']:
                    predicted_props['safety_score'] = value
                elif metric_name == 'capacity':
                    predicted_props['energy_density'] = value  # 容量映射到能量密度

            experiment_data['predicted_properties'] = predicted_props

        # 添加到贝叶斯优化器
        return bayesian_optimizer.add_formula_data(experiment_data, user_requirements)

    except Exception as e:
        logger.error(f"加载实验数据失败: {e}")
        return False


def _calculate_weights_from_requirements(user_requirements: Dict) -> Dict[str, float]:
    """根据用户需求动态计算优化权重"""
    logger.info(f"根据用户需求计算优化权重: {user_requirements}")

    # 默认权重
    base_weights = {'w_ret': 0.33, 'w_cap': 0.33, 'w_imp': 0.34}

    if not user_requirements:
        logger.info("用户需求为空，使用默认权重")
        return base_weights

    # 分析用户需求指标
    requirement_indicators = []
    weight_allocations = []

    # 遍历用户需求，提取关键指标
    for key, value in user_requirements.items():
        if isinstance(value, (int, float)) and value > 0:
            if key == 'energy_density':
                # 能量密度需求 → 容量权重增加
                requirement_indicators.append(('capacity', value))
                logger.info(f"检测到能量密度需求: {value} Wh/kg")

            elif key == 'power_density':
                # 功率密度需求 → 容量权重增加
                requirement_indicators.append(('capacity', value))
                logger.info(f"检测到功率密度需求: {value} W/kg")

            elif key == 'cycle_life':
                # 循环寿命需求 → 保持率权重增加
                requirement_indicators.append(('retention', value))
                logger.info(f"检测到循环寿命需求: {value} cycles")

            elif key in ['safety_score', 'stability_score', 'safety']:
                # 安全性需求 → 保持率权重增加，阻抗权重减少
                requirement_indicators.append(('retention', value))
                logger.info(f"检测到安全性需求: {value}")

            elif key == 'impedance':
                # 阻抗需求（通常需要低阻抗）→ 阻抗权重增加（因为我们要最小化）
                requirement_indicators.append(('impedance', value))
                logger.info(f"检测到阻抗需求: {value} Ω")

    # 根据检测到的需求指标动态分配权重
    if not requirement_indicators:
        logger.info("未检测到有效的性能指标需求，使用默认权重")
        return base_weights

    # 初始化权重
    weights = {'w_ret': 0.1, 'w_cap': 0.1, 'w_imp': 0.1}
    total_weight = 0.3  # 保留70%的权重给未指定的指标

    # 根据用户需求的数量和重要性分配权重
    num_requirements = len(requirement_indicators)
    if num_requirements == 1:
        # 单一需求：分配70%权重
        primary_weight = 0.7
    elif num_requirements == 2:
        # 双重需求：各分配40%权重
        primary_weight = 0.4
    elif num_requirements == 3:
        # 三重需求：各分配30%权重
        primary_weight = 0.3
    else:
        # 多重需求：平均分配剩余权重
        primary_weight = 0.6 / num_requirements

    # 分配权重
    for indicator, value in requirement_indicators:
        if indicator == 'retention':
            weights['w_ret'] += primary_weight
        elif indicator == 'capacity':
            weights['w_cap'] += primary_weight
        elif indicator == 'impedance':
            weights['w_imp'] += primary_weight

    # 归一化权重确保总和为1
    total = sum(weights.values())
    if total != 1.0:
        weights = {k: v / total for k, v in weights.items()}

    # 根据用户需求的优先级进行微调
    # 如果用户特别强调某个指标（通过设置较高的数值）
    max_value = max((value for _, value in requirement_indicators), default=1)

    for indicator, value in requirement_indicators:
        ratio = value / max_value  # 相对优先级

        if indicator == 'retention' and ratio > 0.8:
            # 高优先级的保持率需求
            boost = 0.1 * ratio
            weights['w_ret'] += boost
            weights['w_cap'] -= boost * 0.5
            weights['w_imp'] -= boost * 0.5

        elif indicator == 'capacity' and ratio > 0.8:
            # 高优先级的容量需求
            boost = 0.1 * ratio
            weights['w_cap'] += boost
            weights['w_ret'] -= boost * 0.5
            weights['w_imp'] -= boost * 0.5

    # 确保权重都是正数并归一化
    weights = {k: max(0.05, v) for k, v in weights.items()}  # 最小权重0.05
    total = sum(weights.values())
    weights = {k: v / total for k, v in weights.items()}

    logger.info(f"计算得到的优化权重: {weights}")
    return weights


def _save_optimized_formulas(optimization_result: Dict, user_requirements: Dict, experiment_id: int = None) -> List[Dict]:
    """将优化后的配方保存到实验记录中"""
    try:
        saved_formulas = []

        if 'optimized_formulas' not in optimization_result:
            return saved_formulas

        from models import Formula
        from datetime import datetime

        for i, formula_data in enumerate(optimization_result['optimized_formulas']):
            # 创建新的配方记录
            formula = Formula(
                name=f"贝叶斯优化配方_{formula_data.get('id', i+1)}",
                description=f"基于用户需求优化的电解液配方 - 置信度: {formula_data.get('confidence_score', 0):.3f}",
                system_type='电解液',
                application_scenario=user_requirements.get('application_scenario', '3C'),
                generation_method='bayesian_opt',
                predicted_properties=formula_data.get('predicted_performance', {}),
                source_data={
                    'optimization_method': optimization_result.get('method'),
                    'user_requirements': user_requirements,
                    'confidence_score': formula_data.get('confidence_score'),
                    'optimization_target': optimization_result.get('optimization_target'),
                    'source_experiment_id': experiment_id
                },
                created_at=datetime.now()
            )

            # 简化存储：将溶剂比例信息保存在JSON字段中
            if 'solvent_ratios' in formula_data:
                # 保存为JSON字符串，避免ORM关联问题
                formula.source_data['solvent_ratios'] = formula_data['solvent_ratios']

            # 保存到数据库
            db.session.add(formula)
            db.session.commit()

            saved_formula_info = {
                'formula_id': formula.id,
                'name': formula.name,
                'description': formula.description,
                'generation_method': formula.generation_method,
                'predicted_properties': formula.predicted_properties,
                'solvent_ratios': formula_data.get('solvent_ratios', {}),
                'confidence_score': formula_data.get('confidence_score')
            }

            saved_formulas.append(saved_formula_info)
            logger.info(f"保存优化配方到数据库: {formula.name}")

        return saved_formulas

    except Exception as e:
        logger.error(f"保存优化配方失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return []


@closed_loop_bp.route('/add-experiment-data', methods=['POST'])
def add_experiment_data():
    """添加实验数据到贝叶斯优化器"""
    try:
        data = request.get_json()
        experiment_data = data.get('experiment_data', {})
        results = data.get('results', [])

        if not experiment_data or not results:
            return jsonify({'success': False, 'error': '缺少实验数据或结果'}), 400

        success = bayesian_optimizer.add_experiment_data(experiment_data, results)

        if success:
            return jsonify({
                'success': True,
                'data': {
                    'stats': bayesian_optimizer.get_optimization_stats()
                },
                'message': '实验数据添加成功'
            })
        else:
            return jsonify({'success': False, 'error': '实验数据添加失败'}), 400

    except Exception as e:
        logger.error(f"添加实验数据时出错: {str(e)}")
        return jsonify({'success': False, 'error': f'添加失败: {str(e)}'}), 500


@closed_loop_bp.route('/bayesian-stats', methods=['GET'])
def get_bayesian_stats():
    """获取贝叶斯优化器统计信息"""
    try:
        stats = bayesian_optimizer.get_optimization_stats()
        return jsonify({
            'success': True,
            'data': {
                'stats': stats
            },
            'message': '统计信息获取成功'
        })

    except Exception as e:
        logger.error(f"获取统计信息时出错: {str(e)}")
        return jsonify({'success': False, 'error': f'获取失败: {str(e)}'}), 500

@closed_loop_bp.route('/iterations/<int:experiment_id>', methods=['GET'])
def get_iteration_history(experiment_id):
    """获取迭代历史"""
    try:
        # 获取与指定实验相关的所有实验（同一需求的迭代）
        base_experiment = Experiment.query.get_or_404(experiment_id)

        # 这里可以根据业务逻辑查找相关的迭代实验
        # 例如：根据用户需求或者配方来源查找
        related_experiments = Experiment.query.filter(
            Experiment.user_requirements == base_experiment.user_requirements
        ).order_by(Experiment.created_at).all()

        iteration_history = []
        for exp in related_experiments:
            results = ExperimentResult.query.filter_by(experiment_id=exp.id).all()
            iteration_history.append({
                'experiment': exp.to_dict(),
                'results': [result.to_dict() for result in results]
            })

        return jsonify({
            'success': True,
            'iteration_history': iteration_history,
            'total_iterations': len(iteration_history),
            'message': '迭代历史获取成功'
        })

    except Exception as e:
        logger.error(f"获取迭代历史时出错: {str(e)}")
        return jsonify({'success': False, 'error': f'获取失败: {str(e)}'}), 500

@closed_loop_bp.route('/optimization-stats', methods=['GET'])
def get_optimization_stats():
    """获取优化统计信息"""
    try:
        # 统计各种数据
        total_experiments = Experiment.query.count()
        completed_experiments = Experiment.query.filter_by(status='completed').count()
        failed_experiments = Experiment.query.filter_by(status='failed').count()

        # 按生成方法统计
        from models import Formula
        initial_design_count = Formula.query.filter_by(generation_method='initial_design').count()
        bayesian_opt_count = Formula.query.filter_by(generation_method='bayesian_opt').count()
        redesign_count = Formula.query.filter_by(generation_method='redesign').count()

        stats = {
            'total_experiments': total_experiments,
            'completed_experiments': completed_experiments,
            'failed_experiments': failed_experiments,
            'success_rate': (completed_experiments / total_experiments * 100) if total_experiments > 0 else 0,
            'formula_generation_methods': {
                'initial_design': initial_design_count,
                'bayesian_opt': bayesian_opt_count,
                'redesign': redesign_count
            }
        }

        return jsonify({
            'success': True,
            'stats': stats,
            'message': '统计信息获取成功'
        })

    except Exception as e:
        logger.error(f"获取统计信息时出错: {str(e)}")
        return jsonify({'success': False, 'error': f'获取失败: {str(e)}'}), 500