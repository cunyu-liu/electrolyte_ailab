import React, { useState } from 'react';
import {
  Card,
  Button,
  Form,
  Input,
  InputNumber,
  Select,
  Checkbox,
  message,
  Space,
  Typography,
  Divider,
  Alert,
  Tabs,
  Tag,
  Row,
  Col,
  Steps
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
  RobotOutlined,
  ExperimentOutlined,
  BarChartOutlined,
  SearchOutlined
} from '@ant-design/icons';
import { aiDesignerApi, literatureApi, molecularApi } from '../services/api';
import { ParsedParameters } from '../types';

const { Title, Paragraph, Text } = Typography;
const { Option } = Select;
const { TabPane } = Tabs;
const { Step } = Steps;

const TestApiPage: React.FC = () => {
  const [parsedResult, setParsedResult] = useState<ParsedParameters | null>(null);
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [activeTab, setActiveTab] = useState('parsing');
  const [form] = Form.useForm();

  // 测试需求解析API
  const testParseRequest = async (inputText: string) => {
    setLoading(true);
    try {
      console.log('发送需求解析请求:', { parameters: { input: inputText } });

      const response = await aiDesignerApi.parseRequest({ parameters: { input: inputText } });
      console.log('需求解析API响应:', response);

      if (response.success && response.data) {
        setParsedResult(response.data);
        setCurrentStep(1);
        message.success('需求解析成功！后端AI服务正常工作');
        return response.data;
      } else {
        message.error('需求解析失败: ' + (response.message || '未知错误'));
        return null;
      }
    } catch (error) {
      console.error('需求解析API错误:', error);
      message.error('网络错误或后端服务不可用，请检查控制台');
      return null;
    } finally {
      setLoading(false);
    }
  };

  // 测试参数确认API
  const testConfirmParameters = async () => {
    if (!parsedResult) {
      message.error('请先解析需求');
      return;
    }

    setLoading(true);
    try {
      console.log('发送参数确认请求:', { parameters: parsedResult });

      const response = await aiDesignerApi.confirmParameters({ parameters: parsedResult });
      console.log('参数确认API响应:', response);

      if (response.success) {
        setCurrentStep(2);
        message.success('参数确认成功！');
        return response.data;
      } else {
        message.error('参数确认失败: ' + (response.message || '未知错误'));
        return null;
      }
    } catch (error) {
      console.error('参数确认API错误:', error);
      message.error('网络错误或后端服务不可用');
      return null;
    } finally {
      setLoading(false);
    }
  };

  // 测试数据挖掘API
  const testMineData = async () => {
    if (!parsedResult) {
      message.error('请先解析需求并确认参数');
      return;
    }

    setLoading(true);
    try {
      console.log('发送数据挖掘请求:', { parameters: parsedResult });

      const response = await aiDesignerApi.mineData({ parameters: parsedResult });
      console.log('数据挖掘API响应:', response);

      if (response.success) {
        setCurrentStep(3);
        message.success('数据挖掘成功！');
        return response.data;
      } else {
        message.error('数据挖掘失败: ' + (response.message || '未知错误'));
        return null;
      }
    } catch (error) {
      console.error('数据挖掘API错误:', error);
      message.error('网络错误或后端服务不可用');
      return null;
    } finally {
      setLoading(false);
    }
  };

  // 测试分子生成API
  const testGenerateMolecules = async () => {
    if (!parsedResult) {
      message.error('请先完成前面的步骤');
      return;
    }

    setLoading(true);
    try {
      const request = {
        target_properties: parsedResult.performance_params,
        component_type: parsedResult.basic_info.system_type?.value || parsedResult.basic_info.system_type,
        max_count: 10,
        method: 'ai_generation'
      };

      console.log('发送分子生成请求:', request);

      const response = await molecularApi.generateMolecules(request);
      console.log('分子生成API响应:', response);

      if (response.success) {
        setCurrentStep(4);
        message.success(`分子生成成功！生成了${response.data.molecules?.length || 0}个分子`);
        return response.data;
      } else {
        message.error('分子生成失败: ' + (response.message || '未知错误'));
        return null;
      }
    } catch (error) {
      console.error('分子生成API错误:', error);
      message.error('网络错误或后端服务不可用');
      return null;
    } finally {
      setLoading(false);
    }
  };

  // 处理表单提交
  const handleFormSubmit = async (values: any) => {
    const { input_text } = values;
    if (!input_text || input_text.trim().length === 0) {
      message.error('请输入需求描述');
      return;
    }

    await testParseRequest(input_text);
  };

  // 重置所有状态
  const resetAll = () => {
    setParsedResult(null);
    setCurrentStep(0);
    setActiveTab('parsing');
    form.resetFields();
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <Title level={2}>
        <RobotOutlined /> AI设计师API测试
      </Title>
      <Paragraph type="secondary">
        测试后端AI服务进行需求分析和处理的完整流程
      </Paragraph>

      {/* 流程步骤指示器 */}
      <Card style={{ marginBottom: '24px' }}>
        <Steps current={currentStep} size="small">
          <Step title="需求解析" icon={<SearchOutlined />} />
          <Step title="参数确认" icon={<CheckCircleOutlined />} />
          <Step title="数据挖掘" icon={<ExperimentOutlined />} />
          <Step title="分子生成" icon={<BarChartOutlined />} />
        </Steps>
      </Card>

      {/* 主功能区域 */}
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        {/* 需求解析标签页 */}
        <TabPane tab="需求解析" key="parsing">
          <Card title="使用后端AI进行需求解析" style={{ marginBottom: '16px' }}>
            <Alert
              message="后端AI服务"
              description="此页面使用真正的后端AI服务进行需求分析，不是基础解析"
              type="info"
              showIcon
              style={{ marginBottom: '16px' }}
            />

            <Form
              form={form}
              onFinish={handleFormSubmit}
              layout="vertical"
            >
              <Form.Item
                name="input_text"
                label="需求描述"
                rules={[{ required: true, message: '请输入需求描述' }]}
              >
                <Input.TextArea
                  rows={6}
                  placeholder="请详细描述您的电解液需求，例如：&#10;我需要一种用于动力电池的电解液，要求能量密度达到300Wh/kg，功率密度1000W/kg，循环寿命2000次以上，工作温度25°C，安全性要求4级。"
                />
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button
                    type="primary"
                    htmlType="submit"
                    loading={loading}
                    icon={<SearchOutlined />}
                  >
                    解析需求
                  </Button>
                  <Button onClick={resetAll}>
                    重置
                  </Button>
                </Space>
              </Form.Item>
            </Form>

            {/* 预设需求 */}
            <Divider>预设需求示例</Divider>
            <Space wrap>
              <Button
                size="small"
                onClick={() => {
                  form.setFieldsValue({
                    input_text: "开发一种用于新能源汽车的动力电池电解液，要求能量密度300Wh/kg，支持快充，循环寿命2000次以上，工作温度范围-20°C到60°C"
                  });
                }}
              >
                新能源汽车电池
              </Button>
              <Button
                size="small"
                onClick={() => {
                  form.setFieldsValue({
                    input_text: "储能电站用电解液，要求长循环寿命3000次，低成本，高安全性，工作温度25°C"
                  });
                }}
              >
                储能电站
              </Button>
              <Button
                size="small"
                onClick={() => {
                  form.setFieldsValue({
                    input_text: "三元材料体系电解液，高电压4.4V，能量密度350Wh/kg，功率密度1500W/kg"
                  });
                }}
              >
                高能量密度
              </Button>
            </Space>
          </Card>

          {/* 解析结果显示 */}
          {parsedResult && (
            <Card title="解析结果" style={{ marginBottom: '16px' }}>
              <Row gutter={[16, 16]}>
                <Col span={8}>
                  <div style={{ padding: '12px', border: '1px solid #d9d9d9', borderRadius: '6px' }}>
                    <Title level={5}>基本信息</Title>
                    <p><strong>系统类型:</strong> {parsedResult.basic_info?.system_type?.value}</p>
                    <p><strong>应用场景:</strong> {parsedResult.basic_info?.application_scenario?.value}</p>
                    <p><strong>确认状态:</strong>
                      <Tag color={parsedResult.basic_info?.system_type?.required ? 'green' : 'orange'}>
                        {parsedResult.basic_info?.system_type?.required ? '已确认' : '未确认'}
                      </Tag>
                    </p>
                  </div>
                </Col>
                <Col span={16}>
                  <div style={{ padding: '12px', border: '1px solid #d9d9d9', borderRadius: '6px' }}>
                    <Title level={5}>性能参数</Title>
                    <Row gutter={[16, 8]}>
                      <Col span={8}>
                        <p><strong>能量密度:</strong> {parsedResult.performance_params?.energy_density?.value} {parsedResult.performance_params?.energy_density?.unit}</p>
                      </Col>
                      <Col span={8}>
                        <p><strong>功率密度:</strong> {parsedResult.performance_params?.power_density?.value} {parsedResult.performance_params?.power_density?.unit}</p>
                      </Col>
                      <Col span={8}>
                        <p><strong>循环寿命:</strong> {parsedResult.performance_params?.cycle_life?.value} {parsedResult.performance_params?.cycle_life?.unit}</p>
                      </Col>
                      <Col span={8}>
                        <p><strong>工作温度:</strong> {parsedResult.performance_params?.working_temperature?.value} {parsedResult.performance_params?.working_temperature?.unit}</p>
                      </Col>
                      <Col span={8}>
                        <p><strong>安全性:</strong> {parsedResult.performance_params?.safety?.value} {parsedResult.performance_params?.safety?.unit}</p>
                      </Col>
                      {parsedResult.metadata?.total_confidence && (
                        <Col span={8}>
                          <p><strong>置信度:</strong> <Tag color="blue">{(parsedResult.metadata.total_confidence * 100).toFixed(1)}%</Tag></p>
                        </Col>
                      )}
                    </Row>
                  </div>
                </Col>
              </Row>

              {parsedResult.metadata && (
                <div style={{ marginTop: '16px' }}>
                  <Title level={5}>元数据</Title>
                  <pre style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px', fontSize: '12px' }}>
                    {JSON.stringify(parsedResult.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </Card>
          )}
        </TabPane>

        {/* API测试标签页 */}
        <TabPane tab="API测试" key="testing">
          <Card title="分步骤API测试" style={{ marginBottom: '16px' }}>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <Card size="small" title="1. 参数确认API">
                <Button
                  type="primary"
                  onClick={testConfirmParameters}
                  loading={loading}
                  disabled={!parsedResult}
                  block
                >
                  确认参数
                </Button>
              </Card>

              <Card size="small" title="2. 数据挖掘API">
                <Button
                  type="primary"
                  onClick={testMineData}
                  loading={loading}
                  disabled={currentStep < 2}
                  block
                >
                  启动数据挖掘
                </Button>
              </Card>

              <Card size="small" title="3. 分子生成API">
                <Button
                  type="primary"
                  onClick={testGenerateMolecules}
                  loading={loading}
                  disabled={currentStep < 3}
                  block
                >
                  生成候选分子
                </Button>
              </Card>
            </Space>
          </Card>

          {/* 原始请求测试 */}
          <Card title="原始API请求测试" style={{ marginBottom: '16px' }}>
            <Alert
              message="高级用法"
              description="可以直接发送自定义请求到后端API进行测试"
              type="info"
              showIcon
              style={{ marginBottom: '16px' }}
            />

            <Form onFinish={async (values) => {
              const request = {
                input: values.input,
                parameters: values.parameters ? JSON.parse(values.parameters) : undefined
              };

              console.log('发送原始请求:', request);

              try {
                const response = await fetch('/api/ai-designer/parse-request', {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                  },
                  body: JSON.stringify(request)
                });

                const result = await response.json();
                console.log('原始响应:', result);
                setParsedResult(result.data?.parsed_parameters);
              } catch (error) {
                console.error('请求失败:', error);
                message.error('请求失败，请查看控制台');
              }
            }}>
              <Form.Item name="input" label="输入文本">
                <Input.TextArea rows={4} placeholder="输入测试文本..." />
              </Form.Item>

              <Form.Item name="parameters" label="参数JSON">
                <Input.TextArea
                  rows={8}
                  placeholder='{"basic_info": {"system_type": "三元材料"}, "application_scenario": "动力电池"}}'
                />
              </Form.Item>

              <Button type="primary" htmlType="submit" loading={loading}>
                发送请求
              </Button>
            </Form>
          </Card>
        </TabPane>

        {/* 完整结果显示 */}
        <TabPane tab="完整结果" key="results">
          <Card title="完整处理结果">
            <pre style={{
              background: '#f5f5f5',
              padding: '16px',
              borderRadius: '6px',
              maxHeight: '500px',
              overflow: 'auto',
              fontSize: '12px'
            }}>
              {parsedResult ? JSON.stringify(parsedResult, null, 2) : '暂无结果'}
            </pre>
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default TestApiPage;