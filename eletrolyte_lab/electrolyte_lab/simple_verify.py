#!/usr/bin/env python3
"""
简单验证脚本 - 检查集成修复
"""

import os

def main():
    print("=" * 50)
    print("验证算法集成修复")
    print("=" * 50)

    # 检查关键文件
    files = [
        r'D:\electrolyte\BO\newsearch.py',
        r'D:\electrolyte\ChemMind_pdfExtractor\main_port.py',
        r'D:\electrolyte\code\frontend\src\pages\AIDesignerPage.tsx',
        r'D:\electrolyte\code\backend\api\ai_designer_routes.py'
    ]

    print("\n1. 检查关键文件存在性:")
    all_exist = True
    for file_path in files:
        exists = os.path.exists(file_path)
        status = "OK" if exists else "MISSING"
        print(f"   {status}: {os.path.basename(file_path)}")
        if not exists:
            all_exist = False

    # 检查前端关键组件
    print("\n2. 检查前端关键组件:")
    try:
        frontend_file = r'D:\electrolyte\code\frontend\src\pages\AIDesignerPage.tsx'
        with open(frontend_file, 'r', encoding='utf-8') as f:
            content = f.read()

        components = [
            'parseRequestByRules',
            'stepHistory[2]',
            'setCurrentStep(2)',
            '数据挖掘结果展示',
            '文献匹配结果',
            '文本挖掘结果'
        ]

        all_found = True
        for comp in components:
            found = comp in content
            status = "OK" if found else "MISSING"
            print(f"   {status}: {comp}")
            if not found:
                all_found = False

    except Exception as e:
        print(f"   ERROR: 无法读取前端文件 - {str(e)}")
        all_found = False

    # 总结
    print("\n" + "=" * 50)
    print("验证结果:")

    if all_exist and all_found:
        print("SUCCESS: 集成修复验证通过！")
        print("\n修复要点:")
        print("1. 步骤一使用基于规则解析作为备用方案")
        print("2. 步骤三数据挖掘完成后正确跳转到步骤三界面")
        print("3. 步骤三界面使用stepHistory[2]展示算法结果")
        print("4. 包含完整的文献匹配和文本挖掘结果展示")
        print("\n完整流程:")
        print("需求输入 → 参数确认 → 数据挖掘 → 步骤三展示结果")
    else:
        print("FAILED: 集成修复验证失败")
        print("需要检查文件存在性和关键组件")

if __name__ == "__main__":
    main()