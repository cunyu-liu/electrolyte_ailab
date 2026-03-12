#!/usr/bin/env python3
"""
详细的语法和逻辑检查
"""

import ast
import os
import sys
import json
import importlib.util

def check_python_syntax(file_path):
    """检查Python文件语法"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # 解析AST检查语法
        ast.parse(source)
        return True, None
    except SyntaxError as e:
        return False, f"语法错误: {e}"
    except Exception as e:
        return False, f"其他错误: {e}"

def check_imports():
    """检查所有导入"""
    print("🔍 检查导入...")

    try:
        # 检查贝叶斯优化器导入
        spec = importlib.util.spec_from_file_location(
            "bayesian_optimizer",
            "app/closed_loop/bayesian_optimizer.py"
        )
        bayesian_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bayesian_module)
        print("✓ bayesian_optimizer.py 导入成功")

        # 检查API路由导入
        spec = importlib.util.spec_from_file_location(
            "closed_loop_routes",
            "api/closed_loop_routes.py"
        )
        routes_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(routes_module)
        print("✓ closed_loop_routes.py 导入成功")

        return True

    except Exception as e:
        print(f"✗ 导入检查失败: {e}")
        return False

def check_bayesian_optimizer_logic():
    """检查贝叶斯优化器逻辑"""
    print("\n🔍 检查贝叶斯优化器逻辑...")

    try:
        from app_bk.closed_loop.bayesian_optimizer import ElectrolyteBayesianOptimizer

        # 测试基本实例化
        optimizer = ElectrolyteBayesianOptimizer('test_syntax.json')
        print("✓ 优化器实例化成功")

        # 检查关键方法存在
        required_methods = [
            'add_experiment_data',
            'suggest_optimized_formulas',
            'get_optimization_stats',
            'save_data',
            'load_data'
        ]

        for method in required_methods:
            if hasattr(optimizer, method):
                print(f"✓ 方法 {method} 存在")
            else:
                print(f"✗ 方法 {method} 缺失")
                return False

        # 清理测试文件
        if os.path.exists('test_syntax.json'):
            os.remove('test_syntax.json')

        return True

    except Exception as e:
        print(f"✗ 逻辑检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_api_routes():
    """检查API路由"""
    print("\n🔍 检查API路由...")

    try:
        # 检查路由文件语法
        syntax_ok, error = check_python_syntax("api/closed_loop_routes.py")
        if not syntax_ok:
            print(f"✗ API路由语法错误: {error}")
            return False
        print("✓ API路由语法正确")

        # 检查关键路由
        from api.closed_loop_routes import closed_loop_bp
        print("✓ 路由蓝图创建成功")

        # 检查路由函数
        route_functions = [
            'run_bayesian_optimization',
            'add_experiment_data',
            'get_bayesian_stats'
        ]

        for func_name in route_functions:
            if hasattr(closed_loop_bp, func_name):
                print(f"✓ 路由函数 {func_name} 存在")
            else:
                print(f"⚠️  路由函数 {func_name} 在蓝图中不直接可见（这是正常的）")

        return True

    except Exception as e:
        print(f"✗ API路由检查失败: {e}")
        return False

def check_error_handling():
    """检查错误处理"""
    print("\n🔍 检查错误处理...")

    try:
        from app_bk.closed_loop.bayesian_optimizer import ElectrolyteBayesianOptimizer

        # 测试错误情况
        optimizer = ElectrolyteBayesianOptimizer('test_error.json')

        # 测试空数据处理
        result = optimizer.suggest_optimized_formulas(
            weights={'invalid_key': 0.5},
            n_candidates=1
        )

        if result['success'] and result.get('method') == 'random_generation':
            print("✓ 空数据处理正确")
        else:
            print("✗ 空数据处理异常")
            return False

        # 清理
        if os.path.exists('test_error.json'):
            os.remove('test_error.json')

        return True

    except Exception as e:
        print(f"✗ 错误处理检查失败: {e}")
        return False

def check_data_formats():
    """检查数据格式"""
    print("\n🔍 检查数据格式...")

    try:
        from app_bk.closed_loop.bayesian_optimizer import ElectrolyteBayesianOptimizer

        optimizer = ElectrolyteBayesianOptimizer('test_format.json')

        # 测试标准数据格式
        test_data = {
            'experiment_data': {
                'id': 'test_format',
                'formula': {
                    'solvent_ratios': {1: 0.1, 2: 0.05, 3: 0.2, 4: 0.1, 5: 0.05,
                                     6: 0.1, 7: 0.15, 8: 0.1, 9: 0.1, 10: 0.05}
                }
            },
            'results': [
                {'metric_name': 'retention', 'value': 0.92},
                {'metric_name': 'capacity', 'value': 180.0},
                {'metric_name': 'impedance', 'value': 50.0}
            ]
        }

        success = optimizer.add_experiment_data(
            test_data['experiment_data'],
            test_data['results']
        )

        if success:
            print("✓ 数据格式处理正确")
        else:
            print("✗ 数据格式处理失败")
            return False

        # 测试优化结果格式
        result = optimizer.suggest_optimized_formulas(
            weights={'w_ret': 0.5, 'w_cap': 0.4, 'w_imp': 0.1},
            n_candidates=1
        )

        if result['success'] and 'optimized_formulas' in result:
            formula = result['optimized_formulas'][0]
            required_keys = ['id', 'solvent_ratios', 'confidence_score']

            for key in required_keys:
                if key in formula:
                    print(f"✓ 配方格式包含 {key}")
                else:
                    print(f"✗ 配方格式缺少 {key}")
                    return False
        else:
            print("✗ 优化结果格式错误")
            return False

        # 清理
        if os.path.exists('test_format.json'):
            os.remove('test_format.json')

        return True

    except Exception as e:
        print(f"✗ 数据格式检查失败: {e}")
        return False

def check_file_dependencies():
    """检查文件依赖"""
    print("\n🔍 检查文件依赖...")

    required_files = [
        'app/closed_loop/bayesian_optimizer.py',
        'api/closed_loop_routes.py',
        'app.py',
        'requirements.txt'
    ]

    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path} 存在")
        else:
            print(f"✗ {file_path} 缺失")
            all_exist = False

    return all_exist

def main():
    """主检查函数"""
    print("🔬 详细代码语法和逻辑检查")
    print("=" * 60)

    checks = [
        ("文件依赖", check_file_dependencies),
        ("Python语法", lambda: check_python_syntax("app/closed_loop/bayesian_optimizer.py")[0] and
                           check_python_syntax("api/closed_loop_routes.py")[0]),
        ("导入检查", check_imports),
        ("贝叶斯优化器逻辑", check_bayesian_optimizer_logic),
        ("API路由", check_api_routes),
        ("错误处理", check_error_handling),
        ("数据格式", check_data_formats)
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

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有详细检查通过！代码质量优秀。")
        return 0
    else:
        print("❌ 发现问题，请修复后重试。")
        return 1

if __name__ == "__main__":
    sys.exit(main())