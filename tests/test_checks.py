"""Moat 检查模块测试"""
import pytest
from pathlib import Path
from moat.checks import l1_import, l1_files, l1_behavior
from moat.baseline import BaselineManager
from moat.runner import CheckResult


class TestCheckResult:
    def test_empty_result(self):
        r = CheckResult()
        assert r.passed == 0
        assert r.failed == 0
        assert r.skipped == 0

    def test_add_ok_errors(self):
        r = CheckResult()
        r.add_errors([{"type": "import_ok", "file": "test.py", "level": "L1", "message": "ok"}])
        assert r.passed == 1
        assert r.failed == 0

    def test_add_failed_errors(self):
        r = CheckResult()
        r.add_errors([{"type": "import_failed", "file": "test.py", "level": "L1", "message": "fail"}])
        assert r.passed == 0
        assert r.failed == 1

    def test_add_skipped_errors(self):
        r = CheckResult()
        r.add_errors([{"type": "skip_no_server", "file": "test.py", "level": "L1", "message": "skip"}])
        assert r.skipped == 1

    def test_summary_format(self):
        r = CheckResult()
        r.passed = 10
        r.failed = 2
        r.skipped = 1
        r.end_time = r.start_time + 1.5
        summary = r.summary()
        assert "10" in summary
        assert "2" in summary
        assert "1" in summary
        assert "1.50" in summary


class TestFileCheck:
    def test_empty_project_has_no_key_files(self, tmp_path):
        """空项目不应该有常见关键文件"""
        errors = l1_files.run_file_check(tmp_path)
        # 应该全部报 missing
        missing = [e for e in errors if e["type"] == "file_missing"]
        # 有 4 个常见关键文件: pyproject.toml, README.md, LICENSE, .gitignore
        assert len(missing) == 4

    def test_project_with_key_files_passes(self, tmp_path):
        """有关键文件的项目应该通过"""
        for f in ["server.py", "README.md", ".gitignore"]:
            (tmp_path / f).write_text("")
        errors = l1_files.run_file_check(tmp_path)
        created_missing = [e for e in errors
                           if e["type"] == "file_missing" and e["file"] in ["server.py", "README.md", ".gitignore"]]
        assert len(created_missing) == 0, "已创建的文件不应报 missing"


class TestBehaviorCheck:
    def test_no_tests_detected(self, tmp_path):
        errors = l1_behavior.run_behavior_check(tmp_path)
        no_tests = [e for e in errors if e["type"] == "behavior_no_tests"]
        assert len(no_tests) > 0

    def test_with_tests_passes(self, tmp_path):
        (tmp_path / "tests").mkdir()
        errors = l1_behavior.run_behavior_check(tmp_path)
        no_tests = [e for e in errors if e["type"] == "behavior_no_tests"]
        assert len(no_tests) == 0


class TestBaseline:
    def test_baseline_save_and_load(self, tmp_path):
        """基线能保存和加载"""
        # 创建几个文件凑数
        (tmp_path / "test.py").write_text("x = 1")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "mod.py").write_text("y = 2")

        bm = BaselineManager(tmp_path)
        data = bm.save()
        assert data["file_count"] > 0
        assert data["total_lines"] > 0

        loaded = bm.load()
        assert loaded is not None
        assert loaded["file_count"] == data["file_count"]