"""
基线管理器测试
"""

import pytest
from pathlib import Path
from datetime import datetime

from moat.baseline import BaselineManager
from moat.verification.types import VerificationContext
from moat.verification.orchestrator import VerifyOrchestrator
from moat.verification.operators import (
    DirectoryResponsibilityOperator,
    MinimalModuleDrillOperator,
)


@pytest.fixture
def baseline_manager(tmp_path):
    """创建基线管理器"""
    # 创建最小项目结构
    (tmp_path / "api").mkdir()
    (tmp_path / "services").mkdir()
    (tmp_path / ".moat").mkdir()
    return BaselineManager(tmp_path)


def test_create_architecture_baseline(baseline_manager, tmp_path):
    """测试创建架构基线"""
    # 运行验收
    orchestrator = VerifyOrchestrator()
    orchestrator.register_operator(DirectoryResponsibilityOperator())
    orchestrator.register_operator(MinimalModuleDrillOperator())

    report = orchestrator.verify_all(tmp_path)

    # 创建基线
    baseline_id = baseline_manager.create_architecture_baseline(
        name="v1.0.0",
        description="初始架构基线",
        verification_report=report,
    )

    assert baseline_id == "v1.0.0"

    # 验证基线已创建
    baseline_data = baseline_manager.get_architecture_baseline("v1.0.0")
    assert baseline_data is not None
    assert baseline_data["name"] == "v1.0.0"
    assert baseline_data["description"] == "初始架构基线"
    assert "timestamp" in baseline_data


def test_list_architecture_baselines(baseline_manager, tmp_path):
    """测试列出架构基线"""
    orchestrator = VerifyOrchestrator()
    orchestrator.register_operator(DirectoryResponsibilityOperator())
    report = orchestrator.verify_all(tmp_path)

    # 创建多个基线
    baseline_manager.create_architecture_baseline("v1.0.0", "基线1", report)
    baseline_manager.create_architecture_baseline("v2.0.0", "基线2", report)

    baselines = baseline_manager.list_architecture_baselines()

    assert len(baselines) == 2
    assert baselines[0]["id"] == "v1.0.0"
    assert baselines[1]["id"] == "v2.0.0"


def test_diff_architecture_baselines(baseline_manager, tmp_path):
    """测试对比架构基线"""
    orchestrator = VerifyOrchestrator()
    orchestrator.register_operator(DirectoryResponsibilityOperator())
    report = orchestrator.verify_all(tmp_path)

    # 创建两个基线
    baseline_manager.create_architecture_baseline("v1.0.0", "基线1", report)
    baseline_manager.create_architecture_baseline("v2.0.0", "基线2", report)

    diff = baseline_manager.diff_architecture_baselines("v1.0.0", "v2.0.0")

    assert "baseline_a" in diff
    assert "baseline_b" in diff
    assert "changes" in diff


def test_rollback_architecture_baseline(baseline_manager, tmp_path):
    """测试回滚架构基线"""
    orchestrator = VerifyOrchestrator()
    orchestrator.register_operator(DirectoryResponsibilityOperator())
    report = orchestrator.verify_all(tmp_path)

    # 创建基线
    baseline_manager.create_architecture_baseline("v1.0.0", "基线1", report)

    # 修改一些文件
    truth_doc = tmp_path / ".moat" / "truth_document.md"
    if truth_doc.exists():
        original_content = truth_doc.read_text()
        truth_doc.write_text("# Modified\n")

        # 回滚
        success = baseline_manager.rollback_architecture_baseline("v1.0.0")
        assert success is True

        # 验证内容已恢复
        restored_content = truth_doc.read_text()
        assert restored_content == original_content


def test_delete_architecture_baseline(baseline_manager, tmp_path):
    """测试删除架构基线"""
    orchestrator = VerifyOrchestrator()
    orchestrator.register_operator(DirectoryResponsibilityOperator())
    report = orchestrator.verify_all(tmp_path)

    baseline_manager.create_architecture_baseline("v1.0.0", "基线1", report)

    baselines = baseline_manager.list_architecture_baselines()
    assert len(baselines) == 1

    # 删除基线
    success = baseline_manager.delete_architecture_baseline("v1.0.0")
    assert success is True

    # 验证已删除
    baselines = baseline_manager.list_architecture_baselines()
    assert len(baselines) == 0


def test_get_current_architecture_baseline(baseline_manager, tmp_path):
    """测试获取当前架构基线"""
    orchestrator = VerifyOrchestrator()
    orchestrator.register_operator(DirectoryResponsibilityOperator())
    report = orchestrator.verify_all(tmp_path)

    # 创建基线
    baseline_manager.create_architecture_baseline("v1.0.0", "基线1", report)

    # 获取当前基线
    current = baseline_manager.get_current_architecture_baseline()
    assert current == "v1.0.0"
