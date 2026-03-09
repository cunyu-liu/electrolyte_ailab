// Mock API服务 - 简化版本，专注于核心功能

// 模拟延迟函数
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// Mock AI设计员API
export const aiDesignerApi = {
  // 解析用户需求
  parseRequest: async (data: { input: string }) => {
    await delay(1500);

    console.log('使用增强的智能解析:', data);

    // 智能解析用户输入
    const userInput = data.input.toLowerCase();
    let systemType = "电解液";
    let applicationScenario = "动力电池";
    let energyDensity = 300;
    let powerDensity = 800;
    let cycleLife = 2000;
    let workingTemp = -20;
    let safety = 0.90;
    let materialName = "";
    let bothMaterials = { positive: "", negative: "" };

    // 体系类型识别
    if (userInput.includes("正极") || userInput.includes("阴极")) {
      systemType = "正极";
    } else if (userInput.includes("负极") || userInput.includes("阳极")) {
      systemType = "负极";
    } else if (userInput.includes("电解液") || userInput.includes("溶剂") || userInput.includes("锂盐")) {
      systemType = "电解液";
    } else if (userInput.includes("全电池") || userInput.includes("完整电池")) {
      systemType = "全电池";
    }

    // 材料识别
    const positiveMaterials = ["ncm", "nca", "lfp", "lco", "lmo", "三元", "高镍", "钴酸锂", "锰酸锂", "磷酸铁锂"];
    const negativeMaterials = ["石墨", "硅", "si", "硬碳", "软碳", "lto", "钛酸锂", "硅碳"];

    for (const material of positiveMaterials) {
      if (userInput.includes(material)) {
        materialName = material.toUpperCase();
        bothMaterials.positive = material.toUpperCase();
        systemType = "正极";
        break;
      }
    }

    for (const material of negativeMaterials) {
      if (userInput.includes(material)) {
        materialName = material.includes("si") ? "Si/C" : material;
        bothMaterials.negative = materialName;
        systemType = "负极";
        break;
      }
    }

    // 应用场景识别
    if (userInput.includes("手机") || userInput.includes("平板") || userInput.includes("笔记本") || userInput.includes("3c")) {
      applicationScenario = "3C";
    } else if (userInput.includes("汽车") || userInput.includes("电动车") || userInput.includes("新能源") || userInput.includes("动力")) {
      applicationScenario = "动力电池";
    } else if (userInput.includes("储能") || userInput.includes("电站") || userInput.includes("电网")) {
      applicationScenario = "储能";
    }

    // 数值提取
    const energyDensityMatch = userInput.match(/(\d+)\s*(wh\/kg|wh)/);
    if (energyDensityMatch) {
      energyDensity = parseInt(energyDensityMatch[1]);
    }

    const powerDensityMatch = userInput.match(/(\d+)\s*(w\/kg|w)/);
    if (powerDensityMatch) {
      powerDensity = parseInt(powerDensityMatch[1]);
    }

    const cycleLifeMatch = userInput.match(/(\d+)\s*(次|cycle|cycles)/);
    if (cycleLifeMatch) {
      cycleLife = parseInt(cycleLifeMatch[1]);
    }

    const tempMatch = userInput.match(/-?\d+\s*°?[cC]/);
    if (tempMatch) {
      workingTemp = parseInt(tempMatch[0]);
    }

    // 安全要求识别
    if (userInput.includes("高安全") || userInput.includes("安全要求高")) {
      safety = 0.95;
    } else if (userInput.includes("低安全") || userInput.includes("安全要求低")) {
      safety = 0.70;
    }

    // 根据应用场景调整基准值
    let baseEnergyDensity, basePowerDensity, baseCycleLife;
    switch (applicationScenario) {
      case "3C":
        baseEnergyDensity = 225; // (200+250)/2
        basePowerDensity = 2000; // (1500+2500)/2
        baseCycleLife = 1500; // (1000+2000)/2
        break;
      case "动力电池":
        baseEnergyDensity = 315; // (280+350)/2
        basePowerDensity = 3250; // (2500+4000)/2
        baseCycleLife = 2500; // (2000+3000)/2
        break;
      case "储能":
        baseEnergyDensity = 215; // (180+250)/2
        basePowerDensity = 750; // (500+1000)/2
        baseCycleLife = 6000; // (4000+8000)/2
        break;
      default:
        baseEnergyDensity = 300;
        basePowerDensity = 800;
        baseCycleLife = 2000;
    }

    // 如果用户没有明确指定数值，使用应用场景的基准值
    if (!energyDensityMatch) energyDensity = baseEnergyDensity;
    if (!powerDensityMatch) powerDensity = basePowerDensity;
    if (!cycleLifeMatch) cycleLife = baseCycleLife;

    const mockResponse = {
      success: true,
      data: {
        basic_info: {
          system_type: {
            key: "system_type",
            label: "体系类型",
            value: systemType,
            type: "select" as const,
            required: true,
            options: ["正极", "负极", "电解液", "全电池"],
            description: "电池系统类型",
            confidence: 0.95,
            source: "智能解析",
            material_name: materialName,
            both_materials: bothMaterials
          },
          application_scenario: {
            key: "application_scenario",
            label: "应用场景",
            value: applicationScenario,
            type: "select" as const,
            required: true,
            options: ["3C", "动力电池", "储能"],
            description: "电池应用场景",
            confidence: 0.90,
            source: "智能解析"
          }
        },
        performance_params: {
          energy_density: {
            key: "energy_density",
            label: "能量密度",
            value: energyDensity,
            type: "number" as const,
            required: true,
            unit: "Wh/kg",
            min: 100,
            max: 500,
            description: "电池能量密度要求",
            confidence: energyDensityMatch ? 0.90 : 0.80,
            source: "智能解析"
          },
          power_density: {
            key: "power_density",
            label: "功率密度",
            value: powerDensity,
            type: "number" as const,
            required: true,
            unit: "W/kg",
            min: 500,
            max: 5000,
            description: "电池功率密度要求",
            confidence: powerDensityMatch ? 0.85 : 0.75,
            source: "智能解析"
          },
          cycle_life: {
            key: "cycle_life",
            label: "循环寿命",
            value: cycleLife,
            type: "number" as const,
            required: true,
            unit: "cycles",
            min: 500,
            max: 10000,
            description: "电池循环寿命要求",
            confidence: cycleLifeMatch ? 0.90 : 0.80,
            source: "智能解析"
          },
          working_temperature: {
            key: "working_temperature",
            label: "工作温度",
            value: workingTemp,
            type: "number" as const,
            required: true,
            unit: "°C",
            min: -40,
            max: 80,
            description: "电池工作温度要求",
            confidence: tempMatch ? 0.85 : 0.70,
            source: "智能解析"
          },
          safety: {
            key: "safety",
            label: "安全性",
            value: safety,
            type: "rating" as const,
            required: true,
            min: 0,
            max: 1,
            description: "电池安全性评分要求",
            confidence: 0.85,
            source: "智能解析"
          }
        },
        metadata: {
          original_input: data.input,
          parsing_timestamp: new Date().toISOString(),
          total_confidence: 0.87,
          missing_required: [],
          warnings: []
        }
      }
    };

    console.log('返回增强的解析结果:', mockResponse);
    return mockResponse;
  },

  // 确认参数
  confirmParameters: async (data: { parameters: any }) => {
    await delay(1000);

    return {
      success: true,
      data: {
        confirmed_parameters: data.parameters,
        confirmation_timestamp: new Date().toISOString()
      }
    };
  },

  // 数据整合
  mineData: async (data: { parameters: any }) => {
    await delay(2000);

    return {
      success: true,
      data: {
        dataset: {
          original_formulas: Array.from({ length: 50 }, (_, i) => ({
            id: i + 1,
            name: `基础配方_${i + 1}`,
            components: [
              { name: "EC", percentage: 30 + Math.random() * 20 },
              { name: "DMC", percentage: 30 + Math.random() * 20 },
              { name: "LiPF6", percentage: 10 + Math.random() * 5 }
            ]
          })),
          augmented_formulas: Array.from({ length: 200 }, (_, i) => ({
            id: i + 1,
            name: `扩增配方_${i + 1}`,
            components: [
              { name: "EC", percentage: 25 + Math.random() * 25 },
              { name: "DMC", percentage: 25 + Math.random() * 25 },
              { name: "LiPF6", percentage: 8 + Math.random() * 7 }
            ]
          })),
          total_count: 250,
          source_parameters: data.parameters,
          generation_timestamp: new Date().toISOString(),
          generation_method: "data_augmentation",
          quality_metrics: {
            average_confidence: 0.85,
            high_confidence_count: 180
          }
        }
      }
    };
  },

  // 数据挖掘
  dataMining: async (data: { parameters: any }) => {
    await delay(2000);

    return {
      success: true,
      data: {
        dataset: {
          original_formulas: Array.from({ length: 50 }, (_, i) => ({
            id: i + 1,
            name: `基础配方_${i + 1}`,
            components: [
              { name: "EC", percentage: 30 + Math.random() * 20 },
              { name: "DMC", percentage: 30 + Math.random() * 20 },
              { name: "LiPF6", percentage: 10 + Math.random() * 5 }
            ]
          })),
          augmented_formulas: Array.from({ length: 200 }, (_, i) => ({
            id: i + 1,
            name: `扩增配方_${i + 1}`,
            components: [
              { name: "EC", percentage: 25 + Math.random() * 25 },
              { name: "DMC", percentage: 25 + Math.random() * 25 },
              { name: "LiPF6", percentage: 8 + Math.random() * 7 }
            ]
          })),
          total_count: 250,
          source_parameters: data.parameters,
          generation_timestamp: new Date().toISOString(),
          generation_method: "data_augmentation",
          quality_metrics: {
            average_confidence: 0.85,
            high_confidence_count: 180
          }
        }
      }
    };
  },

  // 性能预测
  performancePrediction: async (data: { dataset: any }) => {
    await delay(2500);

    const predictedFormulas = Array.from({ length: 20 }, (_, i) => ({
      formula_index: i + 1,
      formula: {
        name: `预测配方_${i + 1}`,
        components: [
          { name: "EC", percentage: 30 },
          { name: "DMC", percentage: 35 },
          { name: "LiPF6", percentage: 12 }
        ]
      },
      molecular_properties: {
        conductivity: 8 + Math.random() * 4,
        viscosity: 2 + Math.random() * 2,
        flash_point: 120 + Math.random() * 30
      },
      system_properties: {
        energy_density: 300 + Math.random() * 100,
        power_density: 700 + Math.random() * 300,
        cycle_life: 1500 + Math.random() * 1000,
        safety_score: 0.8 + Math.random() * 0.15
      },
      overall_score: 0.75 + Math.random() * 0.2,
      prediction_confidence: 0.8 + Math.random() * 0.15
    }));

    return {
      success: true,
      data: {
        total_predictions: 20,
        selected_count: 20,
        predicted_formulas: predictedFormulas,
        selection_criteria: "综合评分>0.8",
        prediction_timestamp: new Date().toISOString(),
        model_info: {
          model_type: "深度学习预测模型",
          prediction_accuracy: "±5%",
          features_used: ["分子结构", "组分比例", "工艺参数"]
        }
      }
    };
  },

  // 性能预测
  predictProperties: async (data: {
    formula_dataset?: any;
    molecules?: any[];
    literature_data?: any[];
    parameters?: Record<string, any>;
    dataset?: any;
  }) => {
    await delay(2500);

    const inputMolecules = data.molecules || [];

    // 从输入分子中按类型分类
    const solvents = inputMolecules.filter(m => m.component_type === 'solvent');
    const salts = inputMolecules.filter(m => m.component_type === 'salt');
    const additives = inputMolecules.filter(m => m.component_type === 'additive');

    // 创建真实的分子数据库用于筛选
    const moleculeDatabase = {
      solvent: [
        { name: "EC", smiles: "O=C1OCCO1", formula: "C3H4O3", properties: { dielectric_constant: 90.1, viscosity: 1.9 } },
        { name: "DMC", smiles: "COC(=O)OC", formula: "C3H6O3", properties: { dielectric_constant: 3.1, viscosity: 0.59 } },
        { name: "EMC", smiles: "CCOC(=O)OC", formula: "C4H8O3", properties: { dielectric_constant: 2.9, viscosity: 0.65 } },
        { name: "PC", smiles: "O=C1OCCC1", formula: "C4H6O3", properties: { dielectric_constant: 64.9, viscosity: 2.5 } },
        { name: "DEC", smiles: "CCOC(=O)OCC", formula: "C5H10O3", properties: { dielectric_constant: 2.8, viscosity: 0.75 } }
      ],
      salt: [
        { name: "LiPF6", smiles: "[Li+].[P-](F)(F)(F)(F)(F)F", formula: "LiF6P", properties: { conductivity: 10.5, solubility: 1.2 } },
        { name: "LiBF4", smiles: "[Li+].[B-](F)(F)(F)F", formula: "LiBF4", properties: { conductivity: 9.2, solubility: 1.0 } },
        { name: "LiTFSI", smiles: "[Li+].S(=O)(=O)([O-])C(F)(F)C(F)(F)S(=O)(=O)[O-]", formula: "C2F6LiNO4S2", properties: { conductivity: 8.8, solubility: 1.5 } }
      ],
      additive: [
        { name: "VC", smiles: "C=CC1OC(=O)O1", formula: "C4H4O3", properties: { sei_formation: 0.85, flame_retardancy: 0.3 } },
        { name: "FEC", smiles: "C1OC(=O)C(F)O1", formula: "C3H3FO3", properties: { sei_formation: 0.90, flame_retardancy: 0.4 } },
        { name: "PS", smiles: "O=P(O)(O)SC1=CC=CC=C1", formula: "C6H7O3PS", properties: { flame_retardancy: 0.8, sei_formation: 0.6 } }
      ]
    };

    // 按性能排序筛选最优分子
    const topSolvents = solvents.length > 0 ? solvents.sort((a, b) =>
      (b.predicted_properties?.conductivity || 0) - (a.predicted_properties?.conductivity || 0)
    ).slice(0, 3) : moleculeDatabase.solvent.slice(0, 3);

    const topSalts = salts.length > 0 ? salts.sort((a, b) =>
      (b.predicted_properties?.conductivity || 0) - (a.predicted_properties?.conductivity || 0)
    ).slice(0, 2) : moleculeDatabase.salt.slice(0, 2);

    const topAdditives = additives.length > 0 ? additives.sort((a, b) =>
      (b.predicted_properties?.sei_formation_ability || 0) - (a.predicted_properties?.sei_formation_ability || 0)
    ).slice(0, 2) : moleculeDatabase.additive.slice(0, 2);

    // 创建筛选后的分子结构
    const filteredMolecules = {
      top_solvents: topSolvents.map(m => ({
        formula: {
          name: m.name,
          chemical_formula: m.chemical_formula || moleculeDatabase.solvent.find(s => s.name === m.name)?.formula || "C3H6O3",
          smiles_notation: m.smiles_notation || moleculeDatabase.solvent.find(s => s.name === m.name)?.smiles || "COC(=O)OC",
          molecular_properties: m.predicted_properties || moleculeDatabase.solvent.find(s => s.name === m.name)?.properties || {}
        },
        overall_score: 0.85 + Math.random() * 0.1,
        prediction_confidence: 0.8 + Math.random() * 0.15
      })),
      top_salts: topSalts.map(m => ({
        formula: {
          name: m.name,
          chemical_formula: m.chemical_formula || moleculeDatabase.salt.find(s => s.name === m.name)?.formula || "LiF6P",
          smiles_notation: m.smiles_notation || moleculeDatabase.salt.find(s => s.name === m.name)?.smiles || "[Li+].[P-](F)(F)(F)(F)(F)F",
          molecular_properties: m.predicted_properties || moleculeDatabase.salt.find(s => s.name === m.name)?.properties || {}
        },
        overall_score: 0.8 + Math.random() * 0.15,
        prediction_confidence: 0.75 + Math.random() * 0.2
      })),
      top_additives: topAdditives.map(m => ({
        formula: {
          name: m.name,
          chemical_formula: m.chemical_formula || moleculeDatabase.additive.find(s => s.name === m.name)?.formula || "C4H4O3",
          smiles_notation: m.smiles_notation || moleculeDatabase.additive.find(s => s.name === m.name)?.smiles || "C=CC1OC(=O)O1",
          molecular_properties: m.predicted_properties || moleculeDatabase.additive.find(s => s.name === m.name)?.properties || {}
        },
        overall_score: 0.75 + Math.random() * 0.2,
        prediction_confidence: 0.7 + Math.random() * 0.2
      }))
    };

    const predictedFormulas = Array.from({ length: 20 }, (_, i) => {
      const solvent = topSolvents[i % topSolvents.length] || topSolvents[0];
      const salt = topSalts[i % topSalts.length] || topSalts[0];
      const additive = topAdditives[i % topAdditives.length];

      return {
        formula_index: i + 1,
        formula: {
          name: `预测配方_${i + 1}`,
          components: [
            { name: solvent.name, percentage: 30 + Math.random() * 20 },
            { name: salt.name, percentage: 10 + Math.random() * 8 }
          ].concat(additive ? [{ name: additive.name, percentage: 2 + Math.random() * 8 }] : [])
        },
        molecular_properties: {
          conductivity: 8 + Math.random() * 4,
          viscosity: 2 + Math.random() * 2,
          flash_point: 120 + Math.random() * 30
        },
        system_properties: {
          energy_density: 300 + Math.random() * 100,
          power_density: 700 + Math.random() * 300,
          cycle_life: 1500 + Math.random() * 1000,
          safety_score: 0.8 + Math.random() * 0.15
        },
        overall_score: 0.75 + Math.random() * 0.2,
        prediction_confidence: 0.8 + Math.random() * 0.15
      };
    });

    return {
      success: true,
      data: {
        total_predictions: 20,
        selected_count: 20,
        predicted_formulas: predictedFormulas,
        filtered_molecules: filteredMolecules, // 添加这个关键字段
        selection_criteria: "综合评分>0.8",
        prediction_timestamp: new Date().toISOString(),
        model_info: {
          model_type: "深度学习预测模型",
          prediction_accuracy: "±5%",
          features_used: ["分子结构", "组分比例", "工艺参数"]
        }
      }
    };
  },

  // 配方生成 - 简化版本
  generateFormula: async (data: { predicted_data: any; method?: string }) => {
    await delay(3000);

    const method = data.method || "多目标优化";
    const predictedFormulas = data.predicted_data?.predicted_formulas || [];
    const bestFormula = predictedFormulas.length > 0 ?
      predictedFormulas.reduce((best: any, current: any) =>
        current.overall_score > best.overall_score ? current : best
      ) : null;

    if (!bestFormula) {
      return {
        success: false,
        message: "没有找到合适的配方候选"
      };
    }

    // 创建简化版配方
    const finalFormula = {
      id: Date.now(),
      name: `AI优化电解液配方_${bestFormula.formula_index}`,
      description: `基于${method}算法优化的高性能电解液配方，综合平衡了能量密度、循环寿命和安全性`,
      system_type: "电解液",
      application_scenario: "动力电池",
      generation_method: "ai_optimization",
      components: [
        {
          id: 1,
          formula_id: Date.now(),
          component_type: "solvent",
          name: "EC",
          chemical_formula: "C3H4O3",
          percentage: 35,
          unit: "wt%",
          properties: {
            dielectric_constant: 90.1,
            viscosity: 1.9,
            flash_point: 160
          },
          source: "AI优化",
          role: "主溶剂",
          created_at: new Date().toISOString()
        },
        {
          id: 2,
          formula_id: Date.now(),
          component_type: "solvent",
          name: "DMC",
          chemical_formula: "C3H6O3",
          percentage: 45,
          unit: "wt%",
          properties: {
            dielectric_constant: 3.1,
            viscosity: 0.59,
            flash_point: 18
          },
          source: "AI优化",
          role: "辅助溶剂",
          created_at: new Date().toISOString()
        },
        {
          id: 3,
          formula_id: Date.now(),
          component_type: "salt",
          name: "LiPF6",
          chemical_formula: "LiPF6",
          percentage: 12,
          unit: "wt%",
          properties: {
            conductivity: 10.5,
            solubility: 1.2,
            stability: 0.95
          },
          source: "AI优化",
          role: "主锂盐",
          created_at: new Date().toISOString()
        },
        {
          id: 4,
          formula_id: Date.now(),
          component_type: "additive",
          name: "VC",
          chemical_formula: "C3H4O3",
          percentage: 2,
          unit: "wt%",
          properties: {
            sei_formation: 0.92,
            flame_retardancy: 0.75,
            overcharge_protection: 0.85
          },
          source: "AI优化",
          role: "成膜添加剂",
          created_at: new Date().toISOString()
        },
        {
          id: 5,
          formula_id: Date.now(),
          component_type: "additive",
          name: "FEC",
          chemical_formula: "C3H4O3",
          percentage: 6,
          unit: "wt%",
          properties: {
            sei_formation: 0.88,
            flame_retardancy: 0.82,
            cycle_improvement: 0.91
          },
          source: "AI优化",
          role: "循环稳定性添加剂",
          created_at: new Date().toISOString()
        }
      ],
      predicted_performance: {
        energy_density: Math.round(bestFormula.system_properties?.energy_density || 350),
        power_density: Math.round(bestFormula.system_properties?.power_density || 800),
        cycle_life: Math.round(bestFormula.system_properties?.cycle_life || 2000),
        safety_score: bestFormula.system_properties?.safety_score || 0.90,
        stability_score: 0.88,
        cost_per_kwh: 650,
        additional_metrics: {
          ionic_conductivity: 10.2,
          viscosity: 2.8,
          flash_point: 135,
          coulombic_efficiency: 0.98
        }
      },
      preparation_steps: [
        {
          step: 1,
          operation: "溶剂纯化",
          description: "将EC和DMC在分子筛干燥器中干燥24小时",
          conditions: "温度：60°C，真空度：<10Pa",
          duration: "24小时",
          critical_parameters: ["含水量 < 20ppm", "透明度"]
        },
        {
          step: 2,
          operation: "锂盐溶解",
          description: "在氩气保护手套箱中将LiPF6加入混合溶剂中",
          conditions: "温度：25±2°C，湿度：<1ppm H2O",
          duration: "2小时",
          critical_parameters: ["溶解速度", "溶液澄清度"]
        },
        {
          step: 3,
          operation: "添加剂添加",
          description: "按比例将VC和FEC加入电解液中，搅拌至完全溶解",
          conditions: "温度：25±2°C，氩气保护",
          duration: "1小时",
          critical_parameters: ["添加顺序", "溶解均匀性"]
        },
        {
          step: 4,
          operation: "过滤封装",
          description: "用0.2μm PTFE滤膜过滤电解液，封装储存",
          conditions: "手套箱环境，暗处保存",
          duration: "0.5小时",
          critical_parameters: ["过滤精度", "密封性"]
        }
      ],
      quality_metrics: {
        overall_score: Math.round(bestFormula.overall_score * 100) / 100,
        confidence_level: bestFormula.prediction_confidence || 0.85,
        readiness_level: "TRL 6",
        validation_status: "待实验验证",
        risk_assessment: {
          technical_risk: "低",
          scalability_risk: "低",
          cost_risk: "低",
          regulatory_risk: "低"
        }
      },
      optimization_method: method,
      optimization_details: {
        algorithm_used: method,
        target_achievement_rate: 92,
        performance_balance_score: 0.87,
        improvement_vs_baseline: {
          energy_density: "+5%",
          cycle_life: "+8%",
          safety: "+3%",
          cost: "-2%"
        }
      },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    return {
      success: true,
      data: {
        formula: finalFormula,
        optimization_summary: {
          total_candidates_evaluated: predictedFormulas.length,
          selected_formula_score: finalFormula.quality_metrics.overall_score,
          method: method,
          optimization_time: "3.2秒",
          key_improvements: ["能量密度提升5%", "循环寿命提升8%", "成本降低2%"]
        }
      },
      message: `AI优化配方生成完成！综合评分${finalFormula.quality_metrics.overall_score}，置信度${(finalFormula.quality_metrics.confidence_level * 100).toFixed(1)}%`
    };
  }
};

// Mock分子API - 简化版本
export const molecularApi = {
  generateMolecules: async (data: { literature_results: any; target_count: number; component_types: string[] }) => {
    await delay(2000);

    // 真实的电解液分子SMILES数据库
    const moleculeDatabase = {
      solvent: [
        { name: "EC", smiles: "O=C1OCCO1", formula: "C3H4O3" },
        { name: "DMC", smiles: "COC(=O)OC", formula: "C3H6O3" },
        { name: "EMC", smiles: "CCOC(=O)OC", formula: "C4H8O3" },
        { name: "PC", smiles: "O=C1OCCC1", formula: "C4H6O3" },
        { name: "DEC", smiles: "CCOC(=O)OCC", formula: "C5H10O3" },
        { name: "VC", smiles: "C=CC1OC(=O)O1", formula: "C4H4O3" },
        { name: "FEC", smiles: "C1OC(=O)C(F)O1", formula: "C3H3FO3" }
      ],
      salt: [
        { name: "LiPF6", smiles: "[Li+].[P-](F)(F)(F)(F)(F)F", formula: "LiF6P" },
        { name: "LiBF4", smiles: "[Li+].[B-](F)(F)(F)F", formula: "LiBF4" },
        { name: "LiClO4", smiles: "[Li+].[Cl-]([O])([O])([O])[O]", formula: "LiClO4" },
        { name: "LiTFSI", smiles: "[Li+].S(=O)(=O)([O-])C(F)(F)C(F)(F)S(=O)(=O)[O-]", formula: "C2F6LiNO4S2" },
        { name: "LiFSI", smiles: "[Li+].S(=O)(=O)([O-])N(S(=O)(=O)[O-])C(F)(F)F", formula: "CF3LiNO4S2" }
      ],
      additive: [
        { name: "VC", smiles: "C=CC1OC(=O)O1", formula: "C4H4O3" },
        { name: "FEC", smiles: "C1OC(=O)C(F)O1", formula: "C3H3FO3" },
        { name: "PS", smiles: "O=P(O)(O)SC1=CC=CC=C1", formula: "C6H7O3PS" },
        { name: "DTD", smiles: "O=S(=O)SCC", formula: "C2H6O2S2" },
        { name: "TTSPi", smiles: "CCN(CC)CCOP(=S)(OCC)OCC", formula: "C10H26NO3PS" },
        { name: "DMTP", smiles: "CCSC", formula: "C3H8S" }
      ]
    };

    const molecules = Array.from({ length: data.target_count }, (_, i) => {
      const componentType = data.component_types[i % data.component_types.length];
      const moleculePool = moleculeDatabase[componentType as keyof typeof moleculeDatabase] || moleculeDatabase.solvent;
      const selectedMolecule = moleculePool[i % moleculePool.length];

      return {
        id: i + 1,
        name: selectedMolecule.name,
        component_type: componentType,
        chemical_formula: selectedMolecule.formula,
        smiles_notation: selectedMolecule.smiles,
        predicted_properties: {
          conductivity: 8 + Math.random() * 4,
          viscosity: 2 + Math.random() * 2,
          sei_formation_ability: Math.random(),
          flame_retardancy: Math.random()
        },
        prediction_confidence: 0.8 + Math.random() * 0.15,
        requirement_match_score: 0.7 + Math.random() * 0.25
      };
    });

    return {
      success: true,
      data: {
        molecules: molecules,
        total_generated: molecules.length,
        generation_timestamp: new Date().toISOString()
      }
    };
  }
};

// Mock文献API - 简化版本
export const literatureApi = {
  searchLiterature: async (data: { parameters: any }) => {
    await delay(1500);

    return {
      success: true,
      data: {
        query_summary: {
          total_papers_found: 25,
          relevant_papers: 18,
          search_timestamp: new Date().toISOString()
        },
        papers: Array.from({ length: 5 }, (_, i) => ({
          id: i + 1,
          title: `电解液相关研究论文_${i + 1}`,
          authors: ["研究者A", "研究者B", "研究者C"],
          journal: "电池技术学报",
          year: 2020 + i,
          doi: `10.1234/battery.${2023 + i}.${i + 1}`,
          abstract: "本文研究了新型电解液配方的性能...",
          key_findings: [
            "高电导率电解液配方",
            "优异的循环稳定性",
            "良好的安全性能"
          ],
          relevance_score: 0.8 + Math.random() * 0.15
        })),
        extracted_molecules: [
          {
            name: "EC",
            component_type: "solvent",
            chemical_formula: "C3H4O3",
            smiles_notation: "O=C1OCCO1",
            properties: { dielectric_constant: 90.1, viscosity: 1.9 },
            source_papers: [1, 2, 3]
          },
          {
            name: "DMC",
            component_type: "solvent",
            chemical_formula: "C3H6O3",
            smiles_notation: "COC(=O)OC",
            properties: { dielectric_constant: 3.1, viscosity: 0.59 },
            source_papers: [1, 2, 4]
          },
          {
            name: "LiPF6",
            component_type: "salt",
            chemical_formula: "LiF6P",
            smiles_notation: "[Li+].[P-](F)(F)(F)(F)(F)F",
            properties: { conductivity: 10.5, solubility: 1.2 },
            source_papers: [2, 3, 5]
          }
        ],
        generated_molecules: Array.from({ length: 8 }, (_, i) => {
          const moleculeDatabase = [
            { name: "PC", smiles: "O=C1OCCC1", formula: "C4H6O3" },
            { name: "EMC", smiles: "CCOC(=O)OC", formula: "C4H8O3" },
            { name: "LiBF4", smiles: "[Li+].[B-](F)(F)(F)F", formula: "LiBF4" },
            { name: "LiTFSI", smiles: "[Li+].S(=O)(=O)([O-])C(F)(F)C(F)(F)S(=O)(=O)[O-]", formula: "C2F6LiNO4S2" },
            { name: "VC", smiles: "C=CC1OC(=O)O1", formula: "C4H4O3" },
            { name: "PS", smiles: "O=P(O)(O)SC1=CC=CC=C1", formula: "C6H7O3PS" },
            { name: "DTD", smiles: "O=S(=O)SCC", formula: "C2H6O2S2" },
            { name: "FEC", smiles: "C1OC(=O)C(F)O1", formula: "C3H3FO3" }
          ];

          const componentType = ["solvent", "salt", "additive"][i % 3];
          const molecule = moleculeDatabase[i];

          return {
            name: molecule.name,
            component_type: componentType,
            chemical_formula: molecule.formula,
            smiles_notation: molecule.smiles,
            predicted_properties: {
              conductivity: 7 + Math.random() * 5,
              viscosity: 1.5 + Math.random() * 2,
              sei_formation_ability: Math.random(),
              flame_retardancy: Math.random()
            },
            source_papers: [Math.floor(i / 2) + 1],
            prediction_confidence: 0.75 + Math.random() * 0.2
          };
        })
      }
    };
  },

  // 处理文献数据
  processLiterature: async (data: { key_parameters: any; batch_size: number }) => {
    await delay(2500);

    return {
      success: true,
      data: {
        processed_papers: data.batch_size,
        extracted_molecules: 8,
        key_insights: [
          "EC/DMC混合溶剂具有优异的电化学性能",
          "LiPF6是目前最常用的锂盐",
          "VC和FEC添加剂能有效改善SEI膜形成"
        ],
        processing_summary: {
          total_papers_analyzed: 18,
          relevant_formulas_extracted: 12,
          confidence_score: 0.87,
          processing_time: "2.3秒"
        },
        literature_results: {
          papers_found: 25,
          molecules_identified: 8,
          key_formulas: [
            "EC:DMC = 1:1 (by volume)",
            "LiPF6 concentration = 1M",
            "VC additive = 2wt%, FEC additive = 5wt%"
          ],
          generated_molecules: Array.from({ length: 8 }, (_, i) => ({
            name: `文献分子_${i + 1}`,
            component_type: ["solvent", "salt", "additive"][i % 3],
            chemical_formula: `C${i + 2}H${i + 4}O${i + 1}`,
            predicted_properties: {
              conductivity: 7 + Math.random() * 5,
              viscosity: 1.5 + Math.random() * 2,
              sei_formation_ability: Math.random(),
              flame_retardancy: Math.random()
            },
            source_papers: [Math.floor(i / 2) + 1],
            prediction_confidence: 0.75 + Math.random() * 0.2
          }))
        }
      }
    };
  }
};

// 模拟API基础配置
const api = {
  post: async (url: string, data: any) => {
    await delay(1000);
    return { data: { success: true, data: data } };
  }
};

export default api;