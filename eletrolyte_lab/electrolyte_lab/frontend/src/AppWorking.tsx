import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, Link } from 'react-router-dom';
import { Layout, Menu, Button, Card, Form, Input, Typography, theme, ConfigProvider, Space, message } from 'antd';
import {
  HomeOutlined,
  ExperimentOutlined,
  MonitorOutlined,
  BarChartOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SafetyCertificateOutlined,
  FileTextOutlined
} from '@ant-design/icons';
import zhCN from 'antd/locale/zh_CN';

// Import the actual pages
import AIDesignerPage from './pages/AIDesignerPage';
import AIExperimenterPage from './pages/AIExperimenterPage';
import ClosedLoopPage from './pages/ClosedLoopPage';
import ExperimentListPage from './pages/ExperimentListPage';

const { Title, Text } = Typography;
const { Header, Sider, Content } = Layout;

// 模拟用户数据
const mockUsers = {
  'admin@example.com': { password: 'admin123', role: 'admin', name: '管理员' },
  'user@example.com': { password: 'user123', role: 'user', name: '普通用户' }
};

const AppWorking: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const {
    token: { colorBgContainer },
  } = theme.useToken();

  // 检查是否已登录
  const checkLoginStatus = () => {
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch (error) {
        localStorage.removeItem('user');
      }
    }
  };

  React.useEffect(() => {
    checkLoginStatus();
  }, []);

  const handleLogin = async (values: any) => {
    setLoading(true);
    try {
      // 模拟登录验证
      const userData = mockUsers[values.email];
      if (userData && userData.password === values.password) {
        const userInfo = {
          email: values.email,
          role: userData.role,
          name: userData.name,
          is_active: true,
          is_verified: true
        };

        localStorage.setItem('user', JSON.stringify(userInfo));
        localStorage.setItem('access_token', 'mock-token-' + Date.now());
        setUser(userInfo);
      } else {
        throw new Error('用户名或密码错误');
      }
    } catch (error: any) {
      console.error('登录错误:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('user');
    localStorage.removeItem('access_token');
    setUser(null);
  };

  // 登录页面
  const LoginPage = () => (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <Card
        style={{
          width: '100%',
          maxWidth: 400,
          borderRadius: '8px',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)'
        }}
        bodyStyle={{ padding: '40px' }}
      >
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <SafetyCertificateOutlined style={{ fontSize: '48px', color: '#667eea', marginBottom: 16 }} />
          <Title level={3} style={{ color: '#333', margin: 0 }}>
            悟行：智能电池设计与实验系统
          </Title>
          <Text type="secondary">
            基于人工智能的电池配方设计与实验自动化平台
          </Text>
        </div>

        <Form
          onFinish={handleLogin}
          layout="vertical"
          size="large"
        >
          <Form.Item
            name="email"
            label="邮箱"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效的邮箱地址' }
            ]}
          >
            <Input placeholder="请输入邮箱" />
          </Form.Item>

          <Form.Item
            name="password"
            label="密码"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password placeholder="请输入密码" />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              size="large"
              style={{ height: '40px', borderRadius: '4px' }}
            >
              登录
            </Button>
          </Form.Item>
        </Form>

        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            测试账号：admin@example.com / admin123
          </Text>
          <br />
          <Text type="secondary" style={{ fontSize: '12px' }}>
            或：user@example.com / user123
          </Text>
        </div>
      </Card>
    </div>
  );

  // 主页面包装器
  const MainLayoutWrapper = () => {
    const location = useLocation();
    return <MainLayout location={location} />;
  };

  // 主页面
  const MainLayout = ({ location }: { location: any }) => {
    const menuItems = [
      {
        key: '/',
        icon: <HomeOutlined />,
        label: <Link to="/">首页</Link>,
      },
      {
        key: '/ai-designer',
        icon: <ExperimentOutlined />,
        label: <Link to="/ai-designer">AI设计员</Link>,
      },
      {
        key: '/ai-experimenter',
        icon: <MonitorOutlined />,
        label: <Link to="/ai-experimenter">AI实验员</Link>,
      },
      {
        key: '/closed-loop',
        icon: <BarChartOutlined />,
        label: <Link to="/closed-loop">闭环优化</Link>,
      },
      {
        key: '/experiments/list',
        icon: <FileTextOutlined />,
        label: <Link to="/experiments/list">实验记录</Link>,
      },
    ];

    return (
      <Layout style={{ minHeight: '100vh' }}>
        <Sider
          trigger={null}
          collapsible
          collapsed={collapsed}
          style={{
            overflow: 'auto',
            height: '100vh',
            position: 'fixed',
            left: 0,
            top: 0,
            bottom: 0,
            background: '#660874'
          }}
        >
          <div style={{
            height: 32,
            margin: 16,
            background: 'rgba(255, 255, 255, 0.3)',
            borderRadius: 6,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontWeight: 'bold'
          }}>
            {collapsed ? 'AI电池' : '悟行：智能电池设计与实验系统'}
          </div>
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[location?.pathname || '/']}
            items={menuItems}
            style={{ height: 'calc(100vh - 64px)', borderRight: 0 }}
          />
        </Sider>
        <Layout>
          <Header
            style={{
              padding: 0,
              background: colorBgContainer,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              paddingRight: 24,
              marginLeft: collapsed ? 80 : 200,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <Button
                type="text"
                icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                onClick={() => setCollapsed(!collapsed)}
                style={{
                  fontSize: '16px',
                  width: 64,
                  height: 64,
                }}
              />
              <Title level={3} style={{ margin: 0, color: '#660874' }}>
                首页
              </Title>
            </div>
            <Space>
              <span style={{ color: '#666' }}>欢迎，{user?.name || '用户'}</span>
              <Button
                type="text"
                icon={<LogoutOutlined />}
                onClick={handleLogout}
              >
                退出登录
              </Button>
            </Space>
          </Header>
          <Content
            style={{
              margin: '24px 16px',
              marginLeft: collapsed ? 80 : 200,
              padding: 24,
              minHeight: 280,
              background: colorBgContainer,
              borderRadius: 8,
            }}
          >
            {/* 根据路径显示不同内容 */}
            {location?.pathname === '/' && (
              <>
                <Card title="系统统计" style={{ marginBottom: 24 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
                    <div style={{ textAlign: 'center', padding: '20px', background: '#f5f5f5', borderRadius: '8px' }}>
                      <Title level={2}>156</Title>
                      <Text>总实验数</Text>
                    </div>
                    <div style={{ textAlign: 'center', padding: '20px', background: '#e6f7ff', borderRadius: '8px' }}>
                      <Title level={2}>142</Title>
                      <Text>已完成实验</Text>
                    </div>
                    <div style={{ textAlign: 'center', padding: '20px', background: '#f6ffed', borderRadius: '8px' }}>
                      <Title level={2}>91%</Title>
                      <Text>成功率</Text>
                    </div>
                  </div>
                </Card>

                <Card title="功能模块" style={{ marginBottom: 24 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
                    <Link to="/ai-designer">
                      <Button type="dashed" size="large" style={{ height: '120px', display: 'flex', flexDirection: 'column', justifyContent: 'center', width: '100%' }}>
                        <ExperimentOutlined style={{ fontSize: '24px', marginBottom: '8px' }} />
                        AI设计员
                      </Button>
                    </Link>
                    <Link to="/ai-experimenter">
                      <Button type="dashed" size="large" style={{ height: '120px', display: 'flex', flexDirection: 'column', justifyContent: 'center', width: '100%' }}>
                        <MonitorOutlined style={{ fontSize: '24px', marginBottom: '8px' }} />
                        AI实验员
                      </Button>
                    </Link>
                    <Link to="/closed-loop">
                      <Button type="dashed" size="large" style={{ height: '120px', display: 'flex', flexDirection: 'column', justifyContent: 'center', width: '100%' }}>
                        <BarChartOutlined style={{ fontSize: '24px', marginBottom: '8px' }} />
                        闭环优化
                      </Button>
                    </Link>
                  </div>
                </Card>

                <Card title="系统公告">
                  <Text>悟行：智能电池设计与实验系统已成功部署，所有模块正常运行。当前支持正极材料配方设计，涵盖蓄能、动力、3C等多种应用场景。</Text>
                </Card>
              </>
            )}

            {/* AI设计员页面 */}
            {location?.pathname === '/ai-designer' && (
              <AIDesignerPage />
            )}

            {/* AI实验员页面 */}
            {location?.pathname === '/ai-experimenter' && (
              <AIExperimenterPage />
            )}

            {/* 实验记录页面 */}
            {location?.pathname === '/experiments/list' && (
              <ExperimentListPage />
            )}

            {/* 闭环优化页面 */}
            {location?.pathname === '/closed-loop' && (
              <ClosedLoopPage />
            )}
          </Content>
        </Layout>
      </Layout>
    );
  };

  // 自定义主题
  const customTheme = {
    token: {
      colorPrimary: '#660874',
      colorSuccess: '#52c41a',
      colorWarning: '#faad14',
      colorError: '#ff4d4f',
      colorInfo: '#1677ff',
    },
    components: {
      Layout: {
        siderBg: '#660874',
        headerBg: '#ffffff',
      },
    },
  };

  return (
    <ConfigProvider theme={customTheme} locale={zhCN}>
      <BrowserRouter>
        {user ? <MainLayoutWrapper /> : <LoginPage />}
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default AppWorking;