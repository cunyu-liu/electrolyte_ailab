import React from 'react';
import { Routes, Route, useLocation, Link, Navigate, useNavigate } from 'react-router-dom';
import { Layout, Menu, theme, ConfigProvider, Button, Avatar, Dropdown, message } from 'antd';
import {
  ExperimentOutlined,
  BarChartOutlined,
  MonitorOutlined,
  SettingOutlined,
  HomeOutlined,
  ExperimentFilled,
  UserOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  LogoutOutlined
} from '@ant-design/icons';
import './App.css';

import HomePage from './pages/HomePageSimple';
import AIDesignerPage from './pages/AIDesignerPage';
import AIExperimenterPage from './pages/AIExperimenterPage';
import ClosedLoopPage from './pages/ClosedLoopPage';
import ExperimentListPage from './pages/ExperimentListPage';
import LiteraturePage from './pages/LiteraturePage';
import ProfilePage from './pages/ProfilePage';
import AdminPage from './pages/AdminPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import PageTransition from './components/PageTransition';
import { authApi } from './services/api';

const { Header, Sider, Content } = Layout;

// 受保护的路由组件
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const token = localStorage.getItem('access_token');
  const location = useLocation();

  if (!token) {
    // 没有token，重定向到登录页
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

// 主布局组件
const MainLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [collapsed, setCollapsed] = React.useState(false);
  const [currentUser, setCurrentUser] = React.useState<any>(null);
  const location = useLocation();
  const navigate = useNavigate();

  // 从localStorage获取用户信息
  React.useEffect(() => {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        setCurrentUser(JSON.parse(userStr));
      } catch (error) {
        console.error('Failed to parse user info:', error);
      }
    }
  }, []);

  const handleLogout = async () => {
    try {
      await authApi.logout();
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      message.success('登出成功');
      navigate('/login');
    } catch (error) {
      // 即使API调用失败，也要清除本地存储
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      navigate('/login');
    }
  };

  const menuItems = [
    {
      key: '/home',
      icon: <HomeOutlined />,
      label: <Link to="/home">首页</Link>,
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
      icon: <ExperimentFilled />,
      label: <Link to="/experiments/list">实验记录</Link>,
    },
    ...(currentUser?.role === 'admin' ? [{
      key: '/admin',
      icon: <SettingOutlined />,
      label: <Link to="/admin">管理后台</Link>,
    }] : []),
    {
      key: '/profile',
      icon: <UserOutlined />,
      label: <Link to="/profile">个人中心</Link>,
    },
  ];

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: <Link to="/profile">个人中心</Link>,
    },
    {
      key: 'divider',
      type: 'divider' as const,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: (
        <span onClick={handleLogout} style={{ cursor: 'pointer' }}>
          退出登录
        </span>
      ),
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
        }}
      >
        <div className="demo-logo-vertical" style={{
          height: 48,
          margin: '16px',
          background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.2) 0%, rgba(255, 255, 255, 0.1) 100%)',
          borderRadius: '12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontWeight: 700,
          fontSize: collapsed ? '14px' : '16px',
          position: 'sticky',
          top: 0,
          zIndex: 1,
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.2)',
          boxShadow: '0 4px 16px rgba(0, 0, 0, 0.1)',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          letterSpacing: '0.5px'
        }}>
          {collapsed ? '🔬' : '🔬 悟行电池实验室'}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          style={{ height: 'calc(100vh - 64px)', overflowY: 'auto' }}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: '0 16px',
            background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(255, 255, 255, 0.95) 100%)',
            backdropFilter: 'blur(20px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid rgba(102, 8, 116, 0.1)',
            boxShadow: '0 2px 16px rgba(102, 8, 116, 0.08)',
            marginLeft: collapsed ? 80 : 200,
            transition: 'margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            height: '70px', // 增加header高度
            position: 'sticky',
            top: 0,
            zIndex: 100
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              style={{
                fontSize: '16px',
                width: '40px',
                height: '40px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, rgba(102, 8, 116, 0.05) 0%, rgba(156, 39, 176, 0.05) 100%)',
                border: '1px solid rgba(102, 8, 116, 0.1)',
                color: '#660874',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                fontWeight: 500,
                flexShrink: 0
              }}
            />
            <div style={{
              minWidth: 0,
              flex: 1,
              maxWidth: 'calc(100vw - 280px)', // 调整最大宽度
              overflow: 'visible',
              paddingRight: '16px', // 添加右边距
              paddingTop: '0px', // 移除向下移动
              position: 'relative',
              zIndex: 1000 // 确保在最上层
            }}>
              <h1 style={{
                margin: '0 0 2px 0', // 减少下边距
                color: '#333333', // 使用深灰色确保可读性
                fontSize: '24px', // 缩小字体
                fontWeight: 'bold',
                lineHeight: 1.1, // 减少行高
                whiteSpace: 'normal', // 允许换行
                wordWrap: 'break-word',
                wordBreak: 'break-word',
                overflow: 'visible',
                textOverflow: 'clip',
                maxWidth: 'none',
                width: 'auto',
                position: 'relative',
                zIndex: 1001,
                backgroundColor: 'transparent', // 透明背景
                padding: '0', // 移除内边距
                borderRadius: '0', // 移除圆角
                border: 'none' // 移除边框
              }}>
                悟行：智能电池设计与实验系统
              </h1>
              <p style={{
                margin: '2px 0 0 0', // 减少上边距
                color: '#666666', // 使用中灰色
                fontSize: '14px', // 缩小字体
                fontWeight: 'normal',
                lineHeight: 1.1, // 减少行高
                whiteSpace: 'normal', // 允许换行
                wordWrap: 'break-word',
                wordBreak: 'break-word',
                overflow: 'visible',
                textOverflow: 'clip',
                maxWidth: 'none',
                width: 'auto',
                position: 'relative',
                zIndex: 1001,
                backgroundColor: 'transparent', // 透明背景
                padding: '0', // 移除内边距
                borderRadius: '0', // 移除圆角
                border: 'none' // 移除边框
              }}>
                从需求到配方的闭环优化平台
              </p>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <Dropdown
              menu={{ items: userMenuItems }}
              placement="bottomRight"
              arrow
            >
              <div style={{
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px', // 增加间距
                padding: '4px 8px', // 适度内边距
                background: 'transparent', // 透明背景
                border: 'none' // 移除边框
              }}>
                <Avatar
                  size="default" // 恢复默认大小 (32px)
                  icon={<UserOutlined />}
                  style={{
                    background: '#660874',
                    border: 'none'
                  }}
                />
                <span style={{
                  fontWeight: 500,
                  color: '#333333', // 使用深灰色提高可读性
                  fontSize: '14px', // 适中的字体大小
                  whiteSpace: 'nowrap'
                }}>
                  {currentUser?.full_name || currentUser?.username || '用户'}
                </span>
              </div>
            </Dropdown>
          </div>
        </Header>
        <Content
          style={{
            margin: '32px 24px',
            marginLeft: collapsed ? 80 : 200,
            padding: '32px',
            minHeight: 'calc(100vh - 158px)', // 调整最小高度适应新的header高度
            background: 'transparent',
            borderRadius: 0,
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            position: 'relative'
          }}
        >
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

const App: React.FC = () => {
  // Enhanced custom theme using #660874 as base purple palette
  const customTheme = {
    token: {
      colorPrimary: '#660874', // Base deep purple (R102 G8 B116)
      colorSuccess: '#52c41a', // Default green for success
      colorWarning: '#faad14', // Default orange for warnings
      colorError: '#ff4d4f', // Default red for errors
      colorInfo: '#1677ff', // Default blue for info
      colorBgContainer: 'transparent', // Transparent background for cards
      colorBgLayout: 'transparent', // Transparent layout background
      colorBgSpotlight: 'transparent', // Transparent spotlight background
      colorBorder: 'rgba(102, 8, 116, 0.15)', // Purple-tinted border color
      colorTextLightSolid: '#ffffff', // Sidebar text color
      colorBgElevated: 'rgba(255, 255, 255, 0.95)', // Elevated background
      colorText: '#333333', // Default text color
      colorTextSecondary: '#666666', // Secondary text color
      colorTextTertiary: '#999999', // Tertiary text color
      borderRadius: 16, // Increased border radius for modern look
      borderRadiusLG: 20, // Large border radius
      borderRadiusSM: 12, // Small border radius
      wireframe: false, // Disable wireframe mode for cleaner look
    },
    components: {
      Menu: {
        // 使用新的 token 名称，移除已弃用的 `color*` 前缀属性
        itemBg: 'transparent',
        itemSelectedBg: 'rgba(255, 255, 255, 0.15)', // 增强选中背景色
        itemSelectedColor: '#ffffff',
        itemColor: '#ffffff', // 提高对比度，使用纯白色
        itemHoverColor: '#ffffff',
        groupTitleColor: '#ffffff', // 提高对比度，使用纯白色
        itemHoverBg: 'rgba(255, 255, 255, 0.08)', // 增强悬停背景色
        borderRadius: 12,
        itemMarginInline: 8,
        itemMarginBlock: 4,
      },
      Layout: {
        siderBg: 'linear-gradient(135deg, #660874 0%, #4a0563 100%)', // Gradient sidebar background
        headerBg: 'transparent',
        bodyBg: 'transparent',
      },
      Button: {
        colorPrimary: '#660874',
        colorPrimaryHover: '#4a0563',
        colorPrimaryActive: '#330242',
        colorPrimaryText: '#ffffff',
        colorTextLightSolid: '#ffffff',
        colorText: '#333333',
        borderRadius: 12,
        borderRadiusLG: 16,
        borderRadiusSM: 8,
        controlHeight: 40,
        controlHeightLG: 48,
        controlHeightSM: 32,
        paddingContentHorizontal: 20,
        paddingContentHorizontalLG: 24,
        paddingContentHorizontalSM: 16,
      },
      Card: {
        borderRadius: 16,
        borderRadiusLG: 20,
        paddingLG: 24,
        padding: 20,
        paddingSM: 16,
      },
      Input: {
        borderRadius: 12,
        borderRadiusLG: 16,
        borderRadiusSM: 8,
        controlHeight: 40,
        controlHeightLG: 48,
        controlHeightSM: 32,
      },
      Select: {
        borderRadius: 12,
        borderRadiusLG: 16,
        borderRadiusSM: 8,
        controlHeight: 40,
        controlHeightLG: 48,
        controlHeightSM: 32,
      },
      Table: {
        borderRadius: 16,
        headerBg: 'transparent',
        headerBorderRadius: 16,
      },
      Modal: {
        borderRadius: 20,
        borderRadiusLG: 24,
      },
      Alert: {
        borderRadius: 16,
        borderRadiusLG: 20,
      },
      Tooltip: {
        borderRadius: 12,
      },
      Popover: {
        borderRadius: 16,
      },
      Dropdown: {
        borderRadius: 12,
      },
      Tag: {
        borderRadius: 20,
      },
    },
  };

  return (
    <ConfigProvider theme={customTheme}>
      <Routes>
        {/* 公开路由（不需要登录） */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* 受保护的路由（需要登录） */}
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <MainLayout>
                <PageTransition>
                  <Routes>
                    {/* 根路径直接跳转到首页 */}
                    <Route path="/" element={<Navigate to="/home" replace />} />
                    {/* 主页路由 */}
                    <Route path="/home" element={<HomePage />} />
                    {/* AI 设计员路由 */}
                    <Route path="/ai-designer" element={<AIDesignerPage />} />
                    {/* AI 实验员路由 */}
                    <Route path="/ai-experimenter" element={<AIExperimenterPage />} />
                    {/* 闭环优化路由 */}
                    <Route path="/closed-loop" element={<ClosedLoopPage />} />
                    {/* 实验列表路由 */}
                    <Route path="/experiments/list" element={<ExperimentListPage />} />
                    {/* 文献路由 */}
                    <Route path="/literature" element={<LiteraturePage />} />
                    {/* 个人资料路由 */}
                    <Route path="/profile" element={<ProfilePage />} />
                    {/* 管理后台路由 */}
                    <Route path="/admin" element={<AdminPage />} />
                    {/* 默认重定向到首页 */}
                    <Route path="*" element={<Navigate to="/home" replace />} />
                  </Routes>
                </PageTransition>
              </MainLayout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </ConfigProvider>
  );
};

export default App;