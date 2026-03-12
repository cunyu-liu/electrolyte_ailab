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
    COLLECTION_NAME = "electrolyte_papers_chunked" 
    
    # 模型配置
    EMBEDDING_MODEL = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/Xorbits/bge-m3"
    
    # --- ⚡️ 关键优化参数 ---
    CHUNK_SIZE = 800        
    CHUNK_OVERLAP = 150     
    BATCH_SIZE = 2         
    DIMENSION = 1024        

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
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", ".", " ", ""]
        )

    def process_paper(self, paper_data: Dict) -> List[Dict]:
        chunks = []
        title = paper_data.get('title', 'Unknown Title')
        doc_id = paper_data.get('doi') or self._generate_doc_id(title)
        
        # 1. Abstract
        abstract = paper_data.get('abstract', '').strip()
        if abstract:
            text_content = f"Title: {title}\nSection: Abstract\nContent: {abstract}"
            chunks.append({
                "text": text_content,
                "metadata": self._build_metadata(paper_data, "Abstract", 0, doc_id)
            })

        # 2. Main Text
        main_text = paper_data.get('main_text', '').strip()
        if main_text:
            raw_chunks = self.text_splitter.split_text(main_text)
            for idx, chunk_text in enumerate(raw_chunks):
                enriched_text = f"Title: {title}\nContent: {chunk_text}"
                chunks.append({
                    "text": enriched_text,
                    "metadata": self._build_metadata(paper_data, "MainBody", idx + 1, doc_id)
                })
        return chunks

    def _build_metadata(self, original_data: Dict, section: str, chunk_index: int, doc_id: str) -> Dict:
        # 提取标题用于截断逻辑
        title_str = str(original_data.get('title', ''))
        
        # [修改点]：集成完整的 Meta 字典逻辑
        return {
            # --- 用户请求的扩展字段 ---
            "title": title_str[:500],  # 限制标题长度
            "doi": str(original_data.get('doi', '')),
            "authors": str(original_data.get('authors', []))[:1000],  # 转字符串并截断，防止作者名单太长
            "year": str(original_data.get('year', '')),
            "journal": str(original_data.get('journal', ''))[:500],
            "source_pdf": str(original_data.get('source_pdf', '')),
            "citations": str(original_data.get('citations', []))[:2000],  # 引用列表也截一下
            
            # --- 系统必要字段 (用于Schema映射和逻辑区分) ---
            "doc_id": doc_id,         # 必须保留，insert_batch 依赖此字段
            "chunk_type": section,    # 区分摘要还是正文
            "chunk_index": chunk_index
        }

    def _generate_doc_id(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

# ================= 数据库客户端 =================
class MilvusClient:
    def __init__(self):
        self._connect()
        self._init_collection_reset() 

    def _connect(self):
        try:
            connections.connect("default", host=Config.MILVUS_HOST, port=Config.MILVUS_PORT)
            logger.info(f"✅ Milvus Connected: {Config.MILVUS_HOST}")
        except Exception as e:
            logger.error(f"❌ Milvus Connection Failed: {e}")
            raise e

    def _init_collection_reset(self):
        """
        初始化并强制重置集合
        """
        if utility.has_collection(Config.COLLECTION_NAME):
            utility.drop_collection(Config.COLLECTION_NAME)
            logger.warning(f"🗑️ Dropped existing collection: {Config.COLLECTION_NAME}")
        
        logger.info(f"🚀 Creating new collection: {Config.COLLECTION_NAME}")
        fields = [
            FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="embeddings", dtype=DataType.FLOAT_VECTOR, dim=Config.DIMENSION),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192), 
            FieldSchema(name="year", dtype=DataType.VARCHAR, max_length=10),
            FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="metadata", dtype=DataType.JSON)
        ]
        schema = CollectionSchema(fields, description="Electrolyte Papers Chunked DB")
        self.collection = Collection(Config.COLLECTION_NAME, schema)
        
        index_params = {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {"M": 16, "efConstruction": 250}
        }
        self.collection.create_index(field_name="embeddings", index_params=index_params)
        logger.info("✅ Index created.")

    def insert_batch(self, vectors, texts, metadatas):
        # --- 🛠️ 字节级截断 ---
        def safe_truncate(text, max_bytes=8192):
            text = text[:max_bytes] 
            encoded = text.encode('utf-8')
            if len(encoded) <= max_bytes:
                return text
            return encoded[:max_bytes].decode('utf-8', 'ignore')

        safe_texts = [safe_truncate(t, max_bytes=8000) for t in texts]
        # -----------------------------

        # 将数据拆解对齐 Schema
        # 注意：这里依赖 metadatas 中包含 'year' 和 'doc_id' 键
        years = [m.get('year', '') for m in metadatas]
        doc_ids = [m.get('doc_id', '') for m in metadatas]
        
        # 执行插入
        self.collection.insert([
            vectors, 
            safe_texts, 
            years, 
            doc_ids, 
            metadatas
        ])

# ================= 流程控制 =================
class Pipeline:
    def __init__(self):
        if os.path.exists(Config.CHECKPOINT_FILE):
            os.remove(Config.CHECKPOINT_FILE)
            logger.warning(f"🗑️ Deleted checkpoint file: {Config.CHECKPOINT_FILE}")

        self.device = self._get_device()
        self.milvus = MilvusClient() 
        self.processor = TextProcessor()
        
        logger.info(f"Loading Model on {self.device}...")
        self.model = SentenceTransformer(Config.EMBEDDING_MODEL, device=self.device)
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
        
        pbar = tqdm(pending_files, desc="Processing Files")
        
        for json_file in pbar:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                
                if isinstance(content, dict): content = [content]
                
                file_chunks = []
                for item in content:
                    file_chunks.extend(self.processor.process_paper(item))
                
                if not file_chunks:
                    self._save_checkpoint(json_file)
                    continue

                for chunk in file_chunks:
                    buffer_texts.append(chunk["text"])
                    buffer_metas.append(chunk["metadata"])
                    
                    if len(buffer_texts) >= Config.BATCH_SIZE:
                        self._flush_buffer(buffer_texts, buffer_metas)
                        buffer_texts = []
                        buffer_metas = []
                
                self._save_checkpoint(json_file)
                
            except Exception as e:
                logger.error(f"Failed to process {json_file}: {e}")
                continue

        if buffer_texts:
            self._flush_buffer(buffer_texts, buffer_metas)
            
        self.milvus.collection.flush()
        logger.info(f"🎉 Job Done. Total Entities: {self.milvus.collection.num_entities}")

    def _flush_buffer(self, texts, metas):
        try:
            embeddings = self.model.encode(texts, normalize_embeddings=True)
            self.milvus.insert_batch(embeddings, texts, metas)
        except Exception as e:
            logger.error(f"⚠️ Batch Insert Error: {e}")

# ================= 入口 =================
if __name__ == "__main__":
    pipeline = Pipeline()
    pipeline.run()