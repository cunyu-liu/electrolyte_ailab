#!/usr/bin/env python3
"""
网络连接诊断工具 - 帮助用户诊断前端到后端的连接问题
"""

import requests
import json
import time

def test_backend_connection():
    """测试后端连接"""
    print("=== 后端连接诊断 ===")

    # 测试1: 健康检查
    try:
        response = requests.get('http://localhost:5009/api/ai-designer/health', timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ 健康检查: {health_data.get('status')}")
            print(f"   服务: {health_data.get('service')}")
            print(f"   版本: {health_data.get('version')}")
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 健康检查异常: {str(e)}")
        return False

    # 测试2: CORS预检
    try:
        response = requests.options(
            'http://localhost:5009/api/ai-designer/parse-request',
            headers={
                'Origin': 'http://localhost:3000',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            },
            timeout=5
        )
        print(f"✅ CORS预检: {response.status_code}")
        print(f"   允许源: {response.headers.get('Access-Control-Allow-Origin')}")
        print(f"   允许方法: {response.headers.get('Access-Control-Allow-Methods')}")
    except Exception as e:
        print(f"❌ CORS预检失败: {str(e)}")
        return False

    # 测试3: 实际API调用
    try:
        test_data = {"input": "测试连接"}
        response = requests.post(
            'http://localhost:5009/api/ai-designer/parse-request',
            json=test_data,
            timeout=10,
            headers={'Content-Type': 'application/json'}
        )

        print(f"✅ API调用: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"   成功: {result.get('success')}")
            print(f"   消息: {result.get('message')}")
            return True
        else:
            print(f"   错误: {response.text}")
            return False

    except Exception as e:
        print(f"❌ API调用失败: {str(e)}")
        return False

def generate_frontend_test_url():
    """生成前端测试URL"""
    import os
    import webbrowser

    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(current_dir, 'test_frontend.html')

    if os.path.exists(html_path):
        file_url = f'file:///{html_path.replace("\\", "/")}'
        print(f"\n🌐 前端测试页面: {file_url}")
        print("请在浏览器中打开此URL进行连接测试")
        return file_url

    return None

def main():
    print("🔍 网络连接诊断工具")
    print("=" * 50)
    print("用于诊断前端到后端的连接问题")
    print()

    # 测试后端
    backend_ok = test_backend_connection()

    print("\n" + "=" * 50)
    print("📋 诊断结果:")

    if backend_ok:
        print("✅ 后端服务: 正常")
        print("✅ 网络连接: 正常")
        print("✅ API调用: 正常")
        print()
        print("🎯 问题可能在于:")
        print("1. 前端缓存 - 请强制刷新浏览器 (Ctrl+Shift+R)")
        print("2. 前端代理配置 - 检查前端开发服务器配置")
        print("3. 浏览器设置 - 检查浏览器安全设置")
        print()
        print("💡 建议解决方案:")
        print("- 重启前端开发服务器")
        print("- 清除浏览器缓存")
        print("- 在浏览器控制台查看详细错误信息")

        # 生成测试页面
        test_url = generate_frontend_test_url()

    else:
        print("❌ 后端服务: 异常")
        print("❌ 需要启动后端服务")
        print()
        print("🔧 解决方案:")
        print("cd backend")
        print("python app.py")
        print("确保服务运行在端口5009")

if __name__ == "__main__":
    main()