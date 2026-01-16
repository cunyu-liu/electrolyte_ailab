import requests

# 服务器的 IP 地址
RAG_API_URL = "http://192.168.1.100:8000/search"

def query_knowledge_base(question):
    payload = {
        "query": question,
        "top_k": 3
    }
    try:
        response = requests.post(RAG_API_URL, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            print("Error:", response.text)
    except Exception as e:
        print("连接失败:", e)

# 测试
result = query_knowledge_base("Li-S电池中DME电解液的配比")
print(result)