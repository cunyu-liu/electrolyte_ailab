# Agent Chat - 网页对话系统

独立的 Agent 网页对话系统，可以直接在浏览器中与 ChemMind Agent 进行对话。

## 特点

- 💬 实时对话，支持流式输出（打字机效果）
- 📚 自动显示引用文献（已去重）
- 📊 显示任务分类、质量评分等元信息
- 🎯 内置示例快捷输入
- 🔄 支持重置对话
- 🚀 独立运行，不依赖项目其他前后端

## 文件结构

```
agent_chat/
├── server.py     # Flask 后端服务器
├── index.html    # 前端聊天界面
└── README.md     # 本文件
```

## 使用方法

### 1. 启动服务器

```bash
cd agent_chat
python server.py
```

首次启动会自动初始化 Agent（可能需要一些时间加载模型）。

### 2. 打开浏览器访问

```
http://localhost:8889
```

### 3. 开始对话

- 在输入框输入问题，按 Enter 发送
- 或点击示例按钮快速输入
- 支持 Shift+Enter 换行

## 示例问题

| 类型 | 示例 |
|------|------|
| 文献研究 | 锂离子电池高电压电解液添加剂研究进展 |
| 性质预测 | 预测碳酸乙烯酯(EC)的离子电导率 |
| 配方设计 | 设计一个4.5V高电压电解液配方 |
| 知识问答 | SEI膜的形成机理是什么？ |

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/chat` | POST | 普通对话（非流式） |
| `/api/chat/stream` | POST | 流式对话（SSE） |
| `/api/reset` | POST | 重置 Agent |

## 依赖

```bash
pip install flask flask-cors
```

注：Agent 本身的依赖（如 PyTorch、Transformers 等）需要已安装。

## 端口配置

默认端口 `8889`，如需修改，编辑 `server.py` 中的 `PORT` 变量。

## 日志

对话日志会自动保存到 `test_logs/web_chat_YYYYMMDD_HHMMSS/` 目录。
