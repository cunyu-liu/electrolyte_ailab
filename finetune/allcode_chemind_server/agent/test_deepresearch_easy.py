#!/usr/bin/env python3
"""
Deep Research 专项测试工具
功能：测试 /research/deep 端点，清晰展示模型输入输出，保存完整 JSON 记录
python /Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/test_deepresearch_easy.py
"""

import requests
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class DeepResearchTester:
    def __init__(self, base_url: str = "http://localhost:8000", output_dir: str = "/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/test_result"):
        self.base_url = base_url
        self.endpoint = f"{base_url}/research/deep"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # 测试用例定义
        self.test_cases = [
            {
                "name": "基础技术查询",
                "payload": {
                    "query": "锂离子电池电解液中LiPF6的作用机理",
                    "depth": 2,
                    "breadth": 2
                }
            },
            {
                "name": "配方设计查询", 
                "payload": {
                    "query": "高电压电解液添加剂设计策略，要求电压>4.5V",
                    "depth": 3,
                    "breadth": 3
                }
            },
            {
                "name": "性能优化查询",
                "payload": {
                    "query": "如何提升电解液低温电导率至-20℃>5mS/cm",
                    "depth": 2,
                    "breadth": 2,
                    "context": {"temperature": "-20℃"}
                }
            }
        ]
    
    def print_section(self, title: str, content: str, color: str = "\033[94m"):
        """美观的格式化输出"""
        reset = "\033[0m"
        print(f"\n{color}{'='*80}{reset}")
        print(f"{color}{title:^80}{reset}")
        print(f"{color}{'='*80}{reset}")
        print(content)
        print(f"{color}{'-'*80}{reset}\n")
    
    def run_single_test(self, test_case: Dict) -> Dict[str, Any]:
        """执行单个 Deep Research 测试"""
        name = test_case["name"]
        payload = test_case["payload"]
        
        print(f"\n\033[93m>>> 开始测试: {name}\033[0m")
        print(f"查询内容: {payload['query'][:60]}...")
        print(f"参数: depth={payload.get('depth', 1)}, breadth={payload.get('breadth', 2)}")
        
        # 记录请求信息
        record = {
            "test_name": name,
            "timestamp": datetime.now().isoformat(),
            "request": {
                "url": self.endpoint,
                "method": "POST",
                "payload": payload
            },
            "response": None,
            "error": None,
            "metadata": {}
        }
        
        start_time = time.time()
        
        try:
            # 发送请求
            response = self.session.post(
                self.endpoint,
                json=payload,
                timeout=120  # 研究查询可能需要较长时间
            )
            
            elapsed = time.time() - start_time
            record["metadata"]["elapsed_seconds"] = elapsed
            
            # 检查响应状态
            record["metadata"]["status_code"] = response.status_code
            
            if response.status_code != 200:
                error_msg = f"HTTP 错误: {response.status_code}"
                record["error"] = error_msg
                record["response"] = {"text": response.text}
                print(f"\033[91m✗ {error_msg}\033[0m")
                return record
            
            # 解析 JSON 响应
            data = response.json()
            record["response"] = data
            
            # 打印成功信息
            print(f"\033[92m✓ 查询成功 | 耗时: {elapsed:.2f}s\033[0m")
            
            # 清晰展示模型输出
            self._display_results(data, name)
            
            return record
            
        except requests.exceptions.Timeout:
            error_msg = f"请求超时 (>120s)"
            record["error"] = error_msg
            print(f"\033[91m✗ {error_msg}\033[0m")
            return record
            
        except Exception as e:
            error_msg = f"异常: {str(e)}"
            record["error"] = error_msg
            print(f"\033[91m✗ {error_msg}\033[0m")
            return record
    
    def _display_results(self, data: Dict, test_name: str):
        """清晰格式化并展示模型输出"""
        
        # 1. 展示研究总结/分析（如果有）
        if "analysis" in data or "summary" in data:
            analysis = data.get("analysis") or data.get("summary", "")
            self.print_section(
                f"[{test_name}] 模型分析结果", 
                analysis if isinstance(analysis, str) else json.dumps(analysis, indent=2, ensure_ascii=False),
                "\033[92m"  # 绿色
            )
        
        # 2. 展示检索结果（如果有）
        if "results" in data and isinstance(data["results"], list):
            results = data["results"]
            print(f"\033[96m📚 检索到 {len(results)} 条相关文献/数据:\033[0m")
            
            for i, item in enumerate(results[:5], 1):  # 只展示前5条避免刷屏
                title = item.get("title", "无标题")
                content = item.get("content", item.get("summary", "无内容"))[:200]
                source = item.get("source", "未知来源")
                relevance = item.get("relevance_score", "N/A")
                
                print(f"\n  [{i}] {title}")
                print(f"      来源: {source} | 相关度: {relevance}")
                print(f"      摘要: {content}...")
            
            if len(results) > 5:
                print(f"\n  ... 还有 {len(results)-5} 条结果未展示")
        
        # 3. 展示关键数据字段
        key_fields = ["recommendations", "conclusion", "key_findings", "citations"]
        for field in key_fields:
            if field in data:
                self.print_section(
                    f"关键字段: {field}",
                    json.dumps(data[field], indent=2, ensure_ascii=False) if isinstance(data[field], (dict, list)) else str(data[field]),
                    "\033[93m"  # 黄色
                )
        
        # 4. 展示原始数据结构（调试用，限制长度）
        raw_preview = json.dumps(data, indent=2, ensure_ascii=False)[:1000]
        if len(json.dumps(data)) > 1000:
            raw_preview += "\n... (截断)"
        print(f"\033[90m📄 原始响应结构预览:\033[0m")
        print(raw_preview)
    
    def save_record(self, record: Dict):
        """保存详细记录到 JSON 文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_name = record["test_name"].replace(" ", "_")
        filename = f"research_{test_name}_{timestamp}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        
        print(f"\033[94m💾 详细数据已保存: {filepath}\033[0m")
        return filepath
    
    def run_all_tests(self):
        """运行所有测试用例"""
        print("\n" + "="*80)
        print("🔬 Deep Research 专项测试".center(80))
        print(f"服务端点: {self.endpoint}")
        print(f"保存目录: {self.output_dir.absolute()}")
        print("="*80 + "\n")
        
        results = []
        saved_files = []
        
        for i, test_case in enumerate(self.test_cases, 1):
            print(f"\n\033[1m测试进度: [{i}/{len(self.test_cases)}]\033[0m")
            result = self.run_single_test(test_case)
            results.append(result)
            
            if result["response"] or result["error"]:
                saved_path = self.save_record(result)
                saved_files.append(saved_path)
            
            time.sleep(1)  # 避免请求过快
        
        # 打印总结报告
        self._print_summary(results, saved_files)
    
    def _print_summary(self, results: list, saved_files: list):
        """打印测试总结"""
        print("\n" + "="*80)
        print("📊 测试总结报告".center(80))
        print("="*80)
        
        success_count = sum(1 for r in results if r["error"] is None)
        total = len(results)
        
        print(f"\n总测试数: {total}")
        print(f"成功: {success_count} | 失败: {total - success_count}")
        
        print(f"\n📁 已保存文件:")
        for f in saved_files:
            print(f"   - {f}")
        
        print(f"\n💡 查看建议:")
        print(f"   1. 打开 JSON 文件查看完整的 request/response 结构")
        print(f"   2. 检查 'response' 字段中的模型生成内容")
        print(f"   3. 关注 'analysis' 和 'results' 字段的核心输出")
        print("="*80)


def main():
    parser = argparse.ArgumentParser(description="Deep Research 功能测试")
    parser.add_argument("--url", default="http://localhost:8000", help="服务地址")
    parser.add_argument("--output", default="/Users/liucunyu/Documents/all_code/thu_2025/fine-tune/allcode_chemind_server/agent/test_result", help="输出目录")
    parser.add_argument("--query", type=str, help="自定义单次查询内容")
    parser.add_argument("--depth", type=int, default=2, help="研究深度")
    parser.add_argument("--breadth", type=int, default=2, help="研究广度")
    
    args = parser.parse_args()
    
    tester = DeepResearchTester(base_url=args.url, output_dir=args.output)
    
    # 如果提供了自定义查询，只运行单次测试
    if args.query:
        custom_test = {
            "name": "自定义查询",
            "payload": {
                "query": args.query,
                "depth": args.depth,
                "breadth": args.breadth
            }
        }
        print(f"运行自定义查询: {args.query}")
        result = tester.run_single_test(custom_test)
        tester.save_record(result)
    else:
        # 运行预设测试集
        tester.run_all_tests()


if __name__ == "__main__":
    main()