#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cv2
import json
import time
from flask import Flask, Response, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 允许跨域访问

# 全局变量存储视频捕获对象
caps = {}

def get_rtsp_url(channel: int,
                      ip="192.168.80.44",
                      username="admin",
                      password="SZKJ2025"):
    """
    生成海康威视RTSP URL
    :param channel: 102 / 202 / 302 / 402 等子码流编号
    :return: RTSP URL
    """
    return f"rtsp://{username}:{password}@{ip}:554/Streaming/Channels/{channel}"

def get_frame(channel: int):
    """
    获取指定频道的最新帧
    """
    if channel not in caps:
        # 初始化视频捕获
        rtsp_url = get_rtsp_url(channel)
        cap = cv2.VideoCapture(rtsp_url)

        if not cap.isOpened():
            print(f"无法打开RTSP通道 {channel}")
            return None

        caps[channel] = cap
        print(f"成功启动RTSP通道 {channel}")

    cap = caps[channel]
    if cap is None:
        return None

    ret, frame = cap.read()
    if ret:
        return frame
    else:
        print(f"RTSP通道 {channel} 读取失败，尝试重连...")
        # 尝试重连
        cap.release()
        rtsp_url = get_rtsp_url(channel)
        cap = cv2.VideoCapture(rtsp_url)
        caps[channel] = cap
        return None

@app.route('/api/video/stream_mjpeg/<int:channel>', methods=['GET'])
def stream_mjpeg(channel):
    """提供MJPEG视频流（适用于HTML img标签）"""
    if channel not in [102, 202, 302, 402]:
        return jsonify({'error': '不支持的频道号'}), 400

    def generate():
        while True:
            frame = get_frame(channel)
            if frame is not None:
                # 编码为JPEG
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' +
                           buffer.tobytes() +
                           b'\r\n')
            time.sleep(0.033)  # 约30fps

    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame',
                    headers={'Cache-Control': 'no-cache', 'Connection': 'close'})

@app.route('/api/video/start_stream/<int:channel>', methods=['POST'])
def start_stream(channel):
    """启动指定频道的视频流"""
    if channel not in [102, 202, 302, 402]:
        return jsonify({'success': False, 'message': '不支持的频道号'}), 400

    try:
        # 预热连接
        frame = get_frame(channel)
        if frame is not None:
            return jsonify({
                'success': True,
                'message': f'频道 {channel} 视频流已启动',
                'rtsp_url': get_rtsp_url(channel)
            })
        else:
            return jsonify({
                'success': False,
                'message': f'频道 {channel} 连接失败'
            })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/video/start_all', methods=['POST'])
def start_all_streams():
    """启动所有4个频道的视频流"""
    results = {}
    channels = [102, 202, 302, 402]

    for channel in channels:
        try:
            # 预热连接
            frame = get_frame(channel)
            if frame is not None:
                results[channel] = {'success': True, 'message': '连接成功'}
            else:
                results[channel] = {'success': False, 'message': '连接失败'}
        except Exception as e:
            results[channel] = {'success': False, 'message': str(e)}

    return jsonify({
        'success': True,
        'message': '批量启动完成',
        'results': results
    })

@app.route('/api/video/stop_stream/<int:channel>', methods=['POST'])
def stop_stream(channel):
    """停止指定频道的视频流"""
    if channel not in [102, 202, 302, 402]:
        return jsonify({'success': False, 'message': '不支持的频道号'}), 400

    try:
        if channel in caps:
            caps[channel].release()
            del caps[channel]
            return jsonify({'success': True, 'message': f'频道 {channel} 视频流已停止'})
        else:
            return jsonify({'success': True, 'message': f'频道 {channel} 视频流未启动'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/video/stop_all', methods=['POST'])
def stop_all_streams():
    """停止所有4个频道的视频流"""
    try:
        channels = list(caps.keys())
        for channel in channels:
            caps[channel].release()
        caps.clear()
        return jsonify({
            'success': True,
            'message': '所有视频流已停止'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/video/status', methods=['GET'])
def stream_status():
    """获取所有频道的状态"""
    status = {}
    channels = [102, 202, 302, 402]

    for channel in channels:
        status[channel] = {
            'active': channel in caps and caps[channel] is not None,
            'rtsp_url': get_rtsp_url(channel)
        }

    return jsonify({'success': True, 'data': status})

if __name__ == '__main__':
    print("启动RTSP视频流服务器...")
    print("支持4个频道:")
    print("  - 频道102: 配液监控")
    print("  - 频道202: 注液封口监控")
    print("  - 频道302: 组装监控")
    print("  - 频道402: 性能测试监控")
    print("服务器地址: http://localhost:5009")
    print("视频流地址:")
    print("  - http://localhost:5009/api/video/stream_mjpeg/102")
    print("  - http://localhost:5009/api/video/stream_mjpeg/202")
    print("  - http://localhost:5009/api/video/stream_mjpeg/302")
    print("  - http://localhost:5009/api/video/stream_mjpeg/402")

    app.run(host='0.0.0.0', port=5009, debug=True, threaded=True)