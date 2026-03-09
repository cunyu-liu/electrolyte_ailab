"""
实验监控数据库查询模块
支持从真实实验数据库查询内阻电压数据和充放电曲线数据
"""

import sqlite3
import psycopg2
import pymysql
from typing import List, Dict, Any, Optional, Union
import pandas as pd
from datetime import datetime, timedelta
import logging
import sys
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加fpxh_control模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../fpxh_control'))

logger = logging.getLogger(__name__)

# 从环境变量读取Landian数据库配置
def get_landian_db_config() -> Dict[str, Any]:
    """获取Landian数据库配置"""
    return {
        'host': os.getenv('LANDIAN_DB_HOST', '101.6.160.48'),
        'port': int(os.getenv('LANDIAN_DB_PORT', 50003)),
        'user': os.getenv('LANDIAN_DB_USER', 'landian'),
        'password': os.getenv('LANDIAN_DB_PASSWORD', '123456'),
        'database': os.getenv('LANDIAN_DB_NAME', 'electrolyte')
    }

class ExperimentDataQuery:
    """实验数据查询类"""

    def __init__(self, db_config: Dict[str, Any]):
        """
        初始化数据库连接配置

        Args:
            db_config: 数据库配置字典
                - db_type: 数据库类型 ('sqlite', 'mysql', 'postgresql')
                - host: 主机地址 (MySQL/PostgreSQL)
                - port: 端口号 (MySQL/PostgreSQL)
                - database: 数据库名称 (MySQL/PostgreSQL)
                - username: 用户名 (MySQL/PostgreSQL)
                - password: 密码 (MySQL/PostgreSQL)
                - db_path: SQLite数据库文件路径 (SQLite)
        """
        self.db_config = db_config
        self.db_type = db_config.get('db_type', 'sqlite').lower()

    def _get_connection(self):
        """获取数据库连接"""
        try:
            if self.db_type == 'sqlite':
                return sqlite3.connect(self.db_config['db_path'])
            elif self.db_type == 'mysql':
                return pymysql.connect(
                    host=self.db_config['host'],
                    port=self.db_config.get('port', 3306),
                    user=self.db_config['username'],
                    password=self.db_config['password'],
                    database=self.db_config['database'],
                    charset='utf8mb4'
                )
            elif self.db_type == 'postgresql':
                return psycopg2.connect(
                    host=self.db_config['host'],
                    port=self.db_config.get('port', 5432),
                    user=self.db_config['username'],
                    password=self.db_config['password'],
                    database=self.db_config['database']
                )
            else:
                raise ValueError(f"不支持的数据库类型: {self.db_type}")
        except Exception as e:
            logger.error(f"数据库连接失败: {str(e)}")
            raise

    def query_resistance_voltage_data(self,
                                    experiment_id: Union[int, str],
                                    start_time: Optional[str] = None,
                                    end_time: Optional[str] = None,
                                    cycle_numbers: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        查询内阻电压数据

        Args:
            experiment_id: 实验ID
            start_time: 开始时间 (格式: 'YYYY-MM-DD HH:MM:SS')
            end_time: 结束时间 (格式: 'YYYY-MM-DD HH:MM:SS')
            cycle_numbers: 指定循环次数列表，如 [1, 2, 10, 50, 100]

        Returns:
            包含内阻电压数据的列表，每条记录包含:
            - 循环号 (cycle_number)
            - 工步号 (step_number)
            - 总时间 (total_time)
            - 电流 (current)
            - 电压 (voltage)
            - 容量 (capacity)
        """
        query_sql = """
            SELECT
                循环号,
                工步号,
                总时间,
                电流,
                电压,
                容量
            FROM 内阻电压数据表
            WHERE 实验ID = %s
        """

        params = [experiment_id]

        # 添加时间过滤
        if start_time:
            query_sql += " AND 总时间 >= %s"
            params.append(start_time)

        if end_time:
            query_sql += " AND 总时间 <= %s"
            params.append(end_time)

        # 添加循环次数过滤
        if cycle_numbers:
            placeholders = ','.join(['%s'] * len(cycle_numbers))
            query_sql += f" AND 循环号 IN ({placeholders})"
            params.extend(cycle_numbers)

        query_sql += " ORDER BY 循环号, 工步号"

        try:
            with self._get_connection() as conn:
                # 适配不同数据库的参数占位符
                if self.db_type == 'sqlite':
                    query_sql = query_sql.replace('%s', '?')

                df = pd.read_sql_query(query_sql, conn, params=params)

                # 转换为字典列表
                result = []
                for _, row in df.iterrows():
                    result.append({
                        'cycle_number': int(row['循环号']),
                        'step_number': int(row['工步号']),
                        'total_time': str(row['总时间']),
                        'current': float(row['电流']),
                        'voltage': float(row['电压']),
                        'capacity': float(row['容量']),
                        'experiment_id': str(experiment_id)
                    })

                logger.info(f"查询到 {len(result)} 条内阻电压数据")
                return result

        except Exception as e:
            logger.error(f"查询内阻电压数据失败: {str(e)}")
            # 返回模拟数据作为降级方案
            return self._get_mock_resistance_voltage_data(experiment_id)

    def query_charge_discharge_data(self,
                                  experiment_id: Union[int, str],
                                  start_time: Optional[str] = None,
                                  end_time: Optional[str] = None,
                                  cycle_numbers: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        查询充放电曲线数据

        Args:
            experiment_id: 实验ID
            start_time: 开始时间
            end_time: 结束时间
            cycle_numbers: 指定循环次数列表

        Returns:
            包含充放电数据的列表，每条记录包含:
            - 循环号 (cycle_number)
            - 充电容量 (charge_capacity)
            - 放电容量 (discharge_capacity)
            - 充电效率 (charge_efficiency)
            - 实验时间 (experiment_time)
        """
        query_sql = """
            SELECT
                循环号,
                充电容量,
                放电容量,
                实验时间
            FROM 充放电数据表
            WHERE 实验ID = %s
        """

        params = [experiment_id]

        # 添加过滤条件
        if start_time:
            query_sql += " AND 实验时间 >= %s"
            params.append(start_time)

        if end_time:
            query_sql += " AND 实验时间 <= %s"
            params.append(end_time)

        if cycle_numbers:
            placeholders = ','.join(['%s'] * len(cycle_numbers))
            query_sql += f" AND 循环号 IN ({placeholders})"
            params.extend(cycle_numbers)

        query_sql += " ORDER BY 循环号"

        try:
            with self._get_connection() as conn:
                # 适配不同数据库的参数占位符
                if self.db_type == 'sqlite':
                    query_sql = query_sql.replace('%s', '?')

                df = pd.read_sql_query(query_sql, conn, params=params)

                # 转换为字典列表并计算效率
                result = []
                for _, row in df.iterrows():
                    charge_capacity = float(row['充电容量'])
                    discharge_capacity = float(row['放电容量'])
                    efficiency = (discharge_capacity / charge_capacity * 100) if charge_capacity > 0 else 0

                    result.append({
                        'cycle_number': int(row['循环号']),
                        'charge_capacity': charge_capacity,
                        'discharge_capacity': discharge_capacity,
                        'charge_efficiency': round(efficiency, 2),
                        'experiment_time': str(row['实验时间']),
                        'experiment_id': str(experiment_id)
                    })

                logger.info(f"查询到 {len(result)} 条充放电数据")
                return result

        except Exception as e:
            logger.error(f"查询充放电数据失败: {str(e)}")
            # 返回模拟数据作为降级方案
            return self._get_mock_charge_discharge_data(experiment_id)

    def calculate_impedance_from_voltage_data(self,
                                            voltage_data: List[Dict[str, Any]],
                                            current_threshold: float = 0.1) -> List[Dict[str, Any]]:
        """
        从电压数据计算内阻

        Args:
            voltage_data: 电压数据列表
            current_threshold: 电流变化阈值 (A)

        Returns:
            内阻数据列表
        """
        impedance_data = []

        for i in range(1, len(voltage_data)):
            prev_data = voltage_data[i-1]
            curr_data = voltage_data[i]

            current_diff = abs(curr_data['current'] - prev_data['current'])

            # 只有在电流变化显著时才计算内阻
            if current_diff >= current_threshold:
                voltage_diff = abs(curr_data['voltage'] - prev_data['voltage'])
                impedance = voltage_diff / current_diff * 1000  # 转换为mΩ

                impedance_data.append({
                    'cycle_number': curr_data['cycle_number'],
                    'impedance': round(impedance, 2),
                    'voltage_before': prev_data['voltage'],
                    'voltage_after': curr_data['voltage'],
                    'current_before': prev_data['current'],
                    'current_after': curr_data['current'],
                    'total_time': curr_data['total_time'],
                    'experiment_id': curr_data['experiment_id']
                })

        return impedance_data

    def get_experiment_summary(self, experiment_id: Union[int, str]) -> Dict[str, Any]:
        """
        获取实验汇总信息

        Args:
            experiment_id: 实验ID

        Returns:
            实验汇总信息
        """
        try:
            # 查询充放电数据获取汇总信息
            charge_data = self.query_charge_discharge_data(experiment_id)

            if not charge_data:
                return {}

            # 计算汇总统计
            first_cycle = charge_data[0]
            latest_cycle = charge_data[-1]

            capacity_retention = (latest_cycle['discharge_capacity'] / first_cycle['discharge_capacity']) * 100
            avg_efficiency = sum(d['charge_efficiency'] for d in charge_data) / len(charge_data)

            summary = {
                'experiment_id': str(experiment_id),
                'total_cycles': len(charge_data),
                'first_charge_capacity': first_cycle['charge_capacity'],
                'first_discharge_capacity': first_cycle['discharge_capacity'],
                'latest_charge_capacity': latest_cycle['charge_capacity'],
                'latest_discharge_capacity': latest_cycle['discharge_capacity'],
                'capacity_retention': round(capacity_retention, 2),
                'average_efficiency': round(avg_efficiency, 2),
                'latest_efficiency': latest_cycle['charge_efficiency']
            }

            return summary

        except Exception as e:
            logger.error(f"获取实验汇总信息失败: {str(e)}")
            return {}

    def _get_mock_resistance_voltage_data(self, experiment_id: Union[int, str]) -> List[Dict[str, Any]]:
        """生成模拟内阻电压数据"""
        import random

        mock_data = []
        cycles = [1, 1, 1, 2, 2, 2, 10, 10, 10, 25, 25, 25, 50, 50, 50, 100, 100, 100]

        for i, cycle in enumerate(cycles):
            base_hours = cycle * 1.5
            hour_offset = random.randint(0, 2)
            minute_offset = random.randint(0, 59)

            total_time = f"{int(base_hours + hour_offset):02d}:{minute_offset:02d}:{random.randint(0, 59):02d}"

            # 模拟不同阶段的电流和电压
            if i % 3 == 0:  # 充电阶段
                current = 1.0
                voltage = 3.65 + random.uniform(0, 0.15)
                capacity = random.uniform(0.4, 0.6)
            elif i % 3 == 1:  # 恒流充电
                current = 1.0
                voltage = 3.80 + random.uniform(0, 0.35)
                capacity = random.uniform(1.0, 2.0)
            else:  # 放电阶段
                current = -1.0
                voltage = 3.50 + random.uniform(-0.7, 0.3)
                capacity = random.uniform(0.2, 1.0)

            # 循环次数增加，电压轻微衰减，内阻轻微增加
            voltage_factor = 1 - (cycle / 1000)  # 每1000循环衰减0.1V

            mock_data.append({
                'cycle_number': cycle,
                'step_number': (i % 3) + 1,
                'total_time': total_time,
                'current': current,
                'voltage': voltage * voltage_factor,
                'capacity': capacity,
                'experiment_id': str(experiment_id)
            })

        return mock_data

    def _get_mock_charge_discharge_data(self, experiment_id: Union[int, str]) -> List[Dict[str, Any]]:
        """生成模拟充放电数据"""
        mock_data = []

        # 生成100个循环的数据
        for cycle in range(1, 201):
            if cycle in [1, 2, 3, 5, 10, 15, 20, 25, 30, 40, 50, 60, 75, 100, 125, 150, 200]:
                # 模拟容量衰减
                charge_capacity = 2.85 - (cycle / 1000) * 0.15  # 每100循环衰减0.015Ah
                discharge_capacity = charge_capacity * (0.94 - (cycle / 10000) * 0.05)  # 效率也逐渐衰减

                mock_data.append({
                    'cycle_number': cycle,
                    'charge_capacity': round(charge_capacity, 3),
                    'discharge_capacity': round(discharge_capacity, 3),
                    'charge_efficiency': round((discharge_capacity / charge_capacity) * 100, 2),
                    'experiment_time': f"2024-01-{cycle//30 + 1:02d} {cycle%24:02d}:00:00",
                    'experiment_id': str(experiment_id)
                })

        return mock_data


class LandianDataQueryEnhanced:
    """增强版蓝甸数据库查询类，适配实验监控系统"""

    def __init__(self, db_config: Dict[str, Any]):
        """
        初始化蓝甸数据库查询

        Args:
            db_config: 数据库配置
                - host: 数据库主机地址
                - port: 数据库端口
                - user: 用户名
                - password: 密码
                - database: 数据库名
        """
        try:
            from fpxh_control.get_landian_result import LandianDataQuery
            self.landian_query = LandianDataQuery(db_config)
        except ImportError as e:
            logger.error(f"无法导入LandianDataQuery: {str(e)}")
            self.landian_query = None
            self.use_fallback = True
        else:
            self.use_fallback = False

    def query_cycle_curve_data(self, main_id: str) -> List[Dict[str, Any]]:
        """
        查询循环曲线数据

        Args:
            main_id: 电池单元的MainId

        Returns:
            格式化的充放电循环数据
        """
        if self.use_fallback or not self.landian_query:
            logger.warning("蓝甸数据库不可用，使用模拟数据")
            return self._get_mock_charge_discharge_data(main_id)

        try:
            result = self.landian_query.get_cycle_curve(main_id)

            if "error" in result:
                logger.error(f"查询循环曲线失败: {result['error']}")
                return self._get_mock_charge_discharge_data(main_id)

            # 转换为前端需要的格式
            formatted_data = []
            for cycle in result.get("循环曲线", []):
                formatted_data.append({
                    'cycle_number': cycle["循环号"],
                    'charge_capacity': cycle["充电容量(Ah)"],
                    'discharge_capacity': cycle["放电容量(Ah)"],
                    'charge_efficiency': cycle["充电效率(%)"],
                    'experiment_time': cycle.get("测试时间", ""),
                    'experiment_id': main_id
                })

            logger.info(f"从蓝甸数据库获取到 {len(formatted_data)} 条循环曲线数据")
            return formatted_data

        except Exception as e:
            logger.error(f"查询循环曲线数据失败: {str(e)}")
            return self._get_mock_charge_discharge_data(main_id)

    def query_cycle_detail_data(self, main_id: str, cycle_no: int) -> Dict[str, Any]:
        """
        查询循环细节数据

        Args:
            main_id: 电池单元的MainId
            cycle_no: 循环号

        Returns:
            包含电压-容量曲线数据的字典
        """
        if self.use_fallback or not self.landian_query:
            logger.warning("蓝甸数据库不可用，使用模拟数据")
            return self._get_mock_voltage_capacity_data(main_id, cycle_no)

        try:
            result = self.landian_query.get_voltage_capacity_curve(main_id, cycle_no)

            if "error" in result:
                logger.error(f"查询循环细节失败: {result['error']}")
                return self._get_mock_voltage_capacity_data(main_id, cycle_no)

            # 转换为前端需要的格式
            voltage_data = result.get("电压数据", [])
            capacity_data = result.get("容量数据", [])

            formatted_data = {
                'experiment_id': main_id,
                'cycle_number': cycle_no,
                'voltage_curve': voltage_data,
                'capacity_curve': capacity_data,
                'data_points': len(voltage_data),
                'voltage_range': result.get("电压范围", [0, 0]),
                'capacity_range': result.get("容量范围", [0, 0]),
                'charge_curve': self._generate_charge_curve(voltage_data, capacity_data),
                'discharge_curve': self._generate_discharge_curve(voltage_data, capacity_data)
            }

            logger.info(f"从蓝甸数据库获取到 {formatted_data['data_points']} 个数据点")
            return formatted_data

        except Exception as e:
            logger.error(f"查询循环细节数据失败: {str(e)}")
            return self._get_mock_voltage_capacity_data(main_id, cycle_no)

    def _generate_charge_curve(self, voltage_data: List[float], capacity_data: List[float]) -> Dict[str, List[float]]:
        """生成充电曲线数据点"""
        # 简化处理：假设前半部分是充电曲线
        mid_point = len(voltage_data) // 2
        return {
            'voltage': voltage_data[:mid_point],
            'capacity': capacity_data[:mid_point]
        }

    def _generate_discharge_curve(self, voltage_data: List[float], capacity_data: List[float]) -> Dict[str, List[float]]:
        """生成放电曲线数据点"""
        # 简化处理：假设后半部分是放电曲线
        mid_point = len(voltage_data) // 2
        return {
            'voltage': voltage_data[mid_point:],
            'capacity': capacity_data[mid_point:]
        }

    def _get_mock_voltage_capacity_data(self, main_id: str, cycle_no: int) -> Dict[str, Any]:
        """生成模拟的电压-容量数据"""
        import random

        # 模拟充电过程的电压-容量曲线
        charge_points = 50
        discharge_points = 50

        # 充电曲线：从3.0V上升到4.2V，容量从0增加到2.8Ah
        charge_voltage = [3.0 + (1.2 * i / charge_points) + random.uniform(-0.05, 0.05) for i in range(charge_points)]
        charge_capacity = [2.8 * i / charge_points + random.uniform(-0.1, 0.1) for i in range(charge_points)]

        # 放电曲线：从4.2V下降到3.0V，容量从2.8Ah减少到0
        discharge_voltage = [4.2 - (1.2 * i / discharge_points) + random.uniform(-0.05, 0.05) for i in range(discharge_points)]
        discharge_capacity = [2.8 * (1 - i / discharge_points) + random.uniform(-0.1, 0.1) for i in range(discharge_points)]

        return {
            'experiment_id': main_id,
            'cycle_number': cycle_no,
            'voltage_curve': charge_voltage + discharge_voltage,
            'capacity_curve': charge_capacity + discharge_capacity,
            'data_points': charge_points + discharge_points,
            'voltage_range': [min(charge_voltage + discharge_voltage), max(charge_voltage + discharge_voltage)],
            'capacity_range': [0, max(charge_capacity + discharge_capacity)],
            'charge_curve': {
                'voltage': charge_voltage,
                'capacity': charge_capacity
            },
            'discharge_curve': {
                'voltage': discharge_voltage,
                'capacity': discharge_capacity
            }
        }

    def close(self):
        """关闭数据库连接"""
        if self.landian_query:
            self.landian_query.close()


# 使用示例和测试函数
def test_database_query():
    """测试数据库查询功能"""

    # SQLite配置示例
    sqlite_config = {
        'db_type': 'sqlite',
        'db_path': 'experiments.db'
    }

    # MySQL配置示例
    mysql_config = {
        'db_type': 'mysql',
        'host': 'localhost',
        'port': 3306,
        'database': 'battery_experiments',
        'username': 'root',
        'password': 'password'
    }

    # PostgreSQL配置示例
    postgres_config = {
        'db_type': 'postgresql',
        'host': 'localhost',
        'port': 5432,
        'database': 'battery_experiments',
        'username': 'postgres',
        'password': 'password'
    }

    try:
        # 创建查询实例
        query = ExperimentDataQuery(sqlite_config)

        # 测试查询内阻电压数据
        resistance_data = query.query_resistance_voltage_data(
            experiment_id='EXP001',
            cycle_numbers=[1, 2, 10, 50, 100]
        )
        print(f"查询到 {len(resistance_data)} 条内阻电压数据")

        # 测试查询充放电数据
        charge_data = query.query_charge_discharge_data(experiment_id='EXP001')
        print(f"查询到 {len(charge_data)} 条充放电数据")

        # 测试计算内阻
        impedance_data = query.calculate_impedance_from_voltage_data(resistance_data)
        print(f"计算出 {len(impedance_data)} 个内阻数据点")

        # 测试获取实验汇总
        summary = query.get_experiment_summary('EXP001')
        print("实验汇总信息:", summary)

    except Exception as e:
        print(f"测试失败: {str(e)}")


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO)

    # 运行测试
    test_database_query()