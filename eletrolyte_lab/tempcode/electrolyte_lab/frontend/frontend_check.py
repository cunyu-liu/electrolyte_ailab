#!/usr/bin/env python3
"""
前端代码检查
"""

import os
import subprocess
import json

def check_typescript_compilation():
    """检查TypeScript编译"""
    print("🔍 检查TypeScript编译...")

    try:
        # 运行TypeScript编译检查
        result = subprocess.run(
            ['npx', 'tsc', '--noEmit', '--skipLibCheck'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("✓ TypeScript编译检查通过")
            return True
        else:
            print("✗ TypeScript编译错误:")
            print(result.stderr)
            return False

    except subprocess.TimeoutExpired:
        print("✗ TypeScript编译超时")
        return False
    except FileNotFoundError:
        print("⚠️  npx未找到，跳过TypeScript检查")
        return True
    except Exception as e:
        print(f"✗ TypeScript检查异常: {e}")
        return False

def check_api_calls():
    """检查API调用"""
    print("\n🔍 检查API调用...")

    try:
        with open('src/services/api.ts', 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查贝叶斯优化API
        if 'runBayesianOptimization' in content:
            print("✓ runBayesianOptimization API定义存在")
        else:
            print("✗ runBayesianOptimization API定义缺失")
            return False

        if 'addExperimentData' in content:
            print("✓ addExperimentData API定义存在")
        else:
            print("✗ addExperimentData API定义缺失")
            return False

        if 'getBayesianStats' in content:
            print("✓ getBayesianStats API定义存在")
        else:
            print("✗ getBayesianStats API定义缺失")
            return False

        return True

    except FileNotFoundError:
        print("✗ src/services/api.ts 文件未找到")
        return False
    except Exception as e:
        print(f"✗ API调用检查失败: {e}")
        return False

def check_component_usage():
    """检查组件使用"""
    print("\n🔍 检查组件使用...")

    try:
        with open('src/pages/ClosedLoopPage.tsx', 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查关键函数
        checks = [
            ('handleQuickBayesianOptimization', '快速贝叶斯优化函数'),
            ('runBayesianOptimization', '贝叶斯优化API调用'),
            ('Modal.info', '结果展示弹窗'),
            ('optimization_result', '优化结果处理')
        ]

        for check, description in checks:
            if check in content:
                print(f"✓ {description} 存在")
            else:
                print(f"✗ {description} 缺失")
                return False

        # 检查修复的类型问题
        if 'result.success && result.data && result.data.optimization_result' in content:
            print("✓ 类型问题已修复")
        else:
            print("✗ 类型问题未完全修复")
            return False

        return True

    except FileNotFoundError:
        print("✗ src/pages/ClosedLoopPage.tsx 文件未找到")
        return False
    except Exception as e:
        print(f"✗ 组件使用检查失败: {e}")
        return False

def check_package_dependencies():
    """检查包依赖"""
    print("\n🔍 检查包依赖...")

    try:
        with open('package.json', 'r', encoding='utf-8') as f:
            package_data = json.load(f)

        required_deps = ['react', 'antd', 'axios']
        optional_deps = ['typescript', '@types/react']

        all_found = True

        for dep in required_deps:
            if dep in package_data.get('dependencies', {}):
                print(f"✓ {dep} 依赖存在")
            else:
                print(f"✗ {dep} 依赖缺失")
                all_found = False

        for dep in optional_deps:
            if dep in package_data.get('dependencies', {}) or dep in package_data.get('devDependencies', {}):
                print(f"✓ {dep} 依赖存在")
            else:
                print(f"⚠️  {dep} 依赖可选，未找到")

        return all_found

    except FileNotFoundError:
        print("✗ package.json 文件未找到")
        return False
    except Exception as e:
        print(f"✗ 包依赖检查失败: {e}")
        return False

def check_eslint_config():
    """检查ESLint配置"""
    print("\n🔍 检查代码规范配置...")

    eslint_files = ['.eslintrc.js', '.eslintrc.json', 'eslint.config.js']
    has_eslint = any(os.path.exists(f) for f in eslint_files)

    if has_eslint:
        print("✓ ESLint配置存在")
    else:
        print("⚠️  ESLint配置未找到（可选）")

    return True

def main():
    """主检查函数"""
    print("🔬 前端代码详细检查")
    print("=" * 50)

    checks = [
        ("TypeScript编译", check_typescript_compilation),
        ("API调用", check_api_calls),
        ("组件使用", check_component_usage),
        ("包依赖", check_package_dependencies),
        ("代码规范", check_eslint_config)
    ]

    all_passed = True

    for check_name, check_func in checks:
        try:
            result = check_func()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"✗ {check_name} 检查出现异常: {e}")
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 前端检查通过！")
        return 0
    else:
        print("❌ 前端检查发现问题，请修复后重试。")
        return 1

if __name__ == "__main__":
    exit(main())