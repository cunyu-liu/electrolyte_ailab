"""
True Multi-Agent System v7 - 综合测试套件（增强版）
增强功能：
- 完整的输入输出数据持久化
- Deep Research 详细过程记录
- 结构化 JSON 报告生成

# 完整测试并保存结果
python /Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/test_deepresearch.py --mode full --output-dir /Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/test_result

# 仅测试 Deep Research（会保存详细模型IO）
python test_agent_v7.py --mode research --output-dir ./research_data

# 指定测试并保存完整IO
python test_agent_v7.py --mode quick --output-dir ./quick_test


"""

import asyncio
import json
import time
import requests
import argparse
import sys
import os
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum, auto
import threading
from datetime import datetime
from pathlib import Path


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
    save_full_io: bool = False  # 新增：是否保存完整输入输出


# ==============================================================================
# 增强型数据记录器
# ==============================================================================

class DetailedLogger:
    """详细输入输出记录器"""
    
    def __init__(self, output_dir: str = "test_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.research_counter = 0
        
    def save_research_details(self, test_name: str, request_data: Dict, 
                             response_data: Dict, metadata: Dict) -> str:
        """专门保存 Deep Research 的详细数据"""
        self.research_counter += 1
        
        filename = f"research_{self.research_counter:03d}_{test_name}_{self.session_timestamp}.json"
        filepath = self.output_dir / filename
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "test_name": test_name,
            "type": "deep_research",
            "request": {
                "payload": request_data,
                "endpoint": ENDPOINTS["research"],
                "method": "POST"
            },
            "response": response_data,
            "metadata": metadata
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2, default=str)
        
        return str(filepath)
    
    def save_general_test(self, test_name: str, data: Dict) -> str:
        """保存一般测试的详细数据"""
        filename = f"test_{test_name}_{self.session_timestamp}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        return str(filepath)
    
    def get_session_summary_path(self) -> str:
        """获取会话总结报告路径"""
        return str(self.output_dir / f"test_summary_{self.session_timestamp}.json")


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
                        "agent": current_agent,
                        "timestamp": datetime.now().isoformat()
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
# 主测试类（增强版）
# ==============================================================================

class MultiAgentTester:
    def __init__(self, base_url: str, output_dir: str = "test_results"):
        self.base_url = base_url
        self.results: List[Dict] = []
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        self.monitor = WorkflowMonitor(base_url)
        self.logger = DetailedLogger(output_dir)
        self.output_dir = output_dir
        
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
        """执行单个测试用例（增强版，包含完整IO记录）"""
        start_time = time.time()
        result = {
            "name": test_case.name,
            "endpoint": test_case.endpoint,
            "description": test_case.description,
            "success": False,
            "checks": {},
            "stages": {},
            "io_data": {  # 新增：输入输出数据容器
                "request": None,
                "response": None,
                "saved_files": []
            }
        }
        
        try:
            url = f"{self.base_url}{test_case.endpoint}"
            
            # 记录请求数据
            request_record = {
                "url": url,
                "method": test_case.method,
                "headers": dict(self.session.headers),
                "payload": test_case.payload,
                "timestamp": datetime.now().isoformat()
            }
            result["io_data"]["request"] = request_record
            
            # 执行请求
            if test_case.method == "GET":
                resp = self.session.get(url, timeout=test_case.timeout)
            elif test_case.method == "POST":
                if test_case.is_stream:
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
                "elapsed": elapsed,
                "timestamp": datetime.now().isoformat()
            }
            
            # 状态码检查
            status_ok = resp.status_code == test_case.expected_status
            result["checks"]["status_code"] = status_ok
            
            # 记录响应数据（原始）
            raw_response_text = ""
            try:
                raw_response_text = resp.text
            except:
                pass
            
            # 处理流式响应
            if test_case.is_stream:
                tokens = []
                full_response_data = []
                for line in resp.iter_lines():
                    if line:
                        line_decoded = line.decode('utf-8')
                        if line_decoded.startswith('data: '):
                            try:
                                data = json.loads(line_decoded[6:])
                                full_response_data.append(data)
                                if 'token' in data:
                                    tokens.append(data['token'])
                                if data.get('done'):
                                    break
                            except:
                                pass
                
                stream_content = ''.join(tokens)
                result["stream_content"] = stream_content
                result["token_count"] = len(tokens)
                result["checks"]["stream_complete"] = len(tokens) > 0
                
                # 保存流式数据
                result["io_data"]["response"] = {
                    "type": "stream",
                    "tokens": tokens,
                    "full_events": full_response_data if test_case.save_full_io else None,
                    "combined_text": stream_content
                }
                result["success"] = True
                return result
            
            # 解析JSON响应
            parsed_response = None
            try:
                parsed_response = resp.json()
                result["response"] = parsed_response
                result["io_data"]["response"] = {
                    "type": "json",
                    "data": parsed_response,
                    "raw_text": raw_response_text if test_case.save_full_io else None
                }
            except json.JSONDecodeError:
                result["response_text"] = raw_response_text
                result["io_data"]["response"] = {
                    "type": "text",
                    "data": raw_response_text
                }
                if test_case.expected_status == 200:
                    result["checks"]["json_parse"] = False
                    return result
            
            # 检查必要字段
            if parsed_response:
                for field in test_case.check_fields:
                    has_field = field in parsed_response
                    result["checks"][f"has_{field}"] = has_field
            
            # 工作流特殊处理
            if test_case.wait_for_completion and parsed_response and "workflow_id" in parsed_response:
                workflow_id = parsed_response["workflow_id"]
                result["workflow_id"] = workflow_id
                
                poll_result = self.monitor.poll_status(
                    workflow_id,
                    max_wait=test_case.timeout - elapsed - 5,
                    interval=2
                )
                result["stages"]["workflow_execution"] = poll_result
                result["checks"]["workflow_completed"] = poll_result["status"] == "completed"
                
                # 保存工作流详细数据
                if test_case.save_full_io:
                    result["io_data"]["workflow_details"] = poll_result
                
                # 如果等待澄清，测试澄清流程
                if poll_result["status"] == "awaiting_clarification":
                    print(f"  📝 检测到需要澄清，自动提交澄清信息...")
                    clarify_payload = {"clarification": "需要高温稳定性，工作温度60℃"}
                    clarify_resp = self.session.post(
                        f"{self.base_url}{ENDPOINTS['workflow']}/{workflow_id}/clarify",
                        json=clarify_payload,
                        timeout=30
                    )
                    result["clarify_request"] = clarify_payload
                    result["clarify_response"] = clarify_resp.json() if clarify_resp.status_code == 200 else clarify_resp.text
                    result["checks"]["clarify_accepted"] = clarify_resp.status_code == 200
                    
                    # 继续轮询
                    poll_result2 = self.monitor.poll_status(workflow_id, max_wait=300, interval=2)
                    result["stages"]["workflow_execution_after_clarify"] = poll_result2
            
            result["elapsed_total"] = time.time() - start_time
            result["success"] = all(result["checks"].values())
            
            # Deep Research 特殊处理：单独保存详细文件
            if "research" in test_case.endpoint.lower() and test_case.save_full_io:
                metadata = {
                    "elapsed_time": result["elapsed_total"],
                    "checks": result["checks"],
                    "test_name": test_case.name
                }
                saved_path = self.logger.save_research_details(
                    test_case.name,
                    test_case.payload,
                    parsed_response or {"text": raw_response_text},
                    metadata
                )
                result["io_data"]["saved_files"].append(saved_path)
                print(f"  💾 Deep Research 详细数据已保存: {saved_path}")
            
            # 一般测试的完整IO保存（如果标记了save_full_io）
            elif test_case.save_full_io:
                io_record = {
                    "test_name": test_case.name,
                    "request": request_record,
                    "response": result["io_data"]["response"],
                    "metadata": {
                        "elapsed": result["elapsed_total"],
                        "success": result["success"],
                        "checks": result["checks"]
                    }
                }
                saved_path = self.logger.save_general_test(test_case.name, io_record)
                result["io_data"]["saved_files"].append(saved_path)
            
        except requests.exceptions.Timeout:
            result["error"] = f"请求超时 (> {test_case.timeout}s)"
            result["elapsed_total"] = time.time() - start_time
            result["io_data"]["error"] = "timeout"
        except Exception as e:
            result["error"] = str(e)
            result["elapsed_total"] = time.time() - start_time
            result["io_data"]["error"] = str(e)
        
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
                timeout=600,
                save_full_io=True  # 保存完整IO
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
                wait_for_completion=False,
                timeout=60,
                save_full_io=True
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
                timeout=300,
                save_full_io=True
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
                timeout=400,
                save_full_io=True
            ),
        ]
    
    def build_research_tests(self) -> List[TestCase]:
        """构建深度研究测试用例（增强IO记录）"""
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
                description="深度文献检索",
                save_full_io=True,  # 关键：启用完整IO保存
                timeout=120
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
                description="浅层快速搜索",
                save_full_io=True,
                timeout=60
            ),
            TestCase(
                name="RAG-多轮对话式研究",
                endpoint=ENDPOINTS["research"],
                method="POST",
                payload={
                    "query": "硅碳负极电解液溶剂体系优化策略",
                    "depth": 3,
                    "breadth": 2,
                    "session_id": f"research_{int(time.time())}"
                },
                check_fields=["results", "analysis"],
                description="复杂查询深度研究",
                save_full_io=True,
                timeout=180
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
                timeout=60,
                save_full_io=True
            ),
            TestCase(
                name="STREAM-研究流式输出",
                endpoint=ENDPOINTS["chat_stream"],
                method="POST",
                payload={"message": "深度分析电解液添加剂", "stream": True, "enable_research": True},
                is_stream=True,
                description="流式研究响应",
                timeout=120,
                save_full_io=True
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
            
            # 显示保存的文件
            if result.get("io_data", {}).get("saved_files"):
                for f in result["io_data"]["saved_files"]:
                    print(f"  📁 详细数据: {f}")
    
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
            
            if result.get("io_data", {}).get("saved_files"):
                for f in result["io_data"]["saved_files"]:
                    print(f"  📁 工作流详细数据: {f}")
    
    def run_research_tests(self):
        """运行深度研究测试（增强版）"""
        self.print_header("深度研究测试 (/research/deep)")
        print(f"💡 Deep Research 结果将单独保存到: {self.output_dir}/")
        
        tests = self.build_research_tests()
        
        for i, tc in enumerate(tests, 1):
            print(f"\n[{i}/{len(tests)}] {tc.name}")
            print(f"  查询: {tc.payload.get('query', 'N/A')}")
            print(f"  深度: {tc.payload.get('depth', 'N/A')} | 广度: {tc.payload.get('breadth', 'N/A')}")
            
            result = self.run_test(tc)
            self.results.append(result)
            
            success = result.get("success", False)
            self.print_result(success,
                f"HTTP {result['stages']['request']['status_code']} | "
                f"耗时: {result.get('elapsed_total', 0):.2f}s"
            )
            
            # 显示Deep Research的详细信息
            if success and "response" in result:
                resp = result["response"]
                
                # 显示研究统计
                if isinstance(resp, dict):
                    if "results_count" in resp:
                        print(f"  检索结果数: {resp['results_count']}")
                    if "analysis_length" in resp:
                        print(f"  分析文本长度: {resp['analysis_length']}")
                    if "sources" in resp and isinstance(resp["sources"], list):
                        print(f"  引用来源数: {len(resp['sources'])}")
                    
                    # 显示模型输入输出摘要（如果有）
                    if "model_calls" in resp:
                        print(f"  模型调用次数: {len(resp['model_calls'])}")
                        for idx, call in enumerate(resp["model_calls"][:3], 1):  # 只显示前3个
                            print(f"    调用{idx}: {call.get('model', 'unknown')} - {call.get('tokens', 'N/A')} tokens")
            
            # 显示保存的文件路径
            if result.get("io_data", {}).get("saved_files"):
                for f in result["io_data"]["saved_files"]:
                    print(f"  💾 详细研究数据已保存: {f}")
            
            if "error" in result:
                print(f"  错误: {result['error']}")
    
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
            
            if result.get("io_data", {}).get("saved_files"):
                for f in result["io_data"]["saved_files"]:
                    print(f"  📁 流式数据: {f}")
    
    def run_concurrent_test(self, count: int = 3):
        """并发工作流测试"""
        self.print_header(f"并发测试 ({count}个工作流)")
        
        def launch_workflow(i: int) -> Dict:
            start = time.time()
            try:
                payload = {
                    "goal": f"并发测试任务 {i}: 优化电解液配方",
                    "context": {"test_id": i},
                    "mode": "auto"
                }
                resp = self.session.post(
                    f"{self.base_url}{ENDPOINTS['task']}",
                    json=payload,
                    timeout=30
                )
                data = resp.json() if resp.status_code == 200 else {}
                
                # 保存并发测试的详细数据
                result_data = {
                    "id": i,
                    "status": resp.status_code,
                    "workflow_id": data.get("workflow_id"),
                    "time": time.time() - start,
                    "success": resp.status_code == 200,
                    "request": payload,
                    "response": data
                }
                
                # 可选：保存到文件
                concurrent_file = Path(self.output_dir) / f"concurrent_{i}_{self.logger.session_timestamp}.json"
                with open(concurrent_file, "w", encoding="utf-8") as f:
                    json.dump(result_data, f, ensure_ascii=False, indent=2, default=str)
                
                return result_data
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
        
        # 保存并发测试总结
        concurrent_summary = {
            "timestamp": datetime.now().isoformat(),
            "type": "concurrent_test",
            "count": count,
            "launch_results": launch_results,
            "completion_results": completed,
            "statistics": {
                "success_rate": success_complete/len(workflow_ids) if workflow_ids else 0,
                "avg_duration": avg_duration if completed else 0
            }
        }
        summary_file = Path(self.output_dir) / f"concurrent_summary_{self.logger.session_timestamp}.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(concurrent_summary, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n📊 并发测试总结已保存: {summary_file}")
    
    def run_stress_test(self, concurrent: int = 5, iterations: int = 2):
        """压力测试"""
        self.print_header(f"压力测试: {concurrent}并发 × {iterations}轮")
        
        all_results = []
        
        for round_num in range(iterations):
            print(f"\n第 {round_num + 1}/{iterations} 轮...")
            round_start = time.time()
            
            def send_request(i: int) -> Dict:
                req_time = time.time()
                try:
                    # 混合请求类型
                    if i % 3 == 0:
                        endpoint = ENDPOINTS["chat"]
                        payload = {"message": f"压力测试消息 {i}"}
                        resp = self.session.post(
                            f"{self.base_url}{endpoint}",
                            json=payload,
                            timeout=30
                        )
                    elif i % 3 == 1:
                        endpoint = ENDPOINTS["task"]
                        payload = {"goal": f"压力测试任务 {i}"}
                        resp = self.session.post(
                            f"{self.base_url}{endpoint}",
                            json=payload,
                            timeout=30
                        )
                    else:
                        endpoint = ENDPOINTS["health"]
                        resp = self.session.get(
                            f"{self.base_url}{endpoint}",
                            timeout=10
                        )
                        payload = {}
                    
                    result_data = {
                        "type": "chat" if i % 3 == 0 else "task" if i % 3 == 1 else "health",
                        "status": resp.status_code,
                        "success": resp.status_code == 200,
                        "time": time.time() - req_time,
                        "round": round_num,
                        "index": i,
                        "endpoint": endpoint,
                        "request": payload,
                        "response_preview": resp.text[:200] if resp.status_code == 200 else resp.text
                    }
                    return result_data
                except Exception as e:
                    return {
                        "type": "unknown",
                        "status": 0,
                        "success": False,
                        "error": str(e),
                        "time": time.time() - req_time,
                        "round": round_num,
                        "index": i
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
        print(f"  成功率: {success}/{total} ({success/total*100:.1f}%)" if total > 0 else "N/A")
        print(f"  平均响应: {sum(r['time'] for r in all_results)/total:.2f}s")
        
        # 保存压力测试详细结果
        stress_summary = {
            "timestamp": datetime.now().isoformat(),
            "type": "stress_test",
            "config": {"concurrent": concurrent, "iterations": iterations},
            "results": all_results,
            "statistics": {
                "total": total,
                "success": success,
                "success_rate": success/total if total > 0 else 0,
                "avg_response_time": sum(r['time'] for r in all_results)/total if total > 0 else 0,
                "by_type": {}
            }
        }
        
        # 按类型统计
        by_type = {}
        for r in all_results:
            t = r["type"]
            if t not in by_type:
                by_type[t] = {"count": 0, "success": 0, "total_time": 0}
            by_type[t]["count"] += 1
            if r["success"]:
                by_type[t]["success"] += 1
            by_type[t]["total_time"] += r["time"]
        
        for t, stats in by_type.items():
            stress_summary["statistics"]["by_type"][t] = {
                "count": stats["count"],
                "success_rate": stats["success"]/stats["count"] if stats["count"] > 0 else 0,
                "avg_time": stats["total_time"]/stats["count"] if stats["count"] > 0 else 0
            }
        
        stress_file = Path(self.output_dir) / f"stress_test_{self.logger.session_timestamp}.json"
        with open(stress_file, "w", encoding="utf-8") as f:
            json.dump(stress_summary, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n💾 压力测试详细数据已保存: {stress_file}")
    
    def print_final_report(self):
        """打印最终报告并保存完整数据"""
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
        
        # 保存详细总结报告（包含所有IO数据）
        summary_path = self.logger.get_session_summary_path()
        final_report = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "base_url": self.base_url,
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "success_rate": passed/total if total > 0 else 0
            },
            "categories": categories,
            "results": self.results,
            "file_locations": {
                "summary": summary_path,
                "output_directory": str(self.output_dir),
                "research_files": [
                    r["io_data"]["saved_files"] for r in self.results 
                    if r.get("io_data", {}).get("saved_files")
                ]
            }
        }
        
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(final_report, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n📄 完整测试报告已保存: {summary_path}")
        print(f"📁 所有测试数据目录: {self.output_dir}/")
        print(f"   包含文件:")
        print(f"   - 测试总结: test_summary_*.json")
        print(f"   - Deep Research详情: research_*.json")
        print(f"   - 并发测试: concurrent_*.json")
        print(f"   - 压力测试: stress_test_*.json")


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
                                                                     
    True Multi-Agent System v7 - 综合测试套件（增强数据记录版）
    """)
    
    parser = argparse.ArgumentParser(description="多智能体系统API测试工具（增强版）")
    parser.add_argument("--mode", 
                       choices=["full", "chat", "workflow", "research", "stream", "stress", "specific", "quick"],
                       default="full",
                       help="测试模式")
    parser.add_argument("--url", default="http://localhost:8000", help="服务基础URL")
    parser.add_argument("--concurrent", type=int, default=5, help="并发数（用于stress/specific模式）")
    parser.add_argument("--iterations", type=int, default=2, help="迭代次数（用于stress模式）")
    parser.add_argument("--output-dir", default="test_results", help="测试结果保存目录")
    
    args = parser.parse_args()
    
    # 创建测试器实例（指定输出目录）
    tester = MultiAgentTester(args.url, output_dir=args.output_dir)
    
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
        tester.run_concurrent_test(args.concurrent)
        
    elif args.mode == "quick":
        print("\n快速验证关键端点...")
        tests = [
            TestCase("Quick-Health", ENDPOINTS["health"], "GET"),
            TestCase("Quick-Chat", ENDPOINTS["chat"], "POST", 
                    {"message": "你好"}),
            TestCase("Quick-Task", ENDPOINTS["task"], "POST",
                    {"goal": "快速测试"}, wait_for_completion=False, save_full_io=True),
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