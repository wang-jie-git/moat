"""l1_behavior.py 测试

覆盖 moat/checks/l1_behavior.py — 行为验证检查
"""
import tempfile
from pathlib import Path

import pytest

from moat.checks.l1_behavior import run_behavior_check


@pytest.fixture
def tmp_project(tmp_path):
    """创建临时项目"""
    project = tmp_path / "test_project"
    project.mkdir()
    return project


class TestRunBehaviorCheck:
    """测试 run_behavior_check 函数"""

    def test_has_tests_and_ci(self, tmp_project):
        """测试有测试目录和 CI 配置"""
        # 创建测试目录
        (tmp_project / "tests").mkdir()
        (tmp_project / "tests" / "test_main.py").write_text("def test_dummy(): pass\n")

        # 创建 CI 配置
        (tmp_project / ".github").mkdir(parents=True)
        (tmp_project / ".github" / "workflows").mkdir()
        (tmp_project / ".github" / "workflows" / "ci.yml").write_text("name: CI\n")

        errors = run_behavior_check(tmp_project)
        assert len(errors) == 0

    def test_no_tests_dir(self, tmp_project):
        """测试缺少测试目录"""
        # 创建 CI 配置（避免其他错误）
        (tmp_project / ".github").mkdir(parents=True)
        (tmp_project / ".github" / "workflows").mkdir()

        errors = run_behavior_check(tmp_project)

        assert len(errors) >= 1
        assert any(e["type"] == "behavior_no_tests" for e in errors)
        assert any("测试目录" in e["message"] for e in errors)

    def test_no_ci_config(self, tmp_project):
        """测试缺少 CI 配置"""
        # 创建测试目录（避免其他错误）
        (tmp_project / "tests").mkdir()
        (tmp_project / "tests" / "test_main.py").write_text("def test_dummy(): pass\n")

        errors = run_behavior_check(tmp_project)

        assert len(errors) >= 1
        assert any(e["type"] == "behavior_no_ci" for e in errors)
        assert any("CI 配置" in e["message"] for e in errors)

    def test_missing_both(self, tmp_project):
        """测试同时缺少测试目录和 CI 配置"""
        errors = run_behavior_check(tmp_project)

        assert len(errors) == 2
        assert any(e["type"] == "behavior_no_tests" for e in errors)
        assert any(e["type"] == "behavior_no_ci" for e in errors)

    def test_test_dir_alternatives(self, tmp_project):
        """测试 test 目录（而非 tests）"""
        # 创建 test 目录
        (tmp_project / "test").mkdir()
        (tmp_project / "test" / "test_main.py").write_text("def test_dummy(): pass\n")

        # 创建 CI 配置
        (tmp_project / ".github").mkdir(parents=True)
        (tmp_project / ".github" / "workflows").mkdir()

        errors = run_behavior_check(tmp_project)
        # 应该通过（有 test 目录和 CI）
        assert len([e for e in errors if e["type"] == "behavior_no_tests"]) == 0

    def test_ci_alternatives(self, tmp_project):
        """测试其他 CI 配置"""
        # 创建测试目录
        (tmp_project / "tests").mkdir()

        # 创建 GitLab CI
        (tmp_project / ".gitlab-ci.yml").write_text("test:\n  script: pytest\n")

        errors = run_behavior_check(tmp_project)
        # 应该通过（有 tests 目录和 GitLab CI）
        assert len([e for e in errors if e["type"] == "behavior_no_ci"]) == 0

    def test_error_format(self, tmp_project):
        """测试错误格式"""
        errors = run_behavior_check(tmp_project)

        for error in errors:
            assert "file" in error
            assert "level" in error
            assert error["level"] == "L1"
            assert "type" in error
            assert "message" in error

    def test_file_field_values(self, tmp_project):
        """测试 file 字段的值"""
        errors = run_behavior_check(tmp_project)

        for error in errors:
            if error["type"] == "behavior_no_tests":
                assert error["file"] == "tests/"
            elif error["type"] == "behavior_no_ci":
                assert error["file"] == ".github/"
