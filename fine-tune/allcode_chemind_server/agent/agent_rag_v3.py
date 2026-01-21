import uvicorn
import torch
import logging
import re
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any

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
            
            self.has_year_scalar = "year" in self.existing_fields
            self.has_metadata_json = "metadata" in self.existing_fields
            
            logger.info(f"Milvus 就绪 (Year Scalar: {self.has_year_scalar}, Metadata JSON: {self.has_metadata_json})")
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
                logger.warning(f"Elasticsearch Ping 失败: 服务未响应 ({ES_HOST})。已自动降级为纯向量检索模式。")
        except Exception as e:
            self.use_es = False
            logger.warning(f"Elasticsearch 初始化异常: {e}。已自动降级为纯向量检索模式。")

    def get_embedding(self, text: str) -> List[float]:
        return self.embed_model.encode(text, normalize_embeddings=True).tolist()

    # === 1. Query 理解 ===
    def analyze_query(self, query: str) -> Dict[str, Any]:
        prompt = (
            f"分析查询（涉及科研文献或硬件设施）：'{query}'。\n"
            "提取以下信息（如果不存在则为null）：\n"
            "1. year (年份，如 '2023.0')\n"
            "2. author (作者姓名)\n"
            "3. keywords (核心技术词、设备名称或型号)\n"
            "4. high_citation (bool, 用户是否暗示要找'经典'论文或'核心'设备参数)\n"
            "必须输出JSON格式: {{\"year\": ..., \"author\": ..., \"keywords\": ..., \"high_citation\": ...}}\n"
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
                if result.get('year'):
                    clean_year = re.sub(r'[^\d.]', '', str(result['year']))
                    if '.' not in clean_year and len(clean_year) == 4:
                        clean_year += ".0"
                    result['year'] = clean_year
                return result
        except Exception as e:
            logger.warning(f"LLM分析异常: {e}")
        
        return {"year": None, "keywords": query, "author": None, "high_citation": False}

    # === 2. Elasticsearch 检索 ===
    def _search_es_keyword(self, query: str, filters: Dict) -> List[Dict]:
        if not self.use_es: return []
            
        must_clauses = [{"match": {ES_TEXT_FIELD: query}}]
        filter_clauses = []
        if filters.get('year'):
            filter_clauses.append({"term": {"year": filters['year']}})
            
        body = {
            "size": SEARCH_TOP_K,
            "query": {"bool": {"must": must_clauses, "filter": filter_clauses}},
            "_source": [ES_TEXT_FIELD, "title", "authors", "year", "citations", "metadata"] 
        }
        
        try:
            resp = self.es_client.search(index=ES_INDEX, body=body)
            results = []
            for hit in resp["hits"]["hits"]:
                src = hit["_source"]
                meta = src.get("metadata", {}) or {}
                results.append({
                    "content": src.get(ES_TEXT_FIELD, ""),
                    "meta": {
                        "title": src.get("title") or meta.get("title", "Unknown Title"),
                        "authors": src.get("authors") or meta.get("authors", "Unknown Authors"),
                        "year": src.get("year") or meta.get("year", "Unknown Year"),
                        "citations": src.get("citations") or meta.get("citations", "0")
                    }
                })
            return results
        except Exception:
            return []
        
    # [修改点]：批量查询优化的上下文扩展
    def _expand_context(self, hits: List[Dict], window_size: int = 1) -> List[Dict]:
        """
        对 Rerank 后的结果进行上下文扩展 (Batch Query 优化版)。
        """
        if not hits:
            return []

        # 1. 收集需要查询的条件
        query_specs = [] # List of (doc_id, list_of_chunk_ids)
        expanded_hits_map = {} # 用于按顺序映射回原结果

        for idx, hit in enumerate(hits):
            meta = hit.get("meta", {})
            doc_id = hit.get("doc_id")
            chunk_id = meta.get("chunk_id")
            
            # 只有当 doc_id 和 chunk_id 都存在时才尝试扩展
            if doc_id is not None and chunk_id is not None:
                try:
                    c_id = int(chunk_id)
                    target_ids = list(range(c_id - window_size, c_id + window_size + 1))
                    query_specs.append((doc_id, target_ids))
                except ValueError:
                    pass
            
            expanded_hits_map[idx] = hit # 默认保留原样

        if not query_specs:
            return hits

        # 2. 构建批量查询表达式 (使用 OR 连接)
        # expr: (doc_id == "A" && chunk_id in [1,2,3]) || (doc_id == "B" && chunk_id in [4,5,6])
        expr_parts = []
        for doc_id, t_ids in query_specs:
            ids_str = ",".join(str(i) for i in t_ids)
            # 注意：此处假设 doc_id 为字符串类型，需加引号
            expr_parts.append(f'(doc_id == "{doc_id}" && chunk_id in [{ids_str}])')
        
        full_expr = " || ".join(expr_parts)

        try:
            # 3. 执行一次性查询
            res = self.collection.query(
                expr=full_expr,
                output_fields=[MILVUS_TEXT_FIELD, "doc_id", "chunk_id"],
                limit=len(query_specs) * (window_size * 2 + 1)
            )

            # 4. 将结果构建为字典索引: {(doc_id, chunk_id): content}
            content_map = {}
            for item in res:
                d_id = item.get("doc_id")
                c_id = item.get("chunk_id")
                txt = item.get(MILVUS_TEXT_FIELD, "")
                content_map[(d_id, c_id)] = txt

            # 5. 组装结果
            final_hits = []
            for idx, hit in enumerate(hits):
                meta = hit.get("meta", {})
                doc_id = hit.get("doc_id")
                chunk_id = meta.get("chunk_id")

                if doc_id is not None and chunk_id is not None:
                    try:
                        c_id = int(chunk_id)
                        target_ids = list(range(c_id - window_size, c_id + window_size + 1))
                        
                        # 按顺序收集文本
                        merged_parts = []
                        for tid in target_ids:
                            # 如果 map 里有就取，没有就算了 (可能越界)
                            part = content_map.get((doc_id, tid))
                            if part:
                                merged_parts.append(part)
                        
                        if merged_parts:
                            hit["content"] = "\n".join(merged_parts)
                            hit["meta"]["is_expanded"] = True
                    except Exception as e:
                        logger.warning(f"组装扩展内容失败: {e}")
                
                final_hits.append(hit)
            
            return final_hits

        except Exception as e:
            logger.error(f"批量上下文扩展查询失败: {e}")
            return hits

    # === 3. 混合检索主逻辑 ===
    def retrieve_and_rerank(self, query: str, analysis: Dict[str, Any]) -> List[Dict]:
        search_kw = analysis.get("keywords", query) or query
        year_filter = analysis.get("year")
        
        candidates = [] 

        # --- B. Milvus 向量检索 ---
        query_vec = self.get_embedding(search_kw)
        
        expr_list = []
        if year_filter and self.has_year_scalar:
            expr_list.append(f'year == "{year_filter}"')
        expr = " && ".join(expr_list) if expr_list else ""
        
        target_output_fields = [MILVUS_TEXT_FIELD, "doc_id"] 
        if self.has_year_scalar: target_output_fields.append("year")
        if self.has_metadata_json: target_output_fields.append("metadata")
        if "chunk_id" in self.existing_fields:
            target_output_fields.append("chunk_id")

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
                    meta_json = entity.get("metadata") if self.has_metadata_json else {}
                    if not isinstance(meta_json, dict): meta_json = {}

                    c_id = entity.get("chunk_id") or meta_json.get("chunk_id")

                    candidates.append({
                        "content": entity.get(MILVUS_TEXT_FIELD),
                        "doc_id": entity.get("doc_id"), 
                        "meta": {
                            "title": meta_json.get("title", "Unknown Title"),
                            "authors": meta_json.get("authors", "Unknown Authors"),
                            "year": entity.get("year") or meta_json.get("year", "Unknown Year"),
                            "citations": meta_json.get("citations", "0"),
                            "chunk_id": c_id 
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
                
                if analysis.get("high_citation"):
                    cit_str = str(meta.get("citations", "0"))
                    cit_nums = re.findall(r'\d+', cit_str)
                    if cit_nums:
                        cit_val = int(max(cit_nums, key=lambda x: int(x)))
                        final_score += min(cit_val / 10000.0, 0.1) 
                
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

# ==============================================================================
# 3. FastAPI 接口
# ==============================================================================

app = FastAPI(title="Metadata-Aware RAG Service")
rag_service = None

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