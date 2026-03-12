# True Multi-Agent Architecture v7

## 架构概述

这是一个**真正的多智能体系统**，区别于传统的流水线架构，实现了：

1. **LLM动态规划** - Agent自主决策下一步行动
2. **LLM自主选择工具** - Agent根据上下文推理选择最合适的工具
3. **自然语言对话** - 支持交互式多轮对话
4. **LLM推理** - ReAct模式的思考-行动-观察循环
5. **执行后自我评估** - 每步执行后的反思和改进

## 与v6的关键区别

| 特性 | v6 (流水线) | v7 (真正多智能体) |
|------|------------|------------------|
| 规划方式 | Master硬编码状态机 | PlanningAgent LLM动态规划 |
| 工具选择 | 预定义流程 | ReasoningAgent自主推理选择 |
| 决策能力 | 无，被动执行 | 有，主动决策 |
| 自我评估 | 无 | EvaluationAgent深度评估 |
| 自然语言交互 | 有限 | ChatAgent完整对话管理 |
| 错误恢复 | 固定重试 | LLM推理调整策略 |
| 灵活性 | 低 | 高 |

## 核心Agent角色

### 1. OrchestratorAgent (中央协调者)
```
职责：
- 接收用户请求
- 创建和管理工作流
- 协调Agent间协作
- 监控执行状态

工作流程：
用户请求 → 创建工作流 → 派发给PlanningAgent → 接收规划结果 → 
派发给ReasoningAgent → 接收执行结果 → 派发给EvaluationAgent → 
返回最终结果
```

### 2. PlanningAgent (规划者)
```
职责：
- 理解复杂目标
- 将目标分解为可执行步骤
- 识别步骤间依赖关系
- 估算复杂度

关键方法：
- _create_plan(): 使用LLM动态生成计划
- 输出包含步骤描述、工具选择、成功标准
```

### 3. ReasoningAgent (推理执行者)
```
职责：
- 理解任务目标
- 使用ReAct循环自主决策
- 自主选择工具
- 动态调整策略
- 执行后自我评估

ReAct循环：
思考(Thought) → 选择行动(Action) → 执行(Execute) → 
观察(Observation) → 评估(Evaluate) → 下一轮/完成

关键方法：
- think(): LLM推理决策
- _react_loop(): ReAct执行循环
- evaluate(): 自我评估
```

### 4. ToolExecutorAgent (工具执行者)
```
职责：
- 实际执行工具调用
- 封装RAG操作
- 处理工具执行异常

工具列表：
- literature_deep_search: 深度文献检索
- extract_chemical_entities: 化学实体提取
- molecular_design: 分子设计
- property_prediction: 性质预测
- formulate_recipe: 配方生成
- run_simulation: 运行模拟
- analyze_results: 结果分析
- optimize_parameters: 参数优化
- web_search: 网络搜索
- ask_user: 询问用户
```

### 5. EvaluationAgent (评估反思者)
```
职责：
- 质量评估（正确性、完整性、效率、鲁棒性）
- 错误分析
- 改进建议
- 经验总结

评估维度：
- overall_score: 综合评分
- correctness: 正确性
- completeness: 完整性
- efficiency: 效率
- strengths/weaknesses: 优缺点
- errors: 错误分析
- recommendations: 改进建议
```

### 6. ChatAgent (对话管理者)
```
职责：
- 理解用户自然语言输入
- 维护对话上下文
- 多轮对话管理
- 任务委派识别

能力：
- 意图分析（chat/task/clarification）
- 流式回复生成
- 知识增强回答（结合RAG）
```

### 7. MemoryAgent (记忆管理者)
```
职责：
- 工作记忆管理
- 重要信息提取
- 记忆检索
- 知识整合
```

## 通信机制

### MessageBus (消息总线)
```python
# 松耦合异步通信
- register_agent(): 注册Agent
- send(): 发送消息
- get_message(): 接收消息
- subscribe(): 订阅特定消息类型
```

### MessageType (消息类型)
```python
TASK_ASSIGN      # 任务分配
TASK_RESULT      # 任务结果
PLAN_REQUEST     # 请求规划
PLAN_RESPONSE    # 规划响应
TOOL_CALL        # 工具调用
TOOL_RESULT      # 工具结果
REASONING        # 推理过程
EVALUATION       # 评估结果
CHAT_MESSAGE     # 聊天消息
MEMORY_UPDATE    # 记忆更新
SYSTEM_EVENT     # 系统事件
```

### SharedMemory (共享内存)
```python
# 所有Agent可访问的状态存储
- create_workflow(): 创建工作流
- store_plan(): 存储计划
- add_conversation_turn(): 添加对话轮次
- store/retrieve(): 通用存储检索
```

## ReAct模式详解

### 标准格式
```
Thought: 详细分析当前情况，思考应该采取什么行动
Action: 选择的工具名称
Action Input: {"参数名": "参数值"}
Reasoning: 解释为什么选择这个行动
```

### 示例流程
```
用户: "研发高电压电解液"

Thought: 用户需要研发高电压电解液。这是一个复杂任务，我需要先检索相关
       文献了解最新研究进展，然后提取关键化学实体，设计配方。
Action: literature_deep_search
Action Input: {"query": "高电压电解液 4.5V以上", "depth": 2, "breadth": 3}
Reasoning: 首先需要了解高电压电解液的研究现状和关键材料

[执行工具...]

Observation: 检索到15篇相关文献，关键材料包括LiPF6、FEC、氟代溶剂等

Thought: 文献检索成功。我发现了关键材料信息。下一步应该提取具体的化学
       实体，以便进行分子设计。
Action: extract_chemical_entities
Action Input: {"text": "文献内容..."}
Reasoning: 需要从文献中提取具体的化学物质用于后续设计

[继续循环直到完成任务...]

Thought: 已完成配方设计和模拟实验。实验结果达到了目标性能指标。
       可以结束任务并返回结果。
Action: finish
Action Input: {"answer": "成功研发高电压电解液配方..."}
Reasoning: 任务目标已达成，提供完整的研发报告
```

## API端点

### 1. 对话端点
```http
POST /chat
{
    "message": "你好，我想了解高电压电解液",
    "session_id": "可选",
    "stream": false
}

Response:
{
    "session_id": "xxx",
    "status": "success",
    "result": {
        "type": "chat",
        "content": "高电压电解液是指..."
    }
}
```

### 2. 流式对话
```http
POST /chat/stream
Content-Type: text/event-stream

data: {"token": "高"}
data: {"token": "电压"}
data: {"token": "电解液"}
...
data: {"done": true}
```

### 3. 任务执行
```http
POST /task
{
    "goal": "研发4.5V高电压电解液，库伦效率>99.5%",
    "context": {"target_ce": 99.5, "voltage": 4.5},
    "mode": "auto"
}

Response:
{
    "workflow_id": "wf_xxx",
    "status": "started",
    "message": "Task workflow initiated"
}
```

### 4. 查询状态
```http
GET /workflow/{workflow_id}

Response:
{
    "workflow_id": "wf_xxx",
    "goal": "...",
    "status": "running",
    "current_agent": "reasoning_agent",
    "results": [...]
}
```

### 5. 提供澄清
```http
POST /workflow/{workflow_id}/clarify
{
    "clarification": "我希望优先保证循环寿命"
}
```

## 自我评估机制

### 评估时机
1. 每个工具执行后
2. 任务完成后
3. 失败重试前

### 评估内容
```python
{
    "success": true/false,           # 是否成功
    "quality_score": 0.0-1.0,        # 质量评分
    "analysis": "详细分析",           # 执行分析
    "suggestions": ["建议1", ...],   # 改进建议
    "should_retry": true/false       # 是否重试
}
```

### 评估应用
- **成功但质量低**: 尝试优化
- **失败可重试**: 调整策略重试
- **失败不可恢复**: 报错并解释

## 优势对比

### v6架构的问题
```python
# v6: 硬编码状态机
async def _handle_result(self, message):
    if task == "requirement_analysis":
        await self._goto_literature_retrieval()  # 固定流程
    elif task == "literature_retrieval":
        await self._goto_knowledge_mining()      # 无法跳过
    # ... 完全固定的流程
```

### v7架构的优势
```python
# v7: LLM动态决策
async def _react_loop(self, ...):
    for iteration in range(max_iterations):
        decision = await self.think(...)  # LLM自主决策
        # decision["action"] 可以是任意工具或 finish
        # 根据上下文动态选择最优路径
```

## 使用示例

### 示例1: 简单问答
```python
import requests

# 自然语言问答
response = requests.post("http://localhost:8000/chat", json={
    "message": "什么是FEC在电解液中的作用？"
})
print(response.json())
# 输出: 基于知识库的专业回答
```

### 示例2: 复杂任务
```python
# 启动研发任务
response = requests.post("http://localhost:8000/task", json={
    "goal": "研发适用于4.5V NCM正极的电解液，要求库伦效率>99.5%",
    "context": {"priority": "high_voltage", "temperature_range": "-20~60"}
})
workflow_id = response.json()["workflow_id"]

# 查询进度
import time
while True:
    status = requests.get(f"http://localhost:8000/workflow/{workflow_id}").json()
    print(f"Status: {status['status']}, Current: {status.get('current_agent')}")
    
    if status["status"] in ["completed", "failed", "awaiting_clarification"]:
        break
    time.sleep(2)

# 如果需要澄清
if status["status"] == "awaiting_clarification":
    requests.post(f"http://localhost:8000/workflow/{workflow_id}/clarify", json={
        "clarification": "成本优先，可以使用FEC"
    })
```

### 示例3: 流式对话
```python
import requests

response = requests.post("http://localhost:8000/chat/stream", json={
    "message": "详细解释电解液配方设计的原则",
    "stream": True
}, stream=True)

for line in response.iter_lines():
    if line:
        data = json.loads(line.decode().replace("data: ", ""))
        if data.get("done"):
            break
        print(data.get("token", ""), end="", flush=True)
```

## 扩展开发

### 添加新工具
```python
# 1. 在ToolRegistry中注册
class ToolRegistry:
    TOOLS = {
        "my_new_tool": {
            "description": "工具描述",
            "parameters": {
                "param1": {"type": "string", "required": True}
            }
        }
    }

# 2. 在ToolExecutorAgent中实现
async def _do_execute(self, tool_name, parameters):
    if tool_name == "my_new_tool":
        return await self._my_new_tool(parameters)

async def _my_new_tool(self, params):
    # 实现逻辑
    return {"status": "success", "result": ...}
```

### 添加新Agent
```python
class MyNewAgent(TrueAgent):
    def __init__(self, **kwargs):
        super().__init__(
            agent_id="my_new_agent",
            system_prompt="你是MyNewAgent...",
            **kwargs
        )
    
    async def _handle_task_assignment(self, message):
        # 实现任务处理逻辑
        pass
```

## 性能考虑

### 优化建议
1. **LLM调用缓存**: 对重复的think操作进行缓存
2. **并行执行**: 独立的工具调用可以并行
3. **流式响应**: 长文本生成使用流式
4. **超时控制**: 设置合理的执行超时

### 资源需求
- GPU: 至少8GB显存用于Qwen3-0.6B
- 内存: 16GB+
- Milvus: 向量数据库
- Elasticsearch: 全文检索

## 总结

True Multi-Agent Architecture v7 实现了从"流水线执行者"到"自主决策者"的转变：

1. ✅ **LLM动态规划**: PlanningAgent根据目标动态生成计划
2. ✅ **LLM自主选择工具**: ReasoningAgent根据上下文推理选择工具
3. ✅ **自然语言对话**: ChatAgent支持完整的对话交互
4. ✅ **LLM推理**: ReAct模式的思考-行动-观察循环
5. ✅ **执行后自我评估**: EvaluationAgent提供深度质量评估

这是一个真正的多智能体系统，每个Agent都是具备自主决策能力的智能体，而非被动的执行者。
