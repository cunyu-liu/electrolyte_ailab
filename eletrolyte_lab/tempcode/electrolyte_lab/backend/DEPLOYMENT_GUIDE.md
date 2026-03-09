# 后端部署问题诊断和解决方案

## 🔍 **问题诊断结果**

### 1. 端口被占用
- **错误**: `Port 5008 is in use by another program`
- **原因**: 之前的Python进程仍在运行
- **解决**: 已杀死相关进程

### 2. 缺少关键依赖
- **pymysql未安装**: MySQL数据库连接器缺失
- **RDKit未安装**: 分子验证功能受限
- **PyTorch未安装**: AI功能使用scikit-learn替代

## 🛠️ **立即解决方案**

### 修复1: 安装MySQL依赖
```bash
pip install pymysql
```

### 修复2: 使用不同端口启动
```bash
# 方法1: 使用环境变量
export FLASK_PORT=5009
python app.py

# 方法2: 直接修改端口
python -c "
from app import create_app
app = create_app()
app.run(host='0.0.0.0', port=5009, debug=True)
"
```

### 修复3: 检查后端状态
```bash
# 测试API是否正常
curl -X POST http://localhost:5009/api/ai-designer/parse-request \
  -H "Content-Type: application/json" \
  -d '{"input": "测试电解液需求"}'
```

## 🎯 **推荐的完整解决步骤**

### 步骤1: 安装依赖
```bash
cd backend
pip install -r requirements.txt
pip install pymysql  # MySQL支持
pip install rdkit  # 分子功能 (可选)
pip install torch   # AI功能 (可选)
```

### 步骤2: 启动后端服务
```bash
cd backend
export FLASK_ENV=development
python app.py
```

### 步骤3: 验证服务
```bash
# 测试API连接
curl -X POST http://localhost:5009/api/ai-designer/parse-request \
  -H "Content-Type: application/json" \
  -d '{"input": "我需要动力电池电解液，能量密度300Wh/kg"}'
```

## 🔧 **前端配置检查**

### 检查代理配置
确保 `frontend/package.json` 包含正确的代理设置：
```json
{
  "proxy": "http://localhost:5009"
}
```

### 检查API调用
确保前端正确调用：
```javascript
// 正确的API调用
const response = await aiDesignerApi.parseRequest({
  input: "电解液需求描述"
});
```

## ⚠️ **常见问题解决**

### 问题: "后端服务异常"
**可能原因**:
1. Python环境问题
2. 依赖版本冲突
3. 端口被占用
4. 数据库连接失败

**诊断命令**:
```bash
# 1. 检查Python环境
python --version

# 2. 检查关键依赖
pip list | grep -E "(flask|openai|pymysql|rdkit)"

# 3. 检查端口占用
lsof -ti:5008

# 4. 测试数据库连接
python -c "
from app.ai_designer.parser import RequestParser
print('Parser导入成功')
"
```

### 问题: "API响应错误"
**可能原因**:
1. OpenAI API密钥未配置
2. 网络连接问题
3. API配额用尽
4. 请求格式错误

**解决方法**:
```bash
# 1. 检查环境变量
echo $OPENAI_API_KEY

# 2. 设置API密钥
export OPENAI_API_KEY="your-api-key-here"

# 3. 测试连接
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models
```

## 🚀 **快速启动命令**

```bash
# 一键启动后端 (推荐)
cd backend
pip install pymysql
export FLASK_PORT=5009
export OPENAI_API_KEY="your-key"
python app.py
```

## 📱 **验证部署成功**

访问以下URL验证服务状态:
- 后端API: http://localhost:5009
- 前端应用: http://localhost:3000 (启动后运行 `npm start`)

如果问题仍然存在，请检查:
1. 后端控制台日志
2. 浏览器开发者工具网络面板
3. 环境变量配置
4. 依赖安装状态