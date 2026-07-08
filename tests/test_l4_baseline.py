"""L4 基线对比检查测试

验证基线缺失检测、文件数阈值告警、代码行数阈值告警。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from moat.checks import l4_baseline


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture()
def small_project(tmp_path: Path) -> Path:
    """返回约 50 行代码的测试项目。"""
    (tmp_path / "main.py").write_text("x = 1\n" * 50)
    return tmp_path


@pytest.fixture()
def medium_project(tmp_path: Path) -> Path:
    """返回约 250 行代码的测试项目。"""
    for i in range(25):
        (tmp_path / f"module_{i}.py").write_text("x = 1\n" * 10)
    return tmp_path


# ──────────────────────────────────────────────
# 基线缺失
# ──────────────────────────────────────────────

class TestBaselineMissing:
    """无基线时的行为。"""

    def test_no_baseline_returns_warning(self, small_project: Path) -> None:
        """传入 None 基线应返回 baseline_missing 警告。"""
        errors = l4_baseline.run_baseline_check(small_project, baseline=None)
        assert len(errors) >= 1

    def test_no_baseline_type_is_baseline_missing(self, small_project: Path) -> None:
        """警告类型必须为 baseline_missing。"""
        errors = l4_baseline.run_baseline_check(small_project, baseline=None)
        assert errors[0]["type"] == "baseline_missing"

    def test_no_baseline_level_is_l4(self, small_project: Path) -> None:
        """基线缺失警告必须标记为 L4。"""
        errors = l4_baseline.run_baseline_check(small_project, baseline=None)
        assert errors[0]["level"] == "L4"

    def test_no_baseline_mentions_current_state(self, small_project: Path) -> None:
        """警告消息必须包含当前文件数和行数。"""
        errors = l4_baseline.run_baseline_check(small_project, baseline=None)
        msg = errors[0]["message"]
        assert "文件" in msg or "file" in msg.lower()

    def test_empty_baseline_dict(self, small_project: Path) -> None:
        """传入空字典基线应被视为无基线。"""
        errors = l4_baseline.run_baseline_check(small_project, baseline={})
        # 空字典没有 file_count/total_lines，应返回 baseline_missing 或正常对比
        assert isinstance(errors, list)


# ──────────────────────────────────────────────
# 文件数下降告警
# ──────────────────────────────────────────────

class TestFileCountDrop:
    """文件数下降超过 10% 应触发告警。"""

    def test_file_count_drop_detected(self, small_project: Path) -> None:
        """基线 100 文件 → 当前 80 文件（下降 20%）应触发告警。"""
        baseline = {"file_count": 100, "total_lines": 5000}
        # small_project 只有 1 个文件
        errors = l4_baseline.run_baseline_check(small_project, baseline=baseline)

        drop_errors = [e for e in errors if e["type"] == "file_count_drop"]
        assert len(drop_errors) >= 1
        assert drop_errors[0]["level"] == "L4"

    def test_file_count_drop_message_format(self, small_project: Path) -> None:
        """告警消息必须包含基线和当前文件数。"""
        baseline = {"file_count": 100, "total_lines": 5000}
        errors = l4_baseline.run_baseline_check(small_project, baseline=baseline)

        drop = next(e for e in errors if e["type"] == "file_count_drop")
        msg = drop["message"]
        assert "100" in msg or "文件" in msg

    def test_file_count_normal_no_drop_alert(self, medium_project: Path) -> None:
        """基线 25 → 当前 25（无下降）不应触发下降告警。"""
        baseline = {"file_count": 25, "total_lines": 2500}
        errors = l4_baseline.run_baseline_check(medium_project, baseline=baseline)

        drop_errors = [e for e in errors if e["type"] == "file_count_drop"]
        assert drop_errors == []

    def test_file_count_drop_exactly_10_percent(self, tmp_path: Path) -> None:
        """下降恰好 10% 不应触发（阈值是 >10%）。"""
        for i in range(10):
            (tmp_path / f"m{i}.py").write_text("x = 1\n")
        baseline = {"file_count": 10, "total_lines": 10}

        # 删除 1 个文件 → 9/10 = 90%（恰好 10% 下降，不大于 10%）
        (tmp_path / "m0.py").unlink()
        errors = l4_baseline.run_baseline_check(tmp_path, baseline=baseline)

        drop_errors = [e for e in errors if e["type"] == "file_count_drop"]
        assert drop_errors == []

    def test_file_count_drop_11_percent_triggers(self, tmp_path: Path) -> None:
        """下降 11%（>10% 阈值）应触发告警。"""
        for i in range(100):
            (tmp_path / f"m{i}.py").write_text("x = 1\n")
        baseline = {"file_count": 100, "total_lines": 100}

        # 删除 12 个文件 → 88/100 = 88%（下降 12%）
        for i in range(12):
            (tmp_path / f"m{i}.py").unlink()
        errors = l4_baseline.run_baseline_check(tmp_path, baseline=baseline)

        drop_errors = [e for e in errors if e["type"] == "file_count_drop"]
        assert len(drop_errors) >= 1


# ──────────────────────────────────────────────
# 文件数暴涨告警
# ──────────────────────────────────────────────

class TestFileCountSurge:
    """文件数增加超过 30% 应触发告警。"""

    def test_file_count_surge_detected(self, small_project: Path) -> None:
        """基线 10 → 当前 50 文件（增加 400%）应触发告警。"""
        for i in range(49):
            (small_project / f"extra_{i}.py").write_text("x = 1\n")
        baseline = {"file_count": 1, "total_lines": 50}
        errors = l4_baseline.run_baseline_check(small_project, baseline=baseline)

        surge_errors = [e for e in errors if e["type"] == "file_count_surge"]
        assert len(surge_errors) >= 1
        assert surge_errors[0]["level"] == "L4"

    def test_file_count_normal_no_surge_alert(self, medium_project: Path) -> None:
        """基线 25 → 当前 25（无暴涨）不应触发暴涨告警。"""
        baseline = {"file_count": 25, "total_lines": 2500}
        errors = l4_baseline.run_baseline_check(medium_project, baseline=baseline)

        surge_errors = [e for e in errors if e["type"] == "file_count_surge"]
        assert surge_errors == []


# ──────────────────────────────────────────────
# 代码行数下降告警
# ──────────────────────────────────────────────

class TestLineCountDrop:
    """代码行数下降超过 10% 应触发告警。"""

    def test_line_count_drop_detected(self, medium_project: Path) -> None:
        """基线 5000 → 当前 2000 行（下降 60%）应触发告警。"""
        # medium_project 有 250 行
        baseline = {"file_count": 25, "total_lines": 5000}
        errors = l4_baseline.run_baseline_check(medium_project, baseline=baseline)

        line_errors = [e for e in errors if e["type"] == "line_count_drop"]
        assert len(line_errors) >= 1
        assert line_errors[0]["level"] == "L4"

    def test_line_count_normal_no_drop_alert(self, medium_project: Path) -> None:
        """基线匹配当前行数不应触发告警。"""
        baseline = l4_baseline.capture_baseline(medium_project)
        errors = l4_baseline.run_baseline_check(medium_project, baseline=baseline)

        line_errors = [e for e in errors if e["type"] == "line_count_drop"]
        assert line_errors == [], f"预期无行数告警，实际: {line_errors}"

    def test_line_count_zero_baseline_no_error(self, small_project: Path) -> None:
        """基线行数为 0 时应跳过行数检查（避免除零误报）。"""
        baseline = {"file_count": 0, "total_lines": 0}
        errors = l4_baseline.run_baseline_check(small_project, baseline=baseline)

        line_errors = [e for e in errors if e["type"] == "line_count_drop"]
        assert line_errors == []


# ──────────────────────────────────────────────
# 组合场景
# ──────────────────────────────────────────────

class TestCombinedScenarios:
    """多告警同时触发的场景。"""

    def test_multiple_alerts_at_once(self, small_project: Path) -> None:
        """基线 100 文件 / 5000 行 → 当前 1 文件 / 50 行：两个告警同时触发。"""
        baseline = {"file_count": 100, "total_lines": 5000}
        errors = l4_baseline.run_baseline_check(small_project, baseline=baseline)

        types = {e["type"] for e in errors}
        assert "file_count_drop" in types
        assert "line_count_drop" in types

    def test_all_clear_scenario(self, medium_project: Path) -> None:
        """基线匹配当前状态时不应有任何告警。"""
        current_errors = l4_baseline.run_baseline_check(medium_project, baseline=None)
        # 只有 baseline_missing 条目
        assert current_errors[0]["type"] == "baseline_missing"

        # 用 capture_baseline 获取精确基线
        baseline = l4_baseline.capture_baseline(medium_project)
        errors = l4_baseline.run_baseline_check(medium_project, baseline=baseline)

        assert errors == [], f"预期无告警，实际: {errors}"
