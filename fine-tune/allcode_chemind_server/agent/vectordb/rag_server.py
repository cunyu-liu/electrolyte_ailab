import time
import uvicorn
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import List, Optional

# python rag_server.py
# 在服务器上跑，然后用户访问这个端口就行。



# --- 核心依赖 ---
from pymilvus import connections, Collection
from sentence_transformers import SentenceTransformer

# ================= 配置 =================
MILVUS_HOST = "localhost"  # Milvus 就在本机（或内网IP）
MILVUS_PORT = "19530"
COLLECTION_NAME = "electrolyte_papers"
EMBEDDING_MODEL_PATH = "BAAI/bge-large-zh-v1.5"
# =======================================

# 定义请求体结构 (Pydantic)
class SearchRequest(BaseModel):
    query: str
    top_k: int = 3
    filter_metadata: Optional[dict] = None  # 支持元数据过滤

class SearchResponse(BaseModel):
    results: List[dict]
    latency: float

# 初始化 FastAPI
app = FastAPI(title="电解液研发平台 RAG 检索服务", version="1.0")

# 全局变量
milvus_collection = None
embedding_model = None

@app.on_event("startup")
async def load_resources():
    """服务启动时：连接数据库，加载模型到显存"""
    global milvus_collection, embedding_model
    
    print("正在连接 Milvus...")
    connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
    milvus_collection = Collection(COLLECTION_NAME)
    milvus_collection.load() # 预加载到内存
    
    print(f"正在加载 Embedding 模型: {EMBEDDING_MODEL_PATH}...")
    # 这一步会占用显存，确保服务器显存够用
    embedding_model = SentenceTransformer(EMBEDDING_MODEL_PATH)
    print("✅ RAG 服务启动就绪！")

@app.post("/search", response_model=SearchResponse)
async def search_knowledge(request: SearchRequest):
    """
    核心接口：用户发文字 -> 服务端转向量 -> 查库 -> 返回文字
    """
    start_time = time.time()
    
    try:
        # 1. 文本转向量 (统一由服务端处理，保证模型一致)
        query_vector = embedding_model.encode([request.query], normalize_embeddings=True)
        
        # 2. Milvus 检索
        search_params = {"metric_type": "COSINE", "params": {"ef": 64}}
        
        # 构建 expr 过滤 (如果用户传了 filter)
        # 例如: expr="metadata['year'] > 2020"
        expr = None 
        
        results = milvus_collection.search(
            data=query_vector,
            anns_field="embeddings",
            param=search_params,
            limit=request.top_k,
            expr=expr,
            output_fields=["content", "metadata"] # 只返回内容，不返回向量
        )
        
        # 3. 格式化结果
        ret_data = []
        for hits in results:
            for hit in hits:
                ret_data.append({
                    "score": hit.score, # 相似度得分
                    "content": hit.entity.get("content"),
                    "metadata": hit.entity.get("metadata")
                })
                
        return {
            "results": ret_data,
            "latency": round(time.time() - start_time, 4)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # host="0.0.0.0" 表示允许局域网其他机器访问
    uvicorn.run(app, host="0.0.0.0", port=8000)