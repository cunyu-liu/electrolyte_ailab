"""
================================================================================
ChemMind Multi-Agent System v8 - 测试脚本
================================================================================

测试模式:
1. 直接测试模式: 直接初始化Agent进行测试（推荐，无需启动服务器）
2. API测试模式: 通过HTTP调用已启动的服务器

使用方法:
    # 直接测试模式（默认）
    python test_agent_rag_v8.py
    
    # API测试模式（需先启动服务器）
    python test_agent_rag_v8.py --mode api
    
    # 指定查询内容
    python test_agent_rag_v8.py --query "锂离子电池电解液添加剂研究进展"

================================================================================
"""

import asyncio
import argparse
import json
import time
import sys
from typing import Optional, Dict, Any
from dataclasses import asdict

# 导入agent_rag_v8中的核心类
# 注意：确保agent_rag_v8.py在同一目录下
sys.path.insert(0, '/Users/liucunyu/Documents/all_code/thu_2025/eletrolyte_lab/tempcode/electrolyte_lab/agent')

# 尝试导入，如果失败则使用模拟
from agent_rag_v8 import (
    MessageBus, SharedMemory, LLMService, RAGService, SafetyGuard,
    CentralOrchestratorAgent, LiteratureResearchAgent, MolecularPropertyAgent,
    ExperimentDesignAgent, QualityControlAgent, GeneralKnowledgeAgent, ToolExecutorAgent,
    AgentMessage, MessageType, TaskType, TaskComplexity
)


# ==============================================================================
# 1. 直接测试模式 - 直接初始化Agent
# ==============================================================================

class DirectAgentTester:
    """
    直接测试Agent，无需启动FastAPI服务器
    """
    
    def __init__(self):
        self.message_bus: Optional[MessageBus] = None
        self.shared_memory: Optional[SharedMemory] = None
        self.llm_service: Optional[LLMService] = None
        self.rag_service: Optional[RAGService] = None
        self.safety_guard: Optional[SafetyGuard] = None
        self.agents: Dict[str, Any] = {}
        self.orchestrator: Optional[CentralOrchestratorAgent] = None
        self._initialized = False
        
    async def initialize(self):
        """初始化所有组件"""
        if self._initialized:
            return
            
        print("=" * 70)
        print("正在初始化 ChemMind Multi-Agent System v8 (测试模式)...")
        print("=" * 70)
        
        # 初始化基础设施
        self.message_bus = MessageBus()
        self.shared_memory = SharedMemory()
        
        # 初始化LLM服务
        print("\n[1/6] 正在加载LLM模型...")
        try:
            self.llm_service = LLMService(
                "/Users/liucunyu/.cache/modelscope/hub/models/Qwen/Qwen3-0.6B"
            )
            print("✓ LLM模型加载完成")
        except Exception as e:
            print(f"✗ LLM模型加载失败: {e}")
            raise
        
        # 初始化RAG服务
        print("\n[2/6] 正在初始化RAG服务...")
        try:
            self.rag_service = RAGService(self.llm_service)
            rag_status = "就绪" if self.rag_service.milvus_collection else "Milvus未连接(使用LLM模式)"
            print(f"✓ RAG服务初始化完成 ({rag_status})")
        except Exception as e:
            print(f"⚠ RAG服务初始化部分失败: {e}")
            self.rag_service = None
        
        # 初始化安全过滤器
        print("\n[3/6] 正在初始化安全过滤器...")
        self.safety_guard = SafetyGuard(self.llm_service)
        print("✓ 安全过滤器初始化完成")
        
        # 初始化Orchestrator
        print("\n[4/6] 正在启动Agent1: CentralOrchestrator...")
        self.orchestrator = CentralOrchestratorAgent(
            message_bus=self.message_bus,
            shared_memory=self.shared_memory,
            llm_service=self.llm_service,
            rag_service=self.rag_service
        )
        await self.orchestrator.start()
        print("✓ Orchestrator启动完成")
        
        # 初始化专业Agent
        print("\n[5/6] 正在启动专业Agent...")
        
        # Agent2: 文献调研Agent
        agent2 = LiteratureResearchAgent(
            message_bus=self.message_bus,
            shared_memory=self.shared_memory,
            llm_service=self.llm_service,
            rag_service=self.rag_service
        )
        await agent2.start()
        self.agents["agent2_literature"] = agent2
        print("  ✓ Agent2 (LiteratureResearch) 启动完成")
        
        # Agent3: 分子性质预测Agent
        agent3 = MolecularPropertyAgent(
            message_bus=self.message_bus,
            shared_memory=self.shared_memory,
            llm_service=self.llm_service,
            rag_service=self.rag_service
        )
        await agent3.start()
        self.agents["agent3_property"] = agent3
        print("  ✓ Agent3 (MolecularProperty) 启动完成")
        
        # Agent4: 实验方案设计Agent
        agent4 = ExperimentDesignAgent(
            message_bus=self.message_bus,
            shared_memory=self.shared_memory,
            llm_service=self.llm_service,
            rag_service=self.rag_service
        )
        await agent4.start()
        self.agents["agent4_design"] = agent4
        print("  ✓ Agent4 (ExperimentDesign) 启动完成")
        
        # Agent5: 质量控制Agent
        agent5 = QualityControlAgent(
            message_bus=self.message_bus,
            shared_memory=self.shared_memory,
            llm_service=self.llm_service,
            rag_service=self.rag_service
        )
        await agent5.start()
        self.agents["agent5_qc"] = agent5
        print("  ✓ Agent5 (QualityControl) 启动完成")
        
        # Agent6: 常识问答Agent
        agent6 = GeneralKnowledgeAgent(
            message_bus=self.message_bus,
            shared_memory=self.shared_memory,
            llm_service=self.llm_service,
            rag_service=self.rag_service
        )
        await agent6.start()
        self.agents["agent6_general"] = agent6
        print("  ✓ Agent6 (GeneralKnowledge) 启动完成")
        
        # 工具执行器
        tool_executor = ToolExecutorAgent(
            message_bus=self.message_bus,
            shared_memory=self.shared_memory,
            llm_service=self.llm_service,
            rag_service=self.rag_service
        )
        await tool_executor.start()
        self.agents["tool_executor"] = tool_executor
        print("  ✓ ToolExecutor 启动完成")
        
        print("\n" + "=" * 70)
        print("✓ 所有组件初始化完成！")
        print("=" * 70)
        print("\n可用Agent:")
        for agent_id in self.agents.keys():
            print(f"  - {agent_id}")
        
        self._initialized = True
        
    async def query(self, user_query: str, depth: int = 2) -> Dict[str, Any]:
        """
        处理用户查询
        
        Args:
            user_query: 用户输入的自然语言查询
            depth: 研究深度 (1-4)
            
        Returns:
            包含回答和元数据的字典
        """
        if not self._initialized:
            await self.initialize()
        
        print(f"\n{'='*70}")
        print(f"用户查询: {user_query}")
        print(f"{'='*70}\n")
        
        start_time = time.time()
        workflow_id = f"test_{int(time.time())}"
        
        # 创建future等待结果
        future = asyncio.Future()
        
        # 设置结果回调
        async def result_callback(message: AgentMessage):
            if message.correlation_id == workflow_id:
                if not future.done():
                    future.set_result(message.payload)
        
        self.message_bus.subscribe(MessageType.TASK_RESULT.value, result_callback)
        
        # 发送任务给Orchestrator
        print("[流程] 发送任务给Orchestrator...")
        await self.message_bus.send(AgentMessage(
            sender="test_client",
            receiver="agent1_orchestrator",
            message_type=MessageType.TASK_ASSIGN,
            payload={
                "query": user_query,
                "require_citations": True,
                "depth": depth
            },
            correlation_id=workflow_id
        ))
        
        # 等待结果（带超时）
        print("[流程] 等待Agent处理结果...\n")
        try:
            result = await asyncio.wait_for(future, timeout=180)
            processing_time = time.time() - start_time
            
            # 处理结果
            result_inner = result.get("result", {})
            
            return {
                "success": True,
                "workflow_id": workflow_id,
                "status": result.get("status", "unknown"),
                "agent_used": result.get("agent_id", "unknown"),
                "answer": result_inner.get("answer", ""),
                "citations": result_inner.get("citations", []),
                "qc_report": result_inner.get("qc_report"),
                "processing_time": processing_time
            }
            
        except asyncio.TimeoutError:
            processing_time = time.time() - start_time
            return {
                "success": False,
                "workflow_id": workflow_id,
                "status": "timeout",
                "error": "处理超时（180秒），请稍后重试或简化查询",
                "processing_time": processing_time
            }
    
    async def close(self):
        """关闭所有Agent"""
        print("\n正在关闭系统...")
        for agent in self.agents.values():
            await agent.stop()
        if self.orchestrator:
            await self.orchestrator.stop()
        print("✓ 系统已关闭")


# ==============================================================================
# 2. API测试模式 - 通过HTTP调用
# ==============================================================================

class APIAgentTester:
    """
    通过HTTP API测试（需要服务器已启动）
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        
    async def query(self, user_query: str, depth: int = 2) -> Dict[str, Any]:
        """通过API发送查询"""
        import aiohttp
        
        print(f"\n{'='*70}")
        print(f"用户查询: {user_query}")
        print(f"API地址: {self.base_url}/query")
        print(f"{'='*70}\n")
        
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/query",
                json={
                    "query": user_query,
                    "depth": depth,
                    "require_citations": True
                }
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    result["processing_time"] = time.time() - start_time
                    return result
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "status": f"error_{response.status}",
                        "error": error_text,
                        "processing_time": time.time() - start_time
                    }
    
    async def health_check(self) -> bool:
        """检查服务器健康状态"""
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"服务器状态: {data.get('status', 'unknown')}")
                        print(f"可用Agent: {', '.join(data.get('agents', []))}")
                        print(f"LLM加载: {'✓' if data.get('llm_loaded') else '✗'}")
                        print(f"RAG就绪: {'✓' if data.get('rag_ready') else '✗'}")
                        return True
                    return False
        except Exception as e:
            print(f"无法连接到服务器: {e}")
            return False


# ==============================================================================
# 3. 测试结果展示
# ==============================================================================

def print_result(result: Dict[str, Any]):
    """美化打印结果"""
    print("\n" + "=" * 70)
    print("处理结果")
    print("=" * 70)
    
    if not result.get("success", True):
        print(f"\n❌ 处理失败")
        print(f"状态: {result.get('status', 'unknown')}")
        print(f"错误: {result.get('error', '未知错误')}")
        print(f"\n处理时间: {result.get('processing_time', 0):.2f}秒")
        return
    
    print(f"\n✅ 处理成功")
    print(f"\n📋 元数据:")
    print(f"  - Workflow ID: {result.get('workflow_id', 'N/A')}")
    print(f"  - 使用Agent: {result.get('agent_used', 'unknown')}")
    print(f"  - 处理时间: {result.get('processing_time', 0):.2f}秒")
    
    print(f"\n💬 回答内容:")
    print("-" * 70)
    answer = result.get('answer', '无回答')
    print(answer)
    print("-" * 70)
    
    citations = result.get('citations', [])
    if citations:
        print(f"\n📚 引用文献 ({len(citations)}篇):")
        for i, citation in enumerate(citations[:5], 1):  # 最多显示5篇
            title = citation.get('doc_title', 'Unknown')
            year = citation.get('year', 'n.d.')
            print(f"  {i}. {title} ({year})")
        if len(citations) > 5:
            print(f"  ... 还有 {len(citations) - 5} 篇引用")
    
    qc_report = result.get('qc_report')
    if qc_report:
        print(f"\n✅ 质量控制报告:")
        print(f"  - 总体评分: {qc_report.get('overall_score', 'N/A')}")
        print(f"  - 审核状态: {'通过' if qc_report.get('approved') else '需改进'}")


def print_welcome():
    """打印欢迎信息"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║           ChemMind Multi-Agent System v8 - 测试脚本                  ║
║                                                                      ║
║  院士级化学研究智能体系统                                            ║
║                                                                      ║
║  功能:                                                               ║
║    • 文献调研 (Agent2) - 深度文献检索与综合                          ║
║    • 性质预测 (Agent3) - 分子电化学性质预测                          ║
║    • 实验设计 (Agent4) - 电池电解液实验方案设计                      ║
║    • 质量控制 (Agent5) - 事实核查与审核                              ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")


# ==============================================================================
# 4. 主程序
# ==============================================================================

async def interactive_mode(tester):
    """交互式测试模式"""
    print("\n进入交互式测试模式，输入查询内容（输入 'quit' 退出）：\n")
    
    while True:
        try:
            query = input("> ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("退出测试...")
                break
            
            if not query:
                continue
            
            result = await tester.query(query)
            print_result(result)
            
        except KeyboardInterrupt:
            print("\n\n退出测试...")
            break
        except Exception as e:
            print(f"\n错误: {e}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="ChemMind Multi-Agent System v8 测试脚本"
    )
    parser.add_argument(
        '--mode', 
        choices=['direct', 'api'], 
        default='direct',
        help='测试模式: direct(直接测试) 或 api(HTTP调用), 默认: direct'
    )
    parser.add_argument(
        '--query', 
        type=str,
        default=None,
        help='查询内容（如果不指定则进入交互模式）'
    )
    parser.add_argument(
        '--url',
        type=str,
        default='http://localhost:8000',
        help='API服务器地址 (仅api模式), 默认: http://localhost:8000'
    )
    parser.add_argument(
        '--depth',
        type=int,
        default=2,
        help='研究深度 (1-4), 默认: 2'
    )
    
    args = parser.parse_args()
    
    print_welcome()
    
    tester = None
    
    try:
        if args.mode == 'direct':
            # 直接测试模式
            tester = DirectAgentTester()
            await tester.initialize()
        else:
            # API测试模式
            tester = APIAgentTester(args.url)
            print("\n检查服务器状态...")
            if not await tester.health_check():
                print("\n❌ 无法连接到服务器，请确保服务器已启动:")
                print("   python agent/agent_rag_v8.py")
                return
        
        if args.query:
            # 单次查询模式
            result = await tester.query(args.query, depth=args.depth)
            print_result(result)
        else:
            # 交互模式
            await interactive_mode(tester)
            
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if isinstance(tester, DirectAgentTester):
            await tester.close()


# 预定义的测试查询示例
TEST_QUERIES = {
    "literature": [
        "锂离子电池高电压电解液添加剂研究进展",
        "固态电解质界面(SEI)膜的形成机理",
        "锂金属负极的保护策略有哪些？",
        "醚类电解液和酯类电解液的区别是什么？"
    ],
    "property": [
        "预测碳酸乙烯酯(EC)的离子电导率和氧化电位",
        "比较DEC和DMC溶剂的性质差异",
        "氟代碳酸乙烯酯(FEC)的闪点是多少？"
    ],
    "design": [
        "设计一个4.5V高电压锂离子电池电解液配方",
        "设计一个适用于低温环境的电解液实验方案",
        "如何优化电解液以提高电池的循环寿命？"
    ]
}


if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())
