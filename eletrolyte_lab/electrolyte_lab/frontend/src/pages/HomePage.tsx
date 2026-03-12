import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Typography, Button, Space, Alert } from 'antd';
import { Link } from 'react-router-dom';
import {
  ExperimentOutlined,
  MonitorOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  WarningOutlined
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { closedLoopApi } from '../services/api';
import { OptimizationStats } from '../types';

const { Title, Paragraph } = Typography;

const HomePage: React.FC = () => {
  const [stats, setStats] = useState<OptimizationStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const response = await closedLoopApi.getOptimizationStats();
      if (response.success) {
        setStats(response.data.stats);
      } else {
        console.error('获取统计数据失败:', response.message);
        // 使用默认数据，确保页面仍能正常显示
        setStats({
          total_experiments: 0,
          completed_experiments: 0,
          failed_experiments: 0,
          success_rate: 0,
          formula_generation_methods: {
            initial_design: 0,
            bayesian_opt: 0,
            redesign: 0
          }
        });
      }
    } catch (error) {
      console.error('获取统计数据时发生错误:', error);
      // 使用默认数据，确保页面仍能正常显示
      setStats({
        total_experiments: 0,
        completed_experiments: 0,
        failed_experiments: 0,
        success_rate: 0,
        formula_generation_methods: {
          initial_design: 0,
          bayesian_opt: 0,
          redesign: 0
        }
      });
    } finally {
      setLoading(false);
    }
  };

  // 实验状态趋势图配置
  const getTrendChartOption = () => {
    return {
      title: {
        text: '实验活动趋势',
        left: 'center'
      },
      tooltip: {
        trigger: 'axis'
      },
      legend: {
        data: ['成功', '失败', '进行中'],
        bottom: 0
      },
      xAxis: {
        type: 'category',
        data: ['4月11日', '4月12日', '4月13日', '4月14日', '4月15日', '4月16日', '4月17日']
      },
      yAxis: {
        type: 'value'
      },
      series: [
        {
          name: '成功',
          type: 'line',
          data: [17, 12, 14, 18, 11, 16, 14],
          smooth: true,
          itemStyle: { color: '#52c41a' }
        },
        {
          name: '失败',
          type: 'line',
          data: [2, 2, 2, 2, 1, 2, 1],
          smooth: true,
          itemStyle: { color: '#ff4d4f' }
        },
        {
          name: '进行中',
          type: 'line',
          data: [3, 2, 4, 6, 3, 2, 1],
          smooth: true,
          itemStyle: { color: '#1890ff' }
        }
      ]
    };
  };

  // 配方生成方法分布图
  const getFormulaChartOption = () => {
    if (!stats) return {};

    const data = [
      { name: '初始设计', value: stats.formula_generation_methods.initial_design },
      { name: '贝叶斯优化', value: stats.formula_generation_methods.bayesian_opt },
      { name: '重新设计', value: stats.formula_generation_methods.redesign }
    ];

    return {
      title: {
        text: '配方生成方法分布',
        left: 'center'
      },
      tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b}: {c} ({d}%)'
      },
      series: [
        {
          name: '生成方法',
          type: 'pie',
          radius: '50%',
          data: data,
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }
      ]
    };
  };

  return (
    <div>
      <div className="page-header">
        <Title level={2}>悟行：智能电池设计与实验系统</Title>
        <Paragraph>
          基于人工智能的电池配方设计与实验自动化平台，实现从需求到配方的闭环优化。
        </Paragraph>
      </div>

      {/* 系统状态卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="总实验数"
              value={stats?.total_experiments || 0}
              prefix={<ExperimentOutlined />}
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="已完成实验"
              value={stats?.completed_experiments || 0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#4a0563' }}
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="成功率"
              value={stats?.success_rate || 0}
              precision={1}
              suffix="%"
              prefix={<BarChartOutlined />}
              valueStyle={{ color: '#660874' }}
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="失败实验"
              value={stats?.failed_experiments || 0}
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#9c27b0' }}
              loading={loading}
            />
          </Card>
        </Col>
      </Row>

      {/* 系统功能模块 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} md={8}>
          <Card
            title={
              <Space>
                <ExperimentOutlined />
                AI设计员
              </Space>
            }
            extra={<Button type="link"><Link to="/ai-designer">进入模块</Link></Button>}
          >
            <Paragraph>
              从自然语言需求到结构化参数，通过文献挖掘、数据扩增和性能预测，生成初始实验配方。
            </Paragraph>
            <div style={{ marginTop: 8, color: '#666', fontSize: '12px' }}>
              模块运行状态: 正常
            </div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card
            title={
              <Space>
                <MonitorOutlined />
                AI实验员
              </Space>
            }
            extra={<Button type="link"><Link to="/ai-experimenter">进入模块</Link></Button>}
          >
            <Paragraph>
              自动执行实验流程，实时监控多摄像头画面和传感器数据，记录配液、注液、测试全过程。
            </Paragraph>
            <div style={{ marginTop: 8, color: '#666', fontSize: '12px' }}>
              模块运行状态: 正常
            </div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card
            title={
              <Space>
                <BarChartOutlined />
                闭环优化
              </Space>
            }
            extra={<Button type="link"><Link to="/closed-loop">进入模块</Link></Button>}
          >
            <Paragraph>
              智能评估实验结果，自动决策下一步行动，通过贝叶斯优化或重新设计实现性能提升。
            </Paragraph>
            <div style={{ marginTop: 8, color: '#666', fontSize: '12px' }}>
              模块运行状态: 正常
            </div>
          </Card>
        </Col>
      </Row>

      {/* 图表展示 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="实验活动趋势" className="chart-container">
            <ReactECharts option={getTrendChartOption()} style={{ height: '300px' }} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="配方生成方法分布" className="chart-container">
            <ReactECharts option={getFormulaChartOption()} style={{ height: '300px' }} />
          </Card>
        </Col>
      </Row>

      {/* 系统公告 */}
      <Alert
        message="系统公告"
        description="悟行：智能电池设计与实验系统已成功部署，所有模块正常运行。当前支持正极材料配方设计，涵盖蓄能、动力、3C等多种应用场景。"
        type="info"
        showIcon
        style={{ marginTop: 24 }}
      />
    </div>
  );
};

export default HomePage;