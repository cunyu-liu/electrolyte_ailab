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
  Space
} from 'antd';
import {
  UserOutlined,
  LockOutlined,
  LoginOutlined
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { authApi } from '../services/api';
import { LoginForm } from '../types';

const { Title, Text, Link } = Typography;

const LoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as any)?.from?.pathname || '/home';

  const onFinish = async (values: LoginForm) => {
    setLoading(true);
    try {
      const response = await authApi.login({
        username: values.username,
        password: values.password
      });

      if (response.success && response.data) {
        // 保存令牌
        localStorage.setItem('access_token', response.data.access_token);
        localStorage.setItem('refresh_token', response.data.refresh_token);
        localStorage.setItem('user', JSON.stringify(response.data.user));

        message.success('登录成功！');

        // 跳转到原来的页面或首页
        navigate(from, { replace: true });
      }
    } catch (error: any) {
      console.error('Login error:', error);
      message.error(error.response?.data?.error || '登录失败，请检查用户名和密码');
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
      <Row justify="center" align="middle" style={{ width: '100%' }}>
        <Col xs={24} sm={20} md={16} lg={12} xl={8}>
          <Card
            style={{
              borderRadius: '12px',
              boxShadow: '0 10px 40px rgba(0,0,0,0.1)',
              border: 'none'
            }}
          >
            <div style={{ textAlign: 'center', marginBottom: '24px' }}>
              <Title level={2} style={{ color: '#667eea', marginBottom: '8px' }}>
                电解质实验室管理系统
              </Title>
              <Text type="secondary">欢迎回来，请登录您的账户</Text>
            </div>

            <Form
              name="login"
              initialValues={{ remember: true }}
              onFinish={onFinish}
              size="large"
              layout="vertical"
            >
              <Form.Item
                label="用户名/邮箱"
                name="username"
                rules={[
                  { required: true, message: '请输入用户名或邮箱' },
                  { min: 3, message: '用户名至少3个字符' }
                ]}
              >
                <Input
                  prefix={<UserOutlined style={{ color: 'rgba(0,0,0,.25)' }} />}
                  placeholder="请输入用户名或邮箱"
                  autoComplete="username"
                />
              </Form.Item>

              <Form.Item
                label="密码"
                name="password"
                rules={[
                  { required: true, message: '请输入密码' },
                  { min: 8, message: '密码至少8个字符' }
                ]}
              >
                <Input.Password
                  prefix={<LockOutlined style={{ color: 'rgba(0,0,0,.25)' }} />}
                  placeholder="请输入密码"
                  autoComplete="current-password"
                />
              </Form.Item>

              <Form.Item>
                <Form.Item name="remember" valuePropName="checked" noStyle>
                  <Checkbox>记住我</Checkbox>
                </Form.Item>
                <Link style={{ float: 'right' }} href="/forgot-password">
                  忘记密码？
                </Link>
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<LoginOutlined />}
                  loading={loading}
                  block
                  style={{
                    height: '44px',
                    fontSize: '16px',
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    border: 'none'
                  }}
                >
                  登录
                </Button>
              </Form.Item>
            </Form>

            <Divider>
              <Text type="secondary">还没有账户？</Text>
            </Divider>

            <div style={{ textAlign: 'center' }}>
              <Space>
                <Text type="secondary">如果您还没有账户，请</Text>
                <Link href="/register" strong>注册新账户</Link>
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
    </div>
  );
};

export default LoginPage;
