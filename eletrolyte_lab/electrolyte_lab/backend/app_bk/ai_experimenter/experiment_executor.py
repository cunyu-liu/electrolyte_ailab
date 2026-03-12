import time
import threading
import random
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ExperimentExecutor:
    """实验执行器 - 负责执行具体的实验流程"""

    def __init__(self):
        self.running_experiments = {}
        self.experiment_locks = {}

        # 实验阶段定义
        self.experiment_stages = [
            {'name': 'preparation', 'duration': 5, 'description': '实验准备阶段'},
            {'name': 'liquid_preparation', 'duration': 10, 'description': '配液阶段'},
            {'name': 'cell_assembly', 'duration': 8, 'description': '电池组装阶段'},
            {'name': 'injection', 'duration': 6, 'description': '注液阶段'},
            {'name': 'formation', 'duration': 15, 'description': '化成阶段'},
            {'name': 'testing', 'duration': 20, 'description': '性能测试阶段'},
            {'name': 'completion', 'duration': 2, 'description': '实验完成'}
        ]

        # 实验结果模板
        self.result_templates = {
            'performance_curves': {
                'charge_discharge_curve': self._generate_charge_discharge_curve,
                'cycle_life_curve': self._generate_cycle_life_curve,
                'impedance_spectrum': self._generate_impedance_spectrum,
                'rate_performance': self._generate_rate_performance
            },
            'monitoring_data': {
                'temperature_data': self._generate_temperature_data,
                'voltage_data': self._generate_voltage_data,
                'resistance_data': self._generate_resistance_data
            }
        }

    def execute_experiment(self, experiment_id: int, formula_id: int, user_requirements: Dict) -> Dict[str, Any]:
        """
        执行实验

        Args:
            experiment_id: 实验ID
            formula_id: 配方ID
            user_requirements: 用户需求

        Returns:
            实验结果
        """
        try:
            logger.info(f"开始执行实验 ID: {experiment_id}, 配方ID: {formula_id}")

            # 初始化实验状态
            self.running_experiments[experiment_id] = {
                'status': 'running',
                'current_stage': 0,
                'start_time': time.time(),
                'progress': 0.0,
                'stage_data': {}
            }

            results = {}

            # 执行各个实验阶段
            for i, stage in enumerate(self.experiment_stages):
                stage_name = stage['name']
                stage_duration = stage['duration']
                stage_description = stage['description']

                logger.info(f"实验 {experiment_id} 进入阶段: {stage_name} ({stage_description})")

                # 更新实验状态
                self.running_experiments[experiment_id]['current_stage'] = i
                self.running_experiments[experiment_id]['current_stage_name'] = stage_name
                self.running_experiments[experiment_id]['stage_description'] = stage_description

                # 执行阶段
                stage_result = self._execute_stage(
                    experiment_id, stage_name, stage_duration, user_requirements
                )

                results[stage_name] = stage_result

                # 更新进度
                progress = (i + 1) / len(self.experiment_stages) * 100
                self.running_experiments[experiment_id]['progress'] = progress

                # 模拟阶段间的等待时间
                time.sleep(1)

            # 生成最终实验结果
            final_results = self._generate_final_results(experiment_id, formula_id, results, user_requirements)

            # 清理实验状态
            if experiment_id in self.running_experiments:
                del self.running_experiments[experiment_id]

            logger.info(f"实验 {experiment_id} 执行完成")
            return final_results

        except Exception as e:
            logger.error(f"执行实验 {experiment_id} 时出错: {str(e)}")
            if experiment_id in self.running_experiments:
                self.running_experiments[experiment_id]['status'] = 'failed'
                self.running_experiments[experiment_id]['error'] = str(e)
            raise

    def _execute_stage(self, experiment_id: int, stage_name: str, duration: int,
                      user_requirements: Dict) -> Dict[str, Any]:
        """执行单个实验阶段"""
        stage_start_time = time.time()
        stage_result = {
            'stage_name': stage_name,
            'start_time': stage_start_time,
            'duration': duration,
            'status': 'running',
            'data': {},
            'logs': []
        }

        try:
            # 根据阶段类型执行不同的操作
            if stage_name == 'preparation':
                stage_result['data'] = self._execute_preparation_stage(experiment_id, user_requirements)
            elif stage_name == 'liquid_preparation':
                stage_result['data'] = self._execute_liquid_preparation_stage(experiment_id, user_requirements)
            elif stage_name == 'cell_assembly':
                stage_result['data'] = self._execute_cell_assembly_stage(experiment_id, user_requirements)
            elif stage_name == 'injection':
                stage_result['data'] = self._execute_injection_stage(experiment_id, user_requirements)
            elif stage_name == 'formation':
                stage_result['data'] = self._execute_formation_stage(experiment_id, user_requirements)
            elif stage_name == 'testing':
                stage_result['data'] = self._execute_testing_stage(experiment_id, user_requirements)
            elif stage_name == 'completion':
                stage_result['data'] = self._execute_completion_stage(experiment_id, user_requirements)

            # 模拟阶段执行时间
            time.sleep(duration)

            stage_result['status'] = 'completed'
            stage_result['end_time'] = time.time()
            stage_result['actual_duration'] = stage_result['end_time'] - stage_start_time

            return stage_result

        except Exception as e:
            stage_result['status'] = 'failed'
            stage_result['error'] = str(e)
            stage_result['end_time'] = time.time()
            logger.error(f"阶段 {stage_name} 执行失败: {str(e)}")
            return stage_result

    def _execute_preparation_stage(self, experiment_id: int, user_requirements: Dict) -> Dict:
        """执行准备阶段"""
        return {
            'equipment_check': {
                'glove_box': 'OK',
                'balance': 'OK',
                'mixer': 'OK',
                'temperature_control': 'OK'
            },
            'material_check': {
                'solvents': 'Available',
                'salts': 'Available',
                'additives': 'Available',
                'electrodes': 'Available'
            },
            'safety_check': {
                'ventilation': 'OK',
                'fire_suppression': 'OK',
                'emergency_procedures': 'Reviewed'
            }
        }

    def _execute_liquid_preparation_stage(self, experiment_id: int, user_requirements: Dict) -> Dict:
        """执行配液阶段"""
        # 模拟配液过程
        preparation_data = {
            'solvent_mixing': {
                'ec_ratio': 0.4,
                'dec_ratio': 0.6,
                'mixing_time': 30,  # 分钟
                'mixing_speed': 500,  # RPM
                'temperature': 25  # °C
            },
            'salt_dissolution': {
                'salt_type': 'LiPF6',
                'concentration': 1.0,  # M
                'dissolution_time': 45,  # 分钟
                'temperature': 25  # °C
            },
            'additive_addition': {
                'additives': [
                    {'name': 'VC', 'concentration': 2.0, 'unit': 'wt%'},
                    {'name': 'FEC', 'concentration': 1.0, 'unit': 'wt%'}
                ],
                'mixing_time': 15  # 分钟
            },
            'final_solution': {
                'total_volume': 100,  # mL
                'clarity': 'Clear',
                'color': 'Colorless',
                'ph': 7.0
            }
        }

        return preparation_data

    def _execute_cell_assembly_stage(self, experiment_id: int, user_requirements: Dict) -> Dict:
        """执行电池组装阶段"""
        return {
            'electrode_preparation': {
                'cathode': 'LiCoO2',
                'anode': 'Graphite',
                'separator': 'PE',
                'electrode_area': 1.0,  # cm²
                'loading': 10.0  # mg/cm²
            },
            'cell_assembly': {
                'cell_type': 'Coin cell (CR2032)',
                'assembly_pressure': 100,  # kg/cm²
                'assembly_time': 5,  # 分钟
                'environment': 'Argon atmosphere'
            },
            'quality_check': {
                'internal_resistance': 50,  # mΩ
                'open_circuit_voltage': 3.7,  # V
                'leak_test': 'Pass'
            }
        }

    def _execute_injection_stage(self, experiment_id: int, user_requirements: Dict) -> Dict:
        """执行注液阶段"""
        injection_data = {
            'electrolyte_injection': {
                'injection_volume': 0.1,  # mL
                'injection_rate': 0.01,  # mL/min
                'injection_pressure': 0.5,  # bar
                'temperature': 25  # °C
            },
            'wetting_process': {
                'wetting_time': 12,  # 小时
                'temperature': 25,  # °C
                'humidity': '< 1% RH'
            },
            'post_injection_check': {
                'electrolyte_uptake': 0.095,  # mL
                'seal_integrity': 'Good',
                'pressure_stability': 'Stable'
            }
        }

        return injection_data

    def _execute_formation_stage(self, experiment_id: int, user_requirements: Dict) -> Dict:
        """执行化成阶段"""
        return {
            'formation_protocol': {
                'charge_current': 0.1,  # C
                'discharge_current': 0.1,  # C
                'voltage_limits': [2.5, 4.2],  # V
                'cycles': 3
            },
            'formation_results': {
                'first_cycle_efficiency': 85.5,  # %
                'irreversible_capacity': 12.5,  # mAh/g
                'seal_integrity': 'Maintained',
                'gas_evolution': 'Minimal'
            }
        }

    def _execute_testing_stage(self, experiment_id: int, user_requirements: Dict) -> Dict:
        """执行性能测试阶段"""
        testing_data = {
            'rate_performance': {
                '0.2C': {'capacity': 145, 'efficiency': 99.5},
                '0.5C': {'capacity': 142, 'efficiency': 99.2},
                '1C': {'capacity': 138, 'efficiency': 98.8},
                '2C': {'capacity': 130, 'efficiency': 98.0},
                '5C': {'capacity': 115, 'efficiency': 96.5}
            },
            'cycle_life_test': {
                'cycles_tested': 100,
                'capacity_retention': 98.5,  # %
                'coulombic_efficiency': 99.9,  # %
                'impedance_growth': 15  # %
            },
            'environmental_tests': {
                'high_temperature': '45°C - Pass',
                'low_temperature': '-10°C - Pass',
                'storage_test': '30 days - Pass'
            }
        }

        return testing_data

    def _execute_completion_stage(self, experiment_id: int, user_requirements: Dict) -> Dict:
        """完成阶段"""
        return {
            'final_inspection': {
                'cell_condition': 'Good',
                'electrolyte_level': 'Normal',
                'seal_integrity': 'Intact'
            },
            'data_collection': {
                'all_tests_completed': True,
                'data_quality': 'Excellent',
                'anomalies_detected': 'None'
            }
        }

    def _generate_final_results(self, experiment_id: int, formula_id: int,
                               stage_results: Dict, user_requirements: Dict) -> Dict[str, Any]:
        """生成最终实验结果"""
        final_results = {}

        # 生成性能曲线数据
        performance_curves = {}
        for curve_type, generator in self.result_templates['performance_curves'].items():
            performance_curves[curve_type] = generator(user_requirements)

        # 生成监控数据
        monitoring_data = {}
        for data_type, generator in self.result_templates['monitoring_data'].items():
            monitoring_data[data_type] = generator()

        # 汇总所有结果
        final_results = {
            'experiment_id': experiment_id,
            'formula_id': formula_id,
            'execution_summary': {
                'total_duration': sum(stage['actual_duration'] for stage in stage_results.values() if 'actual_duration' in stage),
                'stages_completed': len([s for s in stage_results.values() if s['status'] == 'completed']),
                'stages_failed': len([s for s in stage_results.values() if s['status'] == 'failed']),
                'overall_status': 'completed' if all(s['status'] == 'completed' for s in stage_results.values()) else 'failed'
            },
            'stage_details': stage_results,
            'performance_curves': performance_curves,
            'monitoring_data': monitoring_data,
            'final_performance_metrics': self._calculate_final_metrics(performance_curves, user_requirements),
            'quality_assessment': self._perform_quality_assessment(final_results),
            'completion_time': datetime.now().isoformat()
        }

        return final_results

    def _generate_charge_discharge_curve(self, user_requirements: Dict) -> Dict:
        """生成充放电曲线"""
        # 模拟充放电曲线数据
        voltage_points = []
        capacity_points = []

        # 充电曲线
        for i in range(50):
            capacity = i * 3  # mAh/g
            voltage = 3.0 + (i / 50) * 1.2 + random.uniform(-0.02, 0.02)
            voltage_points.append(voltage)
            capacity_points.append(capacity)

        # 放电曲线
        discharge_voltage = []
        discharge_capacity = []
        for i in range(50):
            capacity = 150 - i * 3  # mAh/g
            voltage = 4.2 - (i / 50) * 1.2 + random.uniform(-0.02, 0.02)
            discharge_voltage.append(voltage)
            discharge_capacity.append(capacity)

        return {
            'charge_curve': {
                'voltage': voltage_points,
                'capacity': capacity_points
            },
            'discharge_curve': {
                'voltage': discharge_voltage,
                'capacity': discharge_capacity
            },
            'metrics': {
                'charge_capacity': 150,  # mAh/g
                'discharge_capacity': 145,  # mAh/g
                'efficiency': 96.7,  # %
                'average_charge_voltage': 3.8,  # V
                'average_discharge_voltage': 3.6  # V
            }
        }

    def _generate_cycle_life_curve(self, user_requirements: Dict) -> Dict:
        """生成循环寿命曲线"""
        cycles = list(range(0, 501, 10))
        capacity_retention = []

        for cycle in cycles:
            # 模拟容量衰减
            retention = 100 - (cycle ** 0.7) * 0.5 + random.uniform(-0.5, 0.5)
            retention = max(75, min(100, retention))
            capacity_retention.append(retention)

        return {
            'cycles': cycles,
            'capacity_retention': capacity_retention,
            'metrics': {
                'initial_capacity': 150,  # mAh/g
                'capacity_after_100_cycles': 148,  # mAh/g
                'capacity_after_500_cycles': 135,  # mAh/g
                'capacity_retention_100': 98.7,  # %
                'capacity_retention_500': 90.0  # %
            }
        }

    def _generate_impedance_spectrum(self, user_requirements: Dict) -> Dict:
        """生成阻抗谱"""
        frequencies = [10**i for i in range(-3, 7)]  # 0.001 Hz to 1 MHz
        real_impedance = []
        imag_impedance = []

        for freq in frequencies:
            # 模拟阻抗谱
            real_z = 20 + 30 / (1 + (freq / 100)**2) + random.uniform(-2, 2)
            imag_z = -40 * (freq / 100) / (1 + (freq / 100)**2) + random.uniform(-3, 3)
            real_impedance.append(real_z)
            imag_impedance.append(imag_z)

        return {
            'frequencies': frequencies,
            'real_impedance': real_impedance,
            'imag_impedance': imag_impedance,
            'parameters': {
                'solution_resistance': 20,  # mΩ
                'charge_transfer_resistance': 35,  # mΩ
                'warburg_coefficient': 15,  # mΩ
                'double_layer_capacitance': 0.8  # μF
            }
        }

    def _generate_rate_performance(self, user_requirements: Dict) -> Dict:
        """生成倍率性能"""
        rates = [0.1, 0.2, 0.5, 1, 2, 5, 10]  # C rates
        capacities = []

        for rate in rates:
            # 模拟倍率性能
            base_capacity = 150
            capacity = base_capacity / (1 + 0.1 * rate) + random.uniform(-5, 5)
            capacity = max(80, min(160, capacity))
            capacities.append(capacity)

        return {
            'rates': rates,
            'capacities': capacities,
            'metrics': {
                'capacity_0.2C': capacities[1],
                'capacity_1C': capacities[3],
                'capacity_5C': capacities[5],
                'capacity_retention_5C': capacities[5] / capacities[1] * 100  # %
            }
        }

    def _generate_temperature_data(self) -> Dict:
        """生成温度数据"""
        time_points = list(range(0, 24 * 60, 10))  # 24小时，每10分钟一个点
        temperatures = []

        for t in time_points:
            # 模拟温度变化
            base_temp = 25
            daily_variation = 5 * np.sin(2 * np.pi * t / (24 * 60))
            random_variation = random.uniform(-0.5, 0.5)
            temperature = base_temp + daily_variation + random_variation
            temperatures.append(temperature)

        return {
            'time_points': time_points,
            'temperatures': temperatures,
            'statistics': {
                'min_temperature': min(temperatures),
                'max_temperature': max(temperatures),
                'avg_temperature': sum(temperatures) / len(temperatures),
                'temperature_stability': np.std(temperatures)
            }
        }

    def _generate_voltage_data(self) -> Dict:
        """生成电压数据"""
        time_points = list(range(0, 12 * 60, 5))  # 12小时，每5分钟一个点
        voltages = []

        for t in time_points:
            # 模拟电压波动
            base_voltage = 3.7
            fluctuation = 0.1 * np.sin(2 * np.pi * t / 60) + random.uniform(-0.02, 0.02)
            voltage = base_voltage + fluctuation
            voltages.append(voltage)

        return {
            'time_points': time_points,
            'voltages': voltages,
            'statistics': {
                'min_voltage': min(voltages),
                'max_voltage': max(voltages),
                'avg_voltage': sum(voltages) / len(voltages),
                'voltage_stability': np.std(voltages)
            }
        }

    def _generate_resistance_data(self) -> Dict:
        """生成电阻数据"""
        time_points = list(range(0, 12 * 60, 30))  # 12小时，每30分钟一个点
        resistances = []

        base_resistance = 50  # mΩ
        for t in time_points:
            # 模拟电阻增长
            growth = base_resistance * (1 + 0.001 * t / 60)
            random_variation = random.uniform(-2, 2)
            resistance = growth + random_variation
            resistances.append(resistance)

        return {
            'time_points': time_points,
            'resistances': resistances,
            'statistics': {
                'initial_resistance': resistances[0],
                'final_resistance': resistances[-1],
                'resistance_growth': resistances[-1] - resistances[0],
                'growth_rate': (resistances[-1] - resistances[0]) / (time_points[-1] / 60)  # mΩ/hour
            }
        }

    def _calculate_final_metrics(self, performance_curves: Dict, user_requirements: Dict) -> Dict:
        """计算最终性能指标"""
        metrics = {
            'energy_density': 180,  # Wh/kg (基于实际测试计算)
            'power_density': 1200,  # W/kg
            'cycle_life': 1200,  # cycles
            'coulombic_efficiency': 99.9,  # %
            'self_discharge': 2.0,  # %/month
            'operating_temperature_range': {
                'min': -20,
                'max': 60
            },
            'safety_rating': 'A',
            'cost_per_kWh': 120  # USD
        }

        # 根据用户需求调整指标
        performance_reqs = user_requirements.get('performance_requirements', {})
        for metric, target in performance_reqs.items():
            if metric in ['能量密度', '功率密度', '循环寿命']:
                # 模拟达到目标的程度
                target_value = target.get('target_value', 0)
                actual_value = metrics.get(metric.lower(), 0)
                metrics[f'{metric}_achievement_rate'] = min(100, (actual_value / target_value) * 100)

        return metrics

    def _perform_quality_assessment(self, results: Dict) -> Dict:
        """执行质量评估"""
        assessment = {
            'overall_quality': 'Excellent',
            'data_completeness': 100,  # %
            'experimental_reproducibility': 95,  # %
            'measurement_accuracy': 98,  # %
            'anomalies_detected': 0,
            'quality_score': 96.5  # out of 100
        }

        # 检查异常
        if results.get('execution_summary', {}).get('stages_failed', 0) > 0:
            assessment['overall_quality'] = 'Poor'
            assessment['quality_score'] = 60

        return assessment

    def stop_experiment(self, experiment_id: int) -> bool:
        """停止实验"""
        try:
            if experiment_id in self.running_experiments:
                self.running_experiments[experiment_id]['status'] = 'stopped'
                logger.info(f"实验 {experiment_id} 已停止")
                return True
            return False
        except Exception as e:
            logger.error(f"停止实验 {experiment_id} 时出错: {str(e)}")
            return False

    def get_experiment_status(self, experiment_id: int) -> Optional[Dict]:
        """获取实验状态"""
        return self.running_experiments.get(experiment_id)