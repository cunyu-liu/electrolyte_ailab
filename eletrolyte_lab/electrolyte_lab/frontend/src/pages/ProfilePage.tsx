import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Avatar,
  Typography,
  Row,
  Col,
  Space,
  Divider,
  message,
  Tabs,
  List,
  Tag,
  Statistic,
  Upload,
  Modal,
  Descriptions,
  Alert,
  Switch,
  Select,
  DatePicker,
  TimePicker,
  Spin
} from 'antd';
import {
  UserOutlined,
  MailOutlined,
  EditOutlined,
  SaveOutlined,
  CameraOutlined,
  KeyOutlined,
  BellOutlined,
  SecurityScanOutlined,
  CalendarOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  UploadOutlined,
  DeleteOutlined,
  EyeOutlined,
  EyeInvisibleOutlined
} from '@ant-design/icons';
import type { UploadProps } from 'antd';
import { User, UpdateProfileForm, ChangePasswordForm } from '../types';
import { authApi } from '../services/api';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;
const { TextArea } = Input;

const ProfilePage: React.FC = () => {
  const [form] = Form.useForm();
  const [passwordForm] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [editing, setEditing] = useState(false);
  const [avatarUrl, setAvatarUrl] = useState<string>('');
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [fetchingUser, setFetchingUser] = useState(true);
  const [notificationSettings, setNotificationSettings] = useState({
    email_notifications: true,
    experiment_updates: true,
    system_alerts: true,
    weekly_reports: false
  });

  useEffect(() => {
    fetchCurrentUser();
  }, []);

  const fetchCurrentUser = async () => {
    setFetchingUser(true);
    try {
      const response = await authApi.getCurrentUser();
      if (response.success && response.data) {
        const user = response.data;
        setCurrentUser(user);
        form.setFieldsValue({
          email: user.email,
          username: user.username || '',
          full_name: user.full_name || '',
          organization: user.organization || '',
          bio: user.bio || ''
        });
        setAvatarUrl(user.avatar_url || '');
      }
    } catch (error) {
      console.error('获取用户信息失败:', error);
      message.error('获取用户信息失败');
    } finally {
      setFetchingUser(false);
    }
  };

  const handleUpdateProfile = async (values: UpdateProfileForm) => {
    setLoading(true);
    try {
      const response = await authApi.updateProfile(values);
      if (response.success) {
        message.success(response.message || '个人信息更新成功');
        setEditing(false);
        // 重新获取用户信息
        await fetchCurrentUser();
      }
    } catch (error: any) {
      console.error('Update profile error:', error);
      message.error(error.response?.data?.error || '更新失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleChangePassword = async (values: ChangePasswordForm) => {
    if (values.new_password !== values.confirm_password) {
      message.error('两次输入的密码不一致');
      return;
    }

    setPasswordLoading(true);
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1000));
      message.success('密码修改成功（演示模式）');
      passwordForm.resetFields();
    } catch (error: any) {
      console.error('Change password error:', error);
      message.error('密码修改失败，请重试');
    } finally {
      setPasswordLoading(false);
    }
  };

  const handleAvatarChange: UploadProps['onChange'] = (info) => {
    if (info.file.status === 'done') {
      setAvatarUrl(info.file.response.url);
      message.success('头像上传成功');
    } else if (info.file.status === 'error') {
      message.error('头像上传失败');
    }
  };

  const beforeUpload = (file: File) => {
    const isJpgOrPng = file.type === 'image/jpeg' || file.type === 'image/png';
    if (!isJpgOrPng) {
      message.error('只能上传 JPG/PNG 格式的图片');
      return false;
    }
    const isLt2M = file.size / 1024 / 1024 < 2;
    if (!isLt2M) {
      message.error('图片大小不能超过 2MB');
      return false;
    }
    return true;
  };

  const uploadButton = (
    <div>
      <CameraOutlined />
      <div style={{ marginTop: 8 }}>上传头像</div>
    </div>
  );

  const uploadProps: UploadProps = {
    name: 'avatar',
    action: '/api/upload/avatar',
    showUploadList: false,
    beforeUpload,
    onChange: handleAvatarChange,
    headers: {
      authorization: `Bearer ${localStorage.getItem('access_token')}`,
    },
  };

  // 直接渲染，无需检查认证状态

  return (
    <div style={{ padding: '24px', background: '#f5f5f5', minHeight: '100vh' }}>
      <Spin spinning={fetchingUser} tip="加载用户信息...">
        <Row gutter={[24, 24]}>
        <Col xs={24} md={8}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <Upload {...uploadProps}>
                <Avatar
                  size={100}
                  src={avatarUrl}
                  icon={<UserOutlined />}
                  style={{ cursor: 'pointer', border: '2px solid #667eea' }}
                />
              </Upload>
              <Title level={4} style={{ marginTop: 16, marginBottom: 4 }}>
                {currentUser?.full_name || currentUser?.username || '用户'}
              </Title>
              <Text type="secondary" style={{ fontSize: '14px' }}>
                {currentUser?.role === 'admin' ? '管理员' :
                 currentUser?.role === 'researcher' ? '研究员' : '普通用户'}
              </Text>
              <div style={{ marginTop: 16 }}>
                <Tag color={currentUser?.email_verified ? 'success' : 'warning'}>
                  {currentUser?.email_verified ? '已验证' : '未验证'}
                </Tag>
                <Tag color="blue">
                  {currentUser?.created_at ? `加入于 ${new Date(currentUser.created_at).getFullYear()}年` : '新用户'}
                </Tag>
              </div>
            </div>

            <Divider />

            <div style={{ marginBottom: 16 }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <Text type="secondary">邮箱</Text>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <MailOutlined />
                    <Text>{currentUser?.email || '未设置'}</Text>
                  </div>
                </div>
                {currentUser?.organization && (
                  <div>
                    <Text type="secondary">机构</Text>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <UserOutlined />
                      <Text>{currentUser.organization}</Text>
                    </div>
                  </div>
                )}
              </Space>
            </div>
          </Card>

          <Card title="账户统计" style={{ marginTop: 16 }}>
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title="实验次数"
                  value={currentUser?.experiment_count || 0}
                  prefix={<CalendarOutlined />}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="配方数量"
                  value={currentUser?.formula_count || 0}
                  prefix={<CheckCircleOutlined />}
                />
              </Col>
            </Row>
          </Card>
        </Col>

        <Col xs={24} md={16}>
          <Tabs defaultActiveKey="profile" type="card">
            <TabPane tab="个人信息" key="profile">
              <Card
                title="个人信息"
                extra={
                  <Button
                    type="link"
                    icon={editing ? <SaveOutlined /> : <EditOutlined />}
                    onClick={() => setEditing(!editing)}
                  >
                    {editing ? '保存' : '编辑'}
                  </Button>
                }
              >
                <Form
                  form={form}
                  layout="vertical"
                  onFinish={handleUpdateProfile}
                  disabled={!editing}
                >
                  <Row gutter={16}>
                    <Col xs={24} md={12}>
                      <Form.Item
                        label="用户名"
                        name="username"
                        rules={[
                          { max: 50, message: '用户名最多50个字符' },
                          { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线' }
                        ]}
                      >
                        <Input placeholder="请输入用户名" />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={12}>
                      <Form.Item
                        label="真实姓名"
                        name="full_name"
                        rules={[
                          { max: 100, message: '姓名最多100个字符' }
                        ]}
                      >
                        <Input placeholder="请输入真实姓名" />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Form.Item
                    label="邮箱地址"
                    name="email"
                  >
                    <Input disabled />
                  </Form.Item>

                  <Form.Item
                    label="机构/公司"
                    name="organization"
                    rules={[
                      { max: 100, message: '机构名称最多100个字符' }
                    ]}
                  >
                    <Input placeholder="请输入机构或公司名称" />
                  </Form.Item>

                  <Form.Item
                    label="个人简介"
                    name="bio"
                    rules={[
                      { max: 500, message: '个人简介最多500个字符' }
                    ]}
                  >
                    <TextArea
                      rows={4}
                      placeholder="请输入个人简介..."
                      showCount
                      maxLength={500}
                    />
                  </Form.Item>

                  {editing && (
                    <Form.Item>
                      <Space>
                        <Button
                          type="primary"
                          htmlType="submit"
                          loading={loading}
                          icon={<SaveOutlined />}
                        >
                          保存更改
                        </Button>
                        <Button onClick={() => setEditing(false)}>
                          取消
                        </Button>
                      </Space>
                    </Form.Item>
                  )}
                </Form>
              </Card>
            </TabPane>

            <TabPane tab="安全设置" key="security">
              <Card title="修改密码">
                <Form
                  form={passwordForm}
                  layout="vertical"
                  onFinish={handleChangePassword}
                >
                  <Form.Item
                    label="当前密码"
                    name="current_password"
                    rules={[
                      { required: true, message: '请输入当前密码' }
                    ]}
                  >
                    <Input.Password placeholder="请输入当前密码" />
                  </Form.Item>

                  <Form.Item
                    label="新密码"
                    name="new_password"
                    rules={[
                      { required: true, message: '请输入新密码' },
                      { min: 6, message: '密码至少6位字符' },
                      {
                        pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
                        message: '密码必须包含大小写字母和数字'
                      }
                    ]}
                  >
                    <Input.Password placeholder="请输入新密码" />
                  </Form.Item>

                  <Form.Item
                    label="确认新密码"
                    name="confirm_password"
                    dependencies={['new_password']}
                    rules={[
                      { required: true, message: '请确认新密码' },
                      ({ getFieldValue }) => ({
                        validator(_, value) {
                          if (!value || getFieldValue('new_password') === value) {
                            return Promise.resolve();
                          }
                          return Promise.reject(new Error('两次输入的密码不一致'));
                        },
                      }),
                    ]}
                  >
                    <Input.Password placeholder="请再次输入新密码" />
                  </Form.Item>

                  <Form.Item>
                    <Button
                      type="primary"
                      htmlType="submit"
                      loading={passwordLoading}
                      icon={<KeyOutlined />}
                    >
                      修改密码
                    </Button>
                  </Form.Item>
                </Form>
              </Card>

              <Card title="登录历史" style={{ marginTop: 16 }}>
                <List
                  itemLayout="horizontal"
                  dataSource={[
                    { time: '2024-01-15 14:30', ip: '192.168.1.100', location: '北京', device: 'Chrome' },
                    { time: '2024-01-14 09:15', ip: '192.168.1.100', location: '北京', device: 'Safari' },
                    { time: '2024-01-13 16:45', ip: '10.0.0.5', location: '上海', device: 'Firefox' },
                  ]}
                  renderItem={item => (
                    <List.Item>
                      <List.Item.Meta
                        avatar={<ClockCircleOutlined />}
                        title={item.time}
                        description={`${item.ip} - ${item.location} - ${item.device}`}
                      />
                    </List.Item>
                  )}
                />
              </Card>
            </TabPane>

            <TabPane tab="通知设置" key="notifications">
              <Card title="通知偏好">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <Title level={5} style={{ margin: 0 }}>邮件通知</Title>
                      <Text type="secondary">接收重要的系统邮件通知</Text>
                    </div>
                    <Switch
                      checked={notificationSettings.email_notifications}
                      onChange={(checked) =>
                        setNotificationSettings(prev => ({ ...prev, email_notifications: checked }))
                      }
                    />
                  </div>

                  <Divider />

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <Title level={5} style={{ margin: 0 }}>实验更新</Title>
                      <Text type="secondary">实验状态变更时通知我</Text>
                    </div>
                    <Switch
                      checked={notificationSettings.experiment_updates}
                      onChange={(checked) =>
                        setNotificationSettings(prev => ({ ...prev, experiment_updates: checked }))
                      }
                    />
                  </div>

                  <Divider />

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <Title level={5} style={{ margin: 0 }}>系统提醒</Title>
                      <Text type="secondary">系统维护和重要更新通知</Text>
                    </div>
                    <Switch
                      checked={notificationSettings.system_alerts}
                      onChange={(checked) =>
                        setNotificationSettings(prev => ({ ...prev, system_alerts: checked }))
                      }
                    />
                  </div>

                  <Divider />

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <Title level={5} style={{ margin: 0 }}>周报</Title>
                      <Text type="secondary">每周实验和配方汇总报告</Text>
                    </div>
                    <Switch
                      checked={notificationSettings.weekly_reports}
                      onChange={(checked) =>
                        setNotificationSettings(prev => ({ ...prev, weekly_reports: checked }))
                      }
                    />
                  </div>
                </Space>

                <div style={{ marginTop: 24 }}>
                  <Button type="primary" icon={<SaveOutlined />}>
                    保存设置
                  </Button>
                </div>
              </Card>
            </TabPane>
          </Tabs>
        </Col>
      </Row>
      </Spin>
    </div>
  );
};

export default ProfilePage;