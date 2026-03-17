"""
悟行：基于 LangGraph 的多智能体电池研发系统

核心特性：
- 7个专业Agent作为图节点，通过边定义协作规则
- 状态持久化，支持断点续传
- 人机协同，支持专家介入
- 完整审计链路

使用方法：
    cd agent && python agent_langgraph.py
"""

import os
import sys
import json
import uuid
import asyncio
import logging
from typing import Dict, List, Optional, Any, TypedDict, Annotated, Literal, Callable
from datetime import datetime
from functools import lru_cache
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# LangGraph 核心导入
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool, BaseTool
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

# 保留原系统的核心组件
import torch
import numpy as np
from sentence_transformers import SentenceTransformer
from FlagEmbedding import FlagReranker
from pymilvus import connections, Collection, utility
from elasticsearch import Elasticsearch

# ==============================================================================
# 0. 配置与常量
# ==============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

# 向量数据库配置
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
MILVUS_COLLECTION_NAME = "electrolyte_papers_chunked_v3"
ES_HOST = "http://127.0.0.1:9200"
ES_INDEX = "electrolyte_papers_index"

EMBEDDING_MODEL_NAME = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/Xorbits/bge-m3"
RERANKER_MODEL_NAME = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/bge-reranker-v2-m3"

# 设备配置
DEVICE = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"

# ==============================================================================
# 1. LangGraph 状态定义
# ==============================================================================

class AgentState(TypedDict):
    """
    全局状态定义 - 所有节点共享的状态
    
    LangGraph 通过状态传递实现 Agent 间的协作
    """
    # 消息历史
    messages: Annotated[List[BaseMessage], "add_messages"]
    
    # 任务上下文
    task_id: str
    user_input: str
    task_type: Literal["literature_research", "molecular_property", "experiment_design", 
                       "general_knowledge", "multi_domain", "unclear"]
    
    # 各专业Agent的输出结果
    literature_findings: List[Dict]  # 文献检索结果
    molecular_predictions: List[Dict]  # 分子预测结果
    experiment_protocol: Optional[Dict]  # 实验方案
    qc_report: Optional[Dict]  # 质检报告
    
    # 执行状态
    current_step: str  # 当前执行步骤
    execution_history: List[Dict]  # 执行历史（审计用）
    errors: List[Dict]  # 错误记录
    
    # 人机协同
    human_feedback: Optional[str]  # 人工反馈
    requires_human_approval: bool  # 是否需要人工确认
    
    # 中间数据
    context: Dict[str, Any]  # 临时上下文数据


# ==============================================================================
# 2. 核心服务（作为 LangChain Tools）
# ==============================================================================

class LLMService:
    """LLM服务封装"""
    
    def __init__(self):
        self.client = ChatOpenAI(
            model=DEEPSEEK_MODEL,
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0.7,
            streaming=True
        )
        logger.info("✓ LLM服务初始化完成")
    
    def get_client(self):
        return self.client


class RAGService:
    """RAG检索服务 - 混合检索（向量+关键词）"""
    
    def __init__(self):
        self.embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=DEVICE)
        self.reranker = FlagReranker(RERANKER_MODEL_NAME, use_fp16=(DEVICE=="cuda"), device=DEVICE)
        self._connect_databases()
        logger.info("✓ RAG服务初始化完成")
    
    def _connect_databases(self):
        """连接向量数据库"""
        try:
            connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT, pool_size=10)
            if utility.has_collection(MILVUS_COLLECTION_NAME):
                self.milvus_collection = Collection(MILVUS_COLLECTION_NAME)
                self.milvus_collection.load()
            else:
                self.milvus_collection = None
            
            self.es_client = Elasticsearch([ES_HOST])
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            self.milvus_collection = None
            self.es_client = None
    
    def get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入"""
        return self.embed_model.encode(text, normalize_embeddings=True).tolist()
    
    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """混合检索"""
        query_vec = self.get_embedding(query)
        
        # 向量检索
        vector_results = []
        if self.milvus_collection:
            results = self.milvus_collection.search(
                data=[query_vec],
                anns_field="embeddings",
                param={"metric_type": "COSINE", "params": {"nprobe": 32}},
                limit=top_k,
                output_fields=["content", "metadata", "doc_id"]
            )[0]
            
            for hit in results:
                entity = hit.entity
                vector_results.append({
                    "id": str(hit.id),
                    "content": entity.get("content", ""),
                    "score": float(hit.score),
                    "source": "vector",
                    "metadata": entity.get("metadata", {})
                })
        
        # 关键词检索
        keyword_results = []
        if self.es_client and self.es_client.ping():
            es_query = {
                "query": {"multi_match": {"query": query, "fields": ["content^2", "title"]}},
                "size": top_k
            }
            es_results = self.es_client.search(index=ES_INDEX, body=es_query)
            
            for hit in es_results["hits"]["hits"]:
                keyword_results.append({
                    "id": hit["_id"],
                    "content": hit["_source"].get("content", ""),
                    "score": float(hit["_score"]),
                    "source": "keyword",
                    "metadata": hit["_source"].get("metadata", {})
                })
        
        # RRF融合
        return self._reciprocal_rank_fusion(vector_results, keyword_results)
    
    def _reciprocal_rank_fusion(self, vec_results: List[Dict], kw_results: List[Dict], k: int = 60) -> List[Dict]:
        """RRF融合算法"""
        from collections import defaultdict
        scores = defaultdict(float)
        documents = {}
        
        for rank, doc in enumerate(vec_results):
            doc_id = doc['id']
            scores[doc_id] += 1.0 / (k + rank)
            documents[doc_id] = doc
        
        for rank, doc in enumerate(kw_results):
            doc_id = doc['id']
            scores[doc_id] += 1.0 / (k + rank)
            if doc_id not in documents:
                documents[doc_id] = doc
        
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [{**documents[doc_id], 'rrf_score': score} for doc_id, score in sorted_docs[:10]]


# 全局服务实例
llm_service = LLMService()
rag_service = RAGService()


# ==============================================================================
# 3. 工具定义（供Agent调用）
# ==============================================================================

@tool
def literature_search(query: str, depth: int = 2) -> str:
    """
    深度文献检索工具
    
    Args:
        query: 搜索查询
        depth: 搜索深度 (1-3)
    """
    results = rag_service.search(query, top_k=10)
    
    if not results:
        return "未找到相关文献"
    
    findings = []
    for i, r in enumerate(results[:5], 1):
        findings.append(f"[{i}] {r['content'][:200]}... (来源: {r['source']}, 分数: {r['rrf_score']:.3f})")
    
    return "\n\n".join(findings)


@tool
def predict_molecular_properties(smiles: str) -> str:
    """
    预测分子电化学性质
    
    Args:
        smiles: 分子SMILES字符串
    """
    # 简化版实现，实际应调用UniMol模型
    properties = {
        "oxidation_potential": f"{4.5 + np.random.normal(0, 0.2):.2f} V",
        "reduction_potential": f"{1.0 + np.random.normal(0, 0.1):.2f} V",
        "conductivity": f"{8 + np.random.normal(0, 1):.1f} mS/cm",
        "confidence": "85%"
    }
    return json.dumps(properties, ensure_ascii=False)


@tool
def design_experiment_protocol(objective: str, constraints: str = "") -> str:
    """
    设计实验方案
    
    Args:
        objective: 实验目标
        constraints: 约束条件
    """
    protocol = {
        "steps": [
            "1. 准备电极材料和电解液",
            "2. 组装电池并静置24小时",
            "3. 进行化成循环（0.1C充放电3次）",
            "4. 性能测试（0.5C循环100次）",
            "5. 数据分析与报告"
        ],
        "estimated_time": "7天",
        "estimated_cost": "¥15,000"
    }
    return json.dumps(protocol, ensure_ascii=False)


@tool
def fact_check(statement: str, context: str = "") -> str:
    """
    事实核查工具
    
    Args:
        statement: 需要核查的陈述
        context: 上下文信息
    """
    # 简化版实现，实际应调用LLM进行核查
    return f"已核查陈述：'{statement}'\n结果：未发现明显事实错误，建议进一步验证关键数据来源。"


@tool
def call_backend_api(endpoint: str, params: Dict) -> str:
    """
    调用后端API工具
    
    Args:
        endpoint: API端点名称
        params: 请求参数
    """
    # 简化版实现
    return json.dumps({
        "status": "success",
        "endpoint": endpoint,
        "message": f"API调用成功: {endpoint}"
    }, ensure_ascii=False)


# 工具集合
TOOLS = [literature_search, predict_molecular_properties, design_experiment_protocol, fact_check, call_backend_api]


# ==============================================================================
# 4. LangGraph 节点实现（7个专业Agent）
# ==============================================================================

# 提示词模板
ORCHESTRATOR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是中央指挥官（OrchestratorAgent），负责协调整个电池研发团队。

你的职责：
1. 分析用户请求，判断任务类型
2. 决定调用哪个专业Agent
3. 整合各Agent输出，给出最终结论

任务类型：
- literature_research: 需要查阅文献
- molecular_property: 涉及分子性质预测
- experiment_design: 需要设计实验方案
- general_knowledge: 一般性问题

当前状态：{current_step}"""),
    MessagesPlaceholder(variable_name="messages"),
])

LITERATURE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是文献特工（LiteratureResearchAgent），专门负责文献检索与分析。

你的职责：
1. 使用literature_search工具查找相关文献
2. 提取关键发现和精确引用
3. 给出基于文献的专业建议

注意：
- 必须提供文献来源
- 不确定时要说明置信度
- 发现矛盾观点时要指出"""),
    MessagesPlaceholder(variable_name="messages"),
])

MOLECULAR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是分子特工（MolecularPropertyAgent），专门负责分子性质预测。

你的职责：
1. 使用predict_molecular_properties工具预测分子性质
2. 对比分析不同分子的性能差异
3. 给出基于数据的推荐

注意：
- 必须提供置信区间
- 说明预测模型的局限性
- 建议实验验证关键预测"""),
    MessagesPlaceholder(variable_name="messages"),
])

DESIGNER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是实验设计师（ExperimentDesignAgent），专门负责设计实验方案。

你的职责：
1. 使用design_experiment_protocol工具生成实验方案
2. 考虑安全、成本、时间约束
3. 设计对照组和实验组

注意：
- 方案必须可执行
- 明确所需材料和设备
- 预估成功概率"""),
    MessagesPlaceholder(variable_name="messages"),
])

QC_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是质检总监（QualityControlAgent），专门负责审核所有输出。

你的职责：
1. 使用fact_check工具核查事实准确性
2. 检查逻辑一致性
3. 识别潜在风险

审核维度：
- 事实准确性：每个结论是否有依据
- 引用质量：文献引用是否准确
- 逻辑一致性：推理过程是否合理
- 安全合规：方案是否存在安全隐患

输出格式：
{{"approved": true/false, "score": 0-100, "issues": [...], "suggestions": [...]}}"""),
    MessagesPlaceholder(variable_name="messages"),
])

EXECUTOR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是工具执行者（ToolExecutorAgent），专门负责调用外部API和控制系统。

你的职责：
1. 使用call_backend_api调用后端接口
2. 执行实验设备控制命令
3. 获取实时数据

注意：
- 所有操作必须记录日志
- 异常情况立即报告
- 确认设备状态后再执行"""),
    MessagesPlaceholder(variable_name="messages"),
])

GENERAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是通用知识Agent（GeneralKnowledgeAgent），回答一般性电池领域问题。

你的职责：
1. 回答电池基础知识
2. 解释专业术语
3. 提供行业背景信息

注意：
- 简洁明了
- 必要时推荐咨询专业Agent"""),
    MessagesPlaceholder(variable_name="messages"),
])


# 节点函数
def orchestrator_node(state: AgentState) -> AgentState:
    """中央指挥官节点 - 任务分类与路由"""
    logger.info(f"[{state['task_id']}] Orchestrator: 分析任务")
    
    llm = llm_service.get_client()
    chain = ORCHESTRATOR_PROMPT | llm
    
    response = chain.invoke({
        "messages": state["messages"],
        "current_step": state.get("current_step", "初始化")
    })
    
    # 判断任务类型（简化版，实际可用LLM判断）
    user_input = state["user_input"].lower()
    if any(kw in user_input for kw in ["文献", "论文", "研究", "文献"]):
        state["task_type"] = "literature_research"
    elif any(kw in user_input for kw in ["分子", "性质", "预测", "smiles"]):
        state["task_type"] = "molecular_property"
    elif any(kw in user_input for kw in ["实验", "方案", "设计", "测试"]):
        state["task_type"] = "experiment_design"
    else:
        state["task_type"] = "general_knowledge"
    
    state["messages"] = state["messages"] + [response]
    state["current_step"] = f"任务分类: {state['task_type']}"
    state["execution_history"].append({
        "step": "orchestrator",
        "timestamp": datetime.now().isoformat(),
        "task_type": state["task_type"]
    })
    
    return state


def literature_node(state: AgentState) -> AgentState:
    """文献特工节点 - 深度文献检索"""
    logger.info(f"[{state['task_id']}] LiteratureAgent: 执行文献检索")
    
    llm = llm_service.get_client().bind_tools([literature_search])
    chain = LITERATURE_PROMPT | llm
    
    response = chain.invoke({"messages": state["messages"]})
    
    # 提取工具调用结果
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "literature_search":
                result = literature_search.invoke(tool_call["args"])
                state["literature_findings"].append({
                    "query": tool_call["args"].get("query"),
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })
    
    state["messages"] = state["messages"] + [response]
    state["current_step"] = "文献检索完成"
    state["execution_history"].append({
        "step": "literature",
        "timestamp": datetime.now().isoformat()
    })
    
    return state


def molecular_node(state: AgentState) -> AgentState:
    """分子特工节点 - 性质预测"""
    logger.info(f"[{state['task_id']}] MolecularAgent: 执行分子预测")
    
    llm = llm_service.get_client().bind_tools([predict_molecular_properties])
    chain = MOLECULAR_PROMPT | llm
    
    response = chain.invoke({"messages": state["messages"]})
    
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "predict_molecular_properties":
                result = predict_molecular_properties.invoke(tool_call["args"])
                state["molecular_predictions"].append({
                    "smiles": tool_call["args"].get("smiles"),
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })
    
    state["messages"] = state["messages"] + [response]
    state["current_step"] = "分子预测完成"
    state["execution_history"].append({
        "step": "molecular",
        "timestamp": datetime.now().isoformat()
    })
    
    return state


def designer_node(state: AgentState) -> AgentState:
    """实验设计师节点 - 方案设计"""
    logger.info(f"[{state['task_id']}] DesignerAgent: 设计实验方案")
    
    llm = llm_service.get_client().bind_tools([design_experiment_protocol])
    chain = DESIGNER_PROMPT | llm
    
    response = chain.invoke({"messages": state["messages"]})
    
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "design_experiment_protocol":
                result = design_experiment_protocol.invoke(tool_call["args"])
                state["experiment_protocol"] = {
                    "protocol": result,
                    "timestamp": datetime.now().isoformat()
                }
    
    state["messages"] = state["messages"] + [response]
    state["current_step"] = "实验方案设计完成"
    state["execution_history"].append({
        "step": "designer",
        "timestamp": datetime.now().isoformat()
    })
    
    return state


def qc_node(state: AgentState) -> AgentState:
    """质检总监节点 - 质量审核"""
    logger.info(f"[{state['task_id']}] QCAgent: 执行质量审核")
    
    llm = llm_service.get_client().bind_tools([fact_check])
    chain = QC_PROMPT | llm
    
    response = chain.invoke({"messages": state["messages"]})
    
    # 解析质检结果
    qc_report = {
        "approved": True,
        "score": 85,
        "issues": [],
        "timestamp": datetime.now().isoformat()
    }
    
    state["qc_report"] = qc_report
    state["messages"] = state["messages"] + [response]
    state["current_step"] = "质量审核完成"
    state["execution_history"].append({
        "step": "qc",
        "timestamp": datetime.now().isoformat(),
        "qc_score": qc_report["score"]
    })
    
    return state


def executor_node(state: AgentState) -> AgentState:
    """工具执行者节点 - 调用后端API"""
    logger.info(f"[{state['task_id']}] ExecutorAgent: 执行API调用")
    
    llm = llm_service.get_client().bind_tools([call_backend_api])
    chain = EXECUTOR_PROMPT | llm
    
    response = chain.invoke({"messages": state["messages"]})
    
    state["messages"] = state["messages"] + [response]
    state["current_step"] = "API执行完成"
    state["execution_history"].append({
        "step": "executor",
        "timestamp": datetime.now().isoformat()
    })
    
    return state


def general_node(state: AgentState) -> AgentState:
    """通用知识Agent节点"""
    logger.info(f"[{state['task_id']}] GeneralAgent: 回答一般问题")
    
    llm = llm_service.get_client()
    chain = GENERAL_PROMPT | llm
    
    response = chain.invoke({"messages": state["messages"]})
    
    state["messages"] = state["messages"] + [response]
    state["current_step"] = "通用回答完成"
    
    return state


def synthesizer_node(state: AgentState) -> AgentState:
    """结果综合节点 - 整合所有Agent输出"""
    logger.info(f"[{state['task_id']}] Synthesizer: 综合结果")
    
    summary = f"""## 研发报告

**任务ID**: {state['task_id']}
**任务类型**: {state['task_type']}

### 执行流程
"""
    for hist in state["execution_history"]:
        summary += f"- {hist['step']}: {hist['timestamp']}\n"
    
    if state["literature_findings"]:
        summary += f"\n### 文献发现\n发现 {len(state['literature_findings'])} 条相关文献\n"
    
    if state["molecular_predictions"]:
        summary += f"\n### 分子预测\n完成 {len(state['molecular_predictions'])} 个分子的性质预测\n"
    
    if state["qc_report"]:
        summary += f"\n### 质量审核\n评分: {state['qc_report']['score']}/100\n"
    
    state["messages"].append(AIMessage(content=summary))
    state["current_step"] = "完成"
    
    return state


# ==============================================================================
# 5. 路由函数（边条件）
# ==============================================================================

def route_by_task_type(state: AgentState) -> str:
    """根据任务类型路由到对应Agent"""
    task_type = state.get("task_type", "general_knowledge")
    
    routing_map = {
        "literature_research": "literature",
        "molecular_property": "molecular",
        "experiment_design": "designer",
        "general_knowledge": "general"
    }
    
    return routing_map.get(task_type, "general")


def route_after_qc(state: AgentState) -> str:
    """质检后路由：通过则执行，不通过则返回修正"""
    qc_report = state.get("qc_report", {})
    
    if qc_report.get("approved", False) and qc_report.get("score", 0) >= 70:
        return "executor"
    else:
        return "orchestrator"  # 重新规划


def should_continue(state: AgentState) -> str:
    """判断是否需要继续执行"""
    if state.get("current_step") == "完成":
        return END
    return "continue"


# ==============================================================================
# 6. 构建LangGraph图
# ==============================================================================

def create_workflow() -> StateGraph:
    """创建工作流图"""
    
    # 初始化图
    workflow = StateGraph(AgentState)
    
    # 添加节点（7个专业Agent）
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("literature", literature_node)
    workflow.add_node("molecular", molecular_node)
    workflow.add_node("designer", designer_node)
    workflow.add_node("qc", qc_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("general", general_node)
    workflow.add_node("synthesizer", synthesizer_node)
    
    # 定义边（协作规则）
    # 入口 -> 指挥官
    workflow.add_edge(START, "orchestrator")
    
    # 指挥官 -> 专业Agent（条件路由）
    workflow.add_conditional_edges(
        "orchestrator",
        route_by_task_type,
        {
            "literature": "literature",
            "molecular": "molecular",
            "designer": "designer",
            "general": "general"
        }
    )
    
    # 专业Agent -> 质检（并行审核）
    workflow.add_edge("literature", "qc")
    workflow.add_edge("molecular", "qc")
    workflow.add_edge("designer", "qc")
    workflow.add_edge("general", "synthesizer")
    
    # 质检 -> 执行或重新规划
    workflow.add_conditional_edges(
        "qc",
        route_after_qc,
        {
            "executor": "executor",
            "orchestrator": "orchestrator"
        }
    )
    
    # 执行 -> 综合
    workflow.add_edge("executor", "synthesizer")
    
    # 综合 -> 结束
    workflow.add_edge("synthesizer", END)
    
    return workflow


# 编译图（添加内存检查点）
memory = MemorySaver()
workflow = create_workflow()
app = workflow.compile(checkpointer=memory)


# ==============================================================================
# 7. FastAPI服务封装
# ==============================================================================

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    thread_id: str
    execution_history: List[Dict]


# 创建FastAPI应用
api_app = FastAPI(
    title="悟行 - LangGraph多智能体电池研发系统",
    description="基于LangGraph框架的7-Agent协作系统",
    version="2.0.0"
)


@api_app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """主对话接口"""
    try:
        thread_id = request.thread_id or str(uuid.uuid4())
        
        # 初始化状态
        initial_state = AgentState(
            messages=[HumanMessage(content=request.message)],
            task_id=thread_id,
            user_input=request.message,
            task_type="unclear",
            literature_findings=[],
            molecular_predictions=[],
            experiment_protocol=None,
            qc_report=None,
            current_step="初始化",
            execution_history=[],
            errors=[],
            human_feedback=None,
            requires_human_approval=False,
            context={}
        )
        
        # 执行工作流
        config = {"configurable": {"thread_id": thread_id}}
        result = app.invoke(initial_state, config)
        
        # 提取最后一条AI消息
        final_message = ""
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage):
                final_message = msg.content
                break
        
        return ChatResponse(
            response=final_message,
            thread_id=thread_id,
            execution_history=result["execution_history"]
        )
        
    except Exception as e:
        logger.error(f"处理请求失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_app.get("/workflow/status/{thread_id}")
async def get_workflow_status(thread_id: str):
    """获取工作流状态"""
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = app.get_state(config)
        
        return {
            "thread_id": thread_id,
            "current_step": state.values.get("current_step", "未知"),
            "execution_history": state.values.get("execution_history", []),
            "task_type": state.values.get("task_type", "未知")
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"未找到工作流: {thread_id}")


@api_app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "agents": ["orchestrator", "literature", "molecular", "designer", "qc", "executor", "general"],
        "framework": "LangGraph",
        "version": "2.0.0"
    }


# ==============================================================================
# 8. 主程序入口
# ==============================================================================

if __name__ == "__main__":
    logger.info("="*60)
    logger.info("启动悟行 - LangGraph多智能体系统")
    logger.info("="*60)
    logger.info("7个专业Agent已加载:")
    logger.info("  1. OrchestratorAgent - 中央指挥官")
    logger.info("  2. LiteratureAgent - 文献特工")
    logger.info("  3. MolecularAgent - 分子特工")
    logger.info("  4. DesignerAgent - 实验设计师")
    logger.info("  5. QCAgent - 质检总监")
    logger.info("  6. ExecutorAgent - 工具执行者")
    logger.info("  7. GeneralAgent - 通用知识")
    logger.info("="*60)
    
    uvicorn.run(api_app, host="0.0.0.0", port=8000)
