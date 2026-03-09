import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Tag,
  Input,
  Space,
  Typography,
  Modal,
  Descriptions,
  Progress,
  Button,
  Tabs,
  Timeline,
  Spin,
  Row,
  Col,
  Select,
  Badge,
  Statistic,
  message,
  Alert,
  Empty,
} from 'antd';
import { SearchOutlined, EyeOutlined, ExperimentOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { Experiment, EXPERIMENT_FORMULA_CONSTRAINTS, Formula, BatteryPerformance, MonitoringData } from '../types';
import { experimentsApi, monitoringApi } from '../services/api';
import { useRealTimeMonitoring } from '../hooks/useRealTimeMonitoring';

const { Title, Paragraph, Text } = Typography;
const { Search } = Input;
const { TabPane } = Tabs;

// 实时监控数据包装组件
interface RealTimeMonitoringWrapperProps {
  experimentId: number;
  formulaId: number;
  onDataUpdate: (data: MonitoringData[]) => void;
  children: (props: {
    isConnected: boolean;
    lastUpdate: string | null;
    reconnect: () => void;
    hasRealTimeData: boolean;
  }) => React.ReactNode;
}

const RealTimeMonitoringWrapper: React.FC<RealTimeMonitoringWrapperProps> = ({
  experimentId,
  formulaId,
  onDataUpdate,
  children
}) => {
  const {
    monitoringData,
    isConnected,
    isLoading,
    error,
    lastUpdate,
    refreshData
  } = useRealTimeMonitoring({
    experimentId,
    formulaId,
    dataTypes: ['charge_discharge', 'voltage', 'impedance', 'temperature'],
    updateInterval: 3, // 3秒更新一次
    autoConnect: true
  });

  // 当实时数据更新时，通知父组件
  useEffect(() => {
    if (monitoringData.length > 0) {
      onDataUpdate(monitoringData);
    }
  }, [monitoringData, formulaId, onDataUpdate]);

  const reconnect = () => {
    refreshData();
  };

  return (
    <>
      {children({
        isConnected,
        lastUpdate,
        reconnect,
        hasRealTimeData: monitoringData.length > 0
      })}
    </>
  );
};

// 辅助函数：创建component对象
const createComponent = (id: number, formula_id: number, name: string, concentration: number, unit: string, type: string) => ({
  id,
  formula_id,
  name,
  concentration,
  unit,
  component_type: type,
  chemical_formula: name,
  source: 'experimental',
  created_at: new Date().toISOString()
});

// 辅助函数：创建配方对象
const createFormula = (id: number, name: string, description: string, systemType: string, scenario: string, generationMethod: string, components: any[]): Formula => ({
  id,
  name,
  description,
  system_type: systemType as '正极' | '负极' | '电解液',
  application_scenario: scenario,
  generation_method: generationMethod as 'initial_design' | 'bayesian_opt' | 'redesign',
  components,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString()
});

// 辅助函数：创建电池性能数据
const createBatteryPerformance = (id: number, formulaId: number, batteryNumber: number, basePerformance: any, status: 'completed' | 'testing' | 'pending' = 'completed'): BatteryPerformance => {
  const randomVariation = (base: number, variance: number = 0.1) => {
    return base * (1 + (Math.random() - 0.5) * variance);
  };

  return {
    id,
    formula_id: formulaId,
    battery_number: batteryNumber,
    status,
    performance_metrics: {
      energy_density: randomVariation(basePerformance.energy_density || 180),
      power_density: randomVariation(basePerformance.power_density || 1200),
      cycle_life: Math.round(randomVariation(basePerformance.cycle_life || 1000)),
      safety_score: randomVariation(basePerformance.safety_score || 0.9, 0.05),
      coulombic_efficiency: randomVariation(95, 0.02),
      impedance: randomVariation(25, 0.2),
      ionic_conductivity: randomVariation(12, 0.15),
      working_temperature_range: {
        min: basePerformance.working_temperature_min || -20,
        max: basePerformance.working_temperature_max || 60
      },
      voltage_retention: randomVariation(92, 0.03),
      capacity_retention: randomVariation(85, 0.05),
      cost_per_kwh: randomVariation(basePerformance.cost_per_kwh || 100, 0.1)
    },
    test_data: status === 'completed' ? {
      charge_discharge_cycles: [
        { cycle: 1, charge_capacity: 100, discharge_capacity: 95, efficiency: 95 },
        { cycle: 100, charge_capacity: 98, discharge_capacity: 92, efficiency: 93.9 },
        { cycle: 500, charge_capacity: 95, discharge_capacity: 88, efficiency: 92.6 }
      ],
      impedance_analysis: {
        initial_impedance: randomVariation(20, 0.15),
        impedance_growth: randomVariation(15, 0.2),
        charge_transfer_resistance: randomVariation(12, 0.1)
      },
      temperature_performance: [
        { temperature: -20, performance_retention: 75 },
        { temperature: 25, performance_retention: 100 },
        { temperature: 60, performance_retention: 85 }
      ],
      safety_tests: {
        overcharge_test: Math.random() > 0.1,
        short_circuit_test: Math.random() > 0.05,
        thermal_runaway_test: Math.random() > 0.02,
        nail_penetration_test: Math.random() > 0.08
      }
    } : undefined,
    test_metadata: {
      test_start_time: new Date(Date.now() - 86400000 * 2).toISOString(),
      test_completion_time: status === 'completed' ? new Date().toISOString() : undefined,
      test_duration_hours: status === 'completed' ? 48 : undefined,
      test_conditions: {
        temperature: 25,
        humidity: 45,
        pressure: 101.3
      },
      equipment_used: ['Battery Tester-2000', 'Thermal Chamber-500', 'Impedance Analyzer'],
      operator: `operator_${Math.floor(Math.random() * 3) + 1}`
    },
    quality_assessment: {
      overall_score: Math.round(randomVariation(85, 0.1)),
      reliability_rating: (['A', 'B', 'C'][Math.floor(Math.random() * 3)] as 'A' | 'B' | 'C'),
      consistency_score: randomVariation(90, 0.05),
      pass_criteria_met: Math.random() > 0.15,
      failure_reasons: Math.random() > 0.85 ? ['minor_variance'] : undefined
    },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };
};

const ExperimentListPage: React.FC = () => {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedExperiment, setSelectedExperiment] = useState<Experiment | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [selectedFormula, setSelectedFormula] = useState<Formula | null>(null);
  const [experimentFormulas, setExperimentFormulas] = useState<any>(null);

  // 监控数据相关状态
  const [formulaMonitoringData, setFormulaMonitoringData] = useState<{[key: number]: MonitoringData[]}>({});
  const [monitoringLoading, setMonitoringLoading] = useState(false);
  const [selectedViewType, setSelectedViewType] = useState<'overview' | 'detailed'>('overview');
  const [selectedCycle, setSelectedCycle] = useState<number | null>(null);

  useEffect(() => {
    // 加载实验数据，包含贝叶斯优化配方
    loadExperiments();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const loadExperiments = async () => {
    try {
      setLoading(true);
      const response = await experimentsApi.getExperiments({
        page: 1,
        per_page: 50
      });

      if (response.success) {
        setExperiments(response.data.experiments);
      } else {
        console.error('获取实验数据失败:', response.message);
        // 降级到模拟数据
        loadMockExperiments();
      }
    } catch (error) {
      console.error('加载实验数据异常:', error);
      // 降级到模拟数据
      loadMockExperiments();
    } finally {
      setLoading(false);
    }
  };

  const loadMockExperiments = () => {
    // 模拟实验数据 - 支持多配方和电池性能数据
    const mockExperiments: any[] = [
      // 已完成的实验 - 包含3个配方，每个配方3个电池
      {
        id: 1,
        experiment_id: 'EXP-20241201-001',
        name: '实验_001',
        description: '高能量密度正极电解液多配方对比实验',
        status: 'completed',
        experiment_type: 'screening',
        formula_count: 3,
        user_requirements: {
          energy_density: 200,
          power_density: 1500,
          cycle_life: 1000,
          safety_score: 0.85,
          working_temperature: -20
        },
        created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
        started_at: new Date(Date.now() - 86400000 * 4).toISOString(),
        completed_at: new Date(Date.now() - 86400000 * 3).toISOString(),
        formulas: [
          createFormula(1, '高能量密度电解液配方-A', '基础高能量密度配方', '电解液', '动力', 'initial_design', [
            createComponent(1, 1, 'EC', 30, 'wt%', 'solvent'),
            createComponent(2, 1, 'DMC', 25, 'wt%', 'solvent'),
            createComponent(3, 1, 'LiPF6', 12, 'wt%', 'salt'),
            createComponent(4, 1, 'FEC', 5, 'wt%', 'additive'),
            createComponent(5, 1, 'VC', 3, 'wt%', 'additive')
          ]),
          createFormula(2, '高能量密度电解液配方-B', '优化粘度配方', '电解液', '动力', 'bayesian_opt', [
            createComponent(6, 2, 'EC', 28, 'wt%', 'solvent'),
            createComponent(7, 2, 'EMC', 27, 'wt%', 'solvent'),
            createComponent(8, 2, 'LiPF6', 11, 'wt%', 'salt'),
            createComponent(9, 2, 'FEC', 6, 'wt%', 'additive'),
            createComponent(10, 2, 'DTD', 4, 'wt%', 'additive')
          ]),
          createFormula(3, '高能量密度电解液配方-C', '低成本配方', '电解液', '动力', 'redesign', [
            createComponent(11, 3, 'EC', 32, 'wt%', 'solvent'),
            createComponent(12, 3, 'DEC', 23, 'wt%', 'solvent'),
            createComponent(13, 3, 'LiPF6', 10, 'wt%', 'salt'),
            createComponent(14, 3, 'FEC', 4, 'wt%', 'additive'),
            createComponent(15, 3, 'VEC', 3, 'wt%', 'additive')
          ])
        ],
        battery_performances: [
          // 配方1的3个电池
          createBatteryPerformance(1, 1, 1, { energy_density: 220, power_density: 1600, cycle_life: 1200, safety_score: 0.88 }),
          createBatteryPerformance(2, 1, 2, { energy_density: 220, power_density: 1600, cycle_life: 1200, safety_score: 0.88 }),
          createBatteryPerformance(3, 1, 3, { energy_density: 220, power_density: 1600, cycle_life: 1200, safety_score: 0.88 }),
          // 配方2的3个电池
          createBatteryPerformance(4, 2, 1, { energy_density: 235, power_density: 1700, cycle_life: 1100, safety_score: 0.86 }),
          createBatteryPerformance(5, 2, 2, { energy_density: 235, power_density: 1700, cycle_life: 1100, safety_score: 0.86 }),
          createBatteryPerformance(6, 2, 3, { energy_density: 235, power_density: 1700, cycle_life: 1100, safety_score: 0.86 }),
          // 配方3的3个电池
          createBatteryPerformance(7, 3, 1, { energy_density: 210, power_density: 1550, cycle_life: 1150, safety_score: 0.90, cost_per_kwh: 85 }),
          createBatteryPerformance(8, 3, 2, { energy_density: 210, power_density: 1550, cycle_life: 1150, safety_score: 0.90, cost_per_kwh: 85 }),
          createBatteryPerformance(9, 3, 3, { energy_density: 210, power_density: 1550, cycle_life: 1150, safety_score: 0.90, cost_per_kwh: 85 })
        ]
      },
      // 运行中的实验 - 包含2个配方，部分电池测试中
      {
        id: 2,
        experiment_id: 'EXP-20241202-002',
        name: '实验_002',
        description: '低温性能优化电解液实验',
        status: 'running',
        experiment_type: 'optimization',
        formula_count: 2,
        user_requirements: {
          energy_density: 180,
          power_density: 1200,
          cycle_life: 800,
          working_temperature: -40
        },
        created_at: new Date(Date.now() - 86400000 * 4).toISOString(),
        started_at: new Date(Date.now() - 86400000 * 3).toISOString(),
        formulas: [
          createFormula(4, '低温电解液配方-A', '标准低温配方', '电解液', '3C', 'bayesian_opt', [
            createComponent(16, 4, 'EC', 25, 'wt%', 'solvent'),
            createComponent(17, 4, 'EMC', 35, 'wt%', 'solvent'),
            createComponent(18, 4, 'LiTFSI', 10, 'wt%', 'salt'),
            createComponent(19, 4, 'FEC', 5, 'wt%', 'additive'),
            createComponent(20, 4, 'DTD', 5, 'wt%', 'additive')
          ]),
          createFormula(5, '低温电解液配方-B', '超低温配方', '电解液', '3C', 'redesign', [
            createComponent(21, 5, 'EC', 20, 'wt%', 'solvent'),
            createComponent(22, 5, 'EMC', 40, 'wt%', 'solvent'),
            createComponent(23, 5, 'LiTFSI', 12, 'wt%', 'salt'),
            createComponent(24, 5, 'FEC', 6, 'wt%', 'additive'),
            createComponent(25, 5, 'LiDFOB', 4, 'wt%', 'additive')
          ])
        ],
        battery_performances: [
          // 配方1: 2个电池完成，1个测试中
          createBatteryPerformance(10, 4, 1, { energy_density: 175, power_density: 1250, cycle_life: 850 }),
          createBatteryPerformance(11, 4, 2, { energy_density: 175, power_density: 1250, cycle_life: 850 }),
          createBatteryPerformance(12, 4, 3, { energy_density: 175, power_density: 1250, cycle_life: 850 }, 'testing'),
          // 配方2: 1个电池完成，2个测试中
          createBatteryPerformance(13, 5, 1, { energy_density: 182, power_density: 1300, cycle_life: 820 }),
          createBatteryPerformance(14, 5, 2, { energy_density: 182, power_density: 1300, cycle_life: 820 }, 'testing'),
          createBatteryPerformance(15, 5, 3, { energy_density: 182, power_density: 1300, cycle_life: 820 }, 'testing')
        ]
      },
      // 等待中的实验 - 包含1个配方，电池等待测试
      {
        id: 3,
        experiment_id: 'EXP-20241203-003',
        name: '实验_003',
        description: '长循环寿命储能电解液验证实验',
        status: 'pending',
        experiment_type: 'validation',
        formula_count: 1,
        user_requirements: {
          energy_density: 160,
          power_density: 800,
          cycle_life: 3000,
          safety_score: 0.9
        },
        created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
        formulas: [
          createFormula(6, '长寿命电解液配方-A', '超长寿命储能配方', '电解液', '储能', 'redesign', [
            createComponent(26, 6, 'EC', 35, 'wt%', 'solvent'),
            createComponent(27, 6, 'PC', 25, 'wt%', 'solvent'),
            createComponent(28, 6, 'LiFSI', 8, 'wt%', 'salt'),
            createComponent(29, 6, 'LiBOB', 4, 'wt%', 'salt'),
            createComponent(30, 6, 'VC', 4, 'wt%', 'additive')
          ])
        ],
        battery_performances: [
          // 配方1: 3个电池都等待测试
          createBatteryPerformance(16, 6, 1, { energy_density: 165, power_density: 850, cycle_life: 3200 }, 'pending'),
          createBatteryPerformance(17, 6, 2, { energy_density: 165, power_density: 850, cycle_life: 3200 }, 'pending'),
          createBatteryPerformance(18, 6, 3, { energy_density: 165, power_density: 850, cycle_life: 3200 }, 'pending')
        ]
      },

      // 兼容性实验数据 - 保持原有单配方结构
      {
        id: 4,
        name: '实验_004',
        description: '快充性能电解液优化实验',
        status: 'completed',
        formula_id: 2,
        user_requirements: {
          energy_density: 180,
          power_density: 1200,
          cycle_life: 800,
          working_temperature: -40
        },
        created_at: new Date(Date.now() - 86400000 * 4).toISOString(),
        started_at: new Date(Date.now() - 86400000 * 3).toISOString(),
        completed_at: new Date(Date.now() - 86400000 * 2).toISOString(),
        formula: {
          id: 2,
          name: '低温电解液配方',
          description: '适用于寒冷地区的高性能电解液',
          system_type: '电解液',
          application_scenario: '3C',
          generation_method: 'bayesian_opt',
          created_at: new Date().toISOString(),
          components: [
            { name: 'EC', concentration: 25, unit: 'wt%', component_type: 'solvent' },
            { name: 'EMC', concentration: 35, unit: 'wt%', component_type: 'solvent' },
            { name: 'DEC', concentration: 20, unit: 'wt%', component_type: 'solvent' },
            { name: 'LiTFSI', concentration: 10, unit: 'wt%', component_type: 'salt' },
            { name: 'FEC', concentration: 5, unit: 'wt%', component_type: 'additive' },
            { name: 'DTD', concentration: 5, unit: 'wt%', component_type: 'additive' }
          ]
        }
      },
      {
        id: 3,
        name: '实验_003',
        description: '长循环寿命储能电解液实验',
        status: 'completed',
        formula_id: 3,
        user_requirements: {
          energy_density: 160,
          power_density: 800,
          cycle_life: 3000,
          safety_score: 0.9
        },
        created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
        started_at: new Date(Date.now() - 86400000 * 2).toISOString(),
        completed_at: new Date(Date.now() - 86400000 * 1).toISOString(),
        formula: {
          id: 3,
          name: '长寿命电解液配方',
          description: '为储能系统设计的超长寿命电解液',
          system_type: '电解液',
          application_scenario: '储能',
          generation_method: 'redesign',
          created_at: new Date().toISOString(),
          components: [
            { name: 'EC', concentration: 35, unit: 'wt%', component_type: 'solvent' },
            { name: 'PC', concentration: 25, unit: 'wt%', component_type: 'solvent' },
            { name: 'LiFSI', concentration: 8, unit: 'wt%', component_type: 'salt' },
            { name: 'LiBOB', concentration: 4, unit: 'wt%', component_type: 'salt' },
            { name: 'VC', concentration: 4, unit: 'wt%', component_type: 'additive' },
            { name: 'PS', concentration: 3, unit: 'wt%', component_type: 'additive' },
            { name: 'LiPO2F2', concentration: 2, unit: 'wt%', component_type: 'additive' }
          ]
        }
      },
      {
        id: 4,
        name: '实验_004',
        description: '快充性能电解液优化实验',
        status: 'completed',
        formula_id: 4,
        user_requirements: {
          energy_density: 190,
          power_density: 2000,
          cycle_life: 1200,
          safety_score: 0.85
        },
        created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
        started_at: new Date(Date.now() - 86400000 * 1).toISOString(),
        completed_at: new Date(Date.now() - 86400000 * 0.5).toISOString(),
        formula: {
          id: 4,
          name: '快充电解液配方',
          description: '支持超级快充的高性能电解液',
          system_type: '电解液',
          application_scenario: '动力',
          generation_method: 'ai_optimization',
          created_at: new Date().toISOString(),
          components: [
            { name: 'EC', concentration: 28, unit: 'wt%', component_type: 'solvent' },
            { name: 'DMC', concentration: 32, unit: 'wt%', component_type: 'solvent' },
            { name: 'DME', concentration: 15, unit: 'wt%', component_type: 'solvent' },
            { name: 'LiPF6', concentration: 11, unit: 'wt%', component_type: 'salt' },
            { name: 'LiFSI', concentration: 4, unit: 'wt%', component_type: 'salt' },
            { name: 'ES', concentration: 4, unit: 'wt%', component_type: 'additive' },
            { name: 'TMSP', concentration: 3, unit: 'wt%', component_type: 'additive' }
          ]
        }
      },
      {
        id: 5,
        name: '实验_005',
        description: '高安全性电解液验证实验',
        status: 'completed',
        formula_id: 5,
        user_requirements: {
          energy_density: 170,
          power_density: 1000,
          cycle_life: 1500,
          safety_score: 0.95
        },
        created_at: new Date(Date.now() - 86400000 * 1).toISOString(),
        started_at: new Date(Date.now() - 86400000 * 0.8).toISOString(),
        completed_at: new Date(Date.now() - 86400000 * 0.3).toISOString(),
        formula: {
          id: 5,
          name: '高安全性电解液配方',
          description: '专为安全敏感应用设计的阻燃电解液',
          system_type: '电解液',
          application_scenario: '储能',
          generation_method: 'safety_first',
          created_at: new Date().toISOString(),
          components: [
            { name: 'EC', concentration: 30, unit: 'wt%', component_type: 'solvent' },
            { name: 'DEC', concentration: 35, unit: 'wt%', component_type: 'solvent' },
            { name: 'LiBF4', concentration: 10, unit: 'wt%', component_type: 'salt' },
            { name: 'LiDFOB', concentration: 5, unit: 'wt%', component_type: 'salt' },
            { name: 'VEC', concentration: 5, unit: 'wt%', component_type: 'additive' },
            { name: 'TTSPi', concentration: 8, unit: 'wt%', component_type: 'additive' },
            { name: 'Al2O3', concentration: 2, unit: 'wt%', component_type: 'additive' }
          ]
        }
      },

      // 正在运行的实验
      {
        id: 6,
        name: '实验_006',
        description: '下一代高电压正极电解液开发实验',
        status: 'running',
        formula_id: 6,
        user_requirements: {
          energy_density: 250,
          power_density: 1800,
          cycle_life: 1000,
          safety_score: 0.88,
          voltage: 4.5
        },
        created_at: new Date(Date.now() - 3600000 * 6).toISOString(),
        started_at: new Date(Date.now() - 3600000 * 4).toISOString(),
        formula: {
          id: 6,
          name: '高电压电解液配方',
          description: '适用于4.5V高电压体系的电解液',
          system_type: '正极',
          application_scenario: '动力',
          generation_method: 'high_voltage_opt',
          created_at: new Date().toISOString(),
          components: [
            { name: 'EC', concentration: 20, unit: 'wt%', component_type: 'solvent' },
            { name: 'DMC', concentration: 30, unit: 'wt%', component_type: 'solvent' },
            { name: 'AN', concentration: 15, unit: 'wt%', component_type: 'solvent' },
            { name: 'LiPF6', concentration: 13, unit: 'wt%', component_type: 'salt' },
            { name: 'LiDFOB', concentration: 7, unit: 'wt%', component_type: 'salt' },
            { name: 'FEC', concentration: 6, unit: 'wt%', component_type: 'additive' },
            { name: 'LiDFP', concentration: 4, unit: 'wt%', component_type: 'additive' }
          ]
        }
      },
      {
        id: 7,
        name: '实验_007',
        description: '成本优化储能电解液验证实验',
        status: 'running',
        formula_id: 7,
        user_requirements: {
          energy_density: 150,
          power_density: 600,
          cycle_life: 2000,
          cost_per_kwh: 500
        },
        created_at: new Date(Date.now() - 3600000 * 4).toISOString(),
        started_at: new Date(Date.now() - 3600000 * 3).toISOString(),
        formula: {
          id: 7,
          name: '成本优化电解液配方',
          description: '低成本高性能储能电解液方案',
          system_type: '电解液',
          application_scenario: '储能',
          generation_method: 'cost_optimization',
          created_at: new Date().toISOString(),
          components: [
            { name: 'EC', concentration: 25, unit: 'wt%', component_type: 'solvent' },
            { name: 'DMC', concentration: 40, unit: 'wt%', component_type: 'solvent' },
            { name: 'LiPF6', concentration: 10, unit: 'wt%', component_type: 'salt' },
            { name: 'VC', concentration: 3, unit: 'wt%', component_type: 'additive' },
            { name: 'FEC', concentration: 2, unit: 'wt%', component_type: 'additive' }
          ]
        }
      },
      {
        id: 8,
        name: '实验_008',
        description: '固态电池界面电解液适配实验',
        status: 'running',
        formula_id: 8,
        user_requirements: {
          energy_density: 300,
          power_density: 1500,
          cycle_life: 800,
          ionic_conductivity: 10
        },
        created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
        started_at: new Date(Date.now() - 3600000 * 1).toISOString(),
        formula: {
          id: 8,
          name: '固态界面电解液配方',
          description: '用于固态电池界面优化的电解液',
          system_type: '电解液',
          application_scenario: '动力',
          generation_method: 'solid_state_opt',
          created_at: new Date().toISOString(),
          components: [
            { name: 'EC', concentration: 15, unit: 'wt%', component_type: 'solvent' },
            { name: 'DME', concentration: 25, unit: 'wt%', component_type: 'solvent' },
            { name: 'DOL', concentration: 20, unit: 'wt%', component_type: 'solvent' },
            { name: 'LiTFSI', concentration: 15, unit: 'wt%', component_type: 'salt' },
            { name: 'LiNO2', concentration: 8, unit: 'wt%', component_type: 'salt' },
            { name: 'PS', concentration: 5, unit: 'wt%', component_type: 'additive' },
            { name: 'LiDFOB', concentration: 3, unit: 'wt%', component_type: 'additive' }
          ]
        }
      },

      // 失败的实验
      {
        id: 9,
        name: '实验_009',
        description: '超高浓度电解液稳定性测试',
        status: 'failed',
        formula_id: 9,
        user_requirements: {
          energy_density: 280,
          power_density: 1200,
          cycle_life: 600
        },
        created_at: new Date(Date.now() - 7200000 * 3).toISOString(),
        started_at: new Date(Date.now() - 7200000 * 2).toISOString(),
        completed_at: new Date(Date.now() - 7200000 * 1).toISOString(),
        formula: {
          id: 9,
          name: '超高浓度电解液配方',
          description: '5M超高浓度锂盐电解液',
          system_type: '电解液',
          application_scenario: '动力',
          generation_method: 'high_concentration',
          created_at: new Date().toISOString(),
          components: [
            { name: 'DME', concentration: 40, unit: 'wt%', component_type: 'solvent' },
            { name: 'TMSB', concentration: 20, unit: 'wt%', component_type: 'solvent' },
            { name: 'LiFSI', concentration: 25, unit: 'wt%', component_type: 'salt' },
            { name: 'LiTFSI', concentration: 10, unit: 'wt%', component_type: 'salt' },
            { name: 'FEC', concentration: 5, unit: 'wt%', component_type: 'additive' }
          ]
        }
      },
      {
        id: 10,
        name: '实验_010',
        description: '新型溶剂体系兼容性验证',
        status: 'failed',
        formula_id: 10,
        user_requirements: {
          energy_density: 220,
          power_density: 1400,
          cycle_life: 800
        },
        created_at: new Date(Date.now() - 3600000 * 8).toISOString(),
        started_at: new Date(Date.now() - 3600000 * 6).toISOString(),
        completed_at: new Date(Date.now() - 3600000 * 4).toISOString(),
        formula: {
          id: 10,
          name: '新型溶剂电解液配方',
          description: '基于GBL/THF混合溶剂的电解液',
          system_type: '电解液',
          application_scenario: '3C',
          generation_method: 'novel_solvent',
          created_at: new Date().toISOString(),
          components: [
            { name: 'GBL', concentration: 30, unit: 'wt%', component_type: 'solvent' },
            { name: 'THF', concentration: 25, unit: 'wt%', component_type: 'solvent' },
            { name: 'EC', concentration: 20, unit: 'wt%', component_type: 'solvent' },
            { name: 'LiTFSI', concentration: 12, unit: 'wt%', component_type: 'salt' },
            { name: 'VC', concentration: 4, unit: 'wt%', component_type: 'additive' },
            { name: 'PES', concentration: 3, unit: 'wt%', component_type: 'additive' }
          ]
        }
      },

      // 等待中的实验
      {
        id: 11,
        name: '实验_011',
        description: '多功能复合添加剂验证实验',
        status: 'pending',
        formula_id: 11,
        user_requirements: {
          energy_density: 210,
          power_density: 1600,
          cycle_life: 1500,
          safety_score: 0.92
        },
        created_at: new Date(Date.now() - 3600000 * 1).toISOString(),
        formula: {
          id: 11,
          name: '多功能添加剂电解液配方',
          description: '集成VC、FEC、DTD等多种添加剂',
          system_type: '电解液',
          application_scenario: '动力',
          generation_method: 'multi_additive',
          created_at: new Date().toISOString(),
          components: [
            { name: 'EC', concentration: 28, unit: 'wt%', component_type: 'solvent' },
            { name: 'DMC', concentration: 35, unit: 'wt%', component_type: 'solvent' },
            { name: 'LiPF6', concentration: 11, unit: 'wt%', component_type: 'salt' },
            { name: 'VC', concentration: 4, unit: 'wt%', component_type: 'additive' },
            { name: 'FEC', concentration: 3, unit: 'wt%', component_type: 'additive' },
            { name: 'DTD', concentration: 3, unit: 'wt%', component_type: 'additive' },
            { name: 'LiPO2F2', concentration: 2, unit: 'wt%', component_type: 'additive' }
          ]
        }
      },
      {
        id: 12,
        name: '实验_012',
        description: '高温稳定性电解液开发实验',
        status: 'pending',
        formula_id: 12,
        user_requirements: {
          energy_density: 190,
          power_density: 1200,
          cycle_life: 1000,
          working_temperature: 60
        },
        created_at: new Date(Date.now() - 1800000).toISOString(),
        formula: {
          id: 12,
          name: '高温稳定电解液配方',
          description: '适用于高温环境的稳定电解液',
          system_type: '电解液',
          application_scenario: '储能',
          generation_method: 'high_temp_stable',
          created_at: new Date().toISOString(),
          components: [
            { name: 'PC', concentration: 30, unit: 'wt%', component_type: 'solvent' },
            { name: 'DEC', concentration: 30, unit: 'wt%', component_type: 'solvent' },
            { name: 'LiBOB', concentration: 12, unit: 'wt%', component_type: 'salt' },
            { name: 'LiDFOB', concentration: 6, unit: 'wt%', component_type: 'salt' },
            { name: 'VEC', concentration: 4, unit: 'wt%', component_type: 'additive' },
            { name: 'TMSB', concentration: 5, unit: 'wt%', component_type: 'additive' }
          ]
        }
      },

      // 更多已完成的实验
      {
        id: 13,
        name: '实验_013',
        description: '钠离子电池电解液适配实验',
        status: 'completed',
        formula_id: 13,
        user_requirements: {
          energy_density: 140,
          power_density: 800,
          cycle_life: 1200
        },
        created_at: new Date(Date.now() - 86400000 * 7).toISOString(),
        started_at: new Date(Date.now() - 86400000 * 6).toISOString(),
        completed_at: new Date(Date.now() - 86400000 * 5).toISOString(),
        formula: {
          id: 13,
          name: '钠离子电解液配方',
          description: '钠离子电池专用电解液',
          system_type: '电解液',
          application_scenario: '储能',
          generation_method: 'sodium_ion',
          created_at: new Date().toISOString(),
          components: [
            { name: 'PC', concentration: 35, unit: 'wt%', component_type: 'solvent' },
            { name: 'EC', concentration: 30, unit: 'wt%', component_type: 'solvent' },
            { name: 'NaPF6', concentration: 12, unit: 'wt%', component_type: 'salt' },
            { name: 'FEC', concentration: 5, unit: 'wt%', component_type: 'additive' },
            { name: 'PS', concentration: 3, unit: 'wt%', component_type: 'additive' }
          ]
        }
      },
      {
        id: 14,
        name: '实验_014',
        description: '锂硫电池电解液优化实验',
        status: 'completed',
        formula_id: 14,
        user_requirements: {
          energy_density: 350,
          power_density: 1000,
          cycle_life: 500
        },
        created_at: new Date(Date.now() - 86400000 * 6).toISOString(),
        started_at: new Date(Date.now() - 86400000 * 5).toISOString(),
        completed_at: new Date(Date.now() - 86400000 * 4).toISOString(),
        formula: {
          id: 14,
          name: '锂硫电池电解液配方',
          description: '锂硫电池体系专用电解液',
          system_type: '电解液',
          application_scenario: '动力',
          generation_method: 'lithium_sulfur',
          created_at: new Date().toISOString(),
          components: [
            { name: 'DOL', concentration: 40, unit: 'wt%', component_type: 'solvent' },
            { name: 'DME', concentration: 30, unit: 'wt%', component_type: 'solvent' },
            { name: 'LiTFSI', concentration: 15, unit: 'wt%', component_type: 'salt' },
            { name: 'LiNO2', concentration: 8, unit: 'wt%', component_type: 'salt' },
            { name: 'PES', concentration: 4, unit: 'wt%', component_type: 'additive' },
            { name: 'TTSPi', concentration: 3, unit: 'wt%', component_type: 'additive' }
          ]
        }
      },
      {
        id: 15,
        name: '实验_015',
        description: '低阻抗电解液开发实验',
        status: 'completed',
        formula_id: 15,
        user_requirements: {
          energy_density: 180,
          power_density: 2500,
          cycle_life: 800,
          impedance: 20
        },
        created_at: new Date(Date.now() - 86400000 * 8).toISOString(),
        started_at: new Date(Date.now() - 86400000 * 7).toISOString(),
        completed_at: new Date(Date.now() - 86400000 * 6).toISOString(),
        formula: {
          id: 15,
          name: '低阻抗电解液配方',
          description: '超低阻抗高功率电解液',
          system_type: '电解液',
          application_scenario: '3C',
          generation_method: 'low_impedance',
          created_at: new Date().toISOString(),
          components: [
            { name: 'EC', concentration: 25, unit: 'wt%', component_type: 'solvent' },
            { name: 'DMC', concentration: 25, unit: 'wt%', component_type: 'solvent' },
            { name: 'DME', concentration: 20, unit: 'wt%', component_type: 'solvent' },
            { name: 'LiFSI', concentration: 12, unit: 'wt%', component_type: 'salt' },
            { name: 'LiPF6', concentration: 8, unit: 'wt%', component_type: 'salt' },
            { name: 'ES', concentration: 5, unit: 'wt%', component_type: 'additive' },
            { name: 'TMSB', concentration: 5, unit: 'wt%', component_type: 'additive' }
          ]
        }
      }
    ];

    setExperiments(mockExperiments);
  };

  const handleSearch = (value: string) => {
    setSearchText(value.toLowerCase());
  };

  const showDetail = async (experiment: Experiment) => {
    setSelectedExperiment(experiment);

    // 加载实验的详细配方信息
    try {
      const response = await experimentsApi.getExperimentFormulas(experiment.id);
      if (response.success) {
        setExperimentFormulas(response.data);
        // 默认选中第一个优化配方
        if (response.data.optimized_formulas && response.data.optimized_formulas.length > 0) {
          setSelectedFormula(response.data.optimized_formulas[0]);
        } else if (response.data.original_formula) {
          setSelectedFormula(response.data.original_formula);
        } else {
          setSelectedFormula(null);
        }
      } else {
        console.error('获取实验配方失败:', response.message);
        // 降级处理：使用实验数据中的配方信息
        if (experiment.formulas && experiment.formulas.length > 0) {
          setSelectedFormula(experiment.formulas[0]);
        } else if (experiment.formula_count && experiment.formula_count === 1 && (experiment as any).formula) {
          setSelectedFormula(null);
        }
      }
    } catch (error) {
      console.error('加载实验配方异常:', error);
      // 降级处理
      if (experiment.formulas && experiment.formulas.length > 0) {
        setSelectedFormula(experiment.formulas[0]);
      } else if (experiment.formula_count && experiment.formula_count === 1 && (experiment as any).formula) {
        setSelectedFormula(null);
      }
    }

    setDetailModalVisible(true);
    // 加载监控数据
    loadFormulaMonitoringData();
  };

  // 加载配方监控数据
  const loadFormulaMonitoringData = async () => {
    if (!selectedExperiment || !experimentFormulas) return;

    setMonitoringLoading(true);
    const monitoringData: {[key: number]: MonitoringData[]} = {};

    // 收集所有配方ID
    const formulaIds: number[] = [];
    if (experimentFormulas.original_formula) {
      formulaIds.push(experimentFormulas.original_formula.id);
    }
    if (experimentFormulas.optimized_formulas) {
      formulaIds.push(...experimentFormulas.optimized_formulas.map(f => f.id));
    }

    try {
      // 并行获取所有配方的监控数据
      const dataPromises = formulaIds.map(async (formulaId) => {
        try {
          const response = await monitoringApi.getFormulaMonitoringData({
            experiment_id: selectedExperiment.id,
            formula_id: formulaId,
            data_types: ['charge_discharge', 'voltage', 'impedance', 'temperature'],
            limit: 200 // 获取最近200个数据点
          });

          if (response.success && response.data) {
            return { formulaId, data: response.data.monitoring_data, success: true };
          } else {
            throw new Error('API返回失败');
          }
        } catch (error) {
          console.warn(`配方${formulaId}的实时监控数据获取失败，使用模拟数据:`, error);
          // 如果API失败，使用备用的模拟数据
          const mockData = await generateMockMonitoringData(formulaId);
          return { formulaId, data: mockData, success: false };
        }
      });

      const results = await Promise.all(dataPromises);

      // 组织数据
      results.forEach(({ formulaId, data, success }) => {
        monitoringData[formulaId] = data;
        if (!success) {
          console.log(`配方${formulaId}使用的是模拟数据`);
        }
      });

      setFormulaMonitoringData(monitoringData);

      // 统计真实数据使用情况
      const realDataCount = results.filter(r => r.success).length;
      if (realDataCount > 0) {
        message.success(`成功加载${realDataCount}个配方的实时监控数据`);
      }
    } catch (error) {
      console.error('加载监控数据失败:', error);
      message.error('加载监控数据失败，已使用模拟数据作为备用');
    } finally {
      setMonitoringLoading(false);
    }
  };

  // 生成模拟监控数据
  const generateMockMonitoringData = async (formulaId: number): Promise<MonitoringData[]> => {
    const mockData: MonitoringData[] = [];
    const numCycles = 50;

    for (let cycle = 1; cycle <= numCycles; cycle++) {
      // 模拟充电容量（轻微衰减）
      const baseCapacity = 2850;
      const degradationRate = 0.002; // 每个循环衰减0.2%
      const chargeCapacity = baseCapacity * (1 - degradationRate * (cycle - 1)) + (Math.random() - 0.5) * 20;

      // 模拟放电容量（考虑库伦效率）
      const baseEfficiency = 0.94;
      const efficiency = baseEfficiency + (Math.random() - 0.5) * 0.02;
      const dischargeCapacity = chargeCapacity * efficiency;

      // 模拟电压
      const nominalVoltage = 3.7 + (Math.random() - 0.5) * 0.2;

      // 模拟阻抗
      const baseImpedance = 0.05;
      const impedanceIncrease = 1 + (cycle - 1) * 0.01;
      const impedance = baseImpedance * impedanceIncrease + (Math.random() - 0.5) * 0.01;

      // 模拟温度
      const temperature = 25 + (Math.random() - 0.5) * 10;

      mockData.push({
        experiment_id: formulaId,
        data_type: 'charge_discharge_cycle',
        data: {
          cycle_number: cycle,
          voltage: parseFloat(nominalVoltage.toFixed(3)),
          current: parseFloat((chargeCapacity / 1000).toFixed(3)),
          capacity: parseFloat(dischargeCapacity.toFixed(2)),
          impedance: parseFloat(impedance.toFixed(4)),
          temperature: parseFloat(temperature.toFixed(1)),
          charge_capacity: parseFloat(chargeCapacity.toFixed(2)),
          discharge_capacity: parseFloat(dischargeCapacity.toFixed(2)),
          charge_efficiency: parseFloat(efficiency.toFixed(4)),
          timestamp: new Date(Date.now() - (numCycles - cycle) * 3600000).toISOString()
        },
        total_points: cycle
      });
    }

    return mockData;
  };

  // 渲染充放电曲线图表
  const renderChargeDischargeChart = (data: MonitoringData[]) => {
    if (!data || data.length === 0) return null;

    const cycles = data.map(d => d.data.cycle_number);
    const chargeCapacities = data.map(d => d.data.charge_capacity);
    const dischargeCapacities = data.map(d => d.data.discharge_capacity);
    const efficiencies = data.map(d => d.data.charge_efficiency * 100);

    return {
      title: {
        text: '充放电曲线 (容量 vs 循环圈数)',
        textStyle: { fontSize: 16 }
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          let result = `第${params[0].axisValue}次循环<br/>`;
          params.forEach((param: any) => {
            if (param.seriesName === '库伦效率') {
              result += `${param.seriesName}: ${param.value.toFixed(2)}%<br/>`;
            } else {
              result += `${param.seriesName}: ${param.value.toFixed(2)} mAh<br/>`;
            }
          });
          return result;
        }
      },
      legend: {
        data: ['充电容量', '放电容量', '库伦效率'],
        bottom: 0
      },
      xAxis: {
        type: 'value',
        name: '循环圈数',
        nameLocation: 'middle',
        nameGap: 25
      },
      yAxis: [
        {
          type: 'value',
          name: '容量 (mAh)',
          nameLocation: 'middle',
          nameGap: 40,
          position: 'left'
        },
        {
          type: 'value',
          name: '库伦效率 (%)',
          nameLocation: 'middle',
          nameGap: 40,
          position: 'right',
          min: 0,
          max: 100
        }
      ],
      series: [
        {
          name: '充电容量',
          type: 'line',
          data: chargeCapacities.map((capacity, index) => [cycles[index], capacity]),
          smooth: true,
          itemStyle: { color: '#1890ff' },
          lineStyle: { width: 2 }
        },
        {
          name: '放电容量',
          type: 'line',
          data: dischargeCapacities.map((capacity, index) => [cycles[index], capacity]),
          smooth: true,
          itemStyle: { color: '#52c41a' },
          lineStyle: { width: 2 }
        },
        {
          name: '库伦效率',
          type: 'line',
          data: efficiencies.map((efficiency, index) => [cycles[index], efficiency]),
          smooth: true,
          itemStyle: { color: '#faad14' },
          lineStyle: { width: 2 },
          yAxisIndex: 1
        }
      ]
    };
  };

  // 渲染电压曲线图表
  const renderVoltageChart = (data: MonitoringData[]) => {
    if (!data || data.length === 0) return null;

    const cycles = data.map(d => d.data.cycle_number);
    const voltages = data.map(d => d.data.voltage);

    return {
      title: {
        text: '电压变化曲线',
        textStyle: { fontSize: 16 }
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          const param = params[0];
          return `第${param.axisValue}次循环<br/>电压: ${param.value.toFixed(3)} V`;
        }
      },
      xAxis: {
        type: 'value',
        name: '循环圈数',
        nameLocation: 'middle',
        nameGap: 25
      },
      yAxis: {
        type: 'value',
        name: '电压 (V)',
        nameLocation: 'middle',
        nameGap: 40,
        min: 3.5,
        max: 4.0
      },
      series: [
        {
          name: '电压',
          type: 'line',
          data: voltages.map((voltage, index) => [cycles[index], voltage]),
          smooth: true,
          itemStyle: { color: '#722ed1' },
          lineStyle: { width: 2 },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(114, 46, 209, 0.3)' },
                { offset: 1, color: 'rgba(114, 46, 209, 0.05)' }
              ]
            }
          }
        }
      ]
    };
  };

  // 渲染阻抗曲线图表
  const renderImpedanceChart = (data: MonitoringData[]) => {
    if (!data || data.length === 0) return null;

    const cycles = data.map(d => d.data.cycle_number);
    const impedances = data.map(d => d.data.impedance * 1000); // 转换为mΩ

    return {
      title: {
        text: '阻抗变化曲线',
        textStyle: { fontSize: 16 }
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          const param = params[0];
          return `第${param.axisValue}次循环<br/>阻抗: ${param.value.toFixed(2)} mΩ`;
        }
      },
      xAxis: {
        type: 'value',
        name: '循环圈数',
        nameLocation: 'middle',
        nameGap: 25
      },
      yAxis: {
        type: 'value',
        name: '阻抗 (mΩ)',
        nameLocation: 'middle',
        nameGap: 40
      },
      series: [
        {
          name: '阻抗',
          type: 'line',
          data: impedances.map((impedance, index) => [cycles[index], impedance]),
          smooth: true,
          itemStyle: { color: '#fa541c' },
          lineStyle: { width: 2 }
        }
      ]
    };
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      'pending': '#faad14',
      'running': '#52c41a',
      'completed': '#1890ff',
      'failed': '#ff4d4f'
    };
    return colors[status] || '#666';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      'pending': '等待中',
      'running': '运行中',
      'completed': '已完成',
      'failed': '失败'
    };
    return texts[status] || status;
  };

  // 获取用户需求参数的中文标签
  const getChineseLabel = (key: string) => {
    const labelMap: Record<string, string> = {
      'energy_density': '能量密度',
      'power_density': '功率密度',
      'cycle_life': '循环寿命',
      'working_temperature': '工作温度',
      'safety_score': '安全性评分',
      'voltage': '电压',
      'ionic_conductivity': '离子电导率',
      'impedance': '阻抗',
      'cost_per_kwh': '每千瓦时成本'
    };
    return labelMap[key] || key;
  };

  // 获取实验特定性能数据
  const getExperimentPerformanceData = (experiment: Experiment) => {
    if (!experiment.user_requirements) {
      return [
        { name: '能量密度', value: 185, target: 200, unit: 'Wh/kg' },
        { name: '功率密度', value: 1600, target: 1500, unit: 'W/kg' },
        { name: '循环寿命', value: 950, target: 1000, unit: 'cycles' },
        { name: '安全性', value: 0.92, target: 0.9, unit: 'score' }
      ];
    }

    const requirements = experiment.user_requirements;
    const randomFactor = (experiment.id % 10) / 10; // 基于实验ID的随机因子

    // 根据用户需求生成相应的性能数据
    const data = [];

    // 能量密度
    if (requirements.energy_density) {
      const actualValue = Math.round(
        requirements.energy_density * (0.85 + randomFactor * 0.25)
      );
      data.push({
        name: '能量密度',
        value: actualValue,
        target: requirements.energy_density,
        unit: 'Wh/kg'
      });
    }

    // 功率密度
    if (requirements.power_density) {
      const actualValue = Math.round(
        requirements.power_density * (0.9 + randomFactor * 0.3)
      );
      data.push({
        name: '功率密度',
        value: actualValue,
        target: requirements.power_density,
        unit: 'W/kg'
      });
    }

    // 循环寿命
    if (requirements.cycle_life) {
      const actualValue = Math.round(
        requirements.cycle_life * (0.8 + randomFactor * 0.4)
      );
      data.push({
        name: '循环寿命',
        value: actualValue,
        target: requirements.cycle_life,
        unit: 'cycles'
      });
    }

    // 安全性
    if (requirements.safety_score) {
      const actualValue = Number(
        (requirements.safety_score * (0.9 + randomFactor * 0.15)).toFixed(3)
      );
      data.push({
        name: '安全性',
        value: actualValue,
        target: requirements.safety_score,
        unit: 'score'
      });
    }

    // 工作温度
    if (requirements.working_temperature) {
      const actualValue = Math.round(
        requirements.working_temperature * (0.8 + randomFactor * 0.4)
      );
      data.push({
        name: '工作温度',
        value: actualValue,
        target: requirements.working_temperature,
        unit: '°C'
      });
    }

    // 电压
    if (requirements.voltage) {
      const actualValue = Number(
        (requirements.voltage * (0.95 + randomFactor * 0.1)).toFixed(2)
      );
      data.push({
        name: '工作电压',
        value: actualValue,
        target: requirements.voltage,
        unit: 'V'
      });
    }

    // 电导率
    if (requirements.ionic_conductivity) {
      const actualValue = Number(
        (requirements.ionic_conductivity * (0.9 + randomFactor * 0.3)).toFixed(1)
      );
      data.push({
        name: '离子电导率',
        value: actualValue,
        target: requirements.ionic_conductivity,
        unit: 'mS/cm'
      });
    }

    // 如果没有特定需求，添加默认数据
    if (data.length === 0) {
      data.push(
        { name: '能量密度', value: 185, target: 200, unit: 'Wh/kg' },
        { name: '功率密度', value: 1600, target: 1500, unit: 'W/kg' },
        { name: '循环寿命', value: 950, target: 1000, unit: 'cycles' },
        { name: '安全性', value: 0.92, target: 0.9, unit: 'score' }
      );
    }

    return data;
  };

  // 渲染电池性能对比图表
  const renderBatteryComparisonChart = (batteryPerformances: BatteryPerformance[], formulaName: string) => {
    const completedBatteries = batteryPerformances.filter(b => b.status === 'completed');

    if (completedBatteries.length === 0) {
      return {
        title: { text: `${formulaName} - 暂无完成的电池测试数据`, left: 'center' },
        xAxis: { type: 'category', data: [] },
        yAxis: { type: 'value' },
        series: []
      };
    }

    const metrics = [
      { key: 'energy_density', name: '能量密度', unit: 'Wh/kg' },
      { key: 'power_density', name: '功率密度', unit: 'W/kg' },
      { key: 'cycle_life', name: '循环寿命', unit: 'cycles' },
      { key: 'safety_score', name: '安全性评分', unit: 'score' },
      { key: 'coulombic_efficiency', name: '库仑效率', unit: '%' }
    ];

    return {
      title: { text: `${formulaName} - 电池性能对比`, left: 'center' },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        }
      },
      legend: {
        data: completedBatteries.map(b => `电池${b.battery_number}`),
        top: 30
      },
      xAxis: {
        type: 'category',
        data: metrics.map(m => m.name),
        axisLabel: { rotate: 0 }
      },
      yAxis: { type: 'value' },
      series: completedBatteries.map(battery => ({
        name: `电池${battery.battery_number}`,
        type: 'bar',
        data: metrics.map(m => {
          const value = battery.performance_metrics[m.key as keyof typeof battery.performance_metrics];
          return m.key === 'safety_score' || m.key === 'coulombic_efficiency'
            ? Number((value as number * (m.unit === '%' ? 100 : 1)).toFixed(2))
            : value;
        }),
        barWidth: '20%',
        itemStyle: {
          borderRadius: [4, 4, 0, 0]
        }
      }))
    };
  };

  // 渲染性能图表
  const renderPerformanceChart = () => {
    if (!selectedExperiment || selectedExperiment.status !== 'completed') return null;

    const data = getExperimentPerformanceData(selectedExperiment);

    return {
      title: {
        text: '性能指标对比',
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        }
      },
      legend: {
        data: ['实际值', '目标值'],
        top: 30
      },
      xAxis: {
        type: 'category',
        data: data.map(item => item.name),
        axisLabel: { rotate: 0 }
      },
      yAxis: {
        type: 'value'
      },
      series: [
        {
          name: '实际值',
          type: 'bar',
          data: data.map(item => item.value),
          itemStyle: {
            color: '#1890ff',
            borderRadius: [4, 4, 0, 0]
          },
          barWidth: '30%'
        },
        {
          name: '目标值',
          type: 'bar',
          data: data.map(item => item.target),
          itemStyle: {
            color: '#ff4d4f',
            borderRadius: [4, 4, 0, 0]
          },
          barWidth: '30%'
        }
      ]
    };
  };

  // 过滤实验数据
  const filteredExperiments = experiments.filter(exp =>
    exp.name.toLowerCase().includes(searchText) ||
    exp.description?.toLowerCase().includes(searchText)
  );

  // 表格列定义
  const columns = [
    {
      title: '实验ID',
      dataIndex: 'experiment_id',
      key: 'experiment_id',
      width: 120,
      render: (experiment_id: string, record: Experiment) => (
        <Button type="link" onClick={() => showDetail(record)}>
          {experiment_id || `EXP-${record.id}`}
        </Button>
      )
    },
    {
      title: '实验名称',
      dataIndex: 'name',
      key: 'name',
      width: 180,
      ellipsis: true
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {getStatusText(status)}
        </Tag>
      )
    },
    {
      title: '配方数量',
      key: 'formula_count',
      width: 100,
      render: (record: Experiment) => (
        <span>
          {record.formula_count || 1} / {EXPERIMENT_FORMULA_CONSTRAINTS.MAX_FORMULAS_PER_EXPERIMENT}
          <div style={{ fontSize: '12px', color: '#666' }}>
            总计 {(record.formula_count || 1) * EXPERIMENT_FORMULA_CONSTRAINTS.COMPONENTS_PER_FORMULA} 个组分
          </div>
        </span>
      )
    },
    {
      title: '贝叶斯优化配方',
      key: 'bayesian_formulas',
      width: 150,
      render: (record: Experiment) => {
        const bayesianFormulas = record.bayesian_formulas || [];
        if (bayesianFormulas.length === 0) {
          return <span style={{ color: '#999' }}>-</span>;
        }

        return (
          <div>
            <Badge count={bayesianFormulas.length} style={{ backgroundColor: '#52c41a' }} />
            <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
              {bayesianFormulas.slice(0, 2).map((formula: any, index: number) => (
                <div key={index} style={{ marginBottom: '2px' }}>
                  {formula.name?.length > 15 ? `${formula.name.substring(0, 15)}...` : formula.name}
                </div>
              ))}
              {bayesianFormulas.length > 2 && (
                <div style={{ color: '#1890ff' }}>+{bayesianFormulas.length - 2} 更多</div>
              )}
            </div>
          </div>
        );
      }
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date: string) => new Date(date).toLocaleString()
    },
    {
      title: '持续时间',
      key: 'duration',
      width: 100,
      render: (record: Experiment) => {
        if (record.started_at && record.completed_at) {
          const duration = new Date(record.completed_at).getTime() - new Date(record.started_at).getTime();
          const hours = Math.floor(duration / 3600000);
          const minutes = Math.floor((duration % 3600000) / 60000);
          return `${hours}h ${minutes}m`;
        }
        if (record.started_at) {
          const duration = Date.now() - new Date(record.started_at).getTime();
          const hours = Math.floor(duration / 3600000);
          const minutes = Math.floor((duration % 3600000) / 60000);
          return `${hours}h ${minutes}m (进行中)`;
        }
        return '-';
      }
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (record: Experiment) => (
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
        <Title level={2}>实验记录</Title>
        <Paragraph>
          查看所有实验的执行记录，包括实验状态、性能结果和详细数据。
        </Paragraph>
      </div>

      {/* 搜索和筛选 */}
      <Card style={{ marginBottom: 24 }}>
        <Space size="large">
          <Search
            placeholder="搜索实验名称或描述"
            allowClear
            enterButton={<SearchOutlined />}
            style={{ width: 300 }}
            onSearch={handleSearch}
          />
        </Space>
      </Card>

      {/* 实验列表 */}
      <Card title="实验记录">
        <Table
          columns={columns}
          dataSource={filteredExperiments}
          rowKey="id"
          loading={loading}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`
          }}
        />
      </Card>

      {/* 实验详情模态框 */}
      <Modal
        title="实验详情"
        visible={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={1000}
      >
        {selectedExperiment && (
          <Tabs>
            <TabPane tab="基本信息" key="basic">
              <Descriptions bordered column={2}>
                <Descriptions.Item label="实验ID">
                  {selectedExperiment.experiment_id || `EXP-${selectedExperiment.id}`}
                </Descriptions.Item>
                <Descriptions.Item label="实验名称">
                  {selectedExperiment.name}
                </Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Tag color={getStatusColor(selectedExperiment.status)}>
                    {getStatusText(selectedExperiment.status)}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="配方数量">
                  {selectedExperiment.formula_count || 1} / {EXPERIMENT_FORMULA_CONSTRAINTS.MAX_FORMULAS_PER_EXPERIMENT}
                  <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                    总计 {(selectedExperiment.formula_count || 1) * EXPERIMENT_FORMULA_CONSTRAINTS.COMPONENTS_PER_FORMULA} 个组分
                  </div>
                </Descriptions.Item>
                <Descriptions.Item label="创建时间">
                  {new Date(selectedExperiment.created_at).toLocaleString()}
                </Descriptions.Item>
                <Descriptions.Item label="开始时间">
                  {selectedExperiment.started_at ?
                    new Date(selectedExperiment.started_at).toLocaleString() :
                    '未开始'
                  }
                </Descriptions.Item>
                <Descriptions.Item label="完成时间">
                  {selectedExperiment.completed_at ?
                    new Date(selectedExperiment.completed_at).toLocaleString() :
                    '未完成'
                  }
                </Descriptions.Item>
                <Descriptions.Item label="描述">
                  {selectedExperiment.description}
                </Descriptions.Item>
              </Descriptions>

              {selectedExperiment.user_requirements && (
                <Card title="用户需求" size="small" style={{ marginTop: 16 }}>
                  <Descriptions bordered column={2}>
                    {Object.entries(selectedExperiment.user_requirements).map(([key, value]) => (
                      <Descriptions.Item key={key} label={getChineseLabel(key)}>
                        {String(value)}
                      </Descriptions.Item>
                    ))}
                  </Descriptions>
                </Card>
              )}
            </TabPane>

            <TabPane tab="配方信息" key="formula">
              {experimentFormulas ? (
                <div>
                  {/* 原始配方和贝叶斯优化配方 */}
                  {experimentFormulas.original_formula && (
                    <Card
                      title={
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <span>原始配方</span>
                          <Tag color="blue">{experimentFormulas.original_formula.generation_method}</Tag>
                        </div>
                      }
                      size="small"
                      style={{ marginBottom: 16 }}
                    >
                      <Descriptions bordered column={2}>
                        <Descriptions.Item label="配方名称">
                          {experimentFormulas.original_formula.name}
                        </Descriptions.Item>
                        <Descriptions.Item label="体系类型">
                          {experimentFormulas.original_formula.system_type}
                        </Descriptions.Item>
                        <Descriptions.Item label="应用场景">
                          {experimentFormulas.original_formula.application_scenario}
                        </Descriptions.Item>
                        <Descriptions.Item label="生成方法">
                          {experimentFormulas.original_formula.generation_method}
                        </Descriptions.Item>
                        <Descriptions.Item label="配方描述" span={2}>
                          {experimentFormulas.original_formula.description || '暂无描述'}
                        </Descriptions.Item>
                      </Descriptions>
                    </Card>
                  )}

                  {/* 贝叶斯优化配方 */}
                  {experimentFormulas.optimized_formulas && experimentFormulas.optimized_formulas.length > 0 && (
                    <Card
                      title={
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <span>贝叶斯优化配方</span>
                          <div>
                            <Badge count={experimentFormulas.optimized_formulas.length} style={{ backgroundColor: '#52c41a' }} />
                            <Tag color="green" style={{ marginLeft: 8 }}>bayesian_opt</Tag>
                          </div>
                        </div>
                      }
                      size="small"
                      style={{ marginBottom: 16 }}
                    >
                      <Row gutter={16} style={{ marginBottom: 16 }}>
                        {experimentFormulas.optimized_formulas.map((formula: any, index: number) => (
                          <Col span={8} key={formula.id}>
                            <Card
                              size="small"
                              style={{
                                border: selectedFormula?.id === formula.id ? '2px solid #52c41a' : '1px solid #d9d9d9',
                                backgroundColor: selectedFormula?.id === formula.id ? '#f6ffed' : '#fff'
                              }}
                              hoverable
                              onClick={() => setSelectedFormula(formula)}
                            >
                              <div style={{ textAlign: 'center' }}>
                                <Tag color="green" style={{ marginBottom: 8 }}>优化配方 {index + 1}</Tag>
                                <div style={{ fontWeight: 'bold', marginBottom: 8 }}>{formula.name}</div>
                                <div style={{ fontSize: '12px', color: '#666' }}>
                                  <div>体系：{formula.system_type}</div>
                                  <div>场景：{formula.application_scenario}</div>
                                  <div>置信度：{(formula.confidence_score * 100).toFixed(1)}%</div>
                                  <div>方法：{formula.generation_method}</div>
                                </div>
                                {formula.user_requirements && Object.keys(formula.user_requirements).length > 0 && (
                                  <div style={{ marginTop: 8, padding: '4px', backgroundColor: '#f0f8ff', borderRadius: '4px' }}>
                                    <div style={{ fontSize: '11px', color: '#1890ff', fontWeight: 'bold' }}>用户需求：</div>
                                    {Object.entries(formula.user_requirements).slice(0, 2).map(([key, value]) => (
                                      <div key={key} style={{ fontSize: '10px', color: '#666' }}>
                                        {getChineseLabel(key)}: {String(value)}
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </Card>
                          </Col>
                        ))}
                      </Row>
                    </Card>
                  )}

                  {/* 选中配方的详细信息 */}
                  {selectedFormula && (
                    <div>
                      {/* 配方基本信息 */}
                      <Descriptions bordered column={2}>
                        <Descriptions.Item label="配方ID">
                          {selectedFormula.id}
                        </Descriptions.Item>
                        <Descriptions.Item label="配方名称">
                          {selectedFormula.name}
                        </Descriptions.Item>
                        <Descriptions.Item label="体系类型">
                          <Tag color="blue">
                            {selectedFormula.system_type}
                          </Tag>
                        </Descriptions.Item>
                        <Descriptions.Item label="应用场景">
                          {selectedFormula.application_scenario}
                        </Descriptions.Item>
                        <Descriptions.Item label="生成方法">
                          <Tag color="green">
                            {selectedFormula.generation_method}
                          </Tag>
                        </Descriptions.Item>
                        {selectedFormula.confidence_score && (
                          <Descriptions.Item label="置信度">
                            {(selectedFormula.confidence_score * 100).toFixed(1)}%
                          </Descriptions.Item>
                        )}
                        {selectedFormula.optimization_method && (
                          <Descriptions.Item label="优化方法">
                            {selectedFormula.optimization_method}
                          </Descriptions.Item>
                        )}
                        <Descriptions.Item label="创建时间">
                          {new Date(selectedFormula.created_at).toLocaleString()}
                        </Descriptions.Item>
                        <Descriptions.Item label="配方描述" span={2}>
                          {selectedFormula.description || '暂无描述'}
                        </Descriptions.Item>
                      </Descriptions>

                      {/* 溶剂比例信息（贝叶斯优化配方特有） */}
                      {selectedFormula.solvent_ratios && Object.keys(selectedFormula.solvent_ratios).length > 0 && (
                        <Card title="溶剂比例信息" size="small" style={{ marginTop: 16 }}>
                          <Row gutter={[8, 8]}>
                            {Object.entries(selectedFormula.solvent_ratios)
                              .sort(([, a], [, b]) => (b as number) - (a as number))
                              .slice(0, 12)
                              .map(([solvent, ratio]) => (
                              <Col span={6} key={solvent}>
                                <div style={{
                                  padding: '8px',
                                  backgroundColor: '#f0f2f5',
                                  borderRadius: '6px',
                                  textAlign: 'center',
                                  border: '1px solid #d9d9d9'
                                }}>
                                  <div style={{ fontWeight: 'bold', fontSize: '12px', color: '#1890ff' }}>
                                    {solvent}
                                  </div>
                                  <div style={{ fontSize: '14px', fontWeight: 'bold', marginTop: '4px' }}>
                                    {((ratio as number) * 100).toFixed(1)}%
                                  </div>
                                </div>
                              </Col>
                            ))}
                          </Row>
                        </Card>
                      )}

                      {/* 预测性能（贝叶斯优化配方特有） */}
                      {selectedFormula.predicted_properties && Object.keys(selectedFormula.predicted_properties).length > 0 && (
                        <Card title="预测性能" size="small" style={{ marginTop: 16 }}>
                          <Descriptions bordered column={2}>
                            {Object.entries(selectedFormula.predicted_properties).map(([key, value]) => (
                              <Descriptions.Item key={key} label={getChineseLabel(key)}>
                                {typeof value === 'number' ? value.toFixed(2) : String(value)}
                              </Descriptions.Item>
                            ))}
                          </Descriptions>
                        </Card>
                      )}

                      {/* 用户需求（贝叶斯优化配方特有） */}
                      {selectedFormula.user_requirements && Object.keys(selectedFormula.user_requirements).length > 0 && (
                        <Card title="用户需求" size="small" style={{ marginTop: 16 }}>
                          <Descriptions bordered column={2}>
                            {Object.entries(selectedFormula.user_requirements).map(([key, value]) => (
                              <Descriptions.Item key={key} label={getChineseLabel(key)}>
                                {String(value)}
                              </Descriptions.Item>
                            ))}
                          </Descriptions>
                        </Card>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <div>
                  <Text type="secondary">暂无配方信息</Text>
                </div>
              )}
            </TabPane>

            <TabPane tab="性能结果" key="performance">
              {selectedExperiment.battery_performances && selectedExperiment.battery_performances.length > 0 ? (
                <div>
                  {/* 配方选择和概览 */}
                  <Card size="small" style={{ marginBottom: 16 }}>
                    <Row justify="space-between" align="middle">
                      <Col>
                        <Text strong>配方选择：</Text>
                        <Select
                          value={selectedFormula?.id || (selectedExperiment.formulas && selectedExperiment.formulas[0]?.id)}
                          onChange={(formulaId) => {
                            const formula = selectedExperiment.formulas?.find(f => f.id === formulaId) || null;
                            setSelectedFormula(formula);
                          }}
                          style={{ width: 300, marginLeft: 12 }}
                          placeholder="选择要查看的配方性能"
                        >
                          {selectedExperiment.formulas?.map((formula, index) => {
                            const formulaBatteries = selectedExperiment.battery_performances?.filter(b => b.formula_id === formula.id) || [];
                            const completedCount = formulaBatteries.filter(b => b.status === 'completed').length;
                            return (
                              <Select.Option key={formula.id} value={formula.id}>
                                {formula.name} ({completedCount}/{formulaBatteries.length} 电池完成)
                              </Select.Option>
                            );
                          })}
                        </Select>
                      </Col>
                      <Col>
                        <Space>
                          <Badge count={selectedExperiment.formulas?.length || 0} style={{ backgroundColor: '#52c41a' }}>
                            <Tag color="blue">配方数量</Tag>
                          </Badge>
                          <Badge count={selectedExperiment.battery_performances?.length || 0} style={{ backgroundColor: '#1890ff' }}>
                            <Tag color="green"><ExperimentOutlined /> 电池总数</Tag>
                          </Badge>
                        </Space>
                      </Col>
                    </Row>
                  </Card>

                  {/* 配方概览卡片 */}
                  <Row gutter={16} style={{ marginBottom: 16 }}>
                    {selectedExperiment.formulas?.map((formula, index) => {
                      const formulaBatteries = selectedExperiment.battery_performances?.filter(b => b.formula_id === formula.id) || [];
                      const completedCount = formulaBatteries.filter(b => b.status === 'completed').length;
                      const avgScore = completedCount > 0
                        ? formulaBatteries
                            .filter(b => b.status === 'completed')
                            .reduce((sum, b) => sum + b.quality_assessment.overall_score, 0) / completedCount
                        : 0;

                      return (
                        <Col span={8} key={formula.id}>
                          <Card
                            size="small"
                            style={{
                              border: selectedFormula?.id === formula.id ? '2px solid #1890ff' : '1px solid #d9d9d9',
                              backgroundColor: selectedFormula?.id === formula.id ? '#f6ffed' : '#fff'
                            }}
                            hoverable
                            onClick={() => setSelectedFormula(formula)}
                          >
                            <div style={{ textAlign: 'center' }}>
                              <Tag color="blue" style={{ marginBottom: 8 }}>配方 {index + 1}</Tag>
                              <div style={{ fontWeight: 'bold', marginBottom: 8 }}>{formula.name}</div>
                              <Row gutter={8}>
                                <Col span={12}>
                                  <Statistic
                                    title="电池进度"
                                    value={completedCount}
                                    suffix={`/${formulaBatteries.length}`}
                                    valueStyle={{ fontSize: '16px', color: '#1890ff' }}
                                  />
                                </Col>
                                <Col span={12}>
                                  <Statistic
                                    title="平均评分"
                                    value={avgScore}
                                    precision={1}
                                    suffix="分"
                                    valueStyle={{ fontSize: '16px', color: '#52c41a' }}
                                  />
                                </Col>
                              </Row>
                            </div>
                          </Card>
                        </Col>
                      );
                    })}
                  </Row>

                  {/* 选中配方的电池性能详情 */}
                  {selectedFormula && (() => {
                    const formulaBatteries = selectedExperiment.battery_performances?.filter(b => b.formula_id === selectedFormula.id) || [];

                    return (
                      <div>
                        {/* 电池性能概览图表 */}
                        {formulaBatteries.some(b => b.status === 'completed') && (
                          <Card title={`${selectedFormula.name} - 电池性能对比`} size="small" style={{ marginBottom: 16 }}>
                            <ReactECharts
                              option={renderBatteryComparisonChart(formulaBatteries, selectedFormula.name)}
                              style={{ height: '350px' }}
                            />
                          </Card>
                        )}

                        {/* 电池性能详细表格 */}
                        <Card title={`${selectedFormula.name} - 电池详细性能数据`} size="small">
                          <Table
                            dataSource={formulaBatteries}
                            rowKey="id"
                            pagination={false}
                            size="small"
                            columns={[
                              {
                                title: '电池编号',
                                dataIndex: 'battery_number',
                                key: 'battery_number',
                                width: 80,
                                render: (num: number) => (
                                  <Tag color="blue" icon={<ExperimentOutlined />}>
                                    电池{num}
                                  </Tag>
                                )
                              },
                              {
                                title: '状态',
                                dataIndex: 'status',
                                key: 'status',
                                width: 100,
                                render: (status: string) => {
                                  const statusConfig = {
                                    'completed': { color: 'success', text: '已完成' },
                                    'testing': { color: 'processing', text: '测试中' },
                                    'pending': { color: 'warning', text: '等待中' },
                                    'failed': { color: 'error', text: '失败' }
                                  };
                                  const config = statusConfig[status] || { color: 'default', text: status };
                                  return <Tag color={config.color}>{config.text}</Tag>;
                                }
                              },
                              {
                                title: '能量密度',
                                dataIndex: ['performance_metrics', 'energy_density'],
                                key: 'energy_density',
                                width: 100,
                                render: (value: number) => `${value || '-'} Wh/kg`
                              },
                              {
                                title: '功率密度',
                                dataIndex: ['performance_metrics', 'power_density'],
                                key: 'power_density',
                                width: 100,
                                render: (value: number) => `${value || '-'} W/kg`
                              },
                              {
                                title: '循环寿命',
                                dataIndex: ['performance_metrics', 'cycle_life'],
                                key: 'cycle_life',
                                width: 100,
                                render: (value: number) => `${value || '-'} cycles`
                              },
                              {
                                title: '安全性评分',
                                dataIndex: ['performance_metrics', 'safety_score'],
                                key: 'safety_score',
                                width: 100,
                                render: (value: number) => value ? value.toFixed(3) : '-'
                              },
                              {
                                title: '综合评分',
                                dataIndex: ['quality_assessment', 'overall_score'],
                                key: 'overall_score',
                                width: 100,
                                render: (value: number, record: BatteryPerformance) => {
                                  if (!value && record.status !== 'completed') return '-';
                                  return (
                                    <Progress
                                      percent={value}
                                      size="small"
                                      status={value >= 85 ? 'success' : value >= 70 ? 'active' : 'exception'}
                                      format={() => `${value}分`}
                                    />
                                  );
                                }
                              },
                              {
                                title: '可靠性等级',
                                dataIndex: ['quality_assessment', 'reliability_rating'],
                                key: 'reliability_rating',
                                width: 100,
                                render: (rating: string) => {
                                  if (!rating) return '-';
                                  const ratingConfig = {
                                    'A': { color: 'success', text: 'A级' },
                                    'B': { color: 'processing', text: 'B级' },
                                    'C': { color: 'warning', text: 'C级' },
                                    'D': { color: 'error', text: 'D级' },
                                    'F': { color: 'error', text: 'F级' }
                                  };
                                  const config = ratingConfig[rating] || { color: 'default', text: rating };
                                  return <Tag color={config.color}>{config.text}</Tag>;
                                }
                              }
                            ]}
                            expandable={{
                              expandedRowRender: (record: BatteryPerformance) => (
                                <div style={{ margin: 0, padding: '16px', backgroundColor: '#fafafa' }}>
                                  <Row gutter={16}>
                                    <Col span={12}>
                                      <Card size="small" title="电化学性能">
                                        <Space direction="vertical" style={{ width: '100%' }}>
                                          <div><Text strong>库仑效率：</Text>{record.performance_metrics.coulombic_efficiency?.toFixed(2)}%</div>
                                          <div><Text strong>阻抗：</Text>{record.performance_metrics.impedance?.toFixed(2)} mΩ</div>
                                          <div><Text strong>离子电导率：</Text>{record.performance_metrics.ionic_conductivity?.toFixed(2)} mS/cm</div>
                                          <div><Text strong>电压保持率：</Text>{record.performance_metrics.voltage_retention?.toFixed(2)}%</div>
                                          <div><Text strong>容量保持率：</Text>{record.performance_metrics.capacity_retention?.toFixed(2)}%</div>
                                        </Space>
                                      </Card>
                                    </Col>
                                    <Col span={12}>
                                      <Card size="small" title="测试信息">
                                        <Space direction="vertical" style={{ width: '100%' }}>
                                          <div><Text strong>操作员：</Text>{record.test_metadata.operator}</div>
                                          <div><Text strong>开始时间：</Text>{new Date(record.test_metadata.test_start_time).toLocaleString()}</div>
                                          {record.test_metadata.test_completion_time && (
                                            <div><Text strong>完成时间：</Text>{new Date(record.test_metadata.test_completion_time).toLocaleString()}</div>
                                          )}
                                          {record.test_metadata.test_duration_hours && (
                                            <div><Text strong>测试时长：</Text>{record.test_metadata.test_duration_hours}小时</div>
                                          )}
                                          <div><Text strong>一致性评分：</Text>{record.quality_assessment.consistency_score?.toFixed(2)}%</div>
                                        </Space>
                                      </Card>
                                    </Col>
                                  </Row>
                                  {record.test_data?.safety_tests && (
                                    <Card size="small" title="安全测试结果" style={{ marginTop: 16 }}>
                                      <Row gutter={16}>
                                        <Col span={6}><Text strong>过充测试：</Text>{record.test_data.safety_tests.overcharge_test ? '✅ 通过' : '❌ 失败'}</Col>
                                        <Col span={6}><Text strong>短路测试：</Text>{record.test_data.safety_tests.short_circuit_test ? '✅ 通过' : '❌ 失败'}</Col>
                                        <Col span={6}><Text strong>热失控测试：</Text>{record.test_data.safety_tests.thermal_runaway_test ? '✅ 通过' : '❌ 失败'}</Col>
                                        <Col span={6}><Text strong>针刺测试：</Text>{record.test_data.safety_tests.nail_penetration_test ? '✅ 通过' : '❌ 失败'}</Col>
                                      </Row>
                                    </Card>
                                  )}
                                </div>
                              ),
                            }}
                          />
                        </Card>
                      </div>
                    );
                  })()}
                </div>
              ) : selectedExperiment.status === 'completed' ? (
                // 兼容旧的单配方展示方式
                <div>
                  <Card title="性能指标对比" size="small" style={{ marginBottom: 16 }}>
                    <ReactECharts option={renderPerformanceChart()} style={{ height: '300px' }} />
                  </Card>

                  <Card title="详细性能数据" size="small">
                    <Table
                      dataSource={getExperimentPerformanceData(selectedExperiment).map(item => ({
                        ...item,
                        achievement: Number(((item.value / item.target) * 100).toFixed(1))
                      }))}
                      rowKey="name"
                      pagination={false}
                      size="small"
                      columns={[
                        { title: '性能指标', dataIndex: 'name', key: 'name' },
                        { title: '实际值', dataIndex: 'value', key: 'value',
                          render: (value: number, record: any) => `${value} ${record.unit}` },
                        { title: '目标值', dataIndex: 'target', key: 'target',
                          render: (value: number, record: any) => `${value} ${record.unit}` },
                        { title: '达成率', dataIndex: 'achievement', key: 'achievement',
                          render: (value: number) => (
                            <Progress
                              percent={Math.min(150, Math.max(0, value))}
                              size="small"
                              status={value >= 100 ? 'success' : value >= 80 ? 'active' : 'exception'}
                              format={() => `${value.toFixed(1)}%`}
                            />
                          )
                        }
                      ]}
                    />
                  </Card>
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
                  {selectedExperiment.status === 'running' ? '实验进行中，暂无完整性能数据' : '实验尚未完成，暂无性能数据'}
                </div>
              )}
            </TabPane>

            <TabPane tab="实验过程" key="process">
              <Timeline>
                <Timeline.Item color="blue">
                  实验创建 - {new Date(selectedExperiment.created_at).toLocaleString()}
                </Timeline.Item>
                {selectedExperiment.started_at && (
                  <Timeline.Item color="green">
                    实验开始 - {new Date(selectedExperiment.started_at).toLocaleString()}
                  </Timeline.Item>
                )}
                {selectedExperiment.status === 'running' && (
                  <Timeline.Item color="blue" dot={<Spin size="small" />}>
                    实验进行中 - 当前正在执行测试阶段
                  </Timeline.Item>
                )}
                {selectedExperiment.completed_at && (
                  <Timeline.Item
                    color={selectedExperiment.status === 'completed' ? 'green' : 'red'}
                  >
                    实验结束 - {new Date(selectedExperiment.completed_at).toLocaleString()}
                    <div style={{ marginTop: 4 }}>
                      状态: <Tag color={getStatusColor(selectedExperiment.status)}>
                        {getStatusText(selectedExperiment.status)}
                      </Tag>
                    </div>
                  </Timeline.Item>
                )}
              </Timeline>
            </TabPane>

            <TabPane tab="监控数据" key="monitoring">
              <Spin spinning={monitoringLoading}>
                {selectedFormula ? (
                  <RealTimeMonitoringWrapper
                    experimentId={selectedExperiment?.id || 0}
                    formulaId={selectedFormula.id}
                    onDataUpdate={(newData) => {
                      setFormulaMonitoringData(prev => ({
                        ...prev,
                        [selectedFormula.id]: newData
                      }));
                    }}
                  >
                    {({ isConnected, lastUpdate, reconnect, hasRealTimeData }) => (
                      <div>
                        {/* 实时连接状态指示器 */}
                        <Alert
                          message={
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                              <span>
                                实时监控状态: {isConnected ? '已连接' : '未连接'}
                                {hasRealTimeData && <Tag color="green" style={{ marginLeft: 8 }}>实时数据</Tag>}
                              </span>
                              <div>
                                {lastUpdate && (
                                  <span style={{ marginRight: 16, fontSize: '12px', color: '#666' }}>
                                    最后更新: {new Date(lastUpdate).toLocaleTimeString()}
                                  </span>
                                )}
                                {!isConnected && (
                                  <Button size="small" type="primary" onClick={reconnect}>
                                    重新连接
                                  </Button>
                                )}
                              </div>
                            </div>
                          }
                          type={isConnected ? 'success' : 'warning'}
                          style={{ marginBottom: 16 }}
                          showIcon
                        />
                    {/* 当前选择的配方信息 */}
                    <Card size="small" style={{ marginBottom: 16 }}>
                      <Descriptions size="small" column={2}>
                        <Descriptions.Item label="配方名称">
                          <strong>{selectedFormula.name}</strong>
                        </Descriptions.Item>
                        <Descriptions.Item label="配方ID">
                          #{selectedFormula.id}
                        </Descriptions.Item>
                        <Descriptions.Item label="体系类型">
                          <Tag color="blue">{selectedFormula.system_type}</Tag>
                        </Descriptions.Item>
                        <Descriptions.Item label="应用场景">
                          {selectedFormula.application_scenario}
                        </Descriptions.Item>
                        <Descriptions.Item label="生成方法" span={2}>
                          <Tag color={selectedFormula.generation_method === 'initial_design' ? 'blue' : 'green'}>
                            {selectedFormula.generation_method}
                          </Tag>
                        </Descriptions.Item>
                      </Descriptions>
                    </Card>

                    {/* 监控数据图表 */}
                    <Row gutter={16}>
                      <Col span={24}>
                        <Card title="充放电性能曲线" size="small">
                          <ReactECharts
                            option={renderChargeDischargeChart(formulaMonitoringData[selectedFormula.id] || [])}
                            style={{ height: '400px' }}
                          />
                        </Card>
                      </Col>
                    </Row>

                    <Row gutter={16} style={{ marginTop: 16 }}>
                      <Col span={12}>
                        <Card title="电压变化曲线" size="small">
                          <ReactECharts
                            option={renderVoltageChart(formulaMonitoringData[selectedFormula.id] || [])}
                            style={{ height: '300px' }}
                          />
                        </Card>
                      </Col>
                      <Col span={12}>
                        <Card title="阻抗变化曲线" size="small">
                          <ReactECharts
                            option={renderImpedanceChart(formulaMonitoringData[selectedFormula.id] || [])}
                            style={{ height: '300px' }}
                          />
                        </Card>
                      </Col>
                    </Row>

                    {/* 关键性能指标 */}
                    {formulaMonitoringData[selectedFormula.id] && formulaMonitoringData[selectedFormula.id].length > 0 && (
                      <Row gutter={16} style={{ marginTop: 16 }}>
                        <Col span={6}>
                          <Card size="small">
                            <Statistic
                              title="总循环数"
                              value={formulaMonitoringData[selectedFormula.id].length}
                              suffix="次"
                            />
                          </Card>
                        </Col>
                        <Col span={6}>
                          <Card size="small">
                            <Statistic
                              title="初始容量"
                              value={formulaMonitoringData[selectedFormula.id][0].data.charge_capacity}
                              precision={1}
                              suffix="mAh"
                            />
                          </Card>
                        </Col>
                        <Col span={6}>
                          <Card size="small">
                            <Statistic
                              title="当前容量"
                              value={formulaMonitoringData[selectedFormula.id][formulaMonitoringData[selectedFormula.id].length - 1].data.discharge_capacity}
                              precision={1}
                              suffix="mAh"
                            />
                          </Card>
                        </Col>
                        <Col span={6}>
                          <Card size="small">
                            <Statistic
                              title="容量保持率"
                              value={((formulaMonitoringData[selectedFormula.id][formulaMonitoringData[selectedFormula.id].length - 1].data.discharge_capacity / formulaMonitoringData[selectedFormula.id][0].data.charge_capacity) * 100)}
                              precision={1}
                              suffix="%"
                            />
                          </Card>
                        </Col>
                      </Row>
                    )}
                    </div>
                    )}
                  </RealTimeMonitoringWrapper>
                ) : (
                  <Alert
                    message="请先选择一个配方"
                    description="在'配方信息'标签页中点击选择一个配方，然后在此查看其监控数据。"
                    type="info"
                    showIcon
                    style={{ marginTop: 16 }}
                  />
                )}
              </Spin>
            </TabPane>
          </Tabs>
        )}
      </Modal>
    </div>
  );
};

export default ExperimentListPage;