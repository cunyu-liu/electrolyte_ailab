import requests
import time

# 配置
URL = "http://127.0.0.1:8000/chat"  # 注意：去掉了末尾空格
TIMEOUT = 300  # 5分钟超时

# 测试问题
payload = {
    "question": "我需要开发一款用于高电压（4.5V）锂金属电池的电解液，目标是库伦效率超过99.5%，同时保持良好的循环寿命。请利用现有最新的文献寻找灵感。",
    "top_k": 3,
    "generate_citations": True
}

print(f"[{time.strftime('%H:%M:%S')}] 正在连接 {URL}...")

try:
    start_time = time.time()
    
    print(f"[{time.strftime('%H:%M:%S')}] 发送请求（本地模型可能需要1-3分钟）...")
    response = requests.post(URL, json=payload, timeout=TIMEOUT)
    
    duration = time.time() - start_time
    print(f"[{time.strftime('%H:%M:%S')}] 收到响应！耗时: {duration:.2f} 秒")

    if response.status_code == 200:
        data = response.json()
        
        print("\n" + "="*60)
        print("【回答内容】:")
        print("="*60)
        print(data.get("answer", "无回答"))
        print("="*60)
        
        # 显示检索统计
        stats = data.get("retrieval_stats", {})
        print(f"\n检索统计:")
        print(f"  - 识别场景: {stats.get('detected_intent', 'N/A')}")
        print(f"  - 命中文献: {stats.get('returned_papers', 0)} 篇")
        
        # 显示引用
        citations = data.get("citations", [])
        if citations:
            print(f"\n参考来源:")
            for i, cite in enumerate(citations[:10], 1):
                title = cite.get('title', 'Unknown')[:50]
                score = cite.get('relevance_score', 0)
                print(f"  [{i}] {title}... (相关度: {score:.2f})")
                
    else:
        print(f"\n❌ 服务器返回错误: {response.status_code}")
        print(response.text)

except requests.exceptions.ConnectionError:
    print("\n❌ 连接失败！请检查：")
    print("  1. 服务端是否已启动 (python server.py)")
    print("  2. Milvus/ES 是否已完成初始化")
    print("  3. 地址和端口是否正确")

except requests.exceptions.Timeout:
    print(f"\n⏱️ 请求超时（超过{TIMEOUT}秒）")

except Exception as e:
    print(f"\n❌ 发生错误: {e}")