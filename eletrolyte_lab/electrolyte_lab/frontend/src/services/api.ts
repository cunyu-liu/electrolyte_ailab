
import axios, { AxiosResponse } from 'axios';
import {
  ApiResponse,
  ParsedParameters,
  ParameterForm,
  FormulaDataset,
  PredictedData,
  Formula,
  Experiment,
  ExperimentExecutionForm,
  MonitoringData,
  EvaluationResult,
  EvaluationForm,
  DecisionResult,
  DecisionForm,
  OptimizationStats
} from '../types';

// 用户认证相关类型
import {
  User,
  LoginForm,
  RegisterForm,
  LoginResponse,
  ForgotPasswordForm,
  ResetPasswordForm,
  EmailVerificationResponse,
  ChangePasswordForm,
  UpdateProfileForm
} from '../types';
import api from '../utils/http';
// 定义RequestForm接口
interface RequestForm {
  input: string;
}
// AI设计员API
export const aiDesignerApi = {
  parseRequest: (data: ParameterForm): Promise<ApiResponse> => {
    return api.post('/ai-designer/parse-request', data).then(res => res.data);
  },
  // 确认参数
  confirmParameters: (data: ParameterForm): Promise<ApiResponse> => {
    return api.post('/ai-designer/confirm-parameters', data).then(res => res.data);
  },
  // 数据挖掘
  mineData: (data: ParameterForm): Promise<ApiResponse<any>> => {
    return api.post('/ai-designer/mine-data', data).then(res => res.data);
  },
  // 性质预测
  predictProperties: async (data: { smiles_list: string[] }): Promise<ApiResponse<PredictedData>> => {
    // 调用真实的后端API，传递SMILES列表
    return api.post('/ai-designer/predict-properties', data).then(res => res.data);
  },
  // 生成配方
  generateFormula: (data: { predicted_data: any; method?: string }): Promise<ApiResponse<{ formula: Formula }>> => {
    return api.post('/ai-designer/generate-formula', data).then(res => res.data);
  },
  // 获取配方详情
  getFormula: (id: number): Promise<ApiResponse<{ formula: Formula }>> => {
    return api.get(`/ai-designer/formulas/${id}`).then(res => res.data);
  },
  // 获取配方列表
  listFormulas: (params?: { page?: number; per_page?: number }): Promise<ApiResponse<{
    formulas: Formula[];
    total: number;
    pages: number;
    current_page: number;
  }>> => {
    return api.get('/ai-designer/formulas', { params }).then(res => res.data);
  },
};

// AI实验员API
export const aiExperimenterApi = {
  // 获取实验列表
  getExperimentList: (params?: {
    page?: number;
    per_page?: number;
    status?: string;
    experiment_type?: string;
  }): Promise<ApiResponse<{
    experiments: Experiment[];
    total: number;
    page: number;
    per_page: number;
  }>> => {
    return api.get('/ai-experimenter/experiments', { params }).then(res => res.data);
  },
  // 执行实验
  executeExperiment: (data: ExperimentExecutionForm): Promise<ApiResponse<{ experiment: Experiment }>> => {
    return api.post('/ai-experimenter/execute', data).then(res => res.data);
  },
  // 获取实验状态
  getExperimentStatus: (id: number): Promise<ApiResponse<{
    experiment: Experiment;
    monitoring_data: any;
  }>> => {
    return api.get(`/ai-experimenter/status/${id}`).then(res => res.data);
  },
  // 获取监控数据
  getMonitoringData: (id: number, type?: string): Promise<ApiResponse<MonitoringData>> => {
    return api.get(`/ai-experimenter/monitoring/${id}`, {
      params: { type }
    }).then(res => res.data);
  },
  // 停止实验
  stopExperiment: (id: number): Promise<ApiResponse> => {
    return api.post(`/ai-experimenter/stop/${id}`).then(res => res.data);
  },
  // 获取实验结果
  getExperimentResults: (id: number): Promise<ApiResponse<{
    experiment: Experiment;
    results: any[];
  }>> => {
    return api.get(`/ai-experimenter/results/${id}`).then(res => res.data);
  },
  // 报告结果（内部API）
  reportResults: (data: { experiment_id: number; results: Record<string, any> }): Promise<ApiResponse> => {
    return api.post('/ai-experimenter/report-results', data).then(res => res.data);
  },
  // 启动视频通道
  startVideoChannel: (channel: number): Promise<ApiResponse<{
    status: string;
    message: string;
    channel: number;
  }>> => {
    return api.get(`/ai-experimenter/video/start/${channel}`).then(res => res.data);
  },
  // 获取视频流URL（用于img标签）
  getVideoStreamUrl: (channel: number): string => {
    return `/api/ai-experimenter/video/get/${channel}`;
  },
};

// 闭环优化API
export const closedLoopApi = {
  // 评估实验
  evaluateExperiment: (data: EvaluationForm): Promise<ApiResponse<{ evaluation_result: EvaluationResult }>> => {
    return api.post('/closed-loop/evaluate', data).then(res => res.data);
  },

  // 决策下一步
  decideNextStep: (data: DecisionForm): Promise<ApiResponse<{ decision: DecisionResult }>> => {
    return api.post('/closed-loop/decide', data).then(res => res.data);
  },

  // 触发重新设计
  triggerRedesign: (data: {
    experiment_id: number;
    failure_reasons: string[];
    iteration_count?: number;
  }): Promise<ApiResponse<{ new_formula_spec: any }>> => {
    return api.post('/closed-loop/trigger-redesign', data).then(res => res.data);
  },

  // 运行贝叶斯优化
  runBayesianOptimization: (data: {
    experiment_id?: number;
    optimization_target?: string;
    iteration_count?: number;
    weights?: { [key: string]: number };
    n_candidates?: number;
  }): Promise<ApiResponse<{ optimization_result: any; stats: any }>> => {
    return api.post('/closed-loop/run-bayesian-optimization', data).then(res => res.data);
  },

  // 基于用户需求的贝叶斯优化
  runRequirementBasedOptimization: (data: {
    experiment_id?: number;
    formula_data?: any;
    user_requirements?: { [key: string]: any };
    n_candidates?: number;
    optimization_target?: string;
  }): Promise<ApiResponse<{
    optimization_result: any;
    saved_formulas: any[];
    user_requirements: { [key: string]: any };
    stats: any
  }>> => {
    return api.post('/closed-loop/run-requirement-based-optimization', data).then(res => res.data);
  },

  // 添加实验数据到贝叶斯优化器
  addExperimentData: (data: {
    experiment_data: any;
    results: any[];
  }): Promise<ApiResponse<{ message: string; stats: any }>> => {
    return api.post('/closed-loop/add-experiment-data', data).then(res => res.data);
  },

  // 获取贝叶斯优化器统计信息
  getBayesianStats: (): Promise<ApiResponse<{ stats: any }>> => {
    return api.get('/closed-loop/bayesian-stats');
  },

  // 获取迭代历史
  getIterationHistory: (experiment_id: number): Promise<ApiResponse<{
    iteration_history: any[];
    total_iterations: number;
  }>> => {
    return api.get(`/closed-loop/iterations/${experiment_id}`).then(res => res.data);
  },

  // 获取优化统计
  getOptimizationStats: (): Promise<ApiResponse<{ stats: OptimizationStats }>> => {
    // 临时Mock响应，模拟统计数据
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          success: true,
          data: {
            stats: {
              total_experiments: 156,
              completed_experiments: 142,
              failed_experiments: 14,
              success_rate: 91.0,
              formula_generation_methods: {
                initial_design: 68,
                bayesian_opt: 52,
                redesign: 36
              }
            }
          }
        });
      }, 500); // 模拟网络延迟
    });
  },
};

// 实验管理API
export const experimentsApi = {
  // 获取所有实验记录，包含贝叶斯优化配方
  getExperiments: (params?: {
    page?: number;
    per_page?: number;
    status?: string;
  }): Promise<ApiResponse<{
    experiments: any[];
    pagination: {
      page: number;
      per_page: number;
      total: number;
      pages: number;
      has_prev: boolean;
      has_next: boolean;
    };
  }>> => {
    const queryParams = new URLSearchParams();
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.per_page) queryParams.append('per_page', params.per_page.toString());
    if (params?.status) queryParams.append('status', params.status);

    const url = `/experiments${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
    return api.get(url).then(res => res.data);
  },

  // 获取特定实验的所有配方
  getExperimentFormulas: (experimentId: number): Promise<ApiResponse<{
    experiment: any;
    original_formula: any;
    optimized_formulas: any[];
    total_optimized: number;
  }>> => {
    return api.get(`/experiments/${experimentId}/formulas`).then(res => res.data);
  },

  // 获取所有贝叶斯优化配方
  getAllBayesianFormulas: (params?: {
    page?: number;
    per_page?: number;
  }): Promise<ApiResponse<{
    formulas: any[];
    pagination: {
      page: number;
      per_page: number;
      total: number;
      pages: number;
      has_prev: boolean;
      has_next: boolean;
    };
  }>> => {
    const queryParams = new URLSearchParams();
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.per_page) queryParams.append('per_page', params.per_page.toString());

    const url = `/bayesian-formulas${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
    return api.get(url).then(res => res.data);
  },

  // 获取配方详细信息
  getFormulaDetails: (formulaId: number): Promise<ApiResponse<{
    formula: any;
  }>> => {
    return api.get(`/formulas/${formulaId}/details`).then(res => res.data);
  }
};

// 实验数据查询API
export const experimentDataApi = {
  // 获取内阻电压数据
  getResistanceVoltageData: (params: {
    experiment_id: string;
    start_time?: string;
    end_time?: string;
    cycle_numbers?: number[];
  }): Promise<ApiResponse<{
    data: Array<{
      cycle_number: number;
      step_number: number;
      total_time: string;
      current: number;
      voltage: number;
      capacity: number;
      experiment_id: string;
    }>;
    total: number;
  }>> => {
    const queryParams = new URLSearchParams();
    queryParams.append('experiment_id', params.experiment_id);

    if (params.start_time) queryParams.append('start_time', params.start_time);
    if (params.end_time) queryParams.append('end_time', params.end_time);
    if (params.cycle_numbers && params.cycle_numbers.length > 0) {
      queryParams.append('cycle_numbers', params.cycle_numbers.join(','));
    }

    return api.get(`/experiment-data/resistance-voltage?${queryParams.toString()}`).then(res => res.data);
  },

  // 获取充放电曲线数据
  getChargeDischargeData: (params: {
    experiment_id: string;
    start_time?: string;
    end_time?: string;
    cycle_numbers?: number[];
  }): Promise<ApiResponse<{
    data: Array<{
      cycle_number: number;
      charge_capacity: number;
      discharge_capacity: number;
      charge_efficiency: number;
      experiment_time: string;
      experiment_id: string;
    }>;
    total: number;
  }>> => {
    const queryParams = new URLSearchParams();
    queryParams.append('experiment_id', params.experiment_id);

    if (params.start_time) queryParams.append('start_time', params.start_time);
    if (params.end_time) queryParams.append('end_time', params.end_time);
    if (params.cycle_numbers && params.cycle_numbers.length > 0) {
      queryParams.append('cycle_numbers', params.cycle_numbers.join(','));
    }

    return api.get(`/experiment-data/charge-discharge?${queryParams.toString()}`).then(res => res.data);
  },

  // 获取内阻数据 (计算得出)
  getImpedanceData: (params: {
    experiment_id: string;
    start_time?: string;
    end_time?: string;
    cycle_numbers?: number[];
    current_threshold?: number;
  }): Promise<ApiResponse<{
    data: Array<{
      cycle_number: number;
      impedance: number;
      voltage_before: number;
      voltage_after: number;
      current_before: number;
      current_after: number;
      total_time: string;
      experiment_id: string;
    }>;
    total: number;
    current_threshold: number;
  }>> => {
    const queryParams = new URLSearchParams();
    queryParams.append('experiment_id', params.experiment_id);

    if (params.start_time) queryParams.append('start_time', params.start_time);
    if (params.end_time) queryParams.append('end_time', params.end_time);
    if (params.cycle_numbers && params.cycle_numbers.length > 0) {
      queryParams.append('cycle_numbers', params.cycle_numbers.join(','));
    }
    if (params.current_threshold) {
      queryParams.append('current_threshold', params.current_threshold.toString());
    }

    return api.get(`/experiment-data/impedance?${queryParams.toString()}`).then(res => res.data);
  },

  // 获取实验汇总信息
  getExperimentSummary: (experimentId: string): Promise<ApiResponse<{
    data: {
      experiment_id: string;
      total_cycles: number;
      first_charge_capacity: number;
      first_discharge_capacity: number;
      latest_charge_capacity: number;
      latest_discharge_capacity: number;
      capacity_retention: number;
      average_efficiency: number;
      latest_efficiency: number;
    };
  }>> => {
    return api.get(`/experiment-data/summary/${experimentId}`).then(res => res.data);
  },

  // 获取所有实验列表
  getExperimentList: (): Promise<ApiResponse<{
    data: Array<{
      id: string;
      name: string;
      created_date: string;
    }>;
    total: number;
  }>> => {
    return api.get('/experiment-data/experiments').then(res => res.data);
  },

  // 更新数据库配置
  updateDatabaseConfig: (config: {
    db_type: 'sqlite' | 'mysql' | 'postgresql';
    host?: string;
    port?: number;
    database?: string;
    username?: string;
    password?: string;
    db_path?: string;
  }): Promise<ApiResponse<{
    config: any;
    message: string;
  }>> => {
    return api.post('/experiment-data/config', config).then(res => res.data);
  },

  // 数据库健康检查
  healthCheck: (): Promise<ApiResponse<{
    message: string;
    db_type: string;
    timestamp: string;
  }>> => {
    return api.get('/experiment-data/health').then(res => res.data);
  }
};

// 蓝甸数据库API
export const landianApi = {
  // 获取蓝甸数据库的循环曲线数据
  getCycleCurveData: (mainId: string): Promise<ApiResponse<{
    data: Array<{
      cycle_number: number;
      charge_capacity: number;
      discharge_capacity: number;
      charge_efficiency: number;
      experiment_time: string;
      experiment_id: string;
    }>;
    total: number;
    message: string;
    main_id: string;
  }>> => {
    return api.get(`/experiment-data/landian/cycle-curve?main_id=${mainId}`).then(res => res.data);
  },

  // 获取蓝甸数据库的循环细节数据
  getCycleDetailData: (mainId: string, cycleNo: number): Promise<ApiResponse<{
    data: {
      experiment_id: string;
      cycle_number: number;
      voltage_curve: number[];
      capacity_curve: number[];
      data_points: number;
      voltage_range: [number, number];
      capacity_range: [number, number];
      charge_curve: {
        voltage: number[];
        capacity: number[];
      };
      discharge_curve: {
        voltage: number[];
        capacity: number[];
      };
    };
    message: string;
    main_id: string;
    cycle_no: number;
    data_points: number;
  }>> => {
    return api.get(`/experiment-data/landian/cycle-detail?main_id=${mainId}&cycle_no=${cycleNo}`).then(res => res.data);
  },

  // 获取蓝甸数据库中所有的MainId列表
  getMainIds: (limit: number = 100): Promise<ApiResponse<{
    data: string[];
    total: number;
    message: string;
  }>> => {
    return api.get(`/experiment-data/landian/main-ids?limit=${limit}`).then(res => res.data);
  },

  // 更新蓝甸数据库连接配置
  updateLandianConfig: (config: {
    host: string;
    port: number;
    user: string;
    password: string;
    database: string;
  }): Promise<ApiResponse<{
    config: any;
    message: string;
    test_result?: string;
  }>> => {
    return api.post('/experiment-data/landian/config', config).then(res => res.data);
  }
};

// 用户认证API
export const authApi = {
  // 用户注册
  register: (data: RegisterForm): Promise<ApiResponse<User>> => {
    const registerData: any = {
      email: data.email,
      password: data.password,
      username: data.username
    };

    // 添加可选字段
    if (data.full_name) {
      registerData.full_name = data.full_name;
    }
    if (data.organization) {
      registerData.organization = data.organization;
    }

    return api.post('/auth/register', registerData).then(response => {
      // 处理后端返回的数据格式
      return {
        success: true,
        data: response.data.user,
        message: response.data.message || '注册成功！'
      };
    }).catch(error => {
      throw error;
    });
  },

  // 用户登录
  login: (data: LoginForm): Promise<LoginResponse> => {
    return api.post('/auth/login', {
      username: data.username,
      password: data.password
    }).then(response => {
      return {
        success: true,
        data: {
          user: response.data.user,
          access_token: response.data.tokens.access_token,
          refresh_token: response.data.tokens.refresh_token,
          expires_in: response.data.tokens.expires_in,
          token_type: response.data.tokens.token_type
        },
        message: response.data.message || '登录成功！'
      };
    }).catch(error => {
      throw error;
    });
  },

  // 用户登出
  logout: (): Promise<ApiResponse> => {
    const token = localStorage.getItem('access_token');
    return api.post('/auth/logout', {}, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }).then(() => {
      // 清除本地存储
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');

      return { success: true, message: '登出成功！' };
    }).catch(error => {
      // 即使API调用失败，也要清除本地存储
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');

      return { success: true, message: '登出成功！' };
    });
  },

  // 获取当前用户信息
  getCurrentUser: (): Promise<ApiResponse<User>> => {
    const token = localStorage.getItem('access_token');
    return api.get('/auth/me', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }).then(response => {
      return {
        success: true,
        data: response.data.user
      };
    }).catch(error => {
      return {
        success: false,
        message: error.response?.data?.error || '获取用户信息失败'
      };
    });
  },

  // 刷新令牌
  refreshToken: (refresh_token: string): Promise<LoginResponse> => {
    return api.post('/auth/refresh', {
      refresh_token: refresh_token
    }).then(response => {
      return {
        success: true,
        data: {
          user: null, // 刷新令牌不返回用户信息
          access_token: response.data.tokens.access_token,
          refresh_token: refresh_token, // 保持原refresh_token
          expires_in: response.data.tokens.expires_in,
          token_type: response.data.tokens.token_type
        },
        message: 'Token刷新成功！'
      };
    }).catch(error => {
      throw error;
    });
  },

  // 忘记密码
  forgotPassword: (data: ForgotPasswordForm): Promise<ApiResponse> => {
    return api.post('/auth/forgot-password', {
      email: data.email
    }).then(response => {
      return {
        success: true,
        message: response.data.message || '密码重置链接已发送到您的邮箱'
      };
    }).catch(error => {
      throw error;
    });
  },

  // 重置密码
  resetPassword: (data: ResetPasswordForm): Promise<ApiResponse> => {
    return api.post('/auth/reset-password', {
      token: data.token,
      new_password: data.new_password
    }).then(response => {
      return {
        success: true,
        message: response.data.message || '密码重置成功'
      };
    }).catch(error => {
      throw error;
    });
  },

  // 验证邮箱
  verifyEmail: (token: string): Promise<EmailVerificationResponse> => {
    return api.post('/auth/verify-email', {
      token: token
    }).then(response => {
      return {
        success: true,
        data: response.data.user,
        message: response.data.message || '邮箱验证成功！'
      };
    }).catch(error => {
      throw error;
    });
  },

  // 重新发送验证邮件
  resendVerification: (email: string): Promise<EmailVerificationResponse> => {
    return api.post('/auth/resend-verification', {
      email: email
    }).then(response => {
      return {
        success: true,
        message: response.data.message || '验证邮件已重新发送'
      };
    }).catch(error => {
      throw error;
    });
  },

  // 修改密码
  changePassword: (data: ChangePasswordForm): Promise<ApiResponse> => {
    const token = localStorage.getItem('access_token');
    return api.post('/auth/change-password', {
      current_password: data.current_password,
      new_password: data.new_password
    }, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }).then(response => {
      return {
        success: true,
        message: response.data.message || '密码修改成功'
      };
    }).catch(error => {
      throw error;
    });
  },

  // 更新用户资料
  updateProfile: (data: UpdateProfileForm): Promise<ApiResponse<User>> => {
    const token = localStorage.getItem('access_token');
    const updateData: any = {};

    // 添加可更新字段
    if (data.full_name) updateData.full_name = data.full_name;
    if (data.first_name) updateData.first_name = data.first_name;
    if (data.last_name) updateData.last_name = data.last_name;
    if (data.phone) updateData.phone = data.phone;
    if (data.organization) updateData.organization = data.organization;
    if (data.avatar_url) updateData.avatar_url = data.avatar_url;

    return api.put('/auth/me', updateData, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }).then(response => {
      return {
        success: true,
        data: response.data.user,
        message: response.data.message || '资料更新成功'
      };
    }).catch(error => {
      throw error;
    });
  },

  // 获取用户列表（管理员）
  getUsers: (params?: {
    page?: number;
    per_page?: number;
    role?: string;
    search?: string;
  }): Promise<ApiResponse<{
    users: User[];
    total: number;
    page: number;
    per_page: number;
  }>> => {
    const token = localStorage.getItem('access_token');
    return api.get('/auth/users', {
      params,
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }).then(response => {
      return {
        success: true,
        data: {
          users: response.data.users,
          total: response.data.total,
          page: response.data.page,
          per_page: response.data.per_page
        },
        message: '获取用户列表成功'
      };
    }).catch(error => {
      throw error;
    });
  },

  // 激活/停用用户（管理员）
  updateUserStatus: (id: number, is_active: boolean): Promise<ApiResponse<User>> => {
    const token = localStorage.getItem('access_token');
    // 将 is_active 转换为 status
    const status = is_active ? 'active' : 'inactive';
    return api.put(`/auth/users/${id}`, { status }, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }).then(response => {
      return {
        success: true,
        data: response.data.user,
        message: response.data.message || `用户状态已成功${is_active ? '激活' : '停用'}`
      };
    }).catch(error => {
      throw error;
    });
  },

  // 更新用户角色（管理员）
  updateUserRole: (id: number, role: string): Promise<ApiResponse<User>> => {
    const token = localStorage.getItem('access_token');
    return api.put(`/auth/users/${id}`, { role }, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }).then(response => {
      return {
        success: true,
        data: response.data.user,
        message: response.data.message || `用户角色已成功更新为${role}`
      };
    }).catch(error => {
      throw error;
    });
  },

  // 更新用户信息（管理员）
  updateUser: (id: number, userData: Partial<User>): Promise<ApiResponse<User>> => {
    const token = localStorage.getItem('access_token');
    const updateData: any = {};

    // 添加可更新字段
    if (userData.username) updateData.username = userData.username;
    if (userData.email) updateData.email = userData.email;
    if (userData.full_name) updateData.full_name = userData.full_name;
    if (userData.first_name) updateData.first_name = userData.first_name;
    if (userData.last_name) updateData.last_name = userData.last_name;
    if (userData.phone) updateData.phone = userData.phone;
    if (userData.organization) updateData.organization = userData.organization;
    if (userData.avatar) updateData.avatar_url = userData.avatar;
    if (userData.role) updateData.role = userData.role;
    if (userData.is_active !== undefined) {
      updateData.status = userData.is_active ? 'active' : 'inactive';
    }

    return api.put(`/auth/users/${id}`, updateData, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }).then(response => {
      return {
        success: true,
        data: response.data.user,
        message: response.data.message || '用户信息已成功更新'
      };
    }).catch(error => {
      throw error;
    });
  },

  // 重置用户密码（管理员）
  resetUserPassword: (id: number, newPassword?: string): Promise<ApiResponse<{ message: string; new_password?: string }>> => {
    const token = localStorage.getItem('access_token');
    const data: any = {};
    if (newPassword) {
      data.new_password = newPassword;
    }

    return api.post(`/auth/users/${id}/reset-password`, data, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }).then(response => {
      return {
        success: true,
        data: {
          message: response.data.message,
          new_password: response.data.new_password
        },
        message: response.data.message || '密码重置成功'
      };
    }).catch(error => {
      throw error;
    });
  },

  // 删除用户（管理员）
  deleteUser: (id: number): Promise<ApiResponse<null>> => {
    const token = localStorage.getItem('access_token');
    return api.delete(`/auth/users/${id}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }).then(response => {
      return {
        success: true,
        data: null,
        message: response.data.message || '用户已成功删除'
      };
    }).catch(error => {
      throw error;
    });
  }
};

// 工具函数
export const apiUtils = {
  // 处理API错误
  handleError: (error: any): string => {
    if (error.response) {
      const serverError = error.response.data?.error || error.response.data?.message || '服务器错误';

      // 特别处理网络相关错误
      if (serverError.includes('网络连接失败') || serverError.includes('API服务不可用')) {
        return 'LLM服务暂时不可用，已使用规则解析替代方案。功能正常，但解析精度可能略有下降。';
      }

      return serverError;
    } else if (error.request) {
      // 请求超时或网络错误
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        return '请求超时，LLM服务暂时不可用，已使用备用解析方案';
      }
      return '网络连接问题，请检查网络连接后重试';
    } else {
      return error.message || '未知错误';
    }
  },

  // 格式化日期
  formatDate: (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN');
  },

  // 获取状态颜色
  getStatusColor: (status: string): string => {
    const colors: Record<string, string> = {
      'pending': '#faad14',
      'running': '#52c41a',
      'completed': '#1890ff',
      'failed': '#ff4d4f',
    };
    return colors[status] || '#666';
  },

  // 获取状态文本
  getStatusText: (status: string): string => {
    const texts: Record<string, string> = {
      'pending': '等待中',
      'running': '运行中',
      'completed': '已完成',
      'failed': '失败',
    };
    return texts[status] || status;
  },
};

// 分子生成API
export const molecularApi = {
  generateMolecules: (data: {
    formula?: string;
    method?: string;
    max_count?: number;
    component_type?: string;
    target_properties?: Record<string, any>;
    literature_results?: Record<string, any>;
    target_count?: number;
    component_types?: string[];
  }): Promise<ApiResponse<{
    molecules: any[];
    saved_components?: any[];
    generation_summary: Record<string, any>;
    message: string;
    target_count?: number;
    actual_count?: number;
    component_types?: string[];
  }>> => {
    return api.post('/ai-designer/generate-molecules', data).then(res => res.data);
  },

  // 获取生成的分子列表
  getGeneratedMolecules: (params?: {
    page?: number;
    per_page?: number;
    component_type?: string;
    generation_method?: string;
  }): Promise<ApiResponse<{
    molecules: any[];
    total: number;
    pages: number;
    current_page: number;
    filters: Record<string, any>;
  }>> => {
    return api.get('/ai-designer/generated-molecules', { params }).then(res => res.data);
  },

  // 验证分子
  validateMolecule: (data: {
    smiles: string;
  }): Promise<ApiResponse<{
    valid: boolean | null;
    properties?: Record<string, any>;
    error?: string;
    message?: string;
  }>> => {
    return api.post('/ai-designer/validate-molecule', data).then(res => res.data);
  },

  // 推荐分子
  recommendMolecules: (data: {
    target_properties: Record<string, any>;
    component_type?: string;
    limit?: number;
  }): Promise<ApiResponse<{
    recommendations: any[];
    total_candidates: number;
    filtered_count: number;
    target_properties: Record<string, any>;
  }>> => {
    return api.post('/ai-designer/recommend-molecules', data).then(res => res.data);
  },
};

// 文献挖掘API
export const literatureApi = {
  // 初始化文献数据库
  initDatabase: (): Promise<ApiResponse<{
    message: string;
  }>> => {
    return api.post('/ai-designer/literature/init-database').then(res => res.data);
  },

  // 上传PDF
  uploadPDF: (formData: FormData): Promise<ApiResponse<{
    literature_id: number;
    filename: string;
    message: string;
  }>> => {
    return api.post('/ai-designer/upload-pdf', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }).then(res => res.data);
  },

  // 处理文献数据库
  processLiterature: (data: {
    pdf_directory?: string;
    update_existing?: boolean;
    batch_size?: number;
    key_parameters?: Record<string, any>;  // 新增：关键参数
  }): Promise<ApiResponse<{
    results: Record<string, any>;
    message: string;
  }>> => {
    return api.post('/ai-designer/process-literature', data).then(res => res.data);
  },

  // 获取文献列表（PostgreSQL版本）
  getLiterature: (params?: {
    page?: number;
    per_page?: number;
    status?: string;
    min_confidence?: number;
    keywords?: string;
    component_type?: string;
  }): Promise<ApiResponse<{
    literature: any[];
    total: number;
    page: number;
    per_page: number;
    pages: number;
  }>> => {
    return api.get('/ai-designer/literature', { params }).then(res => res.data);
  },

  // 获取文献详情
  getLiteratureDetail: (literatureId: number): Promise<ApiResponse<{
    literature: any;
    formulas: any[];
  }>> => {
    return api.get(`/ai-designer/literature/${literatureId}`).then(res => res.data);
  },

  // 获取文献相关的配方
  getLiteratureFormulas: (literatureId: number): Promise<ApiResponse<{
    formulas: any[];
    literature_id: number;
  }>> => {
    return api.get(`/ai-designer/literature/${literatureId}/formulas`).then(res => res.data);
  },

  // 获取配方相关的分子
  getFormulaMolecules: (formulaId: number): Promise<ApiResponse<{
    molecules: any[];
    formula_id: number;
  }>> => {
    return api.get(`/ai-designer/formulas/${formulaId}/molecules`).then(res => res.data);
  },

  // 搜索文献（PostgreSQL版本）
  searchLiterature: (data: {
    query: string;
    component_type?: string;
    min_confidence?: number;
    limit?: number;
  }): Promise<ApiResponse<{
    results: any[];
    total_found: number;
    search_params: Record<string, any>;
  }>> => {
    return api.post('/ai-designer/search-literature', data).then(res => res.data);
  },

  // 获取文献统计信息
  getLiteratureStats: (): Promise<ApiResponse<{
    statistics: Record<string, any>;
  }>> => {
    return api.get('/ai-designer/literature-stats').then(res => res.data);
  },

  // 导入示例文献数据
  importSampleLiterature: (): Promise<ApiResponse<{
    message: string;
    data: {
      inserted_count: number;
    };
  }>> => {
    return api.post('/ai-designer/literature/import-sample').then(res => res.data);
  },

  // 从文献中提取信息
  extractFromLiterature: (data: {
    literature_ids: number[];
    extract_types?: string[];
  }): Promise<ApiResponse<{
    extracted_data: Record<string, any>;
    message: string;
  }>> => {
    return api.post('/ai-designer/extract-from-literature', data).then(res => res.data);
  },

  // 自动处理SPARK PDF文件
  processSparkPdfs: (data?: {
    update_existing?: boolean;
    batch_size?: number;
  }): Promise<ApiResponse<{
    results: Record<string, any>;
    pdf_directory: string;
    message: string;
  }>> => {
    return api.post('/ai-designer/process-spark-pdfs', data || {}).then(res => res.data);
  },
};

// 实时监控数据API
export const monitoringApi = {
  // 获取实验配方的实时监控数据
  getFormulaMonitoringData: (params: {
    experiment_id: number;
    formula_id: number;
    data_types?: string[]; // ['charge_discharge', 'voltage', 'impedance', 'temperature']
    start_time?: string;
    end_time?: string;
    cycle_range?: [number, number];
    limit?: number;
  }): Promise<ApiResponse<{
    monitoring_data: MonitoringData[];
    real_time_status: {
      is_monitoring: boolean;
      last_update: string;
      update_frequency: number; // 秒
      current_cycle?: number;
      total_cycles?: number;
    };
    data_statistics: {
      total_points: number;
      data_types: string[];
      time_range: {
        start: string;
        end: string;
      };
    };
  }>> => {
    const queryParams = new URLSearchParams();
    queryParams.append('experiment_id', params.experiment_id.toString());
    queryParams.append('formula_id', params.formula_id.toString());

    if (params.data_types && params.data_types.length > 0) {
      queryParams.append('data_types', params.data_types.join(','));
    }
    if (params.start_time) queryParams.append('start_time', params.start_time);
    if (params.end_time) queryParams.append('end_time', params.end_time);
    if (params.cycle_range) {
      queryParams.append('cycle_start', params.cycle_range[0].toString());
      queryParams.append('cycle_end', params.cycle_range[1].toString());
    }
    if (params.limit) queryParams.append('limit', params.limit.toString());

    return api.get(`/monitoring/formula-data?${queryParams.toString()}`).then(res => res.data);
  },

  // 获取实验的实时状态
  getExperimentRealTimeStatus: (experimentId: number): Promise<ApiResponse<{
    experiment_id: number;
    status: 'running' | 'paused' | 'completed' | 'error';
    is_monitoring_active: boolean;
    current_cycle?: number;
    total_cycles?: number;
    progress_percentage: number;
    active_formulas: Array<{
      formula_id: number;
      formula_name: string;
      current_cycle: number;
      status: string;
    }>;
    last_data_update: string;
    monitoring_config: {
      update_interval: number; // 秒
      data_buffer_size: number;
      auto_refresh: boolean;
    };
  }>> => {
    return api.get(`/monitoring/experiment-status/${experimentId}`).then(res => res.data);
  },

  // 获取特定配方的最新数据点
  getLatestDataPoint: (params: {
    experiment_id: number;
    formula_id: number;
    data_type: string;
  }): Promise<ApiResponse<{
    data_point: MonitoringData;
    is_latest: boolean;
    next_update_time: string;
  }>> => {
    const queryParams = new URLSearchParams();
    queryParams.append('experiment_id', params.experiment_id.toString());
    queryParams.append('formula_id', params.formula_id.toString());
    queryParams.append('data_type', params.data_type);

    return api.get(`/monitoring/latest-data-point?${queryParams.toString()}`).then(res => res.data);
  },

  // 订阅实时数据更新（WebSocket连接配置）
  subscribeToRealTimeUpdates: (params: {
    experiment_id: number;
    formula_ids?: number[];
    data_types?: string[];
  }): Promise<ApiResponse<{
    websocket_url: string;
    subscription_id: string;
    config: {
      heartbeat_interval: number;
      max_reconnect_attempts: number;
      data_format: string;
    };
  }>> => {
    return api.post('/monitoring/subscribe', params).then(res => res.data);
  },

  // 获取历史数据统计
  getDataStatistics: (params: {
    experiment_id: number;
    formula_id: number;
    statistic_type: 'cycle_summary' | 'performance_trends' | 'degradation_analysis';
    time_range?: [string, string];
  }): Promise<ApiResponse<{
    statistics: {
      total_cycles: number;
      average_efficiency: number;
      capacity_retention: number;
      impedance_growth: number;
      performance_trend: 'improving' | 'stable' | 'degrading';
    };
    detailed_data?: Record<string, any>;
  }>> => {
    const queryParams = new URLSearchParams();
    queryParams.append('experiment_id', params.experiment_id.toString());
    queryParams.append('formula_id', params.formula_id.toString());
    queryParams.append('statistic_type', params.statistic_type);

    if (params.time_range) {
      queryParams.append('start_time', params.time_range[0]);
      queryParams.append('end_time', params.time_range[1]);
    }

    return api.get(`/monitoring/data-statistics?${queryParams.toString()}`).then(res => res.data);
  },

  // 导出监控数据
  exportMonitoringData: (params: {
    experiment_id: number;
    formula_id: number;
    export_format: 'csv' | 'excel' | 'json';
    data_types?: string[];
    cycle_range?: [number, number];
    time_range?: [string, string];
  }): Promise<ApiResponse<{
    download_url: string;
    file_size: number;
    export_config: Record<string, any>;
  }>> => {
    return api.post('/monitoring/export-data', params).then(res => res.data);
  }
};

// 重新导出类型和常量
export * from '../types';

export default api;