#!/bin/bash

# 悟行：智能电池设计与实验系统停止脚本

echo "=== 停止悟行：智能电池设计与实验系统 ==="

# 读取进程ID
if [ -f ".backend.pid" ]; then
    BACKEND_PID=$(cat .backend.pid)
    echo "停止后端服务器 (PID: $BACKEND_PID)..."
    kill $BACKEND_PID 2>/dev/null
    rm .backend.pid
    echo "后端服务器已停止"
else
    echo "未找到后端进程ID文件"
fi

if [ -f ".frontend.pid" ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    echo "停止前端应用 (PID: $FRONTEND_PID)..."
    kill $FRONTEND_PID 2>/dev/null
    rm .frontend.pid
    echo "前端应用已停止"
else
    echo "未找到前端进程ID文件"
fi

# 强制停止相关进程
echo "清理相关进程..."
pkill -f "python app.py" 2>/dev/null
pkill -f "npm start" 2>/dev/null
pkill -f "react-scripts" 2>/dev/null

echo ""
echo "=== 系统已停止 ==="