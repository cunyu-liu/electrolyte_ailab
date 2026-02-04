"""
Deep Research 端口测试套件
测试 /research/deep 端点的各种功能和边界条件

# 1. 确保服务已启动
python your_server.py

# 2. 运行完整测试
python test_deep_research.py --mode full

# 3. 仅运行专项功能测试
python test_deep_research.py --mode specific

# 4. 压力测试（5并发）
python test_deep_research.py --mode stress --concurrent 5

# 5. 快速验证
python test_deep_research.py --mode quick

# 6. 测试远程服务
python test_deep_research.py --url http://your-server:8000 --mode full

"""

import asyncio
import json
import time
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import sys


# ==============================================================================
# 配置
# ==============================================================================

BASE_URL = "http://localhost:8000"
DEEP_RESEARCH_ENDPOINT = f"{BASE_URL}/research/deep"
CHAT_ENDPOINT = f"{BASE_URL}/chat"

# 测试查询样本
TEST_QUERIES = {
    "standard": "高电压电解液中LiPF6的分解机理及其抑制策略",
    "simple": "锂电池电解液导电性优化",
    "complex": "基于局部高浓度电解液（LHCE）设计的溶剂化结构调控策略，以及其对锂离子传输动力学和界面稳定性的影响机制",
    "edge_empty": "",  # 边界：空字符串
    "edge_long": "LiPF6" * 100,  # 边界：超长查询
    "edge_special": "电解液<script>alert('xss')</script>安全性",  # 边界：特殊字符
    "english": "Mechanism of SEI formation in carbonate-based electrolytes",
    "mixed": "高电压下EC/DMC溶剂体系的oxidation stability研究",
}


# ==============================================================================
# 测试用例定义
# ==============================================================================

@dataclass
class TestCase:
    name: str
    payload: Dict
    expected_status: int
    check_fields: List[str]
    description: str


# 构建测试用例
def build_test_cases() -> List[TestCase]:
    return [
        # 标准测试
        TestCase(
            name="标准深度研究",
            payload={
                "query": TEST_QUERIES["standard"],
                "depth": 2,
                "breadth": 3,
                "context": "针对4.5V以上高电压正极材料体系"
            },
            expected_status=200,
            check_fields=["status", "findings", "findings_id", "formatted_report"],
            description="标准参数的深度研究请求"
        ),
        
        # 不同深度测试
        TestCase(
            name="最大深度探索",
            payload={
                "query": TEST_QUERIES["complex"], 
                "depth": 3,  # 最大深度
                "breadth": 5,  # 最大广度
                "context": ""
            },
            expected_status=200,
            check_fields=["findings"],
            description="测试最大深度和广度的性能"
        ),
        
        TestCase(
            name="浅层快速探索",
            payload={
                "query": TEST_QUERIES["simple"],
                "depth": 1,
                "breadth": 2,
                "context": ""
            },
            expected_status=200,
            check_fields=["findings"],
            description="最小参数的快速响应测试"
        ),
        
        # 上下文测试
        TestCase(
            name="带上下文的精准搜索",
            payload={
                "query": "溶剂化结构",
                "depth": 2,
                "breadth": 3,
                "context": "已知的共溶剂包括DME、DOL、TTE，关注氟化醚类溶剂"
            },
            expected_status=200,
            check_fields=["findings"],
            description="测试上下文对搜索质量的提升"
        ),
        
        # 多语言测试
        TestCase(
            name="英文查询",
            payload={
                "query": TEST_QUERIES["english"],
                "depth": 2,
                "breadth": 3,
                "context": ""
            },
            expected_status=200,
            check_fields=["status"],
            description="测试英文查询的支持"
        ),
        
        TestCase(
            name="中英混合查询",
            payload={
                "query": TEST_QUERIES["mixed"],
                "depth": 2,
                "breadth": 3,
                "context": ""
            },
            expected_status=200,
            check_fields=["status"],
            description="测试中英文混合查询"
        ),
        
        # 边界测试
        TestCase(
            name="空查询（边界）",
            payload={
                "query": TEST_QUERIES["edge_empty"],
                "depth": 2,
                "breadth": 3,
                "context": ""
            },
            expected_status=422,  # FastAPI 验证错误，或 200 但返回空结果
            check_fields=[],
            description="测试空查询的处理"
        ),
        
        TestCase(
            name="超长查询（边界）",
            payload={
                "query": TEST_QUERIES["edge_long"],
                "depth": 1,
                "breadth": 2,
                "context": ""
            },
            expected_status=200,  # 或 413 如果服务器有长度限制
            check_fields=["status"],
            description="测试超长查询的截断或处理"
        ),
        
        TestCase(
            name="特殊字符（安全）",
            payload={
                "query": TEST_QUERIES["edge_special"],
                "depth": 2,
                "breadth": 3,
                "context": ""
            },
            expected_status=200,
            check_fields=["status"],
            description="测试特殊字符的XSS防护"
        ),
        
        # 参数边界测试
        TestCase(
            name="超范围深度",
            payload={
                "query": "测试",
                "depth": 10,  # 超出最大值
                "breadth": 3,
                "context": ""
            },
            expected_status=422,  # Pydantic 验证错误
            check_fields=["detail"],
            description="测试超出范围的 depth 参数验证"
        ),
        
        TestCase(
            name="超范围广度",
            payload={
                "query": "测试",
                "depth": 2,
                "breadth": 100,  # 超出最大值
                "context": ""
            },
            expected_status=422,
            check_fields=["detail"],
            description="测试超出范围的 breadth 参数验证"
        ),
        
        # 缺失参数测试
        TestCase(
            name="缺失可选参数",
            payload={
                "query": "电解液添加剂"
                # 省略 depth, breadth, context
            },
            expected_status=200,
            check_fields=["status"],
            description="测试使用默认值"
        ),
        
        TestCase(
            name="缺失必填参数",
            payload={
                "depth": 2,
                "breadth": 3
                # 缺少 query
            },
            expected_status=422,
            check_fields=["detail"],
            description="测试缺少必填参数的处理"
        ),
    ]


# ==============================================================================
# 测试执行器
# ==============================================================================

class DeepResearchTester:
    def __init__(self):
        self.results: List[Dict] = []
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def print_header(self, text: str):
        print(f"\n{'='*60}")
        print(f" {text}")
        print(f"{'='*60}")
    
    def print_result(self, success: bool, message: str):
        icon = "✅" if success else "❌"
        print(f"{icon} {message}")
    
    def run_single_test(self, test_case: TestCase) -> Dict:
        """执行单个测试用例"""
        start_time = time.time()
        
        try:
            response = self.session.post(
                DEEP_RESEARCH_ENDPOINT,
                json=test_case.payload,
                timeout=3000  # Deep research 可能需要较长时间
            )
            
            elapsed = time.time() - start_time
            
            result = {
                "name": test_case.name,
                "description": test_case.description,
                "expected_status": test_case.expected_status,
                "actual_status": response.status_code,
                "elapsed_time": elapsed,
                "success": False,
                "checks": {},
                "response_preview": ""
            }
            
            # 状态码检查
            status_match = response.status_code == test_case.expected_status
            result["checks"]["status_code"] = status_match
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    result["response_data"] = data
                    
                    # 字段存在性检查
                    for field in test_case.check_fields:
                        result["checks"][f"has_field_{field}"] = field in data
                    
                    # 内容质量检查
                    if "findings" in data:
                        findings = data["findings"]
                        result["checks"]["findings_count"] = len(findings)
                        result["checks"]["has_findings"] = len(findings) > 0
                        
                        # 检查发现内容的结构
                        if findings:
                            first = findings[0]
                            result["checks"]["finding_has_content"] = "content" in first
                            result["checks"]["finding_has_confidence"] = "confidence" in first
                    
                    # findings_id 检查
                    if "findings_id" in data:
                        result["checks"]["findings_id_valid"] = bool(data["findings_id"])
                    
                    result["response_preview"] = json.dumps(data, ensure_ascii=False, indent=2)[:500]
                    
                except json.JSONDecodeError:
                    result["checks"]["json_parse"] = False
                    result["response_preview"] = response.text[:200]
            
            else:
                result["response_preview"] = response.text[:200]
                # 对于预期错误的请求，只要状态码匹配就算成功
                if status_match:
                    result["checks"]["error_handling"] = True
            
            # 总体成功判断
            result["success"] = all(result["checks"].values()) if result["checks"] else status_match
            
        except requests.exceptions.Timeout:
            result = {
                "name": test_case.name,
                "success": False,
                "error": "Timeout (>3000s)",
                "elapsed_time": time.time() - start_time
            }
        except Exception as e:
            result = {
                "name": test_case.name,
                "success": False,
                "error": str(e),
                "elapsed_time": time.time() - start_time
            }
        
        return result
    
    def run_all_tests(self):
        """运行所有测试"""
        test_cases = build_test_cases()
        
        self.print_header("Deep Research 端口测试开始")
        print(f"目标端点: {DEEP_RESEARCH_ENDPOINT}")
        print(f"测试用例数: {len(test_cases)}")
        
        # 先检查服务健康
        try:
            health_check = self.session.get(f"{BASE_URL}/docs", timeout=5)
            print(f"服务状态: {'在线' if health_check.status_code == 200 else '异常'}")
        except:
            print("⚠️  警告: 无法连接到服务，请确保服务已启动")
            return
        
        # 顺序执行测试（避免并发压垮服务）
        for i, tc in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}] 测试: {tc.name}")
            print(f"描述: {tc.description}")
            
            result = self.run_single_test(tc)
            self.results.append(result)
            
            # 打印结果
            if "error" in result:
                self.print_result(False, f"执行失败: {result['error']}")
            else:
                status_ok = result["checks"].get("status_code", False)
                self.print_result(status_ok, 
                    f"HTTP {result['actual_status']} (预期 {result['expected_status']}) - {result['elapsed_time']:.2f}s")
                
                # 打印详细检查
                for check_name, check_result in result["checks"].items():
                    if check_name != "status_code":
                        icon = "  ✓" if check_result else "  ✗"
                        print(f"{icon} {check_name}: {check_result}")
                
                if result["response_preview"]:
                    print(f"  响应预览: {result['response_preview'][:150]}...")
        
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
        
        # 性能统计
        times = [r.get("elapsed_time", 0) for r in self.results if "elapsed_time" in r]
        if times:
            print(f"\n性能统计:")
            print(f"  平均响应时间: {sum(times)/len(times):.2f}s")
            print(f"  最慢: {max(times):.2f}s")
            print(f"  最快: {min(times):.2f}s")
        
        # 失败详情
        if failed > 0:
            print(f"\n失败的测试:")
            for r in self.results:
                if not r.get("success", False):
                    print(f"  - {r['name']}: {r.get('error', '检查项未通过')}")
        
        # 保存详细报告
        report_file = f"/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/test_result/deep_research_test_report_{int(time.time())}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"\n详细报告已保存: {report_file}")


# ==============================================================================
# 特定功能测试
# ==============================================================================

class SpecificFunctionTests:
    """特定功能的专项测试"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_data_persistence(self):
        """测试 findings_id 的数据持久化"""
        print("\n" + "="*60)
        print("专项测试: 数据持久化验证")
        print("="*60)
        
        # 1. 执行搜索
        resp = self.session.post(DEEP_RESEARCH_ENDPOINT, json={
            "query": "电解液阻燃剂选择",
            "depth": 1,
            "breadth": 2
        })
        
        if resp.status_code != 200:
            print("❌ 初始请求失败")
            return
        
        data = resp.json()
        findings_id = data.get("findings_id")
        
        if not findings_id:
            print("❌ 未返回 findings_id")
            return
        
        print(f"✅ 获取到 findings_id: {findings_id}")
        
        # 2. 验证数据可通过其他端点访问（如果系统支持）
        # 这里假设可以通过某种方式验证，实际取决于你的API设计
        print("提示: 可通过 /research/status/{id} 或其他端点验证数据持久化")
    
    def test_reproducibility(self):
        """测试相同查询的稳定性"""
        print("\n" + "="*60)
        print("专项测试: 可重复性验证（相同查询执行2次）")
        print("="*60)
        
        query = "LiFSI 锂盐的优势与应用"
        
        results = []
        for i in range(2):
            resp = self.session.post(DEEP_RESEARCH_ENDPOINT, json={
                "query": query,
                "depth": 2,
                "breadth": 3
            })
            if resp.status_code == 200:
                data = resp.json()
                findings_count = len(data.get("findings", []))
                results.append(findings_count)
                print(f"  第{i+1}次: {findings_count} 条发现")
        
        if len(results) == 2:
            if results[0] == results[1]:
                print("✅ 两次查询返回相同数量的发现（注意：内容可能因异步检索略有差异）")
            else:
                print(f"⚠️  两次查询发现数量不同: {results[0]} vs {results[1]}")
                print("   （这可能是正常的，因为检索和LLM生成有一定随机性）")
    
    def test_citation_quality(self):
        """测试引用质量"""
        print("\n" + "="*60)
        print("专项测试: 引用质量检查")
        print("="*60)
        
        resp = self.session.post(DEEP_RESEARCH_ENDPOINT, json={
            "query": "高电压电解液添加剂",
            "depth": 2,
            "breadth": 3
        })
        
        if resp.status_code != 200:
            return
        
        data = resp.json()
        findings = data.get("findings", [])
        
        if not findings:
            print("❌ 无发现")
            return
        
        # 检查引用信息完整性
        complete_citations = 0
        for i, f in enumerate(findings[:3]):  # 检查前3条
            print(f"\n发现 {i+1}:")
            print(f"  内容: {f.get('content', 'N/A')[:100]}...")
            print(f"  置信度: {f.get('confidence', 'N/A')}")
            
            locations = f.get("source_locations", [])
            print(f"  来源位置数: {len(locations)}")
            
            if locations:
                loc = locations[0]
                has_doc = bool(loc.get("doc_name"))
                has_page = loc.get("page", 0) > 0
                print(f"  文档名: {loc.get('doc_name', 'N/A')}")
                print(f"  页码: {loc.get('page', 'N/A')}")
                
                if has_doc and has_page:
                    complete_citations += 1
        
        print(f"\n✅ 完整引用信息: {complete_citations}/3")
    
    def test_depth_effectiveness(self):
        """测试不同深度的有效性"""
        print("\n" + "="*60)
        print("专项测试: 深度效果对比")
        print("="*60)
        
        query = "固态电解质界面(SEI)成膜机理"
        
        for depth in [1, 2, 3]:
            print(f"\n深度 {depth}:")
            start = time.time()
            resp = self.session.post(DEEP_RESEARCH_ENDPOINT, json={
                "query": query,
                "depth": depth,
                "breadth": 3
            })
            elapsed = time.time() - start
            
            if resp.status_code == 200:
                data = resp.json()
                findings = data.get("findings", [])
                
                # 统计不同探索深度的发现
                depth_dist = {}
                for f in findings:
                    d = f.get("exploration_depth", 0)
                    depth_dist[d] = depth_dist.get(d, 0) + 1
                
                print(f"  总发现: {len(findings)}")
                print(f"  耗时: {elapsed:.2f}s")
                print(f"  深度分布: {depth_dist}")
                
                # 检查是否有更深层次的内容
                if depth > 1 and max(depth_dist.keys()) >= 2:
                    print("  ✅ 成功探索到更深层次")
                elif depth == 1:
                    print("  ℹ️  浅层探索")
    
    def run_all(self):
        self.test_data_persistence()
        self.test_reproducibility()
        self.test_citation_quality()
        self.test_depth_effectiveness()


# ==============================================================================
# 压力测试
# ==============================================================================

def stress_test(concurrent_requests: int = 5):
    """并发压力测试"""
    print(f"\n{'='*60}")
    print(f"压力测试: {concurrent_requests} 并发请求")
    print(f"{'='*60}")
    
    def make_request(i: int):
        start = time.time()
        try:
            resp = requests.post(DEEP_RESEARCH_ENDPOINT, json={
                "query": f"并发测试查询 {i}: 电解液导电性",
                "depth": 2,
                "breadth": 2
            }, timeout=120)
            return {
                "id": i,
                "status": resp.status_code,
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
    
    start_all = time.time()
    with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
        results = list(executor.map(make_request, range(concurrent_requests)))
    
    total_time = time.time() - start_all
    
    success_count = sum(1 for r in results if r["success"])
    avg_time = sum(r["time"] for r in results) / len(results)
    
    print(f"总耗时: {total_time:.2f}s")
    print(f"成功率: {success_count}/{concurrent_requests}")
    print(f"平均响应时间: {avg_time:.2f}s")
    
    for r in results:
        status = "✅" if r["success"] else "❌"
        print(f"  {status} 请求 {r['id']}: {r['time']:.2f}s (HTTP {r['status']})")


# ==============================================================================
# 主入口
# ==============================================================================

def main():
    print("""
    ██████╗ ███████╗███████╗██████╗     ██████╗ ███████╗███████╗███████╗ █████╗ ██████╗  ██████╗██╗  ██╗
    ██╔══██╗██╔════╝██╔════╝██╔══██╗    ██╔══██╗██╔════╝██╔════╝██╔════╝██╔══██╗██╔══██╗██╔════╝██║  ██║
    ██║  ██║█████╗  █████╗  ██████╔╝    ██████╔╝█████╗  ███████╗█████╗  ███████║██████╔╝██║     ███████║
    ██║  ██║██╔══╝  ██╔══╝  ██╔═══╝     ██╔══██╗██╔══╝  ╚════██║██╔══╝  ██╔══██║██╔══██╗██║     ██╔══██║
    ██████╔╝███████╗███████╗██║         ██║  ██║███████╗███████║███████╗██║  ██║██║  ██║╚██████╗██║  ██║
    ╚═════╝ ╚══════╝╚══════╝╚═╝         ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
    
    Deep Research API 测试工具
    """)
    
    import argparse
    parser = argparse.ArgumentParser(description="Deep Research 端口测试")
    parser.add_argument("--mode", choices=["full", "specific", "stress", "quick"], 
                       default="full", help="测试模式")
    parser.add_argument("--url", default="http://localhost:8000", help="服务基础URL")
    parser.add_argument("--concurrent", type=int, default=5, help="并发请求数（压力测试）")
    
    args = parser.parse_args()
    
    global BASE_URL, DEEP_RESEARCH_ENDPOINT, CHAT_ENDPOINT
    BASE_URL = args.url
    DEEP_RESEARCH_ENDPOINT = f"{BASE_URL}/research/deep"
    CHAT_ENDPOINT = f"{BASE_URL}/chat"
    
    if args.mode == "full":
        # 完整测试套件
        tester = DeepResearchTester()
        tester.run_all_tests()
        
        # 专项测试
        specific = SpecificFunctionTests()
        specific.run_all()
        
    elif args.mode == "specific":
        # 仅专项测试
        specific = SpecificFunctionTests()
        specific.run_all()
        
    elif args.mode == "stress":
        # 仅压力测试
        stress_test(args.concurrent)
        
    elif args.mode == "quick":
        # 快速验证
        print("\n快速验证...")
        resp = requests.post(DEEP_RESEARCH_ENDPOINT, json={
            "query": "快速测试",
            "depth": 1,
            "breadth": 2
        }, timeout=30)
        print(f"状态码: {resp.status_code}")
        if resp.status_code == 200:
            print("✅ 服务正常")
            print(f"响应: {resp.json().get('status')}")
        else:
            print(f"❌ 错误: {resp.text[:200]}")


if __name__ == "__main__":
    main()