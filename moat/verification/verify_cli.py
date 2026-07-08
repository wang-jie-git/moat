"""
CLI命令: moat verify — 架构验收
"""

import argparse
import sys
from pathlib import Path

from .orchestrator import VerifyOrchestrator
from .types import VerificationReport


def cmd_verify(args) -> int:
    """
    架构验收命令

    用法:
        moat verify                    # 执行完整验收
        moat verify --all              # 等价于上面
        moat verify --operator <name>  # 执行单个算子
        moat verify --json             # JSON输出
        moat verify --fail-on-score 60 # 评分阈值
    """
    from pathlib import Path

    # 初始化编排器
    orchestrator = VerifyOrchestrator()

    # 导入并注册所有算子
    try:
        from .operators import (
            DirectoryResponsibilityOperator,
            MinimalModuleDrillOperator,
            APIResponseSpecOperator,
            FrameworkUsageOperator,
            RuntimeEvidenceOperator,
            ArchitectureHealthScoreOperator,
            TruthDocumentGeneratorOperator,
        )

        orchestrator.register_operator(DirectoryResponsibilityOperator())
        orchestrator.register_operator(MinimalModuleDrillOperator())
        orchestrator.register_operator(APIResponseSpecOperator())
        orchestrator.register_operator(FrameworkUsageOperator())
        orchestrator.register_operator(RuntimeEvidenceOperator())
        orchestrator.register_operator(ArchitectureHealthScoreOperator())
        orchestrator.register_operator(TruthDocumentGeneratorOperator())

    except ImportError as e:
        print(f"❌ 算子加载失败: {e}")
        print("   某些算子可能尚未实现")
        return 1

    # 确定项目路径
    project_path = Path(args.project).resolve()

    # 执行验收
    try:
        if args.operator:
            # 执行单个算子
            result = orchestrator.verify_single(args.operator, project_path)

            if args.json:
                import json

                print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
            else:
                print("\n" + "=" * 60)
                print(f"算子: {result.operator_name}")
                print(f"状态: {'✅ 通过' if result.passed else '❌ 未通过'}")
                print("=" * 60)

                if result.violations:
                    print(f"\n违规 ({len(result.violations)}):")
                    for v in result.violations:
                        print(f"  [{v.severity.value}] {v.rule}: {v.message}")
                        if v.file_path:
                            print(f"    📍 {v.file_path}:{v.line or '?'}")
                        if v.suggestion:
                            print(f"    💡 {v.suggestion}")

                if result.suggestions:
                    print(f"\n建议:")
                    for s in result.suggestions:
                        print(f"  - {s}")

                if result.evidence:
                    print(f"\n证据:")
                    for k, v in result.evidence.items():
                        print(f"  {k}: {v}")

            # 判断是否失败
            if not result.passed and args.fail_on_score is not None:
                return 1

        else:
            # 执行完整验收
            report = orchestrator.verify_all(project_path)

            if args.json:
                import json

                print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
            else:
                print(report.to_markdown())

            # 判断是否失败
            if args.fail_on_score is not None:
                if report.overall_score < args.fail_on_score:
                    print(
                        f"\n❌ 架构评分 {report.overall_score}/100 "
                        f"低于阈值 {args.fail_on_score}"
                    )
                    return 1

            # 如果有CRITICAL违规，返回失败
            if report.get_critical_violations():
                print(f"\n❌ 发现 {len(report.get_critical_violations())} 个CRITICAL违规")
                return 1

            if not report.passed:
                print("\n⚠️  架构验收未通过，请修复违规后再继续开发")
                return 1

    except KeyboardInterrupt:
        print("\n\n⚠️  验收被用户中断")
        return 130
    except Exception as e:
        print(f"\n❌ 验收失败: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0
