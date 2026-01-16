import os
import json
import glob
import logging
import torch  # 引入 torch 以检测 mps
from tqdm import tqdm
import os
# --- 🔥 在最开头添加这两行代码 ---
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
# ------------------------------

import json
import glob
# ... 后面的 import 保持不变
from typing import List, Dict

# --- 依赖库 ---
from pymilvus import connections, Collection, utility, FieldSchema, CollectionSchema, DataType
from sentence_transformers import SentenceTransformer

# =================配置=================
class Config:
    INPUT_DIR = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/paper_text_clean"     
    LOG_DIR = "./logs"
    CHECKPOINT_FILE = os.path.join(LOG_DIR, "step2_processed.log")
    
    # Milvus 配置 (Docker Localhost)
    MILVUS_HOST = "localhost"
    MILVUS_PORT = "19530"
    COLLECTION_NAME = "electrolyte_papers"
    
    # 模型配置
    EMBEDDING_MODEL = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/Xorbits/bge-m3"
    BATCH_SIZE = 1   # Mac 显存共享，稍微调小 Batch Size 以防卡顿，可根据机型调整
    DIMENSION = 1024  

# 确保日志目录存在
os.makedirs(Config.LOG_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# =================功能类封装=================
class MilvusClient:
    def __init__(self):
        # 连接本地 Docker Milvus
        try:
            connections.connect("default", host=Config.MILVUS_HOST, port=Config.MILVUS_PORT)
            print(f"✅ 成功连接到 Milvus ({Config.MILVUS_HOST}:{Config.MILVUS_PORT})")
        except Exception as e:
            print(f"❌ 连接 Milvus 失败，请检查 Docker 是否运行: {e}")
            raise e
            
        self._init_collection()
        
    def _init_collection(self):
        if not utility.has_collection(Config.COLLECTION_NAME):
            print("🚀 初始化 Milvus 集合...")
            fields = [
                FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="embeddings", dtype=DataType.FLOAT_VECTOR, dim=Config.DIMENSION),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="metadata", dtype=DataType.JSON)
            ]
            schema = CollectionSchema(fields, description="电解液知识库")
            self.collection = Collection(Config.COLLECTION_NAME, schema)
            # 创建 HNSW 索引
            index_params = {
                "metric_type": "COSINE", 
                "index_type": "HNSW", 
                "params": {"M": 16, "efConstruction": 200}
            }
            self.collection.create_index(field_name="embeddings", index_params=index_params)
            print("✅ 集合与索引创建完成")
        else:
            self.collection = Collection(Config.COLLECTION_NAME)
            print(f"✅ 加载已有集合: {Config.COLLECTION_NAME}")

    def insert(self, vectors, contents, metadatas):
        # 这里的 insert 返回 MutationResult
        self.collection.insert([vectors, contents, metadatas])

class Checkpoint:
    def __init__(self):
        self.processed = set()
        if os.path.exists(Config.CHECKPOINT_FILE):
            with open(Config.CHECKPOINT_FILE, 'r') as f:
                self.processed = set(line.strip() for line in f if line.strip())
    
    def is_done(self, filepath):
        return os.path.abspath(filepath) in self.processed
    
    def mark_done(self, filepath: str):
        abs_path = os.path.abspath(filepath)
        if abs_path not in self.processed:
            with open(Config.CHECKPOINT_FILE, 'a') as f:
                f.write(abs_path + "\n")
            self.processed.add(abs_path)

# =================主逻辑=================
def main():
    print("⚡ 启动 Mac 向量化入库脚本...")
    
    # 0. 检测设备 (Mac 核心修改点)
    device = "cpu"
    if torch.backends.mps.is_available():
        device = "mps"
        print("🍎 检测到 Apple Silicon，已启用 MPS (Metal) 加速")
    elif torch.cuda.is_available():
        device = "cuda"
        print("🟢 检测到 NVIDIA GPU，已启用 CUDA 加速")
    else:
        print("⚠️ 未检测到 GPU，将使用 CPU 运行 (速度较慢)")

    # 1. 初始化
    milvus = MilvusClient()
    checkpoint = Checkpoint()
    
    print(f"加载 Embedding 模型: {Config.EMBEDDING_MODEL} ...")
    # 这里显式指定 device
    model = SentenceTransformer(Config.EMBEDDING_MODEL, device=device)
    
    # 2. 扫描文件
    if not os.path.exists(Config.INPUT_DIR):
        print(f"❌ 错误：输入目录不存在 {Config.INPUT_DIR}")
        return

    all_jsons = glob.glob(os.path.join(Config.INPUT_DIR, "*.json"))
    pending_files = [f for f in all_jsons if not checkpoint.is_done(f)]
    pending_files.sort() # 排序保证顺序一致
    
    print(f"总文件: {len(all_jsons)}, 待处理: {len(pending_files)}")
    if not pending_files:
        print("✅ 所有文件已处理，无需操作。")
        return
    
    # 3. 循环处理
    buffer_texts = []
    buffer_metadatas = []
    
    # 使用 tqdm 显示进度
    for json_file in tqdm(pending_files, desc="Processing Files"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            # 兼容性处理
            if isinstance(raw_data, dict):
                data_list = [raw_data]
            elif isinstance(raw_data, list):
                data_list = raw_data
            else:
                checkpoint.mark_done(json_file)
                continue

            for item in data_list:
                if not isinstance(item, dict):
                    continue
                
                # --- 组装文本 ---
                title = item.get('title', '')
                abstract = item.get('abstract', '')
                main_text = item.get('main_text', '')
                
                # 拼接
                text_content = f"Title: {title}\nAbstract: {abstract}\nContent: {main_text}"
                
                # Milvus VARCHAR 最大限制 65535。我们限制在 60000 以内确保安全。
                if len(text_content) > 60000:
                    text_content = text_content[:60000] + "...(truncated)"
                
                # 空内容跳过
                if len(text_content) < 10:
                    continue

                # --- 组装 Metadata ---
                # 注意：Metadata 里的字段如果太长也可能导致报错，建议也做简单检查
                meta_dict = {
                    "title": title[:500], # 限制标题长度
                    "doi": item.get('doi', ''),
                    "authors": str(item.get('authors', []))[:1000], # 转字符串并截断，防止作者名单太长
                    "year": str(item.get('year', '')),
                    "journal": str(item.get('journal', ''))[:500],
                    "source_pdf": str(item.get('source_pdf', '')),
                    "citations": str(item.get('citations', []))[:2000] # 引用列表也截一下
                }

                buffer_texts.append(text_content)
                buffer_metadatas.append(meta_dict)
                
                # Buffer 满触发入库
                if len(buffer_texts) >= Config.BATCH_SIZE:
                    try:
                        vectors = model.encode(buffer_texts, normalize_embeddings=True)
                        milvus.insert(vectors, buffer_texts, buffer_metadatas)
                    except Exception as e_insert:
                        # 如果这一批次入库失败，打印更详细的信息以便排查
                        logging.error(f"⚠️ Batch 入库失败: {e_insert}. 尝试跳过此 Batch.")
                        # 可选：这里可以写逻辑把 Batch Size 减半重试，目前先跳过
                    finally:
                        # 无论成功失败，都要清空 Buffer，防止死循环
                        buffer_texts = []
                        buffer_metadatas = []
            
            # 标记文件完成
            checkpoint.mark_done(json_file)
                
        except Exception as e:
            logging.error(f"❌ 处理文件失败 {json_file}: {e}")
            continue

    # 4. 处理剩余 Buffer (Flush)
    if buffer_texts:
        print(f"🧹 处理剩余 {len(buffer_texts)} 条数据...")
        vectors = model.encode(buffer_texts, normalize_embeddings=True)
        milvus.insert(vectors, buffer_texts, buffer_metadatas)
    
    # 5. 强制落盘
    milvus.collection.flush()
    # 打印统计信息
    row_count = milvus.collection.num_entities
    print(f"\n✅ 入库完成！集合当前总实体数: {row_count}")

if __name__ == "__main__":
    main()