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

# 模型路径 (请确认路径正确)
LLM_MODEL_PATH = "/Users/liucunyu/.cache/modelscope/hub/models/Qwen/Qwen3-0.6B" 
EMBEDDING_MODEL_NAME = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/Xorbits/bge-m3"
RERANKER_MODEL_NAME = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/bge-reranker-v2-m3" 

# Milvus 配置
MILVUS_HOST = "127.0.0.1"
MILVUS_PORT = "19530"
MILVUS_COLLECTION_NAME = "electrolyte_papers"
MILVUS_VECTOR_FIELD = "embeddings"
MILVUS_TEXT_FIELD = "content" 

# Metadata Keys (对应您的 JSON 字段)
MILVUS_META_YEAR = "year"          
MILVUS_META_TITLE = "title"        
MILVUS_META_AUTHORS = "authors"    
MILVUS_META_CITATIONS = "citations"
MILVUS_META_DOI = "doi"

# Elasticsearch 配置
ES_HOST = "http://localhost:9200"
ES_INDEX = "electrolyte_papers_index"
ES_TEXT_FIELD = "content"

# 检索超参
SEARCH_TOP_K = 15
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
            
            # === 【核心修复】检测 Schema，看数据库里到底有哪些字段 ===
            self.existing_fields = [field.name for field in self.collection.schema.fields]
            logger.info(f"Milvus Schema 字段检测: {self.existing_fields}")
            
            # 判断关键字段是否存在，用于后续逻辑判断
            self.has_title = MILVUS_META_TITLE in self.existing_fields
            self.has_authors = MILVUS_META_AUTHORS in self.existing_fields
            self.has_year = MILVUS_META_YEAR in self.existing_fields
            self.has_citations = MILVUS_META_CITATIONS in self.existing_fields
            
            logger.info(f"Milvus 就绪")
        except Exception as e:
            logger.error(f"Milvus 连接失败: {e}")
            raise e

    def _connect_es(self):
        try:
            self.es_client = Elasticsearch(ES_HOST)
            if self.es_client.ping():
                self.use_es = True
                logger.info(f"Elasticsearch 就绪")
            else:
                self.use_es = False
                logger.warning("Elasticsearch Ping 失败")
        except Exception:
            self.use_es = False
            logger.warning("Elasticsearch 连接异常，降级为纯向量检索")

    def get_embedding(self, text: str) -> List[float]:
        return self.embed_model.encode(text, normalize_embeddings=True).tolist()

    # === 1. Query 理解 ===
    def analyze_query(self, query: str) -> Dict[str, Any]:
        prompt = (
            f"分析科研查询：'{query}'。\n"
            "提取以下信息（如果不存在则为null）：\n"
            "1. year (年份，如 '2023.0')\n"
            "2. author (作者姓名)\n"
            "3. keywords (核心技术词)\n"
            "4. high_citation (bool, 用户是否暗示要找'经典'、'高引'、'核心'论文)\n"
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
                # 年份格式清洗
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
            
        # ES 的 _source 可以容错，如果字段不存在它只会返回 None，不会报错
        body = {
            "size": SEARCH_TOP_K,
            "query": {"bool": {"must": must_clauses, "filter": filter_clauses}},
            "_source": [ES_TEXT_FIELD, MILVUS_META_TITLE, MILVUS_META_AUTHORS, MILVUS_META_YEAR, MILVUS_META_CITATIONS]
        }
        
        try:
            resp = self.es_client.search(index=ES_INDEX, body=body)
            results = []
            for hit in resp["hits"]["hits"]:
                src = hit["_source"]
                results.append({
                    "content": src.get(ES_TEXT_FIELD, ""),
                    "meta": {
                        "title": src.get(MILVUS_META_TITLE, "Unknown Title"),
                        "authors": src.get(MILVUS_META_AUTHORS, "Unknown Authors"),
                        "year": src.get(MILVUS_META_YEAR, "Unknown Year"),
                        "citations": src.get(MILVUS_META_CITATIONS, "0")
                    }
                })
            return results
        except Exception:
            return []

    # === 3. 混合检索主逻辑 (核心修复：动态 Output Fields) ===
    def retrieve_and_rerank(self, query: str, analysis: Dict[str, Any]) -> List[Dict]:
        search_kw = analysis.get("keywords", query) or query
        year_filter = analysis.get("year")
        author_filter = analysis.get("author")
        
        candidates = [] 

        # --- B. Milvus 向量检索 ---
        query_vec = self.get_embedding(search_kw)
        
        # 1. 动态构建表达式 (只过滤存在的字段)
        expr_list = []
        if year_filter and self.has_year:
            expr_list.append(f'{MILVUS_META_YEAR} == "{year_filter}"')
        if author_filter and self.has_authors:
            expr_list.append(f'{MILVUS_META_AUTHORS} like "%{author_filter}%"')
            
        expr = " && ".join(expr_list) if expr_list else ""
        
        # 2. 动态构建 Output Fields (只请求存在的字段)
        target_output_fields = [MILVUS_TEXT_FIELD] # 正文是必须的
        if self.has_title: target_output_fields.append(MILVUS_META_TITLE)
        if self.has_authors: target_output_fields.append(MILVUS_META_AUTHORS)
        if self.has_year: target_output_fields.append(MILVUS_META_YEAR)
        if self.has_citations: target_output_fields.append(MILVUS_META_CITATIONS)

        try:
            milvus_res = self.collection.search(
                data=[query_vec],
                anns_field=MILVUS_VECTOR_FIELD,
                param={"metric_type": "COSINE", "params": {"nprobe": 10}},
                limit=SEARCH_TOP_K,
                expr=expr if expr else None,
                output_fields=target_output_fields # <--- 只有存在的字段才会被传进去
            )
            
            if milvus_res and milvus_res[0]:
                for hit in milvus_res[0]:
                    entity = hit.entity
                    # 3. 结果构建：如果 Milvus 里没有该字段，手动填默认值
                    candidates.append({
                        "content": entity.get(MILVUS_TEXT_FIELD),
                        "meta": {
                            "title": entity.get(MILVUS_META_TITLE) if self.has_title else "Unknown Title",
                            "authors": entity.get(MILVUS_META_AUTHORS) if self.has_authors else "Unknown Authors",
                            "year": entity.get(MILVUS_META_YEAR) if self.has_year else "Unknown Year",
                            "citations": entity.get(MILVUS_META_CITATIONS) if self.has_citations else "0"
                        }
                    })
        except Exception as e:
            logger.error(f"Milvus search error: {e}")
            # 出错时不崩溃，尝试继续用 ES 结果

        # --- C. ES 检索 ---
        es_res = self._search_es_keyword(search_kw, {"year": year_filter})
        candidates.extend(es_res)

        # --- D. 去重 ---
        unique_map = {c["content"]: c for c in candidates}
        unique_candidates = list(unique_map.values())
        if not unique_candidates: return []

        # --- E. Rerank ---
        docs_text = [c["content"] for c in unique_candidates]
        rerank_pairs = [[query, doc] for doc in docs_text]
        scores = self.reranker_model.compute_score(rerank_pairs, normalize=True)
        if isinstance(scores, float): scores = [scores]
        
        ranked_results = []
        for i, score in enumerate(scores):
            final_score = score
            # 只有当 citations 存在时才进行加权
            meta = unique_candidates[i]["meta"]
            if analysis.get("high_citation") and meta.get("citations") != "0":
                try:
                    cit_val = int(meta["citations"])
                    final_score += min(cit_val / 10000.0, 0.1) 
                except:
                    pass
            ranked_results.append((unique_candidates[i], final_score))
            
        ranked_results.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in ranked_results[:RERANK_TOP_K]]

    def verify_citations(self, answer: str, context_count: int) -> Dict:
        citations = re.findall(r'\[(\d+)\]', answer)
        citations = [int(c) for c in citations]
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
        content_snippet = content[:600] + "..." if len(content) > 600 else content
        
        # 即使是 Unknown，也填入 XML，保持格式一致
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
        "你是一位科研专家。请基于【参考文献】回答问题。\n"
        "1. **利用元数据**：如参考文献包含有效作者/年份，请在引用时提及（例如：“Wang 等人(2023)指出...”）。\n"
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