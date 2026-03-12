#!/usr/bin/env python3
"""
测试 Master Agent 和 API 工具功能 (OpenClaw 风格)

使用方法:
1. 确保后端 Flask 服务运行在 http://localhost:5009
2. 启动 Agent 服务: python agent_rag_v8.py
3. 运行测试: python test_api_tools.py
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"  # Agent 服务地址


def test_list_api_tools():
    """测试列出所有 API 工具"""
    print("=" * 60)
    print("测试 1: 列出所有 API 工具")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/master/tools")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 成功获取 {data.get('tools_count', 0)} 个 API 工具")
            print("\n可用工具:")
            for name, spec in data.get("tools", {}).items():
                print(f"  - {name}: {spec.get('description', '')}")
            return True
        else:
            print(f"✗ 失败: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False


def test_execute_api_tool():
    """测试执行 API 工具"""
    print("\n" + "=" * 60)
    print("测试 2: 执行 API 工具 (api_parse_request)")
    print("=" * 60)
    
    payload = {
        "tool_name": "api_parse_request",
        "parameters": {
            "natural_language_input": "设计4.5V高电压电解液，用于锂离子电池，循环寿命超过500次"
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/master/tool/execute",
            json=payload
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 工具执行成功")
            print(f"\n结果:")
            print(json.dumps(data.get("result", {}), indent=2, ensure_ascii=False))
            return True
        else:
            print(f"✗ 失败: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False


def test_run_master_agent():
    """测试运行 Master Agent 闭环流程"""
    print("\n" + "=" * 60)
    print("测试 3: 运行 Master Agent 闭环流程")
    print("=" * 60)
    
    payload = {
        "query": "设计4.5V高电压电解液，循环寿命超过500次",
        "auto_execute": False  # 分步执行，便于观察
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/master/run",
            json=payload
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Master Agent 启动成功")
            print(f"  Workflow ID: {data.get('workflow_id')}")
            print(f"  Status: {data.get('status')}")
            print(f"  Message: {data.get('message')}")
            if data.get('current_step'):
                print(f"  Current Step: {data.get('current_step')}")
            return True
        else:
            print(f"✗ 失败: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False


def test_health_check():
    """测试健康检查"""
    print("=" * 60)
    print("测试 0: 健康检查")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 服务正常")
            print(f"  状态: {data.get('status')}")
            print(f"  Agent列表: {data.get('agents', [])}")
            print(f"  LLM加载: {data.get('llm_loaded')}")
            print(f"  RAG就绪: {data.get('rag_ready')}")
            return True
        else:
            print(f"✗ 失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 错误: {e}")
        print("\n提示: 请确保 Agent 服务已启动 (python agent_rag_v8.py)")
        return False


def test_list_agents():
    """测试列出所有 Agent"""
    print("\n" + "=" * 60)
    print("测试 4: 列出所有 Agent")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/agents")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 成功获取 Agent 列表")
            print("\nAgent 列表:")
            for agent in data.get("agents", []):
                print(f"  - {agent.get('id')} ({agent.get('type')}): {agent.get('status')}")
            return True
        else:
            print(f"✗ 失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False


def print_usage():
    """打印使用说明"""
    print("""
ChemMind Master Agent API 测试脚本
====================================

使用方法:
  python test_api_tools.py [test_name]

可用测试:
  all         - 运行所有测试 (默认)
  health      - 健康检查
  tools       - 列出 API 工具
  execute     - 执行 API 工具
  master      - 运行 Master Agent
  agents      - 列出所有 Agent

示例:
  python test_api_tools.py           # 运行所有测试
  python test_api_tools.py health    # 仅健康检查
  python test_api_tools.py tools     # 仅列出工具

环境要求:
  1. 后端 Flask 服务运行在 http://localhost:5009
  2. Agent 服务运行在 http://localhost:8000 (python agent_rag_v8.py)
""")


def main():
    """主函数"""
    # 获取命令行参数
    test_name = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if test_name in ["-h", "--help", "help"]:
        print_usage()
        return
    
    print("\n" + "=" * 60)
    print("ChemMind Master Agent API 测试")
    print("=" * 60)
    print(f"Agent服务地址: {BASE_URL}")
    print("=" * 60 + "\n")
    
    results = []
    
    # 运行测试
    if test_name in ["all", "health"]:
        results.append(("health", test_health_check()))
    
    if test_name in ["all", "tools"]:
        results.append(("tools", test_list_api_tools()))
    
    if test_name in ["all", "execute"]:
        results.append(("execute", test_execute_api_tool()))
    
    if test_name in ["all", "master"]:
        results.append(("master", test_run_master_agent()))
    
    if test_name in ["all", "agents"]:
        results.append(("agents", test_list_agents()))
    
    # 打印结果汇总
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name:20s}: {status}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print("=" * 60)
    print(f"总计: {passed_count}/{total_count} 通过")
    print("=" * 60)


if __name__ == "__main__":
    main()
