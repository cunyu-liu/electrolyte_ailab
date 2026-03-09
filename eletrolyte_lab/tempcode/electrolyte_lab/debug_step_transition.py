#!/usr/bin/env python3
"""
调试步骤跳转问题
"""

import os

def main():
    print("🔍 步骤跳转问题诊断")
    print("=" * 50)

    print("\n📋 可能的问题检查清单:")

    print("\n1. 基于规则解析返回数据结构检查:")
    print("   ✅ success 必须为 true")
    print("   ✅ data 必须包含 basic_info.system_type.label")
    print("   ✅ 解析函数必须正确返回格式化的数据")

    print("\n2. 前端状态管理检查:")
    print("   ✅ setCurrentStep(1) 是否被正确调用")
    print("   ✅ parsedParameters 是否被正确设置")
    print("   ✅ loading 状态是否正确重置")

    print("\n3. 界面渲染条件检查:")
    print("   ✅ currentStep === 1 条件")
    print("   ✅ parsedParameters 存在性检查")
    print("   ✅ 步骤二内容渲染逻辑")

    print("\n4. 常见问题排查:")
    print("   ❌ 解析函数返回数据格式不正确")
    print("   ❌ useAPI 变量作用域问题 (已修复)")
    print("   ❌ 异常阻止了状态更新")
    print("   ❌ React状态更新时机问题")

    print("\n🔧 修复建议:")
    print("1. 检查浏览器控制台日志")
    print("2. 确认 parseRequestByRules 返回正确格式")
    print("3. 验证 setCurrentStep(1) 被调用")
    print("4. 检查是否有JavaScript错误阻止执行")

    print("\n📱 调试步骤:")
    print("1. 在浏览器开发者工具中查看控制台")
    print("2. 查看网络请求和响应")
    print("3. 检查 React DevTools 中的状态变化")
    print("4. 查看是否有 JavaScript 错误")

    # 检查关键文件是否存在
    print("\n📁 文件状态检查:")
    files = [
        ('frontend/src/pages/AIDesignerPage.tsx', '前端主界面文件')
    ]

    for file_path, description in files:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        exists = os.path.exists(full_path)
        status = "✅" if exists else "❌"
        print(f"   {status} {description}")

if __name__ == "__main__":
    main()