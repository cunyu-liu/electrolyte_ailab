#!/bin/bash

# 悟行：智能电池设计与实验系统 - 完整启动脚本
# 包含所有已知问题的修复

echo "🚀 启动悟行：智能电池设计与实验系统..."
cd /Users/liucunyu/Documents/all_code/thu_2025/eletrolyte_lab/tempcode/electrolyte_lab
# 检查当前目录
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ 错误: 请在项目根目录下运行此脚本"
    echo "项目结构应包含 backend/ 和 frontend/ 目录"
    exit 1
fi

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: Python3 未安装"
    exit 1
fi

# 检查Node.js环境
if ! command -v node &> /dev/null; then
    echo "❌ 错误: Node.js 未安装"
    exit 1
fi

# 启动后端
echo "📊 启动后端Flask服务器..."
conda activate ailab
cd backend

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "📦 创建Python虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境并安装依赖
echo "📦 安装后端依赖..."
source venv/bin/activate

# 安装核心依赖（如果requirements.txt不存在）
if [ ! -f "requirements.txt" ]; then
    pip install flask flask-cors flask-sqlalchemy python-dotenv
else
    pip install -r requirements.txt
fi

# # 检查并创建关键配置文件
# if [ ! -f "extensions.py" ]; then
#     echo "🔧 创建 extensions.py 文件..."
#     cat > extensions.py << 'EOF'
# from flask_sqlalchemy import SQLAlchemy

# db = SQLAlchemy()
# EOF
# fi

if [ ! -f "app/__init__.py" ]; then
    echo "🔧 创建 app/__init__.py 文件..."
    mkdir -p app
    echo "# App package" > app/__init__.py
fi

# 创建环境变量文件（如果不存在）
if [ ! -f ".env" ]; then
    echo "🔧 创建 .env 文件..."
    cat > .env << 'EOF'
SECRET_KEY=dev-secret-key
DATABASE_URL=sqlite:///battery_lab.db
FLASK_ENV=development
EOF
fi

# 启动Flask应用（后台运行）
echo "🚀 启动Flask服务器 (端口 5002)..."
PYTHONPATH=. nohup python app.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ 后端服务器已启动 (PID: $BACKEND_PID)"

cd ..

# 启动前端
echo "🌐 启动前端React应用..."
cd frontend
conda activate ailab


# 安装前端依赖
if [ ! -d "node_modules" ]; then
    echo "📦 安装前端依赖..."
    npm install
fi

# 检查并修复react-scripts版本兼容性问题
if grep -q '"react-scripts": "^5.0.1"' package.json; then
    echo "🔧 修复 react-scripts 版本兼容性..."
    npm install react-scripts@4.0.3
fi

# 创建日志目录
mkdir -p ../logs

# 启动React应用（后台运行，使用OpenSSL兼容选项）
echo "🚀 启动React开发服务器 (端口 3000)..."
NODE_OPTIONS="--openssl-legacy-provider" nohup npm start > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ 前端应用已启动 (PID: $FRONTEND_PID)"

cd ..

# 保存进程ID
echo $BACKEND_PID > .backend.pid
echo $FRONTEND_PID > .frontend.pid

echo ""
echo "🎉 === 系统启动完成 ==="
echo "📊 后端API服务器: http://localhost:5002"
echo "🌐 前端应用界面: http://localhost:3000"
echo "📝 后端日志: logs/backend.log"
echo "📝 前端日志: logs/frontend.log"
echo ""
echo "⚠️  停止系统请运行: ./stop.sh 或 kill $BACKEND_PID $FRONTEND_PID"
echo ""

# 等待几秒钟确保服务启动
sleep 5

# 检查服务状态
echo "🔍 检查服务状态..."
if kill -0 $BACKEND_PID 2>/dev/null; then
    echo "✅ 后端服务运行正常"
    if curl -s http://localhost:5002 > /dev/null; then
        echo "✅ 后端API响应正常"
    else
        echo "⚠️  后端API可能还在启动中..."
    fi
else
    echo "❌ 后端服务启动失败，请检查 logs/backend.log"
fi

if kill -0 $FRONTEND_PID 2>/dev/null; then
    echo "✅ 前端服务运行正常"
    echo "⏳ 前端编译可能需要1-2分钟，请耐心等待..."
else
    echo "❌ 前端服务启动失败，请检查 logs/frontend.log"
fi

echo ""
echo "🎯 系统启动完成！请访问 http://localhost:3000 使用悟行：智能电池设计与实验系统"
echo ""
echo "📚 如果遇到问题，请参考 SETUP_GUIDE.md 文件"