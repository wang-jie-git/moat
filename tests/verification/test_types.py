"""
类型定义测试
"""

import pytest
from datetime import datetime

from moat.verification.types import (
    Severity,
    Violation,
    OperatorResult,
    VerificationContext,
    VerificationReport,
)
from pathlib import Path


def test_severity_enum():
    """测试严重程度枚举"""
    assert Severity.INFO == "info"
    assert Severity.WARNING == "warning"
    assert Severity.ERROR == "error"
    assert Severity.CRITICAL == "critical"


def test_violation_creation():
    """测试违规对象创建"""
    violation = Violation(
        rule="test_rule",
        message="Test message",
        severity=Severity.ERROR,
        file_path="test.py",
        line=42,
        suggestion="Fix it",
    )

    assert violation.rule == "test_rule"
    assert violation.severity == Severity.ERROR
    assert violation.file_path == "test.py"
    assert violation.line == 42


def test_violation_to_dict():
    """测试违规对象转字典"""
    violation = Violation(
        rule="test_rule",
        message="Test message",
        severity=Severity.ERROR,
    )

    result = violation.to_dict()

    assert result["rule"] == "test_rule"
    assert result["severity"] == "error"
    assert result["file_path"] is None
    assert result["line"] is None


def test_operator_result_creation():
    """测试算子结果创建"""
    result = OperatorResult(
        operator_name="test_op",
        passed=True,
        evidence={"key": "value"},
        suggestions=["suggestion1"],
    )

    assert result.operator_name == "test_op"
    assert result.passed is True
    assert result.evidence == {"key": "value"}
    assert len(result.violations) == 0
    assert len(result.suggestions) == 1


def test_operator_result_to_dict():
    """测试算子结果转字典"""
    violation = Violation(rule="v1", message="m1", severity=Severity.WARNING)
    result = OperatorResult(
        operator_name="test_op",
        passed=False,
        violations=[violation],
        execution_time=1.5,
    )

    result_dict = result.to_dict()

    assert result_dict["operator_name"] == "test_op"
    assert result_dict["passed"] is False
    assert len(result_dict["violations"]) == 1
    assert result_dict["execution_time"] == 1.5


def test_verification_context():
    """测试验收上下文"""
    ctx = VerificationContext(
        project_path=Path("/tmp/project"),
        config={"key": "value"},
    )

    assert ctx.project_path == Path("/tmp/project")
    assert ctx.config == {"key": "value"}
    assert isinstance(ctx.timestamp, datetime)


def test_verification_report_get_violations():
    """测试报告获取所有违规"""
    critical_violation = Violation(rule="v1", message="m1", severity=Severity.CRITICAL)
    warning_violation = Violation(rule="v2", message="m2", severity=Severity.WARNING)

    op1_result = OperatorResult(
        operator_name="op1",
        passed=False,
        violations=[critical_violation],
    )
    op2_result = OperatorResult(
        operator_name="op2",
        passed=False,
        violations=[warning_violation],
    )

    report = VerificationReport(
        project_path=Path("/tmp"),
        operators=[op1_result, op2_result],
        overall_score=50.0,
        passed=False,
    )

    violations = report.get_violations()
    assert len(violations) == 2

    critical = report.get_critical_violations()
    assert len(critical) == 1
    assert critical[0].rule == "v1"
    assert critical[0].severity == Severity.CRITICAL


def test_verification_report_to_dict():
    """测试报告转字典"""
    report = VerificationReport(
        project_path=Path("/tmp/project"),
        operators=[],
        overall_score=80.0,
        passed=True,
    )

    result = report.to_dict()

    assert "project_path" in result
    assert "overall_score" in result
    assert result["overall_score"] == 80.0
    assert result["passed"] is True
    assert "operators" in result


def test_verification_report_to_markdown():
    """测试报告生成Markdown"""
    violation = Violation(
        rule="test_rule",
        message="Test message",
        severity=Severity.ERROR,
        file_path="test.py",
        line=42,
    )

    op_result = OperatorResult(
        operator_name="test_op",
        passed=False,
        violations=[violation],
        suggestions=["Fix this"],
    )

    report = VerificationReport(
        project_path=Path("/tmp/project"),
        operators=[op_result],
        overall_score=50.0,
        passed=False,
    )

    md = report.to_markdown()

    assert "# 架构验收报告" in md
    assert "test_op" in md
    assert "test_rule" in md
    assert "test.py" in md
