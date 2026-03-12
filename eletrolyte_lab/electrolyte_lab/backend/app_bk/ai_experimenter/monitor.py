import time
import threading
import random
import numpy as np
import subprocess
import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000|max_delay;0"
os.environ["OPENCV_FFMPEG_THREADS"] = "1"

import cv2
import base64
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)
cv2.setNumThreads(0)

@dataclass
class CameraConfig:
    """摄像头配置"""
    device_id: int
    name: str
    position: str
    resolution: tuple
    fps: int
    is_active: bool = False

@dataclass
class VideoFrame:
    """视频帧数据"""
    camera_id: str
    timestamp: float
    frame_data: str  # base64编码的图像数据
    resolution: tuple
    motion_detected: bool = False
    frame_count: int = 0

class RealCameraManager:
    """真实摄像头管理器（每路独立 ffmpeg 子进程，MJPEG pipe 输出）"""

    def __init__(self):
        self.cameras: Dict[str, CameraConfig] = {}
        self.camera_threads: Dict[str, threading.Thread] = {}
        self.frame_buffers: Dict[str, Optional[VideoFrame]] = {}

        # 每路一个独立 ffmpeg 进程
        self.ffmpeg_procs: Dict[str, subprocess.Popen] = {}

        # 状态
        self.running: bool = False
        self.last_frame_time: Dict[str, Optional[float]] = {}
        self.frame_count: Dict[str, int] = {}
        self.last_error: Dict[str, Optional[str]] = {}

        # 防止多线程读写 frame_buffers/status 时出奇怪问题
        self._lock = threading.Lock()

        # JPEG 边界
        self._SOI = b"\xff\xd8"
        self._EOI = b"\xff\xd9"

    # -------------------------
    # 你可以直接传 configs（最推荐）
    # -------------------------
    def initialize_cameras(self, camera_configs: List[CameraConfig]) -> Dict[str, bool]:
        """
        初始化摄像头配置（不拉流，只注册配置）
        返回：{config.name: True/False}
        """
        results: Dict[str, bool] = {}
        for cfg in camera_configs:
            camera_id = f"camera_{cfg.device_id + 1}"
            ok = self._register_camera(camera_id, cfg)
            results[cfg.name] = ok
        return results

    def _register_camera(self, camera_id: str, config: CameraConfig) -> bool:
        try:
            if not config.rtsp_url:
                logger.warning("camera_id=%s 配置缺少 rtsp_url", camera_id)
                return False

            with self._lock:
                self.cameras[camera_id] = config
                self.frame_buffers[camera_id] = None
                self.last_frame_time[camera_id] = None
                self.frame_count[camera_id] = 0
                self.last_error[camera_id] = None

            logger.info("注册摄像头成功: %s name=%s rtsp=%s", camera_id, config.name, config.rtsp_url)
            return True
        except Exception as e:
            logger.exception("注册摄像头失败: %s err=%s", camera_id, e)
            return False

    # -------------------------
    # 启停
    # -------------------------
    def start_capture(self):
        """开始捕获：每路开一个线程；线程内部自己维护该路 ffmpeg 子进程"""
        if self.running:
            return
        self.running = True

        for camera_id, cfg in list(self.cameras.items()):
            if not cfg.is_active:
                continue
            t = threading.Thread(target=self._capture_loop, args=(camera_id,), daemon=True)
            t.start()
            self.camera_threads[camera_id] = t

        logger.info("摄像头捕获已启动：%d 路", len(self.camera_threads))

    def stop_capture(self):
        """停止捕获：先停循环，再逐路干掉 ffmpeg，最后 join 线程"""
        self.running = False

        # 先干掉进程
        for camera_id in list(self.ffmpeg_procs.keys()):
            self._stop_ffmpeg(camera_id)

        # 再等线程退出
        for camera_id, t in list(self.camera_threads.items()):
            try:
                t.join(timeout=3)
            except Exception:
                pass

        self.camera_threads.clear()
        logger.info("摄像头捕获已停止")

    # -------------------------
    # FFmpeg 管理
    # -------------------------
    def _start_ffmpeg(self, camera_id: str, cfg: CameraConfig) -> subprocess.Popen:
        """
        启动该路 ffmpeg：输出 MJPEG 到 stdout
        注意：ffmpeg 可执行文件必须在 PATH，或把 "ffmpeg" 换成绝对路径
        """
        w, h = cfg.resolution
        out_w, out_h = 640, 360  # 输出给前端的分辨率（你可以按需改）

        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-rtsp_transport", "tcp",
            "-stimeout", "5000000",          # 5s，单位微秒
            "-i", cfg.rtsp_url,

            # 降分辨率 + 控帧率（减负很关键，4 路才稳）
            "-vf", f"scale={out_w}:{out_h}",
            "-r", str(min(cfg.fps, 12)),     # 输出帧率（建议 <= 12，四路更稳）
            "-q:v", "6",                     # MJPEG 质量（1最好/最大，31最差/最小）

            "-f", "mjpeg",
            "pipe:1"
        ]

        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )
        return p

    def _stop_ffmpeg(self, camera_id: str):
        p = self.ffmpeg_procs.pop(camera_id, None)
        if not p:
            return
        try:
            p.terminate()
            p.wait(timeout=2)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass

    # -------------------------
    # 核心：每路线程循环
    # -------------------------
    def _capture_loop(self, camera_id: str):
        buf = bytearray()

        while self.running:
            cfg = self.cameras.get(camera_id)
            if not cfg or not cfg.is_active:
                time.sleep(0.2)
                continue

            # 1) 确保进程存活
            proc = self.ffmpeg_procs.get(camera_id)
            if proc is None or proc.poll() is not None:
                # 清理旧的
                self._stop_ffmpeg(camera_id)

                try:
                    proc = self._start_ffmpeg(camera_id, cfg)
                    self.ffmpeg_procs[camera_id] = proc
                    with self._lock:
                        self.last_error[camera_id] = None
                    buf.clear()
                    time.sleep(0.1)
                except Exception as e:
                    with self._lock:
                        self.last_error[camera_id] = f"启动ffmpeg失败: {e}"
                    time.sleep(1.0)
                continue

            # 2) 读取 stdout
            try:
                chunk = proc.stdout.read(4096)  # 阻塞读：有数据就返回
            except Exception as e:
                with self._lock:
                    self.last_error[camera_id] = f"读stdout失败: {e}"
                self._stop_ffmpeg(camera_id)
                time.sleep(0.5)
                continue

            if not chunk:
                # stdout 没数据了：记录一点 stderr，重启
                try:
                    err = proc.stderr.read(2000)
                    err_msg = err.decode("utf-8", "ignore") if err else "ffmpeg stdout empty"
                except Exception:
                    err_msg = "ffmpeg stdout empty"
                with self._lock:
                    self.last_error[camera_id] = err_msg
                self._stop_ffmpeg(camera_id)
                time.sleep(0.5)
                continue

            buf.extend(chunk)

            # 3) 切帧：找到完整 JPEG (SOI..EOI)
            #    可能一次 chunk 含多帧，所以 while 循环取尽
            while True:
                s = buf.find(self._SOI)
                if s < 0:
                    # 没找到 JPEG 开头，buf 太大就截断防爆内存
                    if len(buf) > 2_000_000:
                        buf.clear()
                    break

                e = buf.find(self._EOI, s + 2)
                if e < 0:
                    # 还没收齐结尾，继续读
                    # 但如果 s 太靠后之前有垃圾数据，清掉前面的
                    if s > 0:
                        del buf[:s]
                    break

                jpg_bytes = bytes(buf[s:e + 2])
                del buf[:e + 2]

                now = time.time()
                with self._lock:
                    self.last_frame_time[camera_id] = now
                    self.frame_count[camera_id] = self.frame_count.get(camera_id, 0) + 1

                    frame_b64 = base64.b64encode(jpg_bytes).decode("utf-8")
                    self.frame_buffers[camera_id] = VideoFrame(
                        camera_id=camera_id,
                        timestamp=now,
                        frame_data=frame_b64,
                        resolution=(640, 360),
                        motion_detected=False,  # 先别加运动检测，稳定第一
                        frame_count=self.frame_count[camera_id],
                    )

    # -------------------------
    # 对外取帧
    # -------------------------
    def get_latest_frame(self, camera_id: str) -> Optional[VideoFrame]:
        with self._lock:
            return self.frame_buffers.get(camera_id)

    def get_all_latest_frames(self) -> Dict[str, VideoFrame]:
        with self._lock:
            return {cid: f for cid, f in self.frame_buffers.items() if f is not None}

    # -------------------------
    # 状态（给你 /rtsp/camera/status 用）
    # -------------------------
    def get_camera_status(self, camera_id: str) -> Optional[dict]:
        cfg = self.cameras.get(camera_id)
        if not cfg:
            return None

        proc = self.ffmpeg_procs.get(camera_id)
        alive = proc is not None and proc.poll() is None

        now = time.time()
        with self._lock:
            last = self.last_frame_time.get(camera_id) or 0
            fc = self.frame_count.get(camera_id, 0)
            err = self.last_error.get(camera_id)

        stalled = alive and last > 0 and (now - last > 3)

        return {
            "camera_id": camera_id,
            "name": cfg.name,
            "channel": cfg.channel,
            "is_running": alive,
            "stalled": stalled,
            "ffmpeg_pid": proc.pid if proc else None,
            "ffmpeg_returncode": proc.poll() if proc else None,
            "frame_count": fc,
            "last_frame_time": last if last else None,
            "seconds_since_last_frame": (now - last) if last else None,
            "last_error": err,
            "resolution": cfg.resolution,
            "fps": cfg.fps,
        }

    def get_all_cameras_status(self) -> Dict[str, dict]:
        return {cid: self.get_camera_status(cid) for cid in self.cameras.keys()}

class ProcessMonitor:
    """过程监控器 - 负责实时监控实验过程"""

    def __init__(self):
        self.monitoring_sessions = {}
        self.monitoring_threads = {}
        self.data_buffers = {}
        self.camera_manager = RealCameraManager()
        self.use_real_cameras = False

        self.caps = {}

        # 监控设备配置
        self.device_config = {
            'cameras': {
                'camera_1': {'position': 'top', 'resolution': '1920x1080', 'fps': 30},
                'camera_2': {'position': 'side', 'resolution': '1280x720', 'fps': 25},
                'camera_3': {'position': 'close_up', 'resolution': '1920x1080', 'fps': 30}
            },
            'sensors': {
                'temperature': {'range': [-50, 100], 'accuracy': 0.1, 'unit': '°C'},
                'voltage': {'range': [0, 5], 'accuracy': 0.001, 'unit': 'V'},
                'current': {'range': [-10, 10], 'accuracy': 0.001, 'unit': 'A'},
                'resistance': {'range': [0, 1000], 'accuracy': 0.1, 'unit': 'mΩ'},
                'pressure': {'range': [0, 10], 'accuracy': 0.01, 'unit': 'bar'}
            }
        }

        # 监控数据类型
        self.monitoring_types = {
            'video': self._monitor_video,
            'liquid_prep': self._monitor_liquid_preparation,
            'injection': self._monitor_injection,
            'testing': self._monitor_testing,
            'environmental': self._monitor_environmental
        }

    def start_monitoring(self, experiment_id: int, use_real_cameras: bool = False) -> bool:
        """开始监控"""
        try:
            if experiment_id in self.monitoring_sessions:
                logger.warning(f"实验 {experiment_id} 已经在监控中")
                return False

            self.use_real_cameras = use_real_cameras

            # 如果使用真实摄像头，先初始化摄像头
            if use_real_cameras:
                logger.info("正在初始化真实摄像头...")
                camera_results = self.camera_manager.initialize_cameras()
                success_count = sum(1 for success in camera_results.values() if success)
                logger.info(f"摄像头初始化完成: {success_count}/{len(camera_results)} 个摄像头可用")

                if success_count > 0:
                    self.camera_manager.start_capture()
                else:
                    logger.warning("没有可用摄像头，将使用模拟数据")
                    self.use_real_cameras = False

            # 初始化监控会话
            self.monitoring_sessions[experiment_id] = {
                'start_time': time.time(),
                'status': 'active',
                'data_points': 0,
                'last_update': time.time(),
                'use_real_cameras': self.use_real_cameras
            }

            # 初始化数据缓冲区
            self.data_buffers[experiment_id] = {
                'video': [],
                'liquid_prep': [],
                'injection': [],
                'testing': [],
                'environmental': [],
                'system_status': []
            }

            # 启动监控线程
            monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                args=(experiment_id,),
                daemon=True
            )
            monitoring_thread.start()

            self.monitoring_threads[experiment_id] = monitoring_thread

            logger.info(f"开始监控实验 {experiment_id} (摄像头模式: {'真实' if self.use_real_cameras else '模拟'})")
            return True

        except Exception as e:
            logger.error(f"启动监控 {experiment_id} 时出错: {str(e)}")
            return False

    def stop_monitoring(self, experiment_id: int) -> bool:
        """停止监控"""
        try:
            if experiment_id not in self.monitoring_sessions:
                logger.warning(f"实验 {experiment_id} 没有在监控中")
                return False

            # 更新状态
            self.monitoring_sessions[experiment_id]['status'] = 'stopped'
            self.monitoring_sessions[experiment_id]['end_time'] = time.time()

            # 停止摄像头捕获
            if self.use_real_cameras:
                self.camera_manager.stop_capture()
                logger.info("已停止摄像头捕获")

            # 清理资源
            if experiment_id in self.monitoring_threads:
                # 线程会自动结束
                del self.monitoring_threads[experiment_id]

            logger.info(f"停止监控实验 {experiment_id}")
            return True

        except Exception as e:
            logger.error(f"停止监控 {experiment_id} 时出错: {str(e)}")
            return False

    def _monitoring_loop(self, experiment_id: int):
        """监控主循环"""
        try:
            while (experiment_id in self.monitoring_sessions and
                   self.monitoring_sessions[experiment_id]['status'] == 'active'):

                current_time = time.time()

                # 生成各类监控数据
                for data_type, monitor_func in self.monitoring_types.items():
                    try:
                        data = monitor_func(experiment_id, current_time)
                        if data:
                            self._store_monitoring_data(experiment_id, data_type, data)
                    except Exception as e:
                        logger.warning(f"生成 {data_type} 数据时出错: {str(e)}")

                # 生成系统状态数据
                system_status = self._generate_system_status(experiment_id, current_time)
                self._store_monitoring_data(experiment_id, 'system_status', system_status)

                # 更新统计
                self.monitoring_sessions[experiment_id]['last_update'] = current_time
                self.monitoring_sessions[experiment_id]['data_points'] += len(self.monitoring_types) + 1

                # 监控频率：每2秒一次
                time.sleep(2)

        except Exception as e:
            logger.error(f"监控循环出错 {experiment_id}: {str(e)}")
            if experiment_id in self.monitoring_sessions:
                self.monitoring_sessions[experiment_id]['status'] = 'error'
                self.monitoring_sessions[experiment_id]['error'] = str(e)

    def _monitor_video(self, experiment_id: int, timestamp: float) -> Dict:
        """监控视频数据"""
        video_data = {
            'timestamp': timestamp,
            'camera_mode': 'real' if self.use_real_cameras else 'simulated',
            'cameras': {}
        }

        if self.use_real_cameras:
            # 使用真实摄像头数据
            latest_frames = self.camera_manager.get_all_latest_frames()

            for camera_id, config in self.device_config['cameras'].items():
                frame = latest_frames.get(camera_id)

                if frame:
                    # 真实摄像头数据
                    frame_data = {
                        'camera_id': camera_id,
                        'position': config['position'],
                        'resolution': f"{frame.resolution[0]}x{frame.resolution[1]}",
                        'frame_count': frame.frame_count,
                        'motion_detected': frame.motion_detected,
                        'real_time': True,
                        'frame_data': frame.frame_data,  # base64编码的图像
                        'image_quality': {
                            'brightness': random.uniform(0.7, 1.0),
                            'contrast': random.uniform(0.8, 1.0),
                            'sharpness': random.uniform(0.7, 0.95)
                        },
                        'object_detection': {
                            'person_detected': frame.motion_detected,
                            'equipment_status': 'normal' if not frame.motion_detected else random.choice(['normal', 'warning']),
                            'activity_level': min(1.0, frame.motion_detected * 5 + random.uniform(0.1, 0.3))
                        }
                    }
                else:
                    # 摄像头未连接或无数据
                    frame_data = {
                        'camera_id': camera_id,
                        'position': config['position'],
                        'resolution': config['resolution'],
                        'frame_count': 0,
                        'motion_detected': False,
                        'real_time': True,
                        'connected': False,
                        'error': '摄像头未连接或无数据',
                        'image_quality': None,
                        'object_detection': None
                    }

                video_data['cameras'][camera_id] = frame_data
        else:
            # 模拟视频数据
            for camera_id, config in self.device_config['cameras'].items():
                frame_data = {
                    'camera_id': camera_id,
                    'position': config['position'],
                    'resolution': config['resolution'],
                    'frame_count': random.randint(25, 35),  # 每秒帧数
                    'motion_detected': random.choice([True, False]),
                    'real_time': False,
                    'image_quality': {
                        'brightness': random.uniform(0.7, 1.0),
                        'contrast': random.uniform(0.8, 1.0),
                        'sharpness': random.uniform(0.7, 0.95)
                    },
                    'object_detection': {
                        'person_detected': random.choice([True, False]) if random.random() > 0.8 else False,
                        'equipment_status': random.choice(['normal', 'warning', 'error']),
                        'activity_level': random.uniform(0.1, 1.0)
                    }
                }

                video_data['cameras'][camera_id] = frame_data

        return video_data

    def _monitor_liquid_preparation(self, experiment_id: int, timestamp: float) -> Dict:
        """监控配液过程"""
        liquid_data = {
            'timestamp': timestamp,
            'preparation_stage': random.choice(['weighing', 'mixing', 'dissolution', 'filtration']),
            'components': {
                'solvents': {
                    'ec_weight': random.uniform(45.0, 55.0),  # g
                    'dec_weight': random.uniform(45.0, 55.0),  # g
                    'mixing_ratio': round(random.uniform(0.35, 0.45), 3)
                },
                'salt': {
                    'type': 'LiPF6',
                    'weight': random.uniform(14.5, 15.5),  # g
                    'purity': random.uniform(99.5, 99.9),  # %
                    'dissolution_rate': random.uniform(0.8, 1.0)  # relative
                },
                'additives': [
                    {
                        'name': 'VC',
                        'weight': random.uniform(0.9, 1.1),  # g
                        'purity': random.uniform(98.0, 99.5)  # %
                    },
                    {
                        'name': 'FEC',
                        'weight': random.uniform(0.4, 0.6),  # g
                        'purity': random.uniform(98.0, 99.5)  # %
                    }
                ]
            },
            'process_parameters': {
                'mixing_speed': random.uniform(450, 550),  # RPM
                'temperature': random.uniform(23.0, 27.0),  # °C
                'humidity': random.uniform(0.1, 0.5),  # % RH
                'mixing_time': random.uniform(25, 35)  # minutes
            },
            'quality_indicators': {
                'solution_clarity': random.choice(['clear', 'slight_turbidity', 'turbid']),
                'color': random.choice(['colorless', 'slight_yellow']),
                'particulate_count': random.randint(0, 5),  # particles/mL
                'ph_value': round(random.uniform(6.8, 7.2), 1)
            }
        }

        return liquid_data

    def _monitor_injection(self, experiment_id: int, timestamp: float) -> Dict:
        """监控注液过程"""
        injection_data = {
            'timestamp': timestamp,
            'injection_parameters': {
                'target_volume': random.uniform(0.095, 0.105),  # mL
                'actual_volume': random.uniform(0.093, 0.107),  # mL
                'injection_rate': random.uniform(0.008, 0.012),  # mL/min
                'injection_pressure': random.uniform(0.4, 0.6),  # bar
                'needle_position': random.uniform(0.8, 1.2)  # mm
            },
            'cell_conditions': {
                'cell_temperature': random.uniform(22.0, 28.0),  # °C
                'cell_pressure': random.uniform(0.8, 1.2),  # bar
                'internal_resistance': random.uniform(45, 55),  # mΩ
                'open_circuit_voltage': random.uniform(3.65, 3.75)  # V
            },
            'process_status': {
                'injection_phase': random.choice(['approaching', 'injecting', 'withdrawing', 'completed']),
                'leak_detected': random.choice([True, False]) if random.random() > 0.95 else False,
                'bubble_formation': random.choice(['none', 'minor', 'moderate']),
                'seal_status': random.choice(['good', 'fair', 'poor'])
            },
            'quality_metrics': {
                'volume_accuracy': round(random.uniform(95, 105), 1),  # %
                'repeatability': round(random.uniform(98, 102), 1),  # %
                'contamination_risk': random.choice(['low', 'medium', 'high'])
            }
        }

        return injection_data

    def _monitor_testing(self, experiment_id: int, timestamp: float) -> Dict:
        """监控测试过程"""
        testing_data = {
            'timestamp': timestamp,
            'test_type': random.choice(['charge', 'discharge', 'rest', 'impedance']),
            'electrical_parameters': {
                'voltage': random.uniform(2.5, 4.3),  # V
                'current': random.uniform(-1.5, 1.5),  # A
                'power': random.uniform(-5.0, 5.0),  # W
                'energy': random.uniform(0, 500),  # mAh
                'capacity': random.uniform(0, 200)  # mAh/g
            },
            'thermal_parameters': {
                'cell_temperature': random.uniform(20.0, 35.0),  # °C
                'ambient_temperature': random.uniform(22.0, 28.0),  # °C
                'temperature_gradient': random.uniform(-2.0, 2.0),  # °C
                'heat_generation_rate': random.uniform(0.1, 2.0)  # W
            },
            'test_progress': {
                'cycle_number': random.randint(1, 100),
                'step_number': random.randint(1, 10),
                'time_in_step': random.uniform(0, 3600),  # seconds
                'total_test_time': random.uniform(0, 86400)  # seconds
            },
            'performance_indicators': {
                'coulombic_efficiency': random.uniform(95, 100),  # %
                'energy_efficiency': random.uniform(90, 98),  # %
                'voltage_efficiency': random.uniform(85, 95),  # %
                'capacity_retention': random.uniform(85, 100)  # %
            },
            'anomaly_detection': {
                'voltage_anomaly': random.choice([True, False]) if random.random() > 0.98 else False,
                'temperature_anomaly': random.choice([True, False]) if random.random() > 0.99 else False,
                'impedance_anomaly': random.choice([True, False]) if random.random() > 0.95 else False,
                'self_discharge_detected': random.choice([True, False]) if random.random() > 0.97 else False
            }
        }

        return testing_data

    def _monitor_environmental(self, experiment_id: int, timestamp: float) -> Dict:
        """监控环境参数"""
        environmental_data = {
            'timestamp': timestamp,
            'glove_box': {
                'oxygen_level': random.uniform(0.1, 1.0),  # ppm
                'moisture_level': random.uniform(0.1, 1.0),  # ppm
                'pressure': random.uniform(-10, 10),  # Pa
                'temperature': random.uniform(20.0, 25.0)  # °C
            },
            'room_conditions': {
                'temperature': random.uniform(22.0, 26.0),  # °C
                'humidity': random.uniform(40, 60),  # % RH
                'air_pressure': random.uniform(1010, 1020),  # hPa
                'air_quality': random.choice(['good', 'moderate', 'poor'])
            },
            'equipment_status': {
                'power_supply': random.choice(['normal', 'warning', 'error']),
                'temperature_controller': random.choice(['normal', 'warning', 'error']),
                'data_acquisition': random.choice(['normal', 'warning', 'error']),
                'safety_systems': random.choice(['normal', 'warning', 'error'])
            },
            'safety_monitoring': {
                'smoke_detector': random.choice(['clear', 'warning', 'alarm']),
                'gas_detector': random.choice(['clear', 'warning', 'alarm']),
                'fire_suppression': random.choice(['ready', 'warning', 'error']),
                'emergency_stop': random.choice(['ready', 'activated'])
            }
        }

        return environmental_data

    def _generate_system_status(self, experiment_id: int, timestamp: float) -> Dict:
        """生成系统状态"""
        session = self.monitoring_sessions.get(experiment_id, {})
        runtime = timestamp - session.get('start_time', timestamp)

        status_data = {
            'timestamp': timestamp,
            'experiment_id': experiment_id,
            'system_status': 'running',
            'runtime_seconds': runtime,
            'data_points_collected': session.get('data_points', 0),
            'cpu_usage': random.uniform(20, 80),  # %
            'memory_usage': random.uniform(30, 70),  # %
            'disk_usage': random.uniform(10, 40),  # %
            'network_status': random.choice(['excellent', 'good', 'poor']),
            'data_stream_status': {
                'video': random.choice(['active', 'idle', 'error']),
                'sensors': random.choice(['active', 'idle', 'error']),
                'control': random.choice(['active', 'idle', 'error'])
            },
            'alerts': []
        }

        # 生成随机警报
        if random.random() > 0.95:
            status_data['alerts'].append({
                'type': random.choice(['warning', 'error', 'info']),
                'message': random.choice([
                    'Temperature slight deviation',
                    'Network latency increased',
                    'Sensor calibration recommended',
                    'Data buffer nearing capacity'
                ]),
                'severity': random.choice(['low', 'medium', 'high']),
                'timestamp': timestamp
            })

        return status_data

    def _store_monitoring_data(self, experiment_id: int, data_type: str, data: Dict):
        """存储监控数据"""
        if experiment_id in self.data_buffers:
            # 限制缓冲区大小，保留最新的100条记录
            buffer = self.data_buffers[experiment_id][data_type]
            buffer.append(data)
            if len(buffer) > 100:
                buffer.pop(0)

    def get_current_status(self, experiment_id: int) -> Dict:
        """获取当前监控状态"""
        if experiment_id not in self.monitoring_sessions:
            return {'error': '实验不在监控中'}

        session = self.monitoring_sessions[experiment_id]
        current_time = time.time()

        # 获取最新的各类数据
        latest_data = {}
        if experiment_id in self.data_buffers:
            for data_type, buffer in self.data_buffers[experiment_id].items():
                if buffer:
                    latest_data[data_type] = buffer[-1]  # 最新的数据

        status = {
            'session_info': {
                'experiment_id': experiment_id,
                'status': session['status'],
                'start_time': session['start_time'],
                'runtime_seconds': current_time - session['start_time'],
                'data_points_collected': session['data_points'],
                'last_update': session['last_update']
            },
            'latest_data': latest_data,
            'buffer_status': {
                data_type: len(buffer) for data_type, buffer in self.data_buffers.get(experiment_id, {}).items()
            }
        }

        return status

    def get_monitoring_data(self, experiment_id: int, data_type: str = 'all') -> Dict:
        """获取监控数据"""
        if experiment_id not in self.data_buffers:
            return {'error': '没有可用的监控数据'}

        data_buffers = self.data_buffers[experiment_id]

        if data_type == 'all':
            return {
                'experiment_id': experiment_id,
                'data_types': list(data_buffers.keys()),
                'data': data_buffers,
                'total_points': sum(len(buffer) for buffer in data_buffers.values())
            }
        elif data_type in data_buffers:
            return {
                'experiment_id': experiment_id,
                'data_type': data_type,
                'data': data_buffers[data_type],
                'total_points': len(data_buffers[data_type])
            }
        else:
            return {'error': f'未知的数据类型: {data_type}'}

    def get_monitoring_summary(self, experiment_id: int) -> Dict:
        """获取监控摘要"""
        if experiment_id not in self.monitoring_sessions:
            return {'error': '实验不在监控中'}

        session = self.monitoring_sessions[experiment_id]
        data_buffers = self.data_buffers.get(experiment_id, {})

        summary = {
            'experiment_id': experiment_id,
            'monitoring_summary': {
                'total_runtime': time.time() - session['start_time'],
                'total_data_points': session['data_points'],
                'data_types_active': list(data_buffers.keys()),
                'system_health': 'good' if session['status'] == 'active' else 'stopped',
                'alerts_count': 0
            },
            'data_quality': {
                'video_stream': 'active' if 'video' in data_buffers and data_buffers['video'] else 'inactive',
                'sensor_stream': 'active' if len([k for k in data_buffers.keys() if 'monitor' in k]) > 0 else 'inactive',
                'data_integrity': 'good',
                'last_update': session['last_update']
            }
        }

        return summary