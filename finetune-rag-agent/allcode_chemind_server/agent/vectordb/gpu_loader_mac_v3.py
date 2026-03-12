import os
import json
import glob
import logging
import torch
from tqdm import tqdm
from typing import List, Dict, Any
import hashlib

# 这波是针对deep research 做了更精细的划分。

import os
import json
import glob
import logging
import torch
import re
from tqdm import tqdm
from typing import List, Dict, Any, Tuple, Optional
import hashlib

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from pymilvus import connections, Collection, utility, FieldSchema, CollectionSchema, DataType
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ================= 配置中心（增强版）=================
class Config:
    INPUT_DIR = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/paper_text_clean"
    LOG_DIR = "./logs"
    CHECKPOINT_FILE = os.path.join(LOG_DIR, "step2_processed_v3.log")
    
    MILVUS_HOST = "localhost"
    MILVUS_PORT = "19530"
    COLLECTION_NAME = "electrolyte_papers_chunked_v3"  # 建议新版本号避免冲突
    
    EMBEDDING_MODEL = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/Xorbits/bge-m3"
    
    CHUNK_SIZE = 800        
    CHUNK_OVERLAP = 150     
    BATCH_SIZE = 2         
    DIMENSION = 1024        
    
    # 【新增】追踪字符位置的最大文本长度（防止内存爆炸）
    MAX_TEXT_TRACK_LENGTH = 50000  

os.makedirs(Config.LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(Config.LOG_DIR, "import_job_precision.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ================= 核心：精确位置追踪处理器 =================
class TextProcessor:
    """
    增强版文本处理器：支持字符级精确位置追踪和章节识别
    """
    
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", ".", " ", ""],
            # 【关键】保持字符位置追踪的附加参数
            add_start_index=True,  # 记录每个chunk在原始文本中的起始位置
        )
        
        # 章节标题识别模式（学术论文常见结构）
        self.section_patterns = [
            r'^(?:\d+\.)?\s*(Introduction| introduction)',
            r'^(?:\d+\.)?\s*(Experimental|Methods|Methodology)',
            r'^(?:\d+\.)?\s*(Results\s+and\s+Discussion|Results)',
            r'^(?:\d+\.)?\s*(Discussion)',
            r'^(?:\d+\.)?\s*(Conclusion|Conclusions)',
            r'^(?:\d+\.)?\s*(Abstract)',
            r'^(?:\d+\.)?\s*(References)',
        ]

    def process_paper(self, paper_data: Dict) -> List[Dict]:
        """
        处理单篇论文，返回带精确位置信息的chunks
        """
        chunks = []
        title = paper_data.get('title', 'Unknown Title')
        doc_id = paper_data.get('doi') or self._generate_doc_id(title)
        
        # 【新增】提取全文字符映射和页码标记
        full_text_map = self._build_text_map(paper_data)
        
        # 1. 处理摘要（通常被视为第0页或第1页）
        abstract = paper_data.get('abstract', '').strip()
        if abstract:
            abs_chunk = self._process_with_position(
                text=abstract,
                text_type="Abstract",
                doc_id=doc_id,
                base_offset=0,  # 摘要通常在开头
                page_num=0,     # 摘要视为第0页
                paper_data=paper_data
            )
            if abs_chunk:
                abs_chunk["metadata"]["section_title"] = "Abstract"
                chunks.append(abs_chunk)

        # 2. 处理正文（带页码识别）
        main_text = paper_data.get('main_text', '').strip()
        if main_text:
            # 如果原始文本包含页码标记（如 [Page 5]），提取并分割
            pages = self._split_by_pages(main_text) if self._has_page_markers(main_text) else [(1, main_text)]
            
            global_char_offset = len(abstract) + 1 if abstract else 0  # 摘要后的全局偏移
            
            for page_num, page_content in pages:
                # 在此页内分块
                page_chunks = self._split_with_position_tracking(
                    text=page_content,
                    doc_id=doc_id,
                    base_offset=global_char_offset,
                    page_num=page_num,
                    paper_data=paper_data
                )
                
                # 识别章节标题
                page_chunks = self._assign_section_titles(page_chunks, page_content)
                chunks.extend(page_chunks)
                
                # 更新全局偏移
                global_char_offset += len(page_content) + 1

        return chunks

    def _build_text_map(self, paper_data: Dict) -> Dict:
        """
        构建全文字符映射，用于后续精确定位
        """
        abstract = paper_data.get('abstract', '')
        main_text = paper_data.get('main_text', '')
        
        return {
            'abstract_length': len(abstract),
            'main_text_length': len(main_text),
            'full_text': abstract + '\n' + main_text if abstract else main_text
        }

    def _has_page_markers(self, text: str) -> bool:
        """检查文本是否包含页码标记"""
        page_markers = ['[Page ', '--- Page ', '\nPage ', 'PDF Page']
        return any(marker in text for marker in page_markers)

    def _split_by_pages(self, text: str) -> List[Tuple[int, str]]:
        """
        根据页码标记分割文本
        支持格式：[Page 1], --- Page 2 ---, 等
        返回: [(page_num, content), ...]
        """
        # 匹配常见的页码标记
        pattern = r'(?:\[Page\s*(\d+)\]|\-\-\-\s*Page\s*(\d+)\s*\-\-\-|\nPage\s*(\d+)\n)'
        
        parts = re.split(pattern, text)
        pages = []
        current_page = 1
        
        if len(parts) == 1:
            # 没有页码标记，返回整体
            return [(1, text)]
        
        # parts结构: [text_before, page_num1, text_after1, page_num2, text_after2, ...]
        for i in range(0, len(parts)-1, 2):
            if i == 0 and parts[i].strip():
                # 第一页前没有页码标记的内容
                pages.append((1, parts[i].strip()))
            
            # 提取页码（三个捕获组中有一个匹配）
            page_num_str = next((p for p in parts[i+1:i+4] if p), None)
            if page_num_str:
                current_page = int(page_num_str)
            
            # 对应页的内容
            if i+4 < len(parts):
                content = parts[i+4] if i+4 < len(parts) else ""
                if content.strip():
                    pages.append((current_page, content.strip()))
        
        return pages if pages else [(1, text)]

    def _split_with_position_tracking(
        self, 
        text: str, 
        doc_id: str, 
        base_offset: int, 
        page_num: int,
        paper_data: Dict
    ) -> List[Dict]:
        """
        使用LangChain分块并精确追踪字符位置
        """
        chunks = []
        
        # 使用split_text_with_metadata获取起始位置
        try:
            # 新版本LangChain支持直接返回起始索引
            raw_chunks = self.text_splitter.create_documents([text])
            
            for doc in raw_chunks:
                chunk_text = doc.page_content
                # 计算在原始全文中的绝对位置
                start_idx = doc.metadata.get('start_index', 0)
                
                # 如果text_splitter没有提供start_index，手动查找（较慢但可靠）
                if start_idx == 0 and chunk_text not in text[:100]:
                    start_idx = text.find(chunk_text[:50])  # 用前50字符定位
                
                absolute_start = base_offset + start_idx
                absolute_end = absolute_start + len(chunk_text)
                
                # 章节检测（简单启发式）
                section_title = self._detect_section_by_content(chunk_text, text[:start_idx])
                
                metadata = self._build_precision_metadata(
                    paper_data=paper_data,
                    section="MainBody",
                    chunk_index=len(chunks),
                    doc_id=doc_id,
                    page_num=page_num,
                    start_char=absolute_start,
                    end_char=absolute_end,
                    section_title=section_title
                )
                
                enriched_text = f"Title: {paper_data.get('title', '')}\nContent: {chunk_text}"
                
                chunks.append({
                    "text": enriched_text,
                    "metadata": metadata,
                    # 【调试信息】用于验证
                    "debug": {
                        "relative_start": start_idx,
                        "page_offset": base_offset
                    }
                })
                
        except Exception as e:
            logger.error(f"Error in position tracking: {e}, falling back to simple chunking")
            # 降级处理：普通分块，位置标记为0
            simple_chunks = self.text_splitter.split_text(text)
            for idx, chunk_text in enumerate(simple_chunks):
                metadata = self._build_precision_metadata(
                    paper_data=paper_data,
                    section="MainBody",
                    chunk_index=idx,
                    doc_id=doc_id,
                    page_num=page_num,
                    start_char=0,  # 降级时无法确定
                    end_char=0,
                    section_title="Unknown"
                )
                chunks.append({
                    "text": f"Title: {paper_data.get('title', '')}\nContent: {chunk_text}",
                    "metadata": metadata
                })
        
        return chunks

    def _process_with_position(
        self,
        text: str,
        text_type: str,
        doc_id: str,
        base_offset: int,
        page_num: int,
        paper_data: Dict
    ) -> Optional[Dict]:
        """处理摘要或其他单一区块"""
        if not text:
            return None
            
        metadata = self._build_precision_metadata(
            paper_data=paper_data,
            section=text_type,
            chunk_index=0,
            doc_id=doc_id,
            page_num=page_num,
            start_char=base_offset,
            end_char=base_offset + len(text),
            section_title=text_type
        )
        
        return {
            "text": f"Title: {paper_data.get('title', '')}\nSection: {text_type}\nContent: {text}",
            "metadata": metadata
        }

    def _detect_section_by_content(self, chunk_text: str, preceding_text: str) -> str:
        """
        基于内容启发式检测章节标题
        """
        # 检查chunk开头是否包含章节标题
        for pattern in self.section_patterns:
            match = re.match(pattern, chunk_text.strip(), re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # 检查前一个文本块的结尾（章节标题可能在上一页末尾）
        lines = preceding_text.strip().split('\n')
        if lines:
            last_line = lines[-1].strip()
            for pattern in self.section_patterns:
                if re.match(pattern, last_line, re.IGNORECASE):
                    return re.match(pattern, last_line, re.IGNORECASE).group(1).strip()
        
        return "Unknown"

    def _assign_section_titles(self, chunks: List[Dict], page_content: str) -> List[Dict]:
        """
        为chunks分配章节标题（基于整个页面的上下文）
        """
        lines = page_content.split('\n')
        current_section = "Unknown"
        
        for chunk in chunks:
            # 检查此chunk是否包含章节标题
            chunk_start = chunk.get("debug", {}).get("relative_start", 0)
            
            # 找到对应原始文本位置附近的行
            text_before = page_content[:chunk_start]
            recent_lines = text_before.split('\n')[-5:]  # 前5行
            
            for line in recent_lines:
                for pattern in self.section_patterns:
                    if re.match(pattern, line.strip(), re.IGNORECASE):
                        current_section = re.match(pattern, line.strip(), re.IGNORECASE).group(1).strip()
                        break
            
            if chunk["metadata"]["section_title"] == "Unknown":
                chunk["metadata"]["section_title"] = current_section
        
        return chunks

    def _build_precision_metadata(
        self, 
        paper_data: Dict, 
        section: str, 
        chunk_index: int, 
        doc_id: str,
        page_num: int = 0,
        start_char: int = 0,
        end_char: int = 0,
        section_title: str = "Unknown"
    ) -> Dict:
        """
        【核心】构建包含精确定位的Metadata
        """
        return {
            # 基础信息（原有）
            "title": str(paper_data.get('title', ''))[:500],
            "doi": str(paper_data.get('doi', '')),
            "authors": str(paper_data.get('authors', []))[:1000],
            "year": str(paper_data.get('year', '')),
            "journal": str(paper_data.get('journal', ''))[:500],
            "source_pdf": str(paper_data.get('source_pdf', '')),
            "citations": str(paper_data.get('citations', []))[:2000],
            "doc_id": doc_id,
            "chunk_type": section,
            "chunk_index": chunk_index,
            
            # 【新增】精确定位字段（Deep Research必需）
            "page_num": int(page_num),          # 页码（从0或1开始）
            "paragraph_idx": int(chunk_index),  # 段落序号（同chunk_index）
            "start_char": int(start_char),      # 在全文的起始字符位置
            "end_char": int(end_char),          # 在全文的结束字符位置
            "section_title": str(section_title)[:200],  # 所属章节标题
            
            # 【可选】字符长度校验（用于调试）
            "char_length": int(end_char - start_char)
        }

    def _generate_doc_id(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

# ================= 增强的Milvus客户端 =================
class MilvusClient:
    def __init__(self):
        self._connect()
        self._init_collection_schema()

    def _connect(self):
        try:
            connections.connect("default", host=Config.MILVUS_HOST, port=Config.MILVUS_PORT)
            logger.info(f"✅ Milvus Connected: {Config.MILVUS_HOST}")
        except Exception as e:
            logger.error(f"❌ Milvus Connection Failed: {e}")
            raise e

    def _init_collection_schema(self):
        """
        【核心修改】初始化支持精确定位的Schema
        """
        if utility.has_collection(Config.COLLECTION_NAME):
            utility.drop_collection(Config.COLLECTION_NAME)
            logger.warning(f"🗑️ Dropped existing collection: {Config.COLLECTION_NAME}")
        
        logger.info(f"🚀 Creating new collection with precision fields: {Config.COLLECTION_NAME}")
        
        fields = [
            FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="embeddings", dtype=DataType.FLOAT_VECTOR, dim=Config.DIMENSION),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192), 
            
            # 原有字段
            FieldSchema(name="year", dtype=DataType.VARCHAR, max_length=10),
            FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=128),
            
            # 【新增】精确定位字段（独立字段便于索引和查询）
            FieldSchema(name="page_num", dtype=DataType.INT32),      # 页码
            FieldSchema(name="start_char", dtype=DataType.INT32),    # 起始字符
            FieldSchema(name="end_char", dtype=DataType.INT32),      # 结束字符
            FieldSchema(name="section_title", dtype=DataType.VARCHAR, max_length=200),
            
            # JSON存储其他metadata（保持灵活性）
            FieldSchema(name="metadata", dtype=DataType.JSON)
        ]
        
        schema = CollectionSchema(fields, description="Electrolyte Papers with Precision Location")
        self.collection = Collection(Config.COLLECTION_NAME, schema)
        
        # 创建索引
        index_params = {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {"M": 16, "efConstruction": 250}
        }
        self.collection.create_index(field_name="embeddings", index_params=index_params)
        
        # 【可选】为常用过滤字段创建索引（如果需要按页码/章节查询）
        # self.collection.create_index(field_name="page_num")
        
        logger.info("✅ Schema created with precision location fields")

    def insert_batch(self, vectors, texts, metadatas: List[Dict]):
        """
        【修改】适配新的Schema，分离精确定位字段到独立列
        """
        def safe_truncate(text, max_bytes=8192):
            text = text[:max_bytes] 
            encoded = text.encode('utf-8')
            if len(encoded) <= max_bytes:
                return text
            return encoded[:max_bytes].decode('utf-8', 'ignore')

        safe_texts = [safe_truncate(t, max_bytes=8000) for t in texts]
        
        # 提取独立字段（如果不存在则给默认值，保证兼容性）
        years = [str(m.get('year', '')) for m in metadatas]
        doc_ids = [str(m.get('doc_id', '')) for m in metadatas]
        page_nums = [int(m.get('page_num', 0)) for m in metadatas]
        start_chars = [int(m.get('start_char', 0)) for m in metadatas]
        end_chars = [int(m.get('end_char', 0)) for m in metadatas]
        section_titles = [str(m.get('section_title', 'Unknown'))[:200] for m in metadatas]
        
        # 清理metadata中已提取到独立字段的数据（避免重复存储，可选）
        clean_metadatas = []
        for m in metadatas:
            clean_m = {k: v for k, v in m.items() if k not in [
                'page_num', 'start_char', 'end_char', 'section_title', 'year', 'doc_id'
            ]}
            clean_metadatas.append(clean_m)
        
        try:
            self.collection.insert([
                vectors, 
                safe_texts, 
                years, 
                doc_ids,
                page_nums,      # 【新增】
                start_chars,    # 【新增】
                end_chars,      # 【新增】
                section_titles, # 【新增】
                clean_metadatas
            ])
        except Exception as e:
            logger.error(f"Insert error: {e}")
            # 如果失败，尝试旧格式插入（降级）
            logger.warning("Trying legacy insert format...")
            self.collection.insert([
                vectors, safe_texts, years, doc_ids, metadatas
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
                
                if isinstance(content, dict): 
                    content = [content]
                
                file_chunks = []
                for item in content:
                    chunks = self.processor.process_paper(item)
                    file_chunks.extend(chunks)
                    pbar.set_postfix({"chunks": len(file_chunks)})
                
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
                logger.error(f"Failed to process {json_file}: {e}", exc_info=True)
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