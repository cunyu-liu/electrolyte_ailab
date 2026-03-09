"""
海康威视RTSP视频流管理器
支持多通道视频流获取和MJPEG转发
"""

import threading
import time
import logging
from typing import Dict, Optional
import base64
import json
from datetime import datetime

logger = logging.getLogger(__name__)

import subprocess
import signal
import atexit

class FfmpegManager:
    def __init__(self, rtsp_map: Dict[str, str]):
        self.rtsp_map = rtsp_map
        self.procs: Dict[str, subprocess.Popen] = {}
        self.stream_readers: Dict[str, 'FFmpegStreamReader'] = {}

    def start(self, camera_id: str, scale_w=640, fps=10, q=6):
        if camera_id in self.procs and self.procs[camera_id].poll() is None:
            return

        url = self.rtsp_map[camera_id]
        cmd = [
            "ffmpeg",
            "-loglevel", "error",
            "-rtsp_transport", "tcp",
            "-rw_timeout", "5000000",
            "-i", url,
            "-an",
            "-vf", f"scale={scale_w}:-1,fps={fps}",
            "-f", "mjpeg",
            "-q:v", str(q),
            "pipe:1",
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        self.procs[camera_id] = p

        # 创建流读取器
        self.stream_readers[camera_id] = FFmpegStreamReader(p)

    def stop(self, camera_id: str):
        p = self.procs.get(camera_id)
        if not p:
            return
        try:
            p.kill()
        except Exception:
            pass
        self.procs.pop(camera_id, None)

        # 清理流读取器
        if camera_id in self.stream_readers:
            del self.stream_readers[camera_id]

    def get_mjpeg_stream(self, camera_id: str):
        """获取指定摄像头的MJPEG数据流"""
        if camera_id not in self.stream_readers:
            return None

        return self.stream_readers[camera_id].generate_mjpeg_stream()


class FFmpegStreamReader:
    """FFmpeg流数据读取器"""

    def __init__(self, proc: subprocess.Popen):
        self.proc = proc
        self.running = True
        self._buffer = b""

    def _read_mjpeg_frame(self):
        """从FFmpeg输出中读取单个JPEG帧"""
        while self.running and self.proc and self.proc.stdout:
            chunk = self.proc.stdout.read(4096)
            if not chunk:
                return None

            self._buffer += chunk

            # 查找JPEG边界
            while True:
                start_idx = self._buffer.find(b"\xff\xd8")
                if start_idx == -1:
                    break

                end_idx = self._buffer.find(b"\xff\xd9", start_idx + 2)
                if end_idx == -1:
                    break

                # 提取完整的JPEG帧
                jpeg_frame = self._buffer[start_idx:end_idx + 2]
                self._buffer = self._buffer[end_idx + 2:]

                return jpeg_frame

            # 防止缓冲区过大
            if len(self._buffer) > 2_000_000:
                self._buffer = self._buffer[-200_000:]

        return None

    def generate_mjpeg_stream(self):
        """生成MJPEG流数据"""
        def generate():
            try:
                while self.running and self.proc and self.proc.poll() is None:
                    jpeg_frame = self._read_mjpeg_frame()
                    if jpeg_frame:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' +
                               jpeg_frame +
                               b'\r\n')
                    else:
                        # 如果没有帧，等待一小段时间
                        import time
                        time.sleep(0.033)  # 约30fps

            except GeneratorExit:
                self.running = False
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"MJPEG流生成异常: {str(e)}")
                self.running = False

        return generate

class RTSPStreamManager:
    """RTSP流管理器 - 使用FFmpeg方案"""

    def __init__(self):
        self.is_initialized = False
        self.rtsp_map = {}
        self.camera_status = {}
        self.ffmpeg_manager = None

        # 注册退出时的清理函数
        atexit.register(self._cleanup_on_exit)

        # 信号处理，确保优雅关闭
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def initialize_cameras(self):
        """初始化所有摄像头"""
        if self.is_initialized:
            return

        # 从配置文件读取摄像头配置
        camera_configs = self._load_camera_configs()

        # 构建RTSP映射和状态管理
        for config in camera_configs:
            camera_id = config['camera_id']
            channel = config['channel']

            # 构建RTSP URL
            ip = config.get('ip', '192.168.80.44')
            port = config.get('port', 554)
            username = config.get('username', 'admin')
            password = config.get('password', 'admin123')

            rtsp_url = f"rtsp://{username}:{password}@{ip}:{port}/Streaming/Channels/{channel}/"
            self.rtsp_map[camera_id] = rtsp_url

            # 初始化状态
            self.camera_status[camera_id] = {
                "camera_id": camera_id,
                "name": config['name'],
                "channel": channel,
                "is_running": False,
                "last_error": None,
                "frame_count": 0,
                "start_time": None
            }

        # 初始化FFmpeg管理器
        self.ffmpeg_manager = FfmpegManager(self.rtsp_map)

        self.is_initialized = True
        logger.info(f"初始化了 {len(self.rtsp_map)} 个摄像头（FFmpeg方案）")

    def _load_camera_configs(self):
        """从配置文件加载摄像头通道配置"""
        try:
            import os
            config_path = os.path.join(os.path.dirname(__file__), '../../camera_config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            return config_data.get('channels', [])
        except Exception as e:
            logger.warning(f"无法加载摄像头通道配置，使用默认配置: {str(e)}")
            # 默认配置（与camera_config.json中的通道号一致）
            return [
                {
                    'camera_id': 'camera_1',
                    'channel': 102,
                    'name': '配液监控摄像头'
                },
                {
                    'camera_id': 'camera_2',
                    'channel': 202,
                    'name': '注液封口监控'
                },
                {
                    'camera_id': 'camera_3',
                    'channel': 302,
                    'name': '性能测试监控'
                },
                {
                    'camera_id': 'camera_4',
                    'channel': 402,
                    'name': '环境监控摄像头'
                }
            ]

    def start_camera(self, camera_id: str):
        """启动指定摄像头的FFmpeg进程 - 单摄像头模式"""
        try:
            if camera_id not in self.camera_status:
                logger.error(f"摄像头 {camera_id} 不存在")
                return False

            if self.camera_status[camera_id]["is_running"]:
                logger.info(f"摄像头 {camera_id} 已在运行中")
                return True

            # 单摄像头模式：先停止其他所有摄像头
            self._stop_all_other_cameras(camera_id)

            # 启动FFmpeg进程
            self.ffmpeg_manager.start(camera_id, scale_w=640, fps=10, q=6)

            # 更新状态
            self.camera_status[camera_id]["is_running"] = True
            self.camera_status[camera_id]["last_error"] = None
            self.camera_status[camera_id]["start_time"] = time.time()

            logger.info(f"摄像头 {camera_id} FFmpeg进程启动成功")
            return True

        except Exception as e:
            logger.error(f"启动摄像头 {camera_id} 失败: {str(e)}")
            if camera_id in self.camera_status:
                self.camera_status[camera_id]["last_error"] = str(e)
            return False

    def _stop_all_other_cameras(self, exclude_camera_id: str):
        """停止除指定摄像头外的所有其他摄像头"""
        for camera_id in self.camera_status:
            if camera_id != exclude_camera_id and self.camera_status[camera_id]["is_running"]:
                logger.info(f"单摄像头模式：停止其他摄像头 {camera_id}")
                self.stop_camera(camera_id)

    def stop_camera(self, camera_id: str):
        """停止指定摄像头"""
        try:
            # 停止FFmpeg进程
            if self.ffmpeg_manager:
                self.ffmpeg_manager.stop(camera_id)

            # 更新状态
            if camera_id in self.camera_status:
                self.camera_status[camera_id]["is_running"] = False
                logger.info(f"摄像头 {camera_id} 已停止")

        except Exception as e:
            logger.error(f"停止摄像头 {camera_id} 失败: {str(e)}")

    def start_all_cameras(self) -> dict:
        """启动所有摄像头"""
        results = {}
        for camera_id in self.camera_status:
            results[camera_id] = self.start_camera(camera_id)
            time.sleep(0.5)  # 避免同时连接造成压力
        return results

    def stop_all_cameras(self):
        """停止所有摄像头"""
        try:
            # 停止所有FFmpeg进程
            if self.ffmpeg_manager:
                for camera_id in self.camera_status:
                    self.ffmpeg_manager.stop(camera_id)

            # 更新所有状态
            for camera_id in self.camera_status:
                self.camera_status[camera_id]["is_running"] = False

            logger.info("所有摄像头已停止")

        except Exception as e:
            logger.error(f"停止所有摄像头失败: {str(e)}")

    def get_camera_frame(self, camera_id: str) -> Optional[dict]:
        """获取指定摄像头的最新帧"""
        try:
            if camera_id not in self.camera_status:
                return None

            # 尝试从已启动的FFmpeg进程获取帧
            if (self.ffmpeg_manager and
                camera_id in self.ffmpeg_manager.stream_readers and
                camera_id in self.ffmpeg_manager.procs and
                self.ffmpeg_manager.procs[camera_id].poll() is None):

                reader = self.ffmpeg_manager.stream_readers[camera_id]
                jpeg_frame = reader._read_mjpeg_frame()

                if jpeg_frame:
                    frame_data = base64.b64encode(jpeg_frame).decode('utf-8')
                    return {
                        'camera_id': camera_id,
                        'name': self.camera_status[camera_id]['name'],
                        'channel': self.camera_status[camera_id]['channel'],
                        'timestamp': datetime.now().isoformat(),
                        'frame_data': frame_data,
                        'is_running': self.camera_status[camera_id]['is_running']
                    }

            # 如果没有运行的进程，返回状态信息但不包含帧数据
            return {
                'camera_id': camera_id,
                'name': self.camera_status[camera_id]['name'],
                'channel': self.camera_status[camera_id]['channel'],
                'timestamp': datetime.now().isoformat(),
                'frame_data': None,
                'is_running': False,
                'error': 'FFmpeg进程未运行'
            }

        except Exception as e:
            logger.error(f"获取摄像头 {camera_id} 帧失败: {str(e)}")
            return None

    def get_all_cameras_status(self) -> dict:
        """获取所有摄像头状态"""
        return {
            'total_cameras': len(self.camera_status),
            'cameras': self.camera_status,
            'ffmpeg_processes': len(self.ffmpeg_manager.procs) if self.ffmpeg_manager else 0
        }

    def get_camera_status(self, camera_id: str) -> Optional[dict]:
        """获取指定摄像头状态"""
        if camera_id not in self.camera_status:
            return None
        return self.camera_status[camera_id]

    def generate_mjpeg_stream(self, camera_id: str):
        """生成MJPEG视频流 - 直接使用已启动的FFmpeg进程"""
        if camera_id not in self.camera_status:
            return None

        if not self.camera_status[camera_id]["is_running"]:
            return None

        # 确保FFmpeg进程已启动
        if not self.ffmpeg_manager or camera_id not in self.ffmpeg_manager.procs:
            logger.error(f"摄像头 {camera_id} FFmpeg进程未启动")
            return None

        # 直接使用已启动的FFmpeg进程的流
        return self.ffmpeg_manager.get_mjpeg_stream(camera_id)

    def _cleanup_on_exit(self):
        """程序退出时的资源清理"""
        try:
            logger.info("开始清理RTSP流资源...")
            self.stop_all_cameras()
            logger.info("RTSP流资源清理完成")
        except Exception as e:
            logger.error(f"资源清理失败: {str(e)}")

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"接收到信号 {signum}，开始清理资源...")
        self._cleanup_on_exit()
        # 清理完成后退出程序
        import sys
        sys.exit(0)

    def health_check(self) -> dict:
        """健康检查"""
        try:
            status = {
                'is_initialized': self.is_initialized,
                'total_cameras': len(self.camera_status),
                'running_cameras': sum(1 for cam in self.camera_status.values() if cam['is_running']),
                'ffmpeg_processes': len(self.ffmpeg_manager.procs) if self.ffmpeg_manager else 0,
                'timestamp': time.time()
            }

            # 检查FFmpeg进程是否健康
            if self.ffmpeg_manager:
                unhealthy_procs = []
                for camera_id, proc in self.ffmpeg_manager.procs.items():
                    if proc.poll() is not None:  # 进程已退出
                        unhealthy_procs.append(camera_id)

                status['unhealthy_processes'] = unhealthy_procs
                status['healthy'] = len(unhealthy_procs) == 0

            return status

        except Exception as e:
            logger.error(f"健康检查失败: {str(e)}")
            return {
                'healthy': False,
                'error': str(e),
                'timestamp': time.time()
            }


# 全局实例
stream_manager = RTSPStreamManager()