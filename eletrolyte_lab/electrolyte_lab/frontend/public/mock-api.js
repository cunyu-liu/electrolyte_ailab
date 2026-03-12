// 临时的API模拟文件，用于测试前端功能
// 在浏览器控制台中运行这段代码来模拟API响应

(function() {
  console.log('设置模拟API响应...');

  // 模拟parseRequest API
  const originalPost = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method, url, ...args) {
    if (method === 'POST' && url.includes('/api/ai-designer/parse-request')) {
      this.addEventListener('load', function() {
        if (this.readyState === 4) {
          // 模拟成功响应
          const mockResponse = {
            success: true,
            data: {
              basic_info: {
                system_type: { value: "正极", confidence: 0.95, source: "规则解析+关键词匹配" },
                application_scenario: { value: "动力电池", confidence: 0.90, source: "场景词匹配" }
              },
              performance_params: {
                energy_density: { value: "280-320 Wh/kg", target_value: 300, unit: "Wh/kg", confidence: 0.85, source: "数值提取+上下文推理" },
                power_density: { value: "500-1000 W/kg", target_value: 750, unit: "W/kg", confidence: 0.80, source: "数值提取+上下文推理" },
                cycle_life: { value: "1500-2000 cycles", target_value: 1750, unit: "cycles", confidence: 0.88, source: "数值提取+上下文推理" },
                working_temperature: { value: "-20~60°C", range: { min: -20, max: 60 }, unit: "°C", confidence: 0.85, source: "温度范围提取" }
              },
              material_constraints: {
                positive_electrode: {
                  materials: ["NCM811", "高镍三元"],
                  preferred_material: "NCM811",
                  confidence: 0.82,
                  source: "材料关键词匹配+上下文推理"
                },
                negative_electrode: {
                  materials: ["石墨", "硅碳复合"],
                  preferred_material: "硅碳复合",
                  confidence: 0.78,
                  source: "材料关键词匹配"
                }
              },
              safety_requirements: {
                thermal_stability: { value: "通过热失控测试", confidence: 0.85, source: "安全词检测" },
                overcharge_protection: { value: "要求过充保护", confidence: 0.90, source: "安全词检测" }
              },
              cost_constraints: {
                target_cost: { value: "< 800元/kWh", target_value: 800, unit: "元/kWh", confidence: 0.75, source: "成本词检测" }
              }
            },
            message: "需求解析成功"
          };

          // 修改响应
          Object.defineProperty(this, 'response', {
            value: JSON.stringify(mockResponse),
            writable: false
          });
          Object.defineProperty(this, 'status', {
            value: 200,
            writable: false
          });

          console.log('模拟API响应已发送:', mockResponse);
        }
      });
    }
    return originalPost.call(this, method, url, ...args);
  };

  console.log('模拟API已设置。现在可以在AI设计员页面测试需求解析功能。');
})();