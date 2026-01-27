import uvicorn
import torch
import logging
import re
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import uuid
from datetime import datetime

#v4 是做了function calling

# === 核心库 ===
from transformers import AutoModelForCausalLM, AutoTokenizer
from sentence_transformers import SentenceTransformer 
from FlagEmbedding import FlagReranker 
from pymilvus import connections, Collection
from elasticsearch import Elasticsearch

# ==============================================================================
# 1. 配置中心
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

# 模型路径
LLM_MODEL_PATH = "/Users/liucunyu/.cache/modelscope/hub/models/Qwen/Qwen3-0.6B" 
EMBEDDING_MODEL_NAME = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/Xorbits/bge-m3"
RERANKER_MODEL_NAME = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/bge-reranker-v2-m3" 

# Milvus 配置
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
MILVUS_COLLECTION_NAME = "electrolyte_papers_chunked"
MILVUS_VECTOR_FIELD = "embeddings"
MILVUS_TEXT_FIELD = "content" 

# Elasticsearch 配置
ES_HOST = "http://127.0.0.1:9200"
ES_INDEX = "electrolyte_papers_index"
ES_TEXT_FIELD = "content"

# 检索超参
SEARCH_TOP_K = 50
RERANK_TOP_K = 5  
MAX_CONTEXT_CHARS = 2500 

# ==============================================================================
# 2. RAG 服务核心类
# ==============================================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedRAGService:
    def __init__(self):
        logger.info(f"正在初始化服务，运行设备: {DEVICE}")
        
        self.embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=DEVICE)
        
        self.reranker_model = FlagReranker(
            RERANKER_MODEL_NAME, 
            use_fp16=(DEVICE == "cuda"),
            device=DEVICE
        )
        
        self.tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_PATH, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            LLM_MODEL_PATH, 
            torch_dtype=dtype,
            device_map="auto",             
            trust_remote_code=True
        )

        self._connect_milvus()
        self._connect_es()

    def _connect_milvus(self):
        try:
            connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
            self.collection = Collection(MILVUS_COLLECTION_NAME)
            self.collection.load()
            
            self.existing_fields = [field.name for field in self.collection.schema.fields]
            logger.info(f"Milvus Schema 字段检测: {self.existing_fields}")
            
            # 关键：检查是否存在 metadata JSON 字段
            self.has_metadata_json = "metadata" in self.existing_fields
            if not self.has_metadata_json:
                logger.warning("警告：未检测到 'metadata' 字段，基于 JSON 的高级过滤将无法使用！")
            
            logger.info("Milvus 连接成功并加载集合。")
        except Exception as e:
            logger.error(f"Milvus 连接失败: {e}")
            raise e

    def _connect_es(self):
        self.use_es = False
        self.es_client = None
        try:
            self.es_client = Elasticsearch(ES_HOST, request_timeout=2)
            if self.es_client.ping():
                self.use_es = True
                logger.info(f"Elasticsearch 就绪")
            else:
                logger.warning(f"Elasticsearch Ping 失败: 服务未响应。已降级模式。")
        except Exception as e:
            self.use_es = False
            logger.warning(f"Elasticsearch 初始化异常: {e}")

    def get_embedding(self, text: str) -> List[float]:
        return self.embed_model.encode(text, normalize_embeddings=True).tolist()

    # === 1. Query 理解 ===
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        解析用户 Query，提取年份和作者等信息。
        针对数据特征：年份会自动补全为 '2000.0' 格式。
        """
        prompt = (
            f"分析查询（涉及科研文献或硬件设施）：'{query}'。\n"
            "提取以下信息（如果不存在则为null）：\n"
            "1. year (年份，如 '2023')\n"
            "2. author (作者姓名，仅提取姓氏或全名)\n"
            "3. keywords (核心技术词、设备名称或型号)\n"
            "4. high_citation (bool, 用户是否暗示要找'经典'、'高引'、'核心'论文)\n"
            "必须输出严格的JSON格式: {{\"year\": ..., \"author\": ..., \"keywords\": ..., \"high_citation\": ...}}\n"
            "JSON:"
        )
        
        messages = [{"role": "user", "content": prompt}]
        text_input = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer([text_input], return_tensors="pt").to(self.model.device)
        
        try:
            with torch.no_grad():
                outputs = self.model.generate(**inputs, max_new_tokens=128, temperature=0.1)
            output_text = self.tokenizer.decode(outputs[0][len(inputs.input_ids[0]):], skip_special_tokens=True)
            
            json_match = re.search(r'\{.*\}', output_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                # --- 年份特殊处理 ---
                # 你的数据库是 "2000.0" 格式字符串，所以需要格式化
                if result.get('year'):
                    clean_year = re.sub(r'[^\d]', '', str(result['year'])) # 提取纯数字 2000
                    if len(clean_year) == 4:
                        result['year'] = f"{clean_year}.0" # 转换为 2000.0
                    else:
                        result['year'] = None # 格式不对则放弃过滤
                
                return result
        except Exception as e:
            logger.warning(f"LLM分析异常: {e}")
        
        return {"year": None, "keywords": query, "author": None, "high_citation": False}

    # === 辅助：构建 Milvus JSON 表达式 ===
    def _build_milvus_expr(self, filters: Dict[str, Any]) -> str:
        """
        针对 metadata JSON 字段构建查询表达式。
        Milvus JSON 语法：metadata["key"] == "value"
        """
        if not self.has_metadata_json:
            return ""

        expr_list = []
        
        # 1. 年份过滤 (JSON String)
        # 数据库存的是 "2000.0" (String)
        year_val = filters.get("year")
        if year_val:
            expr_list.append(f'metadata["year"] == "{year_val}"')

        # 2. 作者过滤 (JSON String + Like)
        # 数据库存的是 "Jürg Hafner; Ioannis Botonakis..."
        author_val = filters.get("author")
        if author_val:
            # Milvus 支持 JSON 内部字段的模糊匹配
            expr_list.append(f'metadata["authors"] like "%{author_val}%"')

        return " && ".join(expr_list) if expr_list else ""

    # === 2. Elasticsearch 检索 ===
    def _search_es_keyword(self, query: str, filters: Dict) -> List[Dict]:
        """
        ES 同样需要适配新的数据结构。假设 ES 中这些字段也是扁平化或者嵌套的。
        这里假设 ES 索引构建时也将 metadata 放入了顶层或者保留了结构。
        """
        if not self.use_es: return []
            
        must_clauses = [{"match": {ES_TEXT_FIELD: query}}]
        filter_clauses = []
        
        # 如果 ES 中也是嵌套在 metadata 里，需要用 nested query 或者 flattened dot notation
        # 假设 ES 索引已经扁平化处理了 (例如 metadata.year) 或者是顶层字段
        # 这里为了稳健，尝试匹配 metadata.year
        
        if filters.get('year'):
            # 尝试匹配 2000.0
            filter_clauses.append({"term": {"metadata.year.keyword": filters['year']}})
        
        if filters.get('author'):
            must_clauses.append({"match_phrase": {"metadata.authors": filters['author']}})
            
        body = {
            "size": SEARCH_TOP_K,
            "query": {"bool": {"must": must_clauses, "filter": filter_clauses}},
            "_source": [ES_TEXT_FIELD, "metadata"] 
        }
        
        try:
            resp = self.es_client.search(index=ES_INDEX, body=body)
            results = []
            for hit in resp["hits"]["hits"]:
                src = hit["_source"]
                meta = src.get("metadata", {}) or {}
                
                # ES 结果标准化
                results.append({
                    "content": src.get(ES_TEXT_FIELD, ""),
                    "doc_id": meta.get("doc_id"), # 优先用 metadata 里的真实 DOI/ID
                    "meta": {
                        "title": meta.get("title", "Unknown Title"),
                        "authors": meta.get("authors", "Unknown Authors"),
                        "year": meta.get("year", "Unknown Year"),
                        "citations": meta.get("citations", "0"),
                        "chunk_id": meta.get("chunk_index"), # 注意这里映射你的 chunk_index
                        "source": "ES"
                    }
                })
            return results
        except Exception as e:
            logger.warning(f"ES Search Error: {e}")
            return []
        
    def _expand_context(self, hits: List[Dict], window_size: int = 1) -> List[Dict]:
        """批量上下文扩展逻辑"""
        if not hits: return []
        query_specs = []
        expanded_hits_map = {}

        for idx, hit in enumerate(hits):
            meta = hit.get("meta", {})
            doc_id = hit.get("doc_id")
            chunk_id = meta.get("chunk_id")
            
            # 确保 chunk_id 有效
            if doc_id is not None and chunk_id is not None:
                try:
                    c_id = int(chunk_id)
                    target_ids = list(range(c_id - window_size, c_id + window_size + 1))
                    query_specs.append((doc_id, target_ids))
                except ValueError: pass
            expanded_hits_map[idx] = hit

        if not query_specs: return hits

        # 构建 metadata 级别的查询
        # expr: (metadata["doc_id"] == "X" && metadata["chunk_index"] in [1,2])
        expr_parts = []
        for doc_id, t_ids in query_specs:
            ids_str = ",".join(str(i) for i in t_ids)
            # 注意：doc_id 和 chunk_index 都在 metadata 里
            expr_parts.append(f'(metadata["doc_id"] == "{doc_id}" && metadata["chunk_index"] in [{ids_str}])')
        
        full_expr = " || ".join(expr_parts)

        try:
            res = self.collection.query(
                expr=full_expr,
                output_fields=[MILVUS_TEXT_FIELD, "metadata"],
                limit=len(query_specs) * (window_size * 2 + 1)
            )
            content_map = {}
            for item in res:
                meta = item.get("metadata", {})
                d_id = meta.get("doc_id")
                c_id = meta.get("chunk_index")
                content_map[(d_id, c_id)] = item.get(MILVUS_TEXT_FIELD, "")

            final_hits = []
            for idx, hit in enumerate(hits):
                meta = hit.get("meta", {})
                doc_id = hit.get("doc_id")
                chunk_id = meta.get("chunk_id")
                if doc_id is not None and chunk_id is not None:
                    try:
                        c_id = int(chunk_id)
                        target_ids = list(range(c_id - window_size, c_id + window_size + 1))
                        merged_parts = []
                        for tid in target_ids:
                            part = content_map.get((doc_id, tid))
                            if part: merged_parts.append(part)
                        if merged_parts:
                            hit["content"] = "\n".join(merged_parts)
                            hit["meta"]["is_expanded"] = True
                    except Exception: pass
                final_hits.append(hit)
            return final_hits
        except Exception as e:
            logger.error(f"批量上下文扩展查询失败: {e}")
            return hits

    # === 3. 混合检索主逻辑 ===
    def retrieve_and_rerank(self, query: str, analysis: Dict[str, Any]) -> List[Dict]:
        search_kw = analysis.get("keywords", query) or query
        candidates = [] 

        # --- B. Milvus 向量检索 ---
        query_vec = self.get_embedding(search_kw)
        expr = self._build_milvus_expr(analysis)
        logger.info(f"Milvus Query Expr: {expr}")
        
        target_output_fields = [MILVUS_TEXT_FIELD, "metadata"] 

        try:
            milvus_res = self.collection.search(
                data=[query_vec],
                anns_field=MILVUS_VECTOR_FIELD,
                param={"metric_type": "COSINE", "params": {"nprobe": 10}},
                limit=SEARCH_TOP_K,
                expr=expr if expr else None,
                output_fields=target_output_fields
            )
            
            if milvus_res and milvus_res[0]:
                for hit in milvus_res[0]:
                    entity = hit.entity
                    # 核心改动：从 metadata 中提取所有字段
                    meta_json = entity.get("metadata")
                    if not isinstance(meta_json, dict): meta_json = {}

                    candidates.append({
                        "content": entity.get(MILVUS_TEXT_FIELD),
                        "doc_id": meta_json.get("doc_id"), 
                        "meta": {
                            "title": meta_json.get("title", "Unknown Title"),
                            "authors": meta_json.get("authors", "Unknown Authors"),
                            "year": meta_json.get("year", "Unknown Year"),
                            "citations": meta_json.get("citations", "0"), # String
                            "chunk_id": meta_json.get("chunk_index"),
                            "source_pdf": meta_json.get("source_pdf")
                        }
                    })
        except Exception as e:
            logger.error(f"Milvus search error: {e}")

        # --- C. ES 检索 (如有) ---
        es_res = self._search_es_keyword(search_kw, {"year": year_filter})
        candidates.extend(es_res)

        # --- D. 去重 (优化版) ---
        # [修改点]：优先保留含有 chunk_id 的记录，以便后续上下文扩展
        unique_map = {}
        for c in candidates:
            content_key = c["content"]
            # 检查当前候选是否包含 chunk_id
            has_chunk_info = c.get("meta", {}).get("chunk_id") is not None
            
            if content_key not in unique_map:
                unique_map[content_key] = c
            else:
                # 如果已存在的记录没有 chunk_id，而当前记录有，则替换为当前记录
                existing_has_chunk = unique_map[content_key].get("meta", {}).get("chunk_id") is not None
                if has_chunk_info and not existing_has_chunk:
                    unique_map[content_key] = c

        unique_candidates = list(unique_map.values())
        
        if not unique_candidates: return []

        # --- E. Rerank ---
        docs_text = [c["content"] for c in unique_candidates]
        rerank_pairs = [[query, doc] for doc in docs_text]
        
        try:
            scores = self.reranker_model.compute_score(rerank_pairs, normalize=True)
            if isinstance(scores, float): scores = [scores]
            
            ranked_results = []
            for i, score in enumerate(scores):
                final_score = score
                meta = unique_candidates[i]["meta"]
                
                # High Citation 加权 (针对 String 类型的 "citations")
                if analysis.get("high_citation"):
                    cit_val = 0
                    try:
                        cit_raw = meta.get("citations", "0")
                        # 你的数据是 String "74"，这里转 int
                        cit_val = int(float(cit_raw)) # 先转 float 防止 "74.0" 报错
                    except: pass
                    
                    final_score += min(cit_val / 500.0, 0.2) # 适当调整权重分母
                
                ranked_results.append((unique_candidates[i], final_score))
                
            ranked_results.sort(key=lambda x: x[1], reverse=True)
            final_results = [item[0] for item in ranked_results[:RERANK_TOP_K]]
            
        except Exception as e:
            logger.error(f"Rerank failed: {e}")
            final_results = unique_candidates[:RERANK_TOP_K]

        logger.info("正在执行上下文窗口扩展...")
        expanded_results = self._expand_context(final_results, window_size=1) 
        return expanded_results

    # [修改点]：正则优化，支持 [1, 2] 格式
    def verify_citations(self, answer: str, context_count: int) -> Dict:
        # 匹配 [1], [1, 2], [1, 2, 3] 等格式
        raw_matches = re.findall(r'\[([\d,\s]+)\]', answer)
        citations = []
        for m in raw_matches:
            # 分割逗号，去除空格，转为整数
            nums = [int(n.strip()) for n in m.split(',') if n.strip().isdigit()]
            citations.extend(nums)
            
        valid = True
        warnings = []
        if not citations: warnings.append("警告：回答中未检测到引用。")
        for c in citations:
            if c < 1 or c > context_count:
                valid = False
                warnings.append(f"幻觉引用：[{c}]")
        return {"is_valid": valid, "citations_found": citations, "warnings": warnings}

class ExperimentDataManager:
    """
    黑盒数据中心：
    所有具体的配方数值、实验结果数值，全部存在这里。
    LLM 只能拿到 data_id，永远看不到具体的 float 数组。
    """
    def __init__(self):
        self._store = {} # 内存数据库 {data_id: data_payload}
        self._audit_log = [] # 审计日志

    def save(self, data: Any, description: str) -> str:
        """保存数据，返回 ID"""
        data_id = f"data_{str(uuid.uuid4())[:8]}"
        timestamp = datetime.now().isoformat()
        
        entry = {
            "id": data_id,
            "timestamp": timestamp,
            "description": description,
            "payload": data
        }
        self._store[data_id] = entry
        
        # 写入审计日志
        self._audit_log.append({
            "action": "SAVE",
            "id": data_id,
            "desc": description,
            "timestamp": timestamp
        })
        return data_id

    def get(self, data_id: str) -> Any:
        """根据 ID 获取数据"""
        if data_id not in self._store:
            raise ValueError(f"Data ID {data_id} not found in Experiment Manager.")
        return self._store[data_id]["payload"]

    def dump_audit_log(self, filename="experiment_audit.json"):
        """导出审计合规文件"""
        with open(filename, "w", encoding='utf-8') as f:
            json.dump(self._audit_log, f, indent=2, ensure_ascii=False)

# 初始化全局管理器
data_manager = ExperimentDataManager()
# ==================
# 4. 科研 Agent 核心架构 (新增)
# ==================
class ScientificTools:
    """
    封装所有自研算法和硬件接口。
    天才程序员注：这里是核心IP的黑盒调用层，实际部署时连接你的C++/CUDA后端。
    """
    def __init__(self, rag_service: AdvancedRAGService):
        self.rag = rag_service

    def literature_matching(self, requirement: str) -> str:
        """
        调用自研文献匹配算法。
        这里复用 RAG 的检索能力，但逻辑上属于 Tool 的一部分。
        """
        logger.info(f"[Tool] 正在执行文献匹配: {requirement[:20]}...")
        # 复用 RAG 的检索逻辑，获取 Top Docs
        analysis = self.rag.analyze_query(requirement)
        docs = self.rag.retrieve_and_rerank(requirement, analysis)
        # 模拟：将检索到的 Doc ID 传给下游算法
        if not docs:
            return json.dumps({"status": "failed", "reason": "No papers found"})
        
        # 假设返回了最相关的论文 ID 和摘要
        matched_info = [
            {"id": d.get("doc_id", "N/A"), "title": d.get("meta", {}).get("title"), "content": d.get("content")[:200]} 
            for d in docs[:3]
        ]
        return json.dumps(matched_info, ensure_ascii=False)

    def literature_mining(self, paper_ids: str) -> str:
        """
        调用自研文献挖掘算法。从匹配的论文中提取电解液信息。
        """
        logger.info(f"[Tool] 正在挖掘论文数据: {paper_ids}")
        # 模拟：自研算法从非结构化文本中提取出的分子结构
        # 实际应调用你的 Python/C++ 模块
        extracted_data = {
            "molecules": ["LiPF6", "EC", "DMC", "FEC", "VC"],
            "base_formula_ratio": {"EC": 30.0, "DMC": 70.0, "LiPF6": 12.5} # 摩尔比/质量比
        }
        return json.dumps(extracted_data)

    def molecular_screening(self, molecules: Any) -> str: # 修改参数类型标注为 Any
        """
        调用自研分子扩增算法 + 性质预测算法。
        """
        logger.info(f"[Tool] 分子扩增与筛选中: {molecules}")
        
        # 修复点：增加类型检查，防止重复调用 json.loads
        if isinstance(molecules, str):
            try:
                mol_list = json.loads(molecules)
            except json.JSONDecodeError:
                return json.dumps({"status": "error", "reason": "Invalid JSON string in molecules"})
        else:
            mol_list = molecules # 如果已经是 list/dict，直接使用
            
        # 模拟：扩增出了新的添加剂，并预测了 LUMO/HOMO 能级
        screened_result = {
            "selected_solvents": ["EC", "DMC"],
            "selected_salt": ["LiPF6"],
            "optimized_additives": ["FEC", "PS"], 
            "predicted_properties": {"oxidation_potential": 4.5, "conductivity": 10.2}
        }
        return json.dumps(screened_result)

    def generate_initial_recipe(self, insight_id: str) -> str:
        """
        [Hard Science] 确定性算法生成配方。
        严禁 LLM 自己编配方。
        """
        constraints = data_manager.get(insight_id)
        
        # 调用自研算法（非 LLM）生成初始配方
        # 模拟：生成了 3 个并行实验配方 (Batch Processing)
        initial_recipes = [
            {"id": "batch_0_sample_A", "vector": [12.0, 30.0, 58.0]},
            {"id": "batch_0_sample_B", "vector": [15.0, 25.0, 60.0]},
            {"id": "batch_0_sample_C", "vector": [10.0, 35.0, 55.0]}
        ]
        
        # 存入数据中心，LLM 只知道这里有一组配方，不知道具体数字
        recipe_group_id = data_manager.save(initial_recipes, "Batch 0 Initial Recipes")
        
        return json.dumps({
            "recipe_group_id": recipe_group_id,
            "count": 3,
            "message": "已生成 3 组初始配方，准备进行并行实验。"
        })

    def run_hardware_experiment(self, recipe_group_id: str) -> str:
        """
        [Experiment] 硬件执行。
        LLM 传递 ID -> 硬件读取具体数值 -> 硬件执行 -> 存回结果 ID
        """
        recipes = data_manager.get(recipe_group_id)
        results = []
        
        print(f"    >>> [硬件接口] 正在并行执行 {len(recipes)} 组实验...")
        # 模拟硬件执行
        for rec in recipes:
            # 这里的 vector 是 float，完全没有经过 LLM 的文本处理，保证精度
            vec = rec["vector"] 
            # 模拟结果：假设第一个配方最好
            eff = 99.0 if rec["id"] == "batch_0_sample_A" else 98.0
            results.append({
                "recipe_id": rec["id"],
                "vector": vec,
                "metrics": {"coulombic_efficiency": eff}
            })
            
        result_group_id = data_manager.save(results, f"Results for {recipe_group_id}")
        
        return json.dumps({
            "result_group_id": result_group_id,
            "summary": "实验完成。最高效率 99.0%。请决策是否继续优化。"
        })

    def bayesian_optimization(self, result_group_id: str) -> str:
        """
        [Optimization] 贝叶斯优化闭环。
        数值闭环完全在 Python 侧，LLM 只负责看结果决定是否 Stop。
        """
        results = data_manager.get(result_group_id)
        
        # 提取数据喂给贝叶斯模型 (自研算法)
        best_sample = max(results, key=lambda x: x["metrics"]["coulombic_efficiency"])
        current_best_eff = best_sample["metrics"]["coulombic_efficiency"]
        
        # 判定逻辑（数值闭环）
        if current_best_eff >= 99.5:
            return json.dumps({
                "stop_signal": True,
                "best_recipe_id": best_sample["recipe_id"],
                "message": f"达到目标 (当前 {current_best_eff}%)。停止迭代。"
            })
        
        # 如果没达标，生成下一轮 Batch
        next_batch_recipes = [
            {"id": "batch_1_sample_A", "vector": [12.5, 29.5, 58.0]}, # 微调
            {"id": "batch_1_sample_B", "vector": [12.0, 31.0, 57.0]}
        ]
        next_group_id = data_manager.save(next_batch_recipes, "Batch 1 Optimized Recipes")
        
        return json.dumps({
            "stop_signal": False,
            "next_recipe_group_id": next_group_id,
            "message": f"当前最佳 {current_best_eff}%，未达标。已生成下一轮优化配方。"
        })

class ResearchAgent:
    """
    智能体大脑。实现手动 Function Calling 和 状态管理。
    """
    def __init__(self, rag_service: AdvancedRAGService):
        self.rag_service = rag_service
        self.tools = ScientificTools(rag_service)
        self.tokenizer = rag_service.tokenizer
        self.model = rag_service.model
        
        # 定义工具描述 (System Prompt 核心)
        self.tool_definitions = [
            {
                "name": "literature_matching",
                "description": "根据用户需求在论文库中匹配相关文献。",
                "parameters": {"type": "object", "properties": {"requirement": {"type": "string"}}}
            },
            {
                "name": "literature_mining",
                "description": "从匹配的论文ID中挖掘分子和配方信息。",
                "parameters": {"type": "object", "properties": {"paper_ids": {"type": "string"}}}
            },
            {
                "name": "molecular_screening",
                "description": "对分子进行扩增和性质预测筛选。",
                "parameters": {"type": "object", "properties": {"molecules": {"type": "string"}}}
            },
            {
                "name": "generate_initial_recipe",
                "description": "生成初始电解液配方数组。",
                "parameters": {"type": "object", "properties": {"screening_result": {"type": "string"}}}
            },
            {
                "name": "run_hardware_experiment",
                "description": "驱动硬件执行实验。",
                "parameters": {"type": "object", "properties": {"recipe_vector": {"type": "array"}}}
            },
            {
                "name": "bayesian_optimization",
                "description": "根据实验结果组ID进行贝叶斯优化。",
                "parameters": {"type": "object", "properties": {
                    "result_group_id": {"type": "string", "description": "上一步 run_hardware_experiment 返回的 result_group_id"}
                }}
            }
        ]

    def _build_system_prompt(self):
        tools_json = json.dumps(self.tool_definitions, ensure_ascii=False, indent=2)
        return (
            "你是一个世界顶尖的电解液研发智能体。你必须严格按照以下流程工作：\n"
            "1. 设计阶段：分析需求 -> literature_matching -> literature_mining -> molecular_screening -> generate_initial_recipe\n"
            "2. 实验阶段：拿到配方 -> run_hardware_experiment\n"
            "3. 闭环优化：分析结果 -> bayesian_optimization -> 循环实验，直到满足需求。\n\n"
            "你可以使用以下工具：\n"
            f"{tools_json}\n\n"
            "思考格式：\n"
            "Thought: 思考当前步骤...\n"
            "Action: 工具名称\n"
            "Action Input: 工具参数(JSON格式)\n"
            "Observation: 工具返回结果\n"
            "... (重复直到完成)\n"
            "Final Answer: 最终产出\n"
            "注意：必须严格按顺序调用工具，严禁跳步。"
        )

    def run(self, user_requirement: str, max_steps: int = 25):
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": f"开始电解液研发任务，需求：{user_requirement}"}
        ]
        
        history_log = [] # 记录整个过程
        
        current_step = 0
        while current_step < max_steps:
            # 1. 模型推理
            prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = self.tokenizer([prompt], return_tensors="pt").to(self.model.device)
            
            with torch.no_grad():
                # 修复点：添加 tokenizer 参数以支持 stop_strings
                outputs = self.model.generate(
                    **inputs, 
                    max_new_tokens=512, 
                    temperature=0.1, 
                    stop_strings=["Observation:"],
                    tokenizer=self.tokenizer  # <--- 新增此行
                )
                response_text = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            
            # 清理可能产生的幻觉后缀
            if "Observation:" in response_text:
                response_text = response_text.split("Observation:")[0]
            
            messages.append({"role": "assistant", "content": response_text})
            history_log.append(f"Step {current_step}: {response_text}")
            logger.info(f"Agent 思考:\n{response_text}")

            # 2. 解析 Action
            action_match = re.search(r"Action:\s*(\w+)", response_text)
            input_match = re.search(r"Action Input:\s*(\{.*\})", response_text, re.DOTALL)

            if action_match and input_match:
                tool_name = action_match.group(1).strip()
                try:
                    tool_args = json.loads(input_match.group(1).strip())
                except json.JSONDecodeError:
                    tool_output = "Error: Action Input is not valid JSON."
                    self._append_observation(messages, tool_output)
                    continue

                # 3. 执行工具
                tool_output = self._execute_tool(tool_name, tool_args)
                
                # 4. 将结果反馈给模型
                self._append_observation(messages, tool_output)
                
                # 特殊逻辑：如果是贝叶斯优化，检查是否需要终止
                if tool_name == "bayesian_optimization":
                    res_dict = json.loads(tool_output)
                    # 工具返回的是 stop_signal
                    if res_dict.get("stop_signal", False):
                        return {
                            "status": "success",
                            "final_recipe": res_dict.get("best_recipe_id"), # 工具返回的是 best_recipe_id
                            "log": history_log,
                            "message": res_dict.get("message", "优化完成")
                        }
            elif "Final Answer:" in response_text:
                return {"status": "finished", "result": response_text, "log": history_log}
            else:
                # 增加一个计数器，如果连续 3 次格式错误则强制终止任务
                error_count = getattr(self, '_error_count', 0) + 1
                self._error_count = error_count
                if error_count > 3:
                    return {"status": "failed", "reason": "Agent 格式多次错误，无法继续", "log": history_log}
                
                self._append_observation(messages, "System Warning: Invalid Format. Use Action: and Action Input: or Final Answer:")
            
            current_step += 1
            
        return {"status": "timeout", "log": history_log}

    def _execute_tool(self, name: str, args: Dict) -> str:
        try:
            func = getattr(self.tools, name, None)
            if not func:
                return f"Error: Tool {name} not found."
            
            # 自动化参数注入：直接将解析后的 dict 作为关键字参数传入
            # 这样只要 LLM 生成的 JSON Key 和函数参数名一致即可
            return func(**args)
            
        except TypeError as e:
            # 针对参数不匹配（如 LLM 多传或少传参数）的友好报错
            logger.error(f"参数匹配失败: {e}")
            return f"Error: 传入工具 {name} 的参数不匹配，请检查 Action Input。内容: {str(e)}"
        except Exception as e:
            logger.error(f"工具执行异常: {e}")
            return f"Error executing {name}: {str(e)}"

    def _append_observation(self, messages, output):
        logger.info(f"工具输出: {output[:100]}...")
        messages.append({"role": "user", "content": f"Observation: {output}"})



# 注意：保留原有的 /chat 接口用于普通问答


# ==============================================================================
# 3. FastAPI 接口
# ==============================================================================

app = FastAPI(title="Metadata-Aware RAG Service")
rag_service = None

class AgentRequest(BaseModel):
    requirement: str

@app.post("/agent/run")
def run_agent(request: AgentRequest):
    if not rag_service: 
        raise HTTPException(500, "Service initializing")
    
    # 实例化 Agent (每次请求新建或复用视状态管理需求而定，这里新建以隔离状态)
    agent = ResearchAgent(rag_service)
    
    try:
        result = agent.run(request.requirement)
        return result
    except Exception as e:
        logger.error(f"Agent 运行异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    global rag_service
    rag_service = AdvancedRAGService()

class QueryRequest(BaseModel):
    question: str
    
class QueryResponse(BaseModel):
    answer: str
    context_used: List[Dict] 
    verification: Dict
    analysis_debug: Dict

@app.post("/chat", response_model=QueryResponse)
def chat_endpoint(request: QueryRequest):
    if not rag_service: raise HTTPException(500, "Service initializing")

    analysis_result = rag_service.analyze_query(request.question)
    top_docs = rag_service.retrieve_and_rerank(request.question, analysis_result)
    
    if not top_docs:
         return QueryResponse(
            answer="未检索到相关文献。",
            context_used=[],
            verification={},
            analysis_debug=analysis_result
        )

    context_list = []
    current_len = 0
    
    for i, item in enumerate(top_docs):
        meta = item["meta"]
        content = item["content"]
        content_snippet = content[:800] + "..." if len(content) > 800 else content
        
        entry = (
            f"<doc id='{i+1}'>\n"
            f"  <title>{meta.get('title')}</title>\n"
            f"  <authors>{meta.get('authors')}</authors>\n"
            f"  <year>{meta.get('year')}</year>\n"
            f"  <citations>{meta.get('citations')}</citations>\n"
            f"  <text>{content_snippet}</text>\n"
            f"</doc>"
        )
        if current_len + len(entry) < MAX_CONTEXT_CHARS:
            context_list.append(entry)
            current_len += len(entry)
        else:
            break
            
    context_str = "\n".join(context_list)

    system_prompt = (
        "你是一位科研及硬件设施专家。请基于自己的知识和【参考文献】回答问题。\n"
        "1. **利用元数据**：\n"
        "   - 若引用**科研论文**，请提及作者/年份（例如：“Wang 等人(2023)指出...”）。\n"
        "   - 若引用**硬件/设施文档**，请提及设备名称、型号或文档标题（例如：“根据《离心机操作手册》...”）。\n"
        "2. **准确引用**：句尾使用 [x] 标注来源。\n"
        "3. **处理缺失**：如果元数据显示为 'Unknown'，则只引用内容，不要编造作者或年份。"
    )

    user_prompt = f"【参考文献】\n{context_str}\n\n【用户问题】\n{request.question}"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    text_input = rag_service.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = rag_service.tokenizer([text_input], return_tensors="pt").to(rag_service.model.device)
    
    with torch.no_grad():
        outputs = rag_service.model.generate(
            **inputs, 
            max_new_tokens=1024,
            temperature=0.7, 
            top_p=0.9
        )
    
    answer = rag_service.tokenizer.decode(outputs[0][len(inputs.input_ids[0]):], skip_special_tokens=True)
    verification = rag_service.verify_citations(answer, len(top_docs))

    return QueryResponse(
        answer=answer, 
        context_used=top_docs, 
        verification=verification,
        analysis_debug=analysis_result
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)