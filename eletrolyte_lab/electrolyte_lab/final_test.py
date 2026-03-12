#!/usr/bin/env python3
"""
完整测试DeepSeek API集成解决方案
"""
import requests
import time
import json

def test_full_solution():
    """测试完整的解决方案"""

    base_url = "http://localhost:5009/api/ai-designer/parse-request"

    test_cases = [
        {
            "name": "基础动力电池需求",
            "input": "我需要正极材料用于动力电池，能量密度280Wh/kg",
            "expected_method": "deepseek_api"
        },
        {
            "name": "高能量密度需求",
            "input": "开发高镍三元正极材料，能量密度320Wh/kg，用于电动汽车",
            "expected_method": "deepseek_api"
        },
        {
            "name": "复合需求",
            "input": "需要负极材料用于3C电子产品，功率密度1000W/kg，循环寿命1500次，工作温度-20°C",
            "expected_method": "deepseek_api"
        }
    ]

    print("=" * 60)
    print("🔋 电池需求解析完整测试")
    print("=" * 60)

    all_passed = True

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 测试 {i}: {test_case['name']}")
        print(f"输入: {test_case['input']}")

        start_time = time.time()

        try:
            # 模拟前端调用（30秒超时）
            response = requests.post(
                base_url,
                json={"input": test_case['input']},
                timeout=30,
                headers={"Content-Type": "application/json"}
            )

            response_time = time.time() - start_time

            if response.status_code == 200:
                result = response.json()

                if result.get('success'):
                    data = result.get('data', {})
                    method = data.get('metadata', {}).get('parsing_method', 'unknown')

                    print(f"✅ 状态: 成功")
                    print(f"⏱️  响应时间: {response_time:.2f}秒")
                    print(f"🧠 解析方法: {method}")

                    # 验证是否使用了DeepSeek API
                    if method == test_case['expected_method']:
                        print(f"✅ API调用: 正确使用DeepSeek")
                    else:
                        print(f"⚠️  API调用: 预期{test_case['expected_method']}，实际{method}")
                        all_passed = False

                    # 显示解析结果
                    basic_info = data.get('basic_info', {})
                    performance = data.get('performance_params', {})

                    print(f"📊 解析结果:")
                    print(f"   体系类型: {basic_info.get('system_type', {}).get('value', 'N/A')}")
                    print(f"   应用场景: {basic_info.get('application_scenario', {}).get('value', 'N/A')}")
                    print(f"   能量密度: {performance.get('energy_density', {}).get('value', 'N/A')} Wh/kg")
                    print(f"   功率密度: {performance.get('power_density', {}).get('value', 'N/A')} W/kg")

                else:
                    print(f"❌ 状态: 失败 - {result.get('error', '未知错误')}")
                    all_passed = False

            else:
                print(f"❌ HTTP错误: {response.status_code}")
                print(f"响应: {response.text}")
                all_passed = False

        except requests.exceptions.Timeout:
            print(f"❌ 超时: 请求超过30秒")
            all_passed = False

        except Exception as e:
            print(f"❌ 异常: {str(e)}")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！DeepSeek API集成成功！")
        print("💡 用户现在可以正常使用DeepSeek进行需求解析")
    else:
        print("⚠️  部分测试失败，需要进一步调试")
    print("=" * 60)

    return all_passed

if __name__ == "__main__":
    success = test_full_solution()
    exit(0 if success else 1)