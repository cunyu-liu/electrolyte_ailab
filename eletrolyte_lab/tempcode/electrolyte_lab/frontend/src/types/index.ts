// 实验和配方映射关系常量
export const EXPERIMENT_FORMULA_CONSTRAINTS = {
  MAX_FORMULAS_PER_EXPERIMENT: 64,  // 一次实验最多64个配方
  COMPONENTS_PER_FORMULA: 10        // 每个配方固定10个组分
} as const;

// 基础类型定义
export interface BaseEntity {
  id: number;
  created_at: string;
  updated_at?: string;
}

// 配方相关类型 - 每个配方固定包含10个组分
export interface Formula extends BaseEntity {
  name: string;
  description: string;
  system_type: '正极' | '负极' | '电解液';
  application_scenario?: string;
  predicted_properties?: Record<string, any>;
  generation_method: 'initial_design' | 'bayesian_opt' | 'redesign';
  source_data?: Record<string, any>;
  confidence_score?: number; // 贝叶斯优化配方的置信度
  user_requirements?: Record<string, any>; // 用户需求（贝叶斯优化配方特有）
  solvent_ratios?: Record<string, number>; // 溶剂比例（贝叶斯优化配方特有）
  components: Component[]; // 固定10个组分
  // 配方完整性验证
  component_validation?: {
    expected_count: number;      // 期望组分数量：10
    actual_count: number;        // 实际组分数量
    is_valid: boolean;           // 是否符合10个组分规则
    missing_components?: string[]; // 缺失的组分类型
    extra_components?: string[];   // 多余的组分
  };
  // API返回的额外字段
  predicted_performance?: {
    energy_density: number;
    power_density: number;
    cycle_life: number;
    safety_score: number;
    stability_score: number;
    cost_per_kwh: number;
    additional_metrics?: {
      ionic_conductivity: number;
      viscosity: number;
      flash_point: number;
      coulombic_efficiency: number;
    };
  };
  preparation_steps?: Array<{
    step: number;
    operation: string;
    description: string;
    conditions: string;
    duration: string;
    critical_parameters: string[];
  }>;
  quality_metrics?: {
    overall_score: number;
    confidence_level: number;
    readiness_level: string;
    risk_assessment: {
      technical_risk: string;
      scalability_risk: string;
      cost_risk: string;
      regulatory_risk: string;
    };
    validation_status: string;
  };
  optimization_method?: string;
  optimization_details?: any;
}

export interface Component {
  id: number;
  formula_id: number;
  component_type: 'solvent' | 'salt' | 'additive';
  name: string;
  chemical_formula: string;
  concentration?: number;
  percentage?: number;  // API返回的百分比浓度字段
  unit?: string;
  properties?: Record<string, any>;
  source: string;
  role?: string;  // 组分作用描述
  created_at: string;
}

// 实验相关类型 - 一次实验可以测试多个配方
export interface Experiment extends BaseEntity {
  experiment_id: string; // 实验唯一标识，如 EXP-20241201-001
  name: string;
  description?: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  experiment_type: 'screening' | 'optimization' | 'validation';
  user_requirements?: Record<string, any>;
  started_at?: string;
  completed_at?: string;
  // 实验与配方的关系：1个实验 : 多个配方 (最多64个)
  experiment_formulas?: ExperimentFormula[];
  formulas?: Formula[]; // 该实验包含的所有配方（扩展字段，包含完整的配方信息）
  formula_count?: number; // 该实验包含的配方数量，最多64个
  formula_id?: number; // 单一配方ID（用于兼容性）

  // 电池性能数据 - 每个配方对应3个电池
  battery_performances?: BatteryPerformance[];
  // 配方映射统计信息
  formula_stats?: {
    total_formulas: number;          // 实验包含的配方总数 (≤64)
    total_components: number;         // 实验包含的组分总数 (= formula_count * 10)
    component_violations?: Array<{    // 违反10个组分规则的配方
      formula_id: number;
      component_count: number;
      formula_name: string;
    }>;
  };
  results?: ExperimentResult[];
  // 贝叶斯优化配方相关字段
  bayesian_formulas?: any[]; // 该实验关联的贝叶斯优化配方
  all_bayesian_formulas?: any[]; // 所有贝叶斯优化配方
  experiment_data?: {
    formula_info: {
      formula_name: string;
      components: Array<{
        name: string;
        type: string;
        ratio?: string;
        concentration?: string;
        percentage?: string;
        loading?: string;
      }>;
    };
    injection_data: {
      injection_volume: number;
      injection_pressure: number;
      wetting_time: number;
      retention_rate: number;
    };
    impedance_data: {
      initial_impedance: number;
      impedance_growth: number;
      charge_transfer_resistance: number;
      warburg_impedance: number;
    };
    voltage_data: {
      nominal_voltage: number;
      cut_off_voltage_charge: number;
      cut_off_voltage_discharge: number;
      voltage_hysteresis: number;
    };
    charge_discharge_curves: Array<{
      cycle: number;
      charge_capacity: number;
      discharge_capacity: number;
      efficiency: number;
    }>;
  };
}

export interface ExperimentResult extends BaseEntity {
  experiment_id: number;
  formula_id?: number; // 关联的配方ID
  battery_id?: number; // 电池ID (1-3 per formulation)
  result_type: string;
  data: Record<string, any>;
  metadata?: Record<string, any>;
}

// 电池性能数据类型 - 每个配方注入到3个电池中进行测试
export interface BatteryPerformance {
  id: number;
  formula_id: number;
  battery_number: number; // 电池编号: 1, 2, 3
  status: 'pending' | 'testing' | 'completed' | 'failed';

  // 基础性能指标
  performance_metrics: {
    energy_density: number;      // 能量密度 (Wh/kg)
    power_density: number;       // 功率密度 (W/kg)
    cycle_life: number;          // 循环寿命 (cycles)
    safety_score: number;        // 安全性评分 (0-1)
    coulombic_efficiency: number; // 库仑效率 (%)

    // 电化学性能
    impedance: number;           // 阻抗 (mΩ)
    ionic_conductivity: number;  // 离子电导率 (mS/cm)

    // 环境适应性
    working_temperature_range: {
      min: number;               // 最低工作温度 (°C)
      max: number;               // 最高工作温度 (°C)
    };

    // 稳定性指标
    voltage_retention: number;   // 电压保持率 (%)
    capacity_retention: number;  // 容量保持率 (%)

    // 成本指标
    cost_per_kwh: number;        // 每千瓦时成本 ($)
  };

  // 详细测试数据
  test_data?: {
    charge_discharge_cycles: Array<{
      cycle: number;
      charge_capacity: number;
      discharge_capacity: number;
      efficiency: number;
      voltage_curve?: number[];
    }>;

    impedance_analysis: {
      initial_impedance: number;
      impedance_growth: number;
      charge_transfer_resistance: number;
    };

    temperature_performance: Array<{
      temperature: number;
      performance_retention: number;
    }>;

    safety_tests: {
      overcharge_test: boolean;
      short_circuit_test: boolean;
      thermal_runaway_test: boolean;
      nail_penetration_test: boolean;
    };
  };

  // 测试元数据
  test_metadata: {
    test_start_time: string;
    test_completion_time?: string;
    test_duration_hours?: number;
    test_conditions: {
      temperature: number;
      humidity: number;
      pressure: number;
    };
    equipment_used: string[];
    operator?: string;
  };

  // 质量评估
  quality_assessment: {
    overall_score: number;           // 综合评分 (0-100)
    reliability_rating: 'A' | 'B' | 'C' | 'D' | 'F';
    consistency_score?: number;      // 与同配方其他电池的一致性评分
    pass_criteria_met: boolean;      // 是否通过测试标准
    failure_reasons?: string[];      // 失败原因（如果有）
  };

  created_at: string;
  updated_at?: string;
}

// 实验配方关系表 - 定义实验与配方的多对多关系
export interface ExperimentFormula extends BaseEntity {
  experiment_id: number; // 关联的实验ID
  formula_id: number; // 关联的配方ID
  position_in_experiment: number; // 在该实验中的位置（1-64）
  test_priority: 'high' | 'medium' | 'low'; // 测试优先级
  test_status: 'pending' | 'testing' | 'completed' | 'failed';
  test_parameters?: Record<string, any>; // 该配方的特定测试参数
  test_results?: {
    performance_score?: number;
    stability_score?: number;
    cost_efficiency?: number;
    notes?: string;
  };
  formula?: Formula; // 关联的配方信息
}

// AI设计员相关类型
export interface ParsedParameters {
  basic_info: {
    [x: string]: any;
    system_type: ParameterDefinition & {
      material_name?: string;
      both_materials?: {
        positive: string;
        negative: string;
      };
    };
    application_scenario: ParameterDefinition;
    experiment_name: ParameterDefinition;
  };
  performance_params: Record<string, ParameterDefinition>;
  safety_requirements?: Record<string, ParameterDefinition>;
  cost_constraints?: Record<string, ParameterDefinition>;
  metadata: {
    original_input: string;
    parsing_timestamp: string;
    total_confidence: number;
    missing_required: string[];
    warnings: string[];
  };
}

export interface ParameterDefinition {
  key?: string;
  label: string;
  value: any;
  type?: 'select' | 'number' | 'rating' | 'text' | 'boolean';
  required?: boolean;
  unit?: string;
  min?: number;
  max?: number;
  options?: string[];
  description?: string;
  confidence?: number;
  source?: string; // 添加source字段
  material_name?: string; // 材料名称，如NCM811, Si/C等
  both_materials?: {
    positive: string; // 正极材料名称
    negative: string; // 负极材料名称
  }; // 同时包含正负极材料信息
  paramKey?: string; // 参数键名
  category?: string; // 参数类别
}

export interface ParameterItem {
  category: string;
  name: string;
  value: any;
  type: string;
  required: boolean;
  options?: string[];
  unit?: string;
  min?: number;
  max?: number;
}

export interface FormulaDataset {
  original_formulas: Record<string, any>[];
  augmented_formulas: Record<string, any>[];
  total_count: number;
  source_parameters: Record<string, any>;
  generation_timestamp: string;
  generation_method?: string;
  quality_metrics?: {
    average_confidence: number;
    high_confidence_count: number;
    parameter_match_score?: number;
  };
  // 文献挖掘与数据扩增相关字段
  literature_results?: any[];
  text_mining_results?: any;
  molecule_generation_results?: any;
  metadata?: {
    total_literature?: number;
    total_molecules?: number;
    text_mined_molecules?: number;
    generated_molecules?: number;
    processing_method?: string;
    literature_match_success?: boolean;
    text_mining_success?: boolean;
    molecule_generation_success?: boolean;
    literature_error?: string;
    text_mining_error?: string;
    molecule_generation_error?: string;
    processing_details?: {
      bm25_search_used?: boolean;
      chemmind_used?: boolean;
      isomers_used?: boolean;
      fallback_used?: boolean;
    };
  };
}

export interface PredictedData {
  [x: string]: any;
  total_predictions: number;
  selected_count: number;
  predicted_formulas: PredictedFormula[];
  selection_criteria: string;
  prediction_timestamp: string;
  model_info: {
    model_type: string;
    prediction_accuracy: string;
    features_used: string[];
  };
  prediction_summary?: {
    average_confidence: number;
    prediction_method: string;
    optimization_results: Record<string, any>;
  };
}

export interface PredictedFormula {
  formula_index: number;
  formula: Record<string, any>;
  molecular_properties: Record<string, any>;
  system_properties: Record<string, any>;
  overall_score: number;
  prediction_confidence: number;
}

// AI实验员相关类型
export interface MonitoringData {
  experiment_id: number;
  data_type: string;
  data: Record<string, any>;
  total_points: number;
}

export interface ExperimentStatus {
  session_info: {
    experiment_id: number;
    status: string;
    start_time: number;
    runtime_seconds: number;
    data_points_collected: number;
    last_update: number;
  };
  latest_data: Record<string, any>;
  buffer_status: Record<string, number>;
}

// 闭环优化相关类型
export interface EvaluationResult {
  experiment_id: number;
  evaluation_timestamp: string;
  performance_metrics: Record<string, number>;
  metric_evaluations: Record<string, MetricEvaluation>;
  overall_evaluation: {
    overall_score: number;
    overall_grade: string;
    meets_requirements: boolean;
    critical_failures: string[];
    metrics_summary: {
      total_metrics: number;
      metrics_meeting_requirements: number;
      critical_metrics_failing: number;
    };
  };
  failure_analysis?: FailureAnalysis;
  improvement_suggestions: ImprovementSuggestion[];
  evaluation_summary: {
    meets_requirements: boolean;
    overall_score: number;
    critical_issues: string[];
    recommended_action: string;
  };
}

export interface MetricEvaluation {
  chinese_name: string;
  target_value: number;
  actual_value: number;
  achievement_rate: number;
  grade: 'excellent' | 'good' | 'acceptable' | 'poor';
  meets_requirement: boolean;
  unit?: string;
  weight: number;
}

export interface FailureAnalysis {
  critical_issues: string[];
  all_failing_metrics: string[];
  root_cause_analysis: Record<string, {
    shortfall: number;
    percentage_shortfall: number;
    possible_causes: string[];
    severity: string;
  }>;
  impact_assessment: Record<string, {
    impact_level: string;
    affected_applications: string[];
    business_impact: string;
    technical_challenges: string[];
  }>;
  priority_actions: Array<{
    priority: string;
    metric: string;
    action: string;
    timeline: string;
    expected_improvement: string;
  }>;
}

export interface ImprovementSuggestion {
  metric: string;
  chinese_name: string;
  current_performance: number;
  target_performance: number;
  achievement_rate: number;
  improvement_needed: number;
  priority_score: number;
  suggested_actions: string[];
  expected_timeline: string;
  success_probability: number;
}

export interface DecisionResult {
  experiment_id: number;
  decision_timestamp: string;
  strategy_used: string;
  primary_decision: {
    action_type: string;
    reasoning: string[];
    confidence: number;
    priority: string;
  };
  action_plan: {
    action_type: string;
    steps: string[];
    estimated_duration: string;
    required_resources: string[];
    success_criteria: string[];
    monitoring_points: string[];
    optimization_target?: string;
    optimization_focus?: string[];
    redesign_strategy?: string;
    expected_improvement: string;
  };
  risk_assessment: {
    risk_level: string;
    risk_probability: number;
    potential_risks: string[];
    mitigation_strategies: string[];
    risk_acceptance_criteria: Record<string, any>;
  };
  expected_outcome: {
    expected_score_range: {
      min: number;
      max: number;
      most_likely: number;
    };
    success_probability: number;
    expected_time_requirement: string;
    resource_requirements: Record<string, any>;
    potential_benefits: string[];
    confidence_in_prediction: number;
  };
  decision_context: {
    meets_requirements: boolean;
    overall_score: number;
    critical_failures: string[];
    iteration_count: number;
    success_probability: number;
  };
  next_experiment_config: {
    experiment_type: string;
    base_formula_id?: number;
    iteration_count: number;
    priority: string;
    special_instructions: string[];
    optimization_parameters?: Record<string, any>;
    redesign_parameters?: Record<string, any>;
    finalization_parameters?: Record<string, any>;
  };
}

// API响应类型
export interface ApiResponse<T = any> {
  [x: string]: any;
  result_properties?: any;
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
  // 文献匹配相关字段（用于confirm-parameters接口）
  literature_results?: any[];
  literature_match_success?: boolean;
  literature_error?: string;
  literature_count?: number;
  requirement_id?: number;
  // 数据挖掘相关字段（用于mine-data接口）
  formula_dataset?: any;
  literature_data?: any[];
  molecules?: any[];
}

// 统计数据类型
export interface OptimizationStats {
  total_experiments: number;
  completed_experiments: number;
  failed_experiments: number;
  success_rate: number;
  formula_generation_methods: {
    initial_design: number;
    bayesian_opt: number;
    redesign: number;
  };
}

// 表单数据类型
export interface RequestForm {
  input: string;
}

export interface ParameterForm {
  parameters: Record<string, any> | Record<string, any>[];
  literature_results?: any[];
}

export interface ExperimentExecutionForm {
  formula_id: number;
  experiment_name?: string;
  user_requirements?: Record<string, any>;
}

export interface EvaluationForm {
  experiment_id: number;
  requirements?: Record<string, any>;
}

export interface DecisionForm {
  experiment_id: number;
  evaluation_result: EvaluationResult;
  last_results: Record<string, any>;
}

// 用户相关类型
export interface User {
  id: number;
  created_at: string;
  updated_at?: string;
  email: string;
  username?: string;
  full_name?: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  role: 'user' | 'admin' | 'researcher';
  is_active: boolean;
  is_verified: boolean;
  email_verified?: boolean; // 后端返回的字段
  status?: string; // 后端返回的状态字段
  last_login_at?: string;
  last_login?: string; // 后端返回的字段
  verification_token?: string;
  reset_token?: string;
  reset_token_expires_at?: string;
  preferences?: UserPreferences;
  // 新增字段
  organization?: string;
  bio?: string;
  avatar?: string;
  avatar_url?: string; // 后端返回的字段
  experiment_count?: number;
  formula_count?: number;
}

export interface UserPreferences {
  language: 'zh-CN' | 'en-US';
  theme: 'light' | 'dark';
  notifications: {
    email: boolean;
    push: boolean;
    experiment_updates: boolean;
    optimization_results: boolean;
  };
  default_experiment_type?: 'screening' | 'optimization' | 'validation';
}

export interface LoginForm {
  username: string; // 可以是用户名或邮箱
  password: string;
  remember_me?: boolean;
}

export interface RegisterForm {
  email: string;
  password: string;
  confirm_password: string;
  username?: string;
  full_name?: string;
  first_name?: string;
  last_name?: string;
  organization?: string;
  agree_terms: boolean;
}

export interface ForgotPasswordForm {
  email: string;
}

export interface ResetPasswordForm {
  token: string;
  new_password: string;
  confirm_password: string;
}

export interface ChangePasswordForm {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export interface UpdateProfileForm {
  username?: string;
  full_name?: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  organization?: string;
  bio?: string;
  avatar_url?: string;
  preferences?: Partial<UserPreferences>;
}

export interface AuthResponse {
  user: User;
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
}

export interface LoginResponse {
  success: boolean;
  data?: {
    user: User;
    access_token: string;
    refresh_token: string;
    expires_in: number;
    token_type: string;
  };
  message?: string;
}

export interface EmailVerificationResponse {
  success: boolean;
  message: string;
  already_verified?: boolean;
}

// 修改密码表单
export interface ChangePasswordForm {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

// 头像上传响应
export interface AvatarUploadResponse {
  success: boolean;
  url: string;
  message?: string;
}