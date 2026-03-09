import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Input,
  Select,
  Tag,
  Space,
  message,
  Progress,
  Tooltip,
  Modal,
  Row,
  Col,
  Statistic,
  Tabs,
  Badge,
  Collapse,
  Descriptions
} from 'antd';
import {
  SearchOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  ReloadOutlined,
  ExperimentOutlined,
  DownloadOutlined,
  EyeOutlined,
  TagOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { literatureApi } from '../services/api';

const { Search } = Input;
const { Option } = Select;
const { Panel } = Collapse;
const { TabPane } = Tabs;

interface Literature {
  id: number;
  title: string;
  authors: string;
  journal: string;
  publication_year: number;
  doi: string;
  abstract?: string;
  keywords?: string[];
  processed: boolean;
  processing_status: string;
  extraction_confidence: number;
  relevance_score: number;
  created_at: string;
  formula_count?: number;
}

interface Formula {
  id: number;
  literature_id: number;
  name: string;
  chemical_formula: string;
  description: string;
  system_type: string;
  application_scenario: string;
  generation_method: string;
  components: any;
  predicted_properties: any;
  performance_metrics: any;
  extraction_confidence: number;
  molecules?: Molecule[];
}

interface Molecule {
  id: number;
  formula_id: number;
  smiles: string;
  inchi: string;
  molecular_name: string;
  component_type: string;
  properties: any;
  prediction_confidence: number;
  is_synthesized: boolean;
  synthesis_difficulty: string;
  created_at: string;
}

interface LiteratureStats {
  total_literature: number;
  processed_literature: number;
  unprocessed_literature: number;
  confidence_distribution: {
    high: number;
    medium: number;
    low: number;
  };
  unique_journals: number;
  total_formulas: number;
  total_molecules: number;
  by_status: {
    completed: number;
    pending: number;
  };
}

interface TextMiningResultsProps {
  // 从父组件传入的搜索参数
  searchKeywords?: string;
  onResultSelect?: (literature: Literature) => void;
}

const TextMiningResults: React.FC<TextMiningResultsProps> = ({
  searchKeywords = '',
  onResultSelect
}) => {
  const [literature, setLiterature] = useState<Literature[]>([]);
  const [stats, setStats] = useState<LiteratureStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedLiterature, setSelectedLiterature] = useState<Literature | null>(null);
  const [literatureModalVisible, setLiteratureModalVisible] = useState(false);
  const [formulasModalVisible, setFormulasModalVisible] = useState(false);
  const [selectedFormulas, setSelectedFormulas] = useState<Formula[]>([]);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0
  });

  // 筛选条件
  const [filters, setFilters] = useState({
    status: '',
    min_confidence: 0.0,
    component_type: '',
    keywords: searchKeywords
  });

  useEffect(() => {
    loadLiterature();
    loadStats();
  }, [pagination.current, pagination.pageSize, filters]);

  // 加载文献列表
  const loadLiterature = async () => {
    setLoading(true);
    try {
      const response = await literatureApi.getLiterature({
        page: pagination.current,
        per_page: pagination.pageSize,
        status: filters.status,
        min_confidence: filters.min_confidence,
        keywords: filters.keywords,
        component_type: filters.component_type
      });

      if (response.success) {
        setLiterature(response.data?.literature || []);
        setPagination(prev => ({
          ...prev,
          total: response.data?.total || 0
        }));
      } else {
        message.error('加载文献列表失败');
      }
    } catch (error) {
      console.error('加载文献列表错误:', error);
      message.error('加载文献列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 加载统计信息
  const loadStats = async () => {
    try {
      const response = await literatureApi.getLiteratureStats();
      if (response.success) {
        setStats(response.data?.statistics as LiteratureStats || null);
      }
    } catch (error) {
      console.error('加载统计信息错误:', error);
    }
  };

  // 处理文献搜索
  const handleSearch = async (keywords: string) => {
    if (!keywords.trim()) {
      message.warning('请输入搜索关键词');
      return;
    }

    setLoading(true);
    try {
      const response = await literatureApi.searchLiterature({
        query: keywords,
        component_type: filters.component_type,
        min_confidence: filters.min_confidence,
        limit: pagination.pageSize
      });

      if (response.success) {
        setLiterature(response.data?.results || []);
        setPagination(prev => ({
          ...prev,
          total: response.data?.total_found || 0,
          current: 1
        }));
        message.success(`搜索到 ${response.data?.total_found || 0} 篇相关文献`);
      } else {
        message.error('文献搜索失败');
      }
    } catch (error) {
      console.error('文献搜索错误:', error);
      message.error('文献搜索失败');
    } finally {
      setLoading(false);
    }
  };

  // 查看文献详情
  const handleViewLiterature = async (record: Literature) => {
    try {
      const response = await literatureApi.getLiteratureDetail(record.id);
      if (response.success) {
        setSelectedLiterature(response.data?.literature);
        setSelectedFormulas(response.data?.formulas || []);
        setLiteratureModalVisible(true);
      } else {
        message.error('获取文献详情失败');
      }
    } catch (error) {
      console.error('获取文献详情错误:', error);
      message.error('获取文献详情失败');
    }
  };

  // 查看配方详情
  const handleViewFormulas = async (literatureId: number) => {
    try {
      const response = await literatureApi.getLiteratureFormulas(literatureId);
      if (response.success) {
        setSelectedFormulas(response.data?.formulas || []);
        setFormulasModalVisible(true);
      } else {
        message.error('获取配方详情失败');
      }
    } catch (error) {
      console.error('获取配方详情错误:', error);
      message.error('获取配方详情失败');
    }
  };

  // 查看分子详情
  const handleViewMolecules = async (formulaId: number) => {
    try {
      const response = await literatureApi.getFormulaMolecules(formulaId);
      if (response.success) {
        Modal.info({
          title: '分子详情',
          width: 800,
          content: (
            <div>
              <p>共找到 {response.data?.molecules?.length || 0} 个分子</p>
              <Table
                columns={[
                  {
                    title: '分子名称',
                    dataIndex: 'molecular_name',
                    key: 'molecular_name',
                    width: 150
                  },
                  {
                    title: '类型',
                    dataIndex: 'component_type',
                    key: 'component_type',
                    width: 100,
                    render: (type) => (
                      <Tag color={type === 'solvent' ? 'blue' : type === 'salt' ? 'green' : 'orange'}>
                        {type}
                      </Tag>
                    )
                  },
                  {
                    title: 'SMILES',
                    dataIndex: 'smiles',
                    key: 'smiles',
                    width: 200,
                    ellipsis: true
                  },
                  {
                    title: '分子量',
                    dataIndex: ['properties', 'molecular_weight'],
                    key: 'molecular_weight',
                    width: 100
                  },
                  {
                    title: '置信度',
                    dataIndex: 'prediction_confidence',
                    key: 'prediction_confidence',
                    width: 100,
                    render: (confidence) => (
                      <Progress
                        percent={Math.round(confidence * 100)}
                        size="small"
                      />
                    )
                  },
                  {
                    title: '合成难度',
                    dataIndex: 'synthesis_difficulty',
                    key: 'synthesis_difficulty',
                    width: 100,
                    render: (difficulty) => (
                      <Tag color={
                        difficulty === 'easy' ? 'green' :
                        difficulty === 'medium' ? 'blue' : 'red'
                      }>
                        {difficulty}
                      </Tag>
                    )
                  }
                ]}
                dataSource={response.data?.molecules || []}
                rowKey="id"
                pagination={false}
                size="small"
              />
            </div>
          )
        });
      } else {
        message.error('获取分子详情失败');
      }
    } catch (error) {
      console.error('获取分子详情错误:', error);
      message.error('获取分子详情失败');
    }
  };

  // 状态颜色映射
  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'orange',
      processing: 'blue',
      completed: 'green',
      failed: 'red'
    };
    return colors[status] || 'default';
  };

  // 置信度颜色映射
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'green';
    if (confidence >= 0.5) return 'orange';
    return 'red';
  };

  // 文献列表表格列定义
  const literatureColumns: ColumnsType<Literature> = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      width: 300,
      ellipsis: true,
      render: (text, record) => (
        <Tooltip title={text}>
          <Button
            type="link"
            onClick={() => {
              handleViewLiterature(record);
              if (onResultSelect) {
                onResultSelect(record);
              }
            }}
          >
            {text}
          </Button>
        </Tooltip>
      )
    },
    {
      title: '作者',
      dataIndex: 'authors',
      key: 'authors',
      width: 200,
      ellipsis: true
    },
    {
      title: '期刊',
      dataIndex: 'journal',
      key: 'journal',
      width: 150,
      ellipsis: true
    },
    {
      title: '年份',
      dataIndex: 'publication_year',
      key: 'publication_year',
      width: 80,
      sorter: true
    },
    {
      title: '处理状态',
      dataIndex: 'processing_status',
      key: 'processing_status',
      width: 100,
      render: (status) => (
        <Tag color={getStatusColor(status)}>
          {status.toUpperCase()}
        </Tag>
      )
    },
    {
      title: '提取置信度',
      dataIndex: 'extraction_confidence',
      key: 'extraction_confidence',
      width: 120,
      render: (confidence) => (
        <Progress
          percent={Math.round(confidence * 100)}
          size="small"
          status={confidence >= 0.5 ? 'success' : 'exception'}
        />
      ),
      sorter: true
    },
    {
      title: '配方数量',
      dataIndex: 'formula_count',
      key: 'formula_count',
      width: 100,
      render: (count) => (
        <Badge count={count || 0} showZero color="#52c41a" />
      )
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewLiterature(record)}
          >
            详情
          </Button>
          <Button
            size="small"
            type="primary"
            icon={<ExperimentOutlined />}
            onClick={() => handleViewFormulas(record.id)}
            disabled={!record.processed}
          >
            查看配方
          </Button>
        </Space>
      )
    }
  ];

  // 配方列表表格列定义
  const formulaColumns: ColumnsType<Formula> = [
    {
      title: '配方名称',
      dataIndex: 'name',
      key: 'name',
      width: 200
    },
    {
      title: '化学式',
      dataIndex: 'chemical_formula',
      key: 'chemical_formula',
      width: 150
    },
    {
      title: '系统类型',
      dataIndex: 'system_type',
      key: 'system_type',
      width: 120,
      render: (type) => <Tag color="blue">{type}</Tag>
    },
    {
      title: '应用场景',
      dataIndex: 'application_scenario',
      key: 'application_scenario',
      width: 120
    },
    {
      title: '置信度',
      dataIndex: 'extraction_confidence',
      key: 'extraction_confidence',
      width: 100,
      render: (confidence) => (
        <Progress
          percent={Math.round(confidence * 100)}
          size="small"
        />
      )
    },
    {
      title: '分子数量',
      key: 'molecule_count',
      width: 100,
      render: (_, record) => (
        <Badge count={record.molecules?.length || 0} showZero color="#1890ff" />
      )
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Button
          size="small"
          icon={<FileTextOutlined />}
          onClick={() => handleViewMolecules(record.id)}
        >
          查看分子
        </Button>
      )
    }
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Row gutter={16} justify="space-between" align="middle">
            <Col>
              <h2>
                <DatabaseOutlined style={{ marginRight: 8, color: '#1890ff' }} />
                文本挖掘结果
                {searchKeywords && (
                  <Tag color="blue" style={{ marginLeft: 8 }}>
                    关键词: {searchKeywords}
                  </Tag>
                )}
              </h2>
            </Col>
            <Col>
              <Space>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={() => {
                    loadLiterature();
                    loadStats();
                  }}
                  loading={loading}
                >
                  刷新
                </Button>
              </Space>
            </Col>
          </Row>
        </div>

        {/* 搜索和筛选区域 */}
        <div style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={8}>
              <Search
                placeholder="搜索文献标题、摘要或内容"
                value={filters.keywords}
                onChange={(e) => setFilters(prev => ({ ...prev, keywords: e.target.value }))}
                onSearch={handleSearch}
                enterButton
              />
            </Col>
            <Col span={4}>
              <Select
                style={{ width: '100%' }}
                value={filters.component_type}
                onChange={(value) => setFilters(prev => ({ ...prev, component_type: value }))}
                placeholder="组件类型"
                allowClear
              >
                <Option value="solvent">溶剂</Option>
                <Option value="salt">盐</Option>
                <Option value="additive">添加剂</Option>
              </Select>
            </Col>
            <Col span={4}>
              <Select
                style={{ width: '100%' }}
                value={filters.status}
                onChange={(value) => setFilters(prev => ({ ...prev, status: value }))}
                placeholder="处理状态"
                allowClear
              >
                <Option value="pending">待处理</Option>
                <Option value="processing">处理中</Option>
                <Option value="completed">已完成</Option>
                <Option value="failed">失败</Option>
              </Select>
            </Col>
            <Col span={4}>
              <Select
                style={{ width: '100%' }}
                value={filters.min_confidence}
                onChange={(value) => setFilters(prev => ({ ...prev, min_confidence: value }))}
                placeholder="最小置信度"
              >
                <Option value={0.0}>全部</Option>
                <Option value={0.3}>30%</Option>
                <Option value={0.5}>50%</Option>
                <Option value={0.8}>80%</Option>
              </Select>
            </Col>
            <Col span={4}>
              <Button
                type="primary"
                icon={<SearchOutlined />}
                onClick={() => handleSearch(filters.keywords || '')}
                loading={loading}
              >
                搜索
              </Button>
            </Col>
          </Row>
        </div>

        {/* 统计信息 */}
        {stats && (
          <div style={{ marginBottom: 16 }}>
            <Row gutter={[16, 16]}>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="总文献数"
                    value={stats.total_literature}
                    prefix={<DatabaseOutlined />}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="已处理文献"
                    value={stats.processed_literature}
                    valueStyle={{ color: '#3f8600' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="提取配方数"
                    value={stats.total_formulas}
                    prefix={<ExperimentOutlined />}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="分子总数"
                    value={stats.total_molecules}
                    prefix={<ExperimentOutlined />}
                  />
                </Card>
              </Col>
            </Row>
          </div>
        )}

        {/* 文献列表 */}
        <Table
          columns={literatureColumns}
          dataSource={literature}
          rowKey="id"
          loading={loading}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`,
            onChange: (page, pageSize) => {
              setPagination(prev => ({ ...prev, current: page, pageSize: pageSize || 20 }));
            }
          }}
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* 文献详情模态框 */}
      <Modal
        title="文献详情"
        visible={literatureModalVisible}
        onCancel={() => setLiteratureModalVisible(false)}
        footer={null}
        width={800}
      >
        {selectedLiterature && (
          <Tabs defaultActiveKey="1">
            <TabPane tab="基本信息" key="1">
              <Descriptions bordered column={2}>
                <Descriptions.Item label="标题" span={2}>
                  {selectedLiterature.title}
                </Descriptions.Item>
                <Descriptions.Item label="作者" span={2}>
                  {selectedLiterature.authors}
                </Descriptions.Item>
                <Descriptions.Item label="期刊">
                  {selectedLiterature.journal}
                </Descriptions.Item>
                <Descriptions.Item label="年份">
                  {selectedLiterature.publication_year}
                </Descriptions.Item>
                <Descriptions.Item label="DOI" span={2}>
                  <a href={selectedLiterature.doi} target="_blank" rel="noopener noreferrer">
                    {selectedLiterature.doi}
                  </a>
                </Descriptions.Item>
                <Descriptions.Item label="处理状态">
                  <Tag color={getStatusColor(selectedLiterature.processing_status)}>
                    {selectedLiterature.processing_status.toUpperCase()}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="提取置信度">
                  <Progress
                    percent={Math.round(selectedLiterature.extraction_confidence * 100)}
                    size="small"
                  />
                </Descriptions.Item>
                <Descriptions.Item label="相关性评分" span={2}>
                  <Tag color={getConfidenceColor(selectedLiterature.relevance_score)}>
                    {(selectedLiterature.relevance_score * 100).toFixed(1)}%
                  </Tag>
                </Descriptions.Item>
                {selectedLiterature.abstract && (
                  <Descriptions.Item label="摘要" span={2}>
                    <div style={{ maxHeight: 200, overflowY: 'auto' }}>
                      {selectedLiterature.abstract}
                    </div>
                  </Descriptions.Item>
                )}
                {selectedLiterature.keywords && selectedLiterature.keywords.length > 0 && (
                  <Descriptions.Item label="关键词" span={2}>
                    <Space wrap>
                      {selectedLiterature.keywords.map((keyword, index) => (
                        <Tag key={index} color="blue">
                          {keyword}
                        </Tag>
                      ))}
                    </Space>
                  </Descriptions.Item>
                )}
              </Descriptions>
            </TabPane>
            <TabPane tab={`提取配方 (${selectedFormulas.length})`} key="2">
              <Table
                columns={formulaColumns}
                dataSource={selectedFormulas}
                rowKey="id"
                pagination={false}
                size="small"
                scroll={{ x: 800 }}
              />
            </TabPane>
          </Tabs>
        )}
      </Modal>

      {/* 配方列表模态框 */}
      <Modal
        title="提取的配方"
        visible={formulasModalVisible}
        onCancel={() => setFormulasModalVisible(false)}
        footer={null}
        width={1000}
      >
        <Table
          columns={formulaColumns}
          dataSource={selectedFormulas}
          rowKey="id"
          pagination={false}
          size="small"
          scroll={{ x: 800 }}
        />
      </Modal>
    </div>
  );
};

export default TextMiningResults;