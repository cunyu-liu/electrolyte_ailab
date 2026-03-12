from flask import request, jsonify
from fpxh_control.get_landian_result import LandianDataQuery # 核心包
import traceback # 用于打印报错详情

# 接口1：获取【循环寿命曲线】数据
@app.route('/api/battery/cycle-curve', methods=['GET'])
def get_cycle_curve():
    main_id = request.args.get('main_id') # 获取参数 ?main_id=xxx
    if not main_id:
        return jsonify({"code": 400, "msg": "缺少 main_id 参数"}), 400

    query = LandianDataQuery(LANDIAN_DB_CONFIG) # 连接数据库
    try:
        # 查询原始数据
        result = query.get_cycle_curve(main_id)
        
        # 错误检查
        if isinstance(result, dict) and "error" in result:
            return jsonify({"code": 500, "msg": result['error']}), 500

        # 提取 x轴(循环号) 和 y轴(容量)
        cycles = []
        capacities = []
        for item in result.get("循环曲线", []):
            cycles.append(item.get("循环号"))
            capacities.append(item.get("放电容量(Ah)"))

        return jsonify({
            "code": 200,
            "data": {
                "x_axis": cycles,
                "y_axis": capacities
            }
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"code": 500, "msg": str(e)}), 500
    finally:
        query.close() # 必须关闭连接！


# 接口2：获取【单圈详细】数据（电压/容量曲线）
@app.route('/api/battery/cycle-detail', methods=['GET'])
def get_cycle_detail():
    main_id = request.args.get('main_id')
    cycle_no = request.args.get('cycle_no') # 获取参数 ?main_id=xxx&cycle_no=30
    
    if not main_id or not cycle_no:
        return jsonify({"code": 400, "msg": "缺少 main_id 或 cycle_no"}), 400

    query = LandianDataQuery(LANDIAN_DB_CONFIG)
    try:
        # 查询详细记录
        result = query.get_cycle_details(main_id, int(cycle_no))
        
        if isinstance(result, dict) and "error" in result:
            return jsonify({"code": 500, "msg": result['error']}), 500

        records = result.get("详细记录数据", {}).get("采样记录", [])
        
        # 提取电压和容量列表
        voltages = [r.get('Voltage') for r in records]
        capacities = [r.get('Capacity') for r in records]

        return jsonify({
            "code": 200,
            "data": {
                "voltages": voltages,    # 电压点序列
                "capacities": capacities # 容量点序列
            }
        })
    except ValueError:
        return jsonify({"code": 400, "msg": "cycle_no 必须是整数"}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"code": 500, "msg": str(e)}), 500
    finally:
        query.close()