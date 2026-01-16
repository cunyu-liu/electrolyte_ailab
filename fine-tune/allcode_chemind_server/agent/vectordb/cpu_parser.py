import os
import json
import glob
import time
import logging
import multiprocessing
from typing import Dict, List
from tqdm import tqdm


'''
核心逻辑：

使用 multiprocessing.Pool 利用多核 CPU 并行解析。

解析完成后，将结果保存为 JSON 文件存入硬盘。

完全不涉及 GPU 和 Milvus。
'''

# --- 第三方库 ---
# 实际生产中建议使用 MinerU SDK，这里用 LangChain 做演示
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# =================配置=================a
class Config:
    SOURCE_DIR = "./data_source"          # 原始 PDF 文件夹
    OUTPUT_DIR = "./data_intermediate"    # 解析结果保存文件夹
    LOG_DIR = "./logs"
    
    NUM_WORKERS = min(os.cpu_count(), 32) # 并行进程数，不要超过 CPU 核数
    CHUNK_SIZE = 512
    CHUNK_OVERLAP = 100

# =================日志初始化=================
os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
os.makedirs(Config.LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(Config.LOG_DIR, "step1_parser.log"),
    level=logging.INFO,
    format='%(asctime)s - %(processName)s - %(message)s'
)

# =================Worker 函数=================
# 注意：此函数必须在顶层定义，以便 multiprocessing 序列化
def process_single_pdf(file_path: str):
    """
    单个 PDF 处理逻辑：读取 -> 清洗 -> 切分 -> 保存 JSON
    """
    file_name = os.path.basename(file_path)
    # 生成输出文件路径：data_intermediate/xxxx.pdf.json
    output_json_path = os.path.join(Config.OUTPUT_DIR, f"{file_name}.json")
    
    # 1. 跳过已处理文件 (断点续传)
    if os.path.exists(output_json_path):
        return "skipped"

    try:
        # --- [核心] 解析逻辑 ---
        # 工业界建议替换为 MinerU 或 Unstructured
        loader = PyPDFLoader(file_path)
        pages = loader.load() 
        
        # 切分器初始化 (在进程内初始化，避免锁)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=Config.CHUNK_SIZE, 
            chunk_overlap=Config.CHUNK_OVERLAP
        )
        chunks = splitter.split_documents(pages)
        
        # 提取数据
        processed_data = []
        for chunk in chunks:
            processed_data.append({
                "text": chunk.page_content,
                "metadata": {
                    "source": file_name,
                    "page": chunk.metadata.get("page", 0),
                    # 可以在这里增加更多元数据提取逻辑，如年份、作者
                }
            })
            
        # 2. 写入中间文件 (JSON)
        if processed_data:
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, ensure_ascii=False)
            return "success"
        else:
            logging.warning(f"空文件: {file_name}")
            return "empty"

    except Exception as e:
        error_msg = f"解析失败 {file_name}: {str(e)}"
        logging.error(error_msg)
        return "error"

# =================主控制流程=================
def main():
    print(f"🔥 启动 CPU 并行解析脚本 | 进程数: {Config.NUM_WORKERS}")
    
    # 1. 获取所有 PDF
    all_pdfs = glob.glob(os.path.join(Config.SOURCE_DIR, "**/*.pdf"), recursive=True)
    print(f"发现 PDF 总数: {len(all_pdfs)}")
    
    # 2. 启动多进程池
    # 使用 imap_unordered 可以实时获取结果，且不阻塞进度条
    with multiprocessing.Pool(processes=Config.NUM_WORKERS) as pool:
        # tqdm 包装迭代器以显示进度
        results = list(tqdm(
            pool.imap_unordered(process_single_pdf, all_pdfs),
            total=len(all_pdfs),
            desc="Parsing PDFs"
        ))
    
    # 3. 统计结果
    stats = {"success": 0, "skipped": 0, "error": 0, "empty": 0}
    for res in results:
        stats[res] = stats.get(res, 0) + 1
        
    print("\n✅ 解析阶段结束")
    print(f"统计: {stats}")

if __name__ == "__main__":
    main()