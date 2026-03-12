from pymilvus import connections, utility

connections.connect("default", host="localhost", port="19530")

collection_name = "electrolyte_papers"

if utility.has_collection(collection_name):
    print(f"正在删除旧集合: {collection_name}")
    utility.drop_collection(collection_name)
    print("删除成功")
else:
    print("集合不存在")