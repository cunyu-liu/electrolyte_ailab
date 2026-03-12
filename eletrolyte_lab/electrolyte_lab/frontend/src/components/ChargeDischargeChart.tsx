import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Select,
  Button,
  Spin,
  Alert,
  Typography,
  Statistic,
  Tag,
  Space,
  message
} from 'antd';
import { landianApi } from '../services/api';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

interface MainIdOption {
  value: string;
  label: string;
}

const ChargeDischargeChart: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [mainIds, setMainIds] = useState<MainIdOption[]>([]);
  const [selectedMainId, setSelectedMainId] = useState<string>('');
  const [error, setError] = useState<string>('');

  // 获取MainId列表
  const fetchMainIds = async () => {
    try {
      setLoading(true);
      const response = await landianApi.getMainIds(50);

      if (response.success && response.data) {
        const options = response.data.data.map((id: string) => ({
          value: id,
          label: `MainId: ${id}`
        }));
        setMainIds(options);
        message.success(`成功获取 ${options.length} 个MainId`);
      } else {
        setError(response.message || '获取MainId列表失败');
      }
    } catch (err) {
      const errorMsg = '获取MainId列表失败';
      setError(errorMsg);
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  // 处理MainId选择
  const handleMainIdChange = (value: string) => {
    setSelectedMainId(value);
    message.info(`选择了MainId: ${value}`);
  };

  // 组件加载时获取MainId列表
  useEffect(() => {
    fetchMainIds();
  }, []);

  return (
    <div>
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>📈 充放电曲线数据分析</span>
            <Button onClick={fetchMainIds} loading={loading}>
              刷新数据
            </Button>
          </div>
        }
        style={{ marginBottom: 16 }}
      >
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={12}>
            <div style={{ marginBottom: 16 }}>
              <Text strong>选择MainId：</Text>
              <Select
                style={{ width: '100%', marginTop: 8 }}
                placeholder="请选择MainId"
                value={selectedMainId}
                onChange={handleMainIdChange}
                loading={loading}
                showSearch
                filterOption={(input, option) =>
                  option?.children?.toString().toLowerCase().includes(input.toLowerCase())
                }
              >
                {mainIds.map((option) => (
                  <Option key={option.value} value={option.value}>
                    {option.label}
                  </Option>
                ))}
              </Select>
            </div>
          </Col>
          <Col span={12}>
            <div style={{ marginBottom: 16 }}>
              <Text strong>数据统计：</Text>
              <div style={{ marginTop: 8 }}>
                <Space>
                  <Statistic
                    title="可用MainId数量"
                    value={mainIds.length}
                    valueStyle={{ color: '#3f8600' }}
                  />
                  {selectedMainId && (
                    <Tag color="blue">已选择: {selectedMainId}</Tag>
                  )}
                </Space>
              </div>
            </div>
          </Col>
        </Row>

        {error && (
          <Alert
            message="错误"
            description={error}
            type="error"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        {loading && (
          <div style={{ textAlign: 'center', padding: 20 }}>
            <Spin size="large" />
            <div style={{ marginTop: 8 }}>
              <Text>正在加载数据...</Text>
            </div>
          </div>
        )}

        {!loading && !error && !selectedMainId && (
          <Alert
            message="提示"
            description="请从上方下拉框选择一个MainId来查看充放电曲线数据"
            type="info"
            showIcon
          />
        )}

        {!loading && !error && selectedMainId && (
          <Card
            title={`📊 MainId: ${selectedMainId} 的数据展示`}
            size="small"
          >
            <Alert
              message="数据获取功能"
              description="充放电曲线数据展示功能正在开发中，当前已成功连接到蓝甸数据库API。"
              type="info"
              showIcon
            />
          </Card>
        )}
      </Card>
    </div>
  );
};

export default ChargeDischargeChart;