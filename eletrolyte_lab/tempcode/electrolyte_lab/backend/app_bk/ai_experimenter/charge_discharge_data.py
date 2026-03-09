"""
充放电曲线数据获取模块
集成真实的蓝殿数据库查询功能
"""
import sys
import os
import logging
import json
from typing import Dict, List, Any, Optional
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加蓝殿数据查询模块路径
sys.path.append(r'D:\electrolyte\code')

logger = logging.getLogger(__name__)

# 导入外部数据查询模块
landian_data_query = None
LANDIAN_AVAILABLE = False

try:
    from fpxh_control.get_landian_result import LandianDataQuery
    LANDIAN_AVAILABLE = True
    logger.info("蓝殿数据查询模块加载成功")
except ImportError as e:
    logger.warning(f"蓝殿数据查询模块导入不可用: {e}")
    LANDIAN_AVAILABLE = False
except Exception as e:
    logger.warning(f"蓝殿数据查询模块加载失败: {e}")
    LANDIAN_AVAILABLE = False

class ChargeDischargeDataFetcher:
    """充放电曲线数据获取器 - 仅使用真实蓝殿数据库数据"""

    def __init__(self):
        if not LANDIAN_AVAILABLE:
            raise Exception("蓝殿数据查询模块不可用，无法使用真实数据")

        self.db_config = {
            'host': os.getenv('LANDIAN_DB_HOST', '101.6.160.48'),
            'port': int(os.getenv('LANDIAN_DB_PORT', 50003)),
            'user': os.getenv('LANDIAN_DB_USER', 'landian'),
            'password': os.getenv('LANDIAN_DB_PASSWORD', '123456'),
            'database': os.getenv('LANDIAN_DB_NAME', 'electrolyte')
        }
        self.query_instance = None

    def _get_query_instance(self):
        """获取查询实例"""
        if not self.query_instance:
            try:
                self.query_instance = LandianDataQuery(self.db_config)
                logger.info("蓝殿数据库连接创建成功")
            except Exception as e:
                logger.error(f"创建蓝殿数据库连接失败: {str(e)}")
                raise Exception(f"无法连接到蓝殿数据库: {str(e)}")

        return self.query_instance

    def get_available_main_ids(self, limit: int = 100) -> List[str]:
        """获取可用的MainId列表"""
        try:
            query = self._get_query_instance()
            main_id_list = query.get_all_main_ids(limit=limit)
            logger.info(f"获取到 {len(main_id_list)} 个MainId")
            return main_id_list
        except Exception as e:
            logger.error(f"获取MainId列表失败: {str(e)}")
            raise Exception(f"获取MainId列表失败: {str(e)}")

    def get_cycle_curve_data(self, main_id: str) -> Dict[str, Any]:
        """获取循环曲线数据"""
        try:
            query = self._get_query_instance()
            cycle_curve_result = query.get_cycle_curve(main_id)

            if "error" in cycle_curve_result:
                logger.warning(f"数据库查询出错(MainId={main_id}): {cycle_curve_result['error']}")
                # 不再使用模拟数据，直接抛出异常
                raise Exception(f"无法获取MainId={main_id}的循环曲线数据，蓝殿数据库连接失败")

            # 提取并格式化数据
            cycle_data = cycle_curve_result.get("循环曲线", [])

            # 提取数据用于绘图
            cycles = []
            discharge_capacities = []
            charge_capacities = []

            for cycle in cycle_data:
                cycle_num = cycle.get("循环号")
                discharge_cap = cycle.get("放电容量(Ah)")
                charge_cap = cycle.get("充电容量(Ah)")

                if cycle_num is not None:
                    cycles.append(cycle_num)
                    discharge_capacities.append(discharge_cap if discharge_cap is not None else 0)
                    charge_capacities.append(charge_cap if charge_cap is not None else 0)

            # 如果没有数据，抛出异常
            if not cycles:
                logger.warning(f"MainId={main_id}没有循环数据")
                raise Exception(f"MainId={main_id}在蓝殿数据库中没有找到循环曲线数据")

            return {
                "main_id": main_id,
                "total_cycles": len(cycles),
                "cycle_data": cycle_data,
                "plotting_data": {
                    "cycles": cycles,
                    "discharge_capacities": discharge_capacities,
                    "charge_capacities": charge_capacities
                },
                "summary": {
                    "max_discharge_capacity": max(discharge_capacities) if discharge_capacities else 0,
                    "final_discharge_capacity": discharge_capacities[-1] if discharge_capacities else 0,
                    "capacity_retention": (discharge_capacities[-1] / discharge_capacities[0] * 100) if len(discharge_capacities) > 1 and discharge_capacities[0] > 0 else 0
                },
                "data_source": "landian_database"
            }

        except Exception as e:
            logger.error(f"获取循环曲线数据失败 (MainId={main_id}): {str(e)}")
            # 不再使用模拟数据，直接抛出异常
            raise Exception(f"无法获取MainId={main_id}的循环曲线数据: {str(e)}")

    def get_cycle_details_data(self, main_id: str, cycle_number: int) -> Dict[str, Any]:
        """获取特定循环的详细数据"""
        try:
            query = self._get_query_instance()
            cycle_detail_result = query.get_cycle_details(main_id, cycle_number)

            if "error" in cycle_detail_result:
                raise Exception(cycle_detail_result['error'])

            # 提取详细记录数据
            detailed_records = cycle_detail_result.get("详细记录数据", {}).get("采样记录", [])

            # 提取电压、容量、电流等关键数据
            voltages = []
            capacities = []
            currents = []
            time_points = []

            for i, record in enumerate(detailed_records):
                voltage = record.get('Voltage')
                capacity = record.get('Capacity')
                current = record.get('Current')

                if voltage is not None:
                    voltages.append(voltage)
                    capacities.append(capacity if capacity is not None else 0)
                    currents.append(current if current is not None else 0)
                    time_points.append(i)

            return {
                "main_id": main_id,
                "cycle_number": cycle_number,
                "total_records": len(detailed_records),
                "detailed_records": detailed_records,
                "plotting_data": {
                    "time_points": time_points,
                    "voltages": voltages,
                    "capacities": capacities,
                    "currents": currents
                },
                "summary": {
                    "max_voltage": max(voltages) if voltages else 0,
                    "min_voltage": min(voltages) if voltages else 0,
                    "max_capacity": max(capacities) if capacities else 0,
                    "final_capacity": capacities[-1] if capacities else 0
                }
            }

        except Exception as e:
            logger.error(f"获取循环详细数据失败 (MainId={main_id}, Cycle={cycle_number}): {str(e)}")
            raise Exception(f"获取循环详细数据失败: {str(e)}")

    def generate_capacity_fade_plot(self, main_id: str) -> str:
        """生成容量衰减曲线图并返回base64编码的图片"""
        try:
            data = self.get_cycle_curve_data(main_id)
            plotting_data = data["plotting_data"]

            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei']
            plt.rcParams['axes.unicode_minus'] = False

            # 创建图表
            fig, ax = plt.subplots(figsize=(12, 8))

            cycles = plotting_data["cycles"]
            discharge_capacities = plotting_data["discharge_capacities"]
            charge_capacities = plotting_data["charge_capacities"]

            # 绘制曲线
            ax.plot(cycles, discharge_capacities, 'b-o', linewidth=2, markersize=6, label='放电容量')
            if any(cap > 0 for cap in charge_capacities):
                ax.plot(cycles, charge_capacities, 'r-s', linewidth=2, markersize=6, label='充电容量')

            ax.set_xlabel("循环次数", fontsize=14)
            ax.set_ylabel("容量 (Ah)", fontsize=14)
            ax.set_title(f"电池充放电容量衰减曲线 (MainId: {main_id})", fontsize=16)
            ax.grid(True, alpha=0.3)
            ax.legend()

            # 添加数值标签
            for i, (cycle, capacity) in enumerate(zip(cycles, discharge_capacities)):
                if capacity is not None and i % max(1, len(cycles)//10) == 0:  # 显示部分标签避免过于密集
                    ax.annotate(f"{capacity:.2f}",
                              xy=(cycle, capacity),
                              xytext=(0, 5),
                              textcoords="offset points",
                              ha='center',
                              fontsize=8)

            # 添加统计信息
            summary = data["summary"]
            ax.text(0.02, 0.98, f"初始容量: {summary['max_discharge_capacity']:.2f} Ah\n"
                                f"最终容量: {summary['final_discharge_capacity']:.2f} Ah\n"
                                f"容量保持率: {summary['capacity_retention']:.1f}%",
                   transform=ax.transAxes,
                   verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

            plt.tight_layout()

            # 保存为base64图片
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
            img_buffer.seek(0)
            plot_data = base64.b64encode(img_buffer.getvalue()).decode()
            plt.close()

            return plot_data

        except Exception as e:
            logger.error(f"生成容量衰减图失败 (MainId={main_id}): {str(e)}")
            raise Exception(f"生成容量衰减图失败: {str(e)}")

    def generate_voltage_capacity_plot(self, main_id: str, cycle_number: int) -> str:
        """生成电压-容量曲线图并返回base64编码的图片"""
        try:
            data = self.get_cycle_details_data(main_id, cycle_number)
            plotting_data = data["plotting_data"]

            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei']
            plt.rcParams['axes.unicode_minus'] = False

            # 创建图表
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

            time_points = plotting_data["time_points"]
            voltages = plotting_data["voltages"]
            capacities = plotting_data["capacities"]

            # 上图：电压曲线
            ax1.plot(time_points, voltages, 'b-', linewidth=2, label='电压')
            ax1.set_ylabel('电压 (V)', fontsize=14, color='b')
            ax1.tick_params(axis='y', labelcolor='b')
            ax1.set_title(f'第{cycle_number}次循环电压变化曲线 (MainId: {main_id})', fontsize=16)
            ax1.grid(True, alpha=0.3)
            ax1.legend()

            # 下图：容量曲线
            ax2.plot(time_points, capacities, 'r-', linewidth=2, label='容量')
            ax2.set_xlabel('记录序号', fontsize=14)
            ax2.set_ylabel('容量 (Ah)', fontsize=14, color='r')
            ax2.tick_params(axis='y', labelcolor='r')
            ax2.set_title(f'第{cycle_number}次循环容量变化曲线 (MainId: {main_id})', fontsize=16)
            ax2.grid(True, alpha=0.3)
            ax2.legend()

            plt.tight_layout()

            # 保存为base64图片
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
            img_buffer.seek(0)
            plot_data = base64.b64encode(img_buffer.getvalue()).decode()
            plt.close()

            return plot_data

        except Exception as e:
            logger.error(f"生成电压-容量图失败 (MainId={main_id}, Cycle={cycle_number}): {str(e)}")
            raise Exception(f"生成电压-容量图失败: {str(e)}")

    
    def close(self):
        """关闭数据库连接"""
        if self.query_instance:
            try:
                self.query_instance.close()
                logger.info("蓝殿数据库连接已关闭")
            except Exception as e:
                logger.error(f"关闭数据库连接时出错: {str(e)}")

# 全局实例
data_fetcher = None

def get_data_fetcher():
    """获取数据获取器实例"""
    global data_fetcher
    if data_fetcher is None:
        data_fetcher = ChargeDischargeDataFetcher()
    return data_fetcher

def close_data_fetcher():
    """关闭数据获取器"""
    global data_fetcher
    if data_fetcher:
        data_fetcher.close()
        data_fetcher = None