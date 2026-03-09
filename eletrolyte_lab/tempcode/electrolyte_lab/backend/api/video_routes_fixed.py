from flask import Blueprint, Response, jsonify, request
import cv2
import threading
import queue
import time
from utils import auth

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
    生成器函数，持续从RTSP流获取帧，增强错误处理和稳定性
    """
    rtsp_url = get_rtsp_url(channel)
    cap = None
    retry_count = 0
    max_retries = 5
    retry_delay = 2

    while active_streams.get(channel, False):
        try:
            if cap is None or not cap.isOpened():
                if retry_count >= max_retries:
                    print(f"RTSP通道 {channel} 重连次数过多，停止尝试")
                    break

                print(f"RTSP通道 {channel} 尝试连接 ({retry_count + 1}/{max_retries})")
                cap = cv2.VideoCapture(rtsp_url)

                # 设置缓冲区大小和超时
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(cv2.CAP_PROP_FPS, 15)

                if not cap.isOpened():
                    print(f"RTSP通道 {channel} 连接失败")
                    retry_count += 1
                    time.sleep(retry_delay)
                    continue

                print(f"RTSP通道 {channel} 连接成功")
                retry_count = 0

            ret, frame = cap.read()
            if not ret:
                print(f"RTSP通道 {channel} 读取帧失败，尝试重连...")
                cap.release()
                cap = None
                retry_count += 1
                time.sleep(retry_delay)
                continue

            # 重置重试计数
            retry_count = 0

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

            # 短暂休眠，避免过度占用CPU
            time.sleep(0.03)  # 约30fps

        except Exception as e:
            print(f"RTSP通道 {channel} 发生异常: {str(e)}")
            if cap:
                cap.release()
                cap = None
            retry_count += 1
            time.sleep(retry_delay)

    if cap:
        cap.release()
    print(f"RTSP通道 {channel} 已停止")

@video_bp.route('/start_stream/<int:channel>', methods=['POST'])
@auth.token_required
def start_stream(channel):
    """启动指定频道的视频流，增强资源管理和错误处理"""
    if channel not in [102, 202, 302, 402]:
        return jsonify({'success': False, 'message': '不支持的频道号'}), 400

    # 如果已经在运行，先停止
    stop_stream(channel)

    try:
        # 清理现有资源
        if channel in frame_queues:
            del frame_queues[channel]
        if channel in active_streams:
            del active_streams[channel]
        if channel in stream_threads:
            del stream_threads[channel]

        # 初始化队列和状态
        frame_queues[channel] = queue.Queue(maxsize=5)  # 减小队列大小，降低延迟
        active_streams[channel] = True

        # 启动视频获取线程，设置线程名称便于调试
        thread_name = f"camera_stream_{channel}"
        thread = threading.Thread(target=camera_stream_generator, args=(channel,), name=thread_name)
        thread.daemon = True
        thread.start()
        stream_threads[channel] = thread

        print(f"已启动频道 {channel} 视频流线程: {thread_name}")

        return jsonify({
            'success': True,
            'message': f'频道 {channel} 视频流已启动',
            'rtsp_url': get_rtsp_url(channel),
            'thread_name': thread_name,
            'timestamp': time.time()
        })
    except Exception as e:
        # 清理资源
        active_streams[channel] = False
        if channel in frame_queues:
            del frame_queues[channel]
        if channel in stream_threads:
            del stream_threads[channel]
        print(f"启动频道 {channel} 视频流失败: {str(e)}")
        return jsonify({'success': False, 'message': f'启动失败: {str(e)}'}), 500

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

@video_bp.route('/stream_status/<int:channel>', methods=['GET'])
@auth.token_required
def stream_status(channel):
    """获取指定频道的视频流状态"""
    is_active = active_streams.get(channel, False)
    thread_info = None

    if channel in stream_threads:
        thread = stream_threads[channel]
        thread_info = {
            'name': thread.name,
            'is_alive': thread.is_alive(),
            'daemon': thread.daemon
        }

    queue_info = None
    if channel in frame_queues:
        queue_info = {
            'size': frame_queues[channel].qsize(),
            'maxsize': frame_queues[channel].maxsize,
            'empty': frame_queues[channel].empty()
        }

    return jsonify({
        'success': True,
        'channel': channel,
        'active': is_active,
        'thread_info': thread_info,
        'queue_info': queue_info,
        'timestamp': time.time()
    })

@video_bp.route('/stream_status_all', methods=['GET'])
@auth.token_required
def stream_status_all():
    """获取所有频道的视频流状态"""
    channels = [102, 202, 302, 402]
    status = {}

    for channel in channels:
        try:
            is_active = active_streams.get(channel, False)
            thread_info = None

            if channel in stream_threads:
                thread = stream_threads[channel]
                thread_info = {
                    'name': thread.name,
                    'is_alive': thread.is_alive(),
                    'daemon': thread.daemon
                }

            queue_info = None
            if channel in frame_queues:
                queue_info = {
                    'size': frame_queues[channel].qsize(),
                    'maxsize': frame_queues[channel].maxsize,
                    'empty': frame_queues[channel].empty()
                }

            status[channel] = {
                'active': is_active,
                'thread_info': thread_info,
                'queue_info': queue_info
            }
        except Exception as e:
            status[channel] = {
                'error': str(e)
            }

    return jsonify({
        'success': True,
        'status': status,
        'timestamp': time.time()
    })

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