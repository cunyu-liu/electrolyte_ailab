import uvicorn
import torch
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

# 引入必要的 NLP 和 数据库 库
from transformers import AutoModelForCausalLM, AutoTokenizer
from sentence_transformers import SentenceTransformer
from pymilvus import connections, Collection, utility
'''
先启动 docker，再跑这个代码.成功了

必须确认的几点修改：
换到 gpu 上跑的时候，记得开 float16。
COSINE方法计算相似度（距离）。

MILVUS_COLLECTION_NAME: 必须改成你创建数据库时的名字（例如 "qa_collection" 或 "wiki_data"）。

MILVUS_VECTOR_FIELD: 这是你在 Milvus schema 中定义存储向量的字段名（常见的叫 "embedding" 或 "vector"）。

MILVUS_TEXT_FIELD: 这是你在 Milvus schema 中存储原始文本内容的字段名（检索时我们需要把这段文字拿出来喂给 LLM，如果你的 Milvus 只存了 ID，你需要在这里改成根据 ID 去 MySQL/Redis 查文本的逻辑；如果 Milvus 里直接存了文本，填字段名即可）。

metric_type: 代码里写的是 "L2" (欧式距离)。如果你建库时用的是 "IP" (内积) 或 "COSINE"，请在 search_vector_db 函数中修改 search_params。
'''

import uvicorn
import torch
import logging
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Tuple

# === 核心库变更 ===
from transformers import AutoModelForCausalLM, AutoTokenizer
from sentence_transformers import SentenceTransformer 
# 【变更】引入 FlagReranker
from FlagEmbedding import FlagReranker 
from pymilvus import connections, Collection, utility

# ==============================================================================
# 1. 配置中心 (请根据你的本地路径修改)
# ==============================================================================

# 硬件配置
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# 模型路径
# 【请修改】你的微调 LLM 路径
LLM_MODEL_PATH = "/Users/liucunyu/.cache/modelscope/hub/models/Qwen/Qwen3-0.6B" 

# 【请修改】Embedding 模型路径 (用于 Milvus 检索)
EMBEDDING_MODEL_NAME = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/Xorbits/bge-m3"

# 【请修改】Reranker 模型路径 (建议使用 bge-reranker-v2-m3 或 large)
RERANKER_MODEL_NAME = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/bge-reranker-v2-m3" 

# Milvus 配置
MILVUS_HOST = "127.0.0.1"
MILVUS_PORT = "19530"
MILVUS_COLLECTION_NAME = "electrolyte_papers" # 这三部分，必须和数据库中的字段名一样
MILVUS_VECTOR_FIELD = "embeddings"
MILVUS_TEXT_FIELD = "content"

# 检索超参
SEARCH_TOP_K = 50  # 粗排召回数量
RERANK_TOP_K = 5   # 精排保留数量

# ==============================================================================
# 2. RAG 服务核心类
# ==============================================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedRAGService:
    def __init__(self):
        logger.info(f"正在初始化服务，运行设备: {DEVICE}")
        
        # 1. 加载 Embedding 模型 (用于 Query 向量化)
        logger.info("Step 1/4: 加载 Embedding 模型...")
        self.embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=DEVICE)
        
        # 2. 加载 Reranker 模型 (使用 FlagEmbedding)
        logger.info(f"Step 2/4: 加载 Reranker 模型 ({RERANKER_MODEL_NAME})...")
        # 【关键修改】使用 FlagReranker，开启 fp16 加速
        self.reranker_model = FlagReranker(
            RERANKER_MODEL_NAME, 
            use_fp16=False,  # 【CPU 必须改】必须关掉 fp16，CPU 不支持半精度加速
            device="cpu"     # 显式指定 cpu
        )
        
        # 3. 加载 LLM
        logger.info(f"Step 3/4: 加载微调 LLM ({LLM_MODEL_PATH})...")
        self.tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_PATH, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            LLM_MODEL_PATH, 
            torch_dtype=torch.float32,  # 【CPU 必须改】改成 float32
            device_map="cpu",           # 【CPU 必须改】强制指定 cpu
            trust_remote_code=True
        )

        # 4. 连接数据库
        logger.info("Step 4/4: 连接 Milvus...")
        self._connect_milvus()

    def _connect_milvus(self):
        try:
            connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
            if not utility.has_collection(MILVUS_COLLECTION_NAME):
                raise ValueError(f"集合 {MILVUS_COLLECTION_NAME} 不存在")
            self.collection = Collection(MILVUS_COLLECTION_NAME)
            self.collection.load()
            logger.info(f"Milvus 就绪，包含 {self.collection.num_entities} 条数据")
        except Exception as e:
            logger.error(f"Milvus 连接失败: {e}")
            raise e

    def get_embedding(self, text: str) -> List[float]:
        return self.embed_model.encode(text, normalize_embeddings=True).tolist()

    def retrieve_and_rerank(self, query: str) -> List[str]:
        """两阶段检索：Milvus 粗排 -> FlagReranker 精排"""
        
        # --- 第一阶段：Milvus 向量检索 (召回 Top-50) ---
        query_vec = self.get_embedding(query)
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
        
        results = self.collection.search(
            data=[query_vec],
            anns_field=MILVUS_VECTOR_FIELD,
            param=search_params,
            limit=SEARCH_TOP_K,
            output_fields=[MILVUS_TEXT_FIELD]
        )
        
        candidates = []
        if results and results[0]:
            for hit in results[0]:
                text = hit.entity.get(MILVUS_TEXT_FIELD)
                candidates.append(text)

        if not candidates:
            return []

        # --- 第二阶段：FlagReranker 重排序 ---
        # 构造 Pair 列表: [['question', 'doc1'], ['question', 'doc2'], ...]
        rerank_pairs = [[query, doc] for doc in candidates]
        
        # 【关键修改】调用 compute_score
        # normalize=True 会将分数映射到 0-1 之间，便于理解
        scores = self.reranker_model.compute_score(rerank_pairs, normalize=True)
        
        # 处理只有 1 个候选文档的边缘情况 (compute_score 返回 float 而不是 list)
        if isinstance(scores, float):
            scores = [scores]
        
        # 打包 (Document, Score) 并排序
        scored_docs = list(zip(candidates, scores))
        # 按分数从高到低排序
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # 截取 Top-K
        final_docs = [doc for doc, score in scored_docs[:RERANK_TOP_K]]
        
        return final_docs

    def verify_citations(self, answer: str, context_count: int) -> Dict:
        """验证引用是否越界"""
        citations = re.findall(r'\[(\d+)\]', answer)
        citations = [int(c) for c in citations]
        
        valid = True
        warnings = []
        
        if not citations:
            warnings.append("警告：回答中未检测到引用标记。")
        else:
            for c in citations:
                if c < 1 or c > context_count:
                    valid = False
                    warnings.append(f"发现幻觉引用：[{c}] (有效范围 1-{context_count})")
        
        return {"is_valid": valid, "citations_found": citations, "warnings": warnings}

# ==============================================================================
# 3. FastAPI 接口定义
# ==============================================================================

app = FastAPI(title="Industrial RAG Service with FlagEmbedding")
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

@app.post("/chat", response_model=QueryResponse)
async def chat_endpoint(request: QueryRequest):
    if not rag_service:
        raise HTTPException(status_code=500, detail="Service initializing")

    # 1. 检索 + Rerank
    top_docs = rag_service.retrieve_and_rerank(request.question)
    
    if not top_docs:
        return QueryResponse(
            answer="未找到相关论文数据。",
            context_used=[],
            verification={"is_valid": True, "note": "No context found"}
        )

    # 2. 构建 Prompt
    context_str_list = [f"[{i+1}] {doc}" for i, doc in enumerate(top_docs)]
    full_context_str = "\n\n".join(context_str_list)
    
    system_prompt = (
        "你是一个专业的科研助手。请严格基于提供的【参考信息】回答问题。\n"
        "要求：\n"
        "1. 必须在回答句尾明确标注引用来源，格式为 [x]。\n"
        "2. 如果参考信息中没有答案，请直接说“未找到相关信息”，严禁编造。\n"
        "3. 保持回答客观、学术。"
    )
    
    user_prompt = f"【参考信息】\n{full_context_str}\n\n【问题】\n{request.question}"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # 3. LLM 生成
    text_input = rag_service.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = rag_service.tokenizer([text_input], return_tensors="pt").to(rag_service.model.device)
    
    with torch.no_grad():
        outputs = rag_service.model.generate(
            **inputs, 
            max_new_tokens=512,
            temperature=0.3, # 学术场景建议低温度
            top_p=0.9,
            do_sample=True
        )
    
    generated_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(inputs.input_ids, outputs)]
    answer = rag_service.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    
    # 4. 验证
    verification_result = rag_service.verify_citations(answer, len(top_docs))

    return QueryResponse(
        answer=answer, 
        context_used=top_docs,
        verification=verification_result
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)