"""
集成测试：完整验证流程
"""

import pytest
from pathlib import Path

from moat.verification.orchestrator import VerifyOrchestrator
from moat.verification.operators import (
    DirectoryResponsibilityOperator,
    MinimalModuleDrillOperator,
    APIResponseSpecOperator,
    FrameworkUsageOperator,
    RuntimeEvidenceOperator,
    ArchitectureHealthScoreOperator,
    TruthDocumentGeneratorOperator,
)
from moat.verification.types import VerificationReport


@pytest.fixture
def orchestrator():
    """创建编排器并注册所有算子"""
    orch = VerifyOrchestrator()
    orch.register_operator(DirectoryResponsibilityOperator())
    orch.register_operator(MinimalModuleDrillOperator())
    orch.register_operator(APIResponseSpecOperator())
    orch.register_operator(FrameworkUsageOperator())
    orch.register_operator(RuntimeEvidenceOperator())
    orch.register_operator(ArchitectureHealthScoreOperator())
    orch.register_operator(TruthDocumentGeneratorOperator())
    return orch


def test_full_verification(orchestrator, tmp_path):
    """测试完整验证流程"""
    # 创建最小项目结构
    (tmp_path / "api").mkdir()
    (tmp_path / "services").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "requirements.txt").write_text("fastapi==0.100.0\n")
    (tmp_path / "main.py").write_text("print('hello')\n")

    report = orchestrator.verify_all(tmp_path)

    assert isinstance(report, VerificationReport)
    assert len(report.operators) == 7
    assert report.overall_score >= 0
    assert report.overall_score <= 100


def test_single_operator_verification(orchestrator, tmp_path):
    """测试单个算子验证"""
    result = orchestrator.verify_single("directory_responsibility", tmp_path)

    assert result.operator_name == "directory_responsibility"
    assert isinstance(result.passed, bool)


def test_single_operator_not_found(orchestrator, tmp_path):
    """测试不存在的算子"""
    with pytest.raises(ValueError, match="不存在"):
        orchestrator.verify_single("nonexistent_operator", tmp_path)


def test_report_json_output(orchestrator, tmp_path):
    """测试JSON输出"""
    report = orchestrator.verify_all(tmp_path)

    import json
    report_dict = report.to_dict()

    # 可以序列化为JSON
    json_str = json.dumps(report_dict)
    assert isinstance(json_str, str)

    # 解析回来
    parsed = json.loads(json_str)
    assert "project_path" in parsed
    assert "overall_score" in parsed
    assert "operators" in parsed


def test_report_markdown_output(orchestrator, tmp_path):
    """测试Markdown输出"""
    report = orchestrator.verify_all(tmp_path)

    md = report.to_markdown()

    assert isinstance(md, str)
    assert "# 架构验收报告" in md
    assert "总体评分" in md
