"""
Architecture Health Score Operator 测试
"""

import pytest
from pathlib import Path

from moat.verification.operators.architecture_health_score import ArchitectureHealthScoreOperator
from moat.verification.types import VerificationContext


@pytest.fixture
def operator():
    """创建算子实例"""
    return ArchitectureHealthScoreOperator()


@pytest.fixture
def context(tmp_path):
    """创建测试上下文"""
    return VerificationContext(project_path=tmp_path)


def test_operator_name(operator):
    """测试算子名称"""
    assert operator.name == "architecture_health_score"


def test_score_calculation_min_score(operator, context, tmp_path):
    """测试最低分（空项目）"""
    score = operator.verify(context)

    assert score.evidence["total_score"] >= 0
    assert score.evidence["total_score"] <= 100


def test_score_calculation_with_structure(operator, context, tmp_path):
    """测试有结构的项目评分"""
    # 创建结构化目录
    (tmp_path / "api").mkdir()
    (tmp_path / "services").mkdir()
    (tmp_path / "repositories").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\ndependencies=['fastapi']")

    result = operator.verify(context)

    score = result.evidence["total_score"]
    assert score >= 70  # 结构清晰的项目应该≥70


def test_score_dimensions(operator, context, tmp_path):
    """测试评分维度"""
    (tmp_path / "api").mkdir()
    (tmp_path / "services").mkdir()
    (tmp_path / "tests").mkdir()

    result = operator.verify(context)

    evidence = result.evidence
    assert "directory_responsibility" in evidence
    assert "layer_separation" in evidence
    assert "api_consistency" in evidence
    assert "framework_usage" in evidence
    assert "naming_consistency" in evidence

    # 验证每个维度的分数范围
    for dimension in ["directory_responsibility", "layer_separation",
                      "api_consistency", "framework_usage", "naming_consistency"]:
        assert 0 <= evidence[dimension]["score"] <= 20


def test_score_thresholds(operator, context, tmp_path):
    """测试评分阈值"""
    # 空项目应该得到较低分数
    result = operator.verify(context)
    score = result.evidence["total_score"]

    if score >= 80:
        assert "优秀" in result.suggestions[0]
    elif score >= 70:
        assert "良好" in result.suggestions[0]
    elif score >= 60:
        assert len([v for v in result.violations if v.severity.name == "WARNING"]) > 0
    else:
        assert len([v for v in result.violations if v.severity.name == "CRITICAL"]) > 0
