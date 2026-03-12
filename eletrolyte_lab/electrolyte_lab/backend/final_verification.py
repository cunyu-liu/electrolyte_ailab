#!/usr/bin/env python3
"""
最终验证测试 - 确保网络连接问题已解决
"""

import requests
import json
import time

def final_test():
    """最终验证测试"""
    print("=== 最终验证测试 ===")

    # 测试1: 后端健康检查
    try:
        response = requests.get('http://localhost:5009/api/ai-designer/health', timeout=5)
        health_ok = response.status_code == 200
        print(f"1. 后端健康检查: {'✅' if health_ok else '❌'}")
    except:
        health_ok = False
        print("1. 后端健康检查: ❌")

    # 测试2: API功能测试
    try:
        test_data = {"input": "我需要开发一个正极材料，用于动力电池，能量密度280Wh/kg"}
        response = requests.post('http://localhost:5009/api/ai-designer/parse-request', json=test_data, timeout=10)
        api_ok = response.status_code == 200

        if api_ok:
            result = response.json()
            success = result.get('success', False)
            print(f"2. API功能测试: {'✅' if success else '❌'}")

            if success:
                data = result.get('data', {})
                system_type = data.get('basic_info', {}).get('system_type', {}).get('value')
                energy_density = data.get('performance_params', {}).get('energy_density', {}).get('value')
                print(f"   - 体系类型: {system_type}")
                print(f"   - 能量密度: {energy_density}")
        else:
            print(f"2. API功能测试: ❌ ({response.status_code})")

    except:
        api_ok = False
        print("2. API功能测试: ❌")

    # 测试3: 响应时间测试
    try:
        start_time = time.time()
        test_data = {"input": "简单测试"}
        response = requests.post('http://localhost:5009/api/ai-designer/parse-request', json=test_data, timeout=15)
        end_time = time.time()

        response_time = end_time - start_time
        time_ok = response_time < 10  # 10秒内响应
        print(f"3. 响应时间: {'✅' if time_ok else '❌'} ({response_time:.2f}秒)")

    except:
        time_ok = False
        print("3. 响应时间: ❌")

    # 总结
    print("\n" + "=" * 50)
    print("验证结果:")

    if health_ok and api_ok and time_ok:
        print("🎉 所有测试通过！")
        print("✅ 后端服务正常运行")
        print("✅ API功能正常")
        print("✅ 响应时间正常")
        print()
        print("用户现在可以:")
        print("- 正常使用需求解析功能")
        print("- 不再看到网络连接错误")
        print("- 顺利进入后续步骤")
        print()
        print("建议用户:")
        print("1. 强制刷新浏览器 (Ctrl+Shift+R)")
        print("2. 清除浏览器缓存")
        print("3. 重启前端开发服务器")

        return True

    else:
        print("❌ 部分测试失败")
        if not health_ok:
            print("- 后端服务未运行，请启动: python app.py")
        if not api_ok:
            print("- API功能异常，请检查日志")
        if not time_ok:
            print("- 响应时间过长，请检查网络")

        return False

if __name__ == "__main__":
    success = final_test()
    exit(0 if success else 1)