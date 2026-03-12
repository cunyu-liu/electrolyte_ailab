import React, { useState, useEffect } from 'react';
import { Card, Tag, Space, Tooltip, Typography } from 'antd';
import {
  VideoCameraOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

interface CameraConfig {
  camera_id: string;
  name: string;
  channel: number;
  description: string;
}

interface RTSPVideoPlayerProps {
  camera: CameraConfig;
  style?: React.CSSProperties;
  active?: boolean; // 是否激活当前通道
}

const RTSPVideoPlayer: React.FC<RTSPVideoPlayerProps> = ({
  camera,
  style,
  active = false
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 构建视频流URL（使用相对路径，自动适配API baseURL）
  const streamUrl = `/api/ai-experimenter/video/get/${camera.channel}`;

  // 检查通道是否可用
  useEffect(() => {
    if (!active) {
      setLoading(false);
      return;
    }

    const checkChannel = async () => {
      try {
        const response = await fetch(`/api/ai-experimenter/video/start/${camera.channel}`);
        const data = await response.json();

        if (data.status !== 'success') {
          setError(data.message || '通道不可用');
        }
      } catch (err) {
        setError(`通道检查失败: ${err instanceof Error ? err.message : '未知错误'}`);
      } finally {
        setLoading(false);
      }
    };

    checkChannel();
  }, [camera.channel, active]);

  // 获取状态标签
  const getStatusTag = () => {
    if (loading) {
      return <Tag color="blue">连接中...</Tag>;
    }
    if (error) {
      return <Tag color="red">错误</Tag>;
    }
    if (active) {
      return <Tag color="green">实时</Tag>;
    }
    return <Tag color="default">未启动</Tag>;
  };

  return (
    <Card
      title={
        <Space>
          <VideoCameraOutlined />
          <span>{camera.name}</span>
          <Tooltip title={`通道 ${camera.channel}`}>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              CH{camera.channel}
            </Text>
          </Tooltip>
        </Space>
      }
      size="small"
      extra={
        <Tooltip title="状态">
          {getStatusTag()}
        </Tooltip>
      }
      style={style}
    >
      <div style={{ position: 'relative' }}>
        {/* 视频显示区域 */}
        <div
          style={{
            width: '100%',
            height: '400px',
            backgroundColor: '#000',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative',
            overflow: 'hidden'
          }}
        >
          {loading && (
            <div style={{
              color: '#fff',
              textAlign: 'center'
            }}>
              <div>连接中...</div>
            </div>
          )}

          {!active && !loading && (
            <div style={{
              color: '#666',
              textAlign: 'center',
              padding: '20px'
            }}>
              <VideoCameraOutlined style={{ fontSize: '48px', marginBottom: '8px' }} />
              <div>摄像头未启动</div>
            </div>
          )}

          {active && !error && (
            <img
              key={`video-${camera.channel}`}
              src={streamUrl}
              alt={camera.name}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'contain',
                borderRadius: '6px'
              }}
              onLoad={() => {
                console.log(`[RTSP播放器] 视频流加载成功: ${camera.name}, 通道: ${camera.channel}`);
                setError(null);
                setLoading(false);
              }}
              onError={(e) => {
                console.error(`[RTSP播放器] 视频流加载失败: ${camera.name}, 通道: ${camera.channel}`, e);
                setError(`视频流连接失败，请检查通道 ${camera.channel} 是否可用`);
                setLoading(false);
              }}
            />
          )}

          {/* 实时标记 */}
          {active && !loading && !error && (
            <div
              style={{
                position: 'absolute',
                top: '8px',
                right: '8px',
                backgroundColor: 'rgba(0, 0, 0, 0.6)',
                color: '#fff',
                padding: '2px 8px',
                borderRadius: '4px',
                fontSize: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              <div style={{
                width: '8px',
                height: '8px',
                backgroundColor: '#52c41a',
                borderRadius: '50%',
                animation: 'pulse 2s infinite'
              }} />
              LIVE
            </div>
          )}
        </div>

        {/* 错误信息 */}
        {error && (
          <div style={{
            marginTop: '8px',
            padding: '8px',
            backgroundColor: '#fff2f0',
            border: '1px solid #ffccc7',
            borderRadius: '4px',
            color: '#ff4d4f',
            fontSize: '12px'
          }}>
            {error}
          </div>
        )}
      </div>
    </Card>
  );
};

export default RTSPVideoPlayer;