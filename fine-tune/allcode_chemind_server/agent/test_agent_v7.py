"""
True Multi-Agent System v7 - 综合测试套件
测试场景设计：
正常对话（QA）
任务委派（包含任务关键词）
完整工作流执行（从创建到完成）
并发工作流（测试Orchestrator的并发处理能力）
澄清流程（测试用户交互）
深度研究（直接RAG）
错误场景（无效ID、超时等）
测试所有API端点和多智能体协作流程

使用方法:
1. 确保服务已启动: python your_server.py
2. 运行完整测试: python /Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/test_agent_v7.py --mode full
3. 仅测试对话: python test_multiagent_v7.py --mode chat
4. 仅测试工作流: python test_multiagent_v7.py --mode workflow
5. 压力测试: python test_multiagent_v7.py --mode stress --concurrent 10
6. 测试远程服务: python test_multiagent_v7.py --url http://remote:8000 --mode full
"""

import asyncio
import json
import time
import requests
import argparse
import sys
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum, auto
import threading
from datetime import datetime


# ==============================================================================
# 配置与常量
# ==============================================================================

BASE_URL = "http://localhost:8000"
ENDPOINTS = {
    "health": "/health",
    "chat": "/chat",
    "chat_stream": "/chat/stream",
    "task": "/task",
    "workflow": "/workflow",
    "research": "/research/deep"
}

# 测试消息样本
TEST_MESSAGES = {
    "greeting": "你好，请介绍一下你自己",
    "qa_simple": "什么是电解液？",
    "qa_technical": "锂离子电池电解液中LiPF6的作用是什么？",
    "task_simple": "帮我设计一款高电压电解液，要求库伦效率99.5%",
    "task_complex": "开发一款适用于硅碳负极的局部高浓度电解液，需要满足：首效>85%、循环500圈保持率>80%、高温存储产气<2mL",
    "task_optimization": "优化现有碳酸酯电解液的低温性能，目标-20℃电导率>5mS/cm",
    "edge_empty": "",
    "edge_short": "好",
    "edge_long": "电解液" * 500,
    "edge_special": "<script>alert('xss')</script>设计电解液",
    "english": "Design a high-voltage electrolyte for NMC811 with CE >99.5%",
    "mixed": "设计high voltage电解液，要求CE>99.5%",
    "clarification_test": "设计一款电解液",  # 可能需要澄清
}


class TestMode(Enum):
    CHAT = "chat"
    WORKFLOW = "workflow"
    FULL = "full"
    STRESS = "stress"
    SPECIFIC = "specific"
    QUICK = "quick"


@dataclass
class TestCase:
    name: str
    endpoint: str
    method: str
    payload: Optional[Dict] = None
    expected_status: int = 200
    check_fields: List[str] = field(default_factory=list)
    description: str = ""
    wait_for_completion: bool = False
    timeout: int = 300
    is_stream: bool = False
    headers: Dict = field(default_factory=dict)


# ==============================================================================
# 工作流监控器
# ==============================================================================

class WorkflowMonitor:
    """监控工作流执行状态"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
    
    def poll_status(self, workflow_id: str, max_wait: int = 600, interval: int = 2) -> Dict:
        """轮询工作流状态直到完成或超时"""
        start_time = time.time()
        history = []
        last_state = None
        
        print(f"  开始监控工作流 {workflow_id[:8]}... (最长{max_wait}s)")
        
        while time.time() - start_time < max_wait:
            try:
                resp = self.session.get(
                    f"{self.base_url}{ENDPOINTS['workflow']}/{workflow_id}",
                    timeout=10
                )
                
                if resp.status_code == 404:
                    return {"status": "not_found", "history": history, "duration": time.time() - start_time}
                
                if resp.status_code != 200:
                    time.sleep(interval)
                    continue
                
                data = resp.json()
                current_state = data.get("status", "unknown")
                current_agent = data.get("current_agent", "none")
                
                # 记录状态变化
                if current_state != last_state:
                    elapsed = time.time() - start_time
                    history.append({
                        "time": elapsed,
                        "state": current_state,
                        "agent": current_agent
                    })
                    print(f"  [{elapsed:.1f}s] 状态: {current_state} | 当前Agent: {current_agent}")
                    last_state = current_state
                
                # 检查是否完成
                if current_state in ["completed", "failed", "error", "awaiting_clarification"]:
                    return {
                        "status": current_state,
                        "final_data": data,
                        "duration": time.time() - start_time,
                        "history": history
                    }
                
                time.sleep(interval)
                
            except Exception as e:
                print(f"  ⚠️ 轮询异常: {e}")
                time.sleep(interval)
        
        return {
            "status": "polling_timeout",
            "duration": time.time() - start_time,
            "history": history
        }


# ==============================================================================
# 主测试类
# ==============================================================================

class MultiAgentTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results: List[Dict] = []
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        self.monitor = WorkflowMonitor(base_url)
        
    def print_header(self, text: str):
        print(f"\n{'='*70}")
        print(f" {text}")
        print(f"{'='*70}")
    
    def print_result(self, success: bool, message: str):
        icon = "✅" if success else "❌"
        print(f"{icon} {message}")
    
    def check_health(self) -> bool:
        """健康检查"""
        try:
            resp = self.session.get(f"{self.base_url}{ENDPOINTS['health']}", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                print(f"服务状态: {data.get('status', 'unknown')}")
                print(f"已加载Agent: {', '.join(data.get('agents', []))}")
                return data.get('status') == 'healthy'
            return False
        except Exception as e:
            print(f"❌ 无法连接服务: {e}")
            return False
    
    def run_test(self, test_case: TestCase) -> Dict:
        """执行单个测试用例"""
        start_time = time.time()
        result = {
            "name": test_case.name,
            "endpoint": test_case.endpoint,
            "description": test_case.description,
            "success": False,
            "checks": {},
            "stages": {}
        }
        
        try:
            url = f"{self.base_url}{test_case.endpoint}"
            
            # 执行请求
            if test_case.method == "GET":
                resp = self.session.get(url, timeout=test_case.timeout)
            elif test_case.method == "POST":
                if test_case.is_stream:
                    # 流式响应处理
                    resp = self.session.post(
                        url, 
                        json=test_case.payload, 
                        stream=True,
                        timeout=test_case.timeout,
                        headers={**self.session.headers, **test_case.headers}
                    )
                else:
                    resp = self.session.post(
                        url, 
                        json=test_case.payload, 
                        timeout=test_case.timeout
                    )
            else:
                result["error"] = f"不支持的HTTP方法: {test_case.method}"
                return result
            
            elapsed = time.time() - start_time
            result["stages"]["request"] = {
                "status_code": resp.status_code,
                "elapsed": elapsed
            }
            
            # 状态码检查
            status_ok = resp.status_code == test_case.expected_status
            result["checks"]["status_code"] = status_ok
            
            if not status_ok:
                result["error"] = f"状态码不匹配: 期望 {test_case.expected_status}, 实际 {resp.status_code}"
                result["response_preview"] = resp.text[:200]
                return result
            
            # 处理流式响应
            if test_case.is_stream:
                tokens = []
                for line in resp.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])
                                if 'token' in data:
                                    tokens.append(data['token'])
                                if data.get('done'):
                                    break
                            except:
                                pass
                result["stream_content"] = ''.join(tokens)
                result["token_count"] = len(tokens)
                result["checks"]["stream_complete"] = len(tokens) > 0
                result["success"] = True
                return result
            
            # 解析JSON响应
            try:
                data = resp.json()
                result["response"] = data
            except json.JSONDecodeError:
                result["response_text"] = resp.text
                if test_case.expected_status == 200:
                    result["checks"]["json_parse"] = False
                    return result
                else:
                    result["checks"]["json_parse"] = True
            
            # 检查必要字段
            for field in test_case.check_fields:
                has_field = field in data
                result["checks"][f"has_{field}"] = has_field
            
            # 工作流特殊处理
            if test_case.wait_for_completion and "workflow_id" in data:
                workflow_id = data["workflow_id"]
                result["workflow_id"] = workflow_id
                
                poll_result = self.monitor.poll_status(
                    workflow_id,
                    max_wait=test_case.timeout - elapsed - 5,
                    interval=2
                )
                result["stages"]["workflow_execution"] = poll_result
                result["checks"]["workflow_completed"] = poll_result["status"] == "completed"
                
                # 如果等待澄清，测试澄清流程
                if poll_result["status"] == "awaiting_clarification":
                    print(f"  📝 检测到需要澄清，自动提交澄清信息...")
                    clarify_resp = self.session.post(
                        f"{self.base_url}{ENDPOINTS['workflow']}/{workflow_id}/clarify",
                        json={"clarification": "需要高温稳定性，工作温度60℃"},
                        timeout=30
                    )
                    result["checks"]["clarify_accepted"] = clarify_resp.status_code == 200
                    
                    # 继续轮询
                    poll_result2 = self.monitor.poll_status(workflow_id, max_wait=300, interval=2)
                    result["stages"]["workflow_execution_after_clarify"] = poll_result2
            
            result["elapsed_total"] = time.time() - start_time
            result["success"] = all(result["checks"].values())
            
        except requests.exceptions.Timeout:
            result["error"] = f"请求超时 (> {test_case.timeout}s)"
            result["elapsed_total"] = time.time() - start_time
        except Exception as e:
            result["error"] = str(e)
            result["elapsed_total"] = time.time() - start_time
        
        return result
    
    def build_chat_tests(self) -> List[TestCase]:
        """构建对话测试用例"""
        return [
            TestCase(
                name="CHAT-基础问候",
                endpoint=ENDPOINTS["chat"],
                method="POST",
                payload={"message": TEST_MESSAGES["greeting"], "session_id": None},
                check_fields=["session_id", "status"],
                description="基础问候语测试"
            ),
            TestCase(
                name="CHAT-技术问答",
                endpoint=ENDPOINTS["chat"],
                method="POST",
                payload={"message": TEST_MESSAGES["qa_technical"], "session_id": f"test_{int(time.time())}"},
                check_fields=["session_id"],
                description="技术知识问答"
            ),
            TestCase(
                name="CHAT-任务委派检测",
                endpoint=ENDPOINTS["chat"],
                method="POST",
                payload={"message": TEST_MESSAGES["task_simple"], "session_id": f"task_{int(time.time())}"},
                check_fields=["session_id"],
                description="包含任务关键词，应触发委派",
                wait_for_completion=False
            ),
            TestCase(
                name="CHAT-空消息",
                endpoint=ENDPOINTS["chat"],
                method="POST",
                payload={"message": TEST_MESSAGES["edge_empty"]},
                expected_status=422,
                description="空消息边界测试"
            ),
            TestCase(
                name="CHAT-超长消息",
                endpoint=ENDPOINTS["chat"],
                method="POST",
                payload={"message": TEST_MESSAGES["edge_long"]},
                check_fields=["session_id"],
                description="超长消息处理"
            ),
            TestCase(
                name="CHAT-特殊字符",
                endpoint=ENDPOINTS["chat"],
                method="POST",
                payload={"message": TEST_MESSAGES["edge_special"]},
                check_fields=["session_id"],
                description="XSS防护测试"
            ),
            TestCase(
                name="CHAT-英文输入",
                endpoint=ENDPOINTS["chat"],
                method="POST",
                payload={"message": TEST_MESSAGES["english"]},
                check_fields=["session_id"],
                description="英文输入处理"
            ),
        ]
    
    def build_workflow_tests(self) -> List[TestCase]:
        """构建工作流测试用例"""
        return [
            TestCase(
                name="WF-标准任务",
                endpoint=ENDPOINTS["task"],
                method="POST",
                payload={
                    "goal": TEST_MESSAGES["task_simple"],
                    "context": {"target_ce": 99.5},
                    "mode": "auto"
                },
                check_fields=["workflow_id", "status"],
                description="标准工作流创建与执行",
                wait_for_completion=True,
                timeout=600
            ),
            TestCase(
                name="WF-复杂研发任务",
                endpoint=ENDPOINTS["task"],
                method="POST",
                payload={
                    "goal": TEST_MESSAGES["task_complex"],
                    "context": {"priority": "high"},
                    "mode": "auto"
                },
                check_fields=["workflow_id"],
                description="复杂多目标优化任务",
                wait_for_completion=False,  # 太长，不等待完成
                timeout=60
            ),
            TestCase(
                name="WF-快速任务",
                endpoint=ENDPOINTS["task"],
                method="POST",
                payload={
                    "goal": "简单电解液分析",
                    "mode": "auto"
                },
                check_fields=["workflow_id"],
                description="无上下文快速任务",
                wait_for_completion=True,
                timeout=300
            ),
            TestCase(
                name="WF-需要澄清的任务",
                endpoint=ENDPOINTS["task"],
                method="POST",
                payload={
                    "goal": TEST_MESSAGES["clarification_test"],
                    "mode": "auto"
                },
                check_fields=["workflow_id"],
                description="测试澄清流程",
                wait_for_completion=True,
                timeout=400
            ),
        ]
    
    def build_research_tests(self) -> List[TestCase]:
        """构建深度研究测试用例"""
        return [
            TestCase(
                name="RAG-深度搜索",
                endpoint=ENDPOINTS["research"],
                method="POST",
                payload={
                    "query": "高电压电解液添加剂",
                    "depth": 2,
                    "breadth": 3
                },
                check_fields=["status", "results"],
                description="深度文献检索"
            ),
            TestCase(
                name="RAG-简单搜索",
                endpoint=ENDPOINTS["research"],
                method="POST",
                payload={
                    "query": "LiPF6",
                    "depth": 1,
                    "breadth": 2
                },
                check_fields=["results"],
                description="浅层快速搜索"
            ),
        ]
    
    def build_stream_tests(self) -> List[TestCase]:
        """构建流式响应测试"""
        return [
            TestCase(
                name="STREAM-基础流式对话",
                endpoint=ENDPOINTS["chat_stream"],
                method="POST",
                payload={"message": "请详细解释电解液组成", "stream": True},
                is_stream=True,
                headers={"Accept": "text/event-stream"},
                description="SSE流式响应测试",
                timeout=60
            ),
        ]
    
    def run_chat_tests(self):
        """运行对话测试"""
        self.print_header("对话系统测试 (/chat)")
        tests = self.build_chat_tests()
        
        for i, tc in enumerate(tests, 1):
            print(f"\n[{i}/{len(tests)}] {tc.name}")
            print(f"  描述: {tc.description}")
            
            result = self.run_test(tc)
            self.results.append(result)
            
            success = result.get("success", False)
            self.print_result(success, 
                f"HTTP {result['stages']['request']['status_code']} | "
                f"耗时: {result.get('elapsed_total', 0):.2f}s"
            )
            
            if "error" in result:
                print(f"  错误: {result['error']}")
            elif "response" in result:
                resp = result["response"]
                if "content" in resp:
                    preview = resp["content"][:100] + "..." if len(resp["content"]) > 100 else resp["content"]
                    print(f"  回复预览: {preview}")
    
    def run_workflow_tests(self):
        """运行工作流测试"""
        self.print_header("工作流系统测试 (/task, /workflow)")
        tests = self.build_workflow_tests()
        
        for i, tc in enumerate(tests, 1):
            print(f"\n[{i}/{len(tests)}] {tc.name}")
            print(f"  描述: {tc.description}")
            if tc.wait_for_completion:
                print(f"  模式: 等待完成 (最长{tc.timeout}s)")
            
            result = self.run_test(tc)
            self.results.append(result)
            
            success = result.get("success", False)
            status_code = result['stages']['request']['status_code']
            
            if tc.wait_for_completion and "workflow_execution" in result.get("stages", {}):
                wf_result = result["stages"]["workflow_execution"]
                self.print_result(success,
                    f"HTTP {status_code} | 工作流状态: {wf_result['status']} | "
                    f"总耗时: {result.get('elapsed_total', 0):.1f}s"
                )
                if wf_result.get("history"):
                    print(f"  状态变化: {' -> '.join([h['state'] for h in wf_result['history']])}")
            else:
                self.print_result(success,
                    f"HTTP {status_code} | 耗时: {result.get('elapsed_total', 0):.2f}s"
                )
            
            if "error" in result:
                print(f"  错误: {result['error']}")
    
    def run_research_tests(self):
        """运行深度研究测试"""
        self.print_header("深度研究测试 (/research/deep)")
        tests = self.build_research_tests()
        
        for i, tc in enumerate(tests, 1):
            print(f"\n[{i}/{len(tests)}] {tc.name}")
            result = self.run_test(tc)
            self.results.append(result)
            
            success = result.get("success", False)
            self.print_result(success,
                f"HTTP {result['stages']['request']['status_code']} | "
                f"耗时: {result.get('elapsed_total', 0):.2f}s"
            )
            
            if success and "response" in result:
                resp = result["response"]
                if "results_count" in resp:
                    print(f"  检索结果数: {resp['results_count']}")
    
    def run_stream_tests(self):
        """运行流式测试"""
        self.print_header("流式响应测试 (/chat/stream)")
        tests = self.build_stream_tests()
        
        for i, tc in enumerate(tests, 1):
            print(f"\n[{i}/{len(tests)}] {tc.name}")
            result = self.run_test(tc)
            self.results.append(result)
            
            success = result.get("success", False)
            self.print_result(success,
                f"Token数: {result.get('token_count', 0)} | "
                f"耗时: {result.get('elapsed_total', 0):.2f}s"
            )
            if success:
                preview = result.get('stream_content', '')[:100]
                print(f"  内容预览: {preview}...")
    
    def run_concurrent_test(self, count: int = 3):
        """并发工作流测试"""
        self.print_header(f"并发测试 ({count}个工作流)")
        
        def launch_workflow(i: int) -> Dict:
            start = time.time()
            try:
                resp = self.session.post(
                    f"{self.base_url}{ENDPOINTS['task']}",
                    json={
                        "goal": f"并发测试任务 {i}: 优化电解液配方",
                        "context": {"test_id": i},
                        "mode": "auto"
                    },
                    timeout=30
                )
                data = resp.json() if resp.status_code == 200 else {}
                return {
                    "id": i,
                    "status": resp.status_code,
                    "workflow_id": data.get("workflow_id"),
                    "time": time.time() - start,
                    "success": resp.status_code == 200
                }
            except Exception as e:
                return {
                    "id": i,
                    "status": 0,
                    "time": time.time() - start,
                    "success": False,
                    "error": str(e)
                }
        
        # 并发启动
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=count) as executor:
            futures = [executor.submit(launch_workflow, i) for i in range(count)]
            launch_results = [f.result() for f in as_completed(futures)]
        
        launch_time = time.time() - start_time
        success_count = sum(1 for r in launch_results if r["success"])
        
        print(f"启动阶段: {success_count}/{count} 成功 | 耗时: {launch_time:.2f}s")
        
        # 监控完成
        workflow_ids = [r["workflow_id"] for r in launch_results if r.get("workflow_id")]
        completed = []
        
        with ThreadPoolExecutor(max_workers=count) as executor:
            future_to_id = {
                executor.submit(self.monitor.poll_status, wid, 300, 2): wid 
                for wid in workflow_ids
            }
            
            for future in as_completed(future_to_id):
                wid = future_to_id[future]
                try:
                    result = future.result()
                    completed.append(result)
                    print(f"  {wid[:8]}...: {result['status']} ({result.get('duration', 0):.1f}s)")
                except Exception as e:
                    print(f"  {wid[:8]}...: 异常 {e}")
        
        # 统计
        success_complete = sum(1 for c in completed if c["status"] == "completed")
        print(f"\n完成统计: {success_complete}/{len(workflow_ids)} 成功完成")
        if completed:
            avg_duration = sum(c.get("duration", 0) for c in completed) / len(completed)
            print(f"平均执行时间: {avg_duration:.1f}s")
    
    def run_stress_test(self, concurrent: int = 5, iterations: int = 2):
        """压力测试"""
        self.print_header(f"压力测试: {concurrent}并发 × {iterations}轮")
        
        all_results = []
        
        for round_num in range(iterations):
            print(f"\n第 {round_num + 1}/{iterations} 轮...")
            round_start = time.time()
            
            def send_request(i: int) -> Dict:
                try:
                    # 混合请求类型
                    if i % 3 == 0:
                        # Chat请求
                        resp = self.session.post(
                            f"{self.base_url}{ENDPOINTS['chat']}",
                            json={"message": f"压力测试消息 {i}"},
                            timeout=30
                        )
                    elif i % 3 == 1:
                        # 工作流创建
                        resp = self.session.post(
                            f"{self.base_url}{ENDPOINTS['task']}",
                            json={"goal": f"压力测试任务 {i}"},
                            timeout=30
                        )
                    else:
                        # 健康检查
                        resp = self.session.get(
                            f"{self.base_url}{ENDPOINTS['health']}",
                            timeout=10
                        )
                    
                    return {
                        "type": "chat" if i % 3 == 0 else "task" if i % 3 == 1 else "health",
                        "status": resp.status_code,
                        "success": resp.status_code == 200,
                        "time": time.time() - round_start
                    }
                except Exception as e:
                    return {
                        "type": "unknown",
                        "status": 0,
                        "success": False,
                        "error": str(e),
                        "time": time.time() - round_start
                    }
            
            with ThreadPoolExecutor(max_workers=concurrent) as executor:
                futures = [executor.submit(send_request, i) for i in range(concurrent)]
                results = [f.result() for f in as_completed(futures)]
            
            round_time = time.time() - round_start
            success_count = sum(1 for r in results if r["success"])
            
            print(f"  耗时: {round_time:.2f}s | 成功: {success_count}/{concurrent}")
            all_results.extend(results)
        
        # 总报告
        total = len(all_results)
        success = sum(1 for r in all_results if r["success"])
        print(f"\n总统计:")
        print(f"  请求数: {total}")
        print(f"  成功率: {success}/{total} ({success/total*100:.1f}%)")
        print(f"  平均响应: {sum(r['time'] for r in all_results)/total:.2f}s")
    
    def print_final_report(self):
        """打印最终报告"""
        self.print_header("测试总结报告")
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.get("success", False))
        failed = total - passed
        
        print(f"总测试数: {total}")
        print(f"通过: {passed} ({passed/total*100:.1f}%)" if total > 0 else "N/A")
        print(f"失败: {failed} ({failed/total*100:.1f}%)" if total > 0 else "N/A")
        
        # 分类统计
        categories = {}
        for r in self.results:
            cat = r["name"].split("-")[0] if "-" in r["name"] else "OTHER"
            if cat not in categories:
                categories[cat] = {"total": 0, "passed": 0}
            categories[cat]["total"] += 1
            if r.get("success"):
                categories[cat]["passed"] += 1
        
        print(f"\n分类统计:")
        for cat, stats in categories.items():
            rate = stats["passed"]/stats["total"]*100 if stats["total"] > 0 else 0
            print(f"  {cat}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")
        
        # 失败详情
        if failed > 0:
            print(f"\n失败详情:")
            for r in self.results:
                if not r.get("success", False):
                    error = r.get("error", "检查项未通过")
                    print(f"  - {r['name']}: {error}")
        
        # 保存详细报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"multiagent_test_report_{timestamp}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n详细报告已保存: {report_file}")


# ==============================================================================
# 主入口
# ==============================================================================

def main():
    print("""
    ████████╗██████╗ ███████╗██╗   ██╗███████╗    ███╗   ███╗███████╗
    ╚══██╔══╝██╔══██╗██╔════╝██║   ██║██╔════╝    ████╗ ████║██╔════╝
       ██║   ██████╔╝█████╗  ██║   ██║███████╗    ██╔████╔██║█████╗  
       ██║   ██╔══██╗██╔══╝  ██║   ██║╚════██║    ██║╚██╔╝██║██╔══╝  
       ██║   ██║  ██║███████╗╚██████╔╝███████║    ██║ ╚═╝ ██║███████╗
       ╚═╝   ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚══════╝    ╚═╝     ╚═╝╚══════╝
                                                                     
    True Multi-Agent System v7 - 综合测试套件
    """)
    
    parser = argparse.ArgumentParser(description="多智能体系统API测试工具")
    parser.add_argument("--mode", 
                       choices=["full", "chat", "workflow", "research", "stream", "stress", "specific", "quick"],
                       default="full",
                       help="测试模式")
    parser.add_argument("--url", default="http://localhost:8000", help="服务基础URL")
    parser.add_argument("--concurrent", type=int, default=5, help="并发数（用于stress/specific模式）")
    parser.add_argument("--iterations", type=int, default=2, help="迭代次数（用于stress模式）")
    
    args = parser.parse_args()
    
    tester = MultiAgentTester(args.url)
    
    # 健康检查
    if not tester.check_health():
        print("服务未就绪，退出测试")
        sys.exit(1)
    
    # 执行测试
    if args.mode == "full":
        tester.run_chat_tests()
        tester.run_workflow_tests()
        tester.run_research_tests()
        tester.run_stream_tests()
        tester.run_concurrent_test(3)
        
    elif args.mode == "chat":
        tester.run_chat_tests()
        
    elif args.mode == "workflow":
        tester.run_workflow_tests()
        
    elif args.mode == "research":
        tester.run_research_tests()
        
    elif args.mode == "stream":
        tester.run_stream_tests()
        
    elif args.mode == "stress":
        tester.run_stress_test(args.concurrent, args.iterations)
        
    elif args.mode == "specific":
        # 专项功能测试
        tester.run_concurrent_test(args.concurrent)
        
    elif args.mode == "quick":
        # 快速验证
        print("\n快速验证关键端点...")
        tests = [
            TestCase("Quick-Health", ENDPOINTS["health"], "GET"),
            TestCase("Quick-Chat", ENDPOINTS["chat"], "POST", 
                    {"message": "你好"}),
            TestCase("Quick-Task", ENDPOINTS["task"], "POST",
                    {"goal": "快速测试"}, wait_for_completion=False),
        ]
        for tc in tests:
            result = tester.run_test(tc)
            tester.results.append(result)
            tester.print_result(result["success"], 
                f"{tc.name}: HTTP {result['stages']['request']['status_code']}")
    
    # 打印报告
    if args.mode != "stress":
        tester.print_final_report()


if __name__ == "__main__":
    main()