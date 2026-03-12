from flask import Blueprint, request, jsonify, Response, stream_with_context
from flask import Response, stream_with_context
from .video_now import generate_frames, check_camera_availability
from app_bk.ai_experimenter.experiment_executor import ExperimentExecutor
from app_bk.ai_experimenter.monitor import ProcessMonitor
from app_bk.ai_experimenter.rtsp_stream import stream_manager
from extensions import db
from models import Experiment, ExperimentResult
from fpxh_control import InjectionController,query_order
from backend.app import injector_obj_list
import logging
import threading
import time
import subprocess

# 创建蓝图
ai_experimenter_bp = Blueprint('ai_experimenter', __name__)
logger = logging.getLogger(__name__)

# 全局实验执行器
experiment_executor = ExperimentExecutor()
process_monitor = ProcessMonitor()

# 当前运行的实验
running_experiments = {}

@ai_experimenter_bp.route('/video/get/<int:channel>', methods=['GET'])
def video_feed(channel):
    """视频流接口"""
    # 直接使用导入的函数
    return Response(generate_frames(channel),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@ai_experimenter_bp.route('/video/start/<int:channel>', methods=['GET'])
def start_channel(channel):
    """启动摄像头通道"""
    logger.info("启动摄像头")
    try:
        # 使用 camera_utils 中的检查逻辑，代码更干净
        if check_camera_availability(channel):
            return jsonify({
                "status": "success",
                "message": f"通道 {channel} 可用",
                "channel": channel
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"通道 {channel} 不可用"
            }), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ai_experimenter_bp.route('/battery/query', methods=['GET'])
def battery_query():
    """曲线1"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体为空'}), 400
        
    project_id = data.get("project_id")
    bottle_no = data.get("bottle_no")
    battery_no = data.get("battery_no")

    if not project_id:
        return jsonify({'error': '缺少 project_id'}), 400
    
    if not bottle_no:
        return jsonify({'error': '缺少 bottle_no'}), 400
    
    if not battery_no:
        return jsonify({'error': '缺少 battery_no'}), 400
    
    order_dict = None
    order_dict = query_order(project_id)

    if order_dict is None:
        logger.warning(f"查询失败：未找到项目 {project_id} 对应的实验实例")
        return jsonify({
            'success': False,
            'error': '未找到相关实验实例或实验已结束',
            'project_id': project_id
        }), 404
    else:
        try:
            battery_info = order_dict["details"]["calculated_recipes"][str(bottle_no)]["battery_info"][battery_no]
            
            # 如果成功拿到数据，继续你的逻辑
            print("拿到数据:", battery_info)

        except (KeyError, TypeError, AttributeError):
            # 这里处理“没有的话返回错误”的逻辑
            return jsonify({'error': "找不到指定的电池信息或路径不存在"}), 500
        else:
            # 数据库配置
            db_config = {
                'host': '101.6.160.48',
                'port': 50003,
                'user': 'landian',
                'password': '123456',
                'database': 'electrolyte'
            }

            from fpxh_control.get_landian_result import LandianDataQuery
            import matplotlib.pyplot as plt

            # 创建查询实例
            query = LandianDataQuery(db_config)

            device_no = battery_info["landian_device_no"]
            channel_no = battery_info["landian_channel_no"]
            time_stamp = battery_info["landian_timestamp"]
            cycle_curve_result = query.get_cycle_curve(device_no,channel_no,time_stamp)
            # 打印结果
            if "error" in cycle_curve_result:
                print(f"错误: {cycle_curve_result['error']}")
            else:
                if "error" in cycle_curve_result:
                    print(f"蓝电查询错误: {cycle_curve_result['error']}")
                    return jsonify({'success': False, 'error': cycle_curve_result['error']}), 500
                
                # 准备两个列表，或者一个对象列表，看前端喜欢哪种格式
                # 这里推荐返回对象列表，通用性强
                chart_data = []

                raw_list = cycle_curve_result.get("循环曲线", [])
                for item in raw_list:
                    # 过滤掉无效数据
                    if item["循环号"] is not None and item["放电容量(Ah)"] is not None:
                        chart_data.append({
                            "cycle": item["循环号"],       # x轴数据
                            "capacity": item["放电容量(Ah)"] # y轴数据
                        })

                # 返回 JSON 给前端
                return jsonify({
                    'success': True,
                    'message': "获取成功",
                    'data': {
                        'title': f"放电容量衰减曲线 (瓶{bottle_no}-电{battery_no})",
                        'points': chart_data  # 前端拿这个数组去循环画图
                    }
                })
        finally:
            # 关闭数据库连接
            query.close()

#前端传递四个参数
@ai_experimenter_bp.route('/battery/query/details', methods=['GET'])
def battery_query_details():
    """曲线2"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体为空'}), 400
        
    project_id = data.get("project_id")
    bottle_no = data.get("bottle_no")
    battery_no = data.get("battery_no")
    cycle_no = data.get("cycle_no")

    if not project_id:
        return jsonify({'error': '缺少 project_id'}), 400
    
    if not bottle_no:
        return jsonify({'error': '缺少 bottle_no'}), 400
    
    if not battery_no:
        return jsonify({'error': '缺少 battery_no'}), 400
    
    if not cycle_no:
        return jsonify({'error': '缺少 cycle_no'}), 400
    
    order_dict = None
    order_dict = query_order(project_id)

    if order_dict is None:
        logger.warning(f"查询失败：未找到项目 {project_id} 对应的实验实例")
        return jsonify({
            'success': False,
            'error': '未找到相关实验实例或实验已结束',
            'project_id': project_id
        }), 404
    else:
        try:
            # 注意：这里我把 .get() 换成了 []，并且加了 str() 转换
            # 这样只要任何一层找不到，就会直接跳到 except
            battery_info = order_dict["details"]["calculated_recipes"][str(bottle_no)]["battery_info"][battery_no]
            
            # 如果成功拿到数据，继续你的逻辑
            print("拿到数据:", battery_info)

        except (KeyError, TypeError, AttributeError):
            # 这里处理“没有的话返回错误”的逻辑
            return jsonify({'error': "找不到指定的电池信息或路径不存在"}), 500
        else:
            # 数据库配置
            db_config = {
                'host': '101.6.160.48',
                'port': 50003,
                'user': 'landian',
                'password': '123456',
                'database': 'electrolyte'
            }

            from fpxh_control.get_landian_result import LandianDataQuery

            # 创建查询实例
            query = LandianDataQuery(db_config)

            device_no = battery_info["landian_device_no"]
            channel_no = battery_info["landian_channel_no"]
            time_stamp = battery_info["landian_timestamp"]
            try:
                # 2. 调用你的数据库查询逻辑
                cycle_detail_result = query.get_cycle_details(device_no,channel_no,time_stamp, cycle_no)

                if "error" in cycle_detail_result:
                    return jsonify({
                        "code": 500, 
                        "message": cycle_detail_result['error'], 
                        "data": None
                    })
                
                else:
                    records = cycle_detail_result["详细记录数据"]["采样记录"]
                    
                    # --- 数据处理与清洗 ---
                    x_axis_data = [] # 序号
                    voltages = []    # 电压数据
                    capacities = []  # 容量数据

                    for index, r in enumerate(records):
                        # 确保数据非空
                        if r.get('Voltage') is not None and r.get('Capacity') is not None:
                            x_axis_data.append(index + 1)
                            # !重要：数据库的 Decimal 类型必须转为 float，否则 jsonify 会报错
                            voltages.append(float(r['Voltage']))
                            capacities.append(float(r['Capacity']))

                    # 3. 构造返回给前端的 JSON 结构
                    response_data = {
                        "code": 200,
                        "message": "success",
                        "data": {
                            "title": f"工步{cycle_no} 电压-容量曲线",
                            "xAxis": x_axis_data,
                            "series": [
                                {
                                    "name": "电压",
                                    "type": "voltage",
                                    "unit": "V",
                                    "data": voltages
                                },
                                {
                                    "name": "容量",
                                    "type": "capacity",
                                    "unit": "Ah",
                                    "data": capacities
                                }
                            ]
                        }
                    }
                    
                    # 使用 jsonify 返回标准的 JSON 响应
                    return jsonify(response_data)

            except Exception as e:
                print(f"Server Error: {str(e)}")
                return jsonify({"code": 500, "message": f"服务器内部错误: {str(e)}", "data": None}), 500

            finally:
                # 关闭数据库连接
                query.close()

@ai_experimenter_bp.route('/experimenter/curve', methods=['GET'])
def experimenter_curve():
#测试曲线
    db_config = {
                'host': '101.6.160.48',
                'port': 50003,
                'user': 'landian',
                'password': '123456',
                'database': 'electrolyte'
            }

    from fpxh_control.get_landian_result import LandianDataQuery
    import matplotlib.pyplot as plt

    # 创建查询实例
    query = LandianDataQuery(db_config)

    cycle_curve_result = query.get_cycle_curve(2,69,1763614629)
    # 打印结果
    if "error" in cycle_curve_result:
        print(f"错误: {cycle_curve_result['error']}")
    else:
        if "error" in cycle_curve_result:
            print(f"蓝电查询错误: {cycle_curve_result['error']}")
            return jsonify({'success': False, 'error': cycle_curve_result['error']}), 500
        
        # 准备两个列表，或者一个对象列表，看前端喜欢哪种格式
        # 这里推荐返回对象列表，通用性强
        chart_data = []

        raw_list = cycle_curve_result.get("循环曲线", [])
        for item in raw_list:
            # 过滤掉无效数据
            if item["循环号"] is not None and item["放电容量(Ah)"] is not None:
                chart_data.append({
                    "cycle": item["循环号"],       # x轴数据
                    "capacity": item["放电容量(Ah)"] # y轴数据
                })

        # 返回 JSON 给前端
        return jsonify({
            'success': True,
            'message': "获取成功",
            'data': {
                'title': f"放电容量衰减曲线",
                'points': chart_data  # 前端拿这个数组去循环画图
            }
        })
            
@ai_experimenter_bp.route('/experimenter/state', methods=['GET'])
def experimenter_state():
    """
    查看注射系统状态: '启动', '组装中', '组装完成', '测试中', '失败', '完成'
    """

    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体为空'}), 400
        
    project_id = data.get("project_id")

    if not project_id:
        return jsonify({'error': '缺少 project_id'}), 400
    
    order_dict = query_order(project_id)

    if order_dict is None:
        logger.warning(f"查询失败：未找到项目 {project_id} 对应的实验数据")
        return jsonify({
            'success': False,
            'error': '未找到相关实验数据',
            'project_id': project_id
        }), 404
    else:
        status = order_dict["status"]
        logger.info(f"订单：{project_id} 获取注射系统状态成功")
        return jsonify({"code":200, "message":True, "data":status}) 
    
@ai_experimenter_bp.route('/experimenter/all', methods=['GET'])
def experimenter_all():
    """
    查看注射系统全部信息
    """

    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体为空'}), 400
        
    project_id = data.get("project_id")

    if not project_id:
        return jsonify({'error': '缺少 project_id'}), 400
    
    order_dict = query_order(project_id)

    if order_dict is None:
        logger.warning(f"查询失败：未找到项目 {project_id} 对应的实验数据")
        return jsonify({
            'success': False,
            'error': '未找到相关实验数据',
            'project_id': project_id
        }), 404
    else:
        logger.info(f"订单：{project_id} 获取注射系统数据成功")
        return jsonify({"code":200, "message":True, "data":order_dict}) 
    
@ai_experimenter_bp.route('/experimenter/stop', methods=['POST'])
def experimenter_stop():
    """停止注射系统"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体为空'}), 400
        
    project_id = data.get("project_id")

    if not project_id:
        return jsonify({'error': '缺少 project_id'}), 400
    
    injector = None

    logger.info(f"injector_obj_list:{injector_obj_list}")
    try:
        for ins in injector_obj_list:
            logger.info(f"order_num:{ins.db_manager.get_order(project_id)}")
            if ins.db_manager.get_order(project_id):
                injector = ins
                break  # 找到后立即退出循环
    except Exception as e:
            logger.info("db_manager失败")

    if injector is None:
        logger.warning(f"查询失败：未找到项目 {project_id} 对应的实验实例")
        return jsonify({
            'success': False,
            'error': '未找到相关实验实例或实验已结束',
            'project_id': project_id
        }), 404
    else:
        try:
            injector.stop()
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.info(f"订单：{project_id} 关闭注射系统失败")
            return jsonify({"code":500, "message":False, "data":""})
        logger.info(f"订单：{project_id} 关闭注射系统成功")
        return jsonify({"code":200, "message":True, "data":""}) 
    
@ai_experimenter_bp.route('/experimenter/plc', methods=['GET'])
def test_plc_connections():
    """
    测试PLC连接
    :return: bool - 所有PLC都连接成功返回True，否则返回False
    """
    # 默认的PLC连接配置
    ip_ports = [
        ("192.168.80.80", 502),
        ("192.168.80.50", 503),
        ("192.168.80.10", 8001)
    ]
    timeout = 1000000
    
    all_success = True
    
    for ip, port in ip_ports:
        from pymodbus.client import ModbusTcpClient
        client = ModbusTcpClient(ip, port=port, timeout=timeout)
        try:
            if client.connect():
                logger.info(f"✅ 已连接PLC :{ip}:{port}")
                client.close()  # 测试完成后关闭连接
            else:
                logger.info(f"❌ 未能连接PLC :{ip}:{port}")
                all_success = False
                client.close()
        except Exception as e:
            logger.error(f"❌ 连接PLC {ip}:{port} 时发生异常: {e}")
            all_success = False
            client.close()
    
    if all_success:
        logger.info("✅ 所有PLC连接成功")
        return jsonify({"code":200, "message":True, "data":all_success}) 
    else:
        logger.info("❌ 部分PLC连接失败")
        return jsonify({"code":500, "message":False, "data":all_success}) 