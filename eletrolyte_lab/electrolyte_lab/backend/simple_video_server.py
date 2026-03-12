#!/usr/bin/env python3
"""
简化版视频服务器 - 专门用于RTSP视频流API
解决复杂Flask应用的启动阻塞问题
"""

from flask import Flask, jsonify, request, Response, stream_with_context
from flask_cors import CORS
import json
import time
import threading
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
CORS(app)

# 全局变量
rtsp_manager = None

def get_rtsp_manager():
    """懒加载RTSP管理器"""
    global rtsp_manager
    if rtsp_manager is None:
        try:
            from app_bk.ai_experimenter.rtsp_stream import stream_manager
            rtsp_manager = stream_manager
            logger.info("RTSP流管理器初始化成功")
        except Exception as e:
            logger.error(f"RTSP流管理器初始化失败: {e}")
            # 创建模拟管理器
            rtsp_manager = MockStreamManager()
    return rtsp_manager

class MockStreamManager:
    """模拟流管理器 - 当真实RTSP不可用时使用"""

    def __init__(self):
        self.cameras = {
            'camera_1': {'name': '配液监控摄像头', 'channel': 102, 'is_running': False},
            'camera_2': {'name': '注液封口监控', 'channel': 202, 'is_running': False},
            'camera_3': {'name': '性能测试监控', 'channel': 302, 'is_running': False},
            'camera_4': {'name': '环境监控摄像头', 'channel': 402, 'is_running': False}
        }

    def initialize_cameras(self):
        logger.info("模拟摄像头初始化完成")

    def start_camera(self, camera_id):
        if camera_id in self.cameras:
            self.cameras[camera_id]['is_running'] = True
            logger.info(f"模拟摄像头 {camera_id} 启动成功")
            return True
        return False

    def stop_camera(self, camera_id):
        if camera_id in self.cameras:
            self.cameras[camera_id]['is_running'] = False
            logger.info(f"模拟摄像头 {camera_id} 停止成功")

    def get_camera_status(self, camera_id):
        if camera_id in self.cameras:
            camera = self.cameras[camera_id]
            return {
                'camera_id': camera_id,
                'name': camera['name'],
                'channel': camera['channel'],
                'is_running': camera['is_running'],
                'frame_count': 100 if camera['is_running'] else 0,
                'runtime_seconds': 60 if camera['is_running'] else 0,
                'last_frame_time': time.time() if camera['is_running'] else None,
                'last_error': None,
                'queue_size': 2 if camera['is_running'] else 0
            }
        return None

    def get_all_cameras_status(self):
        return {
            'total_cameras': len(self.cameras),
            'cameras': {camera_id: self.get_camera_status(camera_id) for camera_id in self.cameras}
        }

    def get_camera_frame(self, camera_id):
        if camera_id in self.cameras and self.cameras[camera_id]['is_running']:
            # 返回模拟帧数据
            return {
                'camera_id': camera_id,
                'name': self.cameras[camera_id]['name'],
                'channel': self.cameras[camera_id]['channel'],
                'timestamp': datetime.now().isoformat(),
                'frame_data': 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==', # 1x1像素透明图片
                'resolution': [640, 480],
                'frame_count': 100,
                'runtime_seconds': 60
            }
        return None

# API路由
@app.route('/api/ai-experimenter/rtsp/camera/status', methods=['GET'])
def get_camera_status():
    """获取摄像头状态"""
    try:
        camera_id = request.args.get('camera_id')
        manager = get_rtsp_manager()

        if camera_id:
            status = manager.get_camera_status(camera_id)
            if status:
                return jsonify({
                    'success': True,
                    'camera_status': status
                })
            else:
                return jsonify({'error': f'摄像头 {camera_id} 不存在'}), 404
        else:
            all_status = manager.get_all_cameras_status()
            return jsonify({
                'success': True,
                'all_status': all_status
            })
    except Exception as e:
        logger.error(f"获取摄像头状态失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai-experimenter/rtsp/camera/start', methods=['POST'])
def start_camera():
    """启动摄像头"""
    try:
        data = request.get_json() or {}
        camera_id = data.get('camera_id')

        manager = get_rtsp_manager()
        manager.initialize_cameras()

        if camera_id:
            success = manager.start_camera(camera_id)
            return jsonify({
                'success': True,
                'message': f'摄像头 {camera_id} {"启动成功" if success else "启动失败"}'
            })
        else:
            # 启动所有摄像头
            results = {}
            for cid in ['camera_1', 'camera_2', 'camera_3', 'camera_4']:
                results[cid] = manager.start_camera(cid)
            return jsonify({
                'success': True,
                'results': results,
                'message': '批量启动摄像头完成'
            })
    except Exception as e:
        logger.error(f"启动摄像头失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai-experimenter/rtsp/camera/stop', methods=['POST'])
def stop_camera():
    """停止摄像头"""
    try:
        data = request.get_json() or {}
        camera_id = data.get('camera_id')

        manager = get_rtsp_manager()

        if camera_id:
            manager.stop_camera(camera_id)
            return jsonify({
                'success': True,
                'message': f'摄像头 {camera_id} 已停止'
            })
        else:
            # 停止所有摄像头
            for cid in ['camera_1', 'camera_2', 'camera_3', 'camera_4']:
                manager.stop_camera(cid)
            return jsonify({
                'success': True,
                'message': '所有摄像头已停止'
            })
    except Exception as e:
        logger.error(f"停止摄像头失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai-experimenter/rtsp/camera/frame/<camera_id>', methods=['GET'])
def get_camera_frame(camera_id):
    """获取摄像头帧"""
    try:
        manager = get_rtsp_manager()
        frame_data = manager.get_camera_frame(camera_id)

        if frame_data:
            return jsonify({
                'success': True,
                'frame': frame_data
            })
        else:
            return jsonify({
                'error': f'摄像头 {camera_id} 无数据或未启动',
                'camera_id': camera_id
            }), 404
    except Exception as e:
        logger.error(f"获取摄像头帧失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai-experimenter/rtsp/camera/list', methods=['GET'])
def list_cameras():
    """列出所有摄像头"""
    try:
        cameras = [
            {
                'camera_id': 'camera_1',
                'name': '配液监控摄像头',
                'channel': 102,
                'description': '配液过程监控'
            },
            {
                'camera_id': 'camera_2',
                'name': '注液封口监控',
                'channel': 202,
                'description': '注液和封口过程监控'
            },
            {
                'camera_id': 'camera_3',
                'name': '性能测试监控',
                'channel': 302,
                'description': '电池性能测试监控'
            },
            {
                'camera_id': 'camera_4',
                'name': '环境监控摄像头',
                'channel': 402,
                'description': '实验室环境监控'
            }
        ]

        manager = get_rtsp_manager()
        current_status = manager.get_all_cameras_status()

        return jsonify({
            'success': True,
            'cameras': cameras,
            'total': len(cameras),
            'current_status': current_status
        })
    except Exception as e:
        logger.error(f"列出摄像头失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'simple-video-server'
    })

if __name__ == '__main__':
    logger.info("启动简化版视频服务器...")
    logger.info("健康检查: http://localhost:5009/health")

    try:
        app.run(
            host='0.0.0.0',
            port=5008,
            debug=False,  # 关闭调试模式避免自动重启
            threaded=True
        )
    except Exception as e:
        logger.error(f"启动服务器失败: {e}")
        import traceback
        traceback.print_exc()