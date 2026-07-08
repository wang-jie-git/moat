"""
Orchestrator 测试
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from moat.verification.orchestrator import VerifyOrchestrator
from moat.verification.operator import VerificationOperator
from moat.verification.types import (
    OperatorResult,
    Severity,
    VerificationContext,
    Violation,
)


class MockOperator(VerificationOperator):
    """用于测试的Mock算子"""

    def __init__(self, name: str, passed: bool = True, violations: list[Violation] = None):
        self._name = name
        self._passed = passed
        self._violations = violations or []
        self.verify_called = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Mock {self._name}"

    def verify(self, context: VerificationContext) -> OperatorResult:
        self.verify_called = True
        return OperatorResult(
            operator_name=self._name,
            passed=self._passed,
            violations=self._violations,
        )


def test_orchestrator_creation():
    """测试编排器创建"""
    orchestrator = VerifyOrchestrator()
    assert len(orchestrator.list_operators()) == 0


def test_orchestrator_register_operator():
    """测试注册算子"""
    orchestrator = VerifyOrchestrator()
    op = MockOperator("test_op")

    orchestrator.register_operator(op)

    assert len(orchestrator.list_operators()) == 1
    assert orchestrator.get_operator("test_op") == op


def test_orchestrator_duplicate_operator():
    """测试重复算子注册"""
    orchestrator = VerifyOrchestrator()
    op1 = MockOperator("test_op")
    op2 = MockOperator("test_op")

    orchestrator.register_operator(op1)

    with pytest.raises(ValueError, match="已存在"):
        orchestrator.register_operator(op2)


def test_orchestrator_verify_all(tmp_path):
    """测试完整验收流程"""
    orchestrator = VerifyOrchestrator()

    op1 = MockOperator("op1", passed=True)
    op2 = MockOperator("op2", passed=False, violations=[
        Violation(rule="v1", message="Violation 1", severity=Severity.ERROR)
    ])
    op3 = MockOperator("op3", passed=True)

    orchestrator.register_operator(op1)
    orchestrator.register_operator(op2)
    orchestrator.register_operator(op3)

    report = orchestrator.verify_all(tmp_path)

    assert len(report.operators) == 3
    assert report.passed is False  # op2失败
    assert report.overall_score < 100

    # 验证所有算子都被调用
    assert op1.verify_called is True
    assert op2.verify_called is True
    assert op3.verify_called is True


def test_orchestrator_verify_single(tmp_path):
    """测试单个算子验收"""
    orchestrator = VerifyOrchestrator()
    op = MockOperator("test_op", passed=True)
    orchestrator.register_operator(op)

    result = orchestrator.verify_single("test_op", tmp_path)

    assert result.operator_name == "test_op"
    assert result.passed is True


def test_orchestrator_verify_single_not_found(tmp_path):
    """测试不存在的算子"""
    orchestrator = VerifyOrchestrator()

    with pytest.raises(ValueError, match="不存在"):
        orchestrator.verify_single("nonexistent", tmp_path)


def test_orchestrator_score_calculation(tmp_path):
    """测试评分计算"""
    orchestrator = VerifyOrchestrator()

    op1 = MockOperator("op1", passed=True)
    op2 = MockOperator("op2", passed=False, violations=[
        Violation(rule="critical", message="Critical", severity=Severity.CRITICAL),
        Violation(rule="error", message="Error", severity=Severity.ERROR),
        Violation(rule="warning", message="Warning", severity=Severity.WARNING),
    ])
    op3 = MockOperator("op3", passed=False, violations=[
        Violation(rule="info", message="Info", severity=Severity.INFO),
    ])

    orchestrator.register_operator(op1)
    orchestrator.register_operator(op2)
    orchestrator.register_operator(op3)

    report = orchestrator.verify_all(tmp_path)

    # op2: CRITICAL(-20) + ERROR(-10) + WARNING(-5) = -35
    # op3: INFO(-1) = -1
    # 总分: 100 - 35 - 1 = 64
    assert report.overall_score == pytest.approx(64.0, rel=0.1)


def test_orchestrator_empty_operators(tmp_path):
    """测试空算子列表"""
    orchestrator = VerifyOrchestrator()
    report = orchestrator.verify_all(tmp_path)

    assert report.overall_score == 0.0
    assert report.passed is True  # 空列表视为通过
