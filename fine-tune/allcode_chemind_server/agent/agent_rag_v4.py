import uvicorn
import torch
import logging
import re
import json
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Optional, Any, Tuple
import uuid
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import numpy as np
from contextlib import asynccontextmanager

#v4 是function calling

# === 核心库 ===
from transformers import AutoModelForCausalLM, AutoTokenizer
from sentence_transformers import SentenceTransformer 
from FlagEmbedding import FlagReranker 
from pymilvus import connections, Collection
from elasticsearch import Elasticsearch

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
MAX_EXPERIMENT_CYCLES = 10  # 防止无限循环的安全上限
TARGET_METRIC_THRESHOLD = 99.5  # 库伦效率目标值
BATCH_SIZE = 4  # 每轮实验并行配方数

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
    """需求结构化数据"""
    target_application: str  # 应用场景（消费电子/动力电池/储能）
    key_constraints: Dict[str, Any]  # 关键约束（电压窗口、温度范围等）
    desired_properties: Dict[str, float]  # 期望性能指标
    priority_weight: float = 1.0  # 需求优先级
    
@dataclass
class ExperimentRecipe:
    """配方数据结构 - 这是黑盒数据的核心"""
    recipe_id: str
    components: Dict[str, float]  # {分子名: 浓度}，仅算法可见，LLM不可见数值
    metadata: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class ExperimentResult:
    """实验结果结构"""
    result_id: str
    recipe_id: str
    metrics: Dict[str, float]  # 电化学性能指标
    raw_data_path: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

# ==============================================================================
# 3. 黑盒数据中心 (核心安全隔离层)
# ==============================================================================

class ExperimentDataManager:
    """
    数据中心 - 严格隔离LLM与实验数据
    所有数值型数据（配方、实验结果）必须经过此处封装
    LLM只能通过data_id引用数据，永远看不到具体的float值
    """
    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._audit_log: List[Dict] = []
        self._lock = asyncio.Lock()
        
    async def save(self, data: Any, description: str, data_type: str = "generic") -> str:
        """线程安全的数据存储"""
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
        """受控访问 - 记录谁在访问敏感数据"""
        async with self._lock:
            if data_id not in self._store:
                raise ValueError(f"Data ID {data_id} not found")
            
            # 如果LLM试图访问配方数据，记录警告
            if "recipe" in data_id or "vector" in data_id:
                self._audit_log.append({
                    "action": "ACCESS_ATTEMPT",
                    "id": data_id,
                    "accessor": accessor,
                    "timestamp": datetime.now().isoformat()
                })
                # 关键安全机制：LLM不能直接获取敏感数据
                if accessor == "llm_agent":
                    raise PermissionError("LLM Agent is prohibited from accessing raw numerical recipe data")
            
            return self._store[data_id]["payload"]

    def get_safe_summary(self, data_id: str) -> Dict:
        """
        提供给LLM的安全摘要 - 只含元数据，不含数值
        """
        if data_id not in self._store:
            return {"error": "Data not found"}
        
        entry = self._store[data_id]
        payload = entry["payload"]
        
        # 如果payload是列表（如多配方），返回数量信息
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
        """导出完整的实验数据集用于后期分析"""
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
# 4. RAG服务核心 (已有代码的优化版本)
# ==============================================================================

class AdvancedRAGService:
    def __init__(self):
        logger.info(f"Initializing RAG Service on {DEVICE}")
        
        # 1. 加载嵌入模型
        self.embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=DEVICE)
        
        # 2. 加载重排模型
        self.reranker_model = FlagReranker(
            RERANKER_MODEL_NAME, 
            use_fp16=(DEVICE == "cuda"),
            device=DEVICE
        )
        
        # 3. 加载大模型 - 用于需求分析和决策
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
        
        # 4. 连接数据库
        self._connect_milvus()
        self._connect_es()

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
            self.es_client = Elasticsearch(ES_HOST)
            if self.es_client.ping():
                self.use_es = True
                logger.info("Elasticsearch connected")
        except Exception as e:
            logger.warning(f"ES not available: {e}")

    def get_embedding(self, text: str) -> List[float]:
        return self.embed_model.encode(text, normalize_embeddings=True).tolist()

    def analyze_research_requirement(self, query: str) -> StructuredRequirement:
        """
        使用LLM深度解析用户需求，提取结构化信息
        """
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
            
        # 回退：简单解析
        return StructuredRequirement(
            target_application="general",
            key_constraints={},
            desired_properties={},
            priority_weight=0.5
        )

    def _generate_response(self, messages: List[Dict], max_new_tokens: int = 512, temperature: float = 0.7) -> str:
        """内部LLM调用封装"""
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
        """
        混合检索：向量检索 + 关键词检索 + Rerank
        """
        # 1. 生成查询向量
        query_vec = self.get_embedding(query)
        
        # 2. Milvus稠密检索
        milvus_results = []
        try:
            search_params = {"metric_type": "COSINE", "params": {"nprobe": 20, "ef": 64}}
            results = self.milvus_collection.search(
                data=[query_vec],
                anns_field=MILVUS_VECTOR_FIELD,
                param=search_params,
                limit=SEARCH_TOP_K,
                output_fields=[MILVUS_TEXT_FIELD, "metadata"]
            )
            
            for hits in results:
                for hit in hits:
                    meta = hit.entity.get("metadata", {}) or {}
                    milvus_results.append({
                        "id": hit.id,
                        "content": hit.entity.get(MILVUS_TEXT_FIELD, ""),
                        "score": hit.score,
                        "source": "vector",
                        "metadata": meta
                    })
        except Exception as e:
            logger.error(f"Milvus search error: {e}")

        # 3. ES稀疏检索（如果可用）
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
                        "metadata": source.get("metadata", {})
                    })
            except Exception as e:
                logger.warning(f"ES search failed: {e}")

        # 4. RRF融合 (Reciprocal Rank Fusion)
        fused_results = self._reciprocal_rank_fusion(milvus_results, es_results)
        
        # 5. 重排序（使用交叉编码器）
        ranked_results = self._rerank_results(query, fused_results)
        
        return ranked_results

    def _reciprocal_rank_fusion(self, vector_results: List[Dict], keyword_results: List[Dict], k: int = 60) -> List[Dict]:
        """RRF算法融合两种检索结果"""
        scores = {}
        documents = {}
        
        # 向量结果加权（权重0.6）
        for rank, item in enumerate(vector_results):
            doc_id = item["id"]
            scores[doc_id] = scores.get(doc_id, 0) + 0.6 * (1.0 / (k + rank))
            documents[doc_id] = item
            
        # 关键词结果加权（权重0.4）
        for rank, item in enumerate(keyword_results):
            doc_id = item["id"]
            scores[doc_id] = scores.get(doc_id, 0) + 0.4 * (1.0 / (k + rank))
            if doc_id not in documents:
                documents[doc_id] = item
        
        # 排序
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [documents[doc_id] for doc_id, _ in sorted_docs]

    def _rerank_results(self, query: str, candidates: List[Dict]) -> List[Dict]:
        """使用BGE重排序器精排"""
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

# ==============================================================================
# 5. 自研算法工具层 (Scientific Tools)
# ==============================================================================

class ScientificTools:
    """
    封装所有自研算法和硬件接口。
    天才程序员注：这里是核心IP的黑盒调用层。
    """
    def __init__(self, rag_service: AdvancedRAGService):
        self.rag = rag_service
        self.execution_log = []
        
    async def literature_matching(self, requirement: str, structured_req: StructuredRequirement) -> str:
        """
        步骤1: 文献匹配算法
        输入：用户原始需求 + 结构化需求
        输出：匹配的论文ID列表及关键信息
        """
        logger.info(f"[Tool] Literature Matching: {requirement[:50]}...")
        
        # 使用RAG检索相关论文
        papers = self.rag.retrieve_papers(requirement, structured_req)
        
        # 转换为标准格式供后续算法处理
        matched_papers = []
        for i, paper in enumerate(papers[:10]):  # 取Top10
            meta = paper["metadata"]
            matched_papers.append({
                "paper_id": str(paper["id"]),
                "title": meta.get("title", "Unknown"),
                "authors": meta.get("authors", "Unknown"),
                "year": meta.get("year", "Unknown"),
                "citations": meta.get("citations", 0),
                "abstract_snippet": paper["content"][:500],
                "relevance_score": float(paper.get("rerank_score", 0.5))
            })
        
        # 存储到数据中心
        paper_refs_id = await data_manager.save(
            matched_papers, 
            f"Literature matching results for: {requirement[:30]}",
            "paper_refs"
        )
        
        return json.dumps({
            "status": "success",
            "paper_refs_id": paper_refs_id,
            "count": len(matched_papers),
            "top_candidates": [p["title"] for p in matched_papers[:3]],
            "note": "请使用 paper_refs_id 调用下一步文献挖掘"
        }, ensure_ascii=False)

    async def literature_mining(self, paper_refs_id: str) -> str:
        """
        步骤2: 文献挖掘算法
        输入：论文引用ID
        输出：提取的电解液分子、配方线索
        """
        logger.info(f"[Tool] Literature Mining: {paper_refs_id}")
        
        # 从数据中心获取论文数据
        try:
            papers = await data_manager.get(paper_refs_id, "literature_mining_tool")
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
        
        # 模拟自研挖掘算法返回结果
        # 实际应调用你的C++/Python算法库，从文本中提取化学实体
        mined_data = {
            "salts": ["LiPF6", "LiFSI", "LiTFSI"],
            "solvents": ["EC", "DEC", "DMC", "EMC", "FEC", "VC"],
            "additives": ["VC", "FEC", "DTD", "PS"],
            "reported_combinations": [
                {"salt": "LiPF6", "solvents": ["EC", "DEC"], "ratio": [3, 7]},
                {"salt": "LiFSI", "solvents": ["DMC", "EMC"], "additives": ["VC"]}
            ],
            "key_insights": [
                "FEC添加剂显著提升高压稳定性",
                "LiFSI基电解液在极端温度下性能更优"
            ]
        }
        
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
                "solvents": mined_data["solvents"][:5],  # 简洁展示
                "additives": mined_data["additives"]
            },
            "note": "包含潜在协同效应的见解，请进行分子扩增"
        }, ensure_ascii=False)

    async def molecular_expansion(self, mining_result_id: str) -> str:
        """
        步骤3: 分子扩增算法
        输入：挖掘出的基础分子
        输出：扩展后的候选分子库
        """
        logger.info(f"[Tool] Molecular Expansion: {mining_result_id}")
        
        try:
            mined = await data_manager.get(mining_result_id, "molecular_expansion_tool")
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
        
        # 模拟分子扩增算法（基于类似性搜索、生成式AI等）
        expanded_molecules = {
            "base_salts": mined["salts"],
            "expanded_salts": mined["salts"] + ["LiBOB", "LiODFB"],  # 扩增类似物
            "base_solvents": mined["solvents"],
            "expanded_solvents": mined["solvents"] + ["FEC", "PC", "VC"],
            "functional_groups": ["fluorinated", "sulfone_based", "phosphate"],
            "search_space_size": 150  # 理论组合数
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
        """
        步骤4: 性质预测与筛选
        使用自研ML模型预测理化性质，过滤不符合要求的分子
        """
        logger.info(f"[Tool] Property Screening: {expansion_id}")
        
        try:
            library = await data_manager.get(expansion_id, "screening_tool")
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
        
        # 模拟预测模型（实际调用你的性质预测算法，如DFT+ML混合）
        # 此处简化：假设筛除了毒性高、稳定性差的分子
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
            "pass_rate": len(screening_results["candidates_passed"]) / len(screening_results.get("candidates_passed", []) + screening_results.get("filtered_out", [])),
            "top_candidates": top_candidates,
            "recommended_base": screening_results["optimal_combinations"][0]
        })

    async def generate_recipe(self, screening_id: str, batch_size: int = BATCH_SIZE) -> str:
        """
        步骤5: 配方生成算法（确定性，非LLM生成！）
        输入：筛选后的分子集合
        输出：具体的配方数组，存入黑盒数据中心
        
        【绝对安全保证】：
        - 本函数生成的数值型配方直接入库存储
        - 返回给Agent的只有data_id，LLM永远看不到具体float值
        """
        logger.info(f"[Tool] Recipe Generation: {screening_id}, Batch={batch_size}")
        
        try:
            screening = await data_manager.get(screening_id, "recipe_generator")
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
        
        # 严格确定性算法生成配方（严禁LLM介入数值生成）
        # 实际应调用你的配方组合优化算法
        recipes = []
        base_salt = "LiPF6"
        base_solvents = ["FEC", "DMC", "EC"]
        
        # 生成拉丁超立方采样或基于AI推荐的配方
        for i in range(batch_size):
            # 随机但系统性的探索（实际应为贝叶斯优化初始采样）
            salt_conc = 1.0 + np.random.uniform(-0.2, 0.2)  # 1M ± 0.2
            fec_ratio = np.random.uniform(0.05, 0.15)  # 5-15%
            dmc_ratio = np.random.uniform(0.4, 0.6)   # 40-60%
            ec_ratio = 1.0 - fec_ratio - dmc_ratio - (salt_conc * 0.1)  # 剩余
            
            # 归一化保证100%
            total = salt_conc * 0.1 + fec_ratio + dmc_ratio + ec_ratio
            norm_factors = [salt_conc * 0.1 / total, fec_ratio / total, dmc_ratio / total, ec_ratio / total]
            
            recipe_vec = {
                "salt_conc_m": float(salt_conc),
                "composition_vol_frac": {
                    "FEC": float(norm_factors[1]),
                    "DMC": float(norm_factors[2]),
                    "EC": float(norm_factors[3])
                },
                "additive_ppm": {"VC": 2000}  # 2000ppm VC
            }
            
            recipes.append(recipe_vec)
        
        # 关键安全步骤：数值配方存入黑盒，只暴露ID
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
        """
        步骤6: 硬件执行层
        输入：配方组ID
        处理：从黑盒中读取配方 -> 硬件执行 -> 返回结果ID
        """
        logger.info(f"[Tool] Hardware Experiment: {recipe_group_id}")
        
        try:
            # 关键：Agent无法读取这个get调用，因为它包含数值
            recipes = await data_manager.get(recipe_group_id, "hardware_interface")
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
        
        # 模拟硬件执行（实际调用你的实验设备API）
        results = []
        for i, recipe in enumerate(recipes):
            # 模拟实验：假设第二个配方效果最好（用于演示）
            ce = 98.5 + np.random.normal(0, 0.5)  # 库伦效率
            if i == 1:  # 模拟一个更好的配方
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
        
        # 结果也存入黑盒（LLM可读取summary，但不能直接打包原始数值用于推理）
        result_group_id = await data_manager.save(
            results,
            f"Experimental results for {recipe_group_id}",
            "experiment_results"
        )
        
        # 给Agent的报告（只有统计信息，不含原始数据）
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
        """
        步骤7: 贝叶斯优化闭环
        输入：实验结果组ID + 历史优化上下文
        输出：优化建议或停止信号
        """
        logger.info(f"[Tool] Bayesian Optimization: {result_group_id}")
        
        try:
            # 安全读取：这里在工具内部读取是允许的
            results = await data_manager.get(result_group_id, "bayesian_optimizer")
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
        
        # 提取性能指标
        ce_values = [r["coulombic_efficiency"] for r in results]
        best_ce = max(ce_values)
        
        # 停止条件检查（数值闭环，不经过LLM）
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
        
        # 如果未达标，生成下一轮优化建议
        # 实际调用你的高斯过程/贝叶斯优化库
        next_cycle_suggestions = {
            "target_metric_improvement": "increase_salt_conc",
            "exploration_direction": "increase_fec_ratio",
            "expected_improvement": 0.5,  # 预期提升0.5%
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
# 6. ReAct Agent核心架构 (实现严格的Function Calling协议)
# ==============================================================================

class ResearchAgent:
    """
    科研智能体 - 基于ReAct模式的手动Function Calling实现
    严格强制工具调用顺序，确保科学方法论正确性
    """
    
    VALID_TOOLS = [
        "literature_matching",
        "literature_mining", 
        "molecular_expansion",
        "property_prediction_and_screening",
        "generate_recipe",
        "run_hardware_experiment",
        "bayesian_optimization"
    ]
    
    # 工具依赖图：确保先调用前置工具
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
        
        # 工具描述（JSON Schema格式）
        self.tool_schemas = {
            "literature_matching": {
                "description": "Step 1: 在20万论文库中匹配相关文献。",
                "parameters": {
                    "requirement": "str (用户原始需求描述)",
                    "structured_req_hint": "JSON字符串, optional (建议从用户输入提取的关键约束)"
                }
            },
            "literature_mining": {
                "description": "Step 2: 从匹配文献中挖掘化学实体(分子、配方)。",
                "parameters": {"paper_refs_id": "str (上一步返回的paper_refs_id)"}
            },
            "molecular_expansion": {
                "description": "Step 3: 分子扩增算法，搜索类似物和功能类似物。",
                "parameters": {"mining_result_id": "str (上一步的mining_result_id)"}
            },
            "property_prediction_and_screening": {
                "description": "Step 4: 性质预测模型筛选，预测LUMO/HOMO/电导率等。",
                "parameters": {
                    "expansion_id": "str (上一步的expansion_id)",
                    "target_properties": "JSON对象, 如{'conductivity': 10, 'voltage': 4.5}"
                }
            },
            "generate_recipe": {
                "description": "Step 5: 生成初始配方数组(黑盒存储)。",
                "parameters": {
                    "screening_id": "str (上一步的screening_id)",
                    "batch_size": "int, optional (并行实验数量, 默认4)"
                }
            },
            "run_hardware_experiment": {
                "description": "Step 6: 驱动硬件执行实验并获取结果。",
                "parameters": {"recipe_group_id": "str (配方组ID, 由generate_recipe生成)"}
            },
            "bayesian_optimization": {
                "description": "Step 7: 贝叶斯优化分析结果并决定迭代策略。",
                "parameters": {
                    "result_group_id": "str (实验结果ID)",
                    "historical_context": "list[str], 之前的优化历史ID列表"
                }
            }
        }
        
        self.conversation_history = []
        
    def _get_system_prompt(self) -> str:
        """构建严格的System Prompt"""
        tools_desc = json.dumps(self.tool_schemas, indent=2, ensure_ascii=False)
        
        return f"""你是世界顶尖的电化学与AI专家，正在执行自动化电解液研发工作流。

【核心规则】
1. **严格顺序**：必须按照 文献匹配 -> 开采 -> 扩增 -> 筛选 -> 配方生成 -> 实验 -> 优化的顺序执行
2. **数据安全**：永远不要尝试猜测或输出配方的具体数值(如"EC: 30%")。配方数值是黑盒数据，你只能通过ID引用
3. **工具依赖**：不要跳步！调用工具前确保已获取前置工具返回的ID
4. **停止条件**：当贝叶斯优化返回 stop_signal: true 时，立即输出Final Answer并停止

【可用工具】
{tools_desc}

【输出格式 - 必须严格遵守】
Thought: 当前步骤的思考，分析当前状态
Action: 工具名称（必须从工具列表中选择）
Action Input: {{"参数名": "参数值", ...}}
Observation: [等待系统返回，不要自己编造]

【示例】
Thought: 用户需要高压电解液，首先执行文献匹配
Action: literature_matching
Action Input: {{"requirement": "设计5V高压电解液", "structured_req_hint": "{{\\"voltage\\": 5.0}}"}}

Thought: 已获得文献ID paper_xxx，现在提取化学实体
Action: literature_mining
Action Input: {{"paper_refs_id": "paper_xxx"}}

...（以此类推）

当任务完成时：
Thought: 已达成目标，库伦效率99.6%超过99.5%阈值
Final Answer: 研发成功！最终配方见 recipe_final_xxx，性能指标...
"""

    async def run(self, user_requirement: str, max_steps: int = 25) -> Dict:
        """
        执行完整研发工作流
        """
        logger.info(f"Starting Research Agent for requirement: {user_requirement}")
        
        self.conversation_history = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": f"研发需求: {user_requirement}\n\n请开始执行。"}
        ]
        
        execution_log = []
        used_tools = []
        historical_optimizations = []
        structured_req = None
        
        for step in range(max_steps):
            logger.info(f"\n{'='*50}\nStep {step + 1}/{max_steps}\n{'='*50}")
            
            # 1. 生成模型响应
            response = self._generate_llm_response()
            execution_log.append({"step": step + 1, "response": response})
            
            # 2. 解析响应
            thought, action, action_input = self._parse_response(response)
            logger.info(f"Thought: {thought[:100]}...")
            logger.info(f"Action: {action}")
            
            # 3. 检查是否完成
            if action == "Final Answer":
                return {
                    "status": "success",
                    "result": thought,
                    "execution_log": execution_log,
                    "steps_taken": step + 1
                }
            
            # 4. 验证工具调用合法性
            if action and action not in self.VALID_TOOLS:
                error_msg = f"Error: 无效工具'{action}'。可用工具: {self.VALID_TOOLS}"
                self._add_observation(error_msg)
                continue
                
            # 5. 检查工具依赖（防止跳步）
            if action and action in self.DEPENDENCY_GRAPH:
                required_prev = self.DEPENDENCY_GRAPH[action]
                for req in required_prev:
                    if req not in used_tools:
                        error_msg = f"Error: 调用{action}前必须先调用{req}。请按顺序执行。"
                        self._add_observation(error_msg)
                        continue
            
            # 6. 执行工具
            if action:
                tool_output = await self._execute_tool(action, action_input)
                used_tools.append(action)
                
                # 特殊处理：记录优化历史用于贝叶斯优化上下文
                if action == "bayesian_optimization":
                    try:
                        parsed = json.loads(tool_output)
                        if not parsed.get("stop_signal") and "optimization_plan_id" in parsed:
                            historical_optimizations.append(parsed["optimization_plan_id"])
                    except:
                        pass
                    
                    # 如果要求停止，强制结束循环
                    if json.loads(tool_output).get("stop_signal"):
                        self._add_observation(tool_output)
                        # 最后一步总结
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
                
                self._add_observation(tool_output)
            else:
                # 没有识别到Action，提示重新生成
                self._add_observation("系统：未识别到Action。请使用格式：Action: 工具名\nAction Input: {...}")
        
        return {
            "status": "timeout",
            "result": "达到最大步数限制",
            "execution_log": execution_log
        }

    def _generate_llm_response(self) -> str:
        """调用本地模型生成响应"""
        text = self.tokenizer.apply_chat_template(
            self.conversation_history, 
            tokenize=False, 
            add_generation_prompt=True
        )
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.3,  # 低温度确保遵循格式
                do_sample=True,
                stop_strings=["Observation:"],  # 在Observation前停止
                tokenizer=self.tokenizer
            )
        
        response = self.tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:], 
            skip_special_tokens=True
        )
        
        # 清理可能的幻觉
        if "Observation:" in response:
            response = response.split("Observation:")[0]
            
        self.conversation_history.append({"role": "assistant", "content": response})
        return response.strip()

    def _parse_response(self, response: str) -> Tuple[Optional[str], Optional[str], Optional[Dict]]:
        """解析LLM的ReAct格式响应"""
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
        """安全执行工具调用"""
        if not hasattr(self.tools, tool_name):
            return json.dumps({"error": f"Tool {tool_name} not found"})
        
        tool_func = getattr(self.tools, tool_name)
        logger.info(f"[Executing Tool] {tool_name} with params: {parameters}")
        
        try:
            # 调用异步工具函数
            result = await tool_func(**parameters)
            return result
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def _add_observation(self, content: str):
        """添加Observation到对话历史"""
        self.conversation_history.append({
            "role": "user", 
            "content": f"Observation: {content}"
        })

# ==============================================================================
# 7. FastAPI接口层
# ==============================================================================

# 全局服务实例
rag_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global rag_service
    logger.info("Starting up Advanced Electrolyte RAG Service...")
    rag_service = AdvancedRAGService()
    logger.info("Service initialized successfully")
    yield
    logger.info("Shutting down...")

app = FastAPI(
    title="AI Electrolyte Research Agent",
    description="院士级自动化电解液研发Agent - 支持文献挖掘、分子设计、硬件实验闭环",
    version="5.0.0",
    lifespan=lifespan
)

class QueryRequest(BaseModel):
    """RAG问答接口请求模型"""
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

@app.post("/agent/run", response_model=AgentResponse)
async def run_research_agent(request: AgentRequest):
    """
    主入口：自动化研发工作流
    
    流程：
    1. 需求结构化理解
    2. 多轮工具调用（设计→实验→优化循环）
    3. 返回最终结果与审计日志
    """
    if not rag_service:
        raise HTTPException(500, "Service not initialized")
    
    try:
        # 实例化Agent（每个请求独立状态）
        agent = ResearchAgent(rag_service)
        
        # 执行工作流
        result = await agent.run(
            user_requirement=request.requirement,
            max_steps=request.max_cycles * 8  # 每轮约8步
        )
        
        # 导出数据审计日志
        audit_entries = data_manager._audit_log[-50:]  # 最近50条
        
        # 导出完整实验数据集
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

@app.post("/agent/chat")
async def chat_with_knowledge_base(request: QueryRequest):
    """
    简易RAG问答接口（用于快速查询，不走完整Agent流程）
    """
    if not rag_service:
        raise HTTPException(500, "Service not initialized")
    
    # 使用原有RAG逻辑
    analysis = rag_service.analyze_research_requirement(request.question)
    papers = rag_service.retrieve_papers(request.question, analysis)
    
    # 构建Prompt上下文
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