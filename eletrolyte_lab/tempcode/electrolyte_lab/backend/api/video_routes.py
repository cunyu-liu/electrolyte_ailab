from flask import Blueprint, Response, jsonify, request
import cv2
import threading
import queue
import time
from . import auth

video_bp = Blueprint('video', __name__)

# 全局变量存储视频流
stream_threads = {}
frame_queues = {}
active_streams = {}

def get_rtsp_url(channel: int, ip="192.168.80.44", username="admin", password="SZKJ2025"):
    """
    生成海康威视RTSP URL
    :param channel: 102 / 202 / 302 / 402 等子码流编号
    :return: RTSP URL
    """
    return f"rtsp://{username}:{password}@{ip}:554/Streaming/Channels/{channel}"

def camera_stream_generator(channel: int):
    """
    生成器函数，持续从RTSP流获取帧
    """
    rtsp_url = get_rtsp_url(channel)
    cap = cv2.VideoCapture(rtsp_url)

    if not cap.isOpened():
        print(f"无法打开RTSP通道 {channel}")
        return

    print(f"成功启动RTSP通道 {channel}")

    while active_streams.get(channel, False):
        ret, frame = cap.read()
        if not ret:
            print(f"RTSP通道 {channel} 读取失败，尝试重连...")
            time.sleep(1)
            # 尝试重连
            cap.release()
            cap = cv2.VideoCapture(rtsp_url)
            continue

        # 将帧放入队列
        try:
            frame_queues[channel].put_nowait(frame)
        except queue.Full:
            # 如果队列满了，丢弃最旧的帧
            try:
                frame_queues[channel].get_nowait()
                frame_queues[channel].put_nowait(frame)
            except:
                pass

    cap.release()
    print(f"RTSP通道 {channel} 已停止")

@video_bp.route('/start_stream/<int:channel>', methods=['POST'])
@auth.token_required
def start_stream(channel):
    """启动指定频道的视频流"""
    if channel not in [102, 202, 302, 402]:
        return jsonify({'success': False, 'message': '不支持的频道号'}), 400

    # 如果已经在运行，先停止
    stop_stream(channel)

    try:
        # 初始化队列
        frame_queues[channel] = queue.Queue(maxsize=10)
        active_streams[channel] = True

        # 启动视频获取线程
        thread = threading.Thread(target=camera_stream_generator, args=(channel,))
        thread.daemon = True
        thread.start()
        stream_threads[channel] = thread

        return jsonify({
            'success': True,
            'message': f'频道 {channel} 视频流已启动',
            'rtsp_url': get_rtsp_url(channel)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@video_bp.route('/stop_stream/<int:channel>', methods=['POST'])
@auth.token_required
def stop_stream(channel):
    """停止指定频道的视频流"""
    active_streams[channel] = False

    # 清理队列
    if channel in frame_queues:
        try:
            while not frame_queues[channel].empty():
                frame_queues[channel].get_nowait()
        except:
            pass
        del frame_queues[channel]

    # 清理线程
    if channel in stream_threads:
        if stream_threads[channel].is_alive():
            stream_threads[channel].join(timeout=1)
        del stream_threads[channel]

    return jsonify({'success': True, 'message': f'频道 {channel} 视频流已停止'})

@video_bp.route('/stream_frame/<int:channel>', methods=['GET'])
@auth.token_required
def stream_frame(channel):
    """获取指定频道的最新帧"""
    if channel not in frame_queues or frame_queues[channel].empty():
        return jsonify({'success': False, 'message': '无可用帧'}), 404

    try:
        frame = frame_queues[channel].get_nowait()

        # 编码为JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ret:
            return jsonify({'success': False, 'message': '编码失败'}), 500

        return Response(
            buffer.tobytes(),
            mimetype='image/jpeg',
            headers={'Cache-Control': 'no-cache'}
        )
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@video_bp.route('/stream_mjpeg/<int:channel>', methods=['GET'])
@auth.token_required
def stream_mjpeg(channel):
    """提供MJPEG视频流（适用于HTML img标签或video标签）"""
    if channel not in active_streams or not active_streams[channel]:
        return jsonify({'success': False, 'message': '视频流未启动'}), 404

    def generate():
        while active_streams.get(channel, False):
            if channel in frame_queues and not frame_queues[channel].empty():
                try:
                    frame = frame_queues[channel].get_nowait()

                    # 编码为JPEG
                    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' +
                               buffer.tobytes() +
                               b'\r\n')
                except:
                    pass
            else:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' +
                       b'\r\n')
            time.sleep(0.033)  # 约30fps

    return Response(
        generate(),
        mimetype='multipart/x-mixed-replace; boundary=frame',
        headers={'Cache-Control': 'no-cache', 'Connection': 'close'}
    )

@video_bp.route('/status', methods=['GET'])
@auth.token_required
def stream_status():
    """获取所有频道的状态"""
    status = {}
    for channel in [102, 202, 302, 402]:
        status[channel] = {
            'active': active_streams.get(channel, False),
            'thread_running': stream_threads.get(channel) and stream_threads[channel].is_alive(),
            'queue_size': frame_queues.get(channel, queue.Queue()).qsize()
        }

    return jsonify({'success': True, 'data': status})

@video_bp.route('/start_all', methods=['POST'])
@auth.token_required
def start_all_streams():
    """启动所有4个频道的视频流"""
    results = {}
    for channel in [102, 202, 302, 402]:
        try:
            response = start_stream(channel)
            results[channel] = response.get_json()
        except Exception as e:
            results[channel] = {'success': False, 'message': str(e)}

    return jsonify({
        'success': True,
        'message': '批量启动完成',
        'results': results
    })

@video_bp.route('/stop_all', methods=['POST'])
@auth.token_required
def stop_all_streams():
    """停止所有4个频道的视频流"""
    for channel in [102, 202, 302, 402]:
        stop_stream(channel)

    return jsonify({
        'success': True,
        'message': '所有视频流已停止'
    })