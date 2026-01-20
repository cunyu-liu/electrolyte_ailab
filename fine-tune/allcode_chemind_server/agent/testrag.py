import requests
import json
import time

# API 地址
url = "http://127.0.0.1:8000/chat"

# 测试问题
payload = {
    "question": "作者包括Aschi、Brönstrup的论文有哪些？"
}

print(f"[{time.strftime('%H:%M:%S')}] 1. 正在尝试连接服务器...")

try:
    # 设置 timeout 为 300秒 (5分钟)，防止因为模型慢而报错
    # 记录开始时间
    start_time = time.time()
    
    print(f"[{time.strftime('%H:%M:%S')}] 2. 请求已发送，正在等待模型思考（本地运行可能需要 1-3 分钟，请耐心等待）...")
    
    response = requests.post(url, json=payload, timeout=3000)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"[{time.strftime('%H:%M:%S')}] 3. 收到响应！耗时: {duration:.2f} 秒")

    if response.status_code == 200:
        data = response.json()
        
        print("\n" + "="*50)
        print("【模型回答】:")
        print(data["answer"])
        print("="*50)
        
        # 打印调试信息，确认是检索慢还是生成慢
        if "query_analysis" in data:
            print(f"\n【Query分析】: {data['query_analysis']}")
            
        print(f"\n【验证结果】: {data['verification']}")
        
        print(f"\n【检索到的相关片段数】: {len(data['context_used'])}")
        
    else:
        print(f"服务器返回错误: {response.status_code}")
        print("错误内容:", response.text)

except requests.exceptions.ConnectionError:
    print("\n【错误】连接被拒绝！")
    print("可能原因：")
    print("1. 服务端脚本没有运行。")
    print("2. 服务端还在启动中（还在连 Milvus/ES），端口还没打开。")
    print("3. 地址 http://127.0.0.1:8000 写错了。")

except requests.exceptions.ReadTimeout:
    print("\n【错误】请求超时（超过5分钟）！")
    print("可能原因：模型推理太慢，或者代码陷入死循环。")

except Exception as e:
    print(f"\n【未知错误】: {e}")