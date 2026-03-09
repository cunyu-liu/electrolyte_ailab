import React from 'react';
import { Card, Row, Col, Statistic, Typography, Button, Space, Alert } from 'antd';
import { Link } from 'react-router-dom';
import {
  ExperimentOutlined,
  MonitorOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
  WarningOutlined
} from '@ant-design/icons';

const { Title, Paragraph } = Typography;

const HomePageSimple: React.FC = () => {
  console.log('HomePageSimple: 组件已加载');

  return (
    <div>
      <div className="page-header">
        <Title level={1} style={{
          background: 'linear-gradient(135deg, #660874 0%, #9c27b0 50%, #660874 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
          textAlign: 'center',
          marginBottom: 16,
          fontWeight: 700,
          fontSize: 'clamp(24px, 5vw, 42px)', // 响应式字体大小，最小24px，最大42px
          lineHeight: '1.2',
          wordBreak: 'break-word', // 允许单词换行
          padding: '0 16px' // 添加内边距避免贴边
        }}>
          悟行：智能电池设计与实验系统
        </Title>
        <Paragraph style={{
          textAlign: 'center',
          fontSize: 'clamp(16px, 3vw, 18px)', // 响应式字体大小，最小16px，最大18px
          color: '#666',
          maxWidth: '90vw', // 使用视口宽度作为最大宽度
          margin: '0 auto',
          lineHeight: 1.6,
          padding: '0 16px' // 添加内边距避免贴边
        }}>
          基于人工智能的电池配方设计与实验自动化平台，实现从需求到配方的闭环优化。
        </Paragraph>
      </div>

      {/* 系统状态卡片 */}
      <Row gutter={[24, 24]} style={{ marginBottom: 40 }}>
        <Col xs={24} sm={12} md={6}>
          <Card className="metric-card" style={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center'
          }}>
            <Statistic
              title={<span style={{
                fontSize: '16px',
                fontWeight: 600,
                color: '#666',
                marginBottom: '8px',
                display: 'block'
              }}>总实验数</span>}
              value={156}
              prefix={<ExperimentOutlined style={{ color: '#660874' }} />}
              valueStyle={{
                fontSize: '42px',
                fontWeight: 700,
                background: 'linear-gradient(135deg, #660874 0%, #9c27b0 50%, #660874 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text'
              }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="metric-card" style={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center'
          }}>
            <Statistic
              title={<span style={{
                fontSize: '16px',
                fontWeight: 600,
                color: '#666',
                marginBottom: '8px',
                display: 'block'
              }}>已完成实验</span>}
              value={142}
              prefix={<CheckCircleOutlined style={{ color: '#4a0563' }} />}
              valueStyle={{
                fontSize: '42px',
                fontWeight: 700,
                background: 'linear-gradient(135deg, #4a0563 0%, #660874 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text'
              }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="metric-card" style={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center'
          }}>
            <Statistic
              title={<span style={{
                fontSize: '16px',
                fontWeight: 600,
                color: '#666',
                marginBottom: '8px',
                display: 'block'
              }}>成功率</span>}
              value={91.0}
              precision={1}
              suffix="%"
              prefix={<BarChartOutlined style={{ color: '#660874' }} />}
              valueStyle={{
                fontSize: '42px',
                fontWeight: 700,
                background: 'linear-gradient(135deg, #660874 0%, #9c27b0 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text'
              }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="metric-card" style={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center'
          }}>
            <Statistic
              title={<span style={{
                fontSize: '16px',
                fontWeight: 600,
                color: '#666',
                marginBottom: '8px',
                display: 'block'
              }}>失败实验</span>}
              value={14}
              prefix={<WarningOutlined style={{ color: '#9c27b0' }} />}
              valueStyle={{
                fontSize: '42px',
                fontWeight: 700,
                background: 'linear-gradient(135deg, #9c27b0 0%, #ba68c8 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text'
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* 系统功能模块 */}
      <Row gutter={[24, 24]} style={{ marginBottom: 40 }}>
        <Col xs={24} md={8}>
          <Card
            className="content-card"
            style={{
              height: '100%',
              minHeight: '280px',
              position: 'relative',
              overflow: 'hidden',
              border: '1px solid rgba(255, 255, 255, 0.8)'
            }}
            headStyle={{
              background: 'linear-gradient(135deg, rgba(102, 8, 116, 0.05) 0%, rgba(156, 39, 176, 0.05) 100%)',
              borderBottom: '1px solid rgba(102, 8, 116, 0.1)',
              borderRadius: '16px 16px 0 0',
              padding: '24px 24px 16px'
            }}
            title={
              <Space style={{ fontSize: '18px', fontWeight: 600, color: '#660874' }}>
                <ExperimentOutlined style={{ fontSize: '20px' }} />
                AI设计员
              </Space>
            }
            extra={
              <Button
                type="primary"
                ghost
                size="large"
                style={{
                  borderRadius: '25px',
                  fontWeight: 500,
                  border: '2px solid #660874',
                  color: '#660874'
                }}
              >
                <Link to="/ai-designer" style={{ color: '#660874', textDecoration: 'none' }}>进入模块</Link>
              </Button>
            }
          >
            <Paragraph style={{
              fontSize: '16px',
              lineHeight: 1.8,
              color: '#555',
              minHeight: '120px',
              marginBottom: '20px'
            }}>
              从自然语言需求到结构化参数，通过文献挖掘、数据扩增和性能预测，生成初始实验配方。
            </Paragraph>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginTop: 'auto'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <div style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: '#4caf50',
                  boxShadow: '0 0 0 2px rgba(76, 175, 80, 0.2)'
                }}></div>
                <span style={{
                  color: '#666',
                  fontSize: '14px',
                  fontWeight: 500
                }}>模块运行状态: 正常</span>
              </div>
              <div style={{
                fontSize: '20px',
                color: '#660874',
                opacity: 0.7
              }}>
                ⚡
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card
            className="content-card"
            style={{
              height: '100%',
              minHeight: '280px',
              position: 'relative',
              overflow: 'hidden',
              border: '1px solid rgba(255, 255, 255, 0.8)'
            }}
            headStyle={{
              background: 'linear-gradient(135deg, rgba(102, 8, 116, 0.05) 0%, rgba(156, 39, 176, 0.05) 100%)',
              borderBottom: '1px solid rgba(102, 8, 116, 0.1)',
              borderRadius: '16px 16px 0 0',
              padding: '24px 24px 16px'
            }}
            title={
              <Space style={{ fontSize: '18px', fontWeight: 600, color: '#660874' }}>
                <MonitorOutlined style={{ fontSize: '20px' }} />
                AI实验员
              </Space>
            }
            extra={
              <Button
                type="primary"
                ghost
                size="large"
                style={{
                  borderRadius: '25px',
                  fontWeight: 500,
                  border: '2px solid #660874',
                  color: '#660874'
                }}
              >
                <Link to="/ai-experimenter" style={{ color: '#660874', textDecoration: 'none' }}>进入模块</Link>
              </Button>
            }
          >
            <Paragraph style={{
              fontSize: '16px',
              lineHeight: 1.8,
              color: '#555',
              minHeight: '120px',
              marginBottom: '20px'
            }}>
              自动执行实验流程，实时监控多摄像头画面和传感器数据，记录配液、注液、测试全过程。
            </Paragraph>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginTop: 'auto'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <div style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: '#4caf50',
                  boxShadow: '0 0 0 2px rgba(76, 175, 80, 0.2)'
                }}></div>
                <span style={{
                  color: '#666',
                  fontSize: '14px',
                  fontWeight: 500
                }}>模块运行状态: 正常</span>
              </div>
              <div style={{
                fontSize: '20px',
                color: '#660874',
                opacity: 0.7
              }}>
                📹
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card
            className="content-card"
            style={{
              height: '100%',
              minHeight: '280px',
              position: 'relative',
              overflow: 'hidden',
              border: '1px solid rgba(255, 255, 255, 0.8)'
            }}
            headStyle={{
              background: 'linear-gradient(135deg, rgba(102, 8, 116, 0.05) 0%, rgba(156, 39, 176, 0.05) 100%)',
              borderBottom: '1px solid rgba(102, 8, 116, 0.1)',
              borderRadius: '16px 16px 0 0',
              padding: '24px 24px 16px'
            }}
            title={
              <Space style={{ fontSize: '18px', fontWeight: 600, color: '#660874' }}>
                <BarChartOutlined style={{ fontSize: '20px' }} />
                闭环优化
              </Space>
            }
            extra={
              <Button
                type="primary"
                ghost
                size="large"
                style={{
                  borderRadius: '25px',
                  fontWeight: 500,
                  border: '2px solid #660874',
                  color: '#660874'
                }}
              >
                <Link to="/closed-loop" style={{ color: '#660874', textDecoration: 'none' }}>进入模块</Link>
              </Button>
            }
          >
            <Paragraph style={{
              fontSize: '16px',
              lineHeight: 1.8,
              color: '#555',
              minHeight: '120px',
              marginBottom: '20px'
            }}>
              智能评估实验结果，自动决策下一步行动，通过贝叶斯优化或重新设计实现性能提升。
            </Paragraph>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginTop: 'auto'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <div style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: '#4caf50',
                  boxShadow: '0 0 0 2px rgba(76, 175, 80, 0.2)'
                }}></div>
                <span style={{
                  color: '#666',
                  fontSize: '14px',
                  fontWeight: 500
                }}>模块运行状态: 正常</span>
              </div>
              <div style={{
                fontSize: '20px',
                color: '#660874',
                opacity: 0.7
              }}>
                🎯
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 系统公告 */}
      <Alert
        message={
          <span style={{
            fontSize: '18px',
            fontWeight: 600,
            color: '#660874'
          }}>
            🎉 系统公告
          </span>
        }
        description={
          <span style={{
            fontSize: '16px',
            lineHeight: 1.6,
            color: '#555'
          }}>
            悟行：智能电池设计与实验系统已成功部署，所有模块正常运行。当前支持正极材料配方设计，涵盖蓄能、动力、3C等多种应用场景。
          </span>
        }
        type="info"
        showIcon
        style={{
          marginTop: 24,
          background: 'linear-gradient(135deg, rgba(102, 8, 116, 0.05) 0%, rgba(156, 39, 176, 0.05) 100%)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(102, 8, 116, 0.1)',
          borderRadius: '16px',
          padding: '24px'
        }}
        icon={
          <div style={{
            fontSize: '24px',
            color: '#660874'
          }}>
            📢
          </div>
        }
      />
    </div>
  );
};

export default HomePageSimple;