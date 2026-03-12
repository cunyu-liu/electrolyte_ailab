import os
import json
import math
import glob
import time
import logging
import multiprocessing
from typing import Any
from tqdm import tqdm

# ================= 配置区域 =================
class Config:
    # 输入文件夹（包含你那数十万个 dirty json）
    INPUT_DIR = "./data_dirty"
    
    # 输出文件夹（清洗后的 clean json 存放在这）
    OUTPUT_DIR = "./data_clean"
    
    # 错误日志存放位置
    LOG_FILE = "cleaning_errors.log"
    
    # 并行进程数：建议设置为 CPU 核心数 (如果是机械硬盘，建议设小一点，如 4-8，避免磁盘读写瓶颈)
    NUM_WORKERS = max(1, os.cpu_count() - 1)

# ================= 核心清洗逻辑 =================
def clean_nans(obj: Any) -> Any:
    """
    递归遍历 JSON 对象，将 float('nan') 替换为 None (即 JSON null)
    """
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    elif isinstance(obj, dict):
        return {k: clean_nans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nans(v) for v in obj]
    return obj

# ================= 单文件处理 Worker =================
def process_single_file(file_info):
    """
    Worker 进程执行的函数
    file_info: (source_path, relative_path)
    """
    src_path, rel_path = file_info
    
    # 计算输出路径，保持原有目录结构
    dest_path = os.path.join(Config.OUTPUT_DIR, rel_path)
    
    # 如果目标文件已存在，跳过（断点续传）
    if os.path.exists(dest_path):
        return "skipped"

    try:
        # 1. 读取原始数据
        # Python 的 json 库默认允许读取 NaN，会将其转换为 float('nan')
        with open(src_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 2. 清洗数据 (递归替换)
        cleaned_data = clean_nans(data)
        
        # 3. 确保输出目录存在
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        # 4. 写入新文件 (JSON 标准格式，无 NaN)
        with open(dest_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
            
        return "success"
        
    except json.JSONDecodeError:
        return f"error: JSON 格式严重错误 - {src_path}"
    except Exception as e:
        return f"error: {str(e)} - {src_path}"

# ================= 主程序 =================
def main():
    # 初始化日志
    logging.basicConfig(filename=Config.LOG_FILE, level=logging.ERROR, 
                        format='%(asctime)s - %(message)s')
    
    print(f"🔥 开始扫描文件: {Config.INPUT_DIR}")
    
    # 1. 扫描所有 JSON 文件
    # 使用 os.walk 生成任务列表，保留相对路径结构
    tasks = []
    for root, dirs, files in os.walk(Config.INPUT_DIR):
        for file in files:
            if file.lower().endswith('.json'):
                full_path = os.path.join(root, file)
                # 计算相对路径，用于在 output 目录重建结构
                rel_path = os.path.relpath(full_path, Config.INPUT_DIR)
                tasks.append((full_path, rel_path))
    
    total_files = len(tasks)
    print(f"📦 扫描完成，共发现 {total_files} 个文件")
    print(f"🚀 启动 {Config.NUM_WORKERS} 个进程进行并行清洗...")
    
    # 2. 并行处理
    results_stats = {"success": 0, "skipped": 0, "error": 0}
    
    with multiprocessing.Pool(processes=Config.NUM_WORKERS) as pool:
        # 使用 imap_unordered 提高响应速度，配合 tqdm 显示进度
        for res in tqdm(pool.imap_unordered(process_single_file, tasks), total=total_files):
            if res == "success":
                results_stats["success"] += 1
            elif res == "skipped":
                results_stats["skipped"] += 1
            elif res.startswith("error"):
                results_stats["error"] += 1
                logging.error(res) # 记录具体错误到日志文件

    print("\n✅ 清洗任务结束！")
    print(f"📊 统计结果: {results_stats}")
    print(f"📁 结果保存在: {Config.OUTPUT_DIR}")
    print(f"❌ 错误日志在: {Config.LOG_FILE}")

if __name__ == "__main__":
    main()