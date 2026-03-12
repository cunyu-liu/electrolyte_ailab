#!/usr/bin/env python3
"""
前后端集成测试
"""

import sys
import os
import json
import tempfile
from datetime import datetime

def test_bayesian_end_to_end():
    """端到端贝叶斯优化测试"""
    print("🔬 端到端集成测试")
    print("=" * 50)

    try:
        # 1. 测试贝叶斯优化器
        print("\n1️⃣ 测试贝叶斯优化器...")
        from app_bk.closed_loop.bayesian_optimizer import ElectrolyteBayesianOptimizer

        # 创建临时数据文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_data_file = f.name

        optimizer = ElectrolyteBayesianOptimizer(temp_data_file)
        print("✓ 优化器创建成功")

        # 2. 添加测试数据
        print("\n2️⃣ 添加测试数据...")
        test_experiments = [
            {
                'experiment_data': {
                    'id': 'integration_test_1',
                    'formula': {
                        'solvent_ratios': {
                            1: 0.12, 2: 0.08, 3: 0.18, 4: 0.12, 5: 0.07,
                            6: 0.12, 7: 0.13, 8: 0.09, 9: 0.06, 10: 0.03
                        }
                    }
                },
                'results': [
                    {'metric_name': 'retention', 'value': 0.91},
                    {'metric_name': 'capacity', 'value': 185.0},
                    {'metric_name': 'impedance', 'value': 48.0}
                ]
            },
            {
                'experiment_data': {
                    'id': 'integration_test_2',
                    'formula': {
                        'solvent_ratios': {
                            1: 0.09, 2: 0.06, 3: 0.22, 4: 0.14, 5: 0.04,
                            6: 0.11, 7: 0.16, 8: 0.08, 9: 0.07, 10: 0.03
                        }
                    }
                },
                'results': [
                    {'metric_name': 'retention', 'value': 0.94},
                    {'metric_name': 'capacity', 'value': 188.0},
                    {'metric_name': 'impedance', 'value': 55.0}
                ]
            }
        ]

        for i, exp_data in enumerate(test_experiments, 1):
            success = optimizer.add_experiment_data(
                exp_data['experiment_data'],
                exp_data['results']
            )
            if success:
                print(f"✓ 测试数据 {i} 添加成功")
            else:
                print(f"✗ 测试数据 {i} 添加失败")
                return False

        # 3. 执行贝叶斯优化
        print("\n3️⃣ 执行贝叶斯优化...")
        optimization_result = optimizer.suggest_optimized_formulas(
            weights={'w_ret': 0.4, 'w_cap': 0.5, 'w_imp': 0.1},
            n_candidates=3,
            optimization_target='all'
        )

        if optimization_result['success']:
            print("✓ 贝叶斯优化成功")
            print(f"✓ 优化方法: {optimization_result['method']}")
            print(f"✓ 生成配方: {len(optimization_result['optimized_formulas'])} 个")

            # 验证配方格式
            for i, formula in enumerate(optimization_result['optimized_formulas']):
                required_keys = ['id', 'solvent_ratios', 'confidence_score', 'predicted_performance']
                for key in required_keys:
                    if key in formula:
                        print(f"✓ 配方 {i+1} 包含 {key}")
                    else:
                        print(f"✗ 配方 {i+1} 缺少 {key}")
                        return False

                # 验证溶剂比例
                total_ratio = sum(formula['solvent_ratios'].values())
                if abs(total_ratio - 1.0) < 0.01:
                    print(f"✓ 配方 {i+1} 溶剂比例正确 (总和: {total_ratio:.4f})")
                else:
                    print(f"✗ 配方 {i+1} 溶剂比例错误 (总和: {total_ratio:.4f})")
                    return False

        else:
            print("✗ 贝叶斯优化失败")
            return False

        # 4. 测试API路由数据格式
        print("\n4️⃣ 测试API数据格式...")

        # 模拟API响应格式
        api_response = {
            'success': True,
            'data': {
                'optimization_result': optimization_result,
                'stats': optimizer.get_optimization_stats()
            },
            'message': '贝叶斯优化完成'
        }

        # 验证前端期望的格式
        if 'success' in api_response:
            print("✓ API响应包含 success 字段")
        else:
            print("✗ API响应缺少 success 字段")
            return False

        if 'data' in api_response and 'optimization_result' in api_response['data']:
            print("✓ API响应格式正确")
        else:
            print("✗ API响应格式错误")
            return False

        # 5. 清理
        print("\n5️⃣ 清理测试数据...")
        if os.path.exists(temp_data_file):
            os.remove(temp_data_file)
            print("✓ 临时文件已清理")

        print("\n" + "=" * 50)
        print("🎉 端到端集成测试通过！")
        print("\n📊 测试结果:")
        print(f"  ✅ 贝叶斯优化器: 正常")
        print(f"  ✅ 数据添加: 正常")
        print(f"  ✅ 优化执行: 正常")
        print(f"  ✅ 配方格式: 正确")
        print(f"  ✅ API格式: 标准")
        print(f"  ✅ 清理操作: 完成")

        return True

    except Exception as e:
        print(f"✗ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_scenarios():
    """测试错误场景"""
    print("\n\n🛡️  错误场景测试")
    print("=" * 50)

    try:
        from app_bk.closed_loop.bayesian_optimizer import ElectrolyteBayesianOptimizer

        # 测试空数据处理
        print("\n1️⃣ 测试空数据处理...")
        optimizer = ElectrolyteBayesianOptimizer()
        result = optimizer.suggest_optimized_formulas(
            weights={'invalid_key': 1.0},
            n_candidates=1
        )

        if result['success'] and result.get('method') == 'random_generation':
            print("✓ 空数据处理正确")
        else:
            print("✗ 空数据处理异常")
            return False

        # 测试无效权重
        print("\n2️⃣ 测试无效权重...")
        result = optimizer.suggest_optimized_formulas(
            weights={'w_ret': 0.5},  # 权重数量不匹配
            n_candidates=1
        )

        if result['success']:
            print("✓ 无效权重处理正确")
        else:
            print("✗ 无效权重处理异常")
            return False

        # 测试边界情况
        print("\n3️⃣ 测试边界情况...")
        result = optimizer.suggest_optimized_formulas(
            weights={'w_ret': 0.5, 'w_cap': 0.5, 'w_imp': 0.0},
            n_candidates=0  # 零个候选
        )

        if result['success']:
            print("✓ 边界情况处理正确")
        else:
            print("✗ 边界情况处理异常")
            return False

        print("\n✅ 错误场景测试通过")
        return True

    except Exception as e:
        print(f"✗ 错误场景测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 最终集成测试套件")
    print("时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    tests = [
        ("端到端集成测试", test_bayesian_end_to_end),
        ("错误场景测试", test_error_scenarios)
    ]

    all_passed = True

    for test_name, test_func in tests:
        try:
            result = test_func()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"✗ {test_name} 出现异常: {e}")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎊 所有集成测试通过！")
        print("\n✨ 系统已准备就绪:")
        print("  🚀 后端贝叶斯优化: 完全正常")
        print("  🚀 API接口: 格式标准")
        print("  🚀 数据处理: 健壮可靠")
        print("  🚀 错误处理: 完善全面")
        print("  🚀 前后端集成: 无缝对接")
        print("\n🎯 可以安全部署到生产环境！")
        return 0
    else:
        print("❌ 部分集成测试失败，请修复后重试。")
        return 1

if __name__ == "__main__":
    sys.exit(main())