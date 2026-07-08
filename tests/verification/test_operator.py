"""
Operator 基类测试
"""

import pytest
from pathlib import Path
from unittest.mock import Mock

from moat.verification.operator import VerificationOperator
from moat.verification.types import (
    OperatorResult,
    Severity,
    VerificationContext,
    Violation,
)


class ConcreteOperator(VerificationOperator):
    """用于测试的具体算子实现"""

    name = "test_operator"
    description = "测试算子"

    def verify(self, context: VerificationContext) -> OperatorResult:
        return OperatorResult(
            operator_name=self.name,
            passed=True,
            violations=[],
            suggestions=["测试通过"],
        )


class FailingOperator(VerificationOperator):
    """用于测试的失败算子实现"""

    name = "failing_operator"

    def verify(self, context: VerificationContext) -> OperatorResult:
        return OperatorResult(
            operator_name=self.name,
            passed=False,
            violations=[
                Violation(
                    rule="test_rule",
                    message="测试违规",
                    severity=Severity.ERROR,
                )
            ],
            suggestions=["修复测试违规"],
        )


def test_operator_name():
    """测试算子名称"""
    op = ConcreteOperator()
    assert op.name == "test_operator"


def test_operator_description():
    """测试算子描述"""
    op = ConcreteOperator()
    assert op.description == "测试算子"


def test_verify_returns_result():
    """测试verify方法返回正确结果"""
    context = VerificationContext(project_path=Path("/tmp"))
    op = ConcreteOperator()
    result = op.verify(context)

    assert isinstance(result, OperatorResult)
    assert result.passed is True


def test_failing_operator():
    """测试失败算子"""
    context = VerificationContext(project_path=Path("/tmp"))
    op = FailingOperator()
    result = op.verify(context)

    assert result.passed is False
    assert len(result.violations) == 1
    assert result.violations[0].rule == "test_rule"


def test_operator_repr():
    """测试算子字符串表示"""
    op = ConcreteOperator()
    repr_str = repr(op)
    assert "ConcreteOperator" in repr_str
    assert "test_operator" in repr_str
