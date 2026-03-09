"""快速测试 /mine-data 接口的基本功能"""
import requests
import json
import sys

# 简单测试数据 - 只包含基本参数,不包含文献结果
# 这样会跳过文本挖掘和分子生成,只测试基本接口功能
test_data = {
    "parameters": [
        {
            "category": "体系类型",
            "param_name": "system_type",
            "param_value": "锂离子电池",
            "unit": ""
        }
    ],
    "literature_results": []  # 空列表,会跳过文本挖掘
}

print("测试 /mine-data 接口 - 基本功能")
print("=" * 60)
print(f"请求数据: {json.dumps(test_data, ensure_ascii=False)}")
print("-" * 60)

try:
    print("\n发送请求...")
    # 使用30秒超时
    response = requests.post(
        'http://localhost:5009/api/ai-designer/mine-data',
        json=test_data,
        timeout=30
    )

    print(f"✅ 响应状态码: {response.status_code}")
    print(f"响应时间: {response.elapsed.total_seconds():.2f}秒")

    if response.status_code == 200:
        result = response.json()
        print(f"\n响应数据:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        print("\n" + "=" * 60)
        print("测试结果:")
        if result.get('success'):
            print("✅ 接口调用成功")
            print(f"   消息: {result.get('message', 'N/A')}")

            if 'formula_dataset' in result:
                metadata = result['formula_dataset'].get('metadata', {})
                print(f"\n统计信息:")
                print(f"   - 总文献数: {metadata.get('total_literature', 0)}")
                print(f"   - 总分子数: {metadata.get('total_molecules', 0)}")
                print(f"   - 文献匹配成功: {metadata.get('literature_match_success', False)}")
                print(f"   - 文本挖掘成功: {metadata.get('text_mining_success', False)}")
                print(f"   - 分子生成成功: {metadata.get('molecule_generation_success', False)}")
        else:
            print("❌ 接口返回错误")
            print(f"   错误: {result.get('error', 'Unknown')}")
        print("=" * 60)

    else:
        print(f"❌ HTTP错误: {response.status_code}")
        print(f"   内容: {response.text[:200]}")

    sys.exit(0)

except requests.exceptions.Timeout:
    print(f"\n❌ 请求超时(30秒)")
    print("   接口可能在处理复杂算法或卡住了")
    sys.exit(1)

except requests.exceptions.ConnectionError as e:
    print(f"\n❌ 连接失败")
    print(f"   请确保后端服务正在运行在 http://localhost:5009")
    print(f"   错误: {str(e)}")
    sys.exit(2)

except Exception as e:
    print(f"\n❌ 测试失败")
    print(f"   错误类型: {type(e).__name__}")
    print(f"   错误信息: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(3)
