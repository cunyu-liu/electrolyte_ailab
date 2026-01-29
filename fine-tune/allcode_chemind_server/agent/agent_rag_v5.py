import uvicorn
import torch
import logging
import re
import json
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Tuple, Set
import uuid
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field, asdict
import numpy as np
from contextlib import asynccontextmanager
from collections import defaultdict

#v5 是function calling（只有框架） + Deep Research。支持单独运行 chat功能。

# === 核心库 ===
from transformers import AutoModelForCausalLM, AutoTokenizer
from sentence_transformers import SentenceTransformer 
from FlagEmbedding import FlagReranker 
from pymilvus import connections, Collection
from elasticsearch import Elasticsearch

# ==============================================================================
# 【新增】Deep Research 专用数据结构与配置
# ==============================================================================

@dataclass
class SourceLocation:
    """精确原文定位信息"""
    doc_id: str
    doc_name: str
    page: int
    paragraph: int
    char_start: int
    char_end: int
    section_title: Optional[str] = None
    surrounding_context: Optional[str] = None  # 前后100字符用于验证
    bbox: Optional[Tuple[float, float, float, float]] = None  # PDF坐标

@dataclass
class ResearchFinding:
    """研究发现结构 - 包含溯源信息"""
    content: str                      # 核心发现文本
    source_locations: List[SourceLocation]  # 支持该发现的多个来源位置
    confidence: float                 # 置信度
    exploration_depth: int            # 探索深度（第几轮递归发现）
    query_path: List[str]             # 探索路径（从根查询到当前）
    chunk_ids: List[str]              # 关联的chunk ID

@dataclass
class ExplorationQuery:
    """探索查询结构"""
    query: str
    strategy: str                     # 策略：深挖/关联/溯源/对比
    target_concept: Optional[str] = None
    parent_finding_idx: Optional[int] = None  # 关联到哪个父发现

class DeepResearchConfig:
    """深度研究配置"""
    MAX_DEPTH = 3                     # 最大递归深度
    INITIAL_BREADTH = 4               # 初始广度
    MIN_BREADTH = 1                   # 最小广度
    TOP_K_PER_QUERY = 8               # 每个查询召回数量
    SIMILARITY_THRESHOLD = 0.85       # 信息增益判定阈值
    MAX_TOTAL_CHUNKS = 100            # 单任务最大处理chunk数防止爆炸

# ==============================================================================
# 1. 配置中心与常量定义
# ==============================================================================

# 硬件配置
if torch.cuda.is_available():
    DEVICE = "cuda"
    dtype = torch.float16
elif torch.backends.mps.is_available():
    DEVICE = "mps"
    dtype = torch.float32
else:
    DEVICE = "cpu"
    dtype = torch.float32

# 模型路径（请替换为你的实际路径）
LLM_MODEL_PATH = "/Users/liucunyu/.cache/modelscope/hub/models/Qwen/Qwen3-0.6B" 
EMBEDDING_MODEL_NAME = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/Xorbits/bge-m3"
RERANKER_MODEL_NAME = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/bge-reranker-v2-m3" 

# 向量数据库配置
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
MILVUS_COLLECTION_NAME = "electrolyte_papers_chunked"
MILVUS_VECTOR_FIELD = "embeddings"
MILVUS_TEXT_FIELD = "content"

# ES配置
ES_HOST = "http://127.0.0.1:9200"
ES_INDEX = "electrolyte_papers_index"

# 检索参数
SEARCH_TOP_K = 100
RERANK_TOP_K = 10  
MAX_CONTEXT_CHARS = 4000

# 实验参数
MAX_EXPERIMENT_CYCLES = 10
TARGET_METRIC_THRESHOLD = 99.5
BATCH_SIZE = 4

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==============================================================================
# 2. 数据结构定义 (强化类型安全)
# ==============================================================================

class ExperimentState(Enum):
    PENDING = "pending"
    DESIGNING = "designing"
    EXPERIMENTING = "experimenting" 
    OPTIMIZING = "optimizing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class StructuredRequirement:
    target_application: str
    key_constraints: Dict[str, Any]
    desired_properties: Dict[str, float]
    priority_weight: float = 1.0
    
@dataclass
class ExperimentRecipe:
    recipe_id: str
    components: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class ExperimentResult:
    result_id: str
    recipe_id: str
    metrics: Dict[str, float]
    raw_data_path: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

# ==============================================================================
# 【新增】3.5 深度研究引擎 (Deep Research Engine)
# ==============================================================================

class DeepResearchEngine:
    """
    本地知识库深度探索引擎
    实现：递归检索 + 查询扩展 + 信息增益控制 + 精确溯源
    """
    
    def __init__(self, rag_service: 'AdvancedRAGService'):
        self.rag = rag_service
        self.config = DeepResearchConfig()
        
    async def deep_research(
        self, 
        query: str, 
        depth: int = None, 
        breadth: int = None,
        context: str = ""  # 可选：上级提供的上下文
    ) -> Tuple[List[ResearchFinding], Dict]:
        """
        主入口：执行深度研究
        返回：(研究发现列表, 研究路径图)
        """
        depth = depth or self.config.MAX_DEPTH
        breadth = breadth or self.config.INITIAL_BREADTH
        
        # 初始化状态
        visited_chunks: Set[str] = set()
        all_learnings: List[ResearchFinding] = []
        exploration_graph = defaultdict(list)  # 记录探索路径
        
        # 根节点探索
        logger.info(f"[DeepResearch] Starting research: '{query}' | Depth: {depth}, Breadth: {breadth}")
        
        await self._explore_recursive(
            current_query=query,
            parent_queries=[query],
            current_depth=depth,
            current_breadth=breadth,
            visited_chunks=visited_chunks,
            accumulated_learnings=all_learnings,
            exploration_graph=exploration_graph,
            context=context
        )
        
        # 去重与排序
        unique_findings = self._deduplicate_findings(all_learnings)
        
        research_metadata = {
            "total_chunks_explored": len(visited_chunks),
            "total_findings": len(unique_findings),
            "exploration_paths": dict(exploration_graph),
            "query_coverage": self._calculate_coverage(unique_findings, query)
        }
        
        logger.info(f"[DeepResearch] Completed. Explored {len(visited_chunks)} chunks, "
                   f"found {len(unique_findings)} unique insights.")
        
        return unique_findings, research_metadata
    
    async def _explore_recursive(
        self,
        current_query: str,
        parent_queries: List[str],
        current_depth: int,
        current_breadth: int,
        visited_chunks: Set[str],
        accumulated_learnings: List[ResearchFinding],
        exploration_graph: Dict,
        context: str
    ):
        """递归探索核心"""
        
        if current_depth == 0 or len(visited_chunks) > self.config.MAX_TOTAL_CHUNKS:
            return
        
        logger.info(f"[DeepResearch] Depth {current_depth} | Query: {current_query[:50]}...")
        
        # 1. 多层次本地检索（调用RAG服务的增强版）
        search_results = await self._hybrid_search_with_meta(
            query=current_query,
            visited_filter=visited_chunks,
            top_k=self.config.TOP_K_PER_QUERY
        )
        
        if not search_results:
            logger.warning(f"No new results for query: {current_query[:50]}")
            return
        
        # 2. 分析并提取Learnings（使用LLM结构化提取）
        new_findings = await self._analyze_findings(
            chunks=search_results,
            query=current_query,
            depth=self.config.MAX_DEPTH - current_depth + 1,
            query_path=parent_queries
        )
        
        # 3. 信息增益检查（防止循环）
        novel_findings = self._filter_novel_findings(
            new_findings, 
            accumulated_learnings
        )
        
        if not novel_findings:
            logger.info(f"No novel information at depth {current_depth}, pruning branch.")
            return
            
        accumulated_learnings.extend(novel_findings)
        exploration_graph[current_query].extend([f.content[:30] for f in novel_findings])
        
        # 4. 生成子查询（探索扩展）
        if current_depth > 1 and current_breadth > 0:
            sub_queries = await self._generate_exploration_queries(
                current_findings=novel_findings,
                parent_query=current_query,
                breadth=max(current_breadth // 2, self.config.MIN_BREADTH),
                context=context
            )
            
            # 并行递归（控制并发）
            tasks = []
            for eq in sub_queries:
                new_path = parent_queries + [eq.query]
                task = self._explore_recursive(
                    current_query=eq.query,
                    parent_queries=new_path,
                    current_depth=current_depth - 1,
                    current_breadth=max(current_breadth // 2, self.config.MIN_BREADTH),
                    visited_chunks=visited_chunks,
                    accumulated_learnings=accumulated_learnings,
                    exploration_graph=exploration_graph,
                    context=context
                )
                tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks)
    
    async def _hybrid_search_with_meta(
        self, 
        query: str, 
        visited_filter: Set[str],
        top_k: int
    ) -> List[Dict]:
        """
        增强检索：确保返回包含精确定位的元数据
        """
        # 使用现有RAG服务的检索逻辑，但扩展元数据获取
        query_vec = self.rag.get_embedding(query)
        
        results = []
        try:
            # Milvus检索 - 请求额外字段用于溯源
            search_params = {"metric_type": "COSINE", "params": {"nprobe": 20, "ef": 16}}
            
            # 【注意】这里假设你的Milvus schema包含这些字段，如果没有需要调整
            output_fields = [
                MILVUS_TEXT_FIELD, "metadata", "doc_id", "page_num", 
                "paragraph_idx", "start_char", "end_char", "section_title"
            ]
            
            hits = self.rag.milvus_collection.search(
                data=[query_vec],
                anns_field=MILVUS_VECTOR_FIELD,
                param=search_params,
                limit=top_k * 2,  # 扩大候选池供后续过滤
                output_fields=output_fields
            )[0]
            
            for hit in hits:
                chunk_id = str(hit.id)
                if chunk_id in visited_filter:
                    continue
                
                entity = hit.entity
                # 标记为已访问
                visited_filter.add(chunk_id)
                
                # 构建包含精确定位的result
                result = {
                    "id": chunk_id,
                    "content": entity.get(MILVUS_TEXT_FIELD, ""),
                    "score": float(hit.score),
                    "doc_id": entity.get("doc_id", "unknown"),
                    "metadata": {
                        **(entity.get("metadata") or {}),
                        "page": entity.get("page_num", 0),
                        "paragraph": entity.get("paragraph_idx", 0),
                        "start_char": entity.get("start_char", 0),
                        "end_char": entity.get("end_char", 0),
                        "section_title": entity.get("section_title", ""),
                    }
                }
                results.append(result)
                
        except Exception as e:
            logger.error(f"Milvus search error in deep research: {e}")
            
        # 如果没有足够的元数据字段，降级处理但仍然尝试获取
        if not results:
            # 调用标准检索但添加标记
            standard_results = self.rag.retrieve_papers(query, StructuredRequirement("research", {}, {}))
            # 生成模拟的定位信息（如果没有真实数据）
            for r in standard_results:
                r["is_estimated_position"] = True  # 标记为估算位置
                r["doc_id"] = str(r.get("id", uuid.uuid4()))
            results = standard_results[:top_k]
            
        return results[:top_k]
    
    async def _analyze_findings(
        self, 
        chunks: List[Dict], 
        query: str,
        depth: int,
        query_path: List[str]
    ) -> List[ResearchFinding]:
        """
        使用LLM分析chunks，提取结构化发现
        """
        if not chunks:
            return []
        
        # 准备上下文
        chunks_text = "\n\n---\n\n".join([
            f"[{i+1}] {c['content'][:500]}..." 
            for i, c in enumerate(chunks)
        ])
        
        prompt = f"""分析以下文献片段，提取与问题相关的事实发现。请确保每个发现都有明确的来源支持。

研究问题：{query}
探索路径：{' -> '.join(query_path)}

文献片段：
{chunks_text}

请提取关键发现，每个发现应包含：
1. 简洁的事实陈述（不含推测）
2. 支持的片段编号（[1], [2]等）
3. 重要程度（0-1分）

输出JSON数组格式：
[
  {{
    "content": "发现的具体内容",
    "supporting_chunks": [1, 2],
    "confidence": 0.9,
    "key_concepts": ["概念1", "概念2"]
  }}
]"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.rag._generate_response(messages, max_new_tokens=1024, temperature=0.3)
            
            # 解析JSON
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                
                findings = []
                for item in parsed:
                    # 映射回具体的source locations
                    source_locs = []
                    chunk_ids = []
                    
                    for idx in item.get("supporting_chunks", []):
                        if 1 <= idx <= len(chunks):
                            chunk = chunks[idx-1]
                            meta = chunk.get("metadata", {})
                            
                            loc = SourceLocation(
                                doc_id=chunk.get("doc_id", str(chunk.get("id", "unknown"))),
                                doc_name=meta.get("title", meta.get("filename", "Unknown Document")),
                                page=meta.get("page", 0),
                                paragraph=meta.get("paragraph", 0),
                                char_start=meta.get("start_char", 0),
                                char_end=meta.get("end_char", 0),
                                section_title=meta.get("section_title"),
                                surrounding_context=chunk["content"][:200] + "..."
                            )
                            source_locs.append(loc)
                            chunk_ids.append(str(chunk.get("id")))
                    
                    finding = ResearchFinding(
                        content=item["content"],
                        source_locations=source_locs,
                        confidence=item.get("confidence", 0.5) * (chunk["score"] if chunk.get("score") else 0.5),
                        exploration_depth=depth,
                        query_path=query_path.copy(),
                        chunk_ids=chunk_ids
                    )
                    findings.append(finding)
                
                return findings
                
        except Exception as e:
            logger.error(f"Error analyzing findings: {e}")
            # 降级：直接返回原始chunk作为finding
            return [
                ResearchFinding(
                    content=c["content"][:300],
                    source_locations=[SourceLocation(
                        doc_id=str(c.get("id", "unknown")),
                        doc_name=c.get("metadata", {}).get("title", "Unknown"),
                        page=c.get("metadata", {}).get("page", 0),
                        paragraph=0, char_start=0, char_end=0
                    )],
                    confidence=c.get("score", 0.5),
                    exploration_depth=depth,
                    query_path=query_path,
                    chunk_ids=[str(c.get("id"))]
                ) for c in chunks[:3]
            ]
    
    def _filter_novel_findings(
        self, 
        new_findings: List[ResearchFinding], 
        existing: List[ResearchFinding]
    ) -> List[ResearchFinding]:
        """基于embedding相似度过滤重复发现"""
        if not existing:
            return new_findings
        
        # 简化为基于文本相似度的去重
        novel = []
        for nf in new_findings:
            is_duplicate = False
            for ef in existing:
                # 计算内容相似度（简单版）
                if self._text_similarity(nf.content, ef.content) > self.config.SIMILARITY_THRESHOLD:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                novel.append(nf)
        
        return novel
    
    def _text_similarity(self, t1: str, t2: str) -> float:
        """简单的文本相似度计算（基于共有词）"""
        words1 = set(t1.lower().split())
        words2 = set(t2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        return len(intersection) / max(len(words1), len(words2))
    
    async def _generate_exploration_queries(
        self,
        current_findings: List[ResearchFinding],
        parent_query: str,
        breadth: int,
        context: str
    ) -> List[ExplorationQuery]:
        """基于当前发现生成下级探索查询"""
        
        findings_text = "\n".join([
            f"- {f.content} (置信度: {f.confidence:.2f})"
            for f in current_findings[:5]  # 取Top5
        ])
        
        prompt = f"""基于以下研究发现，生成{breadth}个新的深度探索查询，用于在本地知识库中继续检索。

原始问题：{parent_query}
已有发现：
{findings_text}

上下文：{context}

策略指南：
1. **概念深挖**：某个术语需要更详细解释（如"具体机制是什么"）
2. **横向关联**：与发现相关的其他方法论/材料
3. **对比验证**：查找支持或反驳当前发现的证据
4. **溯源**：查找这些发现的原始实验数据/前提条件

请输出JSON数组：
[
  {{
    "query": "具体搜索语句",
    "strategy": "深挖/关联/对比/溯源",
    "target_concept": "涉及的核心概念"
  }}
]"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.rag._generate_response(messages, max_new_tokens=512, temperature=0.5)
            
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return [
                    ExplorationQuery(
                        query=p["query"],
                        strategy=p.get("strategy", "深挖"),
                        target_concept=p.get("target_concept"),
                        parent_finding_idx=None
                    ) for p in parsed[:breadth]
                ]
        except Exception as e:
            logger.error(f"Error generating exploration queries: {e}")
        
        # 降级：返回基于关键词的查询
        return [
            ExplorationQuery(
                query=f"{parent_query} 详细机制",
                strategy="深挖"
            ),
            ExplorationQuery(
                query=f"{parent_query} 对比分析",
                strategy="对比"
            )
        ][:breadth]
    
    def _deduplicate_findings(self, findings: List[ResearchFinding]) -> List[ResearchFinding]:
        """最终去重与排序"""
        seen = set()
        unique = []
        for f in findings:
            key = f.content[:50]  # 取前50字符作为指纹
            if key not in seen:
                seen.add(key)
                unique.append(f)
        
        # 按置信度和深度排序
        unique.sort(key=lambda x: (x.confidence, x.exploration_depth), reverse=True)
        return unique
    
    def _calculate_coverage(self, findings: List[ResearchFinding], original_query: str) -> float:
        """计算查询覆盖度（简化版）"""
        if not findings:
            return 0.0
        # 基于发现数量和深度估算
        return min(1.0, len(findings) * 0.1 + sum(f.exploration_depth for f in findings) * 0.05)

# ==============================================================================
# 【新增】3.6 精确引用管理器 (Citation Manager)
# ==============================================================================

class CitationManager:
    """
    管理研究发现的精确引用生成与原文定位
    """
    
    def __init__(self):
        self.citation_db: Dict[int, Dict] = {}
        
    def format_findings_with_citations(
        self, 
        findings: List[ResearchFinding],
        format_type: str = "markdown"
    ) -> Dict[str, Any]:
        """
        将研究发现格式化为带精确引用的报告
        """
        formatted_sections = []
        citation_map = {}
        
        for idx, finding in enumerate(findings, 1):
            # 构建引用标记
            citation_marks = []
            for loc_idx, loc in enumerate(finding.source_locations):
                cite_id = f"{idx}.{loc_idx+1}"
                citation_marks.append(f"[{cite_id}]")
                
                # 存储详细的定位信息
                citation_map[cite_id] = {
                    "doc_name": loc.doc_name,
                    "page": loc.page,
                    "paragraph": loc.paragraph,
                    "char_range": [loc.char_start, loc.char_end],
                    "section": loc.section_title,
                    "preview": loc.surrounding_context,
                    "exact_text": finding.content[:100] + "..."
                }
            
            # 构建格式化文本
            if format_type == "markdown":
                section = (
                    f"### {idx}. {finding.content[:100]}...\n\n"
                    f"{finding.content}\n\n"
                    f"**来源**: {', '.join(citation_marks)} | "
                    f"**探索深度**: {finding.exploration_depth} | "
                    f"**置信度**: {finding.confidence:.2f}\n"
                    f"**探索路径**: {' -> '.join(finding.query_path)}\n"
                )
            else:
                section = {
                    "index": idx,
                    "content": finding.content,
                    "citations": citation_marks,
                    "metadata": {
                        "depth": finding.exploration_depth,
                        "confidence": finding.confidence,
                        "path": finding.query_path
                    }
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
    
    def generate_clickable_citation(self, cite_id: str) -> Optional[Dict]:
        """生成前端可点击的引用链接"""
        if cite_id not in self.citation_db:
            return None
        
        info = self.citation_db[cite_id]
        return {
            "protocol": "localdoc://",
            "action": "highlight",
            "params": {
                "doc_id": info.get("doc_id"),
                "page": info.get("page"),
                "char_start": info.get("char_range", [0, 0])[0],
                "char_end": info.get("char_range", [0, 0])[1],
                "search_text": info.get("preview", "")[:50]  # 用于页面内搜索
            }
        }

# ==============================================================================
# 3. 黑盒数据中心 (核心安全隔离层)
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

# 全局数据中心实例
data_manager = ExperimentDataManager()

# ==============================================================================
# 4. RAG服务核心 - 【修改】集成深度研究能力
# ==============================================================================

class AdvancedRAGService:
    def __init__(self):
        logger.info(f"Initializing RAG Service on {DEVICE}")
        
        self.embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=DEVICE)
        self.reranker_model = FlagReranker(
            RERANKER_MODEL_NAME, 
            use_fp16=(DEVICE == "cuda"),
            device=DEVICE
        )
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            LLM_MODEL_PATH, 
            trust_remote_code=True
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            LLM_MODEL_PATH, 
            torch_dtype=dtype,
            device_map="auto",             
            trust_remote_code=True
        )
        
        self._connect_milvus()
        self._connect_es()
        
        # 【新增】初始化深度研究引擎
        self.deep_research_engine = DeepResearchEngine(self)
        self.citation_manager = CitationManager()

    def _connect_milvus(self):
        try:
            connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
            self.milvus_collection = Collection(MILVUS_COLLECTION_NAME)
            self.milvus_collection.load()
            schema_fields = [f.name for f in self.milvus_collection.schema.fields]
            self.has_metadata_json = "metadata" in schema_fields
            logger.info(f"Milvus connected. Fields: {schema_fields}")
        except Exception as e:
            logger.error(f"Milvus connection failed: {e}")
            raise

    def _connect_es(self):
        self.es_client = None
        self.use_es = False
        try:
            self.es_client = Elasticsearch([ES_HOST])
            if self.es_client.ping():
                self.use_es = True
                logger.info("Elasticsearch connected")
        except Exception as e:
            logger.warning(f"ES not available: {e}")

    def get_embedding(self, text: str) -> List[float]:
        return self.embed_model.encode(text, normalize_embeddings=True).tolist()

    def analyze_research_requirement(self, query: str) -> StructuredRequirement:
        prompt = f"""你是一个电解液研发专家。请深度分析以下需求，提取结构化信息。

需求描述: "{query}"

请提取以下信息并以JSON格式输出：
1. target_application: 应用场景（如"动力电池"、"消费电子产品"、"极端气候储能"）
2. key_constraints: 关键约束条件（如电压窗口、温度范围、安全要求等）
3. desired_properties: 期望性能指标（如电导率、库伦效率、循环寿命等）
4. priority_weight: 需求紧迫度(0.0-1.0)

输出格式：
{{
    "target_application": "...",
    "key_constraints": {{"voltage_window": "...", "temperature_range": "...": }},
    "desired_properties": {{"coulombic_efficiency": 99.5, "conductivity": 10.0}},
    "priority_weight": 0.9
}}
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
            logger.error(f"Failed to parse requirement: {e}")
            
        return StructuredRequirement(
            target_application="general",
            key_constraints={},
            desired_properties={},
            priority_weight=0.5
        )

    def _generate_response(self, messages: List[Dict], max_new_tokens: int = 512, temperature: float = 0.7) -> str:
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs, 
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=True
            )
        return self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)

    def retrieve_papers(self, query: str, requirement: StructuredRequirement) -> List[Dict]:
        query_vec = self.get_embedding(query)
        
        milvus_results = []
        try:
            search_params = {"metric_type": "COSINE", "params": {"nprobe": 20, "ef": 120}}
            # 【修改】请求更多字段用于溯源
            output_fields = [MILVUS_TEXT_FIELD, "metadata"]
            if self.has_metadata_json:
                output_fields.append("metadata")
            
            results = self.milvus_collection.search(
                data=[query_vec],
                anns_field=MILVUS_VECTOR_FIELD,
                param=search_params,
                limit=SEARCH_TOP_K,
                output_fields=output_fields
            )
            
            for hits in results:
                for hit in hits:
                    meta = hit.entity.get("metadata", {}) or {}
                    milvus_results.append({
                        "id": hit.id,
                        "content": hit.entity.get(MILVUS_TEXT_FIELD, ""),
                        "score": hit.score,
                        "source": "vector",
                        "metadata": meta,
                        "doc_id": str(hit.id)  # 【新增】确保有doc_id
                    })
        except Exception as e:
            logger.error(f"Milvus search error: {e}")

        es_results = []
        if self.use_es:
            try:
                es_body = {
                    "size": SEARCH_TOP_K,
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["content", "metadata.title^2", "metadata.authors"],
                            "type": "best_fields"
                        }
                    }
                }
                es_resp = self.es_client.search(index=ES_INDEX, body=es_body)
                for hit in es_resp["hits"]["hits"]:
                    source = hit["_source"]
                    es_results.append({
                        "id": hit["_id"],
                        "content": source.get("content", ""),
                        "score": hit["_score"],
                        "source": "keyword",
                        "metadata": source.get("metadata", {}),
                        "doc_id": str(hit["_id"])
                    })
            except Exception as e:
                logger.warning(f"ES search failed: {e}")

        fused_results = self._reciprocal_rank_fusion(milvus_results, es_results)
        ranked_results = self._rerank_results(query, fused_results)
        
        return ranked_results

    def _reciprocal_rank_fusion(self, vector_results: List[Dict], keyword_results: List[Dict], k: int = 60) -> List[Dict]:
        scores = {}
        documents = {}
        
        for rank, item in enumerate(vector_results):
            doc_id = item["id"]
            scores[doc_id] = scores.get(doc_id, 0) + 0.6 * (1.0 / (k + rank))
            documents[doc_id] = item
            
        for rank, item in enumerate(keyword_results):
            doc_id = item["id"]
            scores[doc_id] = scores.get(doc_id, 0) + 0.4 * (1.0 / (k + rank))
            if doc_id not in documents:
                documents[doc_id] = item
        
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [documents[doc_id] for doc_id, _ in sorted_docs]

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
            logger.error(f"Reranking failed: {e}")
            return candidates[:RERANK_TOP_K]
    
    # 【新增】深度研究主入口
    async def deep_research_query(
        self, 
        query: str, 
        depth: int = 3, 
        breadth: int = 3
    ) -> Dict[str, Any]:
        """
        对外提供的深度研究接口
        """
        findings, metadata = await self.deep_research_engine.deep_research(
            query=query,
            depth=depth,
            breadth=breadth
        )
        
        # 格式化带引用的结果
        formatted = self.citation_manager.format_findings_with_citations(
            findings, 
            format_type="markdown"
        )
        
        return {
            "findings": findings,
            "formatted_report": formatted,
            "metadata": metadata
        }

# ==============================================================================
# 【新增】5.5 深度研究工具 (供Agent调用)
# ==============================================================================

class DeepResearchTools:
    """
    为ReAct Agent提供的深度研究工具集
    替代原有的简单文献匹配，实现深度探索
    """
    
    def __init__(self, rag_service: AdvancedRAGService):
        self.rag = rag_service
        self.deep_engine = rag_service.deep_research_engine
        
    async def deep_local_research(
        self, 
        research_question: str, 
        depth: int = 2,
        context: str = ""
    ) -> str:
        """
        深度本地研究工具 - 递归探索向量数据库
        
        Args:
            research_question: 研究问题
            depth: 探索深度 (1-3)
            context: 上级上下文/约束条件
        """
        logger.info(f"[DeepResearchTool] Question: {research_question[:60]}...")
        
        try:
            findings, metadata = await self.deep_engine.deep_research(
                query=research_question,
                depth=depth,
                breadth=3,
                context=context
            )
            
            if not findings:
                return json.dumps({
                    "status": "no_results",
                    "message": "在本地知识库中未找到相关信息",
                    "suggestion": "尝试使用更广泛的关键词或检查拼写"
                }, ensure_ascii=False)
            
            # 格式化发现为可读的文本（带引用）
            formatted_output = []
            for i, finding in enumerate(findings[:10], 1):  # Top10
                sources = []
                for loc in finding.source_locations[:2]:  # 每个发现最多显示2个来源
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
            
            # 存储到数据中心供后续步骤使用
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
            return json.dumps({
                "status": "error",
                "message": str(e)
            }, ensure_ascii=False)
    
    async def extract_citation_context(self, findings_id: str, citation_idx: int) -> str:
        """
        获取指定引用的详细上下文（精确到原文位置）
        """
        try:
            findings_data = await data_manager.get(findings_id, "citation_tool")
            findings = [ResearchFinding(**f) for f in findings_data]
            
            if citation_idx < 1 or citation_idx > len(findings):
                return json.dumps({"error": "Invalid citation index"})
            
            finding = findings[citation_idx - 1]
            
            detailed_sources = []
            for loc in finding.source_locations:
                detailed_sources.append({
                    "document": loc.doc_name,
                    "page": loc.page,
                    "paragraph": loc.paragraph,
                    "character_range": f"{loc.char_start}-{loc.char_end}",
                    "section": loc.section_title,
                    "surrounding_text": loc.surrounding_context,
                    "exact_quote": finding.content[:200]
                })
            
            return json.dumps({
                "citation_id": citation_idx,
                "insight": finding.content,
                "confidence": finding.confidence,
                "source_locations": detailed_sources,
                "query_path": finding.query_path
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({"error": str(e)})

# ==============================================================================
# 5. 自研算法工具层 (Scientific Tools) - 【修改】集成深度研究
# ==============================================================================

class ScientificTools:
    def __init__(self, rag_service: AdvancedRAGService):
        self.rag = rag_service
        self.execution_log = []
        # 【新增】初始化深度研究工具
        self.deep_tools = DeepResearchTools(rag_service)
        
    async def literature_matching(self, requirement: str, structured_req: StructuredRequirement) -> str:
        """
        【增强】步骤1: 文献匹配现在使用深度研究引擎替代简单检索
        """
        logger.info(f"[Tool] Literature Deep Matching: {requirement[:50]}...")
        
        # 【关键修改】调用深度研究而非简单检索
        deep_result = await self.deep_tools.deep_local_research(
            research_question=requirement,
            depth=2,  # 2层递归足够发现关联文献
            context=json.dumps(structured_req.key_constraints, ensure_ascii=False)
        )
        
        parsed = json.loads(deep_result)
        
        if parsed.get("status") == "success":
            # 兼容原有接口格式
            findings_id = parsed.get("findings_id")
            
            # 转换为原有格式（保持向后兼容）
            paper_refs = parsed.get("key_insights", [])
            
            return json.dumps({
                "status": "success",
                "paper_refs_id": findings_id,  # 实际上是findings_id，但接口保持兼容
                "count": parsed.get("findings_count"),
                "top_candidates": [p["insight"][:50] + "..." for p in paper_refs[:3]],
                "deep_research_metadata": parsed.get("exploration_metadata"),
                "note": "已使用深度研究(Deep Research)模式遍历本地知识库，包含精确的原文引用定位"
            }, ensure_ascii=False)
        else:
            # 降级到简单检索
            logger.warning("Deep research failed, falling back to standard retrieval")
            papers = self.rag.retrieve_papers(requirement, structured_req)
            
            matched_papers = []
            for i, paper in enumerate(papers[:10]):
                meta = paper["metadata"]
                matched_papers.append({
                    "paper_id": str(paper["id"]),
                    "title": meta.get("title", "Unknown"),
                    "relevance_score": float(paper.get("rerank_score", 0.5))
                })
            
            paper_refs_id = await data_manager.save(
                matched_papers, 
                f"Standard literature matching for: {requirement[:30]}",
                "paper_refs"
            )
            
            return json.dumps({
                "status": "success",
                "paper_refs_id": paper_refs_id,
                "count": len(matched_papers),
                "note": "使用标准检索（深度研究失败后的降级）"
            }, ensure_ascii=False)

    async def literature_mining(self, paper_refs_id: str) -> str:
        logger.info(f"[Tool] Literature Mining: {paper_refs_id}")
        
        try:
            # 可能是findings_id（新格式）或paper_refs（旧格式）
            data = await data_manager.get(paper_refs_id, "literature_mining_tool")
            
            # 判断是否是深度研究发现格式
            if isinstance(data, list) and len(data) > 0 and "source_locations" in data[0]:
                # 从深度研究发现中提取化学实体
                findings = [ResearchFinding(**f) for f in data]
                combined_text = " ".join([f.content for f in findings])
            else:
                combined_text = str(data)
            
            # 使用LLM从深度研究发现中提取化学实体（更精准）
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
        """使用LLM从研究发现文本中提取化学实体"""
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
    "additives": ["...", "..."],
    "key_insights": ["...", "..."]
}}"""
        
        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.rag._generate_response(messages, max_new_tokens=512, temperature=0.2)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
        
        # 默认返回
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

    # 【新增】供Agent直接调用的深度研究工具
    async def deep_local_research(self, research_question: str, depth: int = 2, context: str = "") -> str:
        return await self.deep_tools.deep_local_research(research_question, depth, context)
    
    async def extract_citation_context(self, findings_id: str, citation_idx: int) -> str:
        return await self.deep_tools.extract_citation_context(findings_id, citation_idx)

# ==============================================================================
# 6. ReAct Agent核心架构 - 【修改】添加深度研究工具
# ==============================================================================

class ResearchAgent:
    VALID_TOOLS = [
        "literature_matching",
        "literature_mining", 
        "molecular_expansion",
        "property_prediction_and_screening",
        "generate_recipe",
        "run_hardware_experiment",
        "bayesian_optimization",
        "deep_local_research",      # 【新增】深度研究工具
        "extract_citation_context"  # 【新增】引用溯源工具
    ]
    
    DEPENDENCY_GRAPH = {
        "literature_mining": ["literature_matching", "deep_local_research"],  # 【修改】支持从深度研究开始
        "molecular_expansion": ["literature_mining"],
        "property_prediction_and_screening": ["molecular_expansion"],
        "generate_recipe": ["property_prediction_and_screening"],
        "run_hardware_experiment": ["generate_recipe"],
        "bayesian_optimization": ["run_hardware_experiment"],
        "extract_citation_context": ["deep_local_research"]  # 【新增】依赖关系
    }

    def __init__(self, rag_service: AdvancedRAGService):
        self.rag = rag_service
        self.tools = ScientificTools(rag_service)
        self.tokenizer = rag_service.tokenizer
        self.model = rag_service.model
        
        # 【修改】更新工具描述，加入深度研究
        self.tool_schemas = {
            "literature_matching": {
                "description": "Step 1: 深度文献匹配。使用递归检索在本地知识库中进行深度探索，比简单检索发现更多关联信息。",
                "parameters": {
                    "requirement": "str (用户原始需求描述)",
                    "structured_req_hint": "JSON字符串, optional (建议从用户输入提取的关键约束)"
                }
            },
            "deep_local_research": {  # 【新增】
                "description": "【增强版文献调研】使用Deep Research模式递归探索本地知识库，自动发现多层次关联文献并提供精确引用定位。",
                "parameters": {
                    "research_question": "str (研究问题)",
                    "depth": "int (探索深度 1-3, 默认2)",
                    "context": "str (可选上下文)"
                }
            },
            "extract_citation_context": {  # 【新增】
                "description": "获取指定研究发现的精确原文位置（页码、段落、字符范围）。",
                "parameters": {
                    "findings_id": "str (deep_local_research返回的findings_id)",
                    "citation_idx": "int (引用编号)"
                }
            },
            "literature_mining": {
                "description": "Step 2: 从深度研究发现中挖掘化学实体。",
                "parameters": {"paper_refs_id": "str (上一步返回的findings_id或paper_refs_id)"}
            },
            "molecular_expansion": {
                "description": "Step 3: 分子扩增算法。",
                "parameters": {"mining_result_id": "str"}
            },
            "property_prediction_and_screening": {
                "description": "Step 4: 性质预测模型筛选。",
                "parameters": {
                    "expansion_id": "str",
                    "target_properties": "JSON对象"
                }
            },
            "generate_recipe": {
                "description": "Step 5: 生成初始配方数组。",
                "parameters": {
                    "screening_id": "str",
                    "batch_size": "int, optional"
                }
            },
            "run_hardware_experiment": {
                "description": "Step 6: 驱动硬件执行实验。",
                "parameters": {"recipe_group_id": "str"}
            },
            "bayesian_optimization": {
                "description": "Step 7: 贝叶斯优化。",
                "parameters": {
                    "result_group_id": "str",
                    "historical_context": "list[str]"
                }
            }
        }
        
        self.conversation_history = []
        
    def _get_system_prompt(self) -> str:
        tools_desc = json.dumps(self.tool_schemas, indent=2, ensure_ascii=False)
        
        return f"""你是世界顶尖的电化学与AI专家，正在执行自动化电解液研发工作流。

【核心规则】
1. **优先使用深度研究**：调研阶段优先使用 `deep_local_research` 而非简单 `literature_matching`，以获得更全面的文献关联和精确引用
2. **严格顺序**：文献调研 -> 实体挖掘 -> 扩增 -> 筛选 -> 配方 -> 实验 -> 优化
3. **数据安全**：永远不要尝试猜测或输出配方的具体数值
4. **引用精确性**：使用 `extract_citation_context` 可查看任何研究发现的精确原文位置（页码、段落）

【可用工具】
{tools_desc}

【输出格式】
Thought: 当前步骤的思考
Action: 工具名称
Action Input: {{"参数名": "参数值"}}
Observation: [等待系统返回]

当任务完成时输出 Final Answer。"""

    async def run(self, user_requirement: str, max_steps: int = 25) -> Dict:
        logger.info(f"Starting Research Agent for requirement: {user_requirement}")
        
        self.conversation_history = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": f"研发需求: {user_requirement}\n\n请开始执行。建议首先使用 deep_local_research 进行深度文献调研。"}
        ]
        
        execution_log = []
        used_tools = []
        historical_optimizations = []
        
        for step in range(max_steps):
            logger.info(f"\n{'='*50}\nStep {step + 1}/{max_steps}\n{'='*50}")
            
            response = self._generate_llm_response()
            execution_log.append({"step": step + 1, "response": response})
            
            thought, action, action_input = self._parse_response(response)
            logger.info(f"Thought: {thought[:100]}...")
            logger.info(f"Action: {action}")
            
            if action == "Final Answer":
                return {
                    "status": "success",
                    "result": thought,
                    "execution_log": execution_log,
                    "steps_taken": step + 1
                }
            
            if action and action not in self.VALID_TOOLS:
                error_msg = f"Error: 无效工具'{action}'。可用工具: {self.VALID_TOOLS}"
                self._add_observation(error_msg)
                continue
                
            if action and action in self.DEPENDENCY_GRAPH:
                required_prev = self.DEPENDENCY_GRAPH[action]
                for req in required_prev:
                    if req not in used_tools:
                        error_msg = f"Error: 调用{action}前必须先调用{req}。请按顺序执行。"
                        self._add_observation(error_msg)
                        continue
            
            if action:
                tool_output = await self._execute_tool(action, action_input)
                used_tools.append(action)
                
                if action == "bayesian_optimization":
                    try:
                        parsed = json.loads(tool_output)
                        if not parsed.get("stop_signal") and "optimization_plan_id" in parsed:
                            historical_optimizations.append(parsed["optimization_plan_id"])
                        
                        if json.loads(tool_output).get("stop_signal"):
                            self._add_observation(tool_output)
                            self.conversation_history.append({
                                "role": "user", 
                                "content": "系统：已达到停止条件。请输出Final Answer总结整个研发过程。"
                            })
                            final_response = self._generate_llm_response()
                            execution_log.append({"step": step + 1, "final_summary": final_response})
                            return {
                                "status": "success",
                                "result": final_response,
                                "execution_log": execution_log,
                                "total_cycles": len(historical_optimizations) + 1
                            }
                    except:
                        pass
                
                self._add_observation(tool_output)
            else:
                self._add_observation("系统：未识别到Action。请使用格式：Action: 工具名\nAction Input: {...}")
        
        return {
            "status": "timeout",
            "result": "达到最大步数限制",
            "execution_log": execution_log
        }

    def _generate_llm_response(self) -> str:
        text = self.tokenizer.apply_chat_template(
            self.conversation_history, 
            tokenize=False, 
            add_generation_prompt=True
        )
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=1024,  # 【修改】增加token以支持复杂深度研究prompt
                temperature=0.3,
                do_sample=True,
                stop_strings=["Observation:"],
                tokenizer=self.tokenizer
            )
        
        response = self.tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:], 
            skip_special_tokens=True
        )
        
        if "Observation:" in response:
            response = response.split("Observation:")[0]
            
        self.conversation_history.append({"role": "assistant", "content": response})
        return response.strip()

    def _parse_response(self, response: str) -> Tuple[Optional[str], Optional[str], Optional[Dict]]:
        thought_match = re.search(r"Thought:\s*(.*?)(?=Action:|Final Answer:|$)", response, re.DOTALL)
        action_match = re.search(r"Action:\s*(\w+)", response)
        input_match = re.search(r"Action Input:\s*(\{.*\})", response, re.DOTALL)
        
        thought = thought_match.group(1).strip() if thought_match else response
        
        if "Final Answer:" in response:
            final_content = response.split("Final Answer:")[1].strip()
            return final_content, "Final Answer", None
            
        action = action_match.group(1).strip() if action_match else None
        
        action_input = None
        if input_match and action:
            try:
                action_input = json.loads(input_match.group(1))
            except json.JSONDecodeError:
                logger.error(f"Failed to parse Action Input: {input_match.group(1)}")
                
        return thought, action, action_input

    async def _execute_tool(self, tool_name: str, parameters: Dict) -> str:
        if not hasattr(self.tools, tool_name):
            return json.dumps({"error": f"Tool {tool_name} not found"})
        
        tool_func = getattr(self.tools, tool_name)
        logger.info(f"[Executing Tool] {tool_name} with params: {parameters}")
        
        try:
            result = await tool_func(**parameters)
            return result
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def _add_observation(self, content: str):
        self.conversation_history.append({
            "role": "user", 
            "content": f"Observation: {content}"
        })

# ==============================================================================
# 【新增】7.5 深度研究专用请求模型
# ==============================================================================

class DeepResearchRequest(BaseModel):
    query: str = Field(..., description="研究问题")
    depth: int = Field(2, ge=1, le=DeepResearchConfig.MAX_DEPTH, description="探索深度 (1:浅层, 2:标准, 3:深入, 4: exhaustive)")
    breadth: int = Field(3, ge=1, le=5, description="每轮探索的广度")
    context: Optional[str] = Field("", description="额外上下文/约束条件")
    return_format: str = Field("markdown", description="返回格式: markdown/json")

class DeepResearchResponse(BaseModel):
    status: str
    query: str
    findings: List[Dict] = Field(default_factory=list)
    formatted_report: Optional[str] = None
    citations_map: Dict[str, Any] = Field(default_factory=dict)
    stats: Dict[str, Any] = Field(default_factory=dict)
    findings_id: Optional[str] = None

# ==============================================================================
# 7. FastAPI接口层 - 【修改】添加深度研究端点
# ==============================================================================

rag_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_service
    logger.info("Starting up Advanced Electrolyte RAG Service with Deep Research...")
    rag_service = AdvancedRAGService()
    logger.info("Service initialized successfully")
    yield
    logger.info("Shutting down...")

app = FastAPI(
    title="AI Electrolyte Research Agent - Deep Research Edition",
    description="院士级自动化电解液研发Agent - 支持递归深度文献调研与精确引用溯源",
    version="6.0.0-deep-research",
    lifespan=lifespan
)

class QueryRequest(BaseModel):
    question: str

class AgentRequest(BaseModel):
    requirement: str
    max_cycles: Optional[int] = MAX_EXPERIMENT_CYCLES
    target_ce: Optional[float] = TARGET_METRIC_THRESHOLD
    
class AgentResponse(BaseModel):
    status: str
    result: str
    execution_trace: List[Dict]
    data_audit_log: List[str]
    experiment_dataset_id: Optional[str] = None

# 【新增】独立深度研究端点
@app.post("/research/deep", response_model=DeepResearchResponse)
async def deep_research_endpoint(request: DeepResearchRequest):
    """
    【核心新增接口】本地知识库深度研究
    
    功能：
    - 递归多轮检索本地向量数据库
    - 自动查询扩展与知识图谱遍历  
    - 精确的原文引用定位（页码、段落、字符范围）
    - 防止循环与信息增益控制
    
    与 /agent/run 的区别：
    - 此端点专用于纯文献深度调研
    - /agent/run 用于完整的研发闭环（文献→配方→实验）
    """
    if not rag_service:
        raise HTTPException(500, "Service not initialized")
    
    try:
        # 调用深度研究引擎
        findings, metadata = await rag_service.deep_research_engine.deep_research(
            query=request.query,
            depth=request.depth,
            breadth=request.breadth,
            context=request.context
        )
        
        # 格式化为带引用的报告
        formatted = rag_service.citation_manager.format_findings_with_citations(
            findings, 
            format_type=request.return_format
        )
        
        # 存储结果供后续引用查询
        findings_id = await data_manager.save(
            [asdict(f) for f in findings],
            f"Deep research: {request.query[:30]}",
            "deep_research_session"
        )
        
        # 转换为API响应格式
        findings_serializable = []
        for f in findings:
            fd = asdict(f)
            # 确保source_locations可序列化
            fd["source_locations"] = [asdict(sl) for sl in f.source_locations]
            findings_serializable.append(fd)
        
        return DeepResearchResponse(
            status="success",
            query=request.query,
            findings=findings_serializable[:20],  # 限制返回数量
            formatted_report=formatted.get("content"),
            citations_map=formatted.get("citations"),
            stats={
                **formatted.get("stats", {}),
                **metadata
            },
            findings_id=findings_id
        )
        
    except Exception as e:
        logger.error(f"Deep research failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# 【新增】原文定位查询端点
@app.get("/research/citation/{findings_id}/{citation_idx}")
async def get_citation_detail(findings_id: str, citation_idx: int):
    """
    获取指定引用的精确原文上下文
    
    返回：
    - 文档名称和页码
    - 在原文中的字符精确范围
    - 周围上下文文本（用于验证）
    - 所属章节标题
    """
    try:
        data = await data_manager.get(findings_id, "api_user")
        if not isinstance(data, list):
            raise HTTPException(404, "Invalid findings data")
        
        if citation_idx < 1 or citation_idx > len(data):
            raise HTTPException(404, "Citation index out of range")
        
        finding_data = data[citation_idx - 1]
        finding = ResearchFinding(**finding_data)
        
        return {
            "citation_id": citation_idx,
            "insight": finding.content,
            "confidence": finding.confidence,
            "exploration_path": finding.query_path,
            "source_locations": [asdict(loc) for loc in finding.source_locations],
            "total_sources": len(finding.source_locations)
        }
        
    except ValueError:
        raise HTTPException(404, "Findings not found")
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/run", response_model=AgentResponse)
async def run_research_agent(request: AgentRequest):
    if not rag_service:
        raise HTTPException(500, "Service not initialized")
    
    try:
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
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat_with_knowledge_base(request: QueryRequest):
    if not rag_service:
        raise HTTPException(500, "Service not initialized")
    
    analysis = rag_service.analyze_research_requirement(request.question)
    papers = rag_service.retrieve_papers(request.question, analysis)
    
    context = "\n\n".join([
        f"[{i+1}] {p['metadata'].get('title', 'Unknown')}\n{p['content'][:500]}"
        for i, p in enumerate(papers[:3])
    ])
    
    prompt = f"""基于以下文献回答：
{context}

问题：{request.question}"""
    
    messages = [
        {"role": "system", "content": "你是电化学专家，基于提供的文献引用回答问题。"},
        {"role": "user", "content": prompt}
    ]
    
    response = rag_service._generate_response(messages)
    
    return {
        "answer": response,
        "citations": [p["metadata"] for p in papers[:3]],
        "analysis": {
            "target_application": analysis.target_application,
            "key_constraints": analysis.key_constraints
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")