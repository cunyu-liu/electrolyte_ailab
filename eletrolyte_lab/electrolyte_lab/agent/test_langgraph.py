"""
悟行 - LangGraph 版本测试脚本

测试内容：
1. 健康检查
2. 各类任务路由测试
3. 工作流状态查询
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"


def test_health():
    """测试健康检查接口"""
    print("="*60)
    print("测试1: 健康检查")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_chat(message: str, description: str):
    """测试对话接口"""
    print("\n" + "="*60)
    print(f"测试: {description}")
    print("="*60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json={"message": message},
            timeout=60
        )
        
        result = response.json()
        print(f"状态码: {response.status_code}")
        print(f"任务ID: {result.get('thread_id')}")
        print(f"执行历史:")
        for hist in result.get('execution_history', []):
            print(f"  - {hist['step']}: {hist.get('timestamp', 'N/A')}")
        print(f"\n响应内容预览:")
        print(result.get('response', '无响应')[:500] + "...")
        
        return result.get('thread_id')
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return None


def test_workflow_status(thread_id: str):
    """测试工作流状态查询"""
    print("\n" + "="*60)
    print(f"测试: 查询工作流状态 [{thread_id[:8]}...]")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/workflow/status/{thread_id}")
        result = response.json()
        print(f"状态码: {response.status_code}")
        print(f"当前步骤: {result.get('current_step')}")
        print(f"任务类型: {result.get('task_type')}")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("悟行 - LangGraph 多智能体系统测试")
    print("="*60)
    
    # 测试1: 健康检查
    if not test_health():
        print("\n⚠️ 服务未启动，请先运行: python agent_langgraph.py")
        return
    
    # 测试2: 文献研究类任务
    thread_id_1 = test_chat(
        "查找关于高电压电解液的最新研究文献",
        "文献研究类任务 -> 路由到 LiteratureAgent"
    )
    
    time.sleep(1)
    
    # 测试3: 分子预测类任务
    thread_id_2 = test_chat(
        "预测分子 C1COC(=O)O1 的电化学性质",
        "分子预测类任务 -> 路由到 MolecularAgent"
    )
    
    time.sleep(1)
    
    # 测试4: 实验设计类任务
    thread_id_3 = test_chat(
        "设计一个测试高电压电解液循环寿命的实验方案",
        "实验设计类任务 -> 路由到 DesignerAgent"
    )
    
    time.sleep(1)
    
    # 测试5: 查询工作流状态
    if thread_id_1:
        test_workflow_status(thread_id_1)
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()
