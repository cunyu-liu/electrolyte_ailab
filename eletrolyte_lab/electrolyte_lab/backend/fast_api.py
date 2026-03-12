#!/usr/bin/env python3
"""
超快速API端点 - 500毫秒内响应
"""

from flask import Flask, request, jsonify, Blueprint
from flask_cors import cross_origin
import time
import json
from app_bk.ai_designer.parser import RequestParser

# 创建Flask应用
app = Flask(__name__)
# 设置配置
app.config['JSON_SORT_KEYS'] = False

# 创建蓝图
fast_bp = Blueprint('fast_api', __name__)

# 初始化解析器
parser = RequestParser()

@fast_bp.route('/parse', methods=['POST'])
@cross_origin()
def fast_parse():
    """超快速需求解析 - 500ms内响应"""
    try:
        start_time = time.time()

        # 最快速度获取数据
        data = request.get_json(force=True)  # 强制解析，无超时

        input_text = data.get('input', '').strip()
        if not input_text:
            return jsonify({
                'success': False,
                'error': '输入不能为空'
            }), 400

        # 直接解析（<0.01秒）
        result = parser.parse_request(input_text)

        # 最快速度返回（移除所有不必要操作）
        parse_time = time.time() - start_time

        return jsonify({
            'success': True,
            'data': result,
            'parse_time_ms': int(parse_time * 1000)
        })

    except Exception as e:
        # 即使出错也要快速返回
        return jsonify({
            'success': False,
            'error': str(e)[:100],  # 限制错误信息长度
            'parse_time_ms': -1
        })

@fast_bp.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    """健康检查 - 50ms内响应"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'response_time': 'fast'
    })

# 注册蓝图
app.register_blueprint(fast_bp, url_prefix='/api')

if __name__ == '__main__':
    # 在5009端口运行
    app.run(host='0.0.0.0', port=5009, debug=False)