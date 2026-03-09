import React, { useState } from 'react';
import {
  Form,
  Input,
  Button,
  Card,
  Typography,
  Row,
  Col,
  message,
  Checkbox,
  Divider,
  Space,
  Progress
} from 'antd';
import {
  UserOutlined,
  LockOutlined,
  MailOutlined,
  IdcardOutlined,
  UserAddOutlined,
  CheckCircleOutlined
} from '@ant-design/icons';
import { useNavigate, Link } from 'react-router-dom';
import { authApi } from '../services/api';
import { RegisterForm } from '../types';

const { Title, Text, Paragraph } = Typography;

const RegisterPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [passwordStrength, setPasswordStrength] = useState(0);
  const navigate = useNavigate();
  const [form] = Form.useForm();

  // 密码强度检测
  const checkPasswordStrength = (password: string) => {
    let strength = 0;
    if (password.length >= 8) strength += 25;
    if (password.length >= 12) strength += 15;
    if (/[a-z]/.test(password)) strength += 20;
    if (/[A-Z]/.test(password)) strength += 20;
    if (/[0-9]/.test(password)) strength += 20;
    setPasswordStrength(strength);
  };

  const getPasswordStrengthColor = () => {
    if (passwordStrength < 40) return '#ff4d4f';
    if (passwordStrength < 70) return '#faad14';
    return '#52c41a';
  };

  const getPasswordStrengthText = () => {
    if (passwordStrength < 40) return '弱';
    if (passwordStrength < 70) return '中';
    return '强';
  };

  const onFinish = async (values: RegisterForm) => {
    setLoading(true);
    try {
      const response = await authApi.register(values);

      if (response.success) {
        message.success(
          response.message || '注册成功！请检查邮箱进行验证后登录。'
        );
        // 跳转到登录页面
        navigate('/login');
      }
    } catch (error: any) {
      console.error('Register error:', error);
      message.error(error.response?.data?.error || '注册失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <Row justify="center" align="middle" style={{ width: '100%', maxWidth: '1200px' }}>
        <Col xs={24} sm={20} md={16} lg={14} xl={10}>
          <Card
            style={{
              borderRadius: '12px',
              boxShadow: '0 10px 40px rgba(0,0,0,0.1)',
              border: 'none'
            }}
          >
            <div style={{ textAlign: 'center', marginBottom: '24px' }}>
              <Title level={2} style={{ color: '#667eea', marginBottom: '8px' }}>
                创建新账户
              </Title>
              <Text type="secondary">加入电解质实验室管理系统</Text>
            </div>

            <Form
              form={form}
              name="register"
              onFinish={onFinish}
              size="large"
              layout="vertical"
              scrollToFirstError
            >
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="用户名"
                    name="username"
                    rules={[
                      { required: true, message: '请输入用户名' },
                      { min: 3, max: 50, message: '用户名长度在3-50个字符之间' },
                      { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线' }
                    ]}
                  >
                    <Input
                      prefix={<UserOutlined style={{ color: 'rgba(0,0,0,.25)' }} />}
                      placeholder="请输入用户名"
                      autoComplete="username"
                    />
                  </Form.Item>
                </Col>

                <Col span={12}>
                  <Form.Item
                    label="真实姓名"
                    name="full_name"
                    rules={[
                      { required: true, message: '请输入真实姓名' }
                    ]}
                  >
                    <Input
                      prefix={<IdcardOutlined style={{ color: 'rgba(0,0,0,.25)' }} />}
                      placeholder="请输入真实姓名"
                      autoComplete="name"
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                label="邮箱地址"
                name="email"
                rules={[
                  { required: true, message: '请输入邮箱地址' },
                  { type: 'email', message: '请输入有效的邮箱地址' }
                ]}
              >
                <Input
                  prefix={<MailOutlined style={{ color: 'rgba(0,0,0,.25)' }} />}
                  placeholder="请输入邮箱地址"
                  autoComplete="email"
                />
              </Form.Item>

              <Form.Item
                label="所属机构（可选）"
                name="organization"
              >
                <Input
                  placeholder="请输入所属机构或公司"
                  autoComplete="organization"
                />
              </Form.Item>

              <Form.Item
                label="密码"
                name="password"
                rules={[
                  { required: true, message: '请输入密码' },
                  { min: 8, message: '密码至少8个字符' },
                  {
                    validator: (_, value) => {
                      if (!value) return Promise.resolve();
                      if (!/[a-z]/.test(value) || !/[A-Z]/.test(value)) {
                        return Promise.reject(new Error('密码必须包含大小写字母'));
                      }
                      if (!/[0-9]/.test(value)) {
                        return Promise.reject(new Error('密码必须包含数字'));
                      }
                      return Promise.resolve();
                    }
                  }
                ]}
              >
                <Input.Password
                  prefix={<LockOutlined style={{ color: 'rgba(0,0,0,.25)' }} />}
                  placeholder="请输入密码"
                  autoComplete="new-password"
                  onChange={(e) => checkPasswordStrength(e.target.value)}
                />
              </Form.Item>

              {passwordStrength > 0 && (
                <div style={{ marginBottom: '16px' }}>
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    密码强度：
                    <span style={{ color: getPasswordStrengthColor(), fontWeight: 'bold' }}>
                      {getPasswordStrengthText()}
                    </span>
                  </Text>
                  <Progress
                    percent={passwordStrength}
                    showInfo={false}
                    strokeColor={getPasswordStrengthColor()}
                    size="small"
                  />
                </div>
              )}

              <Form.Item
                label="确认密码"
                name="confirm_password"
                dependencies={['password']}
                rules={[
                  { required: true, message: '请再次输入密码' },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('password') === value) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error('两次输入的密码不一致'));
                    },
                  }),
                ]}
              >
                <Input.Password
                  prefix={<LockOutlined style={{ color: 'rgba(0,0,0,.25)' }} />}
                  placeholder="请再次输入密码"
                  autoComplete="new-password"
                />
              </Form.Item>

              <Form.Item
                name="agreement"
                valuePropName="checked"
                rules={[
                  {
                    validator: (_, value) =>
                      value ? Promise.resolve() : Promise.reject(new Error('请同意服务条款')),
                  },
                ]}
              >
                <Checkbox>
                  我已阅读并同意
                  <a href="/terms" target="_blank" rel="noopener noreferrer"> 服务条款 </a>
                  和
                  <a href="/privacy" target="_blank" rel="noopener noreferrer"> 隐私政策</a>
                </Checkbox>
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<UserAddOutlined />}
                  loading={loading}
                  block
                  style={{
                    height: '44px',
                    fontSize: '16px',
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    border: 'none'
                  }}
                >
                  注册账户
                </Button>
              </Form.Item>
            </Form>

            <Divider>
              <Text type="secondary">已有账户？</Text>
            </Divider>

            <div style={{ textAlign: 'center' }}>
              <Space>
                <Text type="secondary">如果您已经有账户，请</Text>
                <Link to="/login"><strong>直接登录</strong></Link>
              </Space>
            </div>
          </Card>

          <div style={{ textAlign: 'center', marginTop: '16px' }}>
            <Text style={{ color: 'rgba(255,255,255,0.8)' }}>
              © 2024 电解质实验室管理系统
            </Text>
          </div>
        </Col>
      </Row>

      {/* 侧边说明卡片 */}
      <Col
        xs={0}
        md={0}
        lg={10}
        xl={12}
        style={{ paddingLeft: '40px', color: 'white' }}
      >
        <div style={{ marginTop: '60px' }}>
          <Title level={2} style={{ color: 'white', marginBottom: '24px' }}>
            为什么选择我们？
          </Title>

          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start' }}>
              <CheckCircleOutlined style={{ fontSize: '24px', marginRight: '16px', marginTop: '4px' }} />
              <div>
                <Title level={4} style={{ color: 'white', marginBottom: '8px' }}>
                  AI辅助设计
                </Title>
                <Text style={{ color: 'rgba(255,255,255,0.8)' }}>
                  利用先进的人工智能技术，智能推荐电解质配方，加速研发进程
                </Text>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-start' }}>
              <CheckCircleOutlined style={{ fontSize: '24px', marginRight: '16px', marginTop: '4px' }} />
              <div>
                <Title level={4} style={{ color: 'white', marginBottom: '8px' }}>
                  自动化实验
                </Title>
                <Text style={{ color: 'rgba(255,255,255,0.8)' }}>
                  自动化实验执行和实时监控，提高实验效率和数据准确性
                </Text>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-start' }}>
              <CheckCircleOutlined style={{ fontSize: '24px', marginRight: '16px', marginTop: '4px' }} />
              <div>
                <Title level={4} style={{ color: 'white', marginBottom: '8px' }}>
                  闭环优化
                </Title>
                <Text style={{ color: 'rgba(255,255,255,0.8)' }}>
                  基于实验结果自动优化配方，实现持续改进和迭代
                </Text>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-start' }}>
              <CheckCircleOutlined style={{ fontSize: '24px', marginRight: '16px', marginTop: '4px' }} />
              <div>
                <Title level={4} style={{ color: 'white', marginBottom: '8px' }}>
                  文献挖掘
                </Title>
                <Text style={{ color: 'rgba(255,255,255,0.8)' }}>
                  自动提取和分析文献数据，快速获取领域最新研究成果
                </Text>
              </div>
            </div>
          </Space>
        </div>
      </Col>
    </div>
  );
};

export default RegisterPage;
