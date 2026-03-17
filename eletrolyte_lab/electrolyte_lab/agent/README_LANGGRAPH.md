# 悟行 - LangGraph 重构版说明

## 🎯 重构核心变化

### 原架构 vs LangGraph 架构

| 维度 | 原架构 (agent_rag_v8_1.py) | LangGraph 重构版 |
|------|--------------------------|-----------------|
| **架构模式** | 自研 MessageBus + SharedMemory | LangGraph StateGraph |
| **Agent协作** | 异步消息队列 | 图节点 + 边（Edge）路由 |
| **状态管理** | 手动实现 SharedMemory | LangGraph State + MemorySaver |
| **流程控制** | 自定义 ReAct++ 循环 | LangGraph 条件边 + 循环 |
| **可观测性** | 手动实现 Tracer | LangGraph 内置 State 检查点 |
| **人机协同** | 自定义实现 | LangGraph 中断点（interrupt）支持 |

## 🏗️ 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     LangGraph StateGraph                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   START                                                        │
│     │                                                          │
│     ▼                                                          │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐      │
│  │Orchestrator │────▶│  Literature │     │  Molecular  │      │
│  │   (指挥官)   │     │   (文献)     │     │   (分子)     │      │
│  └─────────────┘     └──────┬──────┘     └──────┬──────┘      │
│         │                   │                   │              │
│         │              ┌────┴────┐         ┌────┴────┐         │
│         │              │         │         │         │         │
│         └─────────────▶│   QC    │◀────────┘         │         │
│                        │ (质检)   │◀──────────────────┘         │
│                        └────┬─────┘                            │
│                             │                                   │
│                    ┌────────┴────────┐                         │
│                    │   条件边路由     │                         │
│                    │ approved? score │                         │
│                    └────────┬────────┘                         │
│              ┌──────────────┼──────────────┐                  │
│              │              │              │                   │
│              ▼              │              ▼                   │
│        ┌──────────┐         │       ┌──────────┐              │
│        │Executor  │         │       │Orchestrator│            │
│        │ (执行)    │         │       │ (重新规划) │            │
│        └────┬─────┘         │       └──────────┘              │
│             │               │                                   │
│             └───────────────┘                                   │
│                             │                                   │
│                             ▼                                   │
│                       ┌──────────┐                              │
│                       │Synthesizer│                             │
│                       │ (综合)   │                             │
│                       └────┬─────┘                              │
│                            │                                    │
│                            ▼                                    │
│                           END                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install langgraph langchain langchain-openai langchain-core
pip install fastapi uvicorn pydantic
pip install sentence-transformers FlagEmbedding pymilvus elasticsearch
```

### 2. 设置环境变量

```bash
export DEEPSEEK_API_KEY="your-api-key"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
```

### 3. 启动服务

```bash
cd agent
python agent_langgraph.py
```

### 4. 测试接口

```bash
# 健康检查
curl http://localhost:8000/health

# 发起对话
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "设计一款高电压电解液"}'

# 查看工作流状态
curl http://localhost:8000/workflow/status/{thread_id}
```

## 📊 核心改进点

### 1. 状态管理简化

**原架构：**
```python
class SharedMemory:
    def __init__(self):
        self._state = {}
        self._workflows = {}
        self._agent_states = {}
        # 需要手动实现锁和序列化
```

**LangGraph：**
```python
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], "add_messages"]
    task_id: str
    literature_findings: List[Dict]
    # ... 自动由框架管理
```

### 2. 流程控制声明式

**原架构：**
```python
# 手动实现状态机和路由逻辑
while priority_queue:
    message = await self.message_bus.get_message(agent_id)
    # 复杂的路由逻辑...
```

**LangGraph：**
```python
# 声明式定义
workflow.add_conditional_edges(
    "orchestrator",
    route_by_task_type,
    {"literature": "literature", "molecular": "molecular", ...}
)
```

### 3. 可观测性增强

```python
# 随时获取工作流状态
state = app.get_state({"configurable": {"thread_id": thread_id}})
print(state.values["execution_history"])
```

### 4. 人机协同支持

```python
# 可以在任意节点设置中断点，等待人工确认
workflow.add_node("human_review", human_review_node)
workflow.add_edge("qc", "human_review")
workflow.add_edge("human_review", "executor")
```

## 🔧 扩展开发

### 添加新Agent

```python
# 1. 定义节点函数
def new_agent_node(state: AgentState) -> AgentState:
    # 实现逻辑
    return state

# 2. 添加到图
workflow.add_node("new_agent", new_agent_node)

# 3. 定义边
workflow.add_edge("orchestrator", "new_agent")
workflow.add_edge("new_agent", "qc")
```

### 添加新工具

```python
from langchain_core.tools import tool

@tool
def new_tool(param: str) -> str:
    """工具描述"""
    return f"结果: {param}"

# 绑定到Agent
llm = llm_service.get_client().bind_tools([new_tool])
```

## 📈 性能对比

| 指标 | 原架构 | LangGraph |
|------|--------|-----------|
| 代码行数 | ~8200 行 | ~700 行（核心逻辑）|
| 状态管理复杂度 | 高（手动实现） | 低（框架托管） |
| 调试难度 | 困难（异步消息追踪） | 简单（State 可视化） |
| 社区支持 | 无 | 活跃（LangChain官方） |
| 文档完善度 | 自建文档 | 完善官方文档 |

## 🎓 学习资源

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangGraph 概念介绍](https://langchain-ai.github.io/langgraph/concepts/)
- [多Agent系统最佳实践](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/multi-agent-collaboration/)

## ⚠️ 注意事项

1. **API Key 安全**：生产环境务必使用安全的密钥管理方式
2. **状态持久化**：当前使用 MemorySaver，生产环境建议换为 Redis 或数据库
3. **错误处理**：建议添加更完善的异常处理和重试机制
4. **流式输出**：如需流式响应，可使用 `app.astream()` 方法
