from venv import logger
import cv2

DEFAULT_IP = "192.168.80.44"
DEFAULT_USER = "admin"
DEFAULT_PASS = "SZKJ2025"

def get_rtsp_url(channel, ip=DEFAULT_IP, username=DEFAULT_USER, password=DEFAULT_PASS):
    """辅助函数：统一生成 RTSP 地址

    直接使用前端传入的通道号（101, 201, 301, 401）
    """
    print(f"[视频服务] 使用通道 {channel}，RTSP URL: rtsp://{username}:***@{ip}:554/Streaming/Channels/{channel}")
    return f"rtsp://{username}:{password}@{ip}:554/Streaming/Channels/{channel}"


def get_camera_stream(channel, ip=DEFAULT_IP, username=DEFAULT_USER, password=DEFAULT_PASS):
    """生成视频帧（安全版）"""
    rtsp_url = get_rtsp_url(channel, ip, username, password)
    
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        raise Exception(f"无法打开通道 {channel}")
    
    try:
        # 进入循环，不断读取帧
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print(f"通道 {channel}: 读取失败")
                break
            yield frame
    except GeneratorExit:
        # 这是一个特殊的异常，当客户端（浏览器）断开连接时，Flask 会触发它
        print(f"通道 {channel}: 客户端断开连接，停止推流")
    except Exception as e:
        print(f"通道 {channel}: 发生错误 {e}")
    finally:
        # 【关键】无论上面是因为报错退出，还是因为浏览器关闭退出，
        # 这里一定会执行，确保释放摄像头资源
        print(f"通道 {channel}: 释放资源")
        cap.release()

def generate_frames(channel):
    """生成MJPEG视频流"""
    try:
        for frame in get_camera_stream(channel):
            # 将帧转换为JPEG格式
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            
            # 生成MJPEG流
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + 
                   buffer.tobytes() + b'\r\n')
    except Exception as e:
        print(f"通道 {channel} 错误: {str(e)}")

def check_camera_availability(channel):
    """
    新增函数：专门用于 start 接口检查摄像头是否可用
    """
    rtsp_url = get_rtsp_url(channel)
    print(f"[视频服务] 检查通道 {channel} 可用性，RTSP URL: {rtsp_url}")
    try:
        cap = cv2.VideoCapture(rtsp_url)
        is_opened = cap.isOpened()
        print(f"[视频服务] 通道 {channel} 打开状态: {is_opened}")
        if is_opened:
            # 尝试读取一帧以确认连接
            ret, frame = cap.read()
            print(f"[视频服务] 通道 {channel} 读取帧: {ret}")
        cap.release()
        return is_opened
    except Exception as e:
        print(f"[视频服务] 通道 {channel} 检查异常: {str(e)}")
        return False