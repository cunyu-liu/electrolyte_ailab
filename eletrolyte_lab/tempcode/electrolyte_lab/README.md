# 悟行：智能电池设计与实验系统

## 🚀 环境配置

### 系统要求
- **Python**: 3.8+ (推荐3.9+)
- **Node.js**: 18+ (推荐LTS版本)
- **Anaconda**: 推荐使用Anaconda管理Python环境

### 后端环境配置 (使用Anaconda)
```bash
# 创建conda环境 
conda create -n battery-lab python=3.9

# 激活环境
conda activate battery-lab

# 进入后端目录
cd backend

# 安装依赖
pip install -r requirements.txt
```

### 前端环境配置
```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 修复React Scripts版本兼容性
npm install react-scripts@4.0.3
```

## 🎯 项目运行

### 方式一：一键启动 (推荐)
```bash
# 在项目根目录下运行
./start.sh

# 停止所有服务
./stop.sh
```

### 方式二：手动启动
```bash
# 后端 (终端1)
conda activate battery-lab
cd code
cd backend
PYTHONPATH=. python app.py

# 前端 (终端2)
conda activate battery-lab
cd code
cd frontend
NODE_OPTIONS="--openssl-legacy-provider" npm start
```

## 🌐 访问地址

- **前端界面**: http://localhost:3000
- **后端API**: http://localhost:5009