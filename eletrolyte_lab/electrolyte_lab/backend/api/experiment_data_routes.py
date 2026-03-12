"""
实验数据查询API路由
提供从真实实验数据库查询数据的HTTP接口
"""

from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any, List, Optional
import datetime

logger = logging.getLogger(__name__)

# 导入数据库查询模块
try:
    from app_bk.ai_experimenter.database_query import ExperimentDataQuery, LandianDataQueryEnhanced
    logger.info("数据库查询模块导入成功")
except ImportError as e:
    logger.warning(f"无法导入数据库查询模块: {e}")
    # 尝试导入pymysql创建基础实现
    try:
        import pymysql
        logger.info("pymysql库可用，创建基础查询类")

        class ExperimentDataQuery:
            def __init__(self, config):
                self.config = config

            def query_charge_discharge_data(self, experiment_id, **kwargs):
                return []

            def query_resistance_voltage_data(self, experiment_id, **kwargs):
                return []

            def calculate_impedance_from_voltage_data(self, voltage_data, current_threshold=0.1):
                return []

            def get_experiment_summary(self, experiment_id):
                return None

        class LandianDataQueryEnhanced:
            def __init__(self, config):
                self.config = config

            def query_cycle_curve_data(self, main_id):
                return []

            def query_cycle_detail_data(self, main_id, cycle_no):
                return {"data_points": 0}

            def get_all_main_ids(self, limit):
                return []

    except ImportError:
        logger.error("pymysql库也不可用")
        class ExperimentDataQuery:
            def __init__(self, config):
                raise Exception("实验数据查询模块不可用：无法导入数据库查询模块且pymysql库不可用")

        class LandianDataQueryEnhanced:
            def __init__(self, config):
                raise Exception("蓝甸数据库查询模块不可用：pymysql库不可用")

        
# 创建蓝图
experiment_data_bp = Blueprint('experiment_data', __name__, url_prefix='/api/experiment-data')

# 数据库连接配置 - 实际使用时应该从环境变量或配置文件读取
DB_CONFIG = {
    'db_type': 'sqlite',  # 默认使用SQLite，可配置为mysql或postgresql
    'db_path': 'data/experiments.db'  # SQLite数据库路径
}

# 创建全局查询实例
try:
    data_query = ExperimentDataQuery(DB_CONFIG)
    logger.info("实验数据查询实例创建成功")
except Exception as e:
    logger.error(f"创建实验数据查询实例失败: {str(e)}")
    data_query = None

# 蓝甸数据库配置
LANDIAN_DB_CONFIG = {
    'host': '101.6.160.48',
    'port': 50003,
    'user': 'landian',
    'password': '123456',
    'database': 'electrolyte'
}

# 创建蓝甸数据库查询实例
try:
    landian_data_query = LandianDataQueryEnhanced(LANDIAN_DB_CONFIG)
    logger.info("蓝甸数据库连接初始化成功")
except Exception as e:
    logger.warning(f"蓝甸数据库连接初始化失败，将使用模拟数据: {str(e)}")
    landian_data_query = None

@experiment_data_bp.route('/resistance-voltage', methods=['GET'])
def get_resistance_voltage_data():
    """
    获取内阻电压数据

    Query Parameters:
        - experiment_id: 实验ID (必需)
        - start_time: 开始时间 (可选，格式: YYYY-MM-DD HH:MM:SS)
        - end_time: 结束时间 (可选，格式: YYYY-MM-DD HH:MM:SS)
        - cycle_numbers: 循环次数列表 (可选，格式: 1,2,10,50,100)

    Returns:
        JSON响应包含内阻电压数据列表
    """
    try:
        experiment_id = request.args.get('experiment_id')
        if not experiment_id:
            return jsonify({
                'success': False,
                'error': '缺少实验ID参数'
            }), 400

        # 解析可选参数
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')

        cycle_numbers = None
        if request.args.get('cycle_numbers'):
            try:
                cycle_numbers = [int(x.strip()) for x in request.args.get('cycle_numbers').split(',')]
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'cycle_numbers参数格式错误，应为逗号分隔的整数列表'
                }), 400

        # 查询数据
        data = data_query.query_resistance_voltage_data(
            experiment_id=experiment_id,
            start_time=start_time,
            end_time=end_time,
            cycle_numbers=cycle_numbers
        )

        return jsonify({
            'success': True,
            'data': data,
            'total': len(data),
            'message': f'成功查询到 {len(data)} 条内阻电压数据'
        })

    except Exception as e:
        logger.error(f"获取内阻电压数据失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'查询失败: {str(e)}'
        }), 500

@experiment_data_bp.route('/charge-discharge', methods=['GET'])
def get_charge_discharge_data():
    """
    获取充放电曲线数据

    Query Parameters:
        - experiment_id: 实验ID (必需)
        - start_time: 开始时间 (可选)
        - end_time: 结束时间 (可选)
        - cycle_numbers: 循环次数列表 (可选)

    Returns:
        JSON响应包含充放电数据列表
    """
    try:
        experiment_id = request.args.get('experiment_id')
        if not experiment_id:
            return jsonify({
                'success': False,
                'error': '缺少实验ID参数'
            }), 400

        # 解析可选参数
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')

        cycle_numbers = None
        if request.args.get('cycle_numbers'):
            try:
                cycle_numbers = [int(x.strip()) for x in request.args.get('cycle_numbers').split(',')]
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'cycle_numbers参数格式错误'
                }), 400

        # 查询数据
        data = data_query.query_charge_discharge_data(
            experiment_id=experiment_id,
            start_time=start_time,
            end_time=end_time,
            cycle_numbers=cycle_numbers
        )

        return jsonify({
            'success': True,
            'data': data,
            'total': len(data),
            'message': f'成功查询到 {len(data)} 条充放电数据'
        })

    except Exception as e:
        logger.error(f"获取充放电数据失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'查询失败: {str(e)}'
        }), 500

@experiment_data_bp.route('/impedance', methods=['GET'])
def get_impedance_data():
    """
    获取内阻数据 (基于电压数据计算)

    Query Parameters:
        - experiment_id: 实验ID (必需)
        - start_time: 开始时间 (可选)
        - end_time: 结束时间 (可选)
        - cycle_numbers: 循环次数列表 (可选)
        - current_threshold: 电流变化阈值 (可选，默认0.1A)

    Returns:
        JSON响应包含计算得到的内阻数据列表
    """
    try:
        experiment_id = request.args.get('experiment_id')
        if not experiment_id:
            return jsonify({
                'success': False,
                'error': '缺少实验ID参数'
            }), 400

        # 解析可选参数
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')

        cycle_numbers = None
        if request.args.get('cycle_numbers'):
            try:
                cycle_numbers = [int(x.strip()) for x in request.args.get('cycle_numbers').split(',')]
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'cycle_numbers参数格式错误'
                }), 400

        current_threshold = float(request.args.get('current_threshold', 0.1))

        # 先查询电压数据
        voltage_data = data_query.query_resistance_voltage_data(
            experiment_id=experiment_id,
            start_time=start_time,
            end_time=end_time,
            cycle_numbers=cycle_numbers
        )

        # 计算内阻
        impedance_data = data_query.calculate_impedance_from_voltage_data(
            voltage_data, current_threshold=current_threshold
        )

        return jsonify({
            'success': True,
            'data': impedance_data,
            'total': len(impedance_data),
            'message': f'成功计算出 {len(impedance_data)} 个内阻数据点',
            'current_threshold': current_threshold
        })

    except Exception as e:
        logger.error(f"获取内阻数据失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'查询失败: {str(e)}'
        }), 500

@experiment_data_bp.route('/summary/<experiment_id>', methods=['GET'])
def get_experiment_summary(experiment_id: str):
    """
    获取实验汇总信息

    Path Parameters:
        - experiment_id: 实验ID

    Returns:
        JSON响应包含实验汇总统计信息
    """
    try:
        summary = data_query.get_experiment_summary(experiment_id)

        if not summary:
            return jsonify({
                'success': False,
                'error': '未找到实验数据'
            }), 404

        return jsonify({
            'success': True,
            'data': summary,
            'message': '成功获取实验汇总信息'
        })

    except Exception as e:
        logger.error(f"获取实验汇总信息失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'查询失败: {str(e)}'
        }), 500

@experiment_data_bp.route('/experiments', methods=['GET'])
def list_experiments():
    """
    获取所有实验ID列表

    Returns:
        JSON响应包含所有可用的实验ID列表
    """
    try:
        # 这个功能需要根据实际的数据库表结构来实现
        # 这里提供一个示例实现

        # 模拟返回一些实验ID
        mock_experiments = [
            {'id': 'EXP001', 'name': '高能量密度电池测试', 'created_date': '2024-01-15'},
            {'id': 'EXP002', 'name': '长寿命循环测试', 'created_date': '2024-01-20'},
            {'id': 'EXP003', 'name': '低温性能测试', 'created_date': '2024-02-01'},
            {'id': 'EXP004', 'name': '快充性能测试', 'created_date': '2024-02-10'},
            {'id': 'EXP005', 'name': '安全性测试', 'created_date': '2024-02-15'}
        ]

        return jsonify({
            'success': True,
            'data': mock_experiments,
            'total': len(mock_experiments),
            'message': f'成功获取 {len(mock_experiments)} 个实验'
        })

    except Exception as e:
        logger.error(f"获取实验列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'查询失败: {str(e)}'
        }), 500

@experiment_data_bp.route('/config', methods=['POST'])
def update_database_config():
    """
    更新数据库连接配置

    Request Body:
        - db_type: 数据库类型 ('sqlite', 'mysql', 'postgresql')
        - host: 主机地址 (MySQL/PostgreSQL)
        - port: 端口号 (MySQL/PostgreSQL)
        - database: 数据库名称 (MySQL/PostgreSQL)
        - username: 用户名 (MySQL/PostgreSQL)
        - password: 密码 (MySQL/PostgreSQL)
        - db_path: SQLite数据库文件路径 (SQLite)

    Returns:
        JSON响应包含配置更新结果
    """
    try:
        config_data = request.get_json()
        if not config_data:
            return jsonify({
                'success': False,
                'error': '缺少配置数据'
            }), 400

        global data_query

        # 验证数据库类型
        db_type = config_data.get('db_type', '').lower()
        if db_type not in ['sqlite', 'mysql', 'postgresql']:
            return jsonify({
                'success': False,
                'error': '不支持的数据库类型'
            }), 400

        # 创建新的查询实例并测试连接
        try:
            new_query = ExperimentDataQuery(config_data)
            # 测试连接
            conn = new_query._get_connection()

            if conn is None:
                # 模拟模式，允许配置但提示使用模拟数据
                global data_query
                data_query = new_query
                return jsonify({
                    'success': True,
                    'message': f'配置成功，使用模拟数据模式',
                    'config': {k: v for k, v in config_data.items() if k != 'password'},
                    'mode': 'simulation'
                })

            with conn:
                pass  # 如果连接成功，这里不会抛出异常

            # 更新全局实例
            data_query = new_query

            return jsonify({
                'success': True,
                'message': f'成功连接到 {db_type} 数据库',
                'config': {k: v for k, v in config_data.items() if k != 'password'},
                'mode': 'real_database'
            })

        except Exception as conn_error:
            return jsonify({
                'success': False,
                'error': f'数据库连接失败: {str(conn_error)}'
            }), 400

    except Exception as e:
        logger.error(f"更新数据库配置失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'配置更新失败: {str(e)}'
        }), 500

@experiment_data_bp.route('/health', methods=['GET'])
def health_check():
    """
    数据库连接健康检查

    Returns:
        JSON响应包含数据库连接状态
    """
    try:
        # 尝试连接数据库
        conn = data_query._get_connection()

        if conn is None:
            # 使用模拟数据，返回成功状态
            return jsonify({
                'success': True,
                'message': '使用模拟数据模式',
                'db_type': data_query.db_type,
                'mode': 'simulation',
                'timestamp': str(datetime.datetime.now())
            })

        with conn:
            # 简单查询测试连接
            cursor = conn.cursor()
            try:
                if data_query.db_type != 'sqlite':
                    cursor.execute("SELECT 1")
                else:
                    cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
            except Exception as cursor_error:
                cursor.close()
                raise cursor_error

        if result:
            return jsonify({
                'success': True,
                'message': '数据库连接正常',
                'db_type': data_query.db_type,
                'mode': 'real_database',
                'timestamp': str(datetime.datetime.now())
            })
        else:
            raise Exception("数据库查询失败")

    except Exception as e:
        logger.error(f"数据库健康检查失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'数据库连接异常: {str(e)}',
            'db_type': data_query.db_type,
            'timestamp': str(datetime.datetime.now())
        }), 500

# 错误处理
@experiment_data_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': '接口不存在'
    }), 404

# 蓝甸数据库API端点

@experiment_data_bp.route('/landian/cycle-curve', methods=['GET'])
def get_landian_cycle_curve():
    """
    获取蓝甸数据库的循环曲线数据

    Query Parameters:
        - main_id: 电池单元的MainId (必需)

    Returns:
        JSON响应包含充放电循环曲线数据
    """
    try:
        main_id = request.args.get('main_id')
        if not main_id:
            return jsonify({
                'success': False,
                'error': '缺少main_id参数'
            }), 400

        if not landian_data_query:
            return jsonify({
                'success': False,
                'error': '蓝甸数据库不可用'
            }), 503

        data = landian_data_query.query_cycle_curve_data(main_id)

        return jsonify({
            'success': True,
            'data': data,
            'total': len(data),
            'message': f'成功查询到 {len(data)} 条循环曲线数据',
            'main_id': main_id
        })

    except Exception as e:
        logger.error(f"获取蓝甸循环曲线数据失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'查询失败: {str(e)}'
        }), 500

@experiment_data_bp.route('/landian/cycle-detail', methods=['GET'])
def get_landian_cycle_detail():
    """
    获取蓝甸数据库的循环细节数据

    Query Parameters:
        - main_id: 电池单元的MainId (必需)
        - cycle_no: 循环号 (必需)

    Returns:
        JSON响应包含电压-容量曲线数据
    """
    try:
        main_id = request.args.get('main_id')
        cycle_no = request.args.get('cycle_no')

        if not main_id:
            return jsonify({
                'success': False,
                'error': '缺少main_id参数'
            }), 400

        if not cycle_no:
            return jsonify({
                'success': False,
                'error': '缺少cycle_no参数'
            }), 400

        try:
            cycle_no = int(cycle_no)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'cycle_no参数必须是整数'
            }), 400

        if not landian_data_query:
            return jsonify({
                'success': False,
                'error': '蓝甸数据库不可用'
            }), 503

        data = landian_data_query.query_cycle_detail_data(main_id, cycle_no)

        return jsonify({
            'success': True,
            'data': data,
            'message': f'成功查询到MainId={main_id}, CycleNo={cycle_no}的详细数据',
            'main_id': main_id,
            'cycle_no': cycle_no,
            'data_points': data.get('data_points', 0)
        })

    except Exception as e:
        logger.error(f"获取蓝甸循环细节数据失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'查询失败: {str(e)}'
        }), 500

@experiment_data_bp.route('/landian/main-ids', methods=['GET'])
def get_landian_main_ids():
    """
    获取蓝甸数据库中所有的MainId列表

    Query Parameters:
        - limit: 限制返回的数量 (可选，默认100)

    Returns:
        JSON响应包含MainId列表
    """
    try:
        limit = request.args.get('limit', 100, type=int)

        if not landian_data_query or not hasattr(landian_data_query, 'landian_query') or not landian_data_query.landian_query:
            return jsonify({
                'success': False,
                'error': '蓝甸数据库不可用'
            }), 503

        main_ids = landian_data_query.landian_query.get_all_main_ids(limit)

        return jsonify({
            'success': True,
            'data': main_ids,
            'total': len(main_ids),
            'message': f'成功获取 {len(main_ids)} 个MainId'
        })

    except Exception as e:
        logger.error(f"获取蓝甸MainId列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'查询失败: {str(e)}'
        }), 500

@experiment_data_bp.route('/landian/config', methods=['POST'])
def update_landian_db_config():
    """
    更新蓝甸数据库连接配置

    Request Body:
        - host: 数据库主机地址
        - port: 数据库端口
        - user: 用户名
        - password: 密码
        - database: 数据库名

    Returns:
        JSON响应包含配置更新结果
    """
    try:
        global landian_data_query

        config_data = request.get_json()
        if not config_data:
            return jsonify({
                'success': False,
                'error': '缺少配置数据'
            }), 400

        # 验证必需字段
        required_fields = ['host', 'port', 'user', 'password', 'database']
        for field in required_fields:
            if field not in config_data:
                return jsonify({
                    'success': False,
                    'error': f'缺少必需字段: {field}'
                }), 400

        try:
            new_query = LandianDataQueryEnhanced(config_data)
            # 测试连接 - 尝试获取MainId列表
            if hasattr(new_query, 'landian_query') and new_query.landian_query:
                test_ids = new_query.landian_query.get_all_main_ids(limit=1)
                # 如果成功获取到数据，说明连接正常
                landian_data_query = new_query

                return jsonify({
                    'success': True,
                    'message': '蓝甸数据库连接配置成功',
                    'config': {k: v for k, v in config_data.items() if k != 'password'},
                    'test_result': f'成功连接，获取到 {len(test_ids)} 个MainId'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '蓝甸数据库连接失败'
                }), 400

        except Exception as conn_error:
            return jsonify({
                'success': False,
                'error': f'蓝甸数据库连接失败: {str(conn_error)}'
            }), 400

    except Exception as e:
        logger.error(f"更新蓝甸数据库配置失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'配置更新失败: {str(e)}'
        }), 500


@experiment_data_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': '接口不存在'
    }), 404

@experiment_data_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': '服务器内部错误'
    }), 500