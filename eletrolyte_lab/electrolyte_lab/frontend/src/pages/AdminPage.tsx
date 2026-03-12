import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  message,
  Row,
  Col,
  Statistic,
  Typography,
  Divider,
  Tabs,
  List,
  Avatar,
  Popconfirm,
  Switch
} from 'antd';
import {
  UserOutlined,
  SettingOutlined,
  BarChartOutlined,
  SafetyCertificateOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  PlusOutlined,
  ReloadOutlined,
  ExportOutlined,
  ImportOutlined,
  MailOutlined,
  LockOutlined,
  UnlockOutlined
} from '@ant-design/icons';
import { authApi } from '../services/api';
import { User } from '../types';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { Search } = Input;

const AdminPage: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [form] = Form.useForm();
  const [searchText, setSearchText] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  useEffect(() => {
    fetchUsers();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const response = await authApi.getUsers({
        page: 1,
        per_page: 100,
        role: roleFilter || undefined,
        search: searchText || undefined,
      });
      if (response.success && response.data) {
        setUsers(response.data.users);
      }
    } catch (error) {
      console.error('获取用户列表失败:', error);
      message.error('获取用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleEditUser = (user: User) => {
    setSelectedUser(user);
    form.setFieldsValue({
      username: user.username,
      email: user.email,
      full_name: user.full_name,
      role: user.role,
      is_active: user.is_active,
      is_verified: user.is_verified,
    });
    setModalVisible(true);
  };

  const handleViewUser = (user: User) => {
    setSelectedUser(user);
    setDetailModalVisible(true);
  };

  const handleUpdateUser = async (values: any) => {
    if (!selectedUser) return;

    setLoading(true);
    try {
      const response = await authApi.updateUser(selectedUser.id, values);
      if (response.success) {
        message.success(response.message || '用户信息更新成功');
        setModalVisible(false);
        fetchUsers();
      }
    } catch (error) {
      console.error('更新用户失败:', error);
      message.error('更新失败');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleUserStatus = async (user: User) => {
    try {
      const response = await authApi.updateUserStatus(user.id, !user.is_active);
      if (response.success) {
        message.success(response.message || `用户已${!user.is_active ? '启用' : '禁用'}`);
        fetchUsers();
      }
    } catch (error) {
      console.error('切换用户状态失败:', error);
      message.error('操作失败');
    }
  };

  const handleResetPassword = async (user: User) => {
    try {
      const response = await authApi.resetUserPassword(user.id);
      if (response.success) {
        message.success(response.message || '密码重置邮件已发送');
      }
    } catch (error) {
      console.error('重置密码失败:', error);
      message.error('发送失败');
    }
  };

  const userColumns = [
    {
      title: '用户',
      dataIndex: 'username',
      key: 'username',
      render: (text: string, record: User) => (
        <Space>
          <Avatar size="small" src={record.avatar} icon={<UserOutlined />} />
          <div>
            <div>{record.full_name || text}</div>
            <Text type="secondary" style={{ fontSize: '12px' }}>{record.email}</Text>
          </div>
        </Space>
      ),
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => {
        const colors = {
          admin: 'red',
          researcher: 'blue',
          user: 'green',
        };
        const labels = {
          admin: '管理员',
          researcher: '研究员',
          user: '普通用户',
        };
        return <Tag color={colors[role as keyof typeof colors]}>{labels[role as keyof typeof labels]}</Tag>;
      },
    },
    {
      title: '状态',
      key: 'status',
      render: (record: User) => (
        <Space>
          <Tag color={record.is_active ? 'success' : 'error'}>
            {record.is_active ? '正常' : '禁用'}
          </Tag>
          {record.is_verified && <Tag color="blue">已验证</Tag>}
        </Space>
      ),
    },
    {
      title: '注册时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
    {
      title: '最后登录',
      dataIndex: 'last_login_at',
      key: 'last_login_at',
      render: (date: string) => date ? new Date(date).toLocaleDateString() : '从未登录',
    },
    {
      title: '操作',
      key: 'actions',
      render: (record: User) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewUser(record)}
          >
            查看
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEditUser(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            icon={record.is_active ? <LockOutlined /> : <UnlockOutlined />}
            onClick={() => handleToggleUserStatus(record)}
          >
            {record.is_active ? '禁用' : '启用'}
          </Button>
          <Popconfirm
            title="确定要重置该用户的密码吗？"
            onConfirm={() => handleResetPassword(record)}
          >
            <Button
              type="link"
              size="small"
              icon={<MailOutlined />}
            >
              重置密码
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const filteredUsers = users.filter(user => {
    const matchSearch = !searchText ||
      user.username?.toLowerCase().includes(searchText.toLowerCase()) ||
      user.email?.toLowerCase().includes(searchText.toLowerCase()) ||
      user.full_name?.toLowerCase().includes(searchText.toLowerCase());

    const matchRole = !roleFilter || user.role === roleFilter;
    const matchStatus = !statusFilter ||
      (statusFilter === 'active' && user.is_active) ||
      (statusFilter === 'inactive' && !user.is_active) ||
      (statusFilter === 'verified' && user.is_verified) ||
      (statusFilter === 'unverified' && !user.is_verified);

    return matchSearch && matchRole && matchStatus;
  });

  const stats = {
    totalUsers: users.length,
    activeUsers: users.filter(u => u.is_active).length,
    verifiedUsers: users.filter(u => u.is_verified).length,
    adminUsers: users.filter(u => u.role === 'admin').length,
  };

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>管理员控制台</Title>

      {/* 统计概览 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总用户数"
              value={stats.totalUsers}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="活跃用户"
              value={stats.activeUsers}
              prefix={<BarChartOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已验证用户"
              value={stats.verifiedUsers}
              prefix={<SafetyCertificateOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="管理员"
              value={stats.adminUsers}
              prefix={<SettingOutlined />}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
      </Row>

      <Tabs defaultActiveKey="users">
        <TabPane tab="用户管理" key="users">
          <Card>
            <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
              <Space>
                <Search
                  placeholder="搜索用户名、邮箱或姓名"
                  allowClear
                  style={{ width: 300 }}
                  onSearch={setSearchText}
                  onChange={e => setSearchText(e.target.value)}
                />
                <Select
                  placeholder="筛选角色"
                  allowClear
                  style={{ width: 120 }}
                  onChange={setRoleFilter}
                >
                  <Select.Option value="user">普通用户</Select.Option>
                  <Select.Option value="researcher">研究员</Select.Option>
                  <Select.Option value="admin">管理员</Select.Option>
                </Select>
                <Select
                  placeholder="筛选状态"
                  allowClear
                  style={{ width: 120 }}
                  onChange={setStatusFilter}
                >
                  <Select.Option value="active">正常</Select.Option>
                  <Select.Option value="inactive">禁用</Select.Option>
                  <Select.Option value="verified">已验证</Select.Option>
                  <Select.Option value="unverified">未验证</Select.Option>
                </Select>
              </Space>
              <Space>
                <Button icon={<ReloadOutlined />} onClick={fetchUsers}>刷新</Button>
                <Button type="primary" icon={<PlusOutlined />}>添加用户</Button>
                <Button icon={<ExportOutlined />}>导出</Button>
              </Space>
            </div>

            <Table
              columns={userColumns}
              dataSource={filteredUsers}
              rowKey="id"
              loading={loading}
              pagination={{
                total: filteredUsers.length,
                pageSize: 10,
                showSizeChanger: true,
                showQuickJumper: true,
              }}
            />
          </Card>
        </TabPane>

        <TabPane tab="系统设置" key="settings">
          <Card title="系统配置">
            <List
              itemLayout="horizontal"
              dataSource={[
                { title: '用户注册', description: '是否允许新用户注册' },
                { title: '邮箱验证', description: '是否要求邮箱验证' },
                { title: '密码强度', description: '密码最小长度要求' },
                { title: '会话超时', description: '用户登录会话超时时间' },
              ]}
              renderItem={item => (
                <List.Item
                  actions={[
                    <Switch defaultChecked />
                  ]}
                >
                  <List.Item.Meta
                    title={item.title}
                    description={item.description}
                  />
                </List.Item>
              )}
            />
          </Card>
        </TabPane>

        <TabPane tab="系统监控" key="monitoring">
          <Row gutter={16}>
            <Col span={12}>
              <Card title="系统状态">
                <Statistic
                  title="系统运行时间"
                  value="15天 8小时 32分钟"
                />
                <Divider />
                <Statistic
                  title="今日活跃用户"
                  value={128}
                  valueStyle={{ color: '#3f8600' }}
                />
                <Divider />
                <Statistic
                  title="当前在线用户"
                  value={24}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
            <Col span={12}>
              <Card title="资源使用情况">
                <Statistic
                  title="CPU使用率"
                  value={45.6}
                  suffix="%"
                  valueStyle={{ color: '#3f8600' }}
                />
                <Divider />
                <Statistic
                  title="内存使用率"
                  value={68.2}
                  suffix="%"
                  valueStyle={{ color: '#fa8c16' }}
                />
                <Divider />
                <Statistic
                  title="磁盘使用率"
                  value={32.1}
                  suffix="%"
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
          </Row>
        </TabPane>
      </Tabs>

      {/* 编辑用户Modal */}
      <Modal
        title="编辑用户"
        visible={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleUpdateUser}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="用户名" name="username">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="邮箱" name="email">
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="真实姓名" name="full_name">
            <Input />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="角色" name="role">
                <Select>
                  <Select.Option value="user">普通用户</Select.Option>
                  <Select.Option value="researcher">研究员</Select.Option>
                  <Select.Option value="admin">管理员</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="账户状态" name="is_active" valuePropName="checked">
                <Switch checkedChildren="正常" unCheckedChildren="禁用" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="邮箱验证" name="is_verified" valuePropName="checked">
            <Switch checkedChildren="已验证" unCheckedChildren="未验证" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                保存
              </Button>
              <Button onClick={() => setModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 查看用户详情Modal */}
      <Modal
        title="用户详情"
        visible={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={700}
      >
        {selectedUser && (
          <List
            itemLayout="horizontal"
            dataSource={[
              { title: '用户ID', content: selectedUser.id },
              { title: '用户名', content: selectedUser.username },
              { title: '邮箱', content: selectedUser.email },
              { title: '真实姓名', content: selectedUser.full_name },
              { title: '角色', content: selectedUser.role },
              { title: '账户状态', content: selectedUser.is_active ? '正常' : '禁用' },
              { title: '邮箱验证', content: selectedUser.is_verified ? '已验证' : '未验证' },
              { title: '注册时间', content: new Date(selectedUser.created_at).toLocaleString() },
              { title: '最后登录', content: selectedUser.last_login_at ? new Date(selectedUser.last_login_at).toLocaleString() : '从未登录' },
            ]}
            renderItem={item => (
              <List.Item>
                <List.Item.Meta
                  title={item.title}
                  description={item.content}
                />
              </List.Item>
            )}
          />
        )}
      </Modal>
    </div>
  );
};

export default AdminPage;