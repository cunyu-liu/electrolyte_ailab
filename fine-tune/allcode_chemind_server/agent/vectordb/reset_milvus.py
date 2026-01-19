from pymilvus import connections, utility

# 连接 Milvus
connections.connect("default", host="localhost", port="19530")

# 删库
collection_name = "electrolyte_papers_chunked"
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)
    print(f"🗑️ 已删除集合: {collection_name}，环境已清理干净。")
else:
    print(f"Collections {collection_name} 不存在，无需删除。")