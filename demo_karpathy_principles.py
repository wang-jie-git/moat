#!/usr/bin/env python3
"""
Moat v0.8.0-alpha — Karpathy Principles Constitution 演示

展示如何使用新的规则系统。
"""

from pathlib import Path
from moat.rules import (
    PrinciplesLoader,
    PrincipleViolation,
    get_surgical_checker,
)
from moat.rules.simplicity_checker import SimplicityChecker


def demo_principles_loader():
    """演示原则加载器"""
    print("=" * 60)
    print("1. PrinciplesLoader — 加载原则定义")
    print("=" * 60)

    loader = PrinciplesLoader()
    principles = loader.load_principles()

    print(f"✅ 加载了 {len(principles)} 个原则:\n")

    for name, principle in principles.items():
        print(f"  📋 {name}")
        print(f"     描述: {principle.description}")
        print(f"     类型: {principle.check_type}")
        print(f"     执行: {principle.enforcement}")
        if principle.thresholds:
            print(f"     阈值: {principle.thresholds}")
        print()


def demo_surgical_changes():
    """演示手术刀检查器"""
    print("=" * 60)
    print("2. SurgicalChangesChecker — 手术刀式修改检查")
    print("=" * 60)

    print("模拟 Git diff 场景:\n")

    # 模拟违规场景
    checker = get_surgical_checker()(max_diff_lines=100, max_files_changed=3)

    violations = [
        PrincipleViolation(
            principle_name="surgical_changes",
            severity="warning",
            message="文件 'api/users.py' 修改过大（+150/-30 行）",
            file_path="api/users.py",
            context={
                "added_lines": 150,
                "removed_lines": 30,
                "total_changes": 180,
            }
        ),
        PrincipleViolation(
            principle_name="surgical_changes",
            severity="warning",
            message="修改文件过多（5 个）",
            context={
                "files_changed": 5,
                "files": ["api/users.py", "services/user_service.py", "repositories/user_repo.py",
                          "models/user.py", "tests/test_users.py"]
            }
        ),
    ]

    for i, v in enumerate(violations, 1):
        print(f"⚠️  违规 {i}: {v.message}")
        recommendation = checker.get_recommendation(v)
        print(f"   💡 建议: {recommendation}\n")


def demo_simplicity_checker():
    """演示简单性检查器"""
    print("=" * 60)
    print("3. SimplicityChecker — 代码复杂度检查")
    print("=" * 60)

    checker = SimplicityChecker()

    # 模拟超长函数
    long_function = """
def very_long_function():
    # 假设这里有 60 行代码...
    # 行 1
    # 行 2
    # 行 3
    # ...
    # 行 60
    pass
"""

    violations = checker.check_file("example.py", long_function)

    print("检查超长函数 (>50 行):\n")

    if violations:
        for v in violations:
            print(f"❌ 违规: {v.message}")
            print(f"   行号: {v.line_number}")
            print(f"   上下文: {v.context}\n")
    else:
        print("✅ 未检测到超长函数（示例中函数较短）\n")


def demo_complexity_metrics():
    """演示复杂度指标计算"""
    print("=" * 60)
    print("4. ComplexityMetrics — 代码复杂度指标")
    print("=" * 60)

    checker = SimplicityChecker()

    sample_code = """
def func1():
    pass

def func2():
    pass

class MyClass:
    def method1(self):
        pass

    def method2(self):
        pass
"""

    metrics = checker.calculate_metrics("example.py", sample_code)

    print(f"文件: {metrics.file_path}")
    print(f"总行数: {metrics.total_lines}")
    print(f"函数数量: {metrics.function_count}")
    print(f"类数量: {metrics.class_count}")
    print(f"最大函数长度: {metrics.max_function_lines}")
    print(f"最大类方法数: {metrics.max_class_methods}")
    print(f"继承深度: {metrics.max_inheritance_depth}")
    print(f"平均函数长度: {metrics.avg_function_length:.1f}")
    print(f"圈复杂度: {metrics.cyclomatic_complexity}")


def demo_custom_config():
    """演示自定义配置"""
    print("\n" + "=" * 60)
    print("5. 自定义配置 — 调整阈值")
    print("=" * 60)

    print("创建宽松版本检查器:\n")

    checker = SimplicityChecker(
        max_function_lines=100,  # 函数最多 100 行
        max_class_methods=30,    # 类最多 30 个方法
        max_file_lines=1000,     # 文件最多 1000 行
    )

    print(f"  函数长度阈值: {checker.max_function_lines} 行")
    print(f"  类方法阈值: {checker.max_class_methods} 个")
    print(f"  文件大小阈值: {checker.max_file_lines} 行")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Moat v0.8.0-alpha — Karpathy Principles 演示")
    print("=" * 60)
    print()

    try:
        demo_principles_loader()
        demo_surgical_changes()
        demo_simplicity_checker()
        demo_complexity_metrics()
        demo_custom_config()

        print("\n" + "=" * 60)
        print("✅ 所有演示完成！")
        print("=" * 60)
        print("\n📚 更多信息:")
        print("  - 文档: KARPATHY_PRINCIPLES.md")
        print("  - GitHub: https://github.com/wang-jie-git/moat")
        print()

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
