#!/usr/bin/env python3
"""
贝叶斯优化电解液配方系统启动脚本
"""

import os
import sys
import subprocess

def check_dependencies():
    """检查并安装依赖"""
    print("检查依赖...")
    try:
        import torch
        import botorch
        import flask
        print("✓ 依赖已安装")
        return True
    except ImportError as e:
        print(f"✗ 缺少依赖: {e}")
        print("正在安装依赖...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("✓ 依赖安装完成")
            return True
        except subprocess.CalledProcessError:
            print("✗ 依赖安装失败，请手动安装: pip install -r requirements.txt")
            return False

def ensure_data_directory():
    """确保数据目录存在"""
    os.makedirs("data", exist_ok=True)
    print("✓ 数据目录已准备")

def main():
    """主函数"""
    print("=" * 50)
    print("贝叶斯优化电解液配方系统")
    print("=" * 50)

    # 检查依赖
    if not check_dependencies():
        sys.exit(1)

    # 确保数据目录
    ensure_data_directory()

    # 启动应用
    try:
        print("\n启动Web应用...")
        print("访问地址: http://localhost:5000")
        print("按 Ctrl+C 停止服务")
        print("-" * 50)

        # 导入并运行Flask应用
        from bayes_opt_app import app
        app.run(host='0.0.0.0', port=5000, debug=True)

    except KeyboardInterrupt:
        print("\n服务已停止")
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()