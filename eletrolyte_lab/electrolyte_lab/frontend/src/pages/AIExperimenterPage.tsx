import React, { useState, useEffect, useCallback } from 'react';
import { Card, Typography, message, Spin, Row, Col, Tag, Flex, Progress, Space, Tooltip, Button, Alert } from 'antd';
import { 
  ExperimentOutlined, 
  MedicineBoxOutlined, 
  LineChartOutlined, 
  DashboardOutlined,
  VideoCameraOutlined,
  CheckCircleFilled,
  SettingFilled
} from '@ant-design/icons';
// 假设这是你的API路径
import { aiExperimenterApi } from '../services/api';

const { Title, Text, Paragraph } = Typography;

// --- 常量与类型定义 ---

const THEME_COLOR = '#6B46C1'; // 深紫色
const THEME_BG_ACTIVE = '#F3F0FF'; // 浅紫色背景

// 摄像头配置
const CAMERAS = [
  { label: '配液监控摄像头', value: 101, icon: <ExperimentOutlined /> },
  { label: '注液封口监控', value: 201, icon: <MedicineBoxOutlined /> },
  { label: '性能测试监控', value: 301, icon: <LineChartOutlined /> },
  { label: '环境监控摄像头', value: 401, icon: <DashboardOutlined /> },
];

const AIExperimenterPage: React.FC = () => {
  const [selectedChannel, setSelectedChannel] = useState<number>(101);
  const [cameraName, setCameraName] = useState<string>('配液监控摄像头');
  const [loading, setLoading] = useState<boolean>(false);
  const [videoUrl, setVideoUrl] = useState<string>('');

  // 启动视频流
  const handleStartVideo = useCallback(async (channel: number, name: string) => {
    setLoading(true);
    try {
      if (aiExperimenterApi?.startVideoChannel) {
        await aiExperimenterApi.startVideoChannel(channel);
        const baseUrl = aiExperimenterApi.getVideoStreamUrl(channel);
        const url = `${baseUrl}?t=${Date.now()}`;
        setVideoUrl(url);
      } else {
        setVideoUrl(''); 
      }
    } catch (error: any) {
      message.error(`开启${name}失败: ${error.message || '未知错误'}`);
    } finally {
      setLoading(false);
    }
  }, []);

  // 初始化
  useEffect(() => {
    handleStartVideo(101, '配液监控摄像头');
  }, [handleStartVideo]);

  // 切换摄像头
  const handleCameraChange = async (channel: number) => {
    const camera = CAMERAS.find(c => c.value === channel);
    if (camera) {
      setSelectedChannel(channel);
      setCameraName(camera.label);
      await handleStartVideo(channel, camera.label);
    }
  };

  // 渲染左侧自定义导航项
  const renderMenuItem = (item: typeof CAMERAS[0]) => {
    const isActive = selectedChannel === item.value;
    return (
      <div
        key={item.value}
        onClick={() => handleCameraChange(item.value)}
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '16px 24px',
          cursor: 'pointer',
          borderRadius: '0 8px 8px 0',
          backgroundColor: isActive ? THEME_BG_ACTIVE : 'transparent',
          color: isActive ? THEME_COLOR : '#666',
          marginBottom: '24px',
          borderLeft: isActive ? `4px solid ${THEME_COLOR}` : '4px solid transparent',
          transition: 'all 0.3s ease',
          fontWeight: isActive ? 600 : 400
        }}
      >
        <span style={{ fontSize: '18px', marginRight: '12px' }}>{item.icon}</span>
        <span style={{ fontSize: '15px' }}>{item.label}</span>
      </div>
    );
  };

  return (
    <div>
      <div className="page-header">
        <Title level={2}>AI实验员</Title>
        <Paragraph>
          自动化实验执行平台，支持多摄像头监控、实时数据采集和全过程追踪，确保实验的准确性和可重复性。
        </Paragraph>
      </div>

      {/* === 主内容区域 === */}
      <Row gutter={24} style={{ height: '600px' }}>
        
        {/* === 左侧：导航菜单 (占比 5/24) === */}
        <Col span={5}>
          <Card style={{ height: '100%' }} bodyStyle={{ height: '100%', padding: '24px' }}>
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <div style={{ marginBottom: '16px' }}>
                <Title level={4} style={{ margin: 0 }}>视频监控源</Title>
              </div>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                {CAMERAS.map(renderMenuItem)}
              </div>
            </div>
          </Card>
        </Col>

        {/* === 中间：视频播放区域 (占比 13/24) === */}
        <Col span={13}>
          <div 
            style={{ 
              height: '100%', 
              backgroundColor: '#0F111A', // 深色背景
              borderRadius: '12px', 
              overflow: 'hidden',
              position: 'relative',
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
              display: 'flex',
              flexDirection: 'column'
            }}
          >
            {/* 视频区域顶部覆盖层 */}
            <div style={{ 
              position: 'absolute', 
              top: '20px', 
              left: '20px', 
              zIndex: 10,
              backgroundColor: 'rgba(0,0,0,0.6)',
              padding: '6px 12px',
              borderRadius: '4px'
            }}>
              <Space>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#ff4d4f' }} />
                <Text style={{ color: '#fff', fontSize: '14px' }}>LIVE | {cameraName.replace('摄像头', '')} Cam-01</Text>
              </Space>
            </div>

            {/* 视频内容 */}
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
              {loading ? (
                <div style={{ textAlign: 'center' }}>
                  <Spin size="large" />
                  <div style={{ marginTop: 20, color: '#666' }}>正在连接信号源 (Stream #{selectedChannel})...</div>
                </div>
              ) : videoUrl ? (
                <img
                  src={videoUrl}
                  alt={cameraName}
                  style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = 'none';
                    message.error('视频流断开');
                  }}
                />
              ) : (
                <div style={{ textAlign: 'center', color: '#4B5563' }}>
                  <VideoCameraOutlined style={{ fontSize: '48px', marginBottom: '16px', opacity: 0.5 }} />
                  <div>正在连接信号源 (Stream #{selectedChannel})...</div>
                </div>
              )}
            </div>
          </div>
        </Col>

        {/* === 右侧：系统状态 (占比 6/24) === */}
        <Col span={6}>
          <Card 
            bordered={false}
            style={{ 
              height: '100%', 
              borderRadius: '12px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.05)' 
            }}
            bodyStyle={{ padding: '24px', height: '100%', display: 'flex', flexDirection: 'column' }}
          >
            <Flex justify="space-between" align="center" style={{ marginBottom: '24px' }}>
              <Title level={4} style={{ margin: 0 }}>系统状态</Title>
              <SettingFilled style={{ color: '#ccc', fontSize: '16px' }} />
            </Flex>

            {/* 状态列表 */}
            <Flex vertical gap="large" style={{ flex: 1 }}>
              {[
                { label: '监控摄像头', status: '正常', color: 'success' },
                { label: '传感器', status: '正常', color: 'success' },
                { label: '实验设备', status: '就绪', color: 'processing' },
                { label: '数据采集', status: '正常', color: 'success' },
              ].map((item, idx) => (
                <Flex key={idx} justify="space-between" align="center">
                  <Text style={{ color: '#666', fontSize: '15px' }}>{item.label}</Text>
                  {item.color === 'success' ? (
                     <Tag color="success" style={{ margin: 0, padding: '0 10px', borderRadius: '4px' }}>
                       <CheckCircleFilled style={{ marginRight: 4 }} /> {item.status}
                     </Tag>
                  ) : (
                    <Tag color="blue" style={{ margin: 0, padding: '0 10px', borderRadius: '4px', fontWeight: 'bold' }}>
                       {item.status}
                     </Tag>
                  )}
                </Flex>
              ))}
            </Flex>

            {/* 分割线 */}
            <div style={{ height: '1px', background: '#f0f0f0', margin: '24px 0' }} />

            {/* 任务进度 */}
            <div>
              <Flex justify="space-between" style={{ marginBottom: '8px' }}>
                <Text style={{ fontSize: '15px', fontWeight: 500 }}>当前任务进度</Text>
                <Text style={{ color: THEME_COLOR, fontWeight: 'bold', fontSize: '16px' }}>45%</Text>
              </Flex>
              <Progress 
                percent={45} 
                showInfo={false} 
                strokeColor={THEME_COLOR} 
                trailColor="#F0F0F0"
                strokeLinecap="round"
              />
              <div style={{ marginTop: '12px' }}>
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  正在执行: 样本混合测试 (Batch-09)
                </Text>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

    </div>
  );
};

export default AIExperimenterPage;