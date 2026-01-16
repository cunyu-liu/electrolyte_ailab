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
    dtype = torch.float16
else:
    DEVICE = "cpu"
    dtype = torch.float32

# 模型路径
LLM_MODEL_PATH = "/Users/liucunyu/.cache/modelscope/hub/models/Qwen/Qwen3-0.6B" 
EMBEDDING_MODEL_NAME = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/Xorbits/bge-m3"
RERANKER_MODEL_NAME = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/bge-reranker-v2-m3" 

# Milvus 配置
MILVUS_HOST = "127.0.0.1"
MILVUS_PORT = "19530"
MILVUS_COLLECTION_NAME = "electrolyte_papers"
MILVUS_VECTOR_FIELD = "embeddings"
MILVUS_TEXT_FIELD = "content" 

# Metadata Keys
MILVUS_META_YEAR = "year"      
MILVUS_META_TITLE = "title"    
MILVUS_META_SOURCE = "journal" 

# Elasticsearch 配置
ES_HOST = "http://localhost:9200"
ES_INDEX = "electrolyte_papers_index"
ES_TEXT_FIELD = "content"

# 检索超参 (优化：减少召回数量以提升 Rerank 速度)
SEARCH_TOP_K = 10  # 原50，降至20
RERANK_TOP_K = 5   

# 生成超参 (防止上下文溢出)
MAX_CONTEXT_CHARS = 3000  # 限制参考资料的最大字符数

# ==============================================================================
# 2. RAG 服务核心类
# ==============================================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedRAGService:
    def __init__(self):
        logger.info(f"正在初始化服务，运行设备: {DEVICE}")
        
        # 1. Embedding
        self.embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=DEVICE)
        
        # 2. Reranker
        self.reranker_model = FlagReranker(
            RERANKER_MODEL_NAME, 
            use_fp16=(DEVICE == "cuda"),
            device=DEVICE
        )
        
        # 3. LLM
        self.tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_PATH, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            LLM_MODEL_PATH, 
            torch_dtype=dtype,
            device_map="auto",             
            trust_remote_code=True
        )

        # 4. DB Connections
        self._connect_milvus()
        self._connect_es()

    def _connect_milvus(self):
        try:
            connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
            self.collection = Collection(MILVUS_COLLECTION_NAME)
            self.collection.load()
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

    # === 1. Query 理解 (增加容错机制) ===
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        LLM 提取年份 + 关键词。增加 Try-Except 防止 JSON 解析挂掉。
        """
        prompt = (
            f"分析查询：'{query}'。\n"
            "提取：1.年份(year) 2.关键词(keywords)。\n"
            "必须输出JSON：{\"year\": \"2023.0\", \"keywords\": \"锂电池 电解液\"}\n"
            "JSON:"
        )
        
        messages = [{"role": "user", "content": prompt}]
        text_input = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer([text_input], return_tensors="pt").to(self.model.device)
        
        try:
            with torch.no_grad():
                # 减少 max_new_tokens 加快速度
                outputs = self.model.generate(**inputs, max_new_tokens=64, temperature=0.1)
            output_text = self.tokenizer.decode(outputs[0][len(inputs.input_ids[0]):], skip_special_tokens=True)
            
            # 尝试解析 JSON
            json_match = re.search(r'\{.*\}', output_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                # 格式化年份
                if result.get('year'):
                    # 尝试清理非数字字符，保留 2000.0 格式
                    clean_year = re.sub(r'[^\d.]', '', str(result['year']))
                    if '.' not in clean_year and len(clean_year) == 4:
                        clean_year += ".0"
                    result['year'] = clean_year
                
                logger.info(f"Query分析成功: {result}")
                return result
                
        except json.JSONDecodeError:
            logger.warning("JSON解析失败，降级处理")
        except Exception as e:
            logger.warning(f"LLM分析异常: {e}")
        
        # 降级策略：如果 LLM 失败，尝试简单的正则提取年份，关键词就是原句
        year_match = re.search(r'(20\d{2})', query)
        fallback_year = f"{year_match.group(1)}.0" if year_match else None
        
        return {"rewritten_query": query, "year": fallback_year, "keywords": query}

    # === 2. Elasticsearch 关键词检索 ===
    def _search_es_keyword(self, query: str, year_filter: str = None) -> List[str]:
        if not self.use_es: return []
            
        must_clauses = [{"match": {ES_TEXT_FIELD: query}}]
        filter_clauses = []
        
        if year_filter:
            filter_clauses.append({"term": {"year": year_filter}})

        body = {
            "size": SEARCH_TOP_K,
            "query": {
                "bool": {
                    "must": must_clauses,
                    "filter": filter_clauses
                }
            },
            "_source": [ES_TEXT_FIELD]
        }
        
        try:
            resp = self.es_client.search(index=ES_INDEX, body=body)
            return [hit["_source"][ES_TEXT_FIELD] for hit in resp["hits"]["hits"]]
        except Exception:
            return []

    # === 3. 混合检索主逻辑 (核心修改：接受外部传入的 analysis) ===
    def retrieve_and_rerank(self, query: str, analysis: Dict[str, Any]) -> List[str]:
        # 直接使用传入的 analysis，不再重复调用 LLM
        search_kw = analysis.get("rewritten_query", query)
        
        # 兜底：如果 JSON 解析里没有 rewritten_query 字段
        if not search_kw: search_kw = query 
        
        year_filter = analysis.get("year")
        
        candidates = []

        # B. Milvus 向量检索
        query_vec = self.get_embedding(search_kw)
        
        expr = f'{MILVUS_META_YEAR} == "{year_filter}"' if year_filter else ""
        
        milvus_res = self.collection.search(
            data=[query_vec],
            anns_field=MILVUS_VECTOR_FIELD,
            param={"metric_type": "COSINE", "params": {"nprobe": 10}},
            limit=SEARCH_TOP_K,
            expr=expr if expr else None,
            output_fields=[MILVUS_TEXT_FIELD]
        )
        
        if milvus_res and milvus_res[0]:
            candidates.extend([hit.entity.get(MILVUS_TEXT_FIELD) for hit in milvus_res[0]])

        # C. ES 关键词检索
        es_query_kw = analysis.get('keywords', query)
        es_res = self._search_es_keyword(es_query_kw, year_filter)
        candidates.extend(es_res)

        # D. 去重
        unique_candidates = list(set(candidates))
        if not unique_candidates:
            return []

        # E. Rerank 精排
        rerank_pairs = [[query, doc] for doc in unique_candidates]
        scores = self.reranker_model.compute_score(rerank_pairs, normalize=True)
        
        if isinstance(scores, float): scores = [scores]
        scored_docs = sorted(zip(unique_candidates, scores), key=lambda x: x[1], reverse=True)
        
        return [doc for doc, score in scored_docs[:RERANK_TOP_K]]

    def verify_citations(self, answer: str, context_count: int) -> Dict:
        citations = re.findall(r'\[(\d+)\]', answer)
        citations = [int(c) for c in citations]
        valid = True
        warnings = []
        if not citations:
            warnings.append("警告：回答中未检测到引用。")
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
    context_used: List[str]
    verification: Dict
    analysis_debug: Dict

@app.post("/chat", response_model=QueryResponse)
def chat_endpoint(request: QueryRequest):
    if not rag_service: raise HTTPException(500, "Service initializing")

    # 1. 分析 Query (只执行一次！)
    analysis_result = rag_service.analyze_query(request.question)
    
    # 2. 执行检索 (传入分析结果)
    top_docs = rag_service.retrieve_and_rerank(request.question, analysis_result)
    
    if not top_docs:
        return QueryResponse(
            answer="未找到相关论文数据（请检查年份或关键词）。",
            context_used=[],
            verification={},
            analysis_debug=analysis_result
        )

    # 3. 生成 Prompt (增加长度安全截断)
    context_list = []
    current_len = 0
    
    for i, doc in enumerate(top_docs):
        # 如果单篇太长，稍微截断一下，避免单篇霸占所有窗口
        doc_snippet = doc[:800] + "..." if len(doc) > 800 else doc
        entry = f"[{i+1}] {doc_snippet}"
        
        # 检查是否超过总字符限制
        if current_len + len(entry) < MAX_CONTEXT_CHARS:
            context_list.append(entry)
            current_len += len(entry)
        else:
            break

    context_str = "\n\n".join(context_list)
    
    system_prompt = "你是一个科研助手。基于【参考信息】回答问题，并在句尾标注引用 [x]。若无答案则说明未找到。"
    user_prompt = f"【参考信息】\n{context_str}\n\n【问题】\n{request.question}"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # 4. LLM 生成
    text_input = rag_service.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = rag_service.tokenizer([text_input], return_tensors="pt").to(rag_service.model.device)
    
    with torch.no_grad():
        outputs = rag_service.model.generate(**inputs, max_new_tokens=256, temperature=0.3, top_p=0.9)
    
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