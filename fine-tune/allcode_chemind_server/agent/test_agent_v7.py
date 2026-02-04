"""
True Multi-Agent System v7 测试脚本

演示如何使用真正的多智能体架构：
1. LLM动态规划
2. LLM自主选择工具
3. 自然语言对话
4. LLM推理
5. 执行后自我评估
"""

import asyncio
import json
import aiohttp
from typing import Dict, Any
import sys

# API基础URL
BASE_URL = "http://localhost:8000"

# 设置超时 - 模型生成需要较长时间
CLIENT_TIMEOUT = aiohttp.ClientTimeout(total=1200, connect=100, sock_read=1200)


async def test_chat_simple():
    """测试简单对话 - 展示自然语言交互能力"""
    print("\n" + "="*60)
    print("测试1: 简单对话问答")
    print("="*60)
    
    questions = [
        "什么是FEC在电解液中的作用？",
        "高电压电解液面临哪些挑战？",
        "LiPF6和LiFSI有什么区别？"
    ]
    
    async with aiohttp.ClientSession(timeout=CLIENT_TIMEOUT) as session:
        for q in questions:
            print(f"\n用户: {q}")
            
            async with session.post(
                f"{BASE_URL}/chat",
                json={"message": q}
            ) as resp:
                result = await resp.json()
                
                if result.get("status") == "success":
                    content = result.get("result", {}).get("content", "")
                    print(f"助手: {content}...")
                else:
                    print(f"错误: {result}")


async def test_chat_stream():
    """测试流式对话 - 展示实时响应能力"""
    print("\n" + "="*60)
    print("测试2: 流式对话")
    print("="*60)
    
    async with aiohttp.ClientSession(timeout=CLIENT_TIMEOUT) as session:
        print(f"\n用户: 详细解释电解液配方设计的原则")
        print("助手: ", end="", flush=True)
        
        async with session.post(
            f"{BASE_URL}/chat/stream",
            json={"message": "详细解释电解液配方设计的原则"}
        ) as resp:
            async for line in resp.content:
                line = line.decode().strip()
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if data.get("done"):
                            break
                        token = data.get("token", "")
                        print(token, end="", flush=True)
                    except:
                        pass
        print()  # 换行


async def test_task_workflow():
    """测试复杂任务工作流 - 展示LLM动态规划和自主决策"""
    print("\n" + "="*60)
    print("测试3: 复杂任务工作流")
    print("="*60)
    
    async with aiohttp.ClientSession(timeout=CLIENT_TIMEOUT) as session:
        # 启动任务
        goal = "研发适用于4.5V NCM正极的电解液，要求库伦效率>99.5%"
        print(f"\n任务目标: {goal}")
        
        async with session.post(
            f"{BASE_URL}/task",
            json={
                "goal": goal,
                "context": {
                    "target_ce": 99.5,
                    "voltage": 4.5,
                    "priority": "high_voltage"
                }
            }
        ) as resp:
            result = await resp.json()
            workflow_id = result.get("workflow_id")
            print(f"工作流ID: {workflow_id}")
            print(f"状态: {result.get('status')}")
        
        # 轮询状态
        print("\n监控执行进度:")
        max_polls = 30
        for i in range(max_polls):
            await asyncio.sleep(2)
            
            async with session.get(
                f"{BASE_URL}/workflow/{workflow_id}"
            ) as resp:
                status = await resp.json()
                
                current_agent = status.get("current_agent", "unknown")
                workflow_status = status.get("status", "unknown")
                
                print(f"  [{i+1}] Agent: {current_agent:20s} | Status: {workflow_status}")
                
                if workflow_status in ["completed", "failed"]:
                    print(f"\n最终结果:")
                    print(json.dumps(status, indent=2, ensure_ascii=False)[:1000])
                    break
                
                if workflow_status == "awaiting_clarification":
                    print(f"\n需要澄清: {status.get('clarification_question', '')}")
                    # 提供澄清
                    async with session.post(
                        f"{BASE_URL}/workflow/{workflow_id}/clarify",
                        json={"clarification": "优先考虑循环寿命，成本其次"}
                    ) as resp:
                        print("已提供澄清，继续执行...")
        else:
            print("\n达到最大轮询次数")


async def test_deep_research():
    """测试深度研究 - 展示知识检索能力"""
    print("\n" + "="*60)
    print("测试4: 深度研究")
    print("="*60)
    
    async with aiohttp.ClientSession(timeout=CLIENT_TIMEOUT) as session:
        queries = [
            {
                "query": "高电压电解液添加剂 FEC VC",
                "depth": 2,
                "breadth": 3
            },
            {
                "query": "固态电解质界面 SEI 形成机制",
                "depth": 1,
                "breadth": 2
            }
        ]
        
        for q in queries:
            print(f"\n研究问题: {q['query']}")
            print(f"搜索深度: {q['depth']}, 广度: {q['breadth']}")
            
            async with session.post(
                f"{BASE_URL}/research/deep",
                json=q
            ) as resp:
                result = await resp.json()
                
                if result.get("status") == "success":
                    print(f"找到 {result.get('results_count')} 条结果")
                    for i, r in enumerate(result.get("results", [])[:3], 1):
                        content = r.get("content", "")[:100]
                        score = r.get("score", 0)
                        print(f"  [{i}] (score: {score:.3f}) {content}...")
                else:
                    print(f"错误: {result}")


async def test_multi_turn_dialog():
    """测试多轮对话 - 展示上下文理解能力"""
    print("\n" + "="*60)
    print("测试5: 多轮对话")
    print("="*60)
    
    session_id = None
    conversation = [
        "我想研发一种新型电解液",
        "用于高电压正极材料",
        "4.5V以上的",
        "有哪些关键材料推荐？"
    ]
    
    async with aiohttp.ClientSession(timeout=CLIENT_TIMEOUT) as session:
        for msg in conversation:
            print(f"\n用户: {msg}")
            
            payload = {"message": msg}
            if session_id:
                payload["session_id"] = session_id
            
            async with session.post(
                f"{BASE_URL}/chat",
                json=payload
            ) as resp:
                result = await resp.json()
                
                session_id = result.get("session_id")
                content = result.get("result", {}).get("content", "")
                print(f"助手: {content}...")


async def test_health_check():
    """测试健康检查"""
    print("\n" + "="*60)
    print("测试6: 系统健康检查")
    print("="*60)
    
    async with aiohttp.ClientSession(timeout=CLIENT_TIMEOUT) as session:
        async with session.get(f"{BASE_URL}/health") as resp:
            health = await resp.json()
            print(f"\n系统状态: {health.get('status')}")
            print(f"已加载Agent: {', '.join(health.get('agents', []))}")
            print(f"LLM加载状态: {'已加载' if health.get('llm_loaded') else '未加载'}")


async def test_react_reasoning():
    """
    测试ReAct推理过程 - 展示Agent的自主决策过程
    
    这个测试会展示Agent如何：
    1. 分析问题
    2. 选择工具
    3. 执行并观察
    4. 评估结果
    5. 调整策略
    """
    print("\n" + "="*60)
    print("测试7: ReAct推理过程演示")
    print("="*60)
    
    async with aiohttp.ClientSession(timeout=CLIENT_TIMEOUT) as session:
        # 启动一个需要多步推理的任务
        goal = "分析高电压电解液的失效机制并提出改进方案"
        
        print(f"\n复杂任务: {goal}")
        print("\n这个任务将展示Agent的ReAct推理过程:")
        print("  1. Thought: LLM分析问题并决定行动")
        print("  2. Action: 选择合适的工具")
        print("  3. Observation: 观察执行结果")
        print("  4. Evaluation: 自我评估")
        print("  5. 重复直到完成")
        
        async with session.post(
            f"{BASE_URL}/task",
            json={
                "goal": goal,
                "context": {"analysis_depth": "detailed"}
            }
        ) as resp:
            result = await resp.json()
            workflow_id = result.get("workflow_id")
            print(f"\n工作流ID: {workflow_id}")
        
        # 详细监控每一步
        print("\n详细执行过程:")
        step_count = 0
        while step_count < 50:
            await asyncio.sleep(1)
            
            async with session.get(
                f"{BASE_URL}/workflow/{workflow_id}"
            ) as resp:
                status = await resp.json()
                
                workflow_status = status.get("status")
                if workflow_status != "running":
                    # 获取详细结果
                    results = status.get("results", [])
                    if results:
                        print(f"\n执行历史 ({len(results)} 步):")
                        for i, r in enumerate(results[-5:], 1):
                            agent = r.get("agent", "unknown")
                            result_data = r.get("result", {})
                            print(f"  步骤{i}: Agent={agent}")
                            if isinstance(result_data, dict):
                                if "thought" in result_data:
                                    print(f"    Thought: {result_data['thought'][:100]}...")
                                if "action" in result_data:
                                    print(f"    Action: {result_data['action']}")
                                if "evaluation" in result_data:
                                    eval_data = result_data["evaluation"]
                                    print(f"    Evaluation: score={eval_data.get('quality_score', 0)}")
                    break
                
                step_count += 1
                current = status.get("current_agent", "unknown")
                if step_count % 5 == 0:
                    print(f"  ... 执行中，当前Agent: {current} ({step_count}s)")


async def demo_comparison():
    """
    对比演示：展示v6和v7的区别
    """
    print("\n" + "="*60)
    print("对比演示: v6 流水线 vs v7 自主决策")
    print("="*60)
    
    print("""
场景：用户要求"研发高电压电解液"

v6 (流水线架构):
┌─────────────────────────────────────────────────────────────┐
│  MasterAgent 硬编码状态机                                    │
│                                                             │
│  固定流程:                                                  │
│  需求分析 → 文献检索 → 知识挖掘 → 分子设计 → 配方生成 → ...   │
│       ↑________________________________________________|    │
│  (完全固定的执行顺序，无法跳过或调整)                          │
│                                                             │
│  问题：                                                     │
│  - 如果文献检索没有结果，仍然继续下一步                        │
│  - 无法根据具体情况选择最优路径                               │
│  - 没有自我评估和错误恢复                                     │
└─────────────────────────────────────────────────────────────┘

v7 (真正的多智能体):
┌─────────────────────────────────────────────────────────────┐
│  OrchestratorAgent 协调 + ReasoningAgent 自主决策             │
│                                                             │
│  动态流程:                                                  │
│  PlanningAgent: 根据目标生成动态计划                          │
│       ↓                                                     │
│  ReasoningAgent ReAct循环:                                  │
│    ┌─────────────────────────────────────────┐              │
│    │ Thought: 分析需求，决定第一步行动          │              │
│    │      ↓                                  │              │
│    │ Action: 选择最适合的工具                 │              │
│    │      ↓                                  │              │
│    │ Execute: 执行工具                        │              │
│    │      ↓                                  │              │
│    │ Evaluate: 评估结果质量                   │              │
│    │      ↓                                  │              │
│    │ 成功? → 继续下一步                        │              │
│    │ 失败? → 分析原因，选择替代方案             │              │
│    └─────────────────────────────────────────┘              │
│                                                             │
│  优势：                                                     │
│  - LLM动态规划，根据目标生成最优路径                          │
│  - 自主工具选择，根据上下文选择最适合的工具                    │
│  - 自我评估，每步执行后评估质量                               │
│  - 错误恢复，失败时分析原因并调整策略                         │
│  - 灵活性，可以跳过不必要的步骤                               │
└─────────────────────────────────────────────────────────────┘
""")


async def main():
    """运行所有测试"""
    print("True Multi-Agent System v7 测试")
    print("=" * 60)
    print("请先启动服务器: python agent_rag_v7_true_agent.py")
    print("确保服务在 http://localhost:8000 运行")
    print("=" * 60)
    
    # 等待用户确认
    input("\n按 Enter 开始测试...")
    
    try:
        # 基本检查
        await test_health_check()
        
        # 对话测试
        await test_chat_simple()
        await test_chat_stream()
        await test_multi_turn_dialog()
        
        # 研究测试
        await test_deep_research()
        
        # 工作流测试
        await test_task_workflow()
        await test_react_reasoning()
        
        # 对比演示
        await demo_comparison()
        
        print("\n" + "="*60)
        print("所有测试完成!")
        print("="*60)
        
    except Exception as e:
        print(f"\n测试出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
