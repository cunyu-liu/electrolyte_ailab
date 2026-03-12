"""
================================================================================
True Multi-Agent Architecture v7 - 真正的多智能体系统
================================================================================

核心设计理念：
- 从"流水线执行者"转变为"自主决策者"
- LLM动态规划：Agent自主决定下一步做什么
- LLM自主选择工具：Agent推理选择最合适的工具
- 自然语言对话：支持交互式多轮对话
- LLM推理：真正的ReAct思考-行动-观察循环
- 执行后自我评估：每步执行后的反思和改进

架构角色：
- OrchestratorAgent: 中央协调者，负责任务分发和全局状态管理
- PlanningAgent: 动态规划者，将目标分解为可执行计划
- ReasoningAgent: 推理执行者，使用ReAct循环自主选择和执行工具
- EvaluationAgent: 评估反思者，对执行结果进行质量评估
- ChatAgent: 对话管理者，处理自然语言交互
- MemoryAgent: 记忆管理者，管理短期和长期记忆

使用模型：本地 Qwen3-0.6B

测试结果：
"""

import uvicorn
import torch
import logging
import re
import json
import asyncio
import uuid
from abc import ABC, abstractmethod
from enum import Enum, auto
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple, Set, Callable, Union, AsyncGenerator
from datetime import datetime
from collections import defaultdict
import numpy as np
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from threading import Thread
from sentence_transformers import SentenceTransformer
from FlagEmbedding import FlagReranker
from pymilvus import connections, Collection, utility
from elasticsearch import Elasticsearch


# ==============================================================================
# 0. 配置与基础设施
# ==============================================================================

if torch.cuda.is_available():
    DEVICE = "cuda"
    dtype = torch.float16
elif torch.backends.mps.is_available():
    DEVICE = "mps"
    dtype = torch.float32
else:
    DEVICE = "cpu"
    dtype = torch.float32

LLM_MODEL_PATH = "/Users/liucunyu/.cache/modelscope/hub/models/Qwen/Qwen3-0.6B"
EMBEDDING_MODEL_NAME = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/Xorbits/bge-m3"
RERANKER_MODEL_NAME = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/bge-reranker-v2-m3"

MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
MILVUS_COLLECTION_NAME = "electrolyte_papers_chunked_v3"
MILVUS_VECTOR_FIELD = "embeddings"
MILVUS_TEXT_FIELD = "content"

ES_HOST = "http://127.0.0.1:9200"
ES_INDEX = "electrolyte_papers_index"

SEARCH_TOP_K = 100
RERANK_TOP_K = 10
MAX_EXPERIMENT_CYCLES = 10
TARGET_METRIC_THRESHOLD = 99.5
BATCH_SIZE = 4

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ==============================================================================
# 1. 核心数据结构
# ==============================================================================

class MessageType(Enum):
    TASK_ASSIGN = "task_assign"           # 分配任务
    TASK_RESULT = "task_result"           # 任务结果
    PLAN_REQUEST = "plan_request"         # 请求规划
    PLAN_RESPONSE = "plan_response"       # 规划响应
    TOOL_CALL = "tool_call"               # 工具调用
    TOOL_RESULT = "tool_result"           # 工具结果
    REASONING = "reasoning"               # 推理过程
    EVALUATION = "evaluation"             # 评估结果
    CHAT_MESSAGE = "chat_message"         # 聊天消息
    MEMORY_UPDATE = "memory_update"       # 记忆更新
    SYSTEM_EVENT = "system_event"         # 系统事件


@dataclass
class AgentMessage:
    """Agent间通信消息"""
    sender: str
    receiver: Optional[str]               # None表示广播
    message_type: MessageType
    payload: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None  # 关联的任务ID
    requires_response: bool = False
    priority: int = 1                     # 消息优先级 1-10


@dataclass
class ToolCall:
    """工具调用描述"""
    tool_name: str
    parameters: Dict[str, Any]
    reasoning: str                        # 选择此工具的理由
    expected_outcome: str                 # 期望结果


@dataclass
class ExecutionStep:
    """执行步骤"""
    step_id: str
    description: str
    tool_call: Optional[ToolCall]
    status: str = "pending"               # pending, running, completed, failed
    result: Any = None
    evaluation: Optional[Dict] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


@dataclass
class Plan:
    """动态规划"""
    plan_id: str
    goal: str
    steps: List[ExecutionStep]
    current_step_idx: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceLocation:
    doc_id: str
    doc_name: str
    page: int
    paragraph: int
    char_start: int
    char_end: int
    section_title: Optional[str] = None
    surrounding_context: Optional[str] = None


@dataclass
class ResearchFinding:
    content: str
    source_locations: List[SourceLocation]
    confidence: float
    exploration_depth: int
    query_path: List[str]
    chunk_ids: List[str]


@dataclass
class ConversationTurn:
    role: str                             # user, assistant, system, tool
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class DeepResearchConfig:
    MAX_DEPTH = 3
    INITIAL_BREADTH = 4
    MIN_BREADTH = 1
    TOP_K_PER_QUERY = 8
    SIMILARITY_THRESHOLD = 0.85
    MAX_TOTAL_CHUNKS = 100


@dataclass
class StructuredRequirement:
    target_application: str
    key_constraints: Dict[str, Any]
    desired_properties: Dict[str, float]
    priority_weight: float = 1.0


# ==============================================================================
# 2. 共享基础设施
# ==============================================================================

class MessageBus:
    """异步消息总线 - Agent间松耦合通信"""
    def __init__(self):
        self._queues: Dict[str, asyncio.Queue] = {}
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    def register_agent(self, agent_id: str):
        if agent_id not in self._queues:
            self._queues[agent_id] = asyncio.Queue(maxsize=1000)
            logger.info(f"[MessageBus] Registered: {agent_id}")
    
    def unregister_agent(self, agent_id: str):
        if agent_id in self._queues:
            del self._queues[agent_id]
            logger.info(f"[MessageBus] Unregistered: {agent_id}")
    
    async def send(self, message: AgentMessage):
        # 触发订阅者
        for callback in self._subscribers.get(message.message_type.value, []):
            asyncio.create_task(callback(message))
        
        if message.receiver:
            if message.receiver in self._queues:
                await self._queues[message.receiver].put(message)
        else:
            # 广播
            for agent_id, queue in self._queues.items():
                if agent_id != message.sender:
                    await queue.put(message)
    
    async def get_message(self, agent_id: str, timeout: Optional[float] = None) -> Optional[AgentMessage]:
        if agent_id not in self._queues:
            return None
        try:
            return await asyncio.wait_for(self._queues[agent_id].get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
    
    def subscribe(self, message_type: str, callback: Callable):
        self._subscribers[message_type].append(callback)


class SharedMemory:
    """共享内存 - 所有Agent可访问的状态存储"""
    def __init__(self):
        self._state: Dict[str, Any] = {}
        self._conversations: Dict[str, List[ConversationTurn]] = defaultdict(list)
        self._plans: Dict[str, Plan] = {}
        self._workflows: Dict[str, Dict] = {}
        self._audit_log: List[Dict] = []
        self._lock = asyncio.Lock()
    
    async def create_workflow(self, goal: str, context: Dict = None) -> str:
        """创建新的工作流"""
        workflow_id = str(uuid.uuid4())
        async with self._lock:
            self._workflows[workflow_id] = {
                "workflow_id": workflow_id,
                "goal": goal,
                "context": context or {},
                "status": "created",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "current_plan_id": None,
                "execution_history": []
            }
        return workflow_id
    
    async def get_workflow(self, workflow_id: str) -> Optional[Dict]:
        return self._workflows.get(workflow_id)
    
    async def update_workflow(self, workflow_id: str, updates: Dict):
        async with self._lock:
            if workflow_id in self._workflows:
                self._workflows[workflow_id].update(updates)
                self._workflows[workflow_id]["updated_at"] = datetime.now().isoformat()
    
    async def store_plan(self, plan: Plan):
        async with self._lock:
            self._plans[plan.plan_id] = plan
    
    async def get_plan(self, plan_id: str) -> Optional[Plan]:
        return self._plans.get(plan_id)
    
    async def update_plan(self, plan_id: str, updates: Dict):
        async with self._lock:
            if plan_id in self._plans:
                for key, value in updates.items():
                    setattr(self._plans[plan_id], key, value)
    
    async def add_conversation_turn(self, session_id: str, turn: ConversationTurn):
        async with self._lock:
            self._conversations[session_id].append(turn)
    
    async def get_conversation(self, session_id: str) -> List[ConversationTurn]:
        return list(self._conversations.get(session_id, []))
    
    async def store(self, key: str, value: Any, workflow_id: Optional[str] = None):
        """通用存储"""
        async with self._lock:
            full_key = f"{workflow_id}:{key}" if workflow_id else key
            self._state[full_key] = {
                "value": value,
                "stored_at": datetime.now().isoformat()
            }
    
    async def retrieve(self, key: str, workflow_id: Optional[str] = None) -> Any:
        """通用检索"""
        full_key = f"{workflow_id}:{key}" if workflow_id else key
        entry = self._state.get(full_key)
        return entry["value"] if entry else None
    
    async def append_audit(self, action: str, details: Dict):
        self._audit_log.append({
            "action": action,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })


# ==============================================================================
# 3. LLM 服务 - 所有Agent共享
# ==============================================================================

class LLMService:
    """LLM服务 - 提供推理、规划、对话能力"""
    
    def __init__(self, model_path: str):
        logger.info(f"Loading LLM from {model_path}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=dtype,
            device_map="auto",
            trust_remote_code=True
        )
        self.model.eval()
        logger.info("LLM loaded successfully")
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        max_new_tokens: int = 1024,
        temperature: float = 0.7,
        stop_strings: List[str] = None,
        stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        """生成回复"""
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        if stream:
            return self._generate_stream(inputs, max_new_tokens, temperature, stop_strings)
        else:
            return self._generate_sync(inputs, max_new_tokens, temperature, stop_strings)
    
    def _generate_sync(
        self,
        inputs,
        max_new_tokens: int,
        temperature: float,
        stop_strings: List[str]
    ) -> str:
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                stop_strings=stop_strings,
                tokenizer=self.tokenizer if stop_strings else None
            )
        
        response = self.tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:],
            skip_special_tokens=True
        )
        
        # 处理stop_strings
        if stop_strings:
            for stop in stop_strings:
                if stop in response:
                    response = response.split(stop)[0]
        
        return response.strip()
    
    async def _generate_stream(
        self,
        inputs,
        max_new_tokens: int,
        temperature: float,
        stop_strings: List[str]
    ) -> AsyncGenerator[str, None]:
        """流式生成"""
        streamer = TextIteratorStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True
        )
        
        generation_kwargs = {
            **inputs,
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "do_sample": True,
            "pad_token_id": self.tokenizer.eos_token_id,
            "streamer": streamer
        }
        
        thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()
        
        for text in streamer:
            yield text
        
        thread.join()
    
    def extract_json(self, text: str) -> Optional[Any]:
        """从文本中提取JSON"""
        # 尝试代码块
        patterns = [
            r'```(?:json)?\s*([\s\S]*?)\s*```',
            r'\{[\s\S]*\}',
            r'\[[\s\S]*\]'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    return json.loads(match)
                except:
                    continue
        
        # 尝试整个文本
        try:
            return json.loads(text)
        except:
            pass
        
        return None


# ==============================================================================
# 4. 工具定义
# ==============================================================================

class ToolRegistry:
    """工具注册表 - 所有可用工具"""
    
    TOOLS = {
        "literature_deep_search": {
            "description": "深度文献检索 - 在知识库中进行深度搜索，获取相关研究文献",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "搜索查询语句",
                    "required": True
                },
                "depth": {
                    "type": "integer",
                    "description": "搜索深度 (1-3)",
                    "default": 2
                },
                "breadth": {
                    "type": "integer",
                    "description": "搜索广度 (1-5)",
                    "default": 3
                }
            }
        },
        "extract_chemical_entities": {
            "description": "化学实体提取 - 从文献中提取化学物质、材料、配方等实体",
            "parameters": {
                "text": {
                    "type": "string",
                    "description": "要分析的文本内容",
                    "required": True
                }
            }
        },
        "molecular_design": {
            "description": "分子设计 - 基于需求设计或扩展分子库",
            "parameters": {
                "base_entities": {
                    "type": "array",
                    "description": "基础化学实体列表",
                    "required": True
                },
                "design_strategy": {
                    "type": "string",
                    "description": "设计策略描述",
                    "required": True
                }
            }
        },
        "property_prediction": {
            "description": "性质预测 - 预测材料的电化学性质",
            "parameters": {
                "molecules": {
                    "type": "array",
                    "description": "待预测的分子列表",
                    "required": True
                },
                "target_properties": {
                    "type": "object",
                    "description": "目标性质",
                    "required": True
                }
            }
        },
        "formulate_recipe": {
            "description": "配方生成 - 生成具体的电解液配方",
            "parameters": {
                "components": {
                    "type": "array",
                    "description": "配方组分",
                    "required": True
                },
                "constraints": {
                    "type": "object",
                    "description": "约束条件",
                    "default": {}
                }
            }
        },
        "run_simulation": {
            "description": "运行模拟实验 - 对配方进行模拟测试",
            "parameters": {
                "recipe": {
                    "type": "object",
                    "description": "配方数据",
                    "required": True
                },
                "test_type": {
                    "type": "string",
                    "description": "测试类型",
                    "default": "electrochemical"
                }
            }
        },
        "analyze_results": {
            "description": "结果分析 - 分析实验结果并提供见解",
            "parameters": {
                "results": {
                    "type": "object",
                    "description": "实验结果数据",
                    "required": True
                },
                "analysis_type": {
                    "type": "string",
                    "description": "分析类型: summary, detailed, comparative",
                    "default": "detailed"
                }
            }
        },
        "optimize_parameters": {
            "description": "参数优化 - 基于结果优化配方参数",
            "parameters": {
                "current_recipe": {
                    "type": "object",
                    "description": "当前配方",
                    "required": True
                },
                "performance_data": {
                    "type": "object",
                    "description": "性能数据",
                    "required": True
                },
                "target_metrics": {
                    "type": "object",
                    "description": "目标指标",
                    "required": True
                }
            }
        },
        "web_search": {
            "description": "网络搜索 - 搜索最新信息和补充知识",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "搜索查询",
                    "required": True
                }
            }
        },
        "ask_user": {
            "description": "询问用户 - 当信息不足时向用户提问",
            "parameters": {
                "question": {
                    "type": "string",
                    "description": "要问用户的问题",
                    "required": True
                }
            }
        }
    }
    
    @classmethod
    def get_tool_schema(cls, tool_name: str) -> Optional[Dict]:
        return cls.TOOLS.get(tool_name)
    
    @classmethod
    def get_all_tools(cls) -> Dict:
        return cls.TOOLS
    
    @classmethod
    def format_tools_for_prompt(cls) -> str:
        """格式化工具描述供LLM使用"""
        lines = ["Available Tools:"]
        for name, spec in cls.TOOLS.items():
            lines.append(f"\n{name}:")
            lines.append(f"  Description: {spec['description']}")
            lines.append(f"  Parameters:")
            for param_name, param_spec in spec.get('parameters', {}).items():
                req = " (required)" if param_spec.get('required') else ""
                lines.append(f"    - {param_name}: {param_spec.get('description', '')}{req}")
        return "\n".join(lines)


# ==============================================================================
# 5. RAG 服务（保留核心功能）
# ==============================================================================

class RAGService:
    """RAG核心服务"""
    
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service
        logger.info(f"Initializing RAG on {DEVICE}")
        
        self.embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=DEVICE)
        self.reranker_model = FlagReranker(RERANKER_MODEL_NAME, use_fp16=(DEVICE=="cuda"), device=DEVICE)
        
        self._connect_milvus()
        self._connect_es()
        
        self.citation_manager = CitationManager()
    
    def _connect_milvus(self):
        try:
            connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
            if utility.has_collection(MILVUS_COLLECTION_NAME):
                self.milvus_collection = Collection(MILVUS_COLLECTION_NAME)
                self.milvus_collection.load()
                logger.info("Milvus connected")
            else:
                self.milvus_collection = None
        except Exception as e:
            logger.error(f"Milvus error: {e}")
            self.milvus_collection = None
    
    def _connect_es(self):
        try:
            self.es_client = Elasticsearch([ES_HOST])
            if not self.es_client.ping():
                self.es_client = None
        except:
            self.es_client = None
    
    def get_embedding(self, text: str) -> List[float]:
        return self.embed_model.encode(text, normalize_embeddings=True).tolist()
    
    async def deep_search(self, query: str, depth: int = 2, breadth: int = 3) -> Dict:
        """深度搜索"""
        query_vec = self.get_embedding(query)
        results = []
        
        if self.milvus_collection:
            try:
                hits = self.milvus_collection.search(
                    data=[query_vec],
                    anns_field=MILVUS_VECTOR_FIELD,
                    param={"metric_type": "COSINE", "params": {"nprobe": 20}},
                    limit=SEARCH_TOP_K,
                    output_fields=[MILVUS_TEXT_FIELD, "metadata", "doc_id", "page_num"]
                )[0]
                
                for hit in hits:
                    entity = hit.entity
                    meta_raw = entity.get("metadata", {})
                    meta = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
                    
                    results.append({
                        "id": str(hit.id),
                        "content": entity.get(MILVUS_TEXT_FIELD, ""),
                        "score": float(hit.score),
                        "metadata": meta,
                        "doc_id": entity.get("doc_id") or meta.get("doc_id", "unknown"),
                        "page": entity.get("page_num") or meta.get("page", 0)
                    })
            except Exception as e:
                logger.error(f"Search error: {e}")
        
        # Rerank
        if len(results) > RERANK_TOP_K:
            pairs = [[query, r["content"]] for r in results]
            try:
                scores = self.reranker_model.compute_score(pairs, normalize=True)
                for i, score in enumerate(scores):
                    results[i]["rerank_score"] = score
                results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
                results = results[:RERANK_TOP_K]
            except Exception as e:
                logger.error(f"Rerank error: {e}")
                results = results[:RERANK_TOP_K]
        
        return {
            "query": query,
            "results": results,
            "total_found": len(results)
        }
    
    async def analyze_requirement(self, query: str) -> StructuredRequirement:
        """分析研究需求"""
        prompt = f"""分析电解液研发需求，提取JSON：
{{
    "target_application": "应用场景",
    "key_constraints": {{"voltage_window": "...", "temperature_range": "..."}},
    "desired_properties": {{"coulombic_efficiency": 99.5}},
    "priority_weight": 0.9
}}

需求: "{query}"
JSON:"""
        
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.generate(messages, max_new_tokens=512, temperature=0.2)
        
        try:
            parsed = self.llm.extract_json(response)
            if parsed:
                return StructuredRequirement(
                    target_application=parsed.get("target_application", "general"),
                    key_constraints=parsed.get("key_constraints", {}),
                    desired_properties=parsed.get("desired_properties", {}),
                    priority_weight=parsed.get("priority_weight", 0.5)
                )
        except Exception as e:
            logger.error(f"Parse error: {e}")
        
        return StructuredRequirement("general", {}, {}, 0.5)


class CitationManager:
    """引用管理"""
    def format_findings(self, findings: List[Dict]) -> str:
        formatted = []
        for i, f in enumerate(findings, 1):
            formatted.append(f"[{i}] {f.get('content', '')[:300]}...")
        return "\n\n".join(formatted)


# ==============================================================================
# 6. 真正的Agent基类 - 具备自主决策能力
# ==============================================================================

class TrueAgent(ABC):
    """
    真正的Agent基类
    
    特性：
    1. 自主决策：使用LLM进行推理和决策
    2. 工具选择：自主选择使用什么工具
    3. 自我评估：执行后进行反思
    4. 自然语言理解：理解并生成自然语言
    """
    
    def __init__(
        self,
        agent_id: str,
        message_bus: MessageBus,
        shared_memory: SharedMemory,
        llm_service: LLMService,
        rag_service: RAGService,
        system_prompt: str = ""
    ):
        self.agent_id = agent_id
        self.bus = message_bus
        self.memory = shared_memory
        self.llm = llm_service
        self.rag = rag_service
        self.system_prompt = system_prompt or f"You are {agent_id}, an intelligent AI agent."
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._logger = logging.getLogger(f"Agent.{agent_id}")
        
        # 注册到消息总线
        self.bus.register_agent(self.agent_id)
    
    async def start(self):
        """启动Agent"""
        self.running = True
        self._task = asyncio.create_task(self._lifecycle())
        self._logger.info(f"{self.agent_id} started")
    
    async def stop(self):
        """停止Agent"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.bus.unregister_agent(self.agent_id)
        self._logger.info(f"{self.agent_id} stopped")
    
    async def _lifecycle(self):
        """Agent生命周期"""
        try:
            while self.running:
                message = await self.bus.get_message(self.agent_id, timeout=0.1)
                if message:
                    await self._handle_message(message)
                await self._idle_work()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._logger.error(f"Lifecycle error: {e}", exc_info=True)
    
    async def _handle_message(self, message: AgentMessage):
        """处理收到的消息"""
        self._logger.debug(f"Received {message.message_type.value} from {message.sender}")
        
        try:
            if message.message_type == MessageType.TASK_ASSIGN:
                await self._handle_task_assignment(message)
            elif message.message_type == MessageType.TOOL_RESULT:
                await self._handle_tool_result(message)
            elif message.message_type == MessageType.CHAT_MESSAGE:
                await self._handle_chat(message)
            else:
                await self.handle_custom_message(message)
        except Exception as e:
            self._logger.error(f"Error handling message: {e}")
            await self._send_error(message.correlation_id, str(e))
    
    @abstractmethod
    async def _handle_task_assignment(self, message: AgentMessage):
        """处理任务分配 - 子类必须实现"""
        pass
    
    async def _handle_tool_result(self, message: AgentMessage):
        """处理工具执行结果"""
        # 默认行为：可以被子类覆盖
        pass
    
    async def _handle_chat(self, message: AgentMessage):
        """处理聊天消息"""
        # 默认行为：可以被子类覆盖
        pass
    
    async def handle_custom_message(self, message: AgentMessage):
        """处理自定义消息类型 - 子类可覆盖"""
        pass
    
    async def _idle_work(self):
        """空闲时的工作 - 子类可覆盖"""
        await asyncio.sleep(0.01)
    
    async def think(
        self,
        context: str,
        task: str,
        available_tools: Optional[List[str]] = None
    ) -> Dict:
        """
        思考过程 - 使用ReAct模式
        
        Returns:
            {
                "thought": "思考过程",
                "action": "选择的行动",
                "action_input": {行动参数},
                "reasoning": "决策理由"
            }
        """
        tools_desc = ToolRegistry.format_tools_for_prompt() if available_tools else ""
        if available_tools:
            tools_desc = "\n".join([
                f"- {name}: {ToolRegistry.TOOLS[name]['description']}"
                for name in available_tools if name in ToolRegistry.TOOLS
            ])
        
        prompt = f"""{self.system_prompt}

{tools_desc}

Context:
{context}

Task:
{task}

请使用以下格式回复：

Thought: 详细分析当前情况，思考应该采取什么行动
Action: 选择的工具名称（从Available Tools中选择，或填"finish"表示完成任务，或填"ask_user"表示需要更多信息）
Action Input: {{"参数名": "参数值"}}  
Reasoning: 解释为什么选择这个行动

你的回复："""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.generate(messages, max_new_tokens=1024, temperature=0.3)
        
        # 解析ReAct格式
        parsed = self._parse_react_response(response)
        return parsed
    
    def _parse_react_response(self, response: str) -> Dict:
        """解析ReAct格式的响应"""
        thought_match = re.search(r"Thought:\s*(.*?)(?=Action:|$)", response, re.DOTALL | re.IGNORECASE)
        action_match = re.search(r"Action:\s*(\w+)", response, re.IGNORECASE)
        input_match = re.search(r"Action Input:\s*(\{.*?\})(?=Reasoning:|$)", response, re.DOTALL | re.IGNORECASE)
        reasoning_match = re.search(r"Reasoning:\s*(.*?)$", response, re.DOTALL | re.IGNORECASE)
        
        thought = thought_match.group(1).strip() if thought_match else response
        action = action_match.group(1).strip() if action_match else "finish"
        
        action_input = {}
        if input_match:
            try:
                action_input = json.loads(input_match.group(1))
            except:
                action_input = {"raw": input_match.group(1).strip()}
        
        reasoning = reasoning_match.group(1).strip() if reasoning_match else ""
        
        return {
            "thought": thought,
            "action": action,
            "action_input": action_input,
            "reasoning": reasoning
        }
    
    async def evaluate(
        self,
        task: str,
        action_taken: str,
        result: Any,
        expectation: str
    ) -> Dict:
        """
        自我评估 - 评估执行结果
        
        Returns:
            {
                "success": bool,
                "quality_score": float,  # 0-1
                "analysis": "评估分析",
                "suggestions": [改进建议],
                "should_retry": bool
            }
        """
        prompt = f"""评估以下任务执行结果：

任务: {task}
采取的行动: {action_taken}
期望结果: {expectation}
实际结果: {json.dumps(result, ensure_ascii=False, default=str)[:2000]}

请以JSON格式回复评估结果：
{{
    "success": true/false,
    "quality_score": 0.0-1.0,
    "analysis": "详细分析",
    "suggestions": ["建议1", "建议2"],
    "should_retry": true/false
}}"""
        
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.generate(messages, max_new_tokens=512, temperature=0.2)
        
        parsed = self.llm.extract_json(response)
        if parsed:
            return {
                "success": parsed.get("success", False),
                "quality_score": parsed.get("quality_score", 0.0),
                "analysis": parsed.get("analysis", ""),
                "suggestions": parsed.get("suggestions", []),
                "should_retry": parsed.get("should_retry", False)
            }
        
        return {
            "success": False,
            "quality_score": 0.0,
            "analysis": "评估解析失败",
            "suggestions": [],
            "should_retry": False
        }
    
    async def send_message(
        self,
        receiver: Optional[str],
        message_type: MessageType,
        payload: Dict,
        correlation_id: Optional[str] = None,
        requires_response: bool = False
    ):
        """发送消息"""
        message = AgentMessage(
            sender=self.agent_id,
            receiver=receiver,
            message_type=message_type,
            payload=payload,
            correlation_id=correlation_id,
            requires_response=requires_response
        )
        await self.bus.send(message)
    
    async def _send_result(
        self,
        correlation_id: str,
        result: Dict,
        status: str = "success"
    ):
        """发送任务结果"""
        await self.send_message(
            receiver="orchestrator",
            message_type=MessageType.TASK_RESULT,
            payload={"status": status, "result": result},
            correlation_id=correlation_id
        )
    
    async def _send_error(self, correlation_id: Optional[str], error: str):
        """发送错误通知"""
        await self.send_message(
            receiver="orchestrator",
            message_type=MessageType.TASK_RESULT,
            payload={"status": "error", "error": error},
            correlation_id=correlation_id
        )


# ==============================================================================
# 7. 专业Agent实现
# ==============================================================================

class PlanningAgent(TrueAgent):
    """
    规划Agent - 负责将目标分解为可执行计划
    
    能力：
    - 理解复杂目标
    - 动态分解为步骤
    - 识别依赖关系
    - 估算步骤复杂度
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_id="planning_agent",
            system_prompt="""你是Planning Agent，一个专业的任务规划专家。
你的职责是将复杂目标分解为清晰、可执行的步骤。

原则：
1. 步骤要具体、可操作
2. 考虑步骤间的依赖关系
3. 识别需要的工具和资源
4. 设置明确的完成标准

输出格式必须是有效的JSON。""",
            **kwargs
        )
    
    async def _handle_task_assignment(self, message: AgentMessage):
        """处理规划任务"""
        goal = message.payload.get("goal", "")
        context = message.payload.get("context", {})
        correlation_id = message.correlation_id
        
        self._logger.info(f"Planning for goal: {goal[:50]}...")
        
        # 创建动态规划
        plan = await self._create_plan(goal, context)
        
        # 存储计划
        await self.memory.store_plan(plan)
        await self.memory.update_workflow(correlation_id, {"current_plan_id": plan.plan_id})
        
        # 返回结果
        await self._send_result(correlation_id, {
            "plan_id": plan.plan_id,
            "steps_count": len(plan.steps),
            "steps": [{"id": s.step_id, "description": s.description, "status": s.status} for s in plan.steps]
        })
    
    async def _create_plan(self, goal: str, context: Dict) -> Plan:
        """使用LLM创建动态计划"""
        tools_desc = ToolRegistry.format_tools_for_prompt()
        
        prompt = f"""请为以下目标创建一个详细的执行计划：

目标: {goal}

可用工具:
{tools_desc}

上下文信息:
{json.dumps(context, ensure_ascii=False, indent=2)}

请输出JSON格式的计划：
{{
    "steps": [
        {{
            "description": "步骤描述",
            "tool": "工具名称（可选）",
            "tool_params": {{"参数": "值"}},
            "depends_on": [],
            "success_criteria": "完成标准"
        }}
    ],
    "estimated_complexity": "low/medium/high",
    "key_risks": ["风险1", "风险2"]
}}

计划要求：
1. 步骤要具体、可执行
2. 明确每个步骤的完成标准
3. 考虑可能的失败情况"""
        
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.generate(messages, max_new_tokens=1536, temperature=0.3)
        
        plan_data = self.llm.extract_json(response)
        
        if not plan_data or "steps" not in plan_data:
            # 使用默认计划
            plan_data = {
                "steps": [
                    {"description": f"分析目标: {goal}", "tool": "analyze_results"},
                    {"description": "检索相关信息", "tool": "literature_deep_search"},
                    {"description": "制定解决方案", "tool": None}
                ]
            }
        
        steps = []
        for i, step_data in enumerate(plan_data.get("steps", [])):
            tool_call = None
            if step_data.get("tool") and step_data["tool"] in ToolRegistry.TOOLS:
                tool_call = ToolCall(
                    tool_name=step_data["tool"],
                    parameters=step_data.get("tool_params", {}),
                    reasoning=f"步骤 {i+1}",
                    expected_outcome=step_data.get("success_criteria", "")
                )
            
            step = ExecutionStep(
                step_id=f"step_{i}_{uuid.uuid4().hex[:8]}",
                description=step_data.get("description", f"Step {i+1}"),
                tool_call=tool_call
            )
            steps.append(step)
        
        plan = Plan(
            plan_id=f"plan_{uuid.uuid4().hex[:12]}",
            goal=goal,
            steps=steps,
            metadata={
                "complexity": plan_data.get("estimated_complexity", "medium"),
                "risks": plan_data.get("key_risks", [])
            }
        )
        
        return plan


class ReasoningAgent(TrueAgent):
    """
    推理执行Agent - 核心执行Agent
    
    能力：
    - 理解任务目标
    - 使用ReAct循环自主决策
    - 自主选择工具
    - 动态调整策略
    - 执行后自我评估
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_id="reasoning_agent",
            system_prompt="""你是Reasoning Agent，一个具备自主决策能力的AI助手。

核心能力：
1. 使用ReAct模式（思考-行动-观察）解决问题
2. 自主选择合适的工具
3. 根据反馈调整策略
4. 对执行结果进行自我评估

可用行动：
- 调用工具完成具体任务
- finish: 完成任务并返回结果
- ask_user: 需要更多信息时询问用户

原则：
- 每个行动前都要有清晰的思考
- 选择最适合当前情况的工具
- 失败后分析原因并尝试替代方案
- 保持对目标的聚焦""",
            **kwargs
        )
        self._active_tasks: Dict[str, Dict] = {}  # 活跃任务状态
    
    async def _handle_task_assignment(self, message: AgentMessage):
        """处理执行任务"""
        task = message.payload.get("task", "")
        context = message.payload.get("context", {})
        available_tools = message.payload.get("tools", list(ToolRegistry.TOOLS.keys()))
        correlation_id = message.correlation_id
        max_iterations = message.payload.get("max_iterations", 10)
        
        self._logger.info(f"Executing task: {task[:50]}...")
        
        # 初始化任务状态
        self._active_tasks[correlation_id] = {
            "task": task,
            "context": context,
            "history": [],
            "iteration": 0,
            "accumulated_results": []
        }
        
        # ReAct循环
        final_result = await self._react_loop(
            correlation_id=correlation_id,
            task=task,
            context=context,
            available_tools=available_tools,
            max_iterations=max_iterations
        )
        
        # 清理
        del self._active_tasks[correlation_id]
        
        # 返回结果
        await self._send_result(correlation_id, final_result)
    
    async def _react_loop(
        self,
        correlation_id: str,
        task: str,
        context: Dict,
        available_tools: List[str],
        max_iterations: int
    ) -> Dict:
        """ReAct执行循环"""
        task_state = self._active_tasks[correlation_id]
        
        for iteration in range(max_iterations):
            task_state["iteration"] = iteration
            
            # 构建上下文
            context_str = self._build_context(task_state)
            
            # 思考
            decision = await self.think(
                context=context_str,
                task=task,
                available_tools=available_tools + ["finish", "ask_user"]
            )
            
            self._logger.info(f"Iteration {iteration}: Action={decision['action']}")
            
            # 记录思考
            task_state["history"].append({
                "iteration": iteration,
                "thought": decision["thought"],
                "action": decision["action"],
                "reasoning": decision["reasoning"]
            })
            
            # 执行行动
            if decision["action"] == "finish":
                return await self._handle_finish(decision, task_state)
            
            elif decision["action"] == "ask_user":
                return await self._handle_ask_user(decision, task_state, correlation_id)
            
            else:
                # 执行工具
                tool_result = await self._execute_tool(
                    decision["action"],
                    decision["action_input"],
                    correlation_id
                )
                
                # 自我评估
                evaluation = await self.evaluate(
                    task=task,
                    action_taken=f"{decision['action']}: {json.dumps(decision['action_input'])}",
                    result=tool_result,
                    expectation=decision.get("reasoning", "")
                )
                
                task_state["history"][-1]["result"] = tool_result
                task_state["history"][-1]["evaluation"] = evaluation
                task_state["accumulated_results"].append(tool_result)
                
                # 如果评估建议重试，调整策略
                if evaluation.get("should_retry") and iteration < max_iterations - 1:
                    self._logger.info(f"Retry suggested: {evaluation.get('suggestions')}")
                    # 在下一次迭代中，LLM会看到失败历史并调整
        
        # 达到最大迭代次数
        return {
            "status": "max_iterations_reached",
            "final_answer": "达到最大迭代次数",
            "history": task_state["history"],
            "accumulated_results": task_state["accumulated_results"]
        }
    
    def _build_context(self, task_state: Dict) -> str:
        """构建上下文字符串"""
        lines = [f"任务: {task_state['task']}"]
        
        if task_state.get("context"):
            lines.append(f"背景信息: {json.dumps(task_state['context'], ensure_ascii=False)}")
        
        if task_state["history"]:
            lines.append("\n历史记录:")
            for h in task_state["history"][-3:]:  # 最近3步
                lines.append(f"\n第{h['iteration']+1}步:")
                lines.append(f"  思考: {h['thought'][:200]}...")
                lines.append(f"  行动: {h['action']}")
                if "result" in h:
                    result_str = json.dumps(h['result'], ensure_ascii=False, default=str)[:200]
                    lines.append(f"  结果: {result_str}...")
                if "evaluation" in h:
                    lines.append(f"  评估: 成功={h['evaluation'].get('success')}, 质量={h['evaluation'].get('quality_score')}")
        
        return "\n".join(lines)
    
    async def _execute_tool(
        self,
        tool_name: str,
        parameters: Dict,
        correlation_id: str
    ) -> Dict:
        """执行工具"""
        self._logger.info(f"Executing tool: {tool_name}")
        
        # 发送工具调用消息给ToolExecutor
        future = asyncio.Future()
        
        async def callback(message: AgentMessage):
            if message.correlation_id == correlation_id and message.message_type == MessageType.TOOL_RESULT:
                if not future.done():
                    future.set_result(message.payload)
        
        self.bus.subscribe(MessageType.TOOL_RESULT.value, callback)
        
        await self.send_message(
            receiver="tool_executor",
            message_type=MessageType.TOOL_CALL,
            payload={
                "tool_name": tool_name,
                "parameters": parameters
            },
            correlation_id=correlation_id
        )
        
        try:
            result = await asyncio.wait_for(future, timeout=60)
            return result
        except asyncio.TimeoutError:
            return {"status": "error", "message": "Tool execution timeout"}
    
    async def _handle_finish(self, decision: Dict, task_state: Dict) -> Dict:
        """处理完成"""
        final_answer = decision["action_input"].get("answer", decision["thought"])
        
        # 最终自我评估
        overall_evaluation = await self.evaluate(
            task=task_state["task"],
            action_taken="finish",
            result={"final_answer": final_answer},
            expectation="成功完成任务"
        )
        
        return {
            "status": "success",
            "final_answer": final_answer,
            "iterations": task_state["iteration"] + 1,
            "history": task_state["history"],
            "overall_evaluation": overall_evaluation
        }
    
    async def _handle_ask_user(
        self,
        decision: Dict,
        task_state: Dict,
        correlation_id: str
    ) -> Dict:
        """处理询问用户"""
        question = decision["action_input"].get("question", "需要更多信息")
        
        return {
            "status": "needs_clarification",
            "question": question,
            "history": task_state["history"],
            "correlation_id": correlation_id
        }


class ToolExecutorAgent(TrueAgent):
    """
    工具执行Agent - 负责实际执行工具
    
    将工具调用转换为实际的RAG操作
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_id="tool_executor",
            system_prompt="You are the Tool Executor Agent.",
            **kwargs
        )
    
    async def _handle_task_assignment(self, message: AgentMessage):
        """ToolExecutor只响应TOOL_CALL消息"""
        pass
    
    async def handle_custom_message(self, message: AgentMessage):
        """处理工具调用"""
        if message.message_type == MessageType.TOOL_CALL:
            await self._execute_tool_call(message)
    
    async def _execute_tool_call(self, message: AgentMessage):
        """执行具体的工具"""
        tool_name = message.payload.get("tool_name")
        parameters = message.payload.get("parameters", {})
        correlation_id = message.correlation_id
        
        self._logger.info(f"Executing: {tool_name}")
        
        try:
            result = await self._do_execute(tool_name, parameters)
        except Exception as e:
            self._logger.error(f"Tool execution error: {e}")
            result = {"status": "error", "message": str(e)}
        
        # 返回结果
        await self.send_message(
            receiver=None,  # 广播
            message_type=MessageType.TOOL_RESULT,
            payload=result,
            correlation_id=correlation_id
        )
    
    async def _do_execute(self, tool_name: str, parameters: Dict) -> Dict:
        """实际执行工具"""
        
        if tool_name == "literature_deep_search":
            query = parameters.get("query", "")
            depth = parameters.get("depth", 2)
            breadth = parameters.get("breadth", 3)
            return await self.rag.deep_search(query, depth, breadth)
        
        elif tool_name == "extract_chemical_entities":
            text = parameters.get("text", "")
            return await self._extract_entities(text)
        
        elif tool_name == "molecular_design":
            base_entities = parameters.get("base_entities", [])
            strategy = parameters.get("design_strategy", "")
            return await self._design_molecules(base_entities, strategy)
        
        elif tool_name == "property_prediction":
            molecules = parameters.get("molecules", [])
            target_props = parameters.get("target_properties", {})
            return await self._predict_properties(molecules, target_props)
        
        elif tool_name == "formulate_recipe":
            components = parameters.get("components", [])
            constraints = parameters.get("constraints", {})
            return await self._formulate_recipe(components, constraints)
        
        elif tool_name == "run_simulation":
            recipe = parameters.get("recipe", {})
            test_type = parameters.get("test_type", "electrochemical")
            return await self._run_simulation(recipe, test_type)
        
        elif tool_name == "analyze_results":
            results = parameters.get("results", {})
            analysis_type = parameters.get("analysis_type", "detailed")
            return await self._analyze_results(results, analysis_type)
        
        elif tool_name == "optimize_parameters":
            recipe = parameters.get("current_recipe", {})
            performance = parameters.get("performance_data", {})
            targets = parameters.get("target_metrics", {})
            return await self._optimize(recipe, performance, targets)
        
        elif tool_name == "web_search":
            query = parameters.get("query", "")
            return {"status": "info", "message": "Web search not implemented in local mode"}
        
        elif tool_name == "ask_user":
            question = parameters.get("question", "")
            return {"status": "needs_clarification", "question": question}
        
        else:
            return {"status": "error", "message": f"Unknown tool: {tool_name}"}
    
    async def _extract_entities(self, text: str) -> Dict:
        """提取化学实体"""
        prompt = f"""从以下文本中提取化学实体：

文本: {text[:3000]}

提取：
1. 锂盐（LiPF6, LiFSI等）
2. 溶剂（EC, DEC, DMC等）
3. 添加剂（VC, FEC等）
4. 材料/电极

输出JSON：
{{
    "salts": ["..."],
    "solvents": ["..."],
    "additives": ["..."],
    "materials": ["..."]
}}"""
        
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.generate(messages, max_new_tokens=512, temperature=0.2)
        
        parsed = self.llm.extract_json(response)
        if parsed:
            return {"status": "success", "entities": parsed}
        
        return {
            "status": "success",
            "entities": {"salts": [], "solvents": [], "additives": [], "materials": []}
        }
    
    async def _design_molecules(self, base_entities: List, strategy: str) -> Dict:
        """分子设计"""
        # 模拟扩增
        expanded = {
            "base": base_entities,
            "expanded": base_entities + ["FEC", "VC", "LiBOB", "LiODFB"],
            "strategy_applied": strategy,
            "count": len(base_entities) + 4
        }
        return {"status": "success", "molecular_library": expanded}
    
    async def _predict_properties(self, molecules: List, target_props: Dict) -> Dict:
        """性质预测"""
        predictions = []
        for mol in molecules[:5]:
            predictions.append({
                "molecule": mol,
                "predicted": {
                    "conductivity": round(7.0 + np.random.uniform(-1, 1), 2),
                    "oxidation_potential": round(4.0 + np.random.uniform(-0.5, 0.5), 2),
                    "score": round(np.random.uniform(0.7, 0.95), 2)
                }
            })
        return {"status": "success", "predictions": predictions}
    
    async def _formulate_recipe(self, components: List, constraints: Dict) -> Dict:
        """配方生成"""
        recipes = []
        for i in range(BATCH_SIZE):
            recipe = {
                "salt": "LiPF6",
                "salt_conc": round(1.0 + np.random.uniform(-0.2, 0.2), 2),
                "solvents": {
                    "EC": round(np.random.uniform(0.2, 0.4), 2),
                    "DEC": round(np.random.uniform(0.3, 0.5), 2),
                    "FEC": round(np.random.uniform(0.05, 0.15), 2)
                }
            }
            recipes.append(recipe)
        
        return {
            "status": "success",
            "recipes": recipes,
            "recipe_group_id": f"recipe_{uuid.uuid4().hex[:8]}"
        }
    
    async def _run_simulation(self, recipe: Dict, test_type: str) -> Dict:
        """运行模拟实验"""
        ce = 98.5 + np.random.normal(0, 0.5)
        return {
            "status": "success",
            "results": {
                "coulombic_efficiency": round(float(ce), 2),
                "conductivity_ms": round(7.5 + np.random.normal(0, 0.5), 2),
                "cycle_life": int(500 + np.random.normal(0, 50))
            },
            "test_type": test_type
        }
    
    async def _analyze_results(self, results: Dict, analysis_type: str) -> Dict:
        """分析结果"""
        prompt = f"""分析以下实验结果：

数据: {json.dumps(results, ensure_ascii=False)}

分析类型: {analysis_type}

提供：
1. 关键发现
2. 数据质量评估
3. 改进建议

输出JSON：
{{
    "key_findings": ["..."],
    "quality_assessment": "...",
    "recommendations": ["..."]
}}"""
        
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.generate(messages, max_new_tokens=512, temperature=0.3)
        
        parsed = self.llm.extract_json(response)
        if parsed:
            return {"status": "success", "analysis": parsed}
        
        return {"status": "success", "analysis": {"key_findings": [], "quality_assessment": "", "recommendations": []}}
    
    async def _optimize(self, recipe: Dict, performance: Dict, targets: Dict) -> Dict:
        """优化参数"""
        return {
            "status": "success",
            "optimization": {
                "suggested_changes": {
                    "salt_conc": "+0.1M",
                    "FEC_ratio": "+2%"
                },
                "expected_improvement": "+0.5% CE",
                "confidence": 0.75
            }
        }


class EvaluationAgent(TrueAgent):
    """
    评估反思Agent - 对执行过程和结果进行深度评估
    
    能力：
    - 质量评估
    - 错误分析
    - 改进建议
    - 经验总结
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_id="evaluation_agent",
            system_prompt="""你是Evaluation Agent，一个严格的执行质量评估专家。

职责：
1. 评估任务执行的质量
2. 识别错误和失败原因
3. 提供具体的改进建议
4. 总结可复用的经验

评估维度：
- 正确性：结果是否正确
- 完整性：是否覆盖了所有要求
- 效率：执行路径是否最优
- 鲁棒性：对异常的处理能力

输出格式必须是结构化的评估报告。""",
            **kwargs
        )
    
    async def _handle_task_assignment(self, message: AgentMessage):
        """处理评估任务"""
        execution_history = message.payload.get("execution_history", [])
        original_goal = message.payload.get("goal", "")
        correlation_id = message.correlation_id
        
        self._logger.info(f"Evaluating execution for: {original_goal[:50]}...")
        
        evaluation_report = await self._create_evaluation(execution_history, original_goal)
        
        await self._send_result(correlation_id, evaluation_report)
    
    async def _create_evaluation(self, history: List[Dict], goal: str) -> Dict:
        """创建评估报告"""
        history_text = json.dumps(history, ensure_ascii=False, default=str)[:3000]
        
        prompt = f"""评估以下任务执行过程：

原始目标: {goal}

执行历史:
{history_text}

请提供详细评估报告，输出JSON格式：
{{
    "overall_score": 0.0-1.0,
    "correctness": 0.0-1.0,
    "completeness": 0.0-1.0,
    "efficiency": 0.0-1.0,
    "strengths": ["优点1", "优点2"],
    "weaknesses": ["不足1", "不足2"],
    "errors": [
        {{
            "step": "步骤",
            "error_type": "错误类型",
            "root_cause": "根本原因",
            "prevention": "预防措施"
        }}
    ],
    "improvements": ["改进建议1", "改进建议2"],
    "lessons_learned": ["经验1", "经验2"],
    "recommendations": {{
        "for_similar_tasks": "建议",
        "tool_selection": "工具选择建议",
        "planning": "规划建议"
    }}
}}"""
        
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.generate(messages, max_new_tokens=1024, temperature=0.2)
        
        parsed = self.llm.extract_json(response)
        if parsed:
            return {"status": "success", "evaluation": parsed}
        
        return {
            "status": "success",
            "evaluation": {
                "overall_score": 0.5,
                "analysis": "评估解析失败，请检查执行历史",
                "raw_response": response[:500]
            }
        }


class ChatAgent(TrueAgent):
    """
    对话管理Agent - 处理自然语言交互
    
    能力：
    - 理解用户意图
    - 维护对话上下文
    - 多轮对话管理
    - 任务委派
    """
    
    # 任务关键词，用于快速判断是否需要启动工作流
    TASK_KEYWORDS = [
        "研发", "设计", "开发", "优化", "改进", "创建", "生成",
        "配方", "实验", "测试", "模拟", "预测", "分析",
        "研究", "调查", "探索", "寻找", "查找", "搜索",
        "制作", "合成", "制备", "配置"
    ]
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_id="chat_agent",
            system_prompt="你是电化学领域的AI助手，基于知识库提供专业、准确的回答。",
            **kwargs
        )
        self._active_sessions: Dict[str, List[ConversationTurn]] = {}
    
    async def _handle_task_assignment(self, message: AgentMessage):
        """处理对话任务"""
        session_id = message.correlation_id or str(uuid.uuid4())
        user_message = message.payload.get("message", "")
        
        self._logger.info(f"ChatAgent received: {user_message[:50]}...")
        
        # 获取或创建会话
        if session_id not in self._active_sessions:
            self._active_sessions[session_id] = []
        
        conversation = self._active_sessions[session_id]
        
        # 添加用户消息
        conversation.append(ConversationTurn(
            role="user",
            content=user_message
        ))
        
        try:
            # 简单规则判断：是否包含任务关键词
            is_task = any(kw in user_message for kw in self.TASK_KEYWORDS)
            
            if is_task and len(user_message) > 10:
                # 可能是复杂任务，启动工作流
                self._logger.info(f"Task keywords detected, delegating to workflow")
                response = await self._delegate_task(user_message, session_id)
            else:
                # 简单问答，直接回答
                self._logger.info(f"Handling as chat response")
                response = await self._handle_chat_response(user_message, conversation)
            
            # 添加助手回复
            if response.get("type") == "chat":
                conversation.append(ConversationTurn(
                    role="assistant",
                    content=response.get("content", ""),
                    metadata={"type": "chat"}
                ))
            
            # 保存到共享内存
            for turn in conversation[-2:]:
                await self.memory.add_conversation_turn(session_id, turn)
            
            await self._send_result(message.correlation_id, response)
            
        except Exception as e:
            self._logger.error(f"Error in chat handling: {e}", exc_info=True)
            # 错误时返回友好提示
            await self._send_result(message.correlation_id, {
                "type": "chat",
                "content": "抱歉，处理您的请求时出现了问题。请稍后再试。"
            })
    
    async def _analyze_intent_simple(self, message: str) -> Dict:
        """简化版意图分析 - 使用规则和轻量级LLM辅助"""
        # 首先用关键词规则快速判断
        is_task = any(kw in message for kw in self.TASK_KEYWORDS)
        
        # 问候语判断
        greetings = ["你好", "您好", "hello", "hi", "嗨"]
        is_greeting = any(g in message.lower() for g in greetings)
        
        if is_greeting:
            return {"type": "chat", "subtype": "greeting"}
        
        # 问题判断（包含问号或疑问词）
        question_words = ["什么", "怎么", "为什么", "多少", "哪些", "吗", "？", "?"]
        is_question = any(q in message for q in question_words)
        
        if is_question and not is_task:
            return {"type": "chat", "subtype": "question"}
        
        if is_task:
            return {"type": "task", "goal": message}
        
        return {"type": "chat", "subtype": "general"}
    
    async def _handle_chat_response(
        self,
        message: str,
        conversation: List[ConversationTurn]
    ) -> Dict:
        """生成聊天回复 - 简化版适用于小模型"""
        
        # 搜索相关知识
        try:
            search_results = await self.rag.deep_search(message, depth=1, breadth=2)
            knowledge = ""
            if search_results.get("results"):
                knowledge = "\n".join([
                    f"[{i+1}] {r['content'][:300]}"
                    for i, r in enumerate(search_results["results"][:2])
                ])
        except Exception as e:
            self._logger.warning(f"Search failed: {e}")
            knowledge = ""
        
        # 简化prompt，适合小模型
        if knowledge:
            prompt = f"基于以下知识回答问题。\n\n知识:\n{knowledge}\n\n问题: {message}\n\n回答:"
        else:
            prompt = f"你是电化学专家。请回答: {message}"
        
        messages = [
            {"role": "system", "content": "你是电化学专家助手。简洁、专业地回答。"},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.llm.generate(messages, max_new_tokens=512, temperature=0.5)
            content = response.strip()
            
            # 清理可能的重复前缀
            if content.startswith("回答:"):
                content = content[3:].strip()
            
            return {
                "type": "chat",
                "content": content,
                "has_knowledge": bool(knowledge)
            }
        except Exception as e:
            self._logger.error(f"Generation failed: {e}")
            return {
                "type": "chat",
                "content": "抱歉，生成回答时出现问题。",
                "has_knowledge": False
            }
    
    async def _delegate_task(
        self,
        original_message: str,
        session_id: str
    ) -> Dict:
        """委派任务给其他Agent"""
        goal = original_message
        suggested_agent = "reasoning_agent"
        
        # 通知Orchestrator启动工作流
        await self.send_message(
            receiver="orchestrator",
            message_type=MessageType.SYSTEM_EVENT,
            payload={
                "event": "start_workflow",
                "goal": goal,
                "suggested_agent": suggested_agent,
                "session_id": session_id
            }
        )
        
        return {
            "type": "task_delegated",
            "message": f"我已理解您的需求：{goal}\n正在为您启动专业Agent处理...",
            "goal": goal,
            "session_id": session_id
        }
    
    async def generate_streaming_response(
        self,
        session_id: str,
        message: str
    ) -> AsyncGenerator[str, None]:
        """生成流式回复"""
        # 搜索知识
        search_results = await self.rag.deep_search(message, depth=1, breadth=2)
        knowledge = ""
        if search_results.get("results"):
            knowledge = "\n".join([
                f"- {r['content'][:200]}..."
                for r in search_results["results"][:2]
            ])
        
        prompt = f"""基于以下知识回答：
{knowledge}

用户问题: {message}

请专业、准确地回答："""
        
        messages = [
            {"role": "system", "content": "你是电化学专家助手。"},
            {"role": "user", "content": prompt}
        ]
        
        # 流式生成
        async for token in self.llm.generate(
            messages,
            max_new_tokens=1024,
            temperature=0.7,
            stream=True
        ):
            yield token


class MemoryAgent(TrueAgent):
    """
    记忆管理Agent - 管理短期和长期记忆
    
    能力：
    - 工作记忆管理
    - 重要信息提取
    - 记忆检索
    - 知识整合
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_id="memory_agent",
            system_prompt="You are the Memory Agent.",
            **kwargs
        )
    
    async def _handle_task_assignment(self, message: AgentMessage):
        """处理记忆任务"""
        action = message.payload.get("action")
        
        if action == "summarize":
            result = await self._summarize_workflow(message.payload.get("workflow_id"))
        elif action == "extract_insights":
            result = await self._extract_insights(message.payload.get("content", ""))
        else:
            result = {"status": "unknown_action"}
        
        await self._send_result(message.correlation_id, result)
    
    async def _summarize_workflow(self, workflow_id: str) -> Dict:
        """总结工作流"""
        workflow = await self.memory.get_workflow(workflow_id)
        if not workflow:
            return {"status": "error", "message": "Workflow not found"}
        
        history = workflow.get("execution_history", [])
        
        prompt = f"""总结以下工作流执行过程：

目标: {workflow.get('goal', '')}

执行步骤:
{json.dumps(history, ensure_ascii=False, default=str)[:2000]}

请提供简洁的执行摘要："""
        
        messages = [{"role": "user", "content": prompt}]
        summary = self.llm.generate(messages, max_new_tokens=512, temperature=0.3)
        
        return {"status": "success", "summary": summary}
    
    async def _extract_insights(self, content: str) -> Dict:
        """提取洞察"""
        prompt = f"""从以下内容提取关键洞察：

{content[:2000]}

输出JSON：
{{
    "key_insights": ["洞察1", "洞察2"],
    "actionable_items": ["行动1", "行动2"],
    "knowledge_gaps": ["缺失1"]
}}"""
        
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.generate(messages, max_new_tokens=512, temperature=0.3)
        
        parsed = self.llm.extract_json(response)
        return {"status": "success", "insights": parsed or {}}


# ==============================================================================
# 8. Orchestrator Agent - 中央协调者
# ==============================================================================

class OrchestratorAgent:
    """
    Orchestrator Agent - 中央协调者
    
    职责：
    1. 接收用户请求
    2. 创建和管理工作流
    3. 协调Agent间的协作
    4. 监控执行状态
    5. 处理异常和重试
    """
    
    def __init__(
        self,
        message_bus: MessageBus,
        shared_memory: SharedMemory,
        llm_service: LLMService
    ):
        self.agent_id = "orchestrator"
        self.bus = message_bus
        self.memory = shared_memory
        self.llm = llm_service
        self._logger = logging.getLogger("Orchestrator")
        
        self._workflows: Dict[str, Dict] = {}
        self._futures: Dict[str, asyncio.Future] = {}
        self.running = False
    
    async def start(self):
        """启动Orchestrator"""
        self.running = True
        self.bus.register_agent(self.agent_id)
        
        # 订阅消息
        self.bus.subscribe(MessageType.TASK_RESULT.value, self._handle_task_result)
        self.bus.subscribe(MessageType.SYSTEM_EVENT.value, self._handle_system_event)
        
        self._logger.info("Orchestrator started")
    
    async def stop(self):
        """停止Orchestrator"""
        self.running = False
        self.bus.unregister_agent(self.agent_id)
        self._logger.info("Orchestrator stopped")
    
    async def create_workflow(
        self,
        goal: str,
        mode: str = "auto",
        context: Dict = None
    ) -> str:
        """创建新工作流"""
        workflow_id = await self.memory.create_workflow(goal, context)
        
        self._workflows[workflow_id] = {
            "workflow_id": workflow_id,
            "goal": goal,
            "mode": mode,
            "status": "created",
            "current_step": None,
            "results": [],
            "created_at": datetime.now().isoformat()
        }
        
        self._logger.info(f"Created workflow {workflow_id}: {goal[:50]}...")
        return workflow_id
    
    async def start_workflow(self, workflow_id: str) -> asyncio.Future:
        """启动工作流执行"""
        if workflow_id not in self._workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self._workflows[workflow_id]
        workflow["status"] = "running"
        
        # 创建future用于等待完成
        future = asyncio.Future()
        self._futures[workflow_id] = future
        
        # 第一步：规划
        await self._dispatch_to_agent(
            workflow_id=workflow_id,
            agent_id="planning_agent",
            task="create_plan",
            payload={
                "goal": workflow["goal"],
                "context": workflow.get("context", {})
            }
        )
        
        return future
    
    async def _dispatch_to_agent(
        self,
        workflow_id: str,
        agent_id: str,
        task: str,
        payload: Dict
    ):
        """派发任务给Agent"""
        self._logger.info(f"Dispatching {task} to {agent_id} for {workflow_id}")
        
        await self.bus.send(AgentMessage(
            sender=self.agent_id,
            receiver=agent_id,
            message_type=MessageType.TASK_ASSIGN,
            payload={"task": task, **payload},
            correlation_id=workflow_id,
            requires_response=True
        ))
        
        await self.memory.update_workflow(workflow_id, {
            "current_agent": agent_id,
            "current_task": task
        })
    
    async def _handle_task_result(self, message: AgentMessage):
        """处理任务结果"""
        workflow_id = message.correlation_id
        
        if workflow_id not in self._workflows:
            return
        
        workflow = self._workflows[workflow_id]
        payload = message.payload
        
        self._logger.info(f"Received result from {message.sender} for {workflow_id}")
        
        # 记录结果
        workflow["results"].append({
            "agent": message.sender,
            "result": payload,
            "timestamp": datetime.now().isoformat()
        })
        
        # 根据发送者和状态决定下一步
        if message.sender == "planning_agent":
            await self._handle_planning_result(workflow_id, payload)
        
        elif message.sender == "reasoning_agent":
            await self._handle_reasoning_result(workflow_id, payload)
        
        elif message.sender == "chat_agent":
            await self._handle_chat_result(workflow_id, payload)
    
    async def _handle_planning_result(self, workflow_id: str, payload: Dict):
        """处理规划结果"""
        if payload.get("status") == "success":
            plan_data = payload.get("result", {})
            
            # 进入执行阶段
            await self._dispatch_to_agent(
                workflow_id=workflow_id,
                agent_id="reasoning_agent",
                task="execute",
                payload={
                    "task": self._workflows[workflow_id]["goal"],
                    "plan_id": plan_data.get("plan_id"),
                    "context": {"plan_steps": plan_data.get("steps", [])}
                }
            )
        else:
            await self._fail_workflow(workflow_id, "Planning failed")
    
    async def _handle_reasoning_result(self, workflow_id: str, payload: Dict):
        """处理执行结果"""
        result = payload.get("result", {})
        
        if payload.get("status") == "success":
            # 执行成功，进行评估
            if result.get("status") == "needs_clarification":
                # 需要用户澄清
                workflow = self._workflows[workflow_id]
                workflow["status"] = "awaiting_clarification"
                workflow["clarification_question"] = result.get("question")
                
                if workflow_id in self._futures:
                    self._futures[workflow_id].set_result({
                        "status": "needs_clarification",
                        "question": result.get("question"),
                        "workflow_id": workflow_id
                    })
            
            elif result.get("status") == "success":
                # 任务完成，进行评估
                await self._dispatch_to_agent(
                    workflow_id=workflow_id,
                    agent_id="evaluation_agent",
                    task="evaluate",
                    payload={
                        "execution_history": result.get("history", []),
                        "goal": self._workflows[workflow_id]["goal"]
                    }
                )
        else:
            await self._fail_workflow(workflow_id, payload.get("error", "Execution failed"))
    
    async def _handle_chat_result(self, workflow_id: str, payload: Dict):
        """处理聊天结果"""
        result = payload.get("result", {})
        
        if result.get("type") == "task_delegated":
            # 聊天Agent委派了任务，启动工作流
            await self.start_workflow(workflow_id)
        else:
            # 普通聊天响应
            workflow = self._workflows[workflow_id]
            workflow["status"] = "completed"
            workflow["chat_response"] = result
            
            if workflow_id in self._futures:
                self._futures[workflow_id].set_result({
                    "status": "success",
                    "response": result,
                    "workflow_id": workflow_id
                })
    
    async def _handle_system_event(self, message: AgentMessage):
        """处理系统事件"""
        payload = message.payload
        
        if payload.get("event") == "start_workflow":
            goal = payload.get("goal")
            session_id = payload.get("session_id")
            
            workflow_id = await self.create_workflow(
                goal=goal,
                context={"session_id": session_id}
            )
            await self.start_workflow(workflow_id)
    
    async def _fail_workflow(self, workflow_id: str, error: str):
        """标记工作流失败"""
        if workflow_id in self._workflows:
            self._workflows[workflow_id]["status"] = "failed"
            self._workflows[workflow_id]["error"] = error
        
        if workflow_id in self._futures:
            self._futures[workflow_id].set_exception(Exception(error))
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict]:
        """获取工作流状态"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None
        
        memory_workflow = await self.memory.get_workflow(workflow_id)
        
        return {
            **workflow,
            "memory_state": memory_workflow
        }
    
    async def provide_clarification(self, workflow_id: str, clarification: str):
        """提供用户澄清"""
        if workflow_id not in self._workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        # 重新启动执行
        await self._dispatch_to_agent(
            workflow_id=workflow_id,
            agent_id="reasoning_agent",
            task="execute",
            payload={
                "task": self._workflows[workflow_id]["goal"],
                "context": {"clarification": clarification}
            }
        )


# ==============================================================================
# 9. API 层
# ==============================================================================

# 全局实例
message_bus = MessageBus()
shared_memory = SharedMemory()
llm_service: Optional[LLMService] = None
rag_service: Optional[RAGService] = None
orchestrator: Optional[OrchestratorAgent] = None
agents: Dict[str, TrueAgent] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global llm_service, rag_service, orchestrator, agents
    
    logger.info("Initializing True Multi-Agent System...")
    
    # 初始化服务
    llm_service = LLMService(LLM_MODEL_PATH)
    rag_service = RAGService(llm_service)
    
    # 初始化Orchestrator
    orchestrator = OrchestratorAgent(message_bus, shared_memory, llm_service)
    await orchestrator.start()
    
    # 初始化专业Agent
    common_kwargs = {
        "message_bus": message_bus,
        "shared_memory": shared_memory,
        "llm_service": llm_service,
        "rag_service": rag_service
    }
    
    agents = {
        "planning_agent": PlanningAgent(**common_kwargs),
        "reasoning_agent": ReasoningAgent(**common_kwargs),
        "tool_executor": ToolExecutorAgent(**common_kwargs),
        "evaluation_agent": EvaluationAgent(**common_kwargs),
        "chat_agent": ChatAgent(**common_kwargs),
        "memory_agent": MemoryAgent(**common_kwargs)
    }
    
    for agent in agents.values():
        await agent.start()
    
    logger.info("All agents started and ready")
    yield
    
    # 清理
    logger.info("Shutting down...")
    for agent in agents.values():
        await agent.stop()
    await orchestrator.stop()


app = FastAPI(
    title="True Multi-Agent System v7",
    description="真正的多智能体系统 - LLM驱动、自主决策、自我评估",
    version="7.0.0",
    lifespan=lifespan
)


# 请求/响应模型
class ChatRequest(BaseModel):
    message: str = Field(..., description="用户消息")
    session_id: Optional[str] = Field(None, description="会话ID")
    stream: bool = Field(False, description="是否流式返回")


class TaskRequest(BaseModel):
    goal: str = Field(..., description="任务目标")
    context: Optional[Dict] = Field(None, description="额外上下文")
    mode: str = Field("auto", description="执行模式")


class WorkflowResponse(BaseModel):
    workflow_id: str
    status: str
    message: str


class ClarificationRequest(BaseModel):
    clarification: str = Field(..., description="澄清内容")


# API端点
@app.post("/chat", response_model=Dict)
async def chat_endpoint(request: ChatRequest):
    """
    自然语言对话端点
    
    - 支持闲聊问答
    - 支持任务委派
    - 支持多轮对话
    """
    session_id = request.session_id or str(uuid.uuid4())
    
    # 创建future等待响应
    future = asyncio.Future()
    
    # 订阅结果
    async def callback(message: AgentMessage):
        if message.correlation_id == session_id and message.message_type == MessageType.TASK_RESULT:
            if not future.done():
                future.set_result(message.payload)
    
    message_bus.subscribe(MessageType.TASK_RESULT.value, callback)
    
    # 发送给ChatAgent
    await message_bus.send(AgentMessage(
        sender="api",
        receiver="chat_agent",
        message_type=MessageType.TASK_ASSIGN,
        payload={"task": "handle_chat", "message": request.message},
        correlation_id=session_id
    ))
    
    try:
        result = await asyncio.wait_for(future, timeout=60)
        return {
            "session_id": session_id,
            **result
        }
    except asyncio.TimeoutError:
        return {"session_id": session_id, "status": "timeout"}


@app.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """流式对话端点"""
    session_id = request.session_id or str(uuid.uuid4())
    
    async def event_stream():
        chat_agent = agents.get("chat_agent")
        if chat_agent:
            async for token in chat_agent.generate_streaming_response(
                session_id,
                request.message
            ):
                yield f"data: {json.dumps({'token': token})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )


@app.post("/task", response_model=WorkflowResponse)
async def task_endpoint(request: TaskRequest):
    """
    任务执行端点
    
    - LLM动态规划
    - 自主工具选择
    - 自我评估
    """
    workflow_id = await orchestrator.create_workflow(
        goal=request.goal,
        context=request.context,
        mode=request.mode
    )
    
    # 后台启动执行
    asyncio.create_task(orchestrator.start_workflow(workflow_id))
    
    return WorkflowResponse(
        workflow_id=workflow_id,
        status="started",
        message="Task workflow initiated"
    )


@app.get("/workflow/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """查询工作流状态"""
    status = await orchestrator.get_workflow_status(workflow_id)
    if not status:
        raise HTTPException(404, "Workflow not found")
    return status


@app.post("/workflow/{workflow_id}/clarify")
async def provide_clarification(workflow_id: str, request: ClarificationRequest):
    """提供澄清信息"""
    try:
        await orchestrator.provide_clarification(workflow_id, request.clarification)
        return {"status": "clarification_received"}
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/research/deep")
async def deep_research_endpoint(request: Dict):
    """深度研究端点（直接RAG）"""
    query = request.get("query", "")
    depth = request.get("depth", 2)
    breadth = request.get("breadth", 3)
    
    results = await rag_service.deep_search(query, depth, breadth)
    
    return {
        "status": "success",
        "query": query,
        "results_count": len(results.get("results", [])),
        "results": results.get("results", [])[:5]
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "agents": list(agents.keys()),
        "llm_loaded": llm_service is not None
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
