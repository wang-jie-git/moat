"""
Surgical Changes 规则测试
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from moat.rules import (
    Principle,
    PrincipleViolation,
    PrinciplesLoader,
)
from moat.rules.surgical_changes import SurgicalChangesChecker, DiffStats


class TestPrincipleDefinition:
    """测试原则定义类"""

    def test_principle_creation(self):
        """测试 Principle 创建"""
        principle = Principle(
            name="surgical_changes",
            description="修改必须精准",
            check_type="diff_size_limit",
            enforcement="warning"
        )

        assert principle.name == "surgical_changes"
        assert principle.enforcement == "warning"

    def test_principle_violation_creation(self):
        """测试 PrincipleViolation 创建"""
        violation = PrincipleViolation(
            principle_name="surgical_changes",
            severity="warning",
            message="修改过大",
            file_path="test.py",
            context={"lines": 150}
        )

        assert violation.principle_name == "surgical_changes"
        assert violation.file_path == "test.py"
        assert violation.context["lines"] == 150


class TestPrinciplesLoader:
    """测试原则加载器"""

    def test_load_principles(self):
        """测试加载原则定义"""
        loader = PrinciplesLoader()
        principles = loader.load_principles()

        assert len(principles) > 0
        assert "surgical_changes" in principles
        assert "simplicity_first" in principles
        assert "think_before_coding" in principles
        assert "goal_driven" in principles

    def test_get_principle(self):
        """测试获取单个原则"""
        loader = PrinciplesLoader()
        loader.load_principles()

        principle = loader.get_principle("surgical_changes")
        assert principle is not None
        assert principle.name == "surgical_changes"
        assert principle.check_type == "diff_size_limit"

    def test_get_nonexistent_principle(self):
        """测试获取不存在的原则"""
        loader = PrinciplesLoader()
        loader.load_principles()

        principle = loader.get_principle("nonexistent")
        assert principle is None

    def test_get_enforcement_level(self):
        """测试获取执行级别"""
        loader = PrinciplesLoader()
        loader.load_principles()

        assert loader.get_enforcement_level("surgical_changes") == "warning"
        assert loader.get_enforcement_level("simplicity_first") == "critical"
        assert loader.get_enforcement_level("think_before_coding") == "warning"
        assert loader.get_enforcement_level("goal_driven") == "info"

    def test_thresholds_loaded(self):
        """测试阈值被正确加载"""
        loader = PrinciplesLoader()
        principles = loader.load_principles()

        surgical = principles["surgical_changes"]
        assert "max_diff_lines" in surgical.thresholds
        assert surgical.thresholds["max_diff_lines"] == 100

        simplicity = principles["simplicity_first"]
        assert "max_function_lines" in simplicity.thresholds
        assert simplicity.thresholds["max_function_lines"] == 50


class TestSurgicalChangesChecker:
    """测试手术刀式修改检查器"""

    def test_checker_creation(self):
        """测试检查器创建"""
        checker = SurgicalChangesChecker()
        assert checker.max_diff_lines == 100
        assert checker.max_files_changed == 3

    def test_custom_thresholds(self):
        """测试自定义阈值"""
        checker = SurgicalChangesChecker(max_diff_lines=200, max_files_changed=5)
        assert checker.max_diff_lines == 200
        assert checker.max_files_changed == 5

    @patch('moat.rules.surgical_changes.subprocess.run')
    def test_check_diff_with_large_changes(self, mock_run):
        """测试检测大型修改"""
        # 模拟 git diff 输出（超过 100 行）
        mock_run.return_value = MagicMock(
            stdout="150\t0\tlarge_file.py\n",  # +150 行
            returncode=0
        )

        checker = SurgicalChangesChecker(max_diff_lines=100)
        violations = checker.check_diff(Path.cwd())

        assert len(violations) == 1
        assert violations[0].principle_name == "surgical_changes"
        assert violations[0].severity == "warning"
        assert "修改过大" in violations[0].message
        assert violations[0].context["total_changes"] == 150

    @patch('moat.rules.surgical_changes.subprocess.run')
    def test_check_diff_within_limit(self, mock_run):
        """测试修改在限制内"""
        # 模拟 git diff 输出（50 行）
        mock_run.return_value = MagicMock(
            stdout="50\t10\tsmall_file.py\n",  # +50/-10 = 60 行
            returncode=0
        )

        checker = SurgicalChangesChecker(max_diff_lines=100)
        violations = checker.check_diff(Path.cwd())

        assert len(violations) == 0

    @patch('moat.rules.surgical_changes.subprocess.run')
    def test_check_diff_too_many_files(self, mock_run):
        """测试修改文件过多"""
        # 模拟 4 个文件修改（超过限制 3）
        mock_run.return_value = MagicMock(
            stdout="10\t5\tfile1.py\n10\t5\tfile2.py\n10\t5\tfile3.py\n10\t5\tfile4.py\n",
            returncode=0
        )

        checker = SurgicalChangesChecker(max_files_changed=3)
        violations = checker.check_diff(Path.cwd())

        assert len(violations) == 1
        assert "修改文件过多" in violations[0].message
        assert violations[0].context["files_changed"] == 4

    @patch('moat.rules.surgical_changes.subprocess.run')
    def test_check_diff_not_git_repo(self, mock_run):
        """测试非 Git 仓库"""
        mock_run.side_effect = Exception("Not a git repository")

        checker = SurgicalChangesChecker()
        violations = checker.check_diff(Path.cwd())

        assert len(violations) == 0

    def test_get_recommendation_for_large_file(self):
        """测试大文件修改的建议"""
        checker = SurgicalChangesChecker()

        violation = PrincipleViolation(
            principle_name="surgical_changes",
            severity="warning",
            message="修改过大",
            file_path="large.py",
            context={"added_lines": 150, "removed_lines": 30, "total_changes": 180}
        )

        recommendation = checker.get_recommendation(violation)
        assert "拆分" in recommendation
        assert "large.py" in recommendation

    def test_get_recommendation_for_many_files(self):
        """测试多文件修改的建议"""
        checker = SurgicalChangesChecker()

        violation = PrincipleViolation(
            principle_name="surgical_changes",
            severity="warning",
            message="修改文件过多",
            context={
                "files_changed": 5,
                "files": ["a.py", "b.py", "c.py", "d.py", "e.py"]
            }
        )

        recommendation = checker.get_recommendation(violation)
        assert "a.py" in recommendation
        assert "b.py" in recommendation


class TestDiffStats:
    """测试 DiffStats 数据类"""

    def test_diff_stats_creation(self):
        """测试 DiffStats 创建"""
        stat = DiffStats(
            file_path="test.py",
            added_lines=50,
            removed_lines=20,
            total_changes=70,
            change_type="modified"
        )

        assert stat.file_path == "test.py"
        assert stat.added_lines == 50
        assert stat.removed_lines == 20
        assert stat.total_changes == 70
        assert stat.change_type == "modified"
