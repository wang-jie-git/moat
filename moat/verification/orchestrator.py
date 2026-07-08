"""
验收流程编排器 — 组合算子，灵活调度
"""

from pathlib import Path
from typing import TYPE_CHECKING

from .types import (
    OperatorResult,
    Severity,
    VerificationContext,
    VerificationReport,
)
from .operator import VerificationOperator

if TYPE_CHECKING:
    pass


class VerifyOrchestrator:
    """
    验收流程编排器

    职责:
    1. 注册所有算子
    2. 编排执行顺序
    3. 聚合结果
    4. 计算总体评分

    使用示例:
        orchestrator = VerifyOrchestrator()
        orchestrator.register_operator(DirectoryResponsibilityOperator())
        orchestrator.register_operator(MinimalModuleDrillOperator())
        ...

        # 执行完整验收
        report = orchestrator.verify_all("/path/to/project")

        # 执行单个算子
        result = orchestrator.verify_single("directory_responsibility", "/path/to/project")
    """

    def __init__(self):
        self._operators: list[VerificationOperator] = []
        self._operator_map: dict[str, VerificationOperator] = {}

    def register_operator(self, operator: VerificationOperator) -> None:
        """
        注册算子

        Args:
            operator: 算子实例

        示例:
            orchestrator.register_operator(DirectoryResponsibilityOperator())
        """
        if operator.name in self._operator_map:
            raise ValueError(f"算子 '{operator.name}' 已存在")

        self._operators.append(operator)
        self._operator_map[operator.name] = operator

    def get_operator(self, name: str) -> VerificationOperator | None:
        """根据名称获取算子"""
        return self._operator_map.get(name)

    def list_operators(self) -> list[str]:
        """列出所有已注册算子"""
        return [op.name for op in self._operators]

    def verify_all(self, project_path: str | Path) -> VerificationReport:
        """
        执行完整验收流程（所有算子）

        Args:
            project_path: 项目根路径

        Returns:
            VerificationReport: 完整验收报告
        """
        context = VerificationContext(project_path=Path(project_path))
        results = []

        print(f"\n📋 开始架构验收...")
        print(f"   项目: {project_path}")
        print(f"   算子数: {len(self._operators)}\n")

        for i, operator in enumerate(self._operators, 1):
            print(f"[{i}/{len(self._operators)}] 执行: {operator.name}...")

            try:
                result = operator.verify(context)
                status = "✅ 通过" if result.passed else "❌ 未通过"
                print(f"           {status} ({result.execution_time:.2f}s)")

                if result.violations:
                    print(f"           违规: {len(result.violations)} 个")

            except Exception as e:
                print(f"           ❌ 执行失败: {e}")

                # 创建失败结果
                result = OperatorResult(
                    operator_name=operator.name,
                    passed=False,
                    violations=[],
                    suggestions=[f"算子执行异常: {e}"],
                )

            results.append(result)

        # 计算总体评分
        overall_score = self._calculate_overall_score(results)

        # 判断是否全部通过
        all_passed = all(r.passed for r in results)

        print(f"\n📊 验收完成")
        print(f"   总体评分: {overall_score}/100")
        print(f"   状态: {'✅ 通过' if all_passed else '❌ 未通过'}\n")

        return VerificationReport(
            project_path=Path(project_path),
            operators=results,
            overall_score=overall_score,
            passed=all_passed,
        )

    def verify_single(self, operator_name: str, project_path: str | Path) -> OperatorResult:
        """
        执行单个算子验收

        Args:
            operator_name: 算子名称
            project_path: 项目根路径

        Returns:
            OperatorResult: 算子结果

        Raises:
            ValueError: 算子不存在
        """
        operator = self._operator_map.get(operator_name)
        if not operator:
            raise ValueError(
                f"算子 '{operator_name}' 不存在\n"
                f"可用算子: {', '.join(self.list_operators())}"
            )

        context = VerificationContext(project_path=Path(project_path))
        print(f"\n📋 执行算子: {operator.name}")
        print(f"   {operator.description}\n")

        result = operator.verify(context)
        return result

    def _calculate_overall_score(self, results: list[OperatorResult]) -> float:
        """
        计算总体评分

        策略:
        - 每个算子权重相同
        - 通过的算子得满分，未通过的按违规数量扣分
        - CRITICAL违规扣20分，ERROR扣10分，WARNING扣5分，INFO扣1分
        """
        if not results:
            return 0.0

        total_score = 100.0
        penalties = {
            Severity.CRITICAL: 20.0,
            Severity.ERROR: 10.0,
            Severity.WARNING: 5.0,
            Severity.INFO: 1.0,
        }

        for result in results:
            if not result.passed:
                for violation in result.violations:
                    penalty = penalties.get(violation.severity, 0)
                    total_score -= penalty

        return max(0.0, min(100.0, total_score))

    def __repr__(self) -> str:
        return f"VerifyOrchestrator(operators={len(self._operators)})"
