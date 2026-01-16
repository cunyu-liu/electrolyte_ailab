import os
import time

# ================= 配置区 =================
# 1. 设置国内镜像环境变量 (关键步骤)
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 2. 你想下载的模型 ID (这里是 Reranker)
MODEL_ID = "BAAI/bge-reranker-v2-m3"

# 3. 下载保存的本地目录
LOCAL_DIR = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/vectordb/bge-reranker-v2-m3"
# =========================================

def download_model():
    print(f"🚀 准备从国内镜像下载模型: {MODEL_ID}")
    print(f"📂 保存路径: {os.path.abspath(LOCAL_DIR)}")
    print("⏳ 正在连接镜像站，请稍候...")
    
    try:
        # 尝试导入 huggingface_hub，如果没有安装会自动提示
        from huggingface_hub import snapshot_download
    except ImportError:
        print("❌ 缺少必要库，请先运行: pip install huggingface_hub")
        return

    try:
        # 开始下载
        # resume_download=True 允许断点续传
        # ignore_patterns 排除不需要的大文件（如 flax/tf 权重），只下 pytorch
        snapshot_download(
            repo_id=MODEL_ID,
            local_dir=LOCAL_DIR,
            local_dir_use_symlinks=False, # 确保下载的是真实文件而不是软链接
            resume_download=True,
            ignore_patterns=["*.h5", "*.ot", "*.msgpack", "*.safetensors.index.json"], 
            # 注意：safetensors 是首选权重，如果模型只有 bin，就把 bin 下下来
        )
        print("\n✅ 下载完成！")
        print(f"现在你可以将 RERANKER_MODEL_NAME 设置为: {os.path.abspath(LOCAL_DIR)}")
        
    except Exception as e:
        print(f"\n❌ 下载出错: {e}")
        print("💡 建议：")
        print("1. 检查网络连接")
        print("2. 重新运行此脚本（支持断点续传）")

if __name__ == "__main__":
    download_model()