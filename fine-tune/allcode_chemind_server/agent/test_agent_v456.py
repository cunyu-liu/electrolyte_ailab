import requests
import json
import time
import sys


'''
既然你要求极致，我还得提醒你一个“院士级”的细节：
目前的 HTTP 请求是同步阻塞的（Blocking）。也就是说，Agent 在跑那 15 步循环的时候，你的 Python 脚本只能干等着，屏幕上是一片死寂。

下一步优化建议（高阶玩法）： 如果你想看到 ChatGPT 那样**流式（Streaming）**的输出（字是一个个蹦出来的，或者日志是一行行打印出来的），我们需要利用 Python 的 yield 和 FastAPI 的 StreamingResponse，配合 Server-Sent Events (SSE)。

如果你想实现这种“边思考边打印”的效果，告诉我，我会在下一次迭代中帮你实现 SSE 流式输出。现在，先跑通这个同步版本，验证你的逻辑闭环是否成立。
'''


# ================= 配置区 =================
# Agent 服务地址
API_URL = "http://127.0.0.1:8000/run"

# 模拟一个复杂的科研需求，触发完整的“设计-实验-优化”闭环
TEST_REQUIREMENT = (
    "我需要开发一款用于高电压（4.5V）锂金属电池的电解液，"
    "目标是库伦效率超过99.5%，同时保持良好的循环寿命。"
    "请利用现有文献寻找灵感，并进行配方优化。"
)
# =========================================

def print_step(title, content):
    """打印漂亮的步骤条"""
    print(f"\n{'='*20} {title} {'='*20}")
    print(content)

def main():
    print(f"[{time.strftime('%H:%M:%S')}] 🚀 启动 Agent 自动化研发任务...")
    print(f"目标需求: {TEST_REQUIREMENT}\n")

    payload = {
        "requirement": TEST_REQUIREMENT
    }

    try:
        start_time = time.time()
        
        # 1. 发送请求
        print(f"[{time.strftime('%H:%M:%S')}] 📡 指令已下达，Agent 正在大脑中构建思维链（CoT）...")
        print("    (提示：由于涉及多轮工具调用和实验模拟，此过程可能需要 30-60 秒，请耐心等待...)")
        
        # 设置较长的超时时间，因为 Agent 需要跑完整个闭环
        response = requests.post(API_URL, json=payload, timeout=6000)
        
        duration = time.time() - start_time
        print(f"[{time.strftime('%H:%M:%S')}] ✅ 任务完成！总耗时: {duration:.2f} 秒")

        if response.status_code == 200:
            result = response.json()
            
            # 2. 可视化 Agent 的思考过程 (ReAct Trace)
            print_step("Agent 思考与执行轨迹", "以下是 Agent 的自主决策日志：")
            
            logs = result.get("log", [])
            for i, log_entry in enumerate(logs):
                # 简单清洗一下日志，使其更易读
                clean_log = log_entry.strip()
                prefix = f"[Step {i+1}]"
                print(f"{prefix:<10} {clean_log}")
                # 如果是工具调用的结果，加个分隔线
                if "Observation:" in clean_log:
                    print("-" * 50)

            # 3. 展示最终成果
            print_step("研发成果交付", "")
            status = result.get("status")
            
            if status == "success":
                final_recipe = result.get("final_recipe")
                print(f"🟢 研发成功！达到目标性能。")
                print(f"🧪 最终优化的电解液配方数组: \n{final_recipe}")
                print(f"📝 总结消息: {result.get('message')}")
            elif status == "timeout":
                print("🟡 研发部分完成，但达到最大迭代次数。")
            else:
                print(f"🔴 任务异常结束: {result.get('result', '未知错误')}")
                
        else:
            print(f"❌ 服务器错误: {response.status_code}")
            try:
                # 将 timeout 设置为 300 秒（5分钟），因为闭环实验涉及多轮推理
                response = requests.post(API_URL, json=payload, timeout=300) 
                print(response.json())
            except requests.exceptions.Timeout:
                print("❌ 测试端超时：Agent 仍在后台运行，但 HTTP 连接已中断。")

    except requests.exceptions.ConnectionError:
        print("\n❌ 连接失败！请检查：")
        print("1. uvicorn 服务是否已启动？")
        print("2. 端口 8000 是否被占用？")
    except requests.exceptions.ReadTimeout:
        print("\n⏳ 请求超时！Agent 思考时间过长，请检查后端是否陷入死循环或硬件响应过慢。")
    except Exception as e:
        print(f"\n❌ 未知错误: {e}")

if __name__ == "__main__":
    main()