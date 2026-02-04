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
from typing import Dict, List, Optional, Any, Tuple, Set, Callable, Union
from datetime import datetime
from collections import defaultdict
import numpy as np
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from transformers import AutoModelForCausalLM, AutoTokenizer
from sentence_transformers import SentenceTransformer 
from FlagEmbedding import FlagReranker 
from pymilvus import connections, Collection, utility
from elasticsearch import Elasticsearch


# v6，新增多智能体架构，就是把之前的function外面再套一层agent，就是多智能体。数据库 v3 我也做了
# 能跑chat、run、deep了。
# deep已经过严谨测试。
# multi可能要等到具体函数集成进去再测试

# ==============================================================================
# 0. 多智能体基础设施（新增）
# ==============================================================================

class MessageType(Enum):
    TASK_ASSIGN = "task_assign"
    RESULT_REPORT = "result_report"
    STATE_UPDATE = "state_update"
    ERROR_NOTIFY = "error_notify"
    SYSTEM_CONTROL = "system_control"
    WORKFLOW_EVENT = "workflow_event"

@dataclass
class AgentMessage:
    sender: str
    receiver: Optional[str]  # None表示广播
    message_type: MessageType
    payload: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    requires_response: bool = False

class MessageBus:
    """异步消息总线 - Agent间松耦合通信"""
    def __init__(self):
        self._queues: Dict[str, asyncio.Queue] = {}
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    def register_agent(self, agent_id: str):
        if agent_id not in self._queues:
            self._queues[agent_id] = asyncio.Queue(maxsize=1000)
            logging.info(f"[MessageBus] Registered: {agent_id}")
    
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

class SecureStateManager:
    """带访问控制的状态管理器"""
    def __init__(self):
        self._state: Dict[str, Any] = {}
        self._access_policies: Dict[str, Set[str]] = {}
        self._audit_log: List[Dict] = []
        self._lock = asyncio.Lock()
        self._contexts: Dict[str, Dict] = {}
    
    async def create_workflow(self, requirement: str, target_ce: float, max_iter: int) -> str:
        corr_id = str(uuid.uuid4())
        async with self._lock:
            self._contexts[corr_id] = {
                "requirement": requirement,
                "target_ce": target_ce,
                "max_iterations": max_iter,
                "current_iteration": 0,
                "state": "idle",
                "created_at": datetime.now().isoformat()
            }
        return corr_id
    
    async def get_context(self, corr_id: str) -> Optional[Dict]:
        return self._contexts.get(corr_id)
    
    async def update_context(self, corr_id: str, key: str, value: Any):
        if corr_id in self._contexts:
            self._contexts[corr_id][key] = value
    
    async def set_data(self, key: str, value: Any, allowed_agents: List[str], corr_id: Optional[str] = None):
        async with self._lock:
            full_key = f"{corr_id}:{key}" if corr_id else key
            self._state[full_key] = {
                "value": value,
                "allowed_agents": set(allowed_agents)
            }
            self._audit_log.append({
                "action": "SET", "key": full_key, "time": datetime.now().isoformat()
            })
    
    async def get_data(self, key: str, requester: str, corr_id: Optional[str] = None) -> Any:
        async with self._lock:
            full_key = f"{corr_id}:{key}" if corr_id else key
            if full_key not in self._state:
                raise KeyError(f"Key {key} not found")
            entry = self._state[full_key]
            if requester not in entry["allowed_agents"] and "*" not in entry["allowed_agents"]:
                raise PermissionError(f"Access denied for {requester}")
            return entry["value"]
    
    def get_audit_log(self, limit: int = 50) -> List[Dict]:
        return self._audit_log[-limit:]

# ==============================================================================
# 1. 配置与数据结构（保留原有）
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
class ExplorationQuery:
    query: str
    strategy: str
    target_concept: Optional[str] = None
    parent_finding_idx: Optional[int] = None

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
# 2. RAG服务与Deep Research引擎（保留原有完整实现）
# ==============================================================================

class AdvancedRAGService:
    """RAG核心服务 - 所有Agent共享"""
    
    def __init__(self):
        logger.info(f"Initializing RAG on {DEVICE}")
        self.embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=DEVICE)
        self.reranker_model = FlagReranker(RERANKER_MODEL_NAME, use_fp16=(DEVICE=="cuda"), device=DEVICE)
        
        self.tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_PATH, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            LLM_MODEL_PATH, torch_dtype=dtype, device_map="auto", trust_remote_code=True
        )
        
        self._connect_milvus()
        self._connect_es()
        
        # 初始化深度研究组件
        self.deep_research_engine = DeepResearchEngine(self)
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
    
    def analyze_research_requirement(self, query: str) -> StructuredRequirement:
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
        response = self._generate_response(messages, max_new_tokens=512, temperature=0.2)
        
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return StructuredRequirement(
                    target_application=parsed.get("target_application", "general"),
                    key_constraints=parsed.get("key_constraints", {}),
                    desired_properties=parsed.get("desired_properties", {}),
                    priority_weight=parsed.get("priority_weight", 0.5)
                )
        except Exception as e:
            logger.error(f"Parse error: {e}")
        
        return StructuredRequirement("general", {}, {}, 0.5)
    
    def _generate_response(self, messages: List[Dict], max_new_tokens: int = 512, temperature: float = 0.7) -> str:
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs, max_new_tokens=max_new_tokens, temperature=temperature,
                do_sample=True, pad_token_id=self.tokenizer.eos_token_id
            )
        return self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
    
    def retrieve_papers(self, query: str, requirement: StructuredRequirement) -> List[Dict]:
        query_vec = self.get_embedding(query)
        results = []
        
        if self.milvus_collection:
            try:
                hits = self.milvus_collection.search(
                    data=[query_vec], anns_field=MILVUS_VECTOR_FIELD,
                    param={"metric_type": "COSINE", "params": {"nprobe": 20}},
                    limit=SEARCH_TOP_K, output_fields=[MILVUS_TEXT_FIELD, "metadata"]
                )[0]
                
                for hit in hits:
                    meta = hit.entity.get("metadata", {}) or {}
                    results.append({
                        "id": str(hit.id), "content": hit.entity.get(MILVUS_TEXT_FIELD, ""),
                        "score": float(hit.score), "metadata": meta, "source": "vector"
                    })
            except Exception as e:
                logger.error(f"Milvus search error: {e}")
        
        if self.es_client:
            try:
                es_body = {
                    "size": SEARCH_TOP_K,
                    "query": {"multi_match": {"query": query, "fields": ["content", "metadata.title^2"], "type": "best_fields"}}
                }
                es_resp = self.es_client.search(index=ES_INDEX, body=es_body)
                for hit in es_resp["hits"]["hits"]:
                    source = hit["_source"]
                    results.append({
                        "id": hit["_id"], "content": source.get("content", ""),
                        "score": hit["_score"], "metadata": source.get("metadata", {}), "source": "keyword"
                    })
            except Exception as e:
                logger.warning(f"ES error: {e}")
        
        return self._rerank_results(query, results)
    
    def _rerank_results(self, query: str, candidates: List[Dict]) -> List[Dict]:
        if len(candidates) <= RERANK_TOP_K:
            return candidates
        pairs = [[query, doc["content"]] for doc in candidates]
        try:
            scores = self.reranker_model.compute_score(pairs, normalize=True)
            for i, score in enumerate(scores):
                candidates[i]["rerank_score"] = score
            candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
            return candidates[:RERANK_TOP_K]
        except Exception as e:
            logger.error(f"Rerank error: {e}")
            return candidates[:RERANK_TOP_K]

class CitationManager:
    """保留原有实现"""
    def __init__(self):
        self.citation_db: Dict[int, Dict] = {}
    
    def format_findings_with_citations(self, findings: List[ResearchFinding], format_type: str = "markdown") -> Dict[str, Any]:
        formatted_sections = []
        citation_map = {}
        
        for idx, finding in enumerate(findings, 1):
            citation_marks = []
            for loc_idx, loc in enumerate(finding.source_locations):
                cite_id = f"{idx}.{loc_idx+1}"
                citation_marks.append(f"[{cite_id}]")
                citation_map[cite_id] = {
                    "doc_name": loc.doc_name, "page": loc.page,
                    "char_range": [loc.char_start, loc.char_end],
                    "section": loc.section_title
                }
            
            if format_type == "markdown":
                section = (
                    f"### {idx}. {finding.content[:100]}...\n\n{finding.content}\n\n"
                    f"**来源**: {', '.join(citation_marks)} | "
                    f"**置信度**: {finding.confidence:.2f}\n"
                )
            else:
                section = {
                    "index": idx, "content": finding.content,
                    "citations": citation_marks,
                    "metadata": {"confidence": finding.confidence, "path": finding.query_path}
                }
            formatted_sections.append(section)
        
        return {
            "content": "\n\n---\n\n".join(formatted_sections) if format_type == "markdown" else formatted_sections,
            "citations": citation_map,
            "stats": {
                "total_findings": len(findings),
                "avg_confidence": np.mean([f.confidence for f in findings]) if findings else 0,
                "max_depth": max([f.exploration_depth for f in findings]) if findings else 0
            }
        }

class DeepResearchEngine:
    """保留原有完整实现"""
    def __init__(self, rag_service: AdvancedRAGService):
        self.rag = rag_service
        self.config = DeepResearchConfig()
    
    async def deep_research(self, query: str, depth: int = None, breadth: int = None, context: str = "") -> Tuple[List[ResearchFinding], Dict]:
        depth = depth or self.config.MAX_DEPTH
        breadth = breadth or self.config.INITIAL_BREADTH
        
        visited_chunks: Set[str] = set()
        all_learnings: List[ResearchFinding] = []
        exploration_graph = defaultdict(list)
        
        logger.info(f"[DeepResearch] Starting: '{query}' | Depth: {depth}, Breadth: {breadth}")
        
        await self._explore_recursive(
            current_query=query, parent_queries=[query], current_depth=depth,
            current_breadth=breadth, visited_chunks=visited_chunks,
            accumulated_learnings=all_learnings, exploration_graph=exploration_graph,
            context=context
        )
        
        unique_findings = self._deduplicate_findings(all_learnings)
        
        return unique_findings, {
            "total_chunks_explored": len(visited_chunks),
            "total_findings": len(unique_findings),
            "exploration_paths": dict(exploration_graph),
            "query_coverage": self._calculate_coverage(unique_findings, query)
        }
    
    async def _explore_recursive(self, current_query: str, parent_queries: List[str],
                                current_depth: int, current_breadth: int,
                                visited_chunks: Set[str], accumulated_learnings: List[ResearchFinding],
                                exploration_graph: Dict, context: str):
        if current_depth == 0 or len(visited_chunks) > self.config.MAX_TOTAL_CHUNKS:
            return
        
        logger.info(f"[DeepResearch] Depth {current_depth} | Query: {current_query[:50]}...")
        
        search_results = await self._hybrid_search_with_meta(
            query=current_query, visited_filter=visited_chunks, top_k=self.config.TOP_K_PER_QUERY
        )
        
        if not search_results:
            return
        
        new_findings = await self._analyze_findings(
            chunks=search_results, query=current_query,
            depth=self.config.MAX_DEPTH - current_depth + 1, query_path=parent_queries
        )
        
        novel_findings = self._filter_novel_findings(new_findings, accumulated_learnings)
        
        if not novel_findings:
            return
        
        accumulated_learnings.extend(novel_findings)
        exploration_graph[current_query].extend([f.content[:30] for f in novel_findings])
        
        if current_depth > 1 and current_breadth > 0:
            sub_queries = await self._generate_exploration_queries(
                current_findings=novel_findings, parent_query=current_query,
                breadth=max(current_breadth // 2, self.config.MIN_BREADTH), context=context
            )
            
            tasks = []
            for eq in sub_queries:
                new_path = parent_queries + [eq.query]
                task = self._explore_recursive(
                    current_query=eq.query, parent_queries=new_path,
                    current_depth=current_depth - 1,
                    current_breadth=max(current_breadth // 2, self.config.MIN_BREADTH),
                    visited_chunks=visited_chunks, accumulated_learnings=accumulated_learnings,
                    exploration_graph=exploration_graph, context=context
                )
                tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks)
    
    async def _hybrid_search_with_meta(self, query: str, visited_filter: Set[str], top_k: int) -> List[Dict]:
        query_vec = self.rag.get_embedding(query)
        results = []
        
        try:
            # 只请求顶级字段，metadata 是 JSON 类型，内部字段不能单独 output
            output_fields = [MILVUS_TEXT_FIELD, "metadata", "doc_id", "page_num"]
            
            search_params = {"metric_type": "COSINE", "params": {"nprobe": 20, "ef": 16}}
            
            hits = self.rag.milvus_collection.search(
                data=[query_vec], 
                anns_field=MILVUS_VECTOR_FIELD,
                param=search_params, 
                limit=top_k * 2, 
                output_fields=output_fields
            )[0]
            
            for hit in hits:
                chunk_id = str(hit.id)
                if chunk_id in visited_filter:
                    continue
                visited_filter.add(chunk_id)
                
                entity = hit.entity
                
                # 获取 metadata JSON 并解析内部字段
                meta_raw = entity.get("metadata", {})
                meta = {}
                
                # 处理 metadata 可能是字符串或字典的情况
                if isinstance(meta_raw, str):
                    try:
                        meta = json.loads(meta_raw)
                    except json.JSONDecodeError:
                        meta = {}
                elif isinstance(meta_raw, dict):
                    meta = meta_raw
                
                # 从 metadata 中提取嵌套字段（关键修改）
                paragraph_idx = meta.get("paragraph_idx", 0)
                start_char = meta.get("start_char", 0)
                end_char = meta.get("end_char", 0)
                section_title = meta.get("section_title", "")
                
                # 同时支持顶级字段和 metadata 内字段
                result_item = {
                    "id": chunk_id,
                    "content": entity.get(MILVUS_TEXT_FIELD, ""),
                    "score": float(hit.score),
                    "doc_id": entity.get("doc_id") or meta.get("doc_id", "unknown"),
                    "metadata": {
                        # 合并顶级字段和解析后的 metadata 内部字段
                        "page": entity.get("page_num") or meta.get("page", 0),
                        "paragraph": paragraph_idx,  # 从 metadata 解析
                        "start_char": start_char,     # 从 metadata 解析
                        "end_char": end_char,         # 从 metadata 解析
                        "section_title": section_title,  # 从 metadata 解析
                        # 保留原始 metadata 的其他字段
                        **{k: v for k, v in meta.items() if k not in [
                            "paragraph_idx", "start_char", "end_char", "section_title", "page"
                        ]}
                    }
                }
                results.append(result_item)
                
        except Exception as e:
            logger.error(f"Milvus search error: {e}")
            
            # 降级到标准检索
            standard_results = self.rag.retrieve_papers(
                query, 
                StructuredRequirement("research", {}, {})
            )
            for r in standard_results:
                r["is_estimated_position"] = True
                r["doc_id"] = str(r.get("id", uuid.uuid4()))
                # 确保 metadata 结构一致
                meta = r.get("metadata", {})
                if isinstance(meta, str):
                    try:
                        meta = json.loads(meta)
                    except:
                        meta = {}
                elif not isinstance(meta, dict):
                    meta = {}
                
                # 统一格式
                r["metadata"] = {
                    "page": meta.get("page", 0),
                    "paragraph": meta.get("paragraph_idx", 0),
                    "start_char": meta.get("start_char", 0),
                    "end_char": meta.get("end_char", 0),
                    "section_title": meta.get("section_title", ""),
                    **{k: v for k, v in meta.items() if k not in [
                        "page", "paragraph_idx", "start_char", "end_char", "section_title"
                    ]}
                }
            results = standard_results[:top_k]
            
        return results[:top_k]
    
    async def _analyze_findings(self, chunks: List[Dict], query: str, depth: int, query_path: List[str]) -> List[ResearchFinding]:
        if not chunks:
            return []
        
        chunks_text = "\n\n---\n\n".join([f"[{i+1}] {c['content'][:500]}..." for i, c in enumerate(chunks)])
        
        prompt = f"""分析以下文献片段，提取与问题相关的事实发现。

    研究问题：{query}
    探索路径：{' -> '.join(query_path)}

    文献片段：
    {chunks_text}

    输出JSON数组格式（**严格遵循以下格式，不要添加任何其他文本**）：
    ```json
    [
    {{
        "content": "发现的具体内容，简明扼要",
        "supporting_chunks": [1, 2],
        "confidence": 0.9
    }}
    ]
    ```"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.rag._generate_response(messages, max_new_tokens=1024, temperature=0.3)
            
            logger.debug(f"[DeepResearch] Raw LLM response: {response[:500]}...")
            
            # 更健壮的 JSON 提取
            parsed = self._extract_json_from_response(response)
            
            if not parsed:
                raise ValueError("Failed to extract valid JSON from response")
            
            findings = []
            for item in parsed:
                source_locs = []
                chunk_ids = []
                
                for idx in item.get("supporting_chunks", []):
                    if 1 <= idx <= len(chunks):
                        chunk = chunks[idx-1]
                        meta = chunk.get("metadata", {})
                        
                        doc_id = chunk.get("doc_id", str(chunk.get("id", "unknown")))
                        doc_name = meta.get("title") or meta.get("filename") or "Unknown Document"
                        
                        loc = SourceLocation(
                            doc_id=doc_id,
                            doc_name=doc_name,
                            page=int(meta.get("page", 0)),
                            paragraph=int(meta.get("paragraph", 0)),
                            char_start=int(meta.get("start_char", 0)),
                            char_end=int(meta.get("end_char", 0)),
                            section_title=meta.get("section_title") or None,
                            surrounding_context=chunk["content"][:200] + "..." if len(chunk["content"]) > 200 else chunk["content"]
                        )
                        source_locs.append(loc)
                        chunk_ids.append(str(chunk.get("id", chunk.get("doc_id", str(uuid.uuid4())))))
                
                finding = ResearchFinding(
                    content=item.get("content", "无内容"),
                    source_locations=source_locs,
                    confidence=item.get("confidence", 0.5) * (chunk.get("score", 0.5) if 'chunk' in locals() else 0.5),
                    exploration_depth=depth,
                    query_path=query_path.copy(),
                    chunk_ids=chunk_ids
                )
                findings.append(finding)
            
            return findings
            
        except Exception as e:
            logger.error(f"Error analyzing findings: {e}")
            logger.debug(f"Response content: {response if 'response' in locals() else 'N/A'}")
            
            # Fallback: 创建简单的研究发现
            return self._create_fallback_findings(chunks, query, depth, query_path)


    def _extract_json_from_response(self, response: str) -> Optional[List]:
        """从 LLM 响应中提取 JSON 数组"""
        if not response:
            return None
        
        # 尝试 1: 直接解析整个响应
        try:
            trimmed = response.strip()
            if trimmed.startswith('[') and trimmed.endswith(']'):
                return json.loads(trimmed)
        except json.JSONDecodeError:
            pass
        
        # 尝试 2: 提取 ```json ... ``` 代码块
        try:
            import re
            pattern = r'```(?:json)?\s*(\[[\s\S]*?\])\s*```'
            match = re.search(pattern, response)
            if match:
                return json.loads(match.group(1))
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # 尝试 3: 提取方括号包围的内容
        try:
            pattern = r'(\[[\s\S]*?\])'
            matches = re.findall(pattern, response)
            for match in matches:
                try:
                    parsed = json.loads(match)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        return parsed
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass
        
        # 尝试 4: 寻找第一个 [ 和最后一个 ]
        try:
            start = response.find('[')
            end = response.rfind(']')
            if start != -1 and end != -1 and end > start:
                return json.loads(response[start:end+1])
        except json.JSONDecodeError:
            pass
        
        return None


    def _create_fallback_findings(self, chunks: List[Dict], query: str, depth: int, query_path: List[str]) -> List[ResearchFinding]:
        """当 JSON 解析失败时，创建备用的研究发现"""
        findings = []
        
        for i, chunk in enumerate(chunks[:3]):  # 只取前3个作为备选
            meta = chunk.get("metadata", {})
            
            loc = SourceLocation(
                doc_id=str(chunk.get("id", chunk.get("doc_id", f"chunk_{i}"))),
                doc_name=meta.get("title", meta.get("filename", "Unknown")),
                page=int(meta.get("page", 0)),
                paragraph=int(meta.get("paragraph", 0)),
                char_start=int(meta.get("start_char", 0)),
                char_end=int(meta.get("end_char", 0)),
                section_title=None,
                surrounding_context=chunk["content"][:150] + "..." if len(chunk["content"]) > 150 else chunk["content"]
            )
            
            finding = ResearchFinding(
                content=f"相关片段: {chunk['content'][:200]}...",
                source_locations=[loc],
                confidence=chunk.get("score", 0.5) * 0.8,  # 降低置信度因为解析失败
                exploration_depth=depth,
                query_path=query_path.copy(),
                chunk_ids=[str(chunk.get("id", f"chunk_{i}"))]
            )
            findings.append(finding)
        
        logger.info(f"[DeepResearch] Created {len(findings)} fallback findings")
        return findings
    
    def _filter_novel_findings(self, new_findings: List[ResearchFinding], existing: List[ResearchFinding]) -> List[ResearchFinding]:
        if not existing:
            return new_findings
        
        novel = []
        for nf in new_findings:
            is_duplicate = False
            for ef in existing:
                if self._text_similarity(nf.content, ef.content) > self.config.SIMILARITY_THRESHOLD:
                    is_duplicate = True
                    break
            if not is_duplicate:
                novel.append(nf)
        return novel
    
    def _text_similarity(self, t1: str, t2: str) -> float:
        words1 = set(t1.lower().split())
        words2 = set(t2.lower().split())
        if not words1 or not words2:
            return 0.0
        return len(words1 & words2) / max(len(words1), len(words2))
    
    async def _generate_exploration_queries(self, current_findings: List[ResearchFinding], 
                                           parent_query: str, breadth: int, context: str) -> List[ExplorationQuery]:
        findings_text = "\n".join([f"- {f.content} (置信度: {f.confidence:.2f})" for f in current_findings[:5]])
        
        prompt = f"""基于以下研究发现，生成{breadth}个新的深度探索查询。

原始问题：{parent_query}
已有发现：
{findings_text}

输出JSON数组：
[
  {{
    "query": "具体搜索语句",
    "strategy": "深挖/关联/对比/溯源"
  }}
]"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.rag._generate_response(messages, max_new_tokens=512, temperature=0.5)
            
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return [
                    ExplorationQuery(query=p["query"], strategy=p.get("strategy", "深挖"))
                    for p in parsed[:breadth]
                ]
        except Exception as e:
            logger.error(f"Error generating exploration queries: {e}")
        
        return [
            ExplorationQuery(query=f"{parent_query} 详细机制", strategy="深挖"),
            ExplorationQuery(query=f"{parent_query} 对比分析", strategy="对比")
        ][:breadth]
    
    def _deduplicate_findings(self, findings: List[ResearchFinding]) -> List[ResearchFinding]:
        seen = set()
        unique = []
        for f in findings:
            key = f.content[:50]
            if key not in seen:
                seen.add(key)
                unique.append(f)
        unique.sort(key=lambda x: (x.confidence, x.exploration_depth), reverse=True)
        return unique
    
    def _calculate_coverage(self, findings: List[ResearchFinding], original_query: str) -> float:
        if not findings:
            return 0.0
        return min(1.0, len(findings) * 0.1 + sum(f.exploration_depth for f in findings) * 0.05)

# ==============================================================================
# 3. 数据中心（保留原有）
# ==============================================================================

class ExperimentDataManager:
    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._audit_log: List[Dict] = []
        self._lock = asyncio.Lock()
    
    async def save(self, data: Any, description: str, data_type: str = "generic") -> str:
        async with self._lock:
            data_id = f"{data_type}_{uuid.uuid4().hex[:12]}"
            timestamp = datetime.now().isoformat()
            
            entry = {
                "id": data_id,
                "type": data_type,
                "timestamp": timestamp,
                "description": description,
                "payload": data
            }
            self._store[data_id] = entry
            
            self._audit_log.append({
                "action": "SAVE",
                "id": data_id,
                "type": data_type,
                "desc": description,
                "timestamp": timestamp
            })
            logger.info(f"[DataManager] Stored {data_type} -> {data_id}")
            return data_id

    async def get(self, data_id: str, accessor: str = "system") -> Any:
        async with self._lock:
            if data_id not in self._store:
                raise ValueError(f"Data ID {data_id} not found")
            
            if "recipe" in data_id or "vector" in data_id:
                self._audit_log.append({
                    "action": "ACCESS_ATTEMPT",
                    "id": data_id,
                    "accessor": accessor,
                    "timestamp": datetime.now().isoformat()
                })
                if accessor == "llm_agent":
                    raise PermissionError("LLM Agent is prohibited from accessing raw numerical recipe data")
            
            return self._store[data_id]["payload"]

    def get_safe_summary(self, data_id: str) -> Dict:
        if data_id not in self._store:
            return {"error": "Data not found"}
        
        entry = self._store[data_id]
        payload = entry["payload"]
        
        if isinstance(payload, list):
            return {
                "id": data_id,
                "type": entry["type"],
                "count": len(payload),
                "items_type": type(payload[0]).__name__ if payload else "unknown",
                "description": entry["description"]
            }
        return {
            "id": data_id,
            "type": entry["type"],
            "description": entry["description"]
        }

    async def export_dataset(self, experiment_run_id: str) -> str:
        relevant_entries = [
            entry for entry in self._store.values() 
            if experiment_run_id in entry["description"]
        ]
        dataset_id = f"dataset_{uuid.uuid4().hex[:8]}"
        self._store[dataset_id] = {
            "experiment_run_id": experiment_run_id,
            "records": relevant_entries,
            "export_time": datetime.now().isoformat()
        }
        return dataset_id

data_manager = ExperimentDataManager()

# ==============================================================================
# 4. 科学工具层（保留原有，供Agent调用）
# ==============================================================================

class ScientificTools:
    def __init__(self, rag_service: AdvancedRAGService):
        self.rag = rag_service
        self.execution_log = []
    
    async def literature_matching(self, requirement: str, structured_req: StructuredRequirement) -> str:
        logger.info(f"[Tool] Literature Deep Matching: {requirement[:50]}...")
        deep_result = await self._deep_local_research(requirement, 2, json.dumps(structured_req.key_constraints))
        return deep_result
    
    async def _deep_local_research(self, research_question: str, depth: int, context: str) -> str:
        try:
            findings, metadata = await self.rag.deep_research_engine.deep_research(
                query=research_question, depth=depth, breadth=3, context=context
            )
            
            if not findings:
                return json.dumps({
                    "status": "no_results",
                    "message": "在本地知识库中未找到相关信息",
                    "suggestion": "尝试使用更广泛的关键词或检查拼写"
                }, ensure_ascii=False)
            
            formatted_output = []
            for i, finding in enumerate(findings[:10], 1):
                sources = []
                for loc in finding.source_locations[:2]:
                    src = f"{loc.doc_name}"
                    if loc.page > 0:
                        src += f" (p.{loc.page}"
                        if loc.section_title:
                            src += f", {loc.section_title}"
                        src += ")"
                    sources.append(src)
                
                formatted_output.append({
                    "index": i,
                    "insight": finding.content,
                    "sources": sources,
                    "confidence": round(finding.confidence, 2),
                    "depth": finding.exploration_depth
                })
            
            findings_id = await data_manager.save(
                [asdict(f) for f in findings],
                f"Deep research findings for: {research_question[:30]}",
                "deep_research_findings"
            )
            
            return json.dumps({
                "status": "success",
                "findings_count": len(findings),
                "findings_id": findings_id,
                "exploration_metadata": {
                    "depth_reached": metadata["max_depth"] if metadata else depth,
                    "chunks_explored": metadata["total_chunks_explored"] if metadata else 0
                },
                "key_insights": formatted_output,
                "note": f"发现已存储于 {findings_id}，可使用文献挖掘工具进一步提取化学实体"
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"Deep research failed: {e}", exc_info=True)
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)
    
    async def literature_mining(self, paper_refs_id: str) -> str:
        logger.info(f"[Tool] Literature Mining: {paper_refs_id}")
        
        try:
            data = await data_manager.get(paper_refs_id, "literature_mining_tool")
            
            if isinstance(data, list) and len(data) > 0 and "source_locations" in data[0]:
                findings = [ResearchFinding(**f) for f in data]
                combined_text = " ".join([f.content for f in findings])
            else:
                combined_text = str(data)
            
            mined_data = await self._extract_entities_from_findings(combined_text)
            
            mining_result_id = await data_manager.save(
                mined_data,
                f"Mined chemical entities from {paper_refs_id}",
                "mining_result"
            )
            
            return json.dumps({
                "status": "success",
                "mining_result_id": mining_result_id,
                "extracted_entities": {
                    "salts": mined_data["salts"],
                    "solvents": mined_data["solvents"][:5],
                    "additives": mined_data["additives"]
                },
                "source_findings": len(data) if isinstance(data, list) else 0,
                "note": "从深度研究的详细发现中提取化学实体"
            }, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
    
    async def _extract_entities_from_findings(self, text: str) -> Dict:
        prompt = f"""从以下研究文本中提取电化学相关化学实体：

文本：
{text[:3000]}

请提取：
1. 锂盐（如LiPF6, LiFSI等）
2. 溶剂（如EC, DEC, DMC等）
3. 添加剂（如VC, FEC等）

输出JSON格式：
{{
    "salts": ["...", "..."],
    "solvents": ["...", "..."],
    "additives": ["...", "..."]
}}"""
        
        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.rag._generate_response(messages, max_new_tokens=512, temperature=0.2)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
        
        return {
            "salts": ["LiPF6", "LiFSI"],
            "solvents": ["EC", "DEC", "DMC"],
            "additives": ["VC", "FEC"],
            "key_insights": ["使用深度研究发现的关键线索"]
        }

    async def molecular_expansion(self, mining_result_id: str) -> str:
        logger.info(f"[Tool] Molecular Expansion: {mining_result_id}")
        
        try:
            mined = await data_manager.get(mining_result_id, "molecular_expansion_tool")
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
        
        expanded_molecules = {
            "base_salts": mined["salts"],
            "expanded_salts": mined["salts"] + ["LiBOB", "LiODFB"],
            "base_solvents": mined["solvents"],
            "expanded_solvents": mined["solvents"] + ["FEC", "PC", "VC"],
            "functional_groups": ["fluorinated", "sulfone_based", "phosphate"],
            "search_space_size": 150
        }
        
        expansion_id = await data_manager.save(
            expanded_molecules,
            f"Expanded molecular library from {mining_result_id}",
            "molecular_library"
        )
        
        return json.dumps({
            "status": "success",
            "expansion_id": expansion_id,
            "library_size": expanded_molecules["search_space_size"],
            "candidate_families": list(set(expanded_molecules["expanded_salts"] + expanded_molecules["expanded_solvents"]))
        })

    async def property_prediction_and_screening(self, expansion_id: str, target_properties: Dict[str, float]) -> str:
        logger.info(f"[Tool] Property Screening: {expansion_id}")
        
        try:
            library = await data_manager.get(expansion_id, "screening_tool")
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
        
        screening_results = {
            "candidates_passed": [
                {"name": "LiPF6", "predicted_conductivity": 7.5, "oxidation_potential": 4.3, "score": 0.85},
                {"name": "FEC", "predicted_lumo": -1.2, "reduction_potential": 1.5, "score": 0.92},
                {"name": "DMC", "predicted_viscosity": 0.6, "flash_point": 18, "score": 0.78},
                {"name": "VC", "predicted_sei_quality": 0.9, "gas_generation": 0.1, "score": 0.88}
            ],
            "filtered_out": [
                {"name": "PC", "reason": "与石墨负极不兼容，高分解风险"}
            ],
            "optimal_combinations": [
                {"salt": "LiPF6", "solvents": ["FEC", "DMC"], "expected_performance": 0.87}
            ]
        }
        
        screening_id = await data_manager.save(
            screening_results,
            f"Screened molecules from {expansion_id}",
            "screening_result"
        )
        
        top_candidates = screening_results["candidates_passed"][:3]
        return json.dumps({
            "status": "success",
            "screening_id": screening_id,
            "pass_rate": len(screening_results["candidates_passed"]) / 5,
            "top_candidates": top_candidates,
            "recommended_base": screening_results["optimal_combinations"][0]
        })

    async def generate_recipe(self, screening_id: str, batch_size: int = BATCH_SIZE) -> str:
        logger.info(f"[Tool] Recipe Generation: {screening_id}, Batch={batch_size}")
        
        try:
            screening = await data_manager.get(screening_id, "recipe_generator")
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
        
        recipes = []
        base_salt = "LiPF6"
        base_solvents = ["FEC", "DMC", "EC"]
        
        for i in range(batch_size):
            salt_conc = 1.0 + np.random.uniform(-0.2, 0.2)
            fec_ratio = np.random.uniform(0.05, 0.15)
            dmc_ratio = np.random.uniform(0.4, 0.6)
            ec_ratio = 1.0 - fec_ratio - dmc_ratio - (salt_conc * 0.1)
            
            total = salt_conc * 0.1 + fec_ratio + dmc_ratio + ec_ratio
            norm_factors = [salt_conc * 0.1 / total, fec_ratio / total, dmc_ratio / total, ec_ratio / total]
            
            recipe_vec = {
                "salt_conc_m": float(salt_conc),
                "composition_vol_frac": {
                    "FEC": float(norm_factors[1]),
                    "DMC": float(norm_factors[2]),
                    "EC": float(norm_factors[3])
                },
                "additive_ppm": {"VC": 2000}
            }
            
            recipes.append(recipe_vec)
        
        recipe_group_id = await data_manager.save(
            recipes,
            f"Generated {batch_size} recipes for screening {screening_id}",
            "recipe_group"
        )
        
        return json.dumps({
            "status": "success",
            "recipe_group_id": recipe_group_id,
            "batch_size": batch_size,
            "components": list(recipes[0]["composition_vol_frac"].keys()) + [base_salt],
            "warning": "数值配方已安全存储，使用 recipe_group_id 进行实验，严禁LLM猜测数值"
        })

    async def run_hardware_experiment(self, recipe_group_id: str) -> str:
        logger.info(f"[Tool] Hardware Experiment: {recipe_group_id}")
        
        try:
            recipes = await data_manager.get(recipe_group_id, "hardware_interface")
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
        
        results = []
        for i, recipe in enumerate(recipes):
            ce = 98.5 + np.random.normal(0, 0.5)
            if i == 1:
                ce = 99.2
            
            result = {
                "recipe_index": i,
                "coulombic_efficiency": float(ce),
                "conductivity_ms": float(7.5 + np.random.normal(0, 0.5)),
                "viscosity_cp": float(3.2 + np.random.normal(0, 0.2)),
                "cycle_life_80": int(500 + np.random.normal(0, 50))
            }
            results.append(result)
            logger.info(f"  [Hardware] Recipe {i}: CE={result['coulombic_efficiency']:.2f}%")
        
        result_group_id = await data_manager.save(
            results,
            f"Experimental results for {recipe_group_id}",
            "experiment_results"
        )
        
        ce_values = [r["coulombic_efficiency"] for r in results]
        best_idx = np.argmax(ce_values)
        
        return json.dumps({
            "status": "success",
            "result_group_id": result_group_id,
            "experiment_count": len(results),
            "performance_summary": {
                "best_ce": float(max(ce_values)),
                "worst_ce": float(min(ce_values)),
                "mean_ce": float(np.mean(ce_values)),
                "best_recipe_index": int(best_idx)
            },
            "next_action_hint": "如果未达标，请调用贝叶斯优化；如果达标，结束实验"
        })

    async def bayesian_optimization(self, result_group_id: str, historical_context: List[str] = None) -> str:
        logger.info(f"[Tool] Bayesian Optimization: {result_group_id}")
        
        try:
            results = await data_manager.get(result_group_id, "bayesian_optimizer")
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
        
        ce_values = [r["coulombic_efficiency"] for r in results]
        best_ce = max(ce_values)
        
        if best_ce >= TARGET_METRIC_THRESHOLD:
            return json.dumps({
                "stop_signal": True,
                "stop_reason": f"Target CE {TARGET_METRIC_THRESHOLD}% achieved (Current: {best_ce:.2f}%)",
                "recommendation": "TERMINATE_SUCCESS",
                "final_performance": {
                    "best_coulombic_efficiency": float(best_ce),
                    "iterations_completed": len(historical_context) if historical_context else 1
                }
            })
        
        next_cycle_suggestions = {
            "target_metric_improvement": "increase_salt_conc",
            "exploration_direction": "increase_fec_ratio",
            "expected_improvement": 0.5,
            "stop_signal": False
        }
        
        opt_id = await data_manager.save(
            next_cycle_suggestions,
            f"Optimization guidance for {result_group_id}",
            "optimization_plan"
        )
        
        return json.dumps({
            "stop_signal": False,
            "optimization_plan_id": opt_id,
            "reasoning": f"Current best CE {best_ce:.2f}% < target {TARGET_METRIC_THRESHOLD}%. Suggesting next iteration.",
            "hints_for_next_generation": next_cycle_suggestions
        })

# ==============================================================================
# 5. Agent 基类与专业 Agent（新增）
# ==============================================================================

class BaseAgent(ABC):
    def __init__(self, agent_id: str, message_bus: MessageBus, state_manager: SecureStateManager, 
                 data_manager: ExperimentDataManager, rag_service: AdvancedRAGService):
        self.agent_id = agent_id
        self.bus = message_bus
        self.state = state_manager
        self.data = data_manager
        self.rag = rag_service
        self.tools = ScientificTools(rag_service)
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._logger = logging.getLogger(f"Agent.{agent_id}")
    
    async def start(self):
        self.running = True
        self.bus.register_agent(self.agent_id)
        self._task = asyncio.create_task(self._lifecycle())
        self._logger.info(f"Started")
    
    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._logger.info(f"Stopped")
    
    async def _lifecycle(self):
        try:
            await asyncio.gather(
                self._message_loop(),
                self._run()
            )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._logger.error(f"Lifecycle error: {e}", exc_info=True)
            await self._notify_error(str(e))
    
    async def _message_loop(self):
        while self.running:
            try:
                msg = await self.bus.get_message(self.agent_id, timeout=1.0)
                if msg:
                    await self.handle_message(msg)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self._logger.error(f"Message handling error: {e}")
    
    @abstractmethod
    async def _run(self):
        pass
    
    @abstractmethod
    async def handle_message(self, message: AgentMessage):
        pass
    
    async def _notify_error(self, error_msg: str):
        await self.bus.send(AgentMessage(
            sender=self.agent_id,
            receiver="master",
            message_type=MessageType.ERROR_NOTIFY,
            payload={"error": error_msg}
        ))
    
    async def report_result(self, corr_id: str, status: str, task: str, data: Dict):
        await self.bus.send(AgentMessage(
            sender=self.agent_id,
            receiver="master",
            message_type=MessageType.RESULT_REPORT,
            payload={"status": status, "task": task, **data},
            correlation_id=corr_id
        ))

class RequirementAnalystAgent(BaseAgent):
    async def _run(self):
        while self.running:
            await asyncio.sleep(1)
    
    async def handle_message(self, msg: AgentMessage):
        if msg.message_type == MessageType.TASK_ASSIGN and msg.payload.get("task") == "analyze_requirement":
            corr_id = msg.correlation_id
            user_input = msg.payload["user_input"]
            
            self._logger.info(f"Analyzing requirement for {corr_id}")
            
            try:
                structured = self.rag.analyze_research_requirement(user_input)
                
                await self.state.set_data(
                    "structured_requirement",
                    {
                        "target_application": structured.target_application,
                        "key_constraints": structured.key_constraints,
                        "desired_properties": structured.desired_properties,
                        "priority_weight": structured.priority_weight
                    },
                    allowed_agents=["master", "literature_retriever", "knowledge_miner"],
                    corr_id=corr_id
                )
                
                await self.report_result(corr_id, "success", "requirement_analysis", {
                    "summary": structured.target_application
                })
                
            except Exception as e:
                await self.report_result(corr_id, "error", "requirement_analysis", {"error": str(e)})

class LiteratureRetrieverAgent(BaseAgent):
    async def _run(self):
        while self.running:
            await asyncio.sleep(1)
    
    async def handle_message(self, msg: AgentMessage):
        if msg.message_type == MessageType.TASK_ASSIGN and msg.payload.get("task") == "retrieve_literature":
            corr_id = msg.correlation_id
            try:
                req = await self.state.get_data("structured_requirement", self.agent_id, corr_id)
                query = f"{req['target_application']} electrolyte high voltage"
                
                self._logger.info(f"Retrieving literature for {corr_id}")
                result = await self.tools.literature_matching(query, StructuredRequirement(**req))
                parsed = json.loads(result)
                
                if parsed.get("status") == "success":
                    await self.state.set_data(
                        "literature_result",
                        parsed,
                        allowed_agents=["master", "knowledge_miner"],
                        corr_id=corr_id
                    )
                    await self.report_result(corr_id, "success", "literature_retrieval", {
                        "findings_count": parsed.get("findings_count", 0),
                        "findings_id": parsed.get("findings_id")
                    })
                else:
                    raise Exception(parsed.get("message", "Unknown error"))
                    
            except Exception as e:
                await self.report_result(corr_id, "error", "literature_retrieval", {"error": str(e)})

class KnowledgeMinerAgent(BaseAgent):
    async def _run(self):
        while self.running:
            await asyncio.sleep(1)
    
    async def handle_message(self, msg: AgentMessage):
        if msg.message_type == MessageType.TASK_ASSIGN and msg.payload.get("task") == "mine_knowledge":
            corr_id = msg.correlation_id
            try:
                lit_result = await self.state.get_data("literature_result", self.agent_id, corr_id)
                findings_id = lit_result.get("findings_id")
                
                if not findings_id:
                    raise Exception("No findings_id available")
                
                result = await self.tools.literature_mining(findings_id)
                parsed = json.loads(result)
                
                if parsed.get("status") == "success":
                    await self.state.set_data(
                        "mining_result",
                        parsed,
                        allowed_agents=["master", "molecule_designer"],
                        corr_id=corr_id
                    )
                    await self.report_result(corr_id, "success", "knowledge_mining", {
                        "mining_result_id": parsed.get("mining_result_id"),
                        "entities": parsed.get("extracted_entities")
                    })
                else:
                    raise Exception(parsed.get("message"))
                    
            except Exception as e:
                await self.report_result(corr_id, "error", "knowledge_mining", {"error": str(e)})

class MoleculeDesignerAgent(BaseAgent):
    async def _run(self):
        while self.running:
            await asyncio.sleep(1)
    
    async def handle_message(self, msg: AgentMessage):
        if msg.message_type == MessageType.TASK_ASSIGN and msg.payload.get("task") == "design_molecules":
            corr_id = msg.correlation_id
            try:
                mining = await self.state.get_data("mining_result", self.agent_id, corr_id)
                mining_id = mining.get("mining_result_id")
                
                result = await self.tools.molecular_expansion(mining_id)
                parsed = json.loads(result)
                
                if parsed.get("status") == "success":
                    await self.state.set_data(
                        "molecule_library",
                        parsed,
                        allowed_agents=["master", "formulation_engineer"],
                        corr_id=corr_id
                    )
                    await self.report_result(corr_id, "success", "molecule_design", {
                        "expansion_id": parsed.get("expansion_id"),
                        "library_size": parsed.get("library_size")
                    })
                else:
                    raise Exception("Expansion failed")
                    
            except Exception as e:
                await self.report_result(corr_id, "error", "molecule_design", {"error": str(e)})

class FormulationEngineerAgent(BaseAgent):
    async def _run(self):
        while self.running:
            await asyncio.sleep(1)
    
    async def handle_message(self, msg: AgentMessage):
        if msg.message_type == MessageType.TASK_ASSIGN and msg.payload.get("task") == "generate_formulation":
            corr_id = msg.correlation_id
            try:
                lib = await self.state.get_data("molecule_library", self.agent_id, corr_id)
                expansion_id = lib.get("expansion_id")
                
                # 获取目标属性
                req = await self.state.get_data("structured_requirement", self.agent_id, corr_id)
                target_props = req.get("properties", {})
                
                # 先进行性质预测筛选
                screen_result = await self.tools.property_prediction_and_screening(expansion_id, target_props)
                screen_parsed = json.loads(screen_result)
                
                if screen_parsed.get("status") != "success":
                    raise Exception("Screening failed")
                
                screening_id = screen_parsed.get("screening_id")
                
                # 生成配方
                result = await self.tools.generate_recipe(screening_id, BATCH_SIZE)
                parsed = json.loads(result)
                
                if parsed.get("status") == "success":
                    await self.state.set_data(
                        "recipe_data",
                        parsed,
                        allowed_agents=["master", "experiment_executor"],  # 严格限制
                        corr_id=corr_id
                    )
                    await self.report_result(corr_id, "success", "formulation", {
                        "recipe_group_id": parsed.get("recipe_group_id"),
                        "batch_size": parsed.get("batch_size")
                    })
                else:
                    raise Exception("Formulation failed")
                    
            except Exception as e:
                await self.report_result(corr_id, "error", "formulation", {"error": str(e)})

class ExperimentExecutorAgent(BaseAgent):
    async def _run(self):
        while self.running:
            await asyncio.sleep(1)
    
    async def handle_message(self, msg: AgentMessage):
        if msg.message_type == MessageType.TASK_ASSIGN and msg.payload.get("task") == "run_experiment":
            corr_id = msg.correlation_id
            try:
                recipe_data = await self.state.get_data("recipe_data", self.agent_id, corr_id)
                recipe_group_id = recipe_data.get("recipe_group_id")
                
                self._logger.info(f"Running hardware experiment for {corr_id}")
                result = await self.tools.run_hardware_experiment(recipe_group_id)
                parsed = json.loads(result)
                
                if parsed.get("status") == "success":
                    await self.state.set_data(
                        "experiment_result",
                        parsed,
                        allowed_agents=["master", "result_analyzer", "bayesian_optimizer"],
                        corr_id=corr_id
                    )
                    await self.report_result(corr_id, "success", "experiment", {
                        "result_group_id": parsed.get("result_group_id"),
                        "best_ce": parsed["performance_summary"]["best_ce"]
                    })
                else:
                    raise Exception("Experiment failed")
                    
            except Exception as e:
                await self.report_result(corr_id, "error", "experiment", {"error": str(e)})

class ResultAnalyzerAgent(BaseAgent):
    async def _run(self):
        while self.running:
            await asyncio.sleep(1)
    
    async def handle_message(self, msg: AgentMessage):
        if msg.message_type == MessageType.TASK_ASSIGN and msg.payload.get("task") == "analyze_results":
            corr_id = msg.correlation_id
            try:
                exp_result = await self.state.get_data("experiment_result", self.agent_id, corr_id)
                ctx = await self.state.get_context(corr_id)
                
                best_ce = exp_result["performance_summary"]["best_ce"]
                target_ce = ctx.get("target_ce", TARGET_METRIC_THRESHOLD)
                meets_target = best_ce >= target_ce
                
                analysis = {
                    "meets_target": meets_target,
                    "best_ce": best_ce,
                    "target_ce": target_ce,
                    "gap": target_ce - best_ce
                }
                
                await self.state.set_data(
                    "analysis_result",
                    analysis,
                    allowed_agents=["master", "bayesian_optimizer"],
                    corr_id=corr_id
                )
                
                await self.report_result(corr_id, "success", "analysis", {
                    "meets_target": meets_target,
                    "requires_optimization": not meets_target and ctx.get("current_iteration", 0) < ctx.get("max_iterations", 5)
                })
                
            except Exception as e:
                await self.report_result(corr_id, "error", "analysis", {"error": str(e)})

class BayesianOptimizerAgent(BaseAgent):
    async def _run(self):
        while self.running:
            await asyncio.sleep(1)
    
    async def handle_message(self, msg: AgentMessage):
        if msg.message_type == MessageType.TASK_ASSIGN and msg.payload.get("task") == "optimize":
            corr_id = msg.correlation_id
            try:
                analysis = await self.state.get_data("analysis_result", self.agent_id, corr_id)
                
                if analysis.get("meets_target"):
                    await self.report_result(corr_id, "success", "optimization", {
                        "stop_signal": True,
                        "reason": "Target achieved",
                        "final_ce": analysis["best_ce"]
                    })
                else:
                    exp_result = await self.state.get_data("experiment_result", self.agent_id, corr_id)
                    result_group_id = exp_result.get("result_group_id")
                    
                    opt_result = await self.tools.bayesian_optimization(result_group_id)
                    parsed = json.loads(opt_result)
                    
                    if parsed.get("status") == "success":
                        await self.state.set_data(
                            "optimization_plan",
                            parsed,
                            allowed_agents=["master", "formulation_engineer"],
                            corr_id=corr_id
                        )
                        await self.report_result(corr_id, "success", "optimization", {
                            "stop_signal": parsed.get("stop_signal", False),
                            "strategy": parsed.get("hints_for_next_generation", {})
                        })
                    else:
                        raise Exception("Optimization failed")
                        
            except Exception as e:
                await self.report_result(corr_id, "error", "optimization", {"error": str(e)})

# ==============================================================================
# 6. Master Agent（中央调度器）
# ==============================================================================

class MasterAgent:
    def __init__(self, message_bus: MessageBus, state_manager: SecureStateManager):
        self.agent_id = "master"
        self.bus = message_bus
        self.state = state_manager
        self._logger = logging.getLogger("MasterAgent")
        self._futures: Dict[str, asyncio.Future] = {}
        self.running = False
    
    async def start(self):
        self.running = True
        self.bus.register_agent(self.agent_id)
        self.bus.subscribe(MessageType.RESULT_REPORT.value, self._handle_result)
        self.bus.subscribe(MessageType.ERROR_NOTIFY.value, self._handle_error)
        self._logger.info("MasterAgent started")
    
    async def start_workflow(self, requirement: str, target_ce: float = 99.5, max_iter: int = 5) -> str:
        corr_id = await self.state.create_workflow(requirement, target_ce, max_iter)
        future = asyncio.Future()
        self._futures[corr_id] = future
        
        self._logger.info(f"Starting workflow {corr_id}")
        
        # 启动第一个Agent
        await self.bus.send(AgentMessage(
            sender=self.agent_id,
            receiver="requirement_analyst",
            message_type=MessageType.TASK_ASSIGN,
            payload={"task": "analyze_requirement", "user_input": requirement},
            correlation_id=corr_id
        ))
        
        return corr_id
    
    async def _handle_result(self, message: AgentMessage):
        if message.receiver != self.agent_id:
            return
        
        corr_id = message.correlation_id
        payload = message.payload
        task = payload.get("task")
        
        self._logger.info(f"Received result: {task} for {corr_id} - Status: {payload.get('status')}")
        
        if payload.get("status") != "success":
            self._logger.error(f"Task failed: {payload.get('error')}")
            await self.state.update_context(corr_id, "state", "failed")
            if corr_id in self._futures:
                self._futures[corr_id].set_exception(Exception(payload.get("error")))
            return
        
        # 状态机路由
        if task == "requirement_analysis":
            await self.state.update_context(corr_id, "state", "literature_retrieval")
            await self.bus.send(AgentMessage(
                sender=self.agent_id,
                receiver="literature_retriever",
                message_type=MessageType.TASK_ASSIGN,
                payload={"task": "retrieve_literature"},
                correlation_id=corr_id
            ))
            
        elif task == "literature_retrieval":
            await self.state.update_context(corr_id, "state", "knowledge_mining")
            await self.bus.send(AgentMessage(
                sender=self.agent_id,
                receiver="knowledge_miner",
                message_type=MessageType.TASK_ASSIGN,
                payload={"task": "mine_knowledge"},
                correlation_id=corr_id
            ))
            
        elif task == "knowledge_mining":
            await self.state.update_context(corr_id, "state", "molecule_design")
            await self.bus.send(AgentMessage(
                sender=self.agent_id,
                receiver="molecule_designer",
                message_type=MessageType.TASK_ASSIGN,
                payload={"task": "design_molecules"},
                correlation_id=corr_id
            ))
            
        elif task == "molecule_design":
            await self.state.update_context(corr_id, "state", "formulation")
            await self.bus.send(AgentMessage(
                sender=self.agent_id,
                receiver="formulation_engineer",
                message_type=MessageType.TASK_ASSIGN,
                payload={"task": "generate_formulation"},
                correlation_id=corr_id
            ))
            
        elif task == "formulation":
            await self.state.update_context(corr_id, "state", "experiment_running")
            await self.bus.send(AgentMessage(
                sender=self.agent_id,
                receiver="experiment_executor",
                message_type=MessageType.TASK_ASSIGN,
                payload={"task": "run_experiment"},
                correlation_id=corr_id
            ))
            
        elif task == "experiment":
            await self.state.update_context(corr_id, "state", "analysis")
            await self.bus.send(AgentMessage(
                sender=self.agent_id,
                receiver="result_analyzer",
                message_type=MessageType.TASK_ASSIGN,
                payload={"task": "analyze_results"},
                correlation_id=corr_id
            ))
            
        elif task == "analysis":
            ctx = await self.state.get_context(corr_id)
            current_iter = ctx.get("current_iteration", 0)
            
            if payload.get("requires_optimization") and current_iter < ctx.get("max_iterations", 5):
                await self.state.update_context(corr_id, "current_iteration", current_iter + 1)
                await self.state.update_context(corr_id, "state", "optimization")
                await self.bus.send(AgentMessage(
                    sender=self.agent_id,
                    receiver="bayesian_optimizer",
                    message_type=MessageType.TASK_ASSIGN,
                    payload={"task": "optimize"},
                    correlation_id=corr_id
                ))
            else:
                await self._complete_workflow(corr_id, payload)
                
        elif task == "optimization":
            if payload.get("stop_signal"):
                await self._complete_workflow(corr_id, payload)
            else:
                # 继续下一轮
                await self.state.update_context(corr_id, "state", "formulation")
                await self.bus.send(AgentMessage(
                    sender=self.agent_id,
                    receiver="formulation_engineer",
                    message_type=MessageType.TASK_ASSIGN,
                    payload={"task": "generate_formulation"},
                    correlation_id=corr_id
                ))
    
    async def _complete_workflow(self, corr_id: str, final_data: Dict):
        await self.state.update_context(corr_id, "state", "completed")
        if corr_id in self._futures:
            self._futures[corr_id].set_result({
                "status": "completed",
                "correlation_id": corr_id,
                "final_data": final_data
            })
    
    async def _handle_error(self, message: AgentMessage):
        corr_id = message.correlation_id
        self._logger.error(f"Error in {corr_id}: {message.payload}")
        await self.state.update_context(corr_id, "state", "failed")
        if corr_id in self._futures:
            self._futures[corr_id].set_exception(Exception(message.payload.get("error")))
    
    async def wait_for_completion(self, corr_id: str, timeout: float = 600):
        if corr_id not in self._futures:
            return None
        try:
            return await asyncio.wait_for(self._futures[corr_id], timeout=timeout)
        except asyncio.TimeoutError:
            return {"status": "timeout"}

# ==============================================================================
# 7. 保留的 ReAct Agent（向后兼容）
# ==============================================================================

class ResearchAgent:
    """保留原有的ReAct Agent作为可选的单体模式"""
    VALID_TOOLS = [
        "literature_matching", "literature_mining", "molecular_expansion",
        "property_prediction_and_screening", "generate_recipe", 
        "run_hardware_experiment", "bayesian_optimization"
    ]
    
    DEPENDENCY_GRAPH = {
        "literature_mining": ["literature_matching"],
        "molecular_expansion": ["literature_mining"],
        "property_prediction_and_screening": ["molecular_expansion"],
        "generate_recipe": ["property_prediction_and_screening"],
        "run_hardware_experiment": ["generate_recipe"],
        "bayesian_optimization": ["run_hardware_experiment"]
    }

    def __init__(self, rag_service: AdvancedRAGService):
        self.rag = rag_service
        self.tools = ScientificTools(rag_service)
        self.tokenizer = rag_service.tokenizer
        self.model = rag_service.model
        self.conversation_history = []
        
        self.tool_schemas = {
            "literature_matching": {
                "description": "Step 1: 深度文献匹配",
                "parameters": {"requirement": "str", "structured_req_hint": "JSON, optional"}
            },
            "literature_mining": {
                "description": "Step 2: 文献挖掘",
                "parameters": {"paper_refs_id": "str"}
            },
            "molecular_expansion": {
                "description": "Step 3: 分子扩增",
                "parameters": {"mining_result_id": "str"}
            },
            "property_prediction_and_screening": {
                "description": "Step 4: 性质预测筛选",
                "parameters": {"expansion_id": "str", "target_properties": "JSON"}
            },
            "generate_recipe": {
                "description": "Step 5: 生成配方",
                "parameters": {"screening_id": "str", "batch_size": "int, optional"}
            },
            "run_hardware_experiment": {
                "description": "Step 6: 运行实验",
                "parameters": {"recipe_group_id": "str"}
            },
            "bayesian_optimization": {
                "description": "Step 7: 贝叶斯优化",
                "parameters": {"result_group_id": "str", "historical_context": "list[str]"}
            }
        }
    
    def _get_system_prompt(self) -> str:
        return f"""你是电化学研发专家。按顺序执行工具：文献匹配→挖掘→扩增→筛选→配方→实验→优化。
可用工具：{json.dumps(self.tool_schemas, indent=2, ensure_ascii=False)}

格式：
Thought: 思考
Action: 工具名
Action Input: {{"参数": "值"}}
Observation: [结果]

完成时输出 Final Answer。"""

    async def run(self, user_requirement: str, max_steps: int = 25) -> Dict:
        self.conversation_history = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": f"研发需求: {user_requirement}"}
        ]
        
        execution_log = []
        used_tools = []
        
        for step in range(max_steps):
            response = self._generate_llm_response()
            execution_log.append({"step": step + 1, "response": response})
            
            thought, action, action_input = self._parse_response(response)
            
            if action == "Final Answer":
                return {"status": "success", "result": thought, "execution_log": execution_log}
            
            if action and action not in self.VALID_TOOLS:
                self._add_observation(f"Error: 无效工具'{action}'")
                continue
            
            if action:
                tool_output = await self._execute_tool(action, action_input)
                used_tools.append(action)
                self._add_observation(tool_output)
                
                if action == "bayesian_optimization":
                    try:
                        parsed = json.loads(tool_output)
                        if parsed.get("stop_signal"):
                            self._add_observation("已达标，准备总结...")
                            final_response = self._generate_llm_response()
                            return {
                                "status": "success",
                                "result": final_response,
                                "execution_log": execution_log
                            }
                    except:
                        pass
            else:
                self._add_observation("未识别到Action")
        
        return {"status": "timeout", "result": "达到最大步数", "execution_log": execution_log}

    def _generate_llm_response(self) -> str:
        text = self.tokenizer.apply_chat_template(
            self.conversation_history, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs, max_new_tokens=1024, temperature=0.3,
                do_sample=True, stop_strings=["Observation:"],
                tokenizer=self.tokenizer
            )
        
        response = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        if "Observation:" in response:
            response = response.split("Observation:")[0]
        self.conversation_history.append({"role": "assistant", "content": response})
        return response.strip()

    def _parse_response(self, response: str):
        thought_match = re.search(r"Thought:\s*(.*?)(?=Action:|Final Answer:|$)", response, re.DOTALL)
        action_match = re.search(r"Action:\s*(\w+)", response)
        input_match = re.search(r"Action Input:\s*(\{.*\})", response, re.DOTALL)
        
        thought = thought_match.group(1).strip() if thought_match else response
        
        if "Final Answer:" in response:
            return response.split("Final Answer:")[1].strip(), "Final Answer", None
        
        action = action_match.group(1).strip() if action_match else None
        action_input = None
        if input_match and action:
            try:
                action_input = json.loads(input_match.group(1))
            except:
                pass
        return thought, action, action_input

    async def _execute_tool(self, tool_name: str, parameters: Dict) -> str:
        if not hasattr(self.tools, tool_name):
            return json.dumps({"error": f"Tool {tool_name} not found"})
        try:
            return await getattr(self.tools, tool_name)(**parameters)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def _add_observation(self, content: str):
        self.conversation_history.append({"role": "user", "content": f"Observation: {content}"})

# ==============================================================================
# 8. API 层（整合两种模式）
# ==============================================================================

# 全局实例
message_bus = MessageBus()
state_manager = SecureStateManager()
rag_service: Optional[AdvancedRAGService] = None
master_agent: Optional[MasterAgent] = None
agents: Dict[str, BaseAgent] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_service, master_agent, agents
    
    logger.info("Initializing Multi-Agent System...")
    rag_service = AdvancedRAGService()
    
    # 初始化 Master
    master_agent = MasterAgent(message_bus, state_manager)
    await master_agent.start()
    
    # 初始化所有专业 Agent
    agents = {
        "requirement_analyst": RequirementAnalystAgent("requirement_analyst", message_bus, state_manager, data_manager, rag_service),
        "literature_retriever": LiteratureRetrieverAgent("literature_retriever", message_bus, state_manager, data_manager, rag_service),
        "knowledge_miner": KnowledgeMinerAgent("knowledge_miner", message_bus, state_manager, data_manager, rag_service),
        "molecule_designer": MoleculeDesignerAgent("molecule_designer", message_bus, state_manager, data_manager, rag_service),
        "formulation_engineer": FormulationEngineerAgent("formulation_engineer", message_bus, state_manager, data_manager, rag_service),
        "experiment_executor": ExperimentExecutorAgent("experiment_executor", message_bus, state_manager, data_manager, rag_service),
        "result_analyzer": ResultAnalyzerAgent("result_analyzer", message_bus, state_manager, data_manager, rag_service),
        "bayesian_optimizer": BayesianOptimizerAgent("bayesian_optimizer", message_bus, state_manager, data_manager, rag_service)
    }
    
    for agent in agents.values():
        await agent.start()
    
    logger.info("All agents started")
    yield
    
    logger.info("Shutting down...")
    for agent in agents.values():
        await agent.stop()

app = FastAPI(
    title="AI Electrolyte Multi-Agent System",
    description="多智能体自动化电解液研发系统 - 保留ReAct兼容模式",
    version="7.0.0-mas",
    lifespan=lifespan
)

class QueryRequest(BaseModel):
    question: str = Field(..., description="用户的电化学相关问题")
    top_k: int = Field(3, ge=1, le=10, description="返回的相关文献数量")
    generate_citations: bool = Field(True, description="是否生成引用来源")

class DeepResearchRequest(BaseModel):
    query: str = Field(..., description="研究问题")
    depth: int = Field(2, ge=1, le=3, description="探索深度")
    breadth: int = Field(3, ge=1, le=5, description="每轮探索的广度")
    context: Optional[str] = Field("", description="额外上下文")

class DeepResearchResponse(BaseModel):
    status: str
    query: str
    findings: List[Dict] = Field(default_factory=list)
    formatted_report: Optional[str] = None
    findings_id: Optional[str] = None

class AgentRequest(BaseModel):
    requirement: str
    max_cycles: Optional[int] = MAX_EXPERIMENT_CYCLES
    target_ce: Optional[float] = TARGET_METRIC_THRESHOLD
    mode: Optional[str] = Field("multi_agent", description="运行模式: multi_agent 或 react")

class AgentResponse(BaseModel):
    status: str
    result: str
    execution_trace: List[Dict]
    data_audit_log: List[str]
    experiment_dataset_id: Optional[str] = None

class ResearchStartRequest(BaseModel):
    requirement: str
    target_ce: float = 99.5
    max_iterations: int = 5
    mode: str = "multi_agent"  # multi_agent 或 react

# 保留的端点 1: Chat（轻量级问答）
@app.post("/chat")
async def chat_with_knowledge_base(request: QueryRequest):
    """保留的轻量级问答接口（直接RAG，不触发Agent工作流）"""
    if not rag_service:
        raise HTTPException(500, "Service not initialized")
    
    try:
        analysis = rag_service.analyze_research_requirement(request.question)
        papers = rag_service.retrieve_papers(request.question, analysis)
        
        if not papers:
            return {
                "answer": "在本地知识库中未找到相关文献。",
                "citations": [],
                "analysis": {"intent": analysis.target_application}
            }
        
        context = "\n\n".join([f"[{i+1}] {p['metadata'].get('title', 'Unknown')}\n{p['content'][:500]}" 
                              for i, p in enumerate(papers[:request.top_k])])
        
        prompt = f"""基于以下文献回答：
{context}

问题：{request.question}"""
        
        messages = [
            {"role": "system", "content": "你是电化学专家，基于文献严谨回答。"},
            {"role": "user", "content": prompt}
        ]
        
        answer = rag_service._generate_response(messages, max_new_tokens=1024, temperature=0.5)
        
        citations = []
        if request.generate_citations:
            for p in papers[:request.top_k]:
                citations.append({
                    "title": p["metadata"].get("title", "Unknown"),
                    "score": p.get("rerank_score", p["score"])
                })
        
        return {
            "answer": answer.strip(),
            "citations": citations,
            "analysis": {
                "detected_application": analysis.target_application,
                "constraints": analysis.key_constraints
            }
        }
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(500, str(e))

# 保留的端点 2: Deep Research（独立深度研究）
@app.post("/research/deep", response_model=DeepResearchResponse)
async def deep_research_endpoint(request: DeepResearchRequest):
    """独立的深度研究接口（可直接调用Deep Research引擎）"""
    if not rag_service:
        raise HTTPException(500, "Service not initialized")
    
    try:
        findings, metadata = await rag_service.deep_research_engine.deep_research(
            query=request.query,
            depth=request.depth,
            breadth=request.breadth,
            context=request.context
        )
        
        formatted = rag_service.citation_manager.format_findings_with_citations(findings)
        
        # 存储到数据中心
        findings_serializable = []
        for f in findings:
            fd = asdict(f)
            fd["source_locations"] = [asdict(sl) for sl in f.source_locations]
            findings_serializable.append(fd)
        
        findings_id = await data_manager.save(
            findings_serializable,
            f"Deep research: {request.query[:30]}",
            "deep_research_session"
        )
        
        return DeepResearchResponse(
            status="success",
            query=request.query,
            findings=findings_serializable[:20],
            formatted_report=formatted.get("content"),
            findings_id=findings_id
        )
        
    except Exception as e:
        logger.error(f"Deep research failed: {e}")
        raise HTTPException(500, str(e))

# 新建端点: Multi-Agent 工作流启动
@app.post("/research/start")
async def start_multi_agent_research(request: ResearchStartRequest):
    """启动多智能体协作研发工作流（新架构）"""
    if not master_agent:
        raise HTTPException(500, "Master not initialized")
    
    try:
        if request.mode == "react":
            # 向后兼容：使用原有的ReAct Agent
            agent = ResearchAgent(rag_service)
            result = await agent.run(request.requirement, max_steps=request.max_iterations * 8)
            audit = data_manager._audit_log[-50:]
            return {
                "status": result["status"],
                "result": result["result"],
                "execution_trace": result["execution_log"],
                "data_audit_log": [f"{e['action']}: {e['id']}" for e in audit],
                "mode": "react"
            }
        else:
            # 新架构：多智能体消息驱动
            corr_id = await master_agent.start_workflow(
                requirement=request.requirement,
                target_ce=request.target_ce,
                max_iter=request.max_iterations
            )
            
            # 后台运行
            asyncio.create_task(master_agent.wait_for_completion(corr_id))
            
            return {
                "correlation_id": corr_id,
                "status": "started",
                "message": "Multi-agent workflow initiated",
                "mode": "multi_agent"
            }
            
    except Exception as e:
        logger.error(f"Research start failed: {e}")
        raise HTTPException(500, str(e))

# 新建端点: 查询工作流状态
@app.get("/research/status/{correlation_id}")
async def get_research_status(correlation_id: str):
    """查询多智能体工作流状态"""
    try:
        ctx = await state_manager.get_context(correlation_id)
        if not ctx:
            raise HTTPException(404, "Correlation ID not found")
        
        return {
            "correlation_id": correlation_id,
            "status": ctx.get("state"),
            "current_iteration": ctx.get("current_iteration"),
            "max_iterations": ctx.get("max_iterations"),
            "target_ce": ctx.get("target_ce"),
            "requirement": ctx.get("requirement", "")[:100]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

# 保留的端点 3: 原有的 /run（ReAct模式，向后兼容）
@app.post("/run", response_model=AgentResponse)
async def run_research_agent(request: AgentRequest):
    """保留的ReAct Agent接口（向后兼容）"""
    if not rag_service:
        raise HTTPException(500, "Service not initialized")
    
    try:
        if request.mode == "multi_agent":
            # 转发到新的多智能体端点
            corr_id = await master_agent.start_workflow(request.requirement, request.target_ce, request.max_cycles)
            result = await master_agent.wait_for_completion(corr_id)
            return {
                "status": result["status"],
                "result": str(result),
                "execution_trace": [],
                "data_audit_log": []
            }
        
        # 原有ReAct模式
        agent = ResearchAgent(rag_service)
        result = await agent.run(
            user_requirement=request.requirement,
            max_steps=request.max_cycles * 8
        )
        
        audit_entries = data_manager._audit_log[-50:]
        dataset_id = await data_manager.export_dataset(request.requirement[:20])
        
        return AgentResponse(
            status=result["status"],
            result=result["result"],
            execution_trace=result["execution_log"],
            data_audit_log=[f"{e['action']}: {e['id']}" for e in audit_entries],
            experiment_dataset_id=dataset_id
        )
        
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")