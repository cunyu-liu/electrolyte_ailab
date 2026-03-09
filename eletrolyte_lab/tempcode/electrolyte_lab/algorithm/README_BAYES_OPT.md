# 贝叶斯优化电解液配方系统

## 概述

这是一个基于贝叶斯优化的电解液配方智能推荐系统，能够：

1. **实验数据管理**：记录和管理电解液配方实验数据
2. **多指标优化**：同时优化多个性能指标（如保持率、容量、阻抗等）
3. **智能推荐**：基于历史数据推荐下一步最优实验配方
4. **闭环优化**：支持持续迭代改进配方

## 系统特性

- 🧠 **智能算法**：使用高斯过程和贝叶斯优化进行推荐
- 📊 **可视化界面**：直观的Web界面，易于操作
- 🔄 **闭环流程**：支持实验→优化→新实验的完整流程
- 📈 **多目标优化**：支持任意数量的性能指标
- 💾 **数据持久化**：自动保存所有实验数据和配置

## 安装和使用

### 1. 环境准备

确保已安装Python 3.8+，然后安装依赖：

```bash
cd algorithm
pip install -r requirements.txt
```

### 2. 启动系统

```bash
# 方法1：使用启动脚本
python start_bayes_opt.py

# 方法2：直接运行Flask应用
python bayes_opt_app.py
```

### 3. 访问系统

打开浏览器访问：http://localhost:5000

## 使用指南

### 添加实验

1. **输入配方**：
   - 输入10个溶剂的配比，总和应为1.0
   - 可以点击"归一化配方"自动调整

2. **输入指标**：
   - 根据实验结果输入各项性能指标
   - 系统会自动识别指标是最大化还是最小化

3. **添加备注**：
   - 可选输入实验备注信息

4. **保存数据**：
   - 点击"保存实验数据"将数据存入系统

### 优化建议

1. **设置权重**：
   - 为每个指标设置权重（总和应接近1.0）
   - 权重越高，该指标在优化中的重要性越大

2. **选择数量**：
   - 选择要生成的配方建议数量（3、5、10个）

3. **生成建议**：
   - 点击"生成优化建议"，系统会基于历史数据计算最优配方
   - 建议包含配方组成和置信度

4. **采用配方**：
   - 可以"采用此配方"进行下一步实验
   - 或"复制配方"供其他用途

### 历史数据

- 查看所有已记录的实验数据
- 包含配方概要、指标结果和备注信息
- 支持按时间排序查看

## 技术架构

### 后端架构

- **Flask**：Web框架，提供RESTful API
- **BoTorch**：贝叶斯优化库
- **GPyTorch**：高斯过程实现
- **PyTorch**：深度学习框架

### 核心算法

1. **数据预处理**：
   - 指标标准化和归一化
   - 配方向量归一化

2. **标量化**：
   - 多目标转换为单目标
   - 权重加权和

3. **高斯过程建模**：
   - SingleTaskGP建模配方-性能关系
   - 精确边际似然优化

4. **采集函数优化**：
   - qSimpleRegret获取最大可能收益
   - Sobol采样提高稳定性

5. **单纯形投影**：
   - 确保配方非负且和为1

### 数据格式

#### 实验数据结构
```json
{
  "id": "exp_1",
  "components": {
    "solvent_1": 0.10,
    "solvent_2": 0.05,
    ...
  },
  "metrics": {
    "retention": 0.92,
    "capacity": 180.0,
    "impedance": 50.0
  },
  "notes": "备注信息",
  "created_at": "2024-01-01T00:00:00"
}
```

#### 建议数据结构
```json
{
  "success": true,
  "suggestions": [
    {
      "id": "suggestion_1_1",
      "components": {...},
      "total_confidence": 0.85,
      "created_at": "2024-01-01T00:00:00"
    }
  ],
  "method": "bayesian_optimization",
  "data_size": 10
}
```

## API接口

### GET /api/metric-info
获取指标配置信息

### GET /api/experiments
获取所有实验数据

### POST /api/experiments
添加新的实验数据

### POST /api/suggest
生成优化建议
```json
{
  "weights": {"w_ret": 0.5, "w_cap": 0.4, "w_imp": 0.1},
  "n_candidates": 5
}
```

### GET /api/status
获取系统状态

## 自定义配置

### 修改指标类型

编辑`bayes_opt.py`中的`default_metrics`和指标信息：

```python
self.default_metrics = ["新指标1", "新指标2", "新指标3"]
self.metric_info = {
    'metrics': ["新指标1", "新指标2", "新指标3"],
    'descriptions': ['指标1描述', '指标2描述', '指标3描述'],
    'directions': ['maximize', 'maximize', 'minimize']
}
```

### 修改溶剂类型

通过Web界面或API更新`component_names`：

```python
self.component_names = ["新溶剂1", "新溶剂2", ...]
```

## 故障排除

### 常见问题

1. **依赖安装失败**：
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt --no-cache-dir
   ```

2. **CUDA相关错误**：
   - 系统会自动降级到CPU模式
   - 如需GPU加速，确保安装CUDA版本的PyTorch

3. **数据文件损坏**：
   - 删除`data/experiments.json`重新开始
   - 或从备份恢复

4. **端口占用**：
   - 修改`bayes_opt_app.py`中的端口号
   - 或停止占用5000端口的其他服务

### 调试模式

在`bayes_opt_app.py`中设置：
```python
app.run(host='0.0.0.0', port=5000, debug=True)
```

## 扩展功能

### 接入真实实验接口

修改`bayes_opt.py`中的建议生成部分，连接实际的实验数据源：

```python
def suggest_new_recipes(self, weights, n_candidates):
    # 1. 从真实API获取数据
    real_data = fetch_from_experimental_api()

    # 2. 转换数据格式
    X, Y = convert_real_data(real_data)

    # 3. 执行贝叶斯优化...
```

### 添加高级功能

1. **约束条件**：添加工艺约束（温度、压力等）
2. **批量优化**：支持同时优化多个配方
3. **模型选择**：支持不同的采集函数
4. **可视化分析**：添加Pareto前沿图等

## 联系支持

如遇到问题或需要功能扩展，请联系开发团队。

---

**版本信息**：v1.0.0
**最后更新**：2024年1月