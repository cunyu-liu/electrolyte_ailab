import os
import json
import glob
import logging
import torch
from tqdm import tqdm
from typing import List, Dict, Any
import hashlib

# --- 🔥 HF 镜像加速 ---
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
# ------------------------------

from pymilvus import connections, Collection, utility, FieldSchema, CollectionSchema, DataType
from sentence_transformers import SentenceTransformer

# 引入工业级分块工具
from langchain_text_splitters import RecursiveCharacterTextSplitter

# =================配置中心=================
class Config:
    # 路径配置
    INPUT_DIR = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/paper_text_clean"
    LOG_DIR = "./logs"
    CHECKPOINT_FILE = os.path.join(LOG_DIR, "step2_processed.log")
    
    # Milvus 配置
    MILVUS_HOST = "localhost"
    MILVUS_PORT = "19530"
    COLLECTION_NAME = "electrolyte_papers_chunked" # 建议换个新名字，区别于之前的整篇存
    
    # 模型配置
    EMBEDDING_MODEL = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/Xorbits/bge-m3"
    
    # --- ⚡️ 关键优化参数 ---
    # BGE-M3 支持 8192 长度，但 RAG 最佳实践通常在 512-1000 字符之间
    CHUNK_SIZE = 800        # 每个块的目标字符数
    CHUNK_OVERLAP = 150     # 重叠字符数，防止切分点丢失语义
    BATCH_SIZE = 32         # 显存允许的情况下，Batch Size 可以调大，提高吞吐量
    DIMENSION = 1024        # BGE-M3 输出维度

# 日志配置
os.makedirs(Config.LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(Config.LOG_DIR, "import_job.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ================= 核心组件：文本处理器 =================
class TextProcessor:
    def __init__(self):
        # 初始化递归分块器
        # 分隔符优先级：双换行(段落) > 单换行 > 句子结尾 > 词空格
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", ".", " ", ""]
        )

    def process_paper(self, paper_data: Dict) -> List[Dict]:
        """
        将单篇论文处理为多个带有元数据的 Chunks
        """
        chunks = []
        
        title = paper_data.get('title', 'Unknown Title')
        doc_id = paper_data.get('doi') or self._generate_doc_id(title)
        
        # 1. 处理 Abstract (作为单独的高优先级块)
        abstract = paper_data.get('abstract', '').strip()
        if abstract:
            # 摘要加上标题前缀，增强语义
            # 格式：Title: <title>\nSection: Abstract\nContent: <abstract>
            text_content = f"Title: {title}\nSection: Abstract\nContent: {abstract}"
            chunks.append({
                "text": text_content,
                "metadata": self._build_metadata(paper_data, "Abstract", 0, doc_id)
            })

        # 2. 处理 Main Text (进行切分)
        main_text = paper_data.get('main_text', '').strip()
        if main_text:
            raw_chunks = self.text_splitter.split_text(main_text)
            
            for idx, chunk_text in enumerate(raw_chunks):
                # 【核心技巧】Context Injection
                # 每一块都带上标题，防止检索出来的块不知道属于哪篇文章
                enriched_text = f"Title: {title}\nContent: {chunk_text}"
                
                chunks.append({
                    "text": enriched_text,
                    "metadata": self._build_metadata(paper_data, "MainBody", idx + 1, doc_id)
                })
                
        return chunks

    def _build_metadata(self, original_data: Dict, section: str, chunk_index: int, doc_id: str) -> Dict:
        """构建标准化的元数据"""
        # 截断过长字段防止数据库报错
        return {
            "doc_id": doc_id,                # 用于聚合同一篇文章的所有块
            "title": str(original_data.get('title', ''))[:500],
            "year": str(original_data.get('year', '')),
            "source": str(original_data.get('journal', ''))[:200],
            "chunk_type": section,           # 标记是摘要还是正文
            "chunk_index": chunk_index,      # 标记顺序
            "doi": str(original_data.get('doi', ''))[:100]
        }

    def _generate_doc_id(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

# ================= 数据库客户端 =================
class MilvusClient:
    def __init__(self):
        self._connect()
        self._init_collection()

    def _connect(self):
        try:
            connections.connect("default", host=Config.MILVUS_HOST, port=Config.MILVUS_PORT)
            logger.info(f"✅ Milvus Connected: {Config.MILVUS_HOST}")
        except Exception as e:
            logger.error(f"❌ Milvus Connection Failed: {e}")
            raise e

    def _init_collection(self):
        if utility.has_collection(Config.COLLECTION_NAME):
            self.collection = Collection(Config.COLLECTION_NAME)
            logger.info(f"✅ Loaded existing collection: {Config.COLLECTION_NAME}")
        else:
            logger.info(f"🚀 Creating new collection: {Config.COLLECTION_NAME}")
            fields = [
                # 主键
                FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
                # 向量
                FieldSchema(name="embeddings", dtype=DataType.FLOAT_VECTOR, dim=Config.DIMENSION),
                # 文本内容 (增加长度以容纳 chunks)
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192),
                # 核心元数据字段 (为了更快的标量过滤，建议提取出来)
                FieldSchema(name="year", dtype=DataType.VARCHAR, max_length=10),
                FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=128),
                # 其他杂项元数据存 JSON
                FieldSchema(name="metadata", dtype=DataType.JSON)
            ]
            schema = CollectionSchema(fields, description="Electrolyte Papers Chunked DB")
            self.collection = Collection(Config.COLLECTION_NAME, schema)
            
            # 创建 HNSW 索引 (适合大规模)
            index_params = {
                "metric_type": "COSINE",
                "index_type": "HNSW",
                "params": {"M": 16, "efConstruction": 250}
            }
            self.collection.create_index(field_name="embeddings", index_params=index_params)
            logger.info("✅ Index created.")

    def insert_batch(self, vectors, texts, metadatas):
        # 将数据拆解对齐 Schema
        years = [m.get('year', '') for m in metadatas]
        doc_ids = [m.get('doc_id', '') for m in metadatas]
        
        # 执行插入
        self.collection.insert([
            vectors, 
            texts, 
            years, 
            doc_ids, 
            metadatas
        ])

# ================= 流程控制 =================
class Pipeline:
    def __init__(self):
        # 1. 设备检测
        self.device = self._get_device()
        
        # 2. 组件初始化
        self.milvus = MilvusClient()
        self.processor = TextProcessor()
        
        # 3. 加载模型
        logger.info(f"Loading Model on {self.device}...")
        self.model = SentenceTransformer(Config.EMBEDDING_MODEL, device=self.device)
        
        # 4. Checkpoint
        self.processed_files = self._load_checkpoint()

    def _get_device(self):
        if torch.backends.mps.is_available():
            logger.info("🍎 Apple Silicon (MPS) Detected.")
            return "mps"
        elif torch.cuda.is_available():
            logger.info("🟢 NVIDIA GPU (CUDA) Detected.")
            return "cuda"
        return "cpu"

    def _load_checkpoint(self):
        if os.path.exists(Config.CHECKPOINT_FILE):
            with open(Config.CHECKPOINT_FILE, 'r') as f:
                return set(line.strip() for line in f if line.strip())
        return set()

    def _save_checkpoint(self, filepath):
        with open(Config.CHECKPOINT_FILE, 'a') as f:
            f.write(os.path.abspath(filepath) + "\n")

    def run(self):
        all_files = sorted(glob.glob(os.path.join(Config.INPUT_DIR, "*.json")))
        pending_files = [f for f in all_files if os.path.abspath(f) not in self.processed_files]
        
        logger.info(f"Total Files: {len(all_files)}, Pending: {len(pending_files)}")
        
        buffer_texts = []
        buffer_metas = []
        
        # 进度条
        pbar = tqdm(pending_files, desc="Processing Files")
        
        for json_file in pbar:
            try:
                # 1. 读取与解析
                with open(json_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                
                if isinstance(content, dict): content = [content]
                
                # 2. 分块处理 (Chunking)
                file_chunks = []
                for item in content:
                    file_chunks.extend(self.processor.process_paper(item))
                
                if not file_chunks:
                    self._save_checkpoint(json_file)
                    continue

                # 3. 放入 Buffer
                for chunk in file_chunks:
                    buffer_texts.append(chunk["text"])
                    buffer_metas.append(chunk["metadata"])
                    
                    # 4. 如果 Buffer 满了，执行向量化和插入
                    if len(buffer_texts) >= Config.BATCH_SIZE:
                        self._flush_buffer(buffer_texts, buffer_metas)
                        buffer_texts = []
                        buffer_metas = []
                
                # 5. 标记文件完成
                self._save_checkpoint(json_file)
                
            except Exception as e:
                logger.error(f"Failed to process {json_file}: {e}")
                continue

        # 6. 处理剩余数据
        if buffer_texts:
            self._flush_buffer(buffer_texts, buffer_metas)
            
        # 7. 最终落盘
        self.milvus.collection.flush()
        logger.info(f"🎉 Job Done. Total Entities: {self.milvus.collection.num_entities}")

    def _flush_buffer(self, texts, metas):
        try:
            # 向量化 (Embedding)
            embeddings = self.model.encode(texts, normalize_embeddings=True)
            # 插入 DB
            self.milvus.insert_batch(embeddings, texts, metas)
        except Exception as e:
            logger.error(f"⚠️ Batch Insert Error: {e}")
            # 简单的重试逻辑或跳过可以在这里添加

# ================= 入口 =================
if __name__ == "__main__":
    pipeline = Pipeline()
    pipeline.run()