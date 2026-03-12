import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Tag,
  Input,
  Space,
  Typography,
  Modal,
  Descriptions,
  Tabs
} from 'antd';
import { SearchOutlined, EyeOutlined } from '@ant-design/icons';
import { aiDesignerApi } from '../services/api';
import { Formula } from '../types';

const { Title, Paragraph } = Typography;
const { Search } = Input;
const { TabPane } = Tabs;

const FormulaListPage: React.FC = () => {
  const [formulas, setFormulas] = useState<Formula[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedFormula, setSelectedFormula] = useState<Formula | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0
  });

  useEffect(() => {
    loadFormulas();
  }, [pagination.current, pagination.pageSize]);

  const loadFormulas = async () => {
    setLoading(true);
    try {
      const response = await aiDesignerApi.listFormulas({
        page: pagination.current,
        per_page: pagination.pageSize
      });
      if (response.success && response.data) {
        setFormulas(response.data.formulas);
        setPagination(prev => ({
          ...prev,
          total: response.data!.total
        }));
      }
    } catch (error) {
      console.error('Failed to load formulas:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (value: string) => {
    // 实现搜索逻辑
    console.log('Search:', value);
  };

  const showDetail = (formula: Formula) => {
    setSelectedFormula(formula);
    setDetailModalVisible(true);
  };

  // 渲染生成方法的标签颜色
  const getGenerationMethodColor = (method: string) => {
    const colorMap: Record<string, string> = {
      'initial_design': 'blue',
      'bayesian_opt': 'green',
      'redesign': 'orange'
    };
    return colorMap[method] || 'default';
  };

  // 渲染生成方法的文本
  const getGenerationMethodText = (method: string) => {
    const textMap: Record<string, string> = {
      'initial_design': '初始设计',
      'bayesian_opt': '贝叶斯优化',
      'redesign': '重新设计'
    };
    return textMap[method] || method;
  };

  // 表格列定义
  const columns = [
    {
      title: '配方ID',
      dataIndex: 'id',
      key: 'id',
      width: 80
    },
    {
      title: '配方名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Formula) => (
        <Button type="link" onClick={() => showDetail(record)}>
          {text}
        </Button>
      )
    },
    {
      title: '体系类型',
      dataIndex: 'system_type',
      key: 'system_type',
      width: 100,
      render: (type: string) => (
        <Tag color={type === '正极' ? 'blue' : 'green'}>
          {type}
        </Tag>
      )
    },
    {
      title: '应用场景',
      dataIndex: 'application_scenario',
      key: 'application_scenario',
      width: 100,
      render: (scenario: string) => scenario || '通用'
    },
    {
      title: '生成方法',
      dataIndex: 'generation_method',
      key: 'generation_method',
      width: 120,
      render: (method: string) => (
        <Tag color={getGenerationMethodColor(method)}>
          {getGenerationMethodText(method)}
        </Tag>
      )
    },
    {
      title: '组件数量',
      key: 'components_count',
      width: 100,
      render: (record: Formula) => record.components?.length || 0
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date: string) => new Date(date).toLocaleString()
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (record: Formula) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => showDetail(record)}
        >
          详情
        </Button>
      )
    }
  ];

  return (
    <div>
      <div className="page-header">
        <Title level={2}>配方管理</Title>
        <Paragraph>
          查看和管理所有生成的电池电解液配方，包括初始设计、贝叶斯优化和重新设计的配方。
        </Paragraph>
      </div>

      {/* 搜索和筛选 */}
      <Card style={{ marginBottom: 24 }}>
        <Space size="large">
          <Search
            placeholder="搜索配方名称或描述"
            allowClear
            enterButton={<SearchOutlined />}
            style={{ width: 300 }}
            onSearch={handleSearch}
          />
        </Space>
      </Card>

      {/* 配方列表 */}
      <Card title="配方列表">
        <Table
          columns={columns}
          dataSource={formulas}
          rowKey="id"
          loading={loading}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
            onChange: (page, pageSize) => {
              setPagination(prev => ({
                ...prev,
                current: page,
                pageSize: pageSize || 10
              }));
            }
          }}
        />
      </Card>

      {/* 配方详情模态框 */}
      <Modal
        title="配方详情"
        visible={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={900}
      >
        {selectedFormula && (
          <Tabs>
            <TabPane tab="基本信息" key="basic">
              <Descriptions bordered column={2}>
                <Descriptions.Item label="配方ID">
                  {selectedFormula.id}
                </Descriptions.Item>
                <Descriptions.Item label="配方名称">
                  {selectedFormula.name}
                </Descriptions.Item>
                <Descriptions.Item label="体系类型">
                  <Tag color={selectedFormula.system_type === '正极' ? 'blue' : 'green'}>
                    {selectedFormula.system_type}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="应用场景">
                  {selectedFormula.application_scenario || '通用'}
                </Descriptions.Item>
                <Descriptions.Item label="生成方法">
                  <Tag color={getGenerationMethodColor(selectedFormula.generation_method)}>
                    {getGenerationMethodText(selectedFormula.generation_method)}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="创建时间">
                  {new Date(selectedFormula.created_at).toLocaleString()}
                </Descriptions.Item>
                <Descriptions.Item label="描述" span={2}>
                  {selectedFormula.description}
                </Descriptions.Item>
              </Descriptions>
            </TabPane>
            <TabPane tab="配方组分" key="components">
              <Table
                dataSource={selectedFormula.components}
                rowKey="id"
                pagination={false}
                size="small"
                columns={[
                  {
                    title: '类型',
                    dataIndex: 'component_type',
                    key: 'component_type',
                    width: 100,
                    render: (type: string) => {
                      const typeMap: Record<string, { text: string; color: string }> = {
                        'solvent': { text: '溶剂', color: 'blue' },
                        'salt': { text: '锂盐', color: 'green' },
                        'additive': { text: '添加剂', color: 'orange' }
                      };
                      const config = typeMap[type] || { text: type, color: 'default' };
                      return <Tag color={config.color}>{config.text}</Tag>;
                    }
                  },
                  {
                    title: '名称',
                    dataIndex: 'name',
                    key: 'name'
                  },
                  {
                    title: '化学式',
                    dataIndex: 'chemical_formula',
                    key: 'chemical_formula'
                  },
                  {
                    title: '浓度',
                    key: 'concentration',
                    render: (record: any) => {
                      if (record.concentration && record.unit) {
                        return `${record.concentration} ${record.unit}`;
                      }
                      return '-';
                    }
                  },
                  {
                    title: '来源',
                    dataIndex: 'source',
                    key: 'source',
                    width: 100,
                    render: (source: string) => {
                      const sourceMap: Record<string, { text: string; color: string }> = {
                        'predicted': { text: '预测', color: 'blue' },
                        'optimized': { text: '优化', color: 'green' },
                        'literature': { text: '文献', color: 'orange' }
                      };
                      const config = sourceMap[source] || { text: source, color: 'default' };
                      return <Tag color={config.color}>{config.text}</Tag>;
                    }
                  }
                ]}
              />
            </TabPane>
            {selectedFormula.predicted_properties && (
              <TabPane tab="预测性质" key="properties">
                <Descriptions bordered column={1}>
                  {Object.entries(selectedFormula.predicted_properties).map(([key, value]) => (
                    <Descriptions.Item key={key} label={key}>
                      {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              </TabPane>
            )}
          </Tabs>
        )}
      </Modal>
    </div>
  );
};

export default FormulaListPage;