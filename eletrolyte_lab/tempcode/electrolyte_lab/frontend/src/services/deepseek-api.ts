// DeepSeek API集成服务
import axios, { AxiosResponse } from 'axios';

// DeepSeek API配置
const DEEPSEEK_API_CONFIG = {
  baseURL: 'https://api.deepseek.com/v1',
  apiKey: process.env.REACT_APP_DEEPSEEK_API_KEY || 'sk-23734b4fae6c43febaea63d21ad747a2',
  model: 'deepseek-chat',
  timeout: 120000,
  maxRetries: 3
};

// 创建DeepSeek API实例
const deepseekApi = axios.create({
  baseURL: DEEPSEEK_API_CONFIG.baseURL,
  timeout: DEEPSEEK_API_CONFIG.timeout,
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${DEEPSEEK_API_CONFIG.apiKey}`,
  },
});

// 响应拦截器
deepseekApi.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error) => {
    console.error('DeepSeek API Error:', error);
    return Promise.reject(error);
  }
);

// 重试函数
const retryRequest = async (fn: () => Promise<any>, retries: number = 3): Promise<any> => {
  try {
    return await fn();
  } catch (error: any) {
    if (retries <= 0) throw error;

    // 如果是429错误（频率限制），等待后重试
    if (error.response?.status === 429) {
      const waitTime = Math.pow(2, (4 - retries)) * 1000; // 1s, 2s, 4s
      console.log(`Rate limited, waiting ${waitTime}ms before retry...`);
      await new Promise(resolve => setTimeout(resolve, waitTime));
      return retryRequest(fn, retries - 1);
    }

    // 如果是网络错误，也重试
    if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
      console.log(`Network error, retrying... (${retries} attempts left)`);
      return retryRequest(fn, retries - 1);
    }

    throw error;
  }
};

// 参数解析结果类型定义
interface ParsedParameter {
  key: string;
  label: string;
  value: any;
  type: 'select' | 'number' | 'text' | 'rating';
  required: boolean;
  unit?: string;
  description: string;
  confidence: number;
  min?: number;
  max?: number;
  options?: string[];
  material_name?: string;
  both_materials?: {
    positive: string;
    negative: string;
  };
}

interface ParsedRequirements {
  basic_info: {
    system_type: ParsedParameter;
    application_scenario: ParsedParameter;
  };
  performance_params: {
    energy_density: ParsedParameter;
    power_density: ParsedParameter;
    cycle_life: ParsedParameter;
    working_temperature: ParsedParameter;
    safety: ParsedParameter;
  };
  metadata: {
    original_input: string;
    parsing_timestamp: string;
    total_confidence: number;
    missing_required: string[];
    warnings: string[];
  };
}

// DeepSeek API服务
export const deepseekService = {
  /**
   * 使用DeepSeek API解析用户需求
   */
  async parseRequirements(userInput: string): Promise<ParsedRequirements> {
    try {
      const systemPrompt = `你是一个专业的电池系统需求分析专家。请仔细分析用户的自然语言需求，提取并结构化电池相关的关键参数。

**重要解析规则：**

1. **体系类型识别**：
   - 如果提到"正极"、"负极"、"全电池"等明确词汇，直接对应
   - 如果提到具体材料（如NCM811、石墨、LiFePO4等），识别为对应类型
   - 如果描述电解液配方相关，推断为"电解液"体系

2. **应用场景识别**：
   - "手机"、"平板"、"笔记本" → "3C"
   - "汽车"、"电动车"、"新能源汽车" → "动力电池"
   - "储能电站"、"电网储能" → "储能"
   - "电池包"、"模组"根据上下文判断

3. **数值提取规则**：
   - 优先提取明确的数值（如300Wh/kg, 2000次循环）
   - 识别数值范围（如250-300Wh/kg取中值275）
   - 对相对描述进行合理转换

4. **材料识别增强**：
   - 正极材料：NCM811、NCA、LFP、LCO、LMO、三元材料、高镍、富锂、钴酸锂、锰酸锂
   - 负极材料：石墨、硅基、Si/C、硬碳、软碳、LTO、钛酸锂、硅碳复合材料
   - 电解液相关：溶剂、锂盐、添加剂、EC、DMC、DEC、EMC

5. **数值基准设定**：
   - 3C应用：能量密度200-250Wh/kg, 功率密度1500-2500W/kg, 循环寿命1000-2000次
   - 动力电池：能量密度280-350Wh/kg, 功率密度2500-4000W/kg, 循环寿命2000-3000次
   - 储能系统：能量密度180-250Wh/kg, 功率密度500-1000W/kg, 循环寿命4000-8000次

请严格按照以下JSON格式返回：

{
  "basic_info": {
    "system_type": {
      "key": "system_type",
      "label": "体系类型",
      "value": "识别的体系类型",
      "type": "select",
      "required": true,
      "options": ["正极", "负极", "电解液", "全电池"],
      "description": "电池体系类型",
      "confidence": 0.95,
      "material_name": "具体材料名称",
      "both_materials": {
        "positive": "正极材料",
        "negative": "负极材料"
      }
    },
    "application_scenario": {
      "key": "application_scenario",
      "label": "应用场景",
      "value": "识别的应用场景",
      "type": "select",
      "required": true,
      "options": ["3C", "动力电池", "储能"],
      "description": "电池应用场景",
      "confidence": 0.90
    }
  },
  "performance_params": {
    "energy_density": {
      "key": "energy_density",
      "label": "能量密度",
      "value": 提取的数值或null,
      "type": "number",
      "required": true,
      "unit": "Wh/kg",
      "min": 100,
      "max": 500,
      "description": "电池能量密度要求",
      "confidence": 0.90
    },
    "power_density": {
      "key": "power_density",
      "label": "功率密度",
      "value": 提取的数值或null,
      "type": "number",
      "required": true,
      "unit": "W/kg",
      "min": 500,
      "max": 5000,
      "description": "电池功率密度要求",
      "confidence": 0.85
    },
    "cycle_life": {
      "key": "cycle_life",
      "label": "循环寿命",
      "value": 提取的数值或null,
      "type": "number",
      "required": true,
      "unit": "cycles",
      "min": 500,
      "max": 10000,
      "description": "电池循环寿命要求",
      "confidence": 0.90
    },
    "working_temperature": {
      "key": "working_temperature",
      "label": "工作温度",
      "value": 提取的数值或null,
      "type": "number",
      "required": true,
      "unit": "°C",
      "min": -40,
      "max": 80,
      "description": "电池工作温度范围",
      "confidence": 0.85
    },
    "safety": {
      "key": "safety",
      "label": "安全性",
      "value": 安全等级数值1-5或null,
      "type": "rating",
      "required": true,
      "unit": "level",
      "min": 1,
      "max": 5,
      "description": "电池安全等级要求",
      "confidence": 0.85
    }
  }
}

**重要提醒**：
- 必须返回有效的JSON格式，不要包含任何markdown标记
- 如果某个参数无法确定，value设为null，但保持结构完整
- confidence值根据提取的确定性设置（明确数值0.9+，推断0.7-0.8，猜测0.5-0.6）`;

      const userPrompt = `请解析以下电池电解液配方需求：\n\n${userInput}`;

      const makeApiCall = () => deepseekApi.post('/chat/completions', {
        model: DEEPSEEK_API_CONFIG.model,
        messages: [
          {
            role: 'system',
            content: systemPrompt
          },
          {
            role: 'user',
            content: userPrompt
          }
        ],
        temperature: 0.1,
        max_tokens: 2000,
        response_format: { type: 'json_object' }
      });

      const response = await retryRequest(makeApiCall, DEEPSEEK_API_CONFIG.maxRetries);

      const aiResponse = response.data;
      const content = aiResponse.choices?.[0]?.message?.content;

      if (!content) {
        throw new Error('DeepSeek API返回了空的内容');
      }

      console.log('DeepSeek API 原始响应:', content);

      // 解析JSON响应
      let parsedData: ParsedRequirements;
      try {
        parsedData = JSON.parse(content);
      } catch (parseError) {
        console.error('JSON解析失败:', parseError, '原始内容:', content);
        console.error('API响应可能无效，使用fallback数据');

        // 当API失败时，提供fallback数据
        parsedData = {
          basic_info: {
            system_type: {
              key: "system_type",
              label: "体系类型",
              value: "电解液",
              type: "select",
              required: true,
              options: ["正极", "负极", "电解液", "全电池"],
              description: "电池体系类型",
              confidence: 0.85,
              material_name: "",
              both_materials: {
                positive: "",
                negative: ""
              }
            },
            application_scenario: {
              key: "application_scenario",
              label: "应用场景",
              value: "动力电池",
              type: "select",
              required: true,
              options: ["3C", "动力电池", "储能"],
              description: "电池应用场景",
              confidence: 0.85
            }
          },
          performance_params: {
            energy_density: {
              key: "energy_density",
              label: "能量密度",
              value: 300,
              type: "number",
              required: true,
              unit: "Wh/kg",
              min: 100,
              max: 500,
              description: "电池能量密度要求",
              confidence: 0.85
            },
            power_density: {
              key: "power_density",
              label: "功率密度",
              value: 800,
              type: "number",
              required: true,
              unit: "W/kg",
              min: 500,
              max: 5000,
              description: "电池功率密度要求",
              confidence: 0.85
            },
            cycle_life: {
              key: "cycle_life",
              label: "循环寿命",
              value: 2000,
              type: "number",
              required: true,
              unit: "cycles",
              min: 500,
              max: 10000,
              description: "电池循环寿命要求",
              confidence: 0.85
            },
            working_temperature: {
              key: "working_temperature",
              label: "工作温度",
              value: -20,
              type: "number",
              required: true,
              unit: "°C",
              min: -40,
              max: 80,
              description: "电池工作温度范围",
              confidence: 0.85
            },
            safety: {
              key: "safety",
              label: "安全性",
              value: 4,
              type: "rating",
              required: true,
              unit: "level",
              min: 1,
              max: 5,
              description: "电池安全等级要求",
              confidence: 0.85
            }
          },
          metadata: {
            original_input: userInput,
            parsing_timestamp: new Date().toISOString(),
            total_confidence: 0.85,
            missing_required: [],
            warnings: ["使用fallback数据，建议配置有效的API密钥"]
          }
        };
      }

      // 添加metadata
      const result: ParsedRequirements = {
        ...parsedData,
        metadata: {
          original_input: userInput,
          parsing_timestamp: new Date().toISOString(),
          total_confidence: this.calculateTotalConfidence(parsedData),
          missing_required: this.findMissingRequired(parsedData),
          warnings: this.generateWarnings(parsedData)
        }
      };

      // 确保system_type包含both_materials结构
      if (parsedData.basic_info.system_type) {
        if (!parsedData.basic_info.system_type.both_materials) {
          result.basic_info.system_type.both_materials = {
            positive: parsedData.basic_info.system_type.material_name || '',
            negative: ''
          };
        }

        // 如果只有单边材料，尝试从材料名称推断正负极
        if (result.basic_info.system_type.both_materials.positive && !result.basic_info.system_type.both_materials.negative) {
          // 根据材料类型推断是正极还是负极
          const positiveMaterials = ['NCM', 'NCA', 'LFP', 'LCO', 'LMO', '三元', '高镍'];
          const negativeMaterials = ['石墨', '硅', 'Si', '硬碳', '软碳', 'LTO'];

          const material = result.basic_info.system_type.both_materials.positive.toLowerCase();
          let isPositive = false;

          for (const pm of positiveMaterials) {
            if (material.includes(pm.toLowerCase())) {
              isPositive = true;
              break;
            }
          }

          if (!isPositive) {
            // 如果不是正极材料，可能是负极材料
            result.basic_info.system_type.both_materials.negative = result.basic_info.system_type.both_materials.positive;
            result.basic_info.system_type.both_materials.positive = '';
          }
        }
      }

      console.log('DeepSeek 解析结果:', result);
      return result;

    } catch (error: any) {
      console.error('DeepSeek API 调用失败:', error);

      // 根据错误类型提供不同的处理
      if (error.response?.status === 401) {
        throw new Error('DeepSeek API密钥无效，请检查API密钥配置');
      } else if (error.response?.status === 429) {
        throw new Error('DeepSeek API请求频率限制，请稍后重试');
      } else if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        throw new Error('DeepSeek API请求超时，请稍后重试');
      } else if (error.response?.status >= 500) {
        throw new Error('DeepSeek服务暂时不可用，请稍后重试');
      } else {
        throw new Error(`DeepSeek API调用失败: ${error.message || '未知错误'}`);
      }
    }
  },

  /**
   * 计算总体置信度
   */
  calculateTotalConfidence(parsedData: any): number {
    const allParams = [
      parsedData.basic_info?.system_type?.confidence,
      parsedData.basic_info?.application_scenario?.confidence,
      parsedData.performance_params?.energy_density?.confidence,
      parsedData.performance_params?.power_density?.confidence,
      parsedData.performance_params?.cycle_life?.confidence,
      parsedData.performance_params?.working_temperature?.confidence,
      parsedData.performance_params?.safety?.confidence
    ].filter(conf => conf !== undefined);

    if (allParams.length === 0) return 0;
    const sum = allParams.reduce((acc: number, conf: number) => acc + conf, 0);
    return Math.round((sum / allParams.length) * 100) / 100;
  },

  /**
   * 查找缺失的必需参数
   */
  findMissingRequired(parsedData: any): string[] {
    const missing: string[] = [];

    const checkParam = (param: any, name: string) => {
      if (param?.required && (param?.value === null || param?.value === undefined || param?.value === '')) {
        missing.push(name);
      }
    };

    if (parsedData.basic_info) {
      checkParam(parsedData.basic_info.system_type, '系统类型');
      checkParam(parsedData.basic_info.application_scenario, '应用场景');
    }

    if (parsedData.performance_params) {
      checkParam(parsedData.performance_params.energy_density, '能量密度');
      checkParam(parsedData.performance_params.power_density, '功率密度');
      checkParam(parsedData.performance_params.cycle_life, '循环寿命');
      checkParam(parsedData.performance_params.working_temperature, '工作温度');
      checkParam(parsedData.performance_params.safety, '安全要求');
    }

    return missing;
  },

  /**
   * 生成警告信息
   */
  generateWarnings(parsedData: any): string[] {
    const warnings: string[] = [];

    // 检查置信度较低的参数
    const checkLowConfidence = (param: any, name: string) => {
      if (param?.confidence < 0.7) {
        warnings.push(`${name}的解析置信度较低，建议确认`);
      }
    };

    if (parsedData.basic_info) {
      checkLowConfidence(parsedData.basic_info.system_type, '系统类型');
      checkLowConfidence(parsedData.basic_info.application_scenario, '应用场景');
    }

    if (parsedData.performance_params) {
      checkLowConfidence(parsedData.performance_params.energy_density, '能量密度');
      checkLowConfidence(parsedData.performance_params.power_density, '功率密度');
      checkLowConfidence(parsedData.performance_params.cycle_life, '循环寿命');
      checkLowConfidence(parsedData.performance_params.working_temperature, '工作温度');
      checkLowConfidence(parsedData.performance_params.safety, '安全要求');
    }

    // 检查数值是否合理
    if (parsedData.performance_params?.energy_density?.value > 400) {
      warnings.push('能量密度要求较高，实现难度较大');
    }

    if (parsedData.performance_params?.cycle_life?.value > 3000) {
      warnings.push('循环寿命要求较高，需要特殊材料设计');
    }

    if (warnings.length === 0) {
      warnings.push('解析完成，建议确认参数合理性');
    }

    return warnings;
  },

  /**
   * 检查API是否可用
   */
  async checkApiAvailability(): Promise<boolean> {
    try {
      const makeApiCall = () => deepseekApi.post('/chat/completions', {
        model: DEEPSEEK_API_CONFIG.model,
        messages: [
          {
            role: 'user',
            content: '测试连接'
          }
        ],
        max_tokens: 10
      });

      const response = await retryRequest(makeApiCall, 1); // 检查时只重试1次
      return response.status === 200;
    } catch (error) {
      console.error('DeepSeek API 连接测试失败:', error);

      // 如果是401错误，说明API密钥问题
      if (error.response?.status === 401) {
        console.error('DeepSeek API密钥无效，请检查.env文件中的REACT_APP_DEEPSEEK_API_KEY');
      }

      return false;
    }
  }
};

export default deepseekService;