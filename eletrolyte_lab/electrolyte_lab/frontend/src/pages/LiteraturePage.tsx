import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Input,
  Select,
  Space,
  Tag,
  Modal,
  Descriptions,
  message,
  Row,
  Col,
  Statistic,
  Tabs,
  Badge,
  Typography,
  Alert,
  Spin
} from 'antd';
import {
  SearchOutlined,
  FileTextOutlined,
  BarChartOutlined,
  DatabaseOutlined,
  UploadOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import axios from 'axios';

const { Title, Paragraph, Text } = Typography;
const { TabPane } = Tabs;
const { Option } = Select;
const { TextArea } = Input;

interface Literature {
  id: string;
  title: string;
  authors: string;
  journal: string;
  publication_year: number;
  doi: string;
  keywords: string[];
  abstract: string;
  extraction_confidence: number;
  relevance_score: number;
  processed: boolean;
  processing_status: string;
  extracted_formulas?: string[];
  extracted_molecules?: any[];
}

interface Stats {
  total_literature: number;
  processed_literature: number;
  confidence_distribution: {
    high: number;
    medium: number;
    low: number;
  };
  component_distribution: {
    solvent: number;
    salt: number;
    additive: number;
  };
}

const LiteraturePage: React.FC = () => {
  const [literature, setLiterature] = useState<Literature[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedLiterature, setSelectedLiterature] = useState<Literature | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [componentFilter, setComponentFilter] = useState<string>('');
  const [stats, setStats] = useState<Stats | null>(null);
  const [activeTab, setActiveTab] = useState('database');
  const [searchInput, setSearchInput] = useState('');
  const [showSicPDF, setShowSicPDF] = useState(false);
  const [sicPDFData, setSicPDFData] = useState<any[]>([]);

  // 文献表格列定义
  const columns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      width: 400,
      render: (text: string, record: Literature) => (
        <div>
          <Text strong>{text}</Text>
          <br />
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {record.authors}
          </Text>
        </div>
      ),
    },
    {
      title: '期刊',
      dataIndex: 'journal',
      key: 'journal',
      width: 150,
      render: (text: string, record: Literature) => (
        <div>
          <Text>{text}</Text>
          <br />
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {record.publication_year}
          </Text>
        </div>
      ),
    },
    {
      title: '关键词',
      dataIndex: 'keywords',
      key: 'keywords',
      width: 200,
      render: (text: string, record: Literature) => (
        <div>
          <Text>{text}</Text>
          <br />
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {record.publication_year}
          </Text>
        </div>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      fixed: 'right' as const,
      width: 100,
      render: (_: any, record: Literature) => (
        <Button
          type="link"
          size="small"
          onClick={() => showLiteratureDetail(record)}
          icon={<FileTextOutlined />}
        >
          详情
        </Button>
      ),
    },
  ];

  // 显示文献详情
  const showLiteratureDetail = (record: Literature) => {
    setSelectedLiterature(record);
    setDetailModalVisible(true);
  };

  // 获取文献列表
  const fetchLiterature = async (useLocalStorageData = true) => {
    setLoading(true);

    // 优先从localStorage读取AI设计员保存的文献数据
    if (useLocalStorageData) {
      try {
        const savedData = localStorage.getItem('ai_designer_literature_data');
        const savedTimestamp = localStorage.getItem('ai_designer_literature_timestamp');

        if (savedData) {
          console.log('从localStorage读取文献数据');
          const parsedData = JSON.parse(savedData);

          if (savedTimestamp) {
            const timestamp = new Date(savedTimestamp);
            const now = new Date();
            const hoursDiff = (now.getTime() - timestamp.getTime()) / (1000 * 60 * 60);

            // 如果数据不超过24小时,使用localStorage的数据
            if (hoursDiff < 24) {
              setLiterature(parsedData);
              message.success(`使用AI设计员确认参数时匹配的文献数据 (${Math.round(hoursDiff)}小时前)`);
              setLoading(false);
              return;
            } else {
              console.log('localStorage数据超过24小时,将调用API获取新数据');
            }
          }
        }
      } catch (error) {
        console.warn('从localStorage读取文献数据失败:', error);
        // 继续调用API
      }
    }

    // 调用后端API获取文献数据
    try {
      const response = await axios.get('/api/ai_designer/literature', {
        params: {
          page: 1,
          per_page: 50,
          keywords: searchText,
          component_type: componentFilter,
        },
      });

      if (response.data.success) {
        setLiterature(response.data.data.literature || []);
      } else {
        // 临时模拟数据
        const mockData: Literature[] = [
          {
            id: '1',
            title: 'High-Performance Electrolytes for Lithium-Ion Batteries: Recent Advances',
            authors: 'Zhang, L.; Wang, Y.; Chen, J.',
            journal: 'Advanced Energy Materials',
            publication_year: 2024,
            doi: '10.1002/aenm.202401234',
            keywords: ['lithium-ion battery', 'electrolyte', 'high-performance'],
            abstract: 'This review summarizes recent advances in electrolyte design...',
            extraction_confidence: 0.92,
            relevance_score: 0.95,
            processed: true,
            processing_status: 'completed',
            extracted_formulas: ['EC:EMC (3:7)', 'LiPF6 1.0M'],
            extracted_molecules: []
          },
          {
            id: '2',
            title: 'Novel Fluorinated Electrolyte Additives for High-Voltage Cathodes',
            authors: 'Li, S.; Yang, K.; Brown, M.',
            journal: 'Journal of Power Sources',
            publication_year: 2023,
            doi: '10.1016/j.jpowsour.2023.233456',
            keywords: ['electrolyte additive', 'high-voltage', 'cathode'],
            abstract: 'We report the development of new fluorinated electrolyte additives...',
            extraction_confidence: 0.87,
            relevance_score: 0.88,
            processed: true,
            processing_status: 'completed',
            extracted_formulas: ['FEC:TFEC (1:1)', 'LiFSI 1.0M'],
            extracted_molecules: []
          }
        ];
        setLiterature(mockData);
      }
    } catch (error) {
      console.error('获取文献数据失败:', error);
      // 使用模拟数据作为fallback
      const mockData: Literature[] = [
        {
          id: '1',
          title: 'High-Performance Electrolytes for Lithium-Ion Batteries: Recent Advances',
          authors: 'Zhang, L.; Wang, Y.; Chen, J.',
          journal: 'Advanced Energy Materials',
          publication_year: 2024,
          doi: '10.1002/aenm.202401234',
          keywords: ['lithium-ion battery', 'electrolyte', 'high-performance'],
          abstract: 'This review summarizes recent advances in electrolyte design for high-performance lithium-ion batteries.',
          extraction_confidence: 0.92,
          relevance_score: 0.95,
          processed: true,
          processing_status: 'completed',
          extracted_formulas: ['EC:EMC (3:7)', 'LiPF6 1.0M'],
          extracted_molecules: []
        }
      ];
      setLiterature(mockData);
      message.info('使用模拟数据展示');
    } finally {
      setLoading(false);
    }
  };

  // 搜索文献
  const handleSearch = async () => {
    setSearchText(searchInput);
    await fetchLiterature(false); // 搜索时不使用localStorage数据
  };

  // 使用默认数据(清除localStorage并调用API)
  const handleUseDefaultData = async () => {
    try {
      localStorage.removeItem('ai_designer_literature_data');
      localStorage.removeItem('ai_designer_literature_timestamp');
      message.info('已切换到默认数据源');
      await fetchLiterature(false); // 不使用localStorage数据
    } catch (error) {
      console.error('切换数据源失败:', error);
      message.error('切换数据源失败');
    }
  };

  // 处理文献
  const processLiterature = async () => {
    setLoading(true);
    try {
      const response = await axios.post('/api/ai_designer/process-literature', {
        key_parameters: {
          system_type: { value: '锂离子电池' },
          target_energy: { value: '300 Wh/kg' },
          power_density: { value: '1000 W/kg' }
        },
        batch_size: 5
      });

      if (response.data.success) {
        message.success(`文献处理完成：成功处理 ${response.data.results.successful} 篇文献`);
        await fetchLiterature();
      } else {
        message.error('文献处理失败');
      }
    } catch (error) {
      console.error('处理文献失败:', error);
      message.error('文献处理失败，使用模拟数据');
      // 生成一些模拟结果
      setLiterature(prev => [...prev, {
        id: Date.now().toString(),
        title: 'Processed Literature: ' + new Date().toLocaleString(),
        authors: 'AI System',
        journal: 'Processed Journal',
        publication_year: new Date().getFullYear(),
        doi: '10.1016/processed.' + Date.now(),
        keywords: ['processed', 'electrolyte', 'ai-generated'],
        abstract: 'This is a simulated processed literature entry.',
        extraction_confidence: 0.85,
        relevance_score: 0.80,
        processed: true,
        processing_status: 'completed',
        extracted_formulas: ['AI Generated Formula'],
        extracted_molecules: []
      }]);
    } finally {
      setLoading(false);
    }
  };

  // 获取统计数据（使用模拟数据）
  const fetchStats = async () => {
    // 使用模拟统计数据
    setStats({
      total_literature: literature.length,
      processed_literature: literature.filter(l => l.processed).length,
      confidence_distribution: {
        high: literature.filter(l => l.extraction_confidence > 0.8).length,
        medium: literature.filter(l => l.extraction_confidence > 0.6 && l.extraction_confidence <= 0.8).length,
        low: literature.filter(l => l.extraction_confidence <= 0.6).length,
      },
      component_distribution: {
        solvent: 15,
        salt: 8,
        additive: 12
      }
    });
  };

  useEffect(() => {
    fetchLiterature();
  }, [searchText, componentFilter]);

  useEffect(() => {
    fetchStats();
  }, [literature]);

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      <div style={{ marginBottom: '24px' }}>
        <Title level={2}>
          <DatabaseOutlined /> 文献数据库
        </Title>
        <Paragraph type="secondary">
          智能文献挖掘系统 - 从科研文献中自动提取电解液配方和分子信息
        </Paragraph>
      </div>

      {/* 统计卡片 */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: '24px' }}>
          <Col span={8}>
            <Card>
              <Statistic
                title="总文献数"
                value={stats.total_literature}
                prefix={<DatabaseOutlined />}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="已处理文献"
                value={stats.processed_literature}
                prefix={<FileTextOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="高置信度文献"
                value={stats.confidence_distribution.high}
                prefix={<BarChartOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 主要内容区域 */}
      <Card>
         {/* 搜索和筛选 */}
        <div style={{ marginBottom: '16px' }}>
          <Row gutter={16}>
            <Col span={8}>
              <Input
                placeholder="搜索文献标题、作者、关键词..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onPressEnter={handleSearch}
                prefix={<SearchOutlined />}
              />
            </Col>
            <Col span={5}>
              <Select
                placeholder="组件类型筛选"
                value={componentFilter}
                onChange={setComponentFilter}
                style={{ width: '100%' }}
                allowClear
              >
                <Option value="solvent">溶剂</Option>
                <Option value="salt">盐类</Option>
                <Option value="additive">添加剂</Option>
              </Select>
            </Col>
            <Col span={7}>
              <Button
                type="primary"
                icon={<SearchOutlined />}
                onClick={handleSearch}
              >
                搜索
              </Button>
            </Col>
           
            <Col span={4}>
              <Button
                type="primary"
                icon={<UploadOutlined />}
                onClick={processLiterature}
                loading={loading}
              >
                处理文献
              </Button>
            </Col>
          </Row>
        </div>
        {/* 文献表格 */}
        <Table
          columns={columns}
          dataSource={literature}
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* 文献详情模态框 */}
      <Modal
        title={
          <div>
            <FileTextOutlined style={{ marginRight: 8 }} />
            文献详情
          </div>
        }
        visible={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={800}
      >
        {selectedLiterature && (
          <div>
            <Descriptions title="基本信息" column={1} bordered>
              <Descriptions.Item label="标题">
                {selectedLiterature.title}
              </Descriptions.Item>
              <Descriptions.Item label="作者">
                {selectedLiterature.authors}
              </Descriptions.Item>
              <Descriptions.Item label="期刊">
                {selectedLiterature.journal} ({selectedLiterature.publication_year})
              </Descriptions.Item>
              <Descriptions.Item label="DOI">
                <a href={`https://doi.org/${selectedLiterature.doi}`} target="_blank" rel="noopener noreferrer">
                  {selectedLiterature.doi}
                </a>
              </Descriptions.Item>
              <Descriptions.Item label="关键词">
                <div>
                  <Tag color="blue" style={{ margin: '2px' }}>
                    {selectedLiterature.keywords}
                  </Tag>
                </div>
              </Descriptions.Item>
            </Descriptions>

            {selectedLiterature.extracted_formulas && selectedLiterature.extracted_formulas.length > 0 && (
              <div style={{ marginTop: '16px' }}>
                <Title level={5}>提取的配方</Title>
                <div>
                  {selectedLiterature.extracted_formulas.map((formula, index) => (
                    <Tag key={index} color="green" style={{ margin: '4px', fontSize: '14px', padding: '4px 8px' }}>
                      {formula}
                    </Tag>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default LiteraturePage;