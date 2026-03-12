from modelscope import snapshot_download

# 下载 BGE-M3 模型到当前目录下的 bge-m3 文件夹
model_dir = snapshot_download('Xorbits/bge-m3', cache_dir='./')
print(f"模型已下载到: {model_dir}")