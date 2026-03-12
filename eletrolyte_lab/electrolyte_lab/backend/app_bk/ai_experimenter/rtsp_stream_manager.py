"""
改进的RTSP流管理器
使用线程池和连接池来提高稳定性和性能
"""
import cv2
import threading
import time
import logging
import queue
import base64
import json
import concurrent.futures
from datetime import datetime
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import os

logger = logging.getLogger(__name__)

# 全局OpenCV线程安全配置
try:
    cv2.setNumThreads(1)
    cv2.setUseOptimized(False)
    logger.info("OpenCV全局线程安全配置已应用")
except Exception as e:
    logger.warning(f"OpenCV全局配置失败: {str(e)}")

class CameraStatus(Enum):
    """摄像头状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    SIMULATION = "simulation"

@dataclass
class CameraConfig:
    """摄像头配置"""
    camera_id: str
    name: str
    channel: int
    ip: str = "192.168.80.44"
    port: int = 554
    username: str = "admin"
    password: str = "admin123"
    use_simulation: bool = False

@dataclass
class CameraStats:
    """摄像头统计信息"""
    frame_count: int = 0
    error_count: int = 0
    last_frame_time: Optional[float] = None
    start_time: Optional[float] = None
    connection_attempts: int = 0

class ImprovedHikvisionCamera:
    """改进的海康威视摄像头管理类"""

    def __init__(self, config: CameraConfig):
        self.config = config
        self.status = CameraStatus.DISCONNECTED
        self.stats = CameraStats()

        # 视频相关
        self.cap = None
        self.latest_frame = None
        self.frame_queue = queue.Queue(maxsize=3)  # 减小队列避免内存问题

        # 线程管理
        self.capture_thread = None
        self.connection_thread = None
        self.stop_event = threading.Event()
        self.last_error = None

        # 连接管理
        self.max_connection_attempts = 3
        self.connection_timeout = 10.0
        self.frame_timeout = 5.0
        self.retry_interval = 30.0  # 30秒重试间隔

        # 性能配置
        self.target_fps = 8
        self.frame_width = 640
        self.frame_height = 480

        # 构建RTSP URL
        self._build_rtsp_url()

    def _build_rtsp_url(self):
        """构建RTSP URL"""
        self.rtsp_url = f"rtsp://{self.config.username}:{self.config.password}@{self.config.ip}:{self.config.port}/Streaming/Channels/{self.config.channel}/"
        logger.info(f"摄像头 {self.config.camera_id} RTSP URL: {self.config.ip}:{self.config.port}/Channel{self.config.channel}")

    def start(self) -> bool:
        """启动摄像头连接"""
        if self.status in [CameraStatus.CONNECTING, CameraStatus.CONNECTED]:
            logger.warning(f"摄像头 {self.config.camera_id} 已在运行或连接中")
            return True

        logger.info(f"开始连接摄像头 {self.config.camera_id}")
        self.status = CameraStatus.CONNECTING
        self.stats.connection_attempts = 0
        self.stop_event.clear()

        # 使用连接线程进行连接，避免阻塞
        self.connection_thread = threading.Thread(target=self._connect_with_retry, daemon=True)
        self.connection_thread.start()

        return True

    def _connect_with_retry(self):
        """带重试的连接逻辑"""
        while not self.stop_event.is_set() and self.stats.connection_attempts < self.max_connection_attempts:
            try:
                self.stats.connection_attempts += 1
                logger.info(f"尝试连接摄像头 {self.config.camera_id}, 第 {self.stats.connection_attempts} 次")

                if self._try_connect():
                    self.status = CameraStatus.CONNECTED
                    self.stats.start_time = time.time()
                    logger.info(f"摄像头 {self.config.camera_id} 连接成功")

                    # 启动帧捕获线程
                    self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
                    self.capture_thread.start()
                    return True
                else:
                    self.stats.error_count += 1
                    if self.stats.connection_attempts < self.max_connection_attempts:
                        logger.warning(f"摄像头 {self.config.camera_id} 连接失败，{self.retry_interval}秒后重试")
                        time.sleep(self.retry_interval)

            except Exception as e:
                self.stats.error_count += 1
                self.last_error = str(e)
                logger.error(f"摄像头 {self.config.camera_id} 连接异常: {e}")

                if self.stats.connection_attempts < self.max_connection_attempts:
                    time.sleep(self.retry_interval)

        # 所有连接尝试都失败，降级到模拟模式
        logger.error(f"摄像头 {self.config.camera_id} 所有连接尝试均失败，切换到模拟模式")
        self._start_simulation_mode()
        return False

    def _try_connect(self) -> bool:
        """尝试单次连接"""
        try:
            # 在独立线程中进行连接测试
            result_queue = queue.Queue()

            def connect_worker():
                try:
                    # 设置OpenCV配置
                    cv2.setNumThreads(1)
                    cv2.setUseOptimized(False)

                    cap = cv2.VideoCapture(self.rtsp_url)

                    # 设置连接参数
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    cap.set(cv2.CAP_PROP_FPS, self.target_fps)
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
                    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, int(self.connection_timeout * 1000))
                    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, int(self.frame_timeout * 1000))

                    if not cap.isOpened():
                        result_queue.put((False, "无法打开RTSP连接"))
                        return

                    # 测试读取一帧
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        cap.release()
                        result_queue.put((False, "无法读取视频帧"))
                        return

                    result_queue.put((True, cap))

                except Exception as e:
                    result_queue.put((False, str(e)))

            # 启动连接工作线程
            worker_thread = threading.Thread(target=connect_worker, daemon=True)
            worker_thread.start()
            worker_thread.join(timeout=self.connection_timeout + 5)

            if worker_thread.is_alive():
                result_queue.put((False, "连接超时"))

            # 获取结果
            try:
                success, result = result_queue.get_nowait()
                if success:
                    self.cap = result
                    return True
                else:
                    self.last_error = result
                    return False
            except queue.Empty:
                self.last_error = "连接结果获取超时"
                return False

        except Exception as e:
            self.last_error = str(e)
            return False

    def _start_simulation_mode(self):
        """启动模拟模式"""
        try:
            self.status = CameraStatus.SIMULATION
            self.stats.start_time = time.time()
            logger.info(f"摄像头 {self.config.camera_id} 切换到模拟模式")

            # 启动模拟帧生成线程
            self.capture_thread = threading.Thread(target=self._simulation_loop, daemon=True)
            self.capture_thread.start()

        except Exception as e:
            self.status = CameraStatus.ERROR
            self.last_error = f"模拟模式启动失败: {str(e)}"
            logger.error(self.last_error)

    def _capture_loop(self):
        """帧捕获主循环"""
        logger.info(f"摄像头 {self.config.camera_id} 开始帧捕获循环")

        while not self.stop_event.is_set() and self.cap is not None:
            try:
                # 使用超时机制读取帧
                ret, frame = self.cap.read()

                if ret and frame is not None:
                    # 调整帧大小以提高性能
                    frame = cv2.resize(frame, (self.frame_width, self.frame_height))

                    # 更新统计信息
                    self.stats.frame_count += 1
                    self.stats.last_frame_time = time.time()
                    self.latest_frame = frame

                    # 将帧放入队列（非阻塞）
                    try:
                        self.frame_queue.put_nowait(frame)
                    except queue.Full:
                        # 队列满时移除最老的帧
                        try:
                            self.frame_queue.get_nowait()
                            self.frame_queue.put_nowait(frame)
                        except queue.Empty:
                            pass

                    # 帧率控制
                    time.sleep(1.0 / self.target_fps)
                else:
                    # 读取失败，尝试重新连接
                    logger.warning(f"摄像头 {self.config.camera_id} 帧读取失败")
                    self.stats.error_count += 1

                    # 释放当前连接
                    if self.cap:
                        self.cap.release()
                        self.cap = None

                    # 尝试重新连接
                    if not self._try_connect():
                        logger.error(f"摄像头 {self.config.camera_id} 重新连接失败")
                        break

            except Exception as e:
                self.stats.error_count += 1
                self.last_error = f"帧捕获异常: {str(e)}"
                logger.error(f"摄像头 {self.config.camera_id} 帧捕获异常: {e}")
                time.sleep(1.0)

        logger.info(f"摄像头 {self.config.camera_id} 帧捕获循环结束")

    def _simulation_loop(self):
        """模拟帧生成循环"""
        logger.info(f"摄像头 {self.config.camera_id} 开始模拟帧生成")

        # 生成简单的测试图像
        import numpy as np

        while not self.stop_event.is_set():
            try:
                # 创建模拟帧
                frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)

                # 添加测试图案
                cv2.putText(frame, f"Camera: {self.config.name}", (20, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.putText(frame, f"Channel: {self.config.channel}", (20, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.putText(frame, f"Status: SIMULATION", (20, 110),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                cv2.putText(frame, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), (20, 150),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                # 添加移动的圆圈表示"视频"
                center_x = int(self.frame_width/2 + 100 * np.sin(time.time() * 2))
                center_y = int(self.frame_height/2)
                cv2.circle(frame, (center_x, center_y), 30, (255, 255, 0), -1)

                self.stats.frame_count += 1
                self.stats.last_frame_time = time.time()
                self.latest_frame = frame

                # 放入队列
                try:
                    self.frame_queue.put_nowait(frame)
                except queue.Full:
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put_nowait(frame)
                    except queue.Empty:
                        pass

                time.sleep(1.0 / self.target_fps)

            except Exception as e:
                logger.error(f"摄像头 {self.config.camera_id} 模拟帧生成异常: {e}")
                time.sleep(1.0)

    def get_latest_frame(self) -> Optional[bytes]:
        """获取最新帧的JPEG编码数据"""
        try:
            frame = self.latest_frame
            if frame is not None:
                # 编码为JPEG
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                if ret:
                    return buffer.tobytes()
            return None
        except Exception as e:
            logger.error(f"摄像头 {self.config.camera_id} 获取帧失败: {e}")
            return None

    def get_frame_from_queue(self) -> Optional[bytes]:
        """从队列获取帧"""
        try:
            frame = self.frame_queue.get(timeout=1.0)
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                if ret:
                    return buffer.tobytes()
            return None
        except queue.Empty:
            return None
        except Exception as e:
            logger.error(f"摄像头 {self.config.camera_id} 队列获取帧失败: {e}")
            return None

    def stop(self):
        """停止摄像头"""
        logger.info(f"停止摄像头 {self.config.camera_id}")

        # 设置停止事件
        self.stop_event.set()

        # 等待线程结束
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=5.0)

        if self.connection_thread and self.connection_thread.is_alive():
            self.connection_thread.join(timeout=5.0)

        # 释放资源
        if self.cap:
            self.cap.release()
            self.cap = None

        # 清空队列
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break

        self.status = CameraStatus.DISCONNECTED
        logger.info(f"摄像头 {self.config.camera_id} 已停止")

    def get_status_info(self) -> dict:
        """获取摄像头状态信息"""
        uptime = time.time() - self.stats.start_time if self.stats.start_time else 0

        return {
            'camera_id': self.config.camera_id,
            'name': self.config.name,
            'status': self.status.value,
            'frame_count': self.stats.frame_count,
            'error_count': self.stats.error_count,
            'connection_attempts': self.stats.connection_attempts,
            'uptime_seconds': uptime,
            'last_frame_time': self.stats.last_frame_time,
            'last_error': self.last_error,
            'is_simulation': self.status == CameraStatus.SIMULATION,
            'queue_size': self.frame_queue.qsize()
        }

class RTSPStreamManager:
    """改进的RTSP流管理器"""

    def __init__(self):
        self.cameras: Dict[str, ImprovedHikvisionCamera] = {}
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="RTSP")
        self.initialized = False
        self.config_lock = threading.Lock()

    def initialize_cameras(self):
        """初始化所有摄像头"""
        if self.initialized:
            return True

        with self.config_lock:
            try:
                # 默认摄像头配置
                camera_configs = [
                    CameraConfig("camera_1", "配液监控摄像头", 101),
                    CameraConfig("camera_2", "注液封口监控", 201),
                    CameraConfig("camera_3", "性能测试监控", 301),
                    CameraConfig("camera_4", "环境监控摄像头", 401)
                ]

                # 从配置文件加载自定义配置
                self._load_camera_configs(camera_configs)

                # 创建摄像头实例
                for config in camera_configs:
                    camera = ImprovedHikvisionCamera(config)
                    self.cameras[config.camera_id] = camera
                    logger.info(f"创建摄像头实例: {config.camera_id}")

                self.initialized = True
                logger.info(f"RTSP流管理器初始化完成，共 {len(self.cameras)} 个摄像头")
                return True

            except Exception as e:
                logger.error(f"初始化摄像头失败: {e}")
                return False

    def _load_camera_configs(self, default_configs: List[CameraConfig]):
        """从配置文件加载摄像头配置"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '../../camera_config.json')
            if not os.path.exists(config_path):
                logger.info(f"摄像头配置文件不存在，使用默认配置: {config_path}")
                return

            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            camera_settings = config_data.get('camera_settings', {})

            # 更新配置
            for config in default_configs:
                if config.camera_id in camera_settings:
                    settings = camera_settings[config.camera_id]
                    config.ip = settings.get('ip', config.ip)
                    config.port = settings.get('port', config.port)
                    config.username = settings.get('username', config.username)
                    config.password = settings.get('password', config.password)
                    config.use_simulation = settings.get('use_simulation', config.use_simulation)

            logger.info("成功加载摄像头配置文件")

        except Exception as e:
            logger.warning(f"加载摄像头配置文件失败，使用默认配置: {e}")

    def start_camera(self, camera_id: str) -> bool:
        """启动指定摄像头"""
        if not self.initialized:
            self.initialize_cameras()

        if camera_id not in self.cameras:
            logger.error(f"摄像头 {camera_id} 不存在")
            return False

        camera = self.cameras[camera_id]
        return camera.start()

    def start_all_cameras(self) -> Dict[str, bool]:
        """启动所有摄像头"""
        if not self.initialized:
            self.initialize_cameras()

        results = {}

        # 并行启动摄像头
        def start_worker(camera_id):
            return self.start_camera(camera_id)

        future_to_camera = {
            self.thread_pool.submit(start_worker, camera_id): camera_id
            for camera_id in self.cameras.keys()
        }

        for future in concurrent.futures.as_completed(future_to_camera):
            camera_id = future_to_camera[future]
            try:
                results[camera_id] = future.result()
            except Exception as e:
                logger.error(f"启动摄像头 {camera_id} 异常: {e}")
                results[camera_id] = False

        success_count = sum(1 for success in results.values() if success)
        logger.info(f"启动完成: {success_count}/{len(self.cameras)} 个摄像头成功")

        return results

    def stop_camera(self, camera_id: str):
        """停止指定摄像头"""
        if camera_id in self.cameras:
            self.cameras[camera_id].stop()

    def stop_all_cameras(self):
        """停止所有摄像头"""
        for camera in self.cameras.values():
            camera.stop()

    def get_camera_frame(self, camera_id: str) -> Optional[bytes]:
        """获取摄像头最新帧"""
        if camera_id not in self.cameras:
            return None

        camera = self.cameras[camera_id]
        return camera.get_frame_from_queue()

    def generate_mjpeg_stream(self, camera_id: str):
        """生成MJPEG流"""
        def generate_frames():
            while True:
                frame_data = self.get_camera_frame(camera_id)
                if frame_data:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
                else:
                    # 发送空白帧保持连接
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + b'\r\n')
                time.sleep(0.1)  # 控制帧率

        return generate_frames

    def get_all_cameras_status(self) -> Dict[str, dict]:
        """获取所有摄像头状态"""
        return {
            camera_id: camera.get_status_info()
            for camera_id, camera in self.cameras.items()
        }

    def is_camera_streaming(self, camera_id: str) -> bool:
        """检查摄像头是否正在流式传输"""
        if camera_id not in self.cameras:
            return False

        camera = self.cameras[camera_id]
        return camera.status in [CameraStatus.CONNECTED, CameraStatus.SIMULATION]

    def shutdown(self):
        """关闭管理器"""
        logger.info("正在关闭RTSP流管理器...")

        # 停止所有摄像头
        self.stop_all_cameras()

        # 关闭线程池
        self.thread_pool.shutdown(wait=True, timeout=10)

        logger.info("RTSP流管理器已关闭")

# 全局实例
stream_manager = RTSPStreamManager()