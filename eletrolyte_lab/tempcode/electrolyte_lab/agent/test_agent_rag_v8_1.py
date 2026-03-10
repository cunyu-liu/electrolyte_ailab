"""
================================================================================
ChemMind Multi-Agent System v8.1 - 测试脚本
================================================================================

测试模式:
1. 直接测试模式: 直接初始化Agent进行测试（推荐，无需启动服务器）
2. API测试模式: 通过HTTP调用已启动的服务器

v8.1 新增测试功能:
- 测试智能路由和WFQ调度
- 测试分层任务分类器
- 测试语义缓存命中率
- 测试Agent能力画像

使用方法:
    # 直接测试模式（默认）
    python test_agent_rag_v8_1.py
    
    # API测试模式（需先启动服务器）
    python test_agent_rag_v8_1.py --mode api
    
    # 指定查询内容
    python test_agent_rag_v8_1.py --query "锂离子电池电解液添加剂研究进展"
    
    # 测试 v8.1 新特性
    python test_agent_rag_v8_1.py --test-features

================================================================================
"""

import asyncio
import argparse
import json
import time
import sys
import os
from typing import Optional, Dict, Any
from dataclasses import asdict

# 导入agent_rag_v8_1中的核心类
# 注意：确保agent_rag_v8_1.py在同一目录下
sys.path.insert(0, '/Users/liucunyu/Documents/all_code/thu_2025/eletrolyte_lab/tempcode/electrolyte_lab/agent')

# 尝试导入，如果失败则使用模拟
try:
    from agent_rag_v8_1 import (
        MessageBus, SharedMemory, LLMService, RAGService, SafetyGuard,
        CentralOrchestratorAgent, LiteratureResearchAgent, MolecularPropertyAgent,
        ExperimentDesignAgent, QualityControlAgent, GeneralKnowledgeAgent, ToolExecutorAgent,
        AgentMessage, MessageType, TaskType, TaskComplexity,
        # v8.1 新增导入
        CapabilityVector, Tracer, get_tracer
    )
    V81_AVAILABLE = True
except ImportError as e:
    print(f"⚠ 无法导入v8.1模块: {e}")
    print("  尝试使用v8.0兼容模式...")
    from agent_rag_v8 import (
        MessageBus, SharedMemory, LLMService, RAGService, SafetyGuard,
        CentralOrchestratorAgent, LiteratureResearchAgent, MolecularPropertyAgent,
        ExperimentDesignAgent, QualityControlAgent, GeneralKnowledgeAgent, ToolExecutorAgent,
        AgentMessage, MessageType, TaskType, TaskComplexity
    )
    V81_AVAILABLE = False


# ==============================================================================
# 0. 测试日志记录器 - v8.1 新增
# ==============================================================================

class TestLogger:
    """
    测试会话日志记录器
    
    自动记录所有测试输入/输出到 timestamped 文件夹
    文件结构:
        test_logs/
            YYYYMMDD_HHMMSS/
                session.json     - 会话元数据
                inputs.txt       - 所有查询输入
                outputs.txt      - 所有回答输出
                conversations/   - 完整对话记录
    """
    
    def __init__(self, session_name: str = None):
        from datetime import datetime
        
        # 创建日志目录
        self.base_dir = os.path.join(os.path.dirname(__file__), "test_logs")
        os.makedirs(self.base_dir, exist_ok=True)
        
        # 创建会话目录 (timestamped)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_name = session_name or f"session_{timestamp}"
        self.session_dir = os.path.join(self.base_dir, session_name)
        os.makedirs(self.session_dir, exist_ok=True)
        
        # 创建子目录
        self.conv_dir = os.path.join(self.session_dir, "conversations")
        os.makedirs(self.conv_dir, exist_ok=True)
        
        # 文件路径
        self.session_file = os.path.join(self.session_dir, "session.json")
        self.inputs_file = os.path.join(self.session_dir, "inputs.txt")
        self.outputs_file = os.path.join(self.session_dir, "outputs.txt")
        
        # 会话元数据
        self.session_data = {
            "session_name": session_name,
            "start_time": datetime.now().isoformat(),
            "queries": [],
            "query_count": 0
        }
        
        # 初始化文件
        self._init_files()
        
        print(f"📁 测试日志目录: {self.session_dir}")
    
    def _init_files(self):
        """初始化日志文件"""
        # 会话元数据
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(self.session_data, f, ensure_ascii=False, indent=2)
        
        # 输入日志头部
        with open(self.inputs_file, 'w', encoding='utf-8') as f:
            f.write(f"{'='*70}\n")
            f.write(f"测试输入记录 - 会话: {self.session_data['session_name']}\n")
            f.write(f"开始时间: {self.session_data['start_time']}\n")
            f.write(f"{'='*70}\n\n")
        
        # 输出日志头部
        with open(self.outputs_file, 'w', encoding='utf-8') as f:
            f.write(f"{'='*70}\n")
            f.write(f"测试输出记录 - 会话: {self.session_data['session_name']}\n")
            f.write(f"开始时间: {self.session_data['start_time']}\n")
            f.write(f"{'='*70}\n\n")
    
    def log_query(self, query: str, query_type: str = "user") -> int:
        """
        记录用户查询
        
        Returns:
            query_id: 查询ID
        """
        from datetime import datetime
        
        self.session_data["query_count"] += 1
        query_id = self.session_data["query_count"]
        
        query_entry = {
            "id": query_id,
            "timestamp": datetime.now().isoformat(),
            "type": query_type,
            "query": query
        }
        self.session_data["queries"].append(query_entry)
        
        # 写入 inputs.txt
        with open(self.inputs_file, 'a', encoding='utf-8') as f:
            f.write(f"\n[{query_id}] {query_entry['timestamp']}\n")
            f.write(f"类型: {query_type}\n")
            f.write(f"内容: {query}\n")
            f.write("-" * 70 + "\n")
        
        # 更新 session.json
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(self.session_data, f, ensure_ascii=False, indent=2)
        
        return query_id
    
    def log_response(self, query_id: int, result: Dict[str, Any], response_text: str = None):
        """
        记录系统响应
        
        Args:
            query_id: 对应的查询ID
            result: 完整的返回结果字典
            response_text: 可选的预格式化响应文本
        """
        from datetime import datetime
        
        timestamp = datetime.now().isoformat()
        
        # 提取关键信息
        agent_used = result.get("agent_used", "unknown")
        status = result.get("status", "unknown")
        processing_time = result.get("processing_time", 0)
        success = result.get("success", False)
        
        # 构建输出内容
        output_content = response_text or result.get("answer", "")
        
        # 写入 outputs.txt
        with open(self.outputs_file, 'a', encoding='utf-8') as f:
            f.write(f"\n[响应 #{query_id}] {timestamp}\n")
            f.write(f"Agent: {agent_used} | 状态: {status} | 耗时: {processing_time:.2f}s\n")
            f.write(f"成功: {success}\n")
            f.write("-" * 70 + "\n")
            f.write(output_content)
            f.write("\n" + "=" * 70 + "\n")
        
        # 保存完整对话记录 (JSON格式)
        conv_file = os.path.join(self.conv_dir, f"query_{query_id:04d}.json")
        conversation = {
            "query_id": query_id,
            "timestamp": timestamp,
            "query": self.session_data["queries"][query_id - 1]["query"] if query_id <= len(self.session_data["queries"]) else "",
            "result": result,
            "formatted_response": output_content
        }
        with open(conv_file, 'w', encoding='utf-8') as f:
            json.dump(conversation, f, ensure_ascii=False, indent=2)
        
        # 更新查询条目
        for q in self.session_data["queries"]:
            if q["id"] == query_id:
                q["response_timestamp"] = timestamp
                q["agent_used"] = agent_used
                q["status"] = status
                q["processing_time"] = processing_time
                q["success"] = success
                break
        
        # 更新 session.json
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(self.session_data, f, ensure_ascii=False, indent=2)
    
    def get_session_summary(self) -> Dict[str, Any]:
        """获取会话摘要"""
        from datetime import datetime
        
        duration = 0
        if self.session_data["queries"]:
            start = datetime.fromisoformat(self.session_data["start_time"])
            now = datetime.now()
            duration = (now - start).total_seconds()
        
        successful = sum(1 for q in self.session_data["queries"] if q.get("success", False))
        failed = self.session_data["query_count"] - successful
        
        return {
            "session_name": self.session_data["session_name"],
            "total_queries": self.session_data["query_count"],
            "successful": successful,
            "failed": failed,
            "duration_seconds": duration,
            "log_directory": self.session_dir
        }
    
    def print_summary(self):
        """打印会话摘要"""
        summary = self.get_session_summary()
        print(f"\n{'='*70}")
        print("📊 测试会话摘要")
        print(f"{'='*70}")
        print(f"会话名称: {summary['session_name']}")
        print(f"总查询数: {summary['total_queries']}")
        print(f"成功: {summary['successful']} | 失败: {summary['failed']}")
        print(f"总耗时: {summary['duration_seconds']:.2f}s")
        print(f"日志目录: {summary['log_directory']}")
        print(f"{'='*70}\n")


# ==============================================================================
# 1. 直接测试模式 - 直接初始化Agent
# ==============================================================================

class DirectAgentTester:
    """
    直接测试Agent，无需启动FastAPI服务器 (v8.1)
    """
    
    def __init__(self, enable_logging: bool = True, session_name: str = None):
        self.message_bus: Optional[MessageBus] = None
        self.shared_memory: Optional[SharedMemory] = None
        self.llm_service: Optional[LLMService] = None
        self.rag_service: Optional[RAGService] = None
        self.safety_guard: Optional[SafetyGuard] = None
        self.agents: Dict[str, Any] = {}
        self.orchestrator: Optional[CentralOrchestratorAgent] = None
        self._initialized = False
        
        # v8.1: 性能统计
        self._performance_stats = {
            "queries": 0,
            "total_time": 0,
            "cache_hits": 0
        }
        
        # v8.1: 测试日志记录器
        self.logger: Optional[TestLogger] = None
        if enable_logging:
            self.logger = TestLogger(session_name=session_name)
        
    async def initialize(self):
        """初始化所有组件"""
        if self._initialized:
            return
            
        print("=" * 70)
        print("正在初始化 ChemMind Multi-Agent System v8.1 (测试模式)...")
        if V81_AVAILABLE:
            print("✓ v8.1 算法升级已启用")
            print("  - 智能路由 + WFQ调度")
            print("  - 语义缓存 + 自适应批处理")
            print("  - 分层分类 + 并行子任务")
        else:
            print("⚠ 使用v8.0兼容模式")
        print("=" * 70)
        
        # 初始化基础设施
        self.message_bus = MessageBus()
        self.shared_memory = SharedMemory()
        
        # 初始化LLM服务
        print("\n[1/6] 正在加载LLM服务...")
        try:
            # v8.1: DeepSeek API模式
            self.llm_service = LLMService()
            print("✓ LLM服务初始化完成 (DeepSeek API)")
        except Exception as e:
            print(f"✗ LLM服务初始化失败: {e}")
            raise
        
        # 初始化RAG服务
        print("\n[2/6] 正在初始化RAG服务...")
        try:
            self.rag_service = RAGService(self.llm_service)
            rag_status = "就绪" if self.rag_service.milvus_collection else "Milvus未连接(使用LLM模式)"
            print(f"✓ RAG服务初始化完成 ({rag_status})")
            if V81_AVAILABLE:
                print("  - 自适应混合检索权重")
                print("  - 级联重排序 + MMR多样性")
        except Exception as e:
            print(f"⚠ RAG服务初始化部分失败: {e}")
            self.rag_service = None
        
        # 初始化安全过滤器
        print("\n[3/6] 正在初始化安全过滤器...")
        self.safety_guard = SafetyGuard(self.llm_service)
        print("✓ 安全过滤器初始化完成")
        if V81_AVAILABLE:
            print("  - 上下文感知安全检查")
            print("  - 对抗样本检测")
        
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
        if V81_AVAILABLE:
            print("  - 分层任务分类器")
            print("  - Agent能力画像路由")
        
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
        
    async def query(self, user_query: str, depth: int = 2, query_type: str = "user") -> Dict[str, Any]:
        """
        处理用户查询 (v8.1)
        
        Args:
            user_query: 用户输入的自然语言查询
            depth: 研究深度 (1-4)
            query_type: 查询类型 (用于日志记录)
            
        Returns:
            包含回答和元数据的字典
        """
        if not self._initialized:
            await self.initialize()
        
        # v8.1: 记录输入
        query_id = None
        if self.logger:
            query_id = self.logger.log_query(user_query, query_type)
        
        print(f"\n{'='*70}")
        print(f"用户查询: {user_query}")
        print(f"{'='*70}\n")
        
        start_time = time.time()
        workflow_id = f"test_{int(time.time())}"
        
        # v8.1: 启动追踪
        if V81_AVAILABLE:
            tracer = get_tracer()
            trace_id = tracer.start_trace(f"query_{workflow_id}")
        
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
        if V81_AVAILABLE:
            print("  - 智能路由到对应分区")
            print("  - 分层任务分类")
        
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
            
            # 更新统计
            self._performance_stats["queries"] += 1
            self._performance_stats["total_time"] += processing_time
            
            # 处理结果
            result_inner = result.get("result", {})
            
            # v8.1: 提取分类信息
            classification = result_inner.get("classification", {})
            
            response = {
                "success": True,
                "workflow_id": workflow_id,
                "status": result.get("status", "unknown"),
                "agent_used": result.get("agent_id", "unknown"),
                "answer": result_inner.get("answer", ""),
                "citations": result_inner.get("citations", []),
                "qc_report": result_inner.get("qc_report"),
                "processing_time": processing_time,
                # v8.1 新增
                "classification": classification,
                "domain": classification.get("domain", ""),
                "complexity_score": classification.get("complexity_score", 0)
            }
            
            # v8.1: 记录输出
            if self.logger and query_id:
                self.logger.log_response(query_id, response)
            
            return response
            
        except asyncio.TimeoutError:
            processing_time = time.time() - start_time
            error_response = {
                "success": False,
                "workflow_id": workflow_id,
                "status": "timeout",
                "error": "处理超时（180秒），请稍后重试或简化查询",
                "processing_time": processing_time
            }
            
            # v8.1: 记录错误
            if self.logger and query_id:
                self.logger.log_response(query_id, error_response)
            
            return error_response
    
    async def test_v81_features(self):
        """测试 v8.1 新特性"""
        if not V81_AVAILABLE:
            print("⚠ v8.1 模块不可用，无法测试新特性")
            return
        
        print("\n" + "=" * 70)
        print("测试 v8.1 新特性")
        print("=" * 70)
        
        # 1. 测试MessageBus分区统计
        print("\n[1/4] MessageBus 分区统计")
        partition_stats = self.message_bus.get_partition_stats()
        print(f"  分区状态: {partition_stats}")
        
        # 2. 测试Agent能力画像
        print("\n[2/4] Agent 能力画像")
        for agent_id, agent in self.agents.items():
            if hasattr(agent, 'capability_vector'):
                cv = agent.capability_vector
                print(f"  {agent_id}:")
                print(f"    - 负载: {cv.load:.2f}")
                print(f"    - 成功率: {cv.success_rate:.2f}")
                print(f"    - 平均延迟: {cv.avg_latency:.3f}s")
                print(f"    - 综合评分: {cv.compute_score():.3f}")
        
        # 3. 测试安全对抗检测
        print("\n[3/4] SafetyGuard 对抗样本检测")
        test_inputs = [
            "正常查询: 锂离子电池研究",
            "零宽字符: 锂\u200b离子\u200c电池",
        ]
        for text in test_inputs:
            result = await self.safety_guard.check_input(text)
            print(f"  '{text[:20]}...': {result.get('risk_level', 'unknown')}")
        
        # 4. 性能统计
        print("\n[4/4] 性能统计")
        print(f"  总查询数: {self._performance_stats['queries']}")
        if self._performance_stats['queries'] > 0:
            avg_time = self._performance_stats['total_time'] / self._performance_stats['queries']
            print(f"  平均处理时间: {avg_time:.2f}s")
        
        print("\n" + "=" * 70)
    
    async def close(self):
        """关闭所有Agent"""
        print("\n正在关闭系统...")
        for agent in self.agents.values():
            await agent.stop()
        if self.orchestrator:
            await self.orchestrator.stop()
        print("✓ 系统已关闭")
        
        # v8.1: 打印日志摘要
        if self.logger:
            self.logger.print_summary()


# ==============================================================================
# 2. API测试模式 - 通过HTTP调用
# ==============================================================================

class APIAgentTester:
    """
    通过HTTP API测试（需要服务器已启动）- v8.1
    """
    
    def __init__(self, base_url: str = "http://localhost:8000", enable_logging: bool = True, session_name: str = None):
        self.base_url = base_url
        
        # v8.1: 测试日志记录器
        self.logger: Optional[TestLogger] = None
        if enable_logging:
            self.logger = TestLogger(session_name=session_name)
        
    async def query(self, user_query: str, depth: int = 2, query_type: str = "user") -> Dict[str, Any]:
        """通过API发送查询"""
        import aiohttp
        
        # v8.1: 记录输入
        query_id = None
        if self.logger:
            query_id = self.logger.log_query(user_query, query_type)
        
        print(f"\n{'='*70}")
        print(f"用户查询: {user_query}")
        print(f"API地址: {self.base_url}/query")
        print(f"{'='*70}\n")
        
        start_time = time.time()
        
        try:
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
                        
                        # v8.1: 记录输出
                        if self.logger and query_id:
                            self.logger.log_response(query_id, result)
                        
                        return result
                    else:
                        error_text = await response.text()
                        error_result = {
                            "success": False,
                            "status": f"error_{response.status}",
                            "error": error_text,
                            "processing_time": time.time() - start_time
                        }
                        
                        # v8.1: 记录错误
                        if self.logger and query_id:
                            self.logger.log_response(query_id, error_result)
                        
                        return error_result
        except Exception as e:
            error_result = {
                "success": False,
                "status": "exception",
                "error": str(e),
                "processing_time": time.time() - start_time
            }
            
            # v8.1: 记录异常
            if self.logger and query_id:
                self.logger.log_response(query_id, error_result)
            
            return error_result
    
    def print_summary(self):
        """打印日志摘要 (v8.1)"""
        if self.logger:
            self.logger.print_summary()
    
    async def health_check(self) -> bool:
        """检查服务器健康状态 (v8.1)"""
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"服务器状态: {data.get('status', 'unknown')}")
                        print(f"版本: {data.get('version', 'unknown')}")
                        print(f"可用Agent: {', '.join(data.get('agents', []))}")
                        
                        # v8.1: 显示新特性状态
                        features = data.get('features', {})
                        if features:
                            print("\nv8.1 特性状态:")
                            for feature, enabled in features.items():
                                status = "✓" if enabled else "✗"
                                print(f"  {status} {feature}")
                        
                        # v8.1: 分区统计
                        partition_stats = data.get('partition_stats', {})
                        if partition_stats:
                            print(f"\n分区统计: {partition_stats}")
                        
                        return True
                    return False
        except Exception as e:
            print(f"无法连接到服务器: {e}")
            return False
    
    async def get_metrics(self) -> Dict:
        """获取性能指标 (v8.1)"""
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/metrics") as response:
                    if response.status == 200:
                        return await response.json()
                    return {}
        except Exception as e:
            print(f"获取指标失败: {e}")
            return {}


# ==============================================================================
# 3. 测试结果展示
# ==============================================================================

def print_result(result: Dict[str, Any]):
    """美化打印结果 (v8.1)"""
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
    
    # v8.1: 显示分类信息
    classification = result.get("classification", {})
    if classification:
        print(f"\n🎯 任务分类 (v8.1):")
        print(f"  - 领域: {classification.get('domain', 'unknown')}")
        print(f"  - 复杂度评分: {classification.get('complexity_score', 0)}/10")
        print(f"  - 置信度: {classification.get('confidence', 0):.2f}")
    
    print(f"\n💬 回答内容:")
    print("-" * 70)
    answer = result.get('answer', '无回答')
    print(answer)
    print("-" * 70)
    
    citations = result.get('citations', [])
    if citations:
        print(f"\n📚 引用文献 ({len(citations)}篇):")
        for i, citation in enumerate(citations[:5], 1):
            title = citation.get('doc_title', 'Unknown')
            year = citation.get('year', 'n.d.')
            # v8.1: 显示冲突标记
            conflict = citation.get('conflict_mark', '')
            conflict_str = f" [⚠️{conflict}]" if conflict else ""
            print(f"  {i}. {title} ({year}){conflict_str}")
        if len(citations) > 5:
            print(f"  ... 还有 {len(citations) - 5} 篇引用")
    
    qc_report = result.get('qc_report')
    if qc_report:
        print(f"\n✅ 质量控制报告:")
        print(f"  - 总体评分: {qc_report.get('overall_score', 'N/A')}")
        print(f"  - 审核状态: {'通过' if qc_report.get('approved') else '需改进'}")


def print_welcome():
    """打印欢迎信息 (v8.1)"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║           ChemMind Multi-Agent System v8.1 - 测试脚本                ║
║                                                                      ║
║  院士级化学研究智能体系统 - 全栈算法升级版                            ║
║                                                                      ║
║  v8.1 升级特性:                                                       ║
║    • 智能路由 + WFQ调度 (MessageBus)                                 ║
║    • 语义缓存 + 自适应批处理 (LLM)                                    ║
║    • 自适应检索 + 级联重排序 (RAG)                                    ║
║    • 分层分类 + 并行子任务 (Orchestrator)                             ║
║    • 上下文感知 + 对抗检测 (SafetyGuard)                              ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")


# ==============================================================================
# 4. 主程序
# ==============================================================================

async def interactive_mode(tester):
    """交互式测试模式"""
    print("\n进入交互式测试模式，输入查询内容（输入 'quit' 退出）：\n")
    
    # v8.1: 显示测试命令
    print("特殊命令:")
    print("  :features - 测试 v8.1 新特性")
    print("  :metrics  - 查看性能指标 (API模式)")
    print("  :quit     - 退出测试")
    print()
    
    while True:
        try:
            query = input("> ").strip()
            
            if query.lower() in ['quit', 'exit', 'q', ':quit']:
                print("退出测试...")
                break
            
            if query == ':features':
                if hasattr(tester, 'test_v81_features'):
                    await tester.test_v81_features()
                else:
                    print("⚠ 直接测试模式不支持此命令")
                continue
            
            if query == ':metrics':
                if hasattr(tester, 'get_metrics'):
                    metrics = await tester.get_metrics()
                    print(json.dumps(metrics, indent=2, ensure_ascii=False))
                else:
                    print("⚠ API测试模式才支持此命令")
                continue
            
            if not query:
                continue
            
            result = await tester.query(query)
            print_result(result)
            
        except KeyboardInterrupt:
            print("\n\n退出测试...")
            break
        except Exception as e:
            print(f"\n错误: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="ChemMind Multi-Agent System v8.1 测试脚本"
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
    parser.add_argument(
        '--test-features',
        action='store_true',
        help='测试 v8.1 新特性 (仅direct模式)'
    )
    
    args = parser.parse_args()
    
    print_welcome()
    
    tester = None
    
    try:
        if args.mode == 'direct':
            # 直接测试模式
            tester = DirectAgentTester()
            await tester.initialize()
            
            # v8.1: 测试新特性
            if args.test_features:
                await tester.test_v81_features()
                
        else:
            # API测试模式
            tester = APIAgentTester(args.url)
            print("\n检查服务器状态...")
            if not await tester.health_check():
                print("\n❌ 无法连接到服务器，请确保服务器已启动:")
                print("   python agent_rag_v8_1.py")
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
        elif isinstance(tester, APIAgentTester):
            tester.print_summary()


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
