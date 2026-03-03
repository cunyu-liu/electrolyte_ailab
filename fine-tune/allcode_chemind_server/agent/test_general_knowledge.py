"""
================================================================================
ChemMind Multi-Agent System v8 - Agent6: GeneralKnowledge 测试脚本
================================================================================

这个脚本专门测试新的常识问答 Agent (Agent6)

Agent6 适合处理的问题类型：
- 基础概念解释（如：什么是SEI膜？）
- 术语定义（如：CEI是什么？）
- 简单对比（如：EC和DEC的区别？）
- 基础理论知识（如：锂离子电池的充放电原理）

使用方法:
    python test_general_knowledge.py

================================================================================
"""

import asyncio
import sys
sys.path.insert(0, '/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent')

from agent_rag_v8 import (
    MessageBus, SharedMemory, LLMService, RAGService,
    CentralOrchestratorAgent, LiteratureResearchAgent, 
    MolecularPropertyAgent, ExperimentDesignAgent,
    QualityControlAgent, GeneralKnowledgeAgent, ToolExecutorAgent,
    AgentMessage, MessageType
)


class GeneralKnowledgeTester:
    """常识问答Agent测试器"""
    
    def __init__(self):
        self.message_bus = None
        self.shared_memory = None
        self.llm_service = None
        self.rag_service = None
        self.orchestrator = None
        self.agents = {}
        self._ready = False
        
    async def initialize(self):
        """初始化所有组件"""
        print("🔧 正在初始化ChemMind系统...")
        
        # 初始化基础设施
        self.message_bus = MessageBus()
        self.shared_memory = SharedMemory()
        
        # 加载LLM模型
        print("  📦 加载语言模型...")
        self.llm_service = LLMService(
            "/Users/liucunyu/.cache/modelscope/hub/models/Qwen/Qwen3-0.6B"
        )
        
        # 初始化RAG服务（Agent6实际上不需要RAG，但保持兼容性）
        print("  📚 初始化RAG服务...")
        self.rag_service = RAGService(self.llm_service)
        
        # 启动中央调度Agent
        print("  🤖 启动中央调度Agent...")
        self.orchestrator = CentralOrchestratorAgent(
            message_bus=self.message_bus,
            shared_memory=self.shared_memory,
            llm_service=self.llm_service,
            rag_service=self.rag_service
        )
        await self.orchestrator.start()
        
        # 启动专业Agent
        print("  🤖 启动专业Agent...")
        
        # Agent2: 文献调研
        agent2 = LiteratureResearchAgent(
            message_bus=self.message_bus,
            shared_memory=self.shared_memory,
            llm_service=self.llm_service,
            rag_service=self.rag_service
        )
        await agent2.start()
        self.agents["agent2_literature"] = agent2
        
        # Agent3: 性质预测
        agent3 = MolecularPropertyAgent(
            message_bus=self.message_bus,
            shared_memory=self.shared_memory,
            llm_service=self.llm_service,
            rag_service=self.rag_service
        )
        await agent3.start()
        self.agents["agent3_property"] = agent3
        
        # Agent4: 实验设计
        agent4 = ExperimentDesignAgent(
            message_bus=self.message_bus,
            shared_memory=self.shared_memory,
            llm_service=self.llm_service,
            rag_service=self.rag_service
        )
        await agent4.start()
        self.agents["agent4_design"] = agent4
        
        # Agent5: 质量控制
        agent5 = QualityControlAgent(
            message_bus=self.message_bus,
            shared_memory=self.shared_memory,
            llm_service=self.llm_service,
            rag_service=self.rag_service
        )
        await agent5.start()
        self.agents["agent5_qc"] = agent5
        
        # Agent6: 常识问答（重点测试对象）
        print("  🤖 启动Agent6: GeneralKnowledge...")
        agent6 = GeneralKnowledgeAgent(
            message_bus=self.message_bus,
            shared_memory=self.shared_memory,
            llm_service=self.llm_service,
            rag_service=self.rag_service
        )
        await agent6.start()
        self.agents["agent6_general"] = agent6
        
        # 工具执行器
        tool_executor = ToolExecutorAgent(
            message_bus=self.message_bus,
            shared_memory=self.shared_memory,
            llm_service=self.llm_service,
            rag_service=self.rag_service
        )
        await tool_executor.start()
        self.agents["tool_executor"] = tool_executor
        
        self._ready = True
        print("✅ 系统初始化完成！\n")
        
    async def ask(self, query: str, timeout: int = 60) -> dict:
        """发送查询并获取回答"""
        if not self._ready:
            raise RuntimeError("系统未初始化，请先调用initialize()")
        
        import time
        start_time = time.time()
        workflow_id = f"wf_{int(time.time())}"
        
        # 创建future等待结果
        future = asyncio.Future()
        
        async def result_callback(message: AgentMessage):
            if message.correlation_id == workflow_id and not future.done():
                future.set_result(message.payload)
        
        self.message_bus.subscribe(MessageType.TASK_RESULT.value, result_callback)
        
        # 发送任务
        await self.message_bus.send(AgentMessage(
            sender="client",
            receiver="agent1_orchestrator",
            message_type=MessageType.TASK_ASSIGN,
            payload={
                "query": query,
                "require_citations": False,  # 常识问答不需要引用
                "depth": 1
            },
            correlation_id=workflow_id
        ))
        
        # 等待结果
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            processing_time = time.time() - start_time
            
            result_inner = result.get("result", {})
            
            return {
                "success": True,
                "answer": result_inner.get("answer", ""),
                "agent_used": result.get("agent_id", "unknown"),
                "status": result.get("status", "success"),
                "processing_time": processing_time
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "answer": "",
                "error": f"处理超时（{timeout}秒）",
                "processing_time": time.time() - start_time
            }
    
    async def close(self):
        """关闭系统"""
        print("\n🔧 正在关闭系统...")
        for agent in self.agents.values():
            await agent.stop()
        if self.orchestrator:
            await self.orchestrator.stop()
        self._ready = False
        print("✅ 系统已关闭")


# ==============================================================================
# 测试用例
# ==============================================================================

TEST_CASES = {
    "概念解释": [
        "什么是SEI膜？",
        "什么是CEI？",
        "请解释离子电导率的概念",
        "什么是氧化电位？",
    ],
    "对比分析": [
        "EC和DEC溶剂有什么区别？",
        "LiPF6和LiFSI哪个更好？",
        "锂离子电池和钠离子电池有什么区别？",
    ],
    "基础知识": [
        "锂离子电池的工作原理是什么？",
        "电解液的主要组成成分有哪些？",
        "什么是快充技术？",
    ],
    "术语定义": [
        "什么是首次库仑效率？",
        "什么是N/P比？",
        "请解释电压平台的概念",
    ]
}


async def run_test_cases():
    """运行所有测试用例"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║        Agent6: GeneralKnowledge - 常识问答Agent测试                  ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    tester = GeneralKnowledgeTester()
    await tester.initialize()
    
    try:
        for category, questions in TEST_CASES.items():
            print(f"\n{'='*70}")
            print(f"📂 测试类别: {category}")
            print(f"{'='*70}")
            
            for i, question in enumerate(questions, 1):
                print(f"\n❓ 问题 {i}: {question}")
                print("-" * 70)
                
                result = await tester.ask(question, timeout=60)
                
                if result["success"]:
                    print(f"✅ 回答 (由 {result['agent_used']} 生成):")
                    print(f"{'-'*70}")
                    # 只显示前500字符
                    answer = result["answer"]
                    if len(answer) > 500:
                        print(answer[:500] + "...")
                    else:
                        print(answer)
                    print(f"{'-'*70}")
                    print(f"⏱️  处理时间: {result['processing_time']:.2f}秒\n")
                else:
                    print(f"❌ 失败: {result.get('error', '未知错误')}\n")
                
                # 每个问题之间暂停一下
                await asyncio.sleep(1)
                
    finally:
        await tester.close()


async def interactive_mode():
    """交互式测试模式"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║        Agent6: GeneralKnowledge - 交互式测试模式                     ║
║                                                                      ║
║  提示: 输入自然语言查询，输入 'quit' 退出                            ║
║        输入 'examples' 查看示例问题                                  ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    tester = GeneralKnowledgeTester()
    await tester.initialize()
    
    try:
        while True:
            query = input("\n> ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                break
            
            if query.lower() == 'examples':
                print("\n📋 示例问题:")
                for category, questions in TEST_CASES.items():
                    print(f"\n【{category}】")
                    for q in questions:
                        print(f"  • {q}")
                continue
            
            if not query:
                continue
            
            print("\n🤔 正在处理...")
            result = await tester.ask(query)
            
            if result["success"]:
                print(f"\n💬 回答 (由 {result['agent_used']} 生成):")
                print(f"{'='*70}")
                print(result["answer"])
                print(f"{'='*70}")
                print(f"⏱️  处理时间: {result['processing_time']:.2f}秒\n")
            else:
                print(f"\n❌ 错误: {result.get('error', '未知错误')}\n")
                
    except KeyboardInterrupt:
        print("\n\n退出...")
    finally:
        await tester.close()


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent6: GeneralKnowledge 测试")
    parser.add_argument(
        '--mode', 
        choices=['auto', 'interactive'], 
        default='interactive',
        help='测试模式: auto(自动运行测试用例) 或 interactive(交互模式), 默认: interactive'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'auto':
        await run_test_cases()
    else:
        await interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())
