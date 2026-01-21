import os
import json
import glob
import logging
import torch
from tqdm import tqdm
from typing import List, Dict, Any
import hashlib

# --- 新增依赖 ---
import pdfplumber
from docx import Document
import re  # [新增] 正则表达式库用于清洗
# ----------------

# --- 🔥 HF 镜像加速 ---
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
# ------------------------------

from pymilvus import connections, Collection, utility, FieldSchema, CollectionSchema, DataType
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

# =================配置中心 (保持不变)=================
class Config:
    INPUT_DIR = "/Users/liucunyu/Documents/课题idea 数据 结论/Thu化工院张强课题组25实习/Qwen3微调数据/rag 硬件数据"
    LOG_DIR = "./logs"
    CHECKPOINT_FILE = os.path.join(LOG_DIR, "step3-hardware_processed.log")
    MILVUS_HOST = "localhost"
    MILVUS_PORT = "19530"
    COLLECTION_NAME = "electrolyte_papers_chunked" 
    EMBEDDING_MODEL = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/Xorbits/bge-m3"
    CHUNK_SIZE = 800        
    CHUNK_OVERLAP = 150     
    BATCH_SIZE = 2         
    DIMENSION = 1024        

os.makedirs(Config.LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(os.path.join(Config.LOG_DIR, "import_job.log")), logging.StreamHandler()]
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

    # --- [新增] 清洗逻辑 ---
    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        
        # 1. 修复断词 (Hyphenation fix): "pro-\ncess" -> "process"
        # 很多 PDF 行尾会有连字符，直接解析会截断单词
        text = re.sub(r'-\n(\w+)', r'\1', text)
        
        # 2. 替换不可见字符 (除了换行符 \n, \r, \t)
        # 移除控制字符，防止数据库写入报错
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        
        # 3. 规范化空白：将连续的宽空白(如制表符)转为单个空格，但保留换行符用于分段
        # 注意：这里不使用 \s+ -> " "，因为要保留段落结构给 Splitter 切分
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 4. 去除多余的空行 (超过2个换行符的压缩为2个，保留段落感)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    # ---------------------

    def read_file(self, filepath: str) -> List[Dict]:
        ext = os.path.splitext(filepath)[1].lower()
        filename = os.path.basename(filepath)
        
        base_data = {
            "title": filename,
            "doi": "", "year": "", "journal": "", "abstract": "", "authors": [],
            "source_pdf": filename
        }

        try:
            if ext == '.json':
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                # JSON 通常已经是清洗过的，但为了保险也可以过一遍
                data_list = content if isinstance(content, list) else [content]
                # 针对 JSON 里的 main_text 做清洗
                for item in data_list:
                    if 'main_text' in item:
                        item['main_text'] = self._clean_text(item['main_text'])
                return data_list
            
            elif ext == '.pdf':
                text = ""
                with pdfplumber.open(filepath) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                
                # [修改点] 应用清洗
                base_data["main_text"] = self._clean_text(text)
                return [base_data]

            elif ext in ['.docx', '.doc']:
                doc = Document(filepath)
                text = "\n".join([para.text for para in doc.paragraphs])
                
                # [修改点] 应用清洗
                base_data["main_text"] = self._clean_text(text)
                return [base_data]
            
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error reading file {filepath}: {e}")
            return []

    def process_paper(self, paper_data: Dict) -> List[Dict]:
        chunks = []
        title = paper_data.get('title', 'Unknown Title')
        doc_id = paper_data.get('doi') or self._generate_doc_id(title)
        
        # 1. Abstract
        abstract = paper_data.get('abstract', '').strip()
        if abstract:
            # 摘要也清洗一下
            abstract = self._clean_text(abstract) 
            text_content = f"Title: {title}\nSection: Abstract\nContent: {abstract}"
            chunks.append({
                "text": text_content,
                "metadata": self._build_metadata(paper_data, "Abstract", 0, doc_id)
            })

        # 2. Main Text
        main_text = paper_data.get('main_text', '').strip()
        if main_text:
            # 注意：read_file 已经清洗过 main_text，这里直接切分
            raw_chunks = self.text_splitter.split_text(main_text)
            for idx, chunk_text in enumerate(raw_chunks):
                enriched_text = f"Title: {title}\nContent: {chunk_text}"
                chunks.append({
                    "text": enriched_text,
                    "metadata": self._build_metadata(paper_data, "MainBody", idx + 1, doc_id)
                })
        return chunks

    def _build_metadata(self, original_data: Dict, section: str, chunk_index: int, doc_id: str) -> Dict:
        title_str = str(original_data.get('title', ''))
        return {
            "title": title_str[:500],
            "doi": str(original_data.get('doi', '')),
            "authors": str(original_data.get('authors', []))[:1000],
            "year": str(original_data.get('year', '')),
            "journal": str(original_data.get('journal', ''))[:500],
            "source_pdf": str(original_data.get('source_pdf', '')),
            "citations": str(original_data.get('citations', []))[:2000],
            "doc_id": doc_id,
            "chunk_type": section,
            "chunk_index": chunk_index
        }

    def _generate_doc_id(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

# ================= 数据库客户端 (保持不变) =================
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

    # 修改后的 _init_collection_reset 方法
    def _init_collection_reset(self):
        # [新增] 检查是否存在，存在则复用（追加模式）
        if utility.has_collection(Config.COLLECTION_NAME):
            logger.info(f"🔄 监测到已存在集合: {Config.COLLECTION_NAME}，切换为【追加模式】(Append Mode)")
            self.collection = Collection(Config.COLLECTION_NAME)
            self.collection.load() # 加载到内存，确保可用
            return

        # --- 以下保持原有的创建逻辑不变 ---
        # 只有当集合不存在时，才执行创建
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
        def safe_truncate(text, max_bytes=8192):
            text = text[:max_bytes] 
            encoded = text.encode('utf-8')
            if len(encoded) <= max_bytes:
                return text
            return encoded[:max_bytes].decode('utf-8', 'ignore')

        safe_texts = [safe_truncate(t, max_bytes=8000) for t in texts]
        years = [m.get('year', '') for m in metadatas]
        doc_ids = [m.get('doc_id', '') for m in metadatas]
        
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
        # if os.path.exists(Config.CHECKPOINT_FILE):
        #     os.remove(Config.CHECKPOINT_FILE)
        #     logger.warning(f"🗑️ Deleted checkpoint file: {Config.CHECKPOINT_FILE}")

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
        # --- [修改] 支持多文件格式搜索 ---
        # 递归搜索所有支持的格式
        extensions = ['*.json', '*.pdf', '*.docx', '*.doc']
        all_files = []
        for ext in extensions:
            all_files.extend(glob.glob(os.path.join(Config.INPUT_DIR, ext)))
        
        all_files = sorted(list(set(all_files))) # 去重并排序
        # -----------------------------
        
        pending_files = [f for f in all_files if os.path.abspath(f) not in self.processed_files]
        
        logger.info(f"Total Files: {len(all_files)}, Pending: {len(pending_files)}")
        
        buffer_texts = []
        buffer_metas = []
        
        pbar = tqdm(pending_files, desc="Processing Files")
        
        for file_path in pbar:
            try:
                # --- [修改] 使用统一的读取方法 ---
                # 将原来的 open + json.load 替换为 read_file
                content_list = self.processor.read_file(file_path)
                
                # 如果是空列表（解析失败或空文件），跳过
                if not content_list:
                    self._save_checkpoint(file_path)
                    continue

                file_chunks = []
                for item in content_list:
                    file_chunks.extend(self.processor.process_paper(item))
                # -----------------------------
                
                if not file_chunks:
                    self._save_checkpoint(file_path)
                    continue

                for chunk in file_chunks:
                    buffer_texts.append(chunk["text"])
                    buffer_metas.append(chunk["metadata"])
                    
                    if len(buffer_texts) >= Config.BATCH_SIZE:
                        self._flush_buffer(buffer_texts, buffer_metas)
                        buffer_texts = []
                        buffer_metas = []
                
                self._save_checkpoint(file_path)
                
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
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

if __name__ == "__main__":
    pipeline = Pipeline()
    pipeline.run()