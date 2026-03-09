import React, { useState } from 'react';
import {
  Card,
  Steps,
  Form,
  Input,
  Button,
  Row,
  Col,
  Table,
  Tag,
  Badge,
  Alert,
  Space,
  Typography,
  Progress,
  Spin,
  Statistic,
  Rate,
  Select,
  InputNumber,
  message,
  Empty,
  Modal,
  Tooltip,
  Tabs,
  List,
  Descriptions
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { Link } from 'react-router-dom';

// AIDesignerPage - AI设计员界面
import {
  ExperimentOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  PlayCircleOutlined,
  InfoCircleOutlined,
  LoadingOutlined,
  FileTextOutlined,
  DatabaseOutlined,
  ArrowRightOutlined
} from '@ant-design/icons';
import { aiDesignerApi, molecularApi, literatureApi } from '../services/api';
import {
  ParsedParameters,
  FormulaDataset,
  PredictedData,
  Formula
} from '../types';
import LiteraturePage from './LiteraturePage';
import Prediction from './AIDesigner/Prediction';
import RecipeGeneration from './AIDesigner/RecipeGeneration';
const { Title, Paragraph, Text } = Typography;
const { Step } = Steps;
const { TextArea } = Input;
const { TabPane } = Tabs;


// 安全的JSON解析函数
const safeJSONParse = <T = any>(str: string, fallback: T): T => {
  try {
    if (!str || typeof str !== 'string') {
      return fallback;
    }
    
    // 处理可能的UTF-8 BOM标记
    let cleanStr = str.trim();
    if (cleanStr.startsWith('﻿')) {
      cleanStr = cleanStr.slice(1);
    }

    // 尝试找到JSON内容的开始位置
    const jsonStart = cleanStr.indexOf('{');
    const jsonArrayStart = cleanStr.indexOf('[');

    let jsonContent = cleanStr;
    if (jsonStart !== -1 && (jsonArrayStart === -1 || jsonStart < jsonArrayStart)) {
      // 找到对象的开始，确保这是JSON的开始
      jsonContent = cleanStr.substring(jsonStart);
    } else if (jsonArrayStart !== -1) {
      // 找到数组的开始
      jsonContent = cleanStr.substring(jsonArrayStart);
    }

    // 尝试解析JSON
    return JSON.parse(jsonContent);
  } catch (error) {
    console.error('JSON解析失败，使用fallback数据:', error, '原始数据:', str);
    return fallback;
  }
};

const AIDesignerPage: React.FC = () => {
  // 输入语义验证函数
  const validateInputSemantic = (userInput: string): { isValid: boolean; reason?: string } => {
    const input = userInput.trim();

    // 检查输入长度
    if (input.length < 3) {
      return { isValid: false, reason: "输入过短，请提供更详细的需求描述" };
    }

    // 检查是否为无意义的重复字符
    if (/(.)\1{3,}/.test(input.toLowerCase())) {
      return { isValid: false, reason: "输入包含无意义的重复字符，请提供具体的需求描述" };
    }

    // 检查是否只包含单一字符重复
    const uniqueChars = new Set(input.toLowerCase().replace(/\s/g, ''));
    if (uniqueChars.size < 3) {
      return { isValid: false, reason: "输入内容过于简单，请描述具体的电池需求" };
    }

    // 检查是否包含有效的电池相关关键词
    const validKeywords = [
      // 体系类型
      "正极", "负极", "电解液", "全电池", "阴极", "阳极", "电池",
      // 材料类型
      "ncm", "nca", "lfp", "lco", "三元", "高镍", "钴酸锂", "锰酸锂", "磷酸铁锂",
      "石墨", "硅", "硬碳", "软碳", "导电剂", "粘结剂",
      // 应用场景
      "动力", "储能", "3c", "手机", "汽车", "电动车", "新能源", "电站", "电网",
      // 性能指标
      "能量密度", "功率密度", "循环", "寿命", "安全", "温度", "成本", "容量",
      // 数值单位
      "wh", "w", "°c", "次", "cycle", "mah", "ah", "v", "kv"
    ];

    const hasValidKeyword = validKeywords.some(keyword =>
      input.toLowerCase().includes(keyword)
    );

    if (!hasValidKeyword) {
      return {
        isValid: false,
        reason: "未能识别有效的电池相关关键词，请描述具体的电池性能需求、材料类型或应用场景"
      };
    }

    // 检查是否为纯数字或无意义字符串
    if (/^\d+$/.test(input)) {
      return { isValid: false, reason: "请输入描述性的需求，而不是纯数字" };
    }

    return { isValid: true };
  };

  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [parsedParameters, setParsedParameters] = useState<ParsedParameters | null>(null);
  const [confirmedParameters, setConfirmedParameters] = useState<Record<string, any> | null>(null);
  const [confirmedParametersList, setConfirmedParametersList] = useState<any[] | null>(null); // 列表格式，用于后端接口
  const [editableParameters, setEditableParameters] = useState<ParsedParameters | null>(null);
  const [formulaDataset, setFormulaDataset] = useState(null);
  const [predictedData, setPredictedData] = useState<PredictedData | null>(null);
  const [generatedFormula, setGeneratedFormula] = useState<Formula | null>(null);
  const [miningProgress, setMiningProgress] = useState(0);
  const [miningStatus, setMiningStatus] = useState('');
  const [predictionProgress, setPredictionProgress] = useState(0);
  const [generatedMolecules, setGeneratedMolecules] = useState<any[]>([]); 
  const [recipeItems, setRecipeItems] = useState<any[]>([]); 
  const [literatureData, setLiteratureData] = useState<any[]>([]);
  const [selectedLiterature, setSelectedLiterature] = useState<any>(null);
  const [selectedMolecule, setSelectedMolecule] = useState<any>(null);
  // 保存参数确认步骤返回的文献匹配结果，供数据挖掘步骤使用
  const [confirmedLiteratureResults, setConfirmedLiteratureResults] = useState<any[]>([]);
  // BM25搜索结果相关状态
  const [parsingProgress, setParsingProgress] = useState({
    currentStep: 0,
    steps: [
      { title: '需求解析', description: '解析用户自然语言需求', completed: false },
      { title: '参数提取', description: '提取电池性能参数', completed: false },
      { title: '材料识别', description: '识别正负极材料信息', completed: false },
      { title: '性能需求分析', description: '分析具体性能指标要求', completed: false },
      { title: '结果整理', description: '整理解析结果', completed: false }
    ]
  });
  const [isParsing, setIsParsing] = useState(false);
  // 步骤历史回顾功能相关状态
  const [stepHistory, setStepHistory] = useState<Record<number, any>>({});
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [reviewingStep, setReviewingStep] = useState<number | null>(null);
  const [userInput, setUserInput] = useState<string>('');
  const [form] = Form.useForm();

  // 步骤点击处理函数
  const handleStepClick = (step: number) => {
    // 只允许回顾已经完成的步骤
    if (stepHistory[step] && step < currentStep) {
      setReviewingStep(step);
      setShowReviewModal(true);
    }
  };
  // 关闭回顾模态框
  const handleCloseReviewModal = () => {
    setShowReviewModal(false);
    setReviewingStep(null);
  };
  // 渲染回顾内容
  const renderReviewContent = () => {
    if (reviewingStep === null || !stepHistory[reviewingStep]) {
      return <Empty description="暂无历史数据" />;
    }
    const stepData = stepHistory[reviewingStep];
    switch (reviewingStep) {
      case 0: // 需求输入
        return (
          <div>
            <Title level={4}>需求输入记录</Title>
            <Paragraph>
              <Text strong>输入时间：</Text>
              {new Date(stepData.timestamp).toLocaleString()}
            </Paragraph>
            <Paragraph>
              <Text strong>需求描述：</Text>
            </Paragraph>
            <Card style={{ marginTop: 16, backgroundColor: '#f5f5f5' }}>
              <Paragraph style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}>
                {stepData.data.input}
              </Paragraph>
            </Card>
          </div>
        );
      case 1: // 参数确认
        return (
          <div>
            <Title level={4}>参数解析结果</Title>
            <Paragraph>
              <Text strong>解析时间：</Text>
              {new Date(stepData.timestamp).toLocaleString()}
            </Paragraph>
            {stepData.data.parameters && (
              <div style={{ marginTop: 16 }}>
                {renderStructuredParameterTable(stepData.data.parameters)}
              </div>
            )}

            {/* 显示生成的基础配方案例 */}
            {stepData.data.formulas && stepData.data.formulas.length > 0 && (
              <div style={{ marginTop: 24 }}>
                <Title level={5}>生成的基础配方案例</Title>
                <Table
                  dataSource={stepData.data.formulas}
                  rowKey="id"
                  pagination={{ pageSize: 3, showSizeChanger: false }}
                  size="small"
                  scroll={{ x: 800 }}
                  columns={[
                    {
                      title: '配方编号',
                      dataIndex: 'id',
                      key: 'id',
                      width: 100,
                      render: (text) => <Text code>{text}</Text>
                    },
                    {
                      title: '配方名称',
                      dataIndex: 'name',
                      key: 'name',
                      width: 150,
                      render: (text) => <Text strong>{text}</Text>
                    },
                    {
                      title: '溶剂组成',
                      key: 'solvents',
                      width: 200,
                      render: (_, record: any) => (
                        <div>
                          {record.components
                            .filter((c: any) => c.component_type === 'solvent')
                            .map((c: any, idx: number) => (
                              <Tag key={idx} color="blue" style={{ margin: '2px' }}>
                                {c.name} {c.concentration}%
                              </Tag>
                            ))}
                        </div>
                      )
                    },
                    {
                      title: '锂盐',
                      key: 'salt',
                      width: 100,
                      render: (_, record: any) => {
                        const salt = record.components.find((c: any) => c.component_type === 'salt');
                        return salt ? <Tag color="green">{salt.name} {salt.concentration}%</Tag> : '-';
                      }
                    },
                    {
                      title: '添加剂',
                      key: 'additives',
                      width: 180,
                      render: (_, record: any) => (
                        <div>
                          {record.components
                            .filter((c: any) => c.component_type === 'additive')
                            .map((c: any, idx: number) => (
                              <Tag key={idx} color="orange" style={{ margin: '2px' }}>
                                {c.name} {c.concentration}%
                              </Tag>
                            ))}
                        </div>
                      )
                    },
                    {
                      title: '预测能量密度',
                      dataIndex: ['predicted_performance', 'energy_density'],
                      key: 'energy',
                      width: 100,
                      render: (value) => `${value} Wh/kg`
                    },
                    {
                      title: '安全评分',
                      dataIndex: ['predicted_performance', 'safety_score'],
                      key: 'safety',
                      width: 80,
                      render: (value) => {
                        const safetyLevel = Math.round(value * 5);
                        return (
                          <div style={{ textAlign: 'center' }}>
                            <div style={{
                              fontSize: '12px',
                              fontWeight: 'bold',
                              color: safetyLevel >= 4 ? '#52c41a' : safetyLevel >= 3 ? '#faad14' : '#ff4d4f'
                            }}>
                              {safetyLevel}/5
                            </div>
                          </div>
                        );
                      }
                    },
                    {
                      title: '实验批次',
                      dataIndex: ['experimental_data', 'batch_number'],
                      key: 'batch',
                      width: 100,
                      render: (text) => <Text code>{text}</Text>
                    }
                  ]}
                />
              </div>
            )}
          </div>
        );

      case 2: // 数据挖掘
        return (
          <div>
            <Title level={4}>数据挖掘结果</Title>
            <Paragraph>
              <Text strong>挖掘时间：</Text>
              {new Date(stepData.timestamp).toLocaleString()}
            </Paragraph>

            {stepData.data.dataset && (
              <div style={{ marginTop: 16 }}>
                {/* 算法执行状态 */}
                {stepData.data.dataset.metadata && (
                  <Card title="算法执行状态" size="small" style={{ marginBottom: 16 }}>
                    <Row gutter={16}>
                      <Col span={8}>
                        <div>
                          <Text strong>文献匹配算法：</Text>
                          {stepData.data.dataset.metadata.literature_match_success ? (
                            <Tag color="success">BM25搜索成功</Tag>
                          ) : (
                            <Tag color="warning">使用模拟数据</Tag>
                          )}
                        </div>
                        <div style={{ marginTop: 4 }}>
                          <Text type="secondary">处理方法：</Text>
                          <Text code>{stepData.data.dataset.metadata.processing_method}</Text>
                        </div>
                      </Col>
                      <Col span={8}>
                        <div>
                          <Text strong>文本挖掘算法：</Text>
                          {stepData.data.dataset.metadata.text_mining_success ? (
                            <Tag color="success">ChemMind成功</Tag>
                          ) : (
                            <Tag color="warning">使用模拟数据</Tag>
                          )}
                        </div>
                        <div style={{ marginTop: 4 }}>
                          <Text type="secondary">挖掘状态：</Text>
                          {stepData.data.dataset.metadata.text_mining_success ? (
                            <Text type="success">完成</Text>
                          ) : (
                            <Text type="warning">失败/备用</Text>
                          )}
                        </div>
                      </Col>
                      <Col span={8}>
                        <div>
                          <Text strong>总体状态：</Text>
                          {stepData.data.dataset.metadata.literature_match_success && stepData.data.dataset.metadata.text_mining_success ? (
                            <Tag color="success">全部算法执行成功</Tag>
                          ) : stepData.data.dataset.metadata.literature_match_success || stepData.data.dataset.metadata.text_mining_success ? (
                            <Tag color="warning">部分算法执行成功</Tag>
                          ) : (
                            <Tag color="error">全部使用备用数据</Tag>
                          )}
                        </div>
                        {stepData.data.dataset.metadata.literature_error && (
                          <div style={{ marginTop: 4 }}>
                            <Text type="secondary" title={stepData.data.dataset.metadata.literature_error}>
                              文献匹配错误：{stepData.data.dataset.metadata.literature_error.length > 30 ?
                                stepData.data.dataset.metadata.literature_error.substring(0, 30) + '...' :
                                stepData.data.dataset.metadata.literature_error}
                            </Text>
                          </div>
                        )}
                        {stepData.data.dataset.metadata.text_mining_error && (
                          <div style={{ marginTop: 4 }}>
                            <Text type="secondary" title={stepData.data.dataset.metadata.text_mining_error}>
                              文本挖掘错误：{stepData.data.dataset.metadata.text_mining_error.length > 30 ?
                                stepData.data.dataset.metadata.text_mining_error.substring(0, 30) + '...' :
                                stepData.data.dataset.metadata.text_mining_error}
                            </Text>
                          </div>
                        )}
                      </Col>
                    </Row>
                  </Card>
                )}

                {/* 文献匹配和文本挖掘结果统计 */}
                <Row gutter={16} style={{ marginBottom: 24 }}>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title="匹配文献数量"
                        value={stepData.data.dataset.literature_results?.length || 0}
                        suffix="篇"
                        valueStyle={{ color: '#1890ff' }}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title="挖掘分子数量"
                        value={stepData.data.dataset.text_mining_results?.molecules?.length || 0}
                        suffix="个"
                        valueStyle={{ color: '#52c41a' }}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title="原始配方数量"
                        value={stepData.data.dataset.original_formulas?.length || 0}
                        suffix="个"
                        valueStyle={{ color: '#722ed1' }}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title="扩增配方数量"
                        value={stepData.data.dataset.augmented_formulas?.length || 0}
                        suffix="个"
                        valueStyle={{ color: '#fa8c16' }}
                      />
                    </Card>
                  </Col>
                </Row>

                {/* 文献匹配结果展示 */}
                {stepData.data.dataset.literature_results && stepData.data.dataset.literature_results.length > 0 && (
                  <Card
                    title={
                      <span>
                        <FileTextOutlined /> 文献匹配结果 ({stepData.data.dataset.metadata?.literature_match_success ? 'BM25算法' : '模拟数据'})
                      </span>
                    }
                    size="small"
                    style={{ marginBottom: 16 }}
                    extra={
                      stepData.data.dataset.literature_results?.length > 5 && (
                        <Button type="link" size="small">
                          查看全部 {stepData.data.dataset.literature_results.length} 篇
                        </Button>
                      )
                    }
                  >
                    <Table
                      dataSource={stepData.data.dataset.literature_results.slice(0, 5)} // 只显示前5篇
                      rowKey="id"
                      pagination={false}
                      size="small"
                      scroll={{ x: 800 }}
                      expandedRowRender={(record: any) => (
                        <div style={{ margin: 0, padding: '8px 12px', background: '#fafafa' }}>
                          <p><Text strong>作者：</Text>{record.authors || '未知'}</p>
                          <p><Text strong>DOI：</Text>{record.doi ? (
                            <a href={`https://doi.org/${record.doi}`} target="_blank" rel="noopener noreferrer">
                              {record.doi}
                            </a>
                          ) : '无DOI'}</p>
                          {record.abstract && (
                            <div>
                              <Text strong>摘要：</Text>
                              <Paragraph ellipsis={{ rows: 3, expandable: true }}>
                                {record.abstract}
                              </Paragraph>
                            </div>
                          )}
                          {record.keywords && record.keywords.length > 0 && (
                            <div>
                              <Text strong>关键词：</Text>
                               <p>
                                {record.keywords}
                              </p>
                              
                            </div>
                          )}
                        </div>
                      )}
                      columns={[
                        {
                          title: '标题',
                          dataIndex: 'title',
                          key: 'title',
                          ellipsis: true,
                          width: '35%',
                          render: (title) => <Text strong>{title}</Text>
                        },
                        {
                          title: '期刊',
                          dataIndex: 'journal',
                          key: 'journal',
                          width: '15%',
                          ellipsis: true,
                        },
                        {
                          title: '年份',
                          dataIndex: 'publication_year',
                          key: 'publication_year',
                          width: '8%',
                          sorter: (a, b) => a.publication_year - b.publication_year,
                        },
                        {
                          title: '相关性评分',
                          dataIndex: 'relevance_score',
                          key: 'relevance_score',
                          width: '12%',
                          sorter: (a, b) => (a.relevance_score || 0) - (b.relevance_score || 0),
                          render: (score) => (
                            <div>
                              <Rate disabled count={5} defaultValue={Math.min(5, Math.round((score || 0) * 5))} />
                              <div style={{ fontSize: '12px', color: '#666' }}>
                                {(score || 0).toFixed(3)}
                              </div>
                            </div>
                          ),
                        },
                        {
                          title: '置信度',
                          dataIndex: 'extraction_confidence',
                          key: 'extraction_confidence',
                          width: '10%',
                          sorter: (a, b) => (a.extraction_confidence || 0) - (b.extraction_confidence || 0),
                          render: (confidence) => (
                            <Badge
                              count={`${Math.round((confidence || 0) * 100)}%`}
                              style={{
                                backgroundColor: (confidence || 0) > 0.8 ? '#52c41a' :
                                               (confidence || 0) > 0.6 ? '#fa8c16' : '#f5222d'
                              }}
                            />
                          ),
                        },
                        {
                          title: '处理状态',
                          dataIndex: 'processing_status',
                          key: 'processing_status',
                          width: '10%',
                          render: (status) => (
                            <Tag color={status === 'completed' ? 'success' : 'processing'}>
                              {status === 'completed' ? '已完成' : '处理中'}
                            </Tag>
                          ),
                        },
                      ]}
                    />
                    {stepData.data.dataset.literature_results.length > 5 && (
                      <div style={{ textAlign: 'center', marginTop: 12 }}>
                        <Text type="secondary">
                          还有 {stepData.data.dataset.literature_results.length - 5} 篇文献未显示
                        </Text>
                      </div>
                    )}
                  </Card>
                )}

                {/* 文本挖掘结果展示 */}
                {stepData.data.dataset.text_mining_results?.molecules && stepData.data.dataset.text_mining_results.molecules.length > 0 && (
                  <Card
                    title={
                      <span>
                        <DatabaseOutlined /> 文本挖掘结果 ({stepData.data.dataset.metadata?.text_mining_success ? 'ChemMind算法' : '模拟数据'})
                      </span>
                    }
                    size="small"
                    style={{ marginBottom: 16 }}
                    extra={
                      <Space>
                        <Tag color={stepData.data.dataset.metadata?.text_mining_success ? 'success' : 'warning'}>
                          {stepData.data.dataset.metadata?.text_mining_success ? '真实挖掘' : '模拟数据'}
                        </Tag>
                        {stepData.data.dataset.text_mining_results.molecules.length > 6 && (
                          <Button type="link" size="small">
                            查看全部 {stepData.data.dataset.text_mining_results.molecules.length} 个分子
                          </Button>
                        )}
                      </Space>
                    }
                  >
                    {/* 按组分类型分组展示 */}
                    <Tabs defaultActiveKey="all" size="small">
                      <TabPane tab="全部" key="all">
                        <Row gutter={[12, 12]}>
                          {stepData.data.dataset.text_mining_results.molecules.slice(0, 6).map((molecule, index) => (
                            <Col span={8} key={molecule.id || index}>
                              <Card
                                size="small"
                                hoverable
                                className="molecule-card"
                                actions={[
                                  molecule.smiles_notation && (
                                    <Button
                                      type="link"
                                      size="small"
                                      icon={<InfoCircleOutlined />}
                                      onClick={() => {
                                        Modal.info({
                                          title: `${molecule.name} - 详细信息`,
                                          content: (
                                            <div>
                                              <p><Text strong>化学式：</Text>{molecule.chemical_formula}</p>
                                              <p><Text strong>SMILES：</Text><Text code copyable>{molecule.smiles_notation}</Text></p>
                                              <p><Text strong>组分类型：</Text>{molecule.component_type}</p>
                                              <p><Text strong>生成方法：</Text>{molecule.generation_method}</p>
                                              {molecule.molecular_properties?.molecular_weight && (
                                                <p><Text strong>分子量：</Text>{molecule.molecular_properties.molecular_weight}</p>
                                              )}
                                              {molecule.molecular_properties?.estimated_polarity && (
                                                <p><Text strong>极性：</Text>{molecule.molecular_properties.estimated_polarity}</p>
                                              )}
                                              <p><Text strong>来源文献：</Text>{molecule.source_literature}</p>
                                            </div>
                                          )
                                        })
                                      }}
                                    >
                                      详情
                                    </Button>
                                  )
                                ].filter(Boolean)}
                              >
                                <Card.Meta
                                  avatar={
                                    <div style={{
                                      width: 40,
                                      height: 40,
                                      borderRadius: '50%',
                                      background: molecule.component_type === 'solvent' ? '#1890ff' :
                                                  molecule.component_type === 'salt' ? '#52c41a' : '#fa8c16',
                                      display: 'flex',
                                      alignItems: 'center',
                                      justifyContent: 'center',
                                      color: 'white',
                                      fontSize: '12px',
                                      fontWeight: 'bold'
                                    }}>
                                      {molecule.component_type === 'solvent' ? '溶剂' :
                                       molecule.component_type === 'salt' ? '盐' : '添加'}
                                    </div>
                                  }
                                  title={
                                    <div>
                                      <Text strong ellipsis style={{ maxWidth: '150px' }}>
                                        {molecule.name}
                                      </Text>
                                      <div style={{ marginTop: 4 }}>
                                        <Tag
                                          color={molecule.component_type === 'solvent' ? 'blue' :
                                                 molecule.component_type === 'salt' ? 'green' : 'orange'}
                                        >
                                          {molecule.component_type === 'solvent' ? '溶剂' :
                                           molecule.component_type === 'salt' ? '锂盐' : '添加剂'}
                                        </Tag>
                                      </div>
                                    </div>
                                  }
                                  description={
                                    <div style={{ fontSize: '12px', color: '#666' }}>
                                      <div>
                                        <Text strong>化学式：</Text>
                                        <Text code>{molecule.chemical_formula}</Text>
                                      </div>
                                      {molecule.molecular_properties?.molecular_weight && (
                                        <div>
                                          <Text strong>分子量：</Text>
                                          {molecule.molecular_properties.molecular_weight}
                                        </div>
                                      )}
                                      <div style={{ marginTop: 4 }}>
                                        <Text type="secondary" ellipsis>
                                          来源：{molecule.source_literature?.substring(0, 20) || '文本挖掘'}...
                                        </Text>
                                      </div>
                                    </div>
                                  }
                                />
                              </Card>
                            </Col>
                          ))}
                        </Row>
                      </TabPane>

                      {/* 按类型分组 */}
                      {['solvent', 'salt', 'additive'].map(type => {
                        const typeMolecules = stepData.data.dataset.text_mining_results.molecules.filter(m => m.component_type === type);
                        if (typeMolecules.length === 0) return null;

                        return (
                          <TabPane
                            tab={`${type === 'solvent' ? '溶剂' : type === 'salt' ? '锂盐' : '添加剂'} (${typeMolecules.length})`}
                            key={type}
                          >
                            <Row gutter={[12, 12]}>
                              {typeMolecules.slice(0, 6).map((molecule, index) => (
                                <Col span={8} key={molecule.id || index}>
                                  <Card size="small" hoverable>
                                    <Card.Meta
                                      title={<span>{molecule.name}</span>}
                                      description={
                                        <div style={{ fontSize: '12px' }}>
                                          <p><Text strong>化学式:</Text> <Text code>{molecule.chemical_formula}</Text></p>
                                          {molecule.molecular_properties?.molecular_weight && (
                                            <p><Text strong>分子量:</Text> {molecule.molecular_properties.molecular_weight}</p>
                                          )}
                                          {molecule.source_literature && (
                                            <p><Text strong>来源:</Text> <Text ellipsis>{molecule.source_literature}</Text></p>
                                          )}
                                        </div>
                                      }
                                    />
                                  </Card>
                                </Col>
                              ))}
                            </Row>
                          </TabPane>
                        );
                      })}
                    </Tabs>

                    {stepData.data.dataset.text_mining_results.molecules.length > 6 && (
                      <div style={{ textAlign: 'center', marginTop: 12 }}>
                        <Text type="secondary">
                          还有 {stepData.data.dataset.text_mining_results.molecules.length - 6} 个分子未显示
                        </Text>
                      </div>
                    )}

                    {/* 推荐结果展示 */}
                    {stepData.data.dataset.text_mining_results.recommendations && (
                      <div style={{ marginTop: 16 }}>
                        <Title level={5}>AI推荐分析</Title>
                        <Card size="small" style={{ background: '#f8f9fa' }}>
                          <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: '14px' }}>
                            {stepData.data.dataset.text_mining_results.recommendations}
                          </pre>
                        </Card>
                      </div>
                    )}
                  </Card>
                )}

                {/* 如果没有文本挖掘结果，显示提示 */}
                {(!stepData.data.dataset.text_mining_results?.molecules || stepData.data.dataset.text_mining_results.molecules.length === 0) && (
                  <Card size="small" style={{ marginBottom: 16, textAlign: 'center' }}>
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description={
                        <span>
                          文本挖掘结果为空
                          {stepData.data.dataset.metadata?.text_mining_error && (
                            <div style={{ marginTop: 8, fontSize: '12px', color: '#999' }}>
                              错误信息：{stepData.data.dataset.metadata.text_mining_error}
                            </div>
                          )}
                        </span>
                      }
                    />
                  </Card>
                )}

                {/* 原始统计信息保留 */}
                <Row gutter={16}>
                  <Col span={8}>
                    <Card>
                      <Statistic
                        title="扩增率"
                        value={stepData.data.dataset.original_formulas?.length > 0 ?
                          Math.round((stepData.data.dataset.augmented_formulas.length / stepData.data.dataset.original_formulas.length) * 100) : 0}
                        suffix="%"
                        valueStyle={{ color: '#722ed1' }}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card>
                      <Statistic
                        title="处理方法"
                        value={stepData.data.dataset.metadata?.processing_method === 'real_algorithm' ? '真实算法' : '模拟数据'}
                        valueStyle={{ color: stepData.data.dataset.metadata?.processing_method === 'real_algorithm' ? '#52c41a' : '#fa8c16' }}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card>
                      <Statistic
                        title="算法状态"
                        value="正常"
                        valueStyle={{ color: '#52c41a' }}
                      />
                    </Card>
                  </Col>
                </Row>
              </div>
            )}
          </div>
        );

      case 3: // 性质预测
        return (
          <div>
            <Title level={4}>性质预测结果</Title>
            <Paragraph>
              <Text strong>预测时间：</Text>
              {new Date(stepData.timestamp).toLocaleString()}
            </Paragraph>

            {/* 预测概览 */}
            <Card size="small" style={{ marginTop: 16 }}>
              <Row gutter={8}>
                <Col span={6}>
                  <Statistic
                    title="总预测数"
                    value={stepData.data.total_predictions || 0}
                    suffix="个"
                    valueStyle={{ fontSize: '14px', color: '#1890ff' }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="筛选数量"
                    value={stepData.data.selected_count || 0}
                    suffix="个"
                    valueStyle={{ fontSize: '14px', color: '#52c41a' }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="筛选率"
                    value={stepData.data.total_predictions > 0 ?
                      Math.round((stepData.data.selected_count / stepData.data.total_predictions) * 100) : 0}
                    suffix="%"
                    valueStyle={{ fontSize: '14px', color: '#fa8c16' }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="模型"
                    value={stepData.data.model_info?.model_type?.slice(0, 8) || 'UniMol'}
                    valueStyle={{ fontSize: '12px' }}
                  />
                </Col>
              </Row>
            </Card>

            {/* 优质分子预览 */}
            {stepData.data.predicted_formulas && stepData.data.predicted_formulas.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <Title level={5}>筛选出的优质分子（前3名）</Title>
                <Table
                  dataSource={stepData.data.predicted_formulas.slice(0, 3)}
                  rowKey="formula_index"
                  pagination={false}
                  size="small"
                  columns={[
                    {
                      title: '排名',
                      dataIndex: 'formula_index',
                      key: 'rank',
                      width: 50,
                      render: (text) => (
                        <Badge count={text} style={{ backgroundColor: '#52c41a' }} />
                      )
                    },
                    {
                      title: '配方',
                      dataIndex: ['formula', 'name'],
                      key: 'name',
                      ellipsis: true
                    },
                    {
                      title: '评分',
                      dataIndex: 'overall_score',
                      key: 'score',
                      width: 60,
                      render: (score) => (
                        <Text strong style={{ color: score > 0.85 ? '#52c41a' : '#1890ff' }}>
                          {Math.round(score * 100)}
                        </Text>
                      )
                    },
                    {
                      title: '能量密度',
                      dataIndex: ['system_properties', 'energy_density'],
                      key: 'energy',
                      width: 70,
                      render: (value) => `${Math.round(value)}`
                    }
                  ]}
                />
                {stepData.data.predicted_formulas.length > 3 && (
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    还有 {stepData.data.predicted_formulas.length - 3} 个分子...
                  </Text>
                )}
              </div>
            )}
          </div>
        );

      case 4: // 配方生成
        return (
          <div>
            <Title level={4}>最终配方生成</Title>
            <Paragraph>
              <Text strong>生成时间：</Text>
              {new Date(stepData.timestamp).toLocaleString()}
            </Paragraph>
            {stepData.data.formula && (
              <div style={{ marginTop: 16 }}>
                <Alert
                  message="配方生成成功"
                  description={`已生成最优配方，包含 ${stepData.data.formula.components?.length || 0} 个组分。`}
                  type="success"
                  showIcon
                />
                {renderFormulaComponents()}
              </div>
            )}
          </div>
        );

      default:
        return <Empty description="暂无历史数据" />;
    }
  };
  // 步骤定义
  const steps = [
    {
      title: '需求输入',
      description: '输入自然语言需求',
      icon: <ExperimentOutlined />
    },
    {
      title: '参数确认',
      description: '确认提取的参数',
      icon: <CheckCircleOutlined />
    },
    {
      title: '数据挖掘',
      description: '文献挖掘与数据扩增',
      icon: <ClockCircleOutlined />
    },
    {
      title: '性质预测',
      description: '高通量性质预测',
      icon: <ClockCircleOutlined />
    },
    {
      title: '配方生成',
      description: '生成实验配方',
      icon: <PlayCircleOutlined />
    }
  ];
   //1.需求解析
   //参数是values: { input: string }
  const handleParseRequest = async (values: { input: string }) => {
    const validation = validateInputSemantic(values.input);
    if (!validation.isValid) {
      message.error(validation.reason || '输入内容无效，请描述具体的电池需求');
      return;
    }
  
    //演戏
    setLoading(true);
    setIsParsing(true);
    setParsingProgress(prev => ({
      ...prev,
      currentStep: 0,
      steps: prev.steps.map(step => ({ ...step, completed: false })),
    }));
  
    const backendPromise = aiDesignerApi.parseRequest({ parameters: values });
  
    const steps = [
      { step: 0, delay: 5000 },
      { step: 1, delay: 5000 },
      { step: 2, delay: 5000 },
      { step: 3, delay: 5000 },
      { step: 4, delay: 2000 },
    ];
  
    try {
      // 演戏
      for (const { step, delay } of steps) {
        await new Promise(r => setTimeout(r, delay));
        setParsingProgress(prev => ({
          currentStep: step + 1,
          steps: prev.steps.map((item, idx) => ({
            ...item,
            completed: idx <= step,
          })),
        }));
      }
  
      // 演完拿结果
      const response = await backendPromise;
  
      if (!response.success || !response.data) {
        message.error(response.message || '需求解析失败，请稍后重试');
        return;
      }
  
      const enhancedParsedParameters = response.data;
  
      // 同时设置两个状态变量
      setParsedParameters(enhancedParsedParameters);
      setEditableParameters(structuredClone(enhancedParsedParameters));
  
      setUserInput(values.input);
      setCurrentStep(1);
  
      message.success(
        `需求解析完成！已识别 ${enhancedParsedParameters.basic_info.system_type.label || ''} 类型电池系统`
      );
    } catch (err: any) {
      const status = err?.response?.status;
      const backendMsg = err?.response?.data?.message;
  
      if (err?.code === 'ECONNABORTED') {
        message.warning('后端响应超时，请稍后重试。');
      } else if (!status) {
        message.warning('无法连接到后端服务，请确认后端已启动且端口可访问。');
      } else if (status >= 500) {
        message.error(backendMsg || '后端服务内部错误，请稍后重试。');
      } else {
        message.error(backendMsg || err?.message || '解析失败，请稍后重试。');
      }
    } finally {
      //UI复位
      setLoading(false);
      setIsParsing(false);
    }
  };
  // 2. 确认参数 - 调用后端接口保存参数
  const handleConfirmParameters = async () => {
    console.log('点击了确认参数按钮');

    if (!editableParameters) {
      message.error('没有可确认的参数');
      return;
    }

    try {
      setLoading(true);

      // 辅助函数：根据表格显示逻辑生成范围字符串
      const getRangeDisplay = (paramData: any): string => {
        if (paramData.type === 'select' && paramData.options) {
          return paramData.options.join(', ');
        } else if (paramData.type === 'number' && paramData.min !== undefined && paramData.max !== undefined) {
          return `${paramData.min} - ${paramData.max}`;
        } else if (paramData.type === 'rating') {
          return '1-5 级';
        }
        return '';
      };

      // 构建参数列表，与 renderEditableParameterTable 中的 allParams 逻辑完全一致
      const tableParams: any[] = [];

      // 添加正极材料（如果存在）
      if (editableParameters.basic_info.positive_electrode) {
        const param = editableParameters.basic_info.positive_electrode;
        tableParams.push({
          category: '基本信息',
          param_name: param.label || '正极材料',
          param_value: param.value,
          unit: param.unit || '',
          range: getRangeDisplay(param),
          confidence: param.confidence || 0.0
        });
      }

      // 添加负极材料（如果存在）
      if (editableParameters.basic_info.negative_electrode) {
        const param = editableParameters.basic_info.negative_electrode;
        tableParams.push({
          category: '基本信息',
          param_name: param.label || '负极材料',
          param_value: param.value,
          unit: param.unit || '',
          range: getRangeDisplay(param),
          confidence: param.confidence || 0.0
        });
      }

      // 添加体系类型（仅当没有正负极材料时）
      if (!editableParameters.basic_info.positive_electrode && !editableParameters.basic_info.negative_electrode) {
        const param = editableParameters.basic_info.system_type;
        tableParams.push({
          category: '基本信息',
          param_name: param.label || '体系类型',
          param_value: param.value,
          unit: param.unit || '',
          range: getRangeDisplay(param),
          confidence: param.confidence || 0.0
        });
      }

      // 添加应用场景
      if (editableParameters.basic_info.application_scenario) {
        const param = editableParameters.basic_info.application_scenario;
        tableParams.push({
          category: '基本信息',
          param_name: param.label || '应用场景',
          param_value: param.value,
          unit: param.unit || '',
          range: getRangeDisplay(param),
          confidence: param.confidence || 0.0
        });
      }

      // 添加性能参数（如果存在）
      if (editableParameters.performance_params) {
        Object.keys(editableParameters.performance_params).forEach(key => {
          const param = editableParameters.performance_params[key];
          if (param && param.value !== undefined) {
            tableParams.push({
              category: '性能参数',
              param_name: param.label || key,
              param_value: param.value,
              unit: param.unit || '',
              range: getRangeDisplay(param),
              confidence: param.confidence || 0.0
            });
          }
        });
      }

      console.log('表格参数数据（共', tableParams.length, '条）:', tableParams);

      // 调用后端接口保存参数
      const response = await aiDesignerApi.confirmParameters({ parameters: tableParams });

      // 参数保存成功，继续处理（即使文献匹配失败）
      console.log('参数保存响应:', response);

      // 判断参数是否保存成功（基于后端新的返回逻辑）
      const parametersSaved = response.data !== undefined || response.success !== false;
      if (!parametersSaved) {
        throw new Error(response.error || '确认参数失败');
      }

      // 处理文献匹配结果
      if (response.data && response.data.length > 0) {
        console.log('文献匹配成功，文献数量:', response.data.length);
        console.log('文献数据:', response.data);

        // 设置文献数据用于界面展示
        setLiteratureData(response.data);
        // 保存文献匹配结果供数据挖掘步骤使用
        setConfirmedLiteratureResults(response.data);

        // 保存文献数据到localStorage,供LiteraturePage使用
        try {
          localStorage.setItem('ai_designer_literature_data', JSON.stringify(response.data));
          localStorage.setItem('ai_designer_literature_timestamp', new Date().toISOString());
          console.log('文献数据已保存到localStorage');
        } catch (error) {
          console.warn('保存文献数据到localStorage失败:', error);
        }

        // 设置步骤历史记录，以便在步骤三显示文献数据
        setStepHistory(prev => ({
          ...prev,
          2: {
            type: 'mining',
            title: '数据挖掘',
            timestamp: new Date().toISOString(),
            data: {
              dataset: {
                literature_results: response.data,
                text_mining_results: { molecules: [] },
                original_formulas: [],
                augmented_formulas: [],
                metadata: {
                  total_literature: response.literature_count || response.data.length,
                  total_molecules: 0,
                  processing_method: 'bm25_literature_matching',
                  literature_match_success: response.literature_match_success !== false,
                  text_mining_success: false,
                  literature_error: response.literature_error,
                  processing_details: {
                    bm25_search_used: true,
                    chemmind_used: false,
                    fallback_used: false
                  }
                }
              },
              literature_data: response.data,
              molecules: [],
              success: true,
              processing_method: 'bm25_only'
            }
          }
        }));

        // 显示成功消息
        message.success(`参数确认成功！匹配到 ${response.data.length} 篇相关文献`);
      } else {
        console.warn('文献匹配失败或返回空结果');
        if (response.literature_error) {
          console.error('文献匹配错误:', response.literature_error);
          message.error(`文献匹配失败: ${response.literature_error}`);
        } else {
          message.error('文献匹配失败，未找到相关文献');
        }

        // 清空文献数据，不使用任何模拟数据
        setLiteratureData([]);

        // 设置空的步骤历史记录
        setStepHistory(prev => ({
          ...prev,
          2: {
            type: 'mining',
            title: '数据挖掘',
            timestamp: new Date().toISOString(),
            data: {
              dataset: {
                literature_results: [],
                text_mining_results: { molecules: [] },
                original_formulas: [],
                augmented_formulas: [],
                metadata: {
                  total_literature: 0,
                  total_molecules: 0,
                  processing_method: 'failed',
                  literature_match_success: false,
                  text_mining_success: false,
                  literature_error: response.literature_error || '未知错误',
                  processing_details: {
                    bm25_search_used: true,
                    chemmind_used: false,
                    fallback_used: false
                  }
                }
              },
              literature_data: [],
              molecules: [],
              success: false,
              processing_method: 'failed'
            }
          }
        }));
      }

      // 将 editableParameters 转换为前端使用的格式
      const confirmed = {
        system_type: editableParameters.basic_info?.system_type?.value || editableParameters.basic_info?.system_type?.label || '',
        application_scenario: editableParameters.basic_info?.application_scenario?.value || editableParameters.basic_info?.application_scenario?.label || '',
        performance_requirements: {},
        timestamp: new Date().toISOString()
      };

      // 转换 performance_params 为 performance_requirements
      if (editableParameters.performance_params) {
        Object.entries(editableParameters.performance_params).forEach(([key, param]: [string, any]) => {
          if (param && typeof param === 'object') {
            // 将 key 从 target_energy_density 转为 energy_density
            const formattedKey = key.replace(/^target_/, '');
            confirmed.performance_requirements[formattedKey] = param.value;
          }
        });
      }

      console.log('转换后的确认参数:', confirmed);

      // 设置确认的参数（对象格式，用于前端显示）
      setConfirmedParameters(confirmed);

      // 同时保存列表格式（用于后端数据挖掘接口）
      setConfirmedParametersList(tableParams);

      // 如果没有文献数据提示，显示参数确认成功
      if (!response.literature_results || response.literature_results.length === 0) {
        // 在上面的处理中已经显示过消息了，这里不需要重复
      }

      // 跳转到步骤三
      setCurrentStep(2);

    } catch (error: any) {
      console.error('确认参数时出错:', error);
      message.error(error.message || '确认参数失败，请重试');
    } finally {
      setLoading(false);
    }
  };
  // 更新参数值 - 简化版
  const updateParameterValue = (category: string, paramKey: string, newValue: any) => {
    if (!editableParameters) return;

    const updatedParams = safeJSONParse(JSON.stringify(editableParameters), editableParameters);

    if (category === 'basic_info') {
      if (updatedParams.basic_info[paramKey]) {
        updatedParams.basic_info[paramKey].value = newValue;
      }
    } else if (category === 'performance_params' && updatedParams.performance_params[paramKey]) {
      updatedParams.performance_params[paramKey].value = newValue;
    }

    setEditableParameters(updatedParams);
  };
  // 3. 数据挖掘
  const handleMineData = async () => {
    console.log('=== handleMineData 被调用 ===');
    console.log('confirmedParameters (对象格式):', confirmedParameters);
    console.log('confirmedParametersList (列表格式):', confirmedParametersList);
    console.log('confirmedLiteratureResults:', confirmedLiteratureResults);

    if (!confirmedParametersList) {
      console.error('confirmedParametersList 为空，无法执行数据挖掘');
      message.error('请先完成参数确认步骤');
      return;
    }

    setLoading(true);
    setMiningProgress(0);
    setMiningStatus('开始数据挖掘...');
    setGeneratedMolecules([]);
    setLiteratureData([]);

    try {
      let dataset = null;
      let allMolecules = null; // 保存完整的分子数据（在try块外也能访问）

      // 执行文献挖掘和数据扩增（使用集成的BM25和文本挖掘算法）
      setMiningStatus('正在进行文献挖掘... ...');
      setMiningProgress(25);

      try {
        console.log('准备发送请求到 /api/ai-designer/mine-data');
        console.log('请求体:', {
          parameters: confirmedParameters,
          literature_results: confirmedLiteratureResults
        });

        // 使用封装好的API调用，与confirmParameters保持一致
        const responseData = await aiDesignerApi.mineData({
          parameters: confirmedParameters,
          literature_results: confirmedLiteratureResults
        });

        console.log('数据挖掘API响应:', responseData);

        if (responseData.success ) {
        
          // 保存完整的分子数据供后续使用
          if (responseData.molecules && responseData.molecules.length > 0) {
            allMolecules = responseData.molecules;
          }
         
         
          // 设置完整的分子数据（包含文本挖掘+生成的所有分子）
          if (allMolecules && allMolecules.length > 0) {
            const mappedMolecules = allMolecules.map((item, index) => ({
              id: index,  // 使用更唯一的id
              ...item
            }));
            console.log(mappedMolecules)
            setGeneratedMolecules(mappedMolecules);
            console.log('设置完整分子数据，总数:', allMolecules.length);
          }


          message.success(`数据挖掘完成`);
          setMiningProgress(75);
        } else {
          console.error('数据挖掘响应结构不正确:', responseData);
          throw new Error(responseData.error || '数据挖掘失败');
        }
      } catch (error) {
        console.error('数据挖掘失败:', error);
        message.error('数据挖掘失败，请重试');
        return;
      }

      // 步骤2: 整合BM25和文本挖掘结果

      // 完成数据挖掘流程

      setMiningProgress(100);
      setMiningStatus('数据挖掘完成！');



      // 保存步骤历史记录（关键修复）
      setStepHistory(prev => ({
        ...prev,
        2: {
          type: 'mining',
          title: '数据挖掘',
          timestamp: new Date().toISOString(),
          data: {
            success: true,
          }
        }
      }));


      // 关键修复：确保跳转到步骤三界面显示结果
      setTimeout(() => {
        setCurrentStep(2);
      }, 500);
    } catch (error) {
      console.error('数据挖掘失败:', error);
      message.error('数据挖掘失败，请重试');
    } finally {
      setLoading(false);
      setTimeout(() => {
        setMiningProgress(0);
        setMiningStatus('');
      }, 2000);
    }
  };
  // 4. 性质预测
  const handlePredictProperties = async () => {
    if (!confirmedParameters) {
      message.error('没有确认的参数，请先完成参数确认步骤');
      return;
    }

    if (generatedMolecules.length === 0) {
      message.error('没有可用的分子数据，请先完成分子生成步骤');
      return;
    }

    setLoading(true);
    setPredictionProgress(0);

    let progressInterval: NodeJS.Timeout;
    setCurrentStep(3); // 跳转到步骤4（性质预测结果）
  }
  // 渲染结构化参数表格（只读）
  const renderStructuredParameterTable = (params: ParsedParameters) => {
    // 将所有参数合并为一个数组，匹配后端返回的数据结构
    const allParams = [
      { ...params.basic_info.system_type, category: '基本信息' },
      { ...params.basic_info.application_scenario, category: '基本信息' },
      { ...params.performance_params.target_energy_density, category: '性能参数' },
      { ...params.performance_params.power_density, category: '性能参数' },
      { ...params.performance_params.cycle_life, category: '性能参数' },
      { ...params.performance_params.operating_temperature, category: '性能参数' }
    ];

    // 添加安全性要求参数
    if (params.safety_requirements) {
      Object.keys(params.safety_requirements).forEach(key => {
        allParams.push({
          ...params.safety_requirements[key],
          category: '安全要求'
        });
      });
    }

    // 添加成本约束参数
    if (params.cost_constraints) {
      Object.keys(params.cost_constraints).forEach(key => {
        allParams.push({
          ...params.cost_constraints[key],
          category: '成本约束'
        });
      });
    }

    const columns = [
      {
        title: '类别',
        dataIndex: 'category',
        key: 'category',
        width: 100
      },
      {
        title: '参数名称',
        dataIndex: 'label',
        key: 'label',
        width: 120
      },
      {
        title: '当前值',
        dataIndex: 'value',
        key: 'value',
        render: (value: any, record: any) => {
          if (record.type === 'select') {
            return <Tag color="blue">{value}</Tag>;
          } else if (record.type === 'rating') {
            return <Rate disabled value={value} style={{ fontSize: 14 }} />;
          } else if (record.unit) {
            return <Text strong>{value} {record.unit}</Text>;
          }
          return <Text strong>{value}</Text>;
        }
      },
      {
        title: '范围/选项',
        dataIndex: 'options',
        key: 'options',
        render: (options: string[], record: any) => {
          if (record.type === 'select' && options) {
            return options.join(', ');
          } else if (record.type === 'number' && record.min !== undefined && record.max !== undefined) {
            return `${record.min} - ${record.max}`;
          } else if (record.type === 'rating') {
            return '1-5 级';
          }
          return '-';
        }
      },
      {
        title: '置信度',
        dataIndex: 'confidence',
        key: 'confidence',
        width: 120,
        render: (confidence: number) => {
          return (
            <div>
              <Progress percent={confidence * 100} size="small" showInfo={false} />
              <Text style={{ fontSize: 12, color: '#666' }}>
                {(confidence * 100).toFixed(1)}%
              </Text>
            </div>
          );
        }
      },
      {
        title: '状态',
        dataIndex: 'value',
        key: 'status',
        width: 80,
        render: (value: any, record: any) => {
          if (value === null || value === undefined) {
            return <Tag color="orange">待设置</Tag>;
          }
          return <Tag color="green">已解析</Tag>;
        }
      }
    ];

    return (
      <Table
        columns={columns}
        dataSource={allParams}
        rowKey="key"
        pagination={false}
        size="small"
        scroll={{ x: 600 }}
      />
    );
  };
  // 渲染可编辑参数表格 - 简化版
  const renderEditableParameterTable = (params: ParsedParameters) => {
    // 构建参数数组，优先显示正负极材料
    const allParams = [];

    // 添加正极材料（如果存在）
    if (params.basic_info.positive_electrode) {
      allParams.push({
        ...params.basic_info.positive_electrode,
        category: 'basic_info',
        paramKey: 'positive_electrode',
        key: 'positive_electrode'
      });
    }

    // 添加负极材料（如果存在）
    if (params.basic_info.negative_electrode) {
      allParams.push({
        ...params.basic_info.negative_electrode,
        category: 'basic_info',
        paramKey: 'negative_electrode',
        key: 'negative_electrode'
      });
    }

    // 添加体系类型（用于向后兼容，如果没有正负极则显示）
    if (!params.basic_info.positive_electrode && !params.basic_info.negative_electrode) {
      allParams.push({
        ...params.basic_info.system_type,
        category: 'basic_info',
        paramKey: 'system_type',
        key: 'system_type'
      });
    }

    // 添加应用场景
    allParams.push({
      ...params.basic_info.application_scenario,
      category: 'basic_info',
      paramKey: 'application_scenario',
      key: 'application_scenario'
    });

    // 添加性能参数（如果存在）
    if (params.performance_params) {
      Object.keys(params.performance_params).forEach(key => {
        allParams.push({
          ...params.performance_params[key],
          category: 'performance_params',
          paramKey: key,
          key: `performance_${key}`
        });
      });
    }

    const columns = [
      {
        title: '类别',
        dataIndex: 'category',
        key: 'category',
        width: 100,
        render: (text: string) => {
          const categoryMap: Record<string, string> = {
            'basic_info': '基本信息',
            'performance_params': '性能参数',
            'safety_requirements': '安全要求',
            'cost_constraints': '成本约束'
          };
          return categoryMap[text] || text;
        }
      },
      {
        title: '参数名称',
        dataIndex: 'label',
        key: 'label',
        width: 120,
        render: (label: string, record: any) => {
          // 对于system_type参数，显示动态label（正极或负极）
          if (record.paramKey === 'system_type') {
            return record.value || label || '体系类型';
          }
          return label;
        }
      },
      {
        title: '参数值',
        dataIndex: 'value',
        key: 'value',
        render: (value: any, record: any) => {
          // 辅助函数：安全获取值的显示形式
          const getDisplayValue = (val: any, defaultValue: any = '') => {
            if (val === null || val === undefined) return defaultValue;
            if (typeof val === 'object') return val.value || val.label || defaultValue;
            return val;
          };

          // 对于正负极参数，使用Select组件支持下拉选择和自定义输入
          if (record.paramKey === 'positive_electrode' || record.paramKey === 'negative_electrode') {
            // 预定义选项
            const predefinedOptions = record.paramKey === 'positive_electrode'
              ? ['LFP', 'LCO', 'NMC811', 'NMC523']
              : ['SiC', 'Li', '石墨'];

            return (
              <Select
                value={value || undefined}
                style={{ width: 200 }}
                placeholder={`请选择${record.label}`}
                allowClear
                showSearch
                optionFilterProp="children"
                onChange={(selectedValue) => {
                  if (!editableParameters) return;

                  const updatedParams = safeJSONParse(JSON.stringify(editableParameters), editableParameters);

                  // 更新对应的电极材料值
                  if (record.paramKey === 'positive_electrode') {
                    if (!updatedParams.basic_info.positive_electrode) {
                      updatedParams.basic_info.positive_electrode = {};
                    }
                    updatedParams.basic_info.positive_electrode.value = selectedValue;
                  } else if (record.paramKey === 'negative_electrode') {
                    if (!updatedParams.basic_info.negative_electrode) {
                      updatedParams.basic_info.negative_electrode = {};
                    }
                    updatedParams.basic_info.negative_electrode.value = selectedValue;
                  }

                  setEditableParameters(updatedParams);
                }}
                dropdownRender={(menu) => (
                  <div>
                    {menu}
                    <div style={{ padding: 8, borderTop: '1px solid #eee' }}>
                      <Input
                        placeholder="或输入自定义材料"
                        onPressEnter={(e) => {
                          const customValue = (e.target as HTMLInputElement).value.trim();
                          if (customValue) {
                            if (!editableParameters) return;

                            const updatedParams = safeJSONParse(JSON.stringify(editableParameters), editableParameters);

                            if (record.paramKey === 'positive_electrode') {
                              if (!updatedParams.basic_info.positive_electrode) {
                                updatedParams.basic_info.positive_electrode = {};
                              }
                              updatedParams.basic_info.positive_electrode.value = customValue;
                            } else if (record.paramKey === 'negative_electrode') {
                              if (!updatedParams.basic_info.negative_electrode) {
                                updatedParams.basic_info.negative_electrode = {};
                              }
                              updatedParams.basic_info.negative_electrode.value = customValue;
                            }

                            setEditableParameters(updatedParams);
                          }
                        }}
                      />
                    </div>
                  </div>
                )}
              >
                {predefinedOptions.map(opt => (
                  <Select.Option key={opt} value={opt}>{opt}</Select.Option>
                ))}
              </Select>
            );
          }

          // 其他参数保持原有逻辑
          if (record.type === 'select') {
            return (
              <Select
                value={getDisplayValue(value, '')}
                style={{ width: 120 }}
                onChange={(newValue) => updateParameterValue(record.category, record.paramKey, newValue)}
              >
                {record.options?.map((option: string) => (
                  <Select.Option key={option} value={option}>{option}</Select.Option>
                ))}
              </Select>
            );
          } else if (record.type === 'rating') {
            return (
              <Rate
                value={getDisplayValue(value, 1)}
                style={{ fontSize: 14 }}
                onChange={(newValue) => updateParameterValue(record.category, record.paramKey, newValue)}
              />
            );
          } else if (record.type === 'number') {
            return (
              <InputNumber
                value={getDisplayValue(value, undefined)}
                min={record.min}
                max={record.max}
                style={{ width: 120 }}
                onChange={(newValue) => updateParameterValue(record.category, record.paramKey, newValue)}
              />
            );
          }
          return (
            <Input
              value={getDisplayValue(value, '')}
              style={{ width: 120 }}
              onChange={(e) => updateParameterValue(record.category, record.paramKey, e.target.value)}
            />
          );
        }
      },
      {
        title: '单位',
        dataIndex: 'unit',
        key: 'unit',
        width: 60,
        render: (unit: string) => unit || '-'
      },
      {
        title: '范围/选项',
        dataIndex: 'options',
        key: 'options',
        render: (options: string[], record: any) => {
          if (record.type === 'select' && options) {
            return options.join(', ');
          } else if (record.type === 'number' && record.min !== undefined && record.max !== undefined) {
            return `${record.min} - ${record.max}`;
          } else if (record.type === 'rating') {
            return '1-5 级';
          }
          return '-';
        }
      },
      {
        title: '状态',
        dataIndex: 'value',
        key: 'status',
        width: 80,
        render: (value: any, record: any) => {
          if (value === null || value === undefined) {
            return <Tag color="red">待设置</Tag>;
          }
          return <Tag color="green">已设置</Tag>;
        }
      }
    ];

    return (
      <Table
        columns={columns}
        dataSource={allParams}
        rowKey="key"
        pagination={false}
        size="small"
        scroll={{ x: 800 }}
      />
    );
  };
  // 渲染配方组件
  const renderFormulaComponents = () => {
    if (!generatedFormula) return null;

    const formula = generatedFormula as any; // 类型断言以处理API返回的额外字段
    const components = formula.components?.map((component: any, index: number) => {
      // 处理不同的字段名和结构
      const percentage = component.percentage || component.concentration || 0;
      const unit = component.unit || 'wt%';
      const role = component.role || component.optimization_reason || 'N/A';
      const source = component.source || 'AI优化';

      // 获取分子分类的标签颜色
      const getTypeColor = (type: string) => {
        switch (type) {
          case 'solvent': return 'blue';
          case 'salt': return 'green';
          case 'additive': return 'orange';
          default: return 'default';
        }
      };

      // 获取分子的中文名称
      const getTypeLabel = (type: string) => {
        switch (type) {
          case 'solvent': return '溶剂';
          case 'salt': return '锂盐';
          case 'additive': return '添加剂';
          default: return '其他';
        }
      };

      return {
        key: index,
        type: component.component_type,
        typeLabel: getTypeLabel(component.component_type),
        typeColor: getTypeColor(component.component_type),
        name: component.name || `组分${index + 1}`,
        chemical_formula: component.chemical_formula || 'N/A',
        smiles: component.smiles_notation || 'N/A',
        concentration: `${percentage} ${unit}`,
        concentrationValue: percentage,
        source: source,
        role: role,
        // 显示额外信息（如果有）
        confidence: component.prediction_confidence || component.confidence || 0.9,
        matchScore: component.requirement_match_score || component.match_score || 0.85,
        // 分子性质
        properties: component.properties || {}
      };
    }) || [];

    // 计算配比统计
    const calculateRatioStats = () => {
      const stats = {
        solvents: components.filter(c => c.type === 'solvent'),
        salts: components.filter(c => c.type === 'salt'),
        additives: components.filter(c => c.type === 'additive'),
        totalPercentage: components.reduce((sum, c) => sum + c.concentrationValue, 0)
      };

      return {
        ...stats,
        solventRatio: stats.solvents.reduce((sum, c) => sum + c.concentrationValue, 0),
        saltRatio: stats.salts.reduce((sum, c) => sum + c.concentrationValue, 0),
        additiveRatio: stats.additives.reduce((sum, c) => sum + c.concentrationValue, 0)
      };
    };

    const stats = calculateRatioStats();

    const columns = [
      {
        title: '类型',
        dataIndex: 'typeLabel',
        key: 'type',
        width: 80,
        render: (text: string, record: any) => (
          <Tag color={record.typeColor}>{text}</Tag>
        )
      },
      {
        title: '名称',
        dataIndex: 'name',
        key: 'name',
        render: (text: string, record: any) => (
          <div>
            <Text strong>{text}</Text>
            {record.smiles !== 'N/A' && (
              <div style={{ marginTop: 4 }}>
                <Text code copyable={{ text: record.smiles }} style={{ fontSize: '11px' }}>
                  {record.smiles.length > 20 ? `${record.smiles.substring(0, 20)}...` : record.smiles}
                </Text>
              </div>
            )}
          </div>
        )
      },
      {
        title: '化学式',
        dataIndex: 'chemical_formula',
        key: 'chemical_formula',
        render: (text: string) => <Text code>{text}</Text>
      },
      {
        title: '浓度配比',
        dataIndex: 'concentration',
        key: 'concentration',
        width: 120,
        render: (text: string, record: any) => (
          <div>
            <Progress
              percent={record.concentrationValue}
              size="small"
              status={record.concentrationValue > 0 ? 'normal' : 'exception'}
              format={() => `${record.concentrationValue.toFixed(1)}%`}
            />
            <Text type="secondary" style={{ fontSize: '11px' }}>{text}</Text>
          </div>
        )
      },
      {
        title: '作用',
        dataIndex: 'role',
        key: 'role',
        width: 100
      },
      {
        title: '来源',
        dataIndex: 'source',
        key: 'source',
        width: 80,
        render: (text: string) => <Badge status="processing" text={text} />
      },
      {
        title: '置信度',
        dataIndex: 'confidence',
        key: 'confidence',
        width: 100,
        render: (value: number) => (
          <div>
            <Progress
              percent={value * 100}
              size="small"
              status={value > 0.9 ? 'success' : value > 0.8 ? 'normal' : 'exception'}
              format={() => `${(value * 100).toFixed(1)}%`}
            />
          </div>
        )
      }
    ];

    return (
      <div>
        {/* 配比统计卡片 */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="溶剂占比"
                value={stats.solventRatio}
                precision={1}
                suffix="%"
                valueStyle={{ color: '#1890ff' }}
              />
              <div style={{ marginTop: 8 }}>
                <Text type="secondary">共 {stats.solvents.length} 种溶剂</Text>
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="锂盐占比"
                value={stats.saltRatio}
                precision={1}
                suffix="%"
                valueStyle={{ color: '#52c41a' }}
              />
              <div style={{ marginTop: 8 }}>
                <Text type="secondary">共 {stats.salts.length} 种锂盐</Text>
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="添加剂占比"
                value={stats.additiveRatio}
                precision={1}
                suffix="%"
                valueStyle={{ color: '#fa8c16' }}
              />
              <div style={{ marginTop: 8 }}>
                <Text type="secondary">共 {stats.additives.length} 种添加剂</Text>
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="总配比"
                value={stats.totalPercentage}
                precision={1}
                suffix="%"
                valueStyle={{ color: stats.totalPercentage === 100 ? '#722ed1' : '#f5222d' }}
              />
              {/* <div style={{ marginTop: 8 }}>
                <Text type={stats.totalPercentage === 100 ? 'success' : 'danger'}>
                  {stats.totalPercentage === 100 ? '配比完整' : '配比不完整'}
                </Text>
              </div> */}
            </Card>
          </Col>
        </Row>

        {/* 配比饼图 */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={12}>
            <Card size="small" title="配比分布">
              <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Row gutter={[16, 16]}>
                  <Col span={8}>
                    <div style={{ textAlign: 'center' }}>
                      <Progress
                        type="circle"
                        percent={stats.solventRatio}
                        width={80}
                        strokeColor="#1890ff"
                        format={() => `${stats.solventRatio.toFixed(1)}%`}
                      />
                      <div style={{ marginTop: 8 }}>
                        <Text strong>溶剂</Text>
                      </div>
                    </div>
                  </Col>
                  <Col span={8}>
                    <div style={{ textAlign: 'center' }}>
                      <Progress
                        type="circle"
                        percent={stats.saltRatio}
                        width={80}
                        strokeColor="#52c41a"
                        format={() => `${stats.saltRatio.toFixed(1)}%`}
                      />
                      <div style={{ marginTop: 8 }}>
                        <Text strong>锂盐</Text>
                      </div>
                    </div>
                  </Col>
                  <Col span={8}>
                    <div style={{ textAlign: 'center' }}>
                      <Progress
                        type="circle"
                        percent={stats.additiveRatio}
                        width={80}
                        strokeColor="#fa8c16"
                        format={() => `${stats.additiveRatio.toFixed(1)}%`}
                      />
                      <div style={{ marginTop: 8 }}>
                        <Text strong>添加剂</Text>
                      </div>
                    </div>
                  </Col>
                </Row>
              </div>
            </Card>
          </Col>
          <Col span={12}>
            <Card size="small" title="配方特征">
              <div style={{ height: 200 }}>
                <Descriptions size="small" column={1}>
                  <Descriptions.Item label="配方复杂度">
                    <Tag color={components.length <= 3 ? 'green' : components.length <= 5 ? 'orange' : 'red'}>
                      {components.length <= 3 ? '简单' : components.length <= 5 ? '中等' : '复杂'}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="主要溶剂">
                    {stats.solvents[0]?.name || 'N/A'}
                  </Descriptions.Item>
                  <Descriptions.Item label="主要锂盐">
                    {stats.salts[0]?.name || 'N/A'}
                  </Descriptions.Item>
                  <Descriptions.Item label="添加剂类型">
                    {stats.additives.length > 0 ? stats.additives.map(a => a.name).join(', ') : '无'}
                  </Descriptions.Item>
                  <Descriptions.Item label="优化程度">
                    <Rate disabled defaultValue={components.length >= 3 ? 4 : 3} />
                  </Descriptions.Item>
                </Descriptions>
              </div>
            </Card>
          </Col>
        </Row>

        {/* 分子详情表格 */}
        <Table
          columns={columns}
          dataSource={components}
          pagination={false}
          size="small"
          scroll={{ x: true }}
          rowClassName={(record) => {
            switch (record.type) {
              case 'solvent': return 'solvent-row';
              case 'salt': return 'salt-row';
              case 'additive': return 'additive-row';
              default: return '';
            }
          }}
        />

        {/* 分子分类说明 */}
        <Alert
          message="分子分类说明"
          description={
            <div>
              <p><Tag color="blue">溶剂</Tag>：提供电解质溶解和离子传输的介质，影响介电常数和粘度</p>
              <p><Tag color="green">锂盐</Tag>：提供可移动的锂离子，决定电解质的电导率和电化学窗口</p>
              <p><Tag color="orange">添加剂</Tag>：改善SEI膜形成、提高安全性或增强特定性能</p>
            </div>
          }
          type="info"
          showIcon
          style={{ marginTop: 16 }}
        />
      </div>
    );
  };
  return (
    <div>
      <div className="page-header">
        <Title level={2}>AI设计员</Title>
        <Paragraph>
          从自然语言需求到结构化配方，通过智能解析、文献挖掘、性能预测和配方生成，为您提供最优的电池电解液配方。
        </Paragraph>
      </div>

      {/* 进度步骤 */}
      <Card style={{ marginBottom: 24 }}>
        <Steps current={currentStep}>
          {steps.map((step, index) => (
            <Step
              key={index}
              title={
                <span
                  style={{
                    cursor: stepHistory[index] && index < currentStep ? 'pointer' : 'default',
                    color: stepHistory[index] && index < currentStep ? '#1890ff' : 'inherit'
                  }}
                  onClick={() => handleStepClick(index)}
                >
                  {step.title}
                </span>
              }
              description={step.description}
              icon={step.icon}
            />
          ))}
        </Steps>
      </Card>

      {/* 历史记录摘要 */}
      {(currentStep > 0) && (
        <Card style={{ marginBottom: 16, backgroundColor: '#fafafa' }}>
          <Title level={5}>📋 历史记录摘要</Title>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
            {userInput && (
              <div style={{ flex: 1, minWidth: 300 }}>
                <Text strong>📝 原始需求：</Text>
                <div style={{ marginTop: 4, padding: 8, backgroundColor: '#fff', borderRadius: 4, border: '1px solid #d9d9d9' }}>
                  <Text type="secondary">{userInput}</Text>
                </div>
              </div>
            )}

            {/* {parsedParameters && (
              <div style={{ flex: 1, minWidth: 300 }}>
                <Text strong>⚙️ 解析结果：</Text>
                <div style={{ marginTop: 4, padding: 8, backgroundColor: '#fff', borderRadius: 4, border: '1px solid #d9d9d9' }}>
                  <div><Text type="secondary">体系类型：</Text><Tag color="blue">{parsedParameters.basic_info.system_type.label}</Tag></div>
                  <div><Text type="secondary">应用场景：</Text><Tag color="green">{parsedParameters.basic_info.application_scenario.value}</Tag></div>
                </div>
              </div>
            )} */}

            {confirmedParameters && (
              <div style={{ flex: 1, minWidth: 300 }}>
                <Text strong>✅ 确认参数：</Text>
                <div style={{ marginTop: 4, padding: 8, backgroundColor: '#fff', borderRadius: 4, border: '1px solid #d9d9d9' }}>
                  <div><Text type="secondary">体系：</Text><Tag color="blue">{confirmedParameters.system_type}</Tag></div>
                  <div><Text type="secondary">场景：</Text><Tag color="green">{confirmedParameters.application_scenario}</Tag></div>
                  <div><Text type="secondary">能量密度：</Text><Text>{confirmedParameters.performance_requirements.energy_density} Wh/kg</Text></div>
                  <div><Text type="secondary">功率密度：</Text><Text>{confirmedParameters.performance_requirements.power_density} W/kg</Text></div>
                </div>
              </div>
            )}

          
            {predictedData && (
              <div style={{ flex: 1, minWidth: 300 }}>
                <Text strong>🎯 预测结果：</Text>
                <div style={{ marginTop: 4, padding: 8, backgroundColor: '#fff', borderRadius: 4, border: '1px solid #d9d9d9' }}>
                  <div><Text type="secondary">预测总数：</Text><Text strong>{predictedData.total_predictions}</Text></div>
                  <div><Text type="secondary">筛选数量：</Text><Text strong>{predictedData.selected_count}</Text></div>
                  <div><Text type="secondary">模型类型：</Text><Text>{predictedData.model_info?.model_type}</Text></div>
                </div>
              </div>
            )}
          </div>
        </Card>
      )}
      {/* 步骤内容 */}
      <Card>
        {currentStep === 0 && (
          <div>
            <Title level={4}>步骤1: 需求输入</Title>
            <Paragraph>
              请用自然语言描述您的电池性能需求，例如："我需要一个用于电动汽车的高能量密度正极电解液，要求循环寿命长，安全性好"。
            </Paragraph>
            <Form form={form} onFinish={handleParseRequest} layout="vertical">
              <Form.Item
                name="input"
                label="需求描述"
                rules={[{ required: true, message: '请输入需求描述' }]}
              >
                <TextArea
                  rows={4}
                  placeholder="请描述您的电池需求，例如：&#10;• 动力电池，能量密度300Wh/kg，循环寿命2000次&#10;• NCM正极材料，用于电动车，高安全性要求&#10;• 储能电池，LFP体系，长寿命低成本&#10;• 电解液配方，工作温度-20°C到60°C"
                />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} icon={<PlayCircleOutlined />}>
                  开始解析
                </Button>
              </Form.Item>
            </Form>

            <Alert
              message="输入要求"
              description={
                <div>
                  <p>系统会验证输入的语义有效性，请确保包含以下内容之一：</p>
                  <ul style={{ margin: '8px 0', paddingLeft: '20px' }}>
                    <li><strong>电池类型</strong>：正极、负极、电解液、全电池等</li>
                    <li><strong>材料名称</strong>：NCM、LFP、石墨、硅等</li>
                    <li><strong>应用场景</strong>：动力电池、储能、3C等</li>
                    <li><strong>性能指标</strong>：能量密度、循环寿命、安全性等</li>
                  </ul>
                  <p style={{ margin: '8px 0 0 0', color: '#999', fontSize: '12px' }}>
                    注意：无意义字符、过短输入或纯数字将被拒绝
                  </p>
                </div>
              }
              type="info"
              showIcon
              style={{ marginTop: 16 }}
            />

            {/* Parsing Progress Display */}
            {isParsing && (
              <Card
                title={
                  <span>
                    <LoadingOutlined style={{ marginRight: 8 }} />
                    分析提取用户需求
                  </span>
                }
                style={{ marginTop: 16 }}
              >
                <Steps
                  current={parsingProgress.currentStep}
                  size="small"
                  direction="vertical"
                  items={parsingProgress.steps.map((step, index) => ({
                    title: step.title,
                    description: step.description,
                    status: step.completed ? 'finish' :
                            index === parsingProgress.currentStep ? 'process' : 'wait',
                    icon: step.completed ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> :
                           index === parsingProgress.currentStep ? <LoadingOutlined /> : null
                  }))}
                />
                <div style={{ marginTop: 12, textAlign: 'center' }}>
                  <Text type="secondary">
                    {parsingProgress.steps[parsingProgress.currentStep]?.description || '正在处理...'}
                  </Text>
                </div>
              </Card>
            )}
          </div>
        )}

        {currentStep === 1 && (parsedParameters || editableParameters) && (
          <div>
            <Title level={4}>步骤2: 参数确认</Title>
            <Paragraph>
              系统已从您的需求中提取以下参数，请确认是否正确。您可以继续下一步或返回修改。
            </Paragraph>

            <Alert
              message="手动输入支持"
              description="正极和负极材料支持手动输入或修改。如果系统未能正确识别电极材料，您可以直接输入材料名称，如：NCM、LFP、NCA、石墨、硅碳等。"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            {(parsedParameters || editableParameters)?.metadata?.warnings && ((parsedParameters || editableParameters)?.metadata.warnings.length > 0) && (
              <Alert
                message="解析提示"
                description={(parsedParameters || editableParameters).metadata.warnings.join(', ')}
                type="warning"
                style={{ marginBottom: 16 }}
              />
            )}

            <Row gutter={16}>
              <Col span={16}>
                <Card
                  title={
                    <Space>
                      <Text>参数编辑（可直接修改参数值）</Text>
                    </Space>
                  }
                  size="small"
                >
                  {editableParameters && renderEditableParameterTable(editableParameters)}
                </Card>
              </Col>
              <Col span={8}>
                <Card title="解析信息" size="small">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div>
                      <Text strong>原始输入：</Text>
                      <Paragraph style={{ marginTop: 8, fontSize: 12 }}>
                        {(parsedParameters || editableParameters)?.metadata?.original_input || userInput || '无'}
                      </Paragraph>
                    </div>
                    <div>
                      <Text strong>解析时间：</Text>
                      <Text>{(parsedParameters || editableParameters)?.metadata?.parsing_timestamp ? new Date((parsedParameters || editableParameters).metadata.parsing_timestamp).toLocaleString() : new Date().toLocaleString()}</Text>
                    </div>
                    {(parsedParameters || editableParameters)?.metadata?.missing_required && (parsedParameters || editableParameters).metadata.missing_required.length > 0 && (
                      <div>
                        <Text strong type="danger">缺少必需参数：</Text>
                        <div>
                          {(parsedParameters || editableParameters).metadata.missing_required.map((param: string, index: number) => (
                            <Tag key={index} color="orange">{param}</Tag>
                          ))}
                        </div>
                      </div>
                    )}
                  </Space>
                </Card>
              </Col>
            </Row>

            <Space style={{ marginTop: 16 }}>
              <Button onClick={() => setCurrentStep(0)}>返回修改</Button>
              <Button
                type="primary"
                onClick={handleConfirmParameters}
                loading={loading}
              >
                确认参数，继续
              </Button>
            </Space>
          </div>
        )}

        {currentStep === 2 && (
          <div>
            {/* 文献匹配 */}
            <Card
              title={
                <span>
                  <FileTextOutlined style={{ marginRight: 8, color: '#1890ff' }} />
                  文献匹配与管理系统
                </span>
              }
              style={{ marginBottom: 24 }}
            >
              <LiteraturePage />
            </Card>

            {/* 数据挖掘控制按钮 */}
            <Card title="数据挖掘操作" style={{ marginBottom: 24 }}>
              <div style={{ marginBottom: 16 }}>
                {loading ? (
                  <div>
                    <Spin size="large" />
                    <div style={{ marginTop: 16 }}>
                      <Text>{miningStatus}</Text>
                      <Progress
                        percent={miningProgress}
                        status={miningProgress >= 100 ? "success" : "active"}
                        style={{ marginTop: 8 }}
                      />
                    </div>
                  </div>
                ) : (
                  <Alert
                    message="准备数据挖掘"
                    description="点击下方按钮开始执行文献挖掘和数据扩增流程"
                    type="info"
                    showIcon
                  />
                )}
              </div>
            </Card>

            <div style={{ marginTop: 16, textAlign: 'center' }}>
              <Space>
                <Button onClick={() => setCurrentStep(1)}>返回上一步</Button>
                <Button
                  type="primary"
                  size="large"
                  icon={<ArrowRightOutlined />}
                  onClick={handleMineData}
                  loading={loading}
                  disabled={loading}
                >
                  {loading ? '正在挖掘数据...' : '开始数据挖掘'}
                </Button>
              </Space>
            </div>
          {/* 挖掘完成后的结果展示 */}
            {generatedMolecules.length>0&&(
              <>
              <Card
                title={
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                      <DatabaseOutlined style={{ marginRight: 8, color: '#52c41a', fontSize: '18px' }} />
                      <span style={{ fontWeight: 'bold', color: '#52c41a', fontSize: '16px' }}>
                        ✅ 成功生成 {formulaDataset?.total_count || generatedMolecules.length || 0} 个候选分子
                      </span>
                    </div>
                    <div style={{ fontSize: '14px', color: '#666' }}>
                      包含 {formulaDataset?.metadata?.text_mined_molecules || 0} 个文本挖掘分子 + {formulaDataset?.metadata?.generated_molecules || 0} 个生成分子
                    </div>
                  </div>
                }
                style={{ marginTop: 24, border: '2px solid #52c41a' }}
              >
                {/* 分子信息展示 */}
                <Card
                  title={
                    <span>
                      <ExperimentOutlined style={{ marginRight: 8 }} />
                      生成的分子信息
                    </span>
                  }
                  size="small"
                  style={{ marginBottom: 16 }}
                >
                  <Table
                    dataSource={generatedMolecules}
                    rowKey="id"
                    pagination={{
                      pageSize: 10,
                      showSizeChanger: true,
                      showQuickJumper: true,
                      showTotal: (total, range) => `显示 ${range[0]}-${range[1]} 条，共 ${total} 条`
                    }}
                    scroll={{ x: 1400 }}
                    columns={[
                      {
                        title: 'SMILES结构',
                        dataIndex: 'SMILES',
                        key: 'SMILES',
                        width: 200,
                        ellipsis: true,
                        render: (text) => (
                          <Tooltip title={text}>
                            <Text code copyable={{ text }}>
                              {text}
                            </Text>
                          </Tooltip>
                        )
                      },
                      {
                        title: 'CAS',
                        dataIndex: 'CAS',
                        key: 'CAS',
                        width: 120,
                        render: (value) => value  || 'N/A'
                      },
                      {
                        title: 'IUPAC',
                        dataIndex: 'IUPAC',
                        key: 'IUPAC',
                        width: 150,
                         render: (value) => value  || 'N/A'
                      },
                      {
                        title: '俗名',
                        dataIndex: 'common_name',
                        key: 'common_name',
                        width: 120,
                        render: (value) => value  || 'N/A'
                      },
                      {
                        title: '分子式',
                        dataIndex: 'formula',
                        key: 'formula',
                        width: 200,
                        ellipsis: true,
                        render: (text) => (
                          <Tooltip title={text}>
                            <Text>{text || 'N/A'}</Text>
                          </Tooltip>
                        )
                      },
                    
                    ]}
                  />
                </Card>
              </Card>
              <div style={{ marginTop: 16, textAlign: 'center' }}>
                <Button
                  type="primary"
                  size="large"
                  onClick={handlePredictProperties}
                  loading={loading}
                  disabled={generatedMolecules.length === 0}
                >
                  {loading ? '正在预测...' : '进入性质预测'}
                </Button>
              </div>
              </>
            )}          </div>
        )}

        {currentStep === 3 && (
          <Prediction setCurrentStep={setCurrentStep} setStepHistory={setStepHistory} generatedMolecules={generatedMolecules} setRecipeItems={setRecipeItems} />
        )}
         {currentStep === 4 && (
          <RecipeGeneration setCurrentStep={setCurrentStep} setStepHistory={setStepHistory}  recipeItems={recipeItems} />
        )}
      
      </Card>
      {/* 分子详情模态框 */}
      <Modal
        title={
          <span>
            <DatabaseOutlined style={{ marginRight: 8, color: '#52c41a' }} />
            分子详细信息
          </span>
        }
        open={!!selectedMolecule}
        onCancel={() => setSelectedMolecule(null)}
        footer={[
          <Button key="close" onClick={() => setSelectedMolecule(null)}>
            关闭
          </Button>
        ]}
        width={800}
        style={{ top: 20 }}
      >
        {selectedMolecule && (
          <div>
            <Descriptions title={selectedMolecule.name || '分子详情'} column={2} bordered>
              <Descriptions.Item label="分子式">
                {selectedMolecule.chemical_formula || 'N/A'}
              </Descriptions.Item>
              <Descriptions.Item label="SMILES表示">
                <Text code>{selectedMolecule.smiles_notation || 'N/A'}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="组分类型">
                <Tag color="blue">{selectedMolecule.component_type || '未知'}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="生成方法">
                <Tag color="green">{selectedMolecule.generation_method || 'N/A'}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="生成时间" span={2}>
                {selectedMolecule.created_at ? new Date(selectedMolecule.created_at).toLocaleString() : 'N/A'}
              </Descriptions.Item>
            </Descriptions>

            {selectedMolecule.molecular_properties && (
              <div style={{ marginTop: 24 }}>
                <Title level={5}>分子性质</Title>
                <Descriptions column={2} bordered size="small">
                  <Descriptions.Item label="分子量">
                    {selectedMolecule.molecular_properties.molecular_weight?.toFixed(2) || 'N/A'}
                  </Descriptions.Item>
                  <Descriptions.Item label="LogP">
                    {selectedMolecule.molecular_properties.logp?.toFixed(2) || 'N/A'}
                  </Descriptions.Item>
                  <Descriptions.Item label="氢键受体数">
                    {selectedMolecule.molecular_properties.num_h_acceptors || 'N/A'}
                  </Descriptions.Item>
                  <Descriptions.Item label="氢键供体数">
                    {selectedMolecule.molecular_properties.num_h_donors || 'N/A'}
                  </Descriptions.Item>
                  <Descriptions.Item label="可旋转键数">
                    {selectedMolecule.molecular_properties.num_rotatable_bonds || 'N/A'}
                  </Descriptions.Item>
                  <Descriptions.Item label="TPSA">
                    {selectedMolecule.molecular_properties.tpsa?.toFixed(2) || 'N/A'}
                  </Descriptions.Item>
                </Descriptions>
              </div>
            )}

            {selectedMolecule.generation_metadata && (
              <div style={{ marginTop: 24 }}>
                <Title level={5}>生成元数据</Title>
                <pre style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px', fontSize: '12px' }}>
                  {JSON.stringify(selectedMolecule.generation_metadata, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* 文献详情模态框 */}
      <Modal
        title={
          <span>
            <FileTextOutlined style={{ marginRight: 8, color: '#1890ff' }} />
            文献详细信息
          </span>
        }
        open={!!selectedLiterature}
        onCancel={() => setSelectedLiterature(null)}
        footer={[
          <Button key="close" onClick={() => setSelectedLiterature(null)}>
            关闭
          </Button>
        ]}
        width={900}
        style={{ top: 20 }}
      >
        {selectedLiterature && (
          <div>
            <Descriptions title="文献基本信息" column={2} bordered>
              <Descriptions.Item label="标题" span={2}>
                {selectedLiterature.title || 'N/A'}
              </Descriptions.Item>
              <Descriptions.Item label="文献ID">
                <Text code>{selectedLiterature.id || 'N/A'}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color="blue">{selectedLiterature.status || '已处理'}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="置信度">
                {selectedLiterature.confidence_score ? (
                  <Progress
                    percent={Math.round(selectedLiterature.confidence_score * 100)}
                    size="small"
                    status={selectedLiterature.confidence_score >= 0.8 ? 'success' : 'normal'}
                  />
                ) : 'N/A'}
              </Descriptions.Item>
              <Descriptions.Item label="处理时间" span={2}>
                {selectedLiterature.processed_at ? new Date(selectedLiterature.processed_at).toLocaleString() : 'N/A'}
              </Descriptions.Item>
            </Descriptions>

            {selectedLiterature.extracted_data && (
              <div style={{ marginTop: 24 }}>
                <Title level={5}>提取数据</Title>
                <Tabs defaultActiveKey="formulas" size="small">
                  {selectedLiterature.extracted_data.formulas && selectedLiterature.extracted_data.formulas.length > 0 && (
                    <TabPane tab={`配方 (${selectedLiterature.extracted_data.formulas.length})`} key="formulas">
                      <List
                        size="small"
                        dataSource={selectedLiterature.extracted_data.formulas}
                        renderItem={(formula: any, index: number) => (
                          <List.Item>
                            <Card size="small" style={{ width: '100%' }}>
                              <div><strong>配方 {index + 1}</strong></div>
                              <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                                类型: {formula.type || 'N/A'}
                              </div>
                              {formula.components && (
                                <div style={{ marginTop: '8px' }}>
                                  <Text strong>组分:</Text>
                                  <div style={{ marginLeft: '16px' }}>
                                    {formula.components.map((comp: any, compIndex: number) => (
                                      <div key={compIndex} style={{ fontSize: '12px' }}>
                                        • {comp.name} ({comp.concentration || 'N/A'} {comp.unit || ''})
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </Card>
                          </List.Item>
                        )}
                      />
                    </TabPane>
                  )}

                  {selectedLiterature.extracted_data.molecules && selectedLiterature.extracted_data.molecules.length > 0 && (
                    <TabPane tab={`分子 (${selectedLiterature.extracted_data.molecules.length})`} key="molecules">
                      <List
                        size="small"
                        dataSource={selectedLiterature.extracted_data.molecules}
                        renderItem={(molecule: any, index: number) => (
                          <List.Item>
                            <Card size="small" style={{ width: '100%' }}>
                              <div><strong>分子 {index + 1}</strong></div>
                              <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                                分子式: {molecule.chemical_formula || 'N/A'}
                              </div>
                              <div style={{ fontSize: '12px', color: '#666' }}>
                                SMILES: <Text code>{molecule.smiles_notation || 'N/A'}</Text>
                              </div>
                              {molecule.properties && (
                                <div style={{ marginTop: '8px' }}>
                                  <Text strong>性质:</Text>
                                  <div style={{ marginLeft: '16px', fontSize: '12px' }}>
                                    {Object.entries(molecule.properties).map(([key, value]: [string, any]) => (
                                      <div key={key}>• {key}: {value}</div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </Card>
                          </List.Item>
                        )}
                      />
                    </TabPane>
                  )}

                  {selectedLiterature.extracted_data.properties && selectedLiterature.extracted_data.properties.length > 0 && (
                    <TabPane tab={`性质 (${selectedLiterature.extracted_data.properties.length})`} key="properties">
                      <List
                        size="small"
                        dataSource={selectedLiterature.extracted_data.properties}
                        renderItem={(property: any, index: number) => (
                          <List.Item>
                            <Card size="small" style={{ width: '100%' }}>
                              <div><strong>性质 {index + 1}</strong></div>
                              <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                                类型: {property.type || 'N/A'}
                              </div>
                              <div style={{ fontSize: '12px', color: '#666' }}>
                                数值: {property.value || 'N/A'} {property.unit || ''}
                              </div>
                              {property.conditions && (
                                <div style={{ fontSize: '12px', color: '#666' }}>
                                  条件: {property.conditions}
                                </div>
                              )}
                            </Card>
                          </List.Item>
                        )}
                      />
                    </TabPane>
                  )}
                </Tabs>
              </div>
            )}

            {selectedLiterature.processing_log && (
              <div style={{ marginTop: 24 }}>
                <Title level={5}>处理日志</Title>
                <pre style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px', fontSize: '12px', maxHeight: '200px', overflow: 'auto' }}>
                  {selectedLiterature.processing_log}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>
      {/* 步骤回顾模态框 */}
      <Modal
        title={
          <span>
            <span style={{ marginRight: 8 }}>{steps[reviewingStep || 0]?.icon}</span>
            {steps[reviewingStep || 0]?.title} - 历史回顾
          </span>
        }
        open={showReviewModal}
        onCancel={handleCloseReviewModal}
        footer={[
          <Button key="close" onClick={handleCloseReviewModal}>
            关闭
          </Button>
        ]}
        width={800}
        style={{ top: 20 }}
      >
        {renderReviewContent()}
      </Modal>

      </div>
  );
};

export default AIDesignerPage;