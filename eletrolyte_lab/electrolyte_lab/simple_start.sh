#!/bin/bash

# 简单启动脚本 - 无需复杂依赖的版本

echo "🚀 启动 AI Battery Lab (文件存储版本)"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3"
    exit 1
fi

# 创建数据目录
echo "📁 创建数据目录..."
mkdir -p data/molecules data/literature/formulas data/literature/associations logs

# 启动后端
echo "🔧 启动后端服务..."
cd backend

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装基本依赖
echo "📦 安装基础依赖..."
pip install flask flask-cors requests python-dotenv marshmallow

# 启动后端服务
echo "🌟 启动后端服务 (端口 5003)..."
PYTHONPATH=. python app.py &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 检查后端是否启动成功
if curl -s http://localhost:5003/api/ai-designer/formulas > /dev/null; then
    echo "✅ 后端服务启动成功!"
else
    echo "❌ 后端服务启动失败"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# 检查Node.js环境
if command -v node &> /dev/null; then
    echo "📱 启动前端服务..."
    cd ../frontend

    # 检查是否已安装依赖
    if [ ! -d "node_modules" ]; then
        echo "📦 安装前端依赖..."
        npm install
    fi

    # 启动前端
    echo "🌟 启动前端服务 (端口 3000)..."
    NODE_OPTIONS="--openssl-legacy-provider" npm start &
    FRONTEND_PID=$!

    echo "✅ AI Battery Lab 启动完成!"
    echo ""
    echo "📱 前端地址: http://localhost:3000"
    echo "🔧 后端API: http://localhost:5003"
    echo ""
    echo "💡 提示: 按 Ctrl+C 停止服务"
    echo ""

    # 等待用户中断
    wait

    # 停止服务
    kill $FRONTEND_PID 2>/dev/null
    kill $BACKEND_PID 2>/dev/null

else
    echo "⚠️  Node.js未找到，仅启动后端服务"
    echo "💡 手动启动前端:"
    echo "   cd frontend"
    echo "   npm install"
    echo "   NODE_OPTIONS=\"--openssl-legacy-provider\" npm start"
    echo ""
    echo "按 Ctrl+C 停止后端服务"
    wait $BACKEND_PID
    kill $BACKEND_PID 2>/dev/null
fi

echo "👋 AI Battery Lab 已停止"