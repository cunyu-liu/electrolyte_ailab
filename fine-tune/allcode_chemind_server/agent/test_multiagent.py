"""
Multi-Agent Research 端口测试套件
测试 /research/start 和 /research/status/{id} 端点

# 1. 确保服务已启动
python your_server.py

# 2. 运行完整测试套件
python /Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/test_multiagent.py --mode full

# 3. 仅测试多智能体模式
python test_research_start.py --mode ma

# 4. 仅测试ReAct模式
python test_research_start.py --mode react

# 5. 专项功能测试（生命周期、并发、对比、错误恢复）
python test_research_start.py --mode specific

# 6. 压力测试（10并发 × 3轮）
python test_research_start.py --mode stress --concurrent 10 --iterations 3

# 7. 快速验证
python test_research_start.py --mode quick

# 8. 测试远程服务
python test_research_start.py --url http://your-server:8000 --mode full
"""

import asyncio
import json
import time
import requests
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
import threading
import sys


# ==============================================================================
# 配置
# ==============================================================================

BASE_URL = "http://localhost:8000"
START_ENDPOINT = f"{BASE_URL}/research/start"
STATUS_ENDPOINT = f"{BASE_URL}/research/status"
RUN_ENDPOINT = f"{BASE_URL}/run"

# 测试需求样本
TEST_REQUIREMENTS = {
    "standard": "设计一款适用于4.5V高电压钴酸锂正极的电解液，要求循环库伦效率>99.5%，工作温度范围-20~60℃",
    "simple": "优化碳酸酯电解液的低温导电性",
    "complex": "开发基于局部高浓度电解液(LHCE)体系的硅碳负极专用电解液，需要兼顾首效>85%、循环500圈容量保持率>80%、以及优异的高温存储性能(60℃存储7天产气量<2mL)",
    "edge_empty": "",  # 边界：空需求
    "edge_short": "好",  # 边界：过短
    "edge_long": "电解液" * 500,  # 边界：超长
    "edge_special": "<script>alert('xss')</script>电解液设计",  # 边界：XSS尝试
    "invalid_target": "设计电解液",  # 边界：缺少具体指标
    "english": "Design a high-voltage electrolyte for NMC811 cathode with coulombic efficiency >99.5%",
    "mixed": "高电压high voltage电解液设计，要求CE>99.5%",
}


class TestMode(Enum):
    MULTI_AGENT = "multi_agent"
    REACT = "react"


@dataclass
class TestCase:
    name: str
    payload: Dict
    expected_status: int
    check_fields: List[str]
    description: str
    mode: TestMode = TestMode.MULTI_AGENT
    wait_for_completion: bool = False
    timeout: int = 300


# ==============================================================================
# 测试用例构建
# ==============================================================================

def build_test_cases() -> List[TestCase]:
    return [
        # ===== 多智能体模式测试 =====
        
        # 标准工作流测试
        TestCase(
            name="MA-标准高电压电解液研发",
            payload={
                "requirement": TEST_REQUIREMENTS["standard"],
                "target_ce": 99.5,
                "max_iterations": 5,
                "mode": "multi_agent"
            },
            expected_status=200,
            check_fields=["correlation_id", "status", "mode"],
            description="标准多智能体工作流启动",
            mode=TestMode.MULTI_AGENT,
            wait_for_completion=True,
            timeout=600
        ),
        
        TestCase(
            name="MA-简单需求快速测试",
            payload={
                "requirement": TEST_REQUIREMENTS["simple"],
                "target_ce": 98.0,
                "max_iterations": 3,
                "mode": "multi_agent"
            },
            expected_status=200,
            check_fields=["correlation_id"],
            description="简单需求，较少迭代",
            mode=TestMode.MULTI_AGENT,
            wait_for_completion=True,
            timeout=300
        ),
        
        TestCase(
            name="MA-复杂多目标优化",
            payload={
                "requirement": TEST_REQUIREMENTS["complex"],
                "target_ce": 99.0,
                "max_iterations": 10,
                "mode": "multi_agent"
            },
            expected_status=200,
            check_fields=["correlation_id"],
            description="复杂需求，最大迭代",
            mode=TestMode.MULTI_AGENT,
            wait_for_completion=False,  # 只启动，不等待（太长）
            timeout=60
        ),
        
        # 参数边界测试
        TestCase(
            name="MA-最低目标CE",
            payload={
                "requirement": "基础电解液设计",
                "target_ce": 90.0,  # 较低目标
                "max_iterations": 2,
                "mode": "multi_agent"
            },
            expected_status=200,
            check_fields=["correlation_id"],
            description="测试低目标值是否能快速达成",
            mode=TestMode.MULTI_AGENT,
            wait_for_completion=True,
            timeout=300
        ),
        
        TestCase(
            name="MA-单次迭代",
            payload={
                "requirement": TEST_REQUIREMENTS["simple"],
                "target_ce": 99.9,
                "max_iterations": 1,
                "mode": "multi_agent"
            },
            expected_status=200,
            check_fields=["correlation_id"],
            description="最少迭代次数",
            mode=TestMode.MULTI_AGENT,
            wait_for_completion=True,
            timeout=200
        ),
        
        # 缺失参数测试（使用默认值）
        TestCase(
            name="MA-默认参数",
            payload={
                "requirement": "设计一款高电压电解液",
                # 省略 target_ce, max_iterations
                "mode": "multi_agent"
            },
            expected_status=200,
            check_fields=["correlation_id"],
            description="测试参数默认值",
            mode=TestMode.MULTI_AGENT,
            wait_for_completion=False,
            timeout=60
        ),
        
        # ===== ReAct 模式测试（向后兼容） =====
        
        TestCase(
            name="ReAct-标准流程",
            payload={
                "requirement": TEST_REQUIREMENTS["standard"],
                "max_cycles": 10,
                "target_ce": 99.5,
                "mode": "react"
            },
            expected_status=200,
            check_fields=["status", "result", "execution_trace"],
            description="ReAct单体模式标准流程",
            mode=TestMode.REACT,
            wait_for_completion=False,  # ReAct是同步的，但可能很慢
            timeout=60
        ),
        
        TestCase(
            name="ReAct-快速模式",
            payload={
                "requirement": TEST_REQUIREMENTS["simple"],
                "max_cycles": 5,
                "target_ce": 98.0,
                "mode": "react"
            },
            expected_status=200,
            check_fields=["status"],
            description="ReAct快速流程",
            mode=TestMode.REACT,
            wait_for_completion=False,
            timeout=60
        ),
        
        # ===== 边界和异常测试 =====
        
        TestCase(
            name="边界-空需求",
            payload={
                "requirement": TEST_REQUIREMENTS["edge_empty"],
                "target_ce": 99.5,
                "max_iterations": 5,
                "mode": "multi_agent"
            },
            expected_status=422,  # 验证错误
            check_fields=["detail"],
            description="空需求应该被拒绝",
            mode=TestMode.MULTI_AGENT,
            wait_for_completion=False,
            timeout=10
        ),
        
        TestCase(
            name="边界-超短需求",
            payload={
                "requirement": TEST_REQUIREMENTS["edge_short"],
                "target_ce": 99.5,
                "max_iterations": 5,
                "mode": "multi_agent"
            },
            expected_status=200,  # 可能接受但效果差
            check_fields=["correlation_id"],
            description="超短需求处理",
            mode=TestMode.MULTI_AGENT,
            wait_for_completion=False,
            timeout=60
        ),
        
        TestCase(
            name="边界-超长需求",
            payload={
                "requirement": TEST_REQUIREMENTS["edge_long"],
                "target_ce": 99.5,
                "max_iterations": 2,
                "mode": "multi_agent"
            },
            expected_status=200,  # 或 413
            check_fields=["correlation_id"],
            description="超长需求截断或处理",
            mode=TestMode.MULTI_AGENT,
            wait_for_completion=False,
            timeout=60
        ),
        
        TestCase(
            name="边界-XSS注入尝试",
            payload={
                "requirement": TEST_REQUIREMENTS["edge_special"],
                "target_ce": 99.5,
                "max_iterations": 2,
                "mode": "multi_agent"
            },
            expected_status=200,
            check_fields=["correlation_id"],
            description="XSS安全测试",
            mode=TestMode.MULTI_AGENT,
            wait_for_completion=False,
            timeout=60
        ),
        
        TestCase(
            name="边界-无效目标值",
            payload={
                "requirement": TEST_REQUIREMENTS["invalid_target"],
                "target_ce": 150.0,  # 不可能的值
                "max_iterations": 5,
                "mode": "multi_agent"
            },
            expected_status=422,  # 或 200 但会失败
            check_fields=[],
            description="无效CE目标值",
            mode=TestMode.MULTI_AGENT,
            wait_for_completion=False,
            timeout=60
        ),
        
        TestCase(
            name="边界-超范围迭代",
            payload={
                "requirement": TEST_REQUIREMENTS["simple"],
                "target_ce": 99.5,
                "max_iterations": 100,  # 可能超出限制
                "mode": "multi_agent"
            },
            expected_status=422,  # 或截断为最大值
            check_fields=["correlation_id"],
            description="超范围迭代次数",
            mode=TestMode.MULTI_AGENT,
            wait_for_completion=False,
            timeout=60
        ),
        
        # 缺失必填参数
        TestCase(
            name="边界-缺失需求",
            payload={
                "target_ce": 99.5,
                "max_iterations": 5,
                "mode": "multi_agent"
            },
            expected_status=422,
            check_fields=["detail"],
            description="缺少requirement字段",
            mode=TestMode.MULTI_AGENT,
            wait_for_completion=False,
            timeout=10
        ),
        
        TestCase(
            name="边界-无效模式",
            payload={
                "requirement": TEST_REQUIREMENTS["simple"],
                "target_ce": 99.5,
                "max_iterations": 5,
                "mode": "invalid_mode"
            },
            expected_status=422,  # 或 200 但使用默认
            check_fields=[],
            description="无效的模式参数",
            mode=TestMode.MULTI_AGENT,
            wait_for_completion=False,
            timeout=10
        ),
        
        # ===== 多语言测试 =====
        
        TestCase(
            name="MA-英文需求",
            payload={
                "requirement": TEST_REQUIREMENTS["english"],
                "target_ce": 99.5,
                "max_iterations": 3,
                "mode": "multi_agent"
            },
            expected_status=200,
            check_fields=["correlation_id"],
            description="英文需求处理",
            mode=TestMode.MULTI_AGENT,
            wait_for_completion=False,
            timeout=120
        ),
        
        TestCase(
            name="MA-中英混合",
            payload={
                "requirement": TEST_REQUIREMENTS["mixed"],
                "target_ce": 99.5,
                "max_iterations": 3,
                "mode": "multi_agent"
            },
            expected_status=200,
            check_fields=["correlation_id"],
            description="中英混合需求",
            mode=TestMode.MULTI_AGENT,
            wait_for_completion=False,
            timeout=120
        ),
    ]


# ==============================================================================
# 状态轮询器
# ==============================================================================

class WorkflowMonitor:
    """监控多智能体工作流状态"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
    
    def poll_status(self, correlation_id: str, max_wait: int = 600, interval: int = 5) -> Dict:
        """轮询工作流状态直到完成或超时"""
        start_time = time.time()
        history = []
        
        print(f"  开始轮询 {correlation_id[:8]}... (最长{max_wait}s)")
        
        while time.time() - start_time < max_wait:
            try:
                resp = self.session.get(
                    f"{self.base_url}/research/status/{correlation_id}",
                    timeout=10
                )
                
                if resp.status_code == 404:
                    print(f"  ⚠️  工作流未找到")
                    return {"status": "not_found", "history": history}
                
                if resp.status_code != 200:
                    print(f"  ⚠️  查询失败: HTTP {resp.status_code}")
                    time.sleep(interval)
                    continue
                
                data = resp.json()
                current_state = data.get("state", "unknown")
                current_iter = data.get("current_iteration", 0)
                max_iter = data.get("max_iterations", 0)
                
                # 记录状态变化
                if not history or history[-1]["state"] != current_state:
                    history.append({
                        "time": time.time() - start_time,
                        "state": current_state,
                        "iteration": current_iter
                    })
                    print(f"  [{time.time()-start_time:.1f}s] 状态: {current_state} | 迭代: {current_iter}/{max_iter}")
                
                # 检查是否完成
                if current_state in ["completed", "failed", "timeout"]:
                    return {
                        "status": current_state,
                        "final_data": data,
                        "duration": time.time() - start_time,
                        "history": history
                    }
                
                time.sleep(interval)
                
            except Exception as e:
                print(f"  ⚠️  轮询异常: {e}")
                time.sleep(interval)
        
        return {
            "status": "polling_timeout",
            "duration": time.time() - start_time,
            "history": history
        }


# ==============================================================================
# 测试执行器
# ==============================================================================

class ResearchStartTester:
    def __init__(self):
        self.results: List[Dict] = []
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        self.monitor = WorkflowMonitor(BASE_URL)
    
    def print_header(self, text: str):
        print(f"\n{'='*70}")
        print(f" {text}")
        print(f"{'='*70}")
    
    def print_result(self, success: bool, message: str):
        icon = "✅" if success else "❌"
        print(f"{icon} {message}")
    
    def run_single_test(self, test_case: TestCase) -> Dict:
        """执行单个测试用例"""
        start_time = time.time()
        
        result = {
            "name": test_case.name,
            "description": test_case.description,
            "mode": test_case.mode.value,
            "expected_status": test_case.expected_status,
            "wait_for_completion": test_case.wait_for_completion,
            "success": False,
            "checks": {},
            "stages": {}
        }
        
        try:
            # Stage 1: 启动工作流
            print(f"\n  [Stage 1] 启动工作流...")
            stage1_start = time.time()
            
            resp = self.session.post(
                START_ENDPOINT,
                json=test_case.payload,
                timeout=test_case.timeout
            )
            
            stage1_elapsed = time.time() - stage1_start
            result["stages"]["start"] = {
                "status_code": resp.status_code,
                "elapsed": stage1_elapsed
            }
            
            # 状态码检查
            status_match = resp.status_code == test_case.expected_status
            result["checks"]["status_code"] = status_match
            
            if not status_match:
                result["error"] = f"状态码不匹配: 期望 {test_case.expected_status}, 实际 {resp.status_code}"
                result["response_text"] = resp.text[:200]
                return result
            
            # 解析响应
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    result["start_response"] = data
                    
                    # 检查必要字段
                    for field in test_case.check_fields:
                        has_field = field in data
                        result["checks"][f"has_{field}"] = has_field
                    
                    # 多智能体模式：获取correlation_id并轮询
                    if test_case.mode == TestMode.MULTI_AGENT and test_case.wait_for_completion:
                        corr_id = data.get("correlation_id")
                        if corr_id:
                            result["correlation_id"] = corr_id
                            
                            # Stage 2: 轮询状态
                            print(f"  [Stage 2] 轮询工作流状态...")
                            poll_result = self.monitor.poll_status(
                                corr_id, 
                                max_wait=test_case.timeout - stage1_elapsed - 10,
                                interval=5
                            )
                            
                            result["stages"]["polling"] = poll_result
                            result["checks"]["workflow_completed"] = poll_result["status"] == "completed"
                            
                            # 如果完成，尝试获取最终结果
                            if poll_result["status"] == "completed":
                                final_data = poll_result.get("final_data", {})
                                result["checks"]["has_final_state"] = "state" in final_data
                    
                    # ReAct模式：同步等待结果
                    elif test_case.mode == TestMode.REACT:
                        # ReAct是同步返回的，结果在start_response中
                        result["checks"]["has_result"] = "result" in data
                        if "execution_trace" in data:
                            result["checks"]["has_trace"] = len(data["execution_trace"]) > 0
                    
                except json.JSONDecodeError as e:
                    result["checks"]["json_parse"] = False
                    result["error"] = f"JSON解析失败: {e}"
            else:
                # 错误响应检查
                result["response_text"] = resp.text[:300]
                # 对于预期错误的请求，只要状态码匹配就算成功
                if status_match:
                    result["checks"]["error_handling"] = True
            
            # 总体成功判断
            result["elapsed_total"] = time.time() - start_time
            result["success"] = all(result["checks"].values()) if result["checks"] else status_match
            
        except requests.exceptions.Timeout:
            result["error"] = f"请求超时 (> {test_case.timeout}s)"
            result["elapsed_total"] = time.time() - start_time
        except Exception as e:
            result["error"] = str(e)
            result["elapsed_total"] = time.time() - start_time
        
        return result
    
    def run_all_tests(self, filter_mode: Optional[str] = None):
        """运行所有测试"""
        test_cases = build_test_cases()
        
        # 过滤测试用例
        if filter_mode:
            test_cases = [tc for tc in test_cases if tc.mode.value == filter_mode]
        
        self.print_header("Multi-Agent Research 端口测试")
        print(f"目标端点: {START_ENDPOINT}")
        print(f"测试用例数: {len(test_cases)}")
        
        # 服务健康检查
        try:
            health = self.session.get(f"{BASE_URL}/docs", timeout=5)
            print(f"服务状态: {'在线' if health.status_code == 200 else '异常'}")
        except Exception as e:
            print(f"⚠️  警告: 无法连接服务: {e}")
            return
        
        # 执行测试
        for i, tc in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}] {tc.name}")
            print(f"  模式: {tc.mode.value} | 描述: {tc.description}")
            
            result = self.run_single_test(tc)
            self.results.append(result)
            
            # 打印结果
            if "error" in result and not result.get("checks", {}).get("status_code"):
                self.print_result(False, f"执行失败: {result['error']}")
            else:
                status_ok = result["checks"].get("status_code", False)
                self.print_result(status_ok, 
                    f"HTTP {result['stages']['start']['status_code']} "
                    f"(期望 {tc.expected_status}) - "
                    f"总耗时: {result['elapsed_total']:.2f}s"
                )
                
                # 打印详细检查
                for check_name, check_result in result["checks"].items():
                    if check_name != "status_code":
                        icon = "  ✓" if check_result else "  ✗"
                        print(f"{icon} {check_name}: {check_result}")
                
                # 打印工作流结果摘要
                if "stages" in result and "polling" in result["stages"]:
                    poll = result["stages"]["polling"]
                    print(f"  📊 工作流结果: {poll['status']} | "
                          f"耗时: {poll.get('duration', 0):.1f}s | "
                          f"状态变化: {len(poll.get('history', []))}次")
        
        self.print_report()
    
    def print_report(self):
        """打印测试报告"""
        self.print_header("测试报告总结")
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.get("success", False))
        failed = total - passed
        
        print(f"总测试数: {total}")
        print(f"通过: {passed} ({passed/total*100:.1f}%)")
        print(f"失败: {failed} ({failed/total*100:.1f}%)")
        
        # 按模式统计
        ma_tests = [r for r in self.results if r["mode"] == "multi_agent"]
        react_tests = [r for r in self.results if r["mode"] == "react"]
        
        print(f"\n按模式统计:")
        print(f"  Multi-Agent: {sum(1 for r in ma_tests if r['success'])}/{len(ma_tests)}")
        print(f"  ReAct: {sum(1 for r in react_tests if r['success'])}/{len(react_tests)}")
        
        # 性能统计
        completed_workflows = [
            r for r in self.results 
            if r.get("stages", {}).get("polling", {}).get("status") == "completed"
        ]
        if completed_workflows:
            durations = [r["stages"]["polling"]["duration"] for r in completed_workflows]
            print(f"\n工作流性能统计 (成功完成):")
            print(f"  样本数: {len(durations)}")
            print(f"  平均: {sum(durations)/len(durations):.1f}s")
            print(f"  最快: {min(durations):.1f}s")
            print(f"  最慢: {max(durations):.1f}s")
        
        # 失败详情
        if failed > 0:
            print(f"\n失败的测试:")
            for r in self.results:
                if not r.get("success", False):
                    error_msg = r.get("error", "检查项未通过")
                    print(f"  - {r['name']}: {error_msg}")
        
        # 保存报告
        report_file = f"research_start_test_report_{int(time.time())}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n详细报告已保存: {report_file}")


# ==============================================================================
# 专项功能测试
# ==============================================================================

class SpecificFunctionTests:
    """专项功能测试"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.monitor = WorkflowMonitor(BASE_URL)
    
    def test_workflow_lifecycle(self):
        """测试完整工作流生命周期"""
        print("\n" + "="*70)
        print("专项测试: 完整工作流生命周期")
        print("="*70)
        
        # 1. 启动工作流
        print("\n[1/4] 启动工作流...")
        resp = self.session.post(START_ENDPOINT, json={
            "requirement": "设计一款高电压电解液，目标CE 99.5%",
            "target_ce": 99.5,
            "max_iterations": 3,
            "mode": "multi_agent"
        })
        
        if resp.status_code != 200:
            print(f"❌ 启动失败: {resp.text}")
            return
        
        data = resp.json()
        corr_id = data["correlation_id"]
        print(f"✅ 启动成功: {corr_id}")
        
        # 2. 立即查询状态
        print("\n[2/4] 立即查询状态...")
        status1 = self.session.get(f"{STATUS_ENDPOINT}/{corr_id}")
        print(f"  状态: {status1.json().get('state', 'unknown')}")
        
        # 3. 轮询到完成
        print("\n[3/4] 轮询到完成...")
        result = self.monitor.poll_status(corr_id, max_wait=300, interval=3)
        print(f"  最终结果: {result['status']}")
        
        # 4. 再次查询（验证数据保留）
        print("\n[4/4] 完成后查询...")
        status2 = self.session.get(f"{STATUS_ENDPOINT}/{corr_id}")
        final_data = status2.json()
        print(f"  状态: {final_data.get('state')}")
        print(f"  迭代: {final_data.get('current_iteration')}/{final_data.get('max_iterations')}")
        
        return result
    
    def test_concurrent_workflows(self, count: int = 3):
        """测试并发工作流"""
        print(f"\n" + "="*70)
        print(f"专项测试: 并发工作流 ({count}个)")
        print("="*70)
        
        corr_ids = []
        
        # 启动多个工作流
        print(f"\n[1/2] 启动{count}个工作流...")
        for i in range(count):
            resp = self.session.post(START_ENDPOINT, json={
                "requirement": f"并发测试电解液设计 {i+1}",
                "target_ce": 99.0 + i * 0.1,
                "max_iterations": 2,
                "mode": "multi_agent"
            })
            if resp.status_code == 200:
                corr_id = resp.json()["correlation_id"]
                corr_ids.append(corr_id)
                print(f"  工作流 {i+1}: {corr_id[:8]}...")
            else:
                print(f"  工作流 {i+1}: 启动失败")
        
        # 并发轮询
        print(f"\n[2/2] 并发监控...")
        with ThreadPoolExecutor(max_workers=count) as executor:
            futures = {
                executor.submit(self.monitor.poll_status, cid, 180, 3): cid 
                for cid in corr_ids
            }
            
            for future in as_completed(futures):
                cid = futures[future]
                try:
                    result = future.result()
                    print(f"  {cid[:8]}...: {result['status']} ({result.get('duration', 0):.1f}s)")
                except Exception as e:
                    print(f"  {cid[:8]}...: 异常 {e}")
    
    def test_mode_comparison(self):
        """对比 Multi-Agent 和 ReAct 模式"""
        print("\n" + "="*70)
        print("专项测试: 模式对比")
        print("="*70)
        
        requirement = "设计一款低温电解液，-20℃下导电率>5mS/cm"
        
        # Multi-Agent 模式
        print("\n[Multi-Agent 模式]")
        start_ma = time.time()
        resp_ma = self.session.post(START_ENDPOINT, json={
            "requirement": requirement,
            "target_ce": 98.5,
            "max_iterations": 2,
            "mode": "multi_agent"
        })
        elapsed_ma = time.time() - start_ma
        
        if resp_ma.status_code == 200:
            corr_id = resp_ma.json()["correlation_id"]
            print(f"  启动耗时: {elapsed_ma:.2f}s")
            result_ma = self.monitor.poll_status(corr_id, max_wait=180, interval=3)
            print(f"  总耗时: {result_ma.get('duration', 0):.1f}s")
            print(f"  结果: {result_ma['status']}")
        
        # ReAct 模式
        print("\n[ReAct 模式]")
        start_react = time.time()
        resp_react = self.session.post(START_ENDPOINT, json={
            "requirement": requirement,
            "max_cycles": 8,
            "target_ce": 98.5,
            "mode": "react"
        })
        elapsed_react = time.time() - start_react
        
        if resp_react.status_code == 200:
            data = resp_react.json()
            print(f"  总耗时: {elapsed_react:.2f}s")
            print(f"  结果: {data.get('status')}")
            if "execution_trace" in data:
                print(f"  执行步数: {len(data['execution_trace'])}")
    
    def test_error_recovery(self):
        """测试错误恢复"""
        print("\n" + "="*70)
        print("专项测试: 错误场景")
        print("="*70)
        
        # 测试无效 correlation_id
        print("\n[1/2] 查询无效ID...")
        fake_id = "invalid-id-12345"
        resp = self.session.get(f"{STATUS_ENDPOINT}/{fake_id}")
        print(f"  状态码: {resp.status_code} (期望 404)")
        print(f"  响应: {resp.text[:100]}")
        
        # 测试已完成的ID再次查询
        print("\n[2/2] 重复查询已完成工作流...")
        # 先启动一个快速完成的
        resp = self.session.post(START_ENDPOINT, json={
            "requirement": "简单测试",
            "target_ce": 90.0,
            "max_iterations": 1,
            "mode": "multi_agent"
        })
        if resp.status_code == 200:
            corr_id = resp.json()["correlation_id"]
            result = self.monitor.poll_status(corr_id, max_wait=120, interval=2)
            print(f"  首次查询: {result['status']}")
            
            # 再次查询
            resp2 = self.session.get(f"{STATUS_ENDPOINT}/{corr_id}")
            print(f"  重复查询: HTTP {resp2.status_code}")
    
    def run_all(self):
        self.test_workflow_lifecycle()
        self.test_concurrent_workflows(3)
        self.test_mode_comparison()
        self.test_error_recovery()


# ==============================================================================
# 压力测试
# ==============================================================================

def stress_test_research_start(concurrent: int = 5, iterations: int = 2):
    """压力测试：并发启动大量工作流"""
    print(f"\n{'='*70}")
    print(f"压力测试: {concurrent}并发 × {iterations}轮")
    print(f"{'='*70}")
    
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    def launch_single(i: int):
        start = time.time()
        try:
            resp = session.post(START_ENDPOINT, json={
                "requirement": f"压力测试电解液 {i}",
                "target_ce": 99.0,
                "max_iterations": 2,
                "mode": "multi_agent"
            }, timeout=30)
            return {
                "id": i,
                "status": resp.status_code,
                "time": time.time() - start,
                "success": resp.status_code == 200,
                "corr_id": resp.json().get("correlation_id", "")[:8] if resp.status_code == 200 else None
            }
        except Exception as e:
            return {
                "id": i,
                "status": 0,
                "time": time.time() - start,
                "success": False,
                "error": str(e)
            }
    
    all_results = []
    
    for round_num in range(iterations):
        print(f"\n第 {round_num + 1}/{iterations} 轮...")
        round_start = time.time()
        
        with ThreadPoolExecutor(max_workers=concurrent) as executor:
            futures = [executor.submit(launch_single, i) for i in range(concurrent)]
            results = [f.result() for f in as_completed(futures)]
        
        round_time = time.time() - round_start
        success_count = sum(1 for r in results if r["success"])
        avg_time = sum(r["time"] for r in results) / len(results)
        
        print(f"  轮次耗时: {round_time:.2f}s")
        print(f"  成功率: {success_count}/{concurrent}")
        print(f"  平均响应: {avg_time:.2f}s")
        
        all_results.extend(results)
    
    # 总统计
    print(f"\n{'='*70}")
    print("压力测试总结")
    print(f"{'='*70}")
    total = len(all_results)
    success = sum(1 for r in all_results if r["success"])
    print(f"总请求: {total}")
    print(f"成功: {success} ({success/total*100:.1f}%)")
    print(f"平均耗时: {sum(r['time'] for r in all_results)/total:.2f}s")
    print(f"最慢: {max(r['time'] for r in all_results):.2f}s")


# ==============================================================================
# 主入口
# ==============================================================================

def main():
    print("""
    ███╗   ███╗██╗   ██╗██╗  ████████╗██╗      █████╗  ██████╗ ███████╗███╗   ██╗████████╗
    ████╗ ████║██║   ██║██║  ╚══██╔══╝██║     ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
    ██╔████╔██║██║   ██║██║     ██║   ██║     ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   
    ██║╚██╔╝██║██║   ██║██║     ██║   ██║     ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   
    ██║ ╚═╝ ██║╚██████╔╝███████╗██║   ███████╗██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   
    ╚═╝     ╚═╝ ╚═════╝ ╚══════╝╚═╝   ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   
                                                                                            
    Multi-Agent Research API 测试工具 (/research/start)
    """)
    
    import argparse
    parser = argparse.ArgumentParser(description="Research Start 端口测试")
    parser.add_argument("--mode", choices=["full", "specific", "stress", "quick", "ma", "react"], 
                       default="full", help="测试模式")
    parser.add_argument("--url", default="http://localhost:8000", help="服务基础URL")
    parser.add_argument("--concurrent", type=int, default=5, help="并发数（压力测试）")
    parser.add_argument("--iterations", type=int, default=2, help="迭代轮数（压力测试）")
    
    args = parser.parse_args()
    
    global BASE_URL, START_ENDPOINT, STATUS_ENDPOINT, RUN_ENDPOINT
    BASE_URL = args.url
    START_ENDPOINT = f"{BASE_URL}/research/start"
    STATUS_ENDPOINT = f"{BASE_URL}/research/status"
    RUN_ENDPOINT = f"{BASE_URL}/run"
    
    if args.mode == "full":
        # 完整测试
        tester = ResearchStartTester()
        tester.run_all_tests()
        
        specific = SpecificFunctionTests()
        specific.run_all()
        
    elif args.mode == "specific":
        # 仅专项测试
        specific = SpecificFunctionTests()
        specific.run_all()
        
    elif args.mode == "stress":
        # 仅压力测试
        stress_test_research_start(args.concurrent, args.iterations)
        
    elif args.mode == "quick":
        # 快速验证
        print("\n快速验证...")
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # 测试启动
        resp = session.post(START_ENDPOINT, json={
            "requirement": "快速测试",
            "target_ce": 98.0,
            "max_iterations": 1,
            "mode": "multi_agent"
        }, timeout=30)
        
        print(f"启动状态: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            corr_id = data.get("correlation_id")
            print(f"Correlation ID: {corr_id[:8]}..." if corr_id else "无ID")
            
            # 立即查询状态
            if corr_id:
                status = session.get(f"{STATUS_ENDPOINT}/{corr_id}")
                print(f"状态查询: {status.status_code}")
                if status.status_code == 200:
                    print(f"当前状态: {status.json().get('state')}")
        else:
            print(f"错误: {resp.text[:200]}")
            
    elif args.mode == "ma":
        # 仅多智能体测试
        tester = ResearchStartTester()
        tester.run_all_tests(filter_mode="multi_agent")
        
    elif args.mode == "react":
        # 仅ReAct测试
        tester = ResearchStartTester()
        tester.run_all_tests(filter_mode="react")


if __name__ == "__main__":
    main()