"""L1 文件完整性检查测试

验证关键文件存在性检测和 __init__.py 覆盖率统计。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from moat.checks import l1_files


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture()
def complete_project(tmp_path: Path) -> Path:
    """包含所有关键文件的完整项目。"""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n")
    (tmp_path / "README.md").write_text("# Demo\n")
    (tmp_path / "LICENSE").write_text("MIT\n")
    (tmp_path / ".gitignore").write_text("*.pyc\n")

    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")

    return tmp_path


@pytest.fixture()
def incomplete_project(tmp_path: Path) -> Path:
    """缺少 README.md 和 LICENSE 的不完整项目。"""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n")
    (tmp_path / ".gitignore").write_text("*.pyc\n")
    return tmp_path


# ──────────────────────────────────────────────
# 关键文件检测
# ──────────────────────────────────────────────

class TestKeyFilesDetection:
    """关键文件存在性检测。"""

    def test_all_key_files_present(self, complete_project: Path) -> None:
        """所有关键文件存在时，应至少有一个 file_ok 条目。"""
        errors = l1_files.run_file_check(complete_project)
        ok_entries = [e for e in errors if e["type"] == "file_ok"]
        assert len(ok_entries) >= 1

    def test_missing_readme_detected(self, incomplete_project: Path) -> None:
        """缺失 README.md 应报告 file_missing 错误。"""
        errors = l1_files.run_file_check(incomplete_project)

        missing_readme = [e for e in errors if e["type"] == "file_missing"]
        assert len(missing_readme) >= 1
        assert any("README.md" in e["file"] for e in missing_readme)

    def test_missing_license_detected(self, incomplete_project: Path) -> None:
        """缺失 LICENSE 应报告 file_missing 错误。"""
        errors = l1_files.run_file_check(incomplete_project)

        missing_license = [e for e in errors if e["type"] == "file_missing"]
        assert any("LICENSE" in e["file"] for e in missing_license)

    def test_missing_gitignore_detected(self, tmp_path: Path) -> None:
        """缺失 .gitignore 应被检测。"""
        (tmp_path / "pyproject.toml").write_text("")
        (tmp_path / "README.md").write_text("")
        (tmp_path / "LICENSE").write_text("")

        errors = l1_files.run_file_check(tmp_path)
        assert any(e["type"] == "file_missing" and ".gitignore" in e["file"] for e in errors)

    def test_missing_pyproject_detected(self, tmp_path: Path) -> None:
        """缺失 pyproject.toml 应被检测。"""
        (tmp_path / "README.md").write_text("")
        (tmp_path / "LICENSE").write_text("")
        (tmp_path / ".gitignore").write_text("")

        errors = l1_files.run_file_check(tmp_path)
        assert any(
            e["type"] == "file_missing" and "pyproject.toml" in e["file"]
            for e in errors
        )

    def test_error_level_is_l1(self, incomplete_project: Path) -> None:
        """文件缺失错误必须标记为 L1。"""
        errors = l1_files.run_file_check(incomplete_project)
        missing = [e for e in errors if e["type"] == "file_missing"]
        assert len(missing) >= 1
        assert missing[0]["level"] == "L1"


# ──────────────────────────────────────────────
# __init__.py 覆盖率统计
# ──────────────────────────────────────────────

class TestInitPyCoverage:
    """__init__.py 覆盖率统计。"""

    def test_reports_init_dirs(self, complete_project: Path) -> None:
        """file_ok 消息应提及发现的包目录数。"""
        errors = l1_files.run_file_check(complete_project)
        ok = next(e for e in errors if e["type"] == "file_ok")
        assert "1 个包目录" in ok["message"] or "1 个" in ok["message"]

    def test_multiple_packages_counted(self, tmp_path: Path) -> None:
        """多个包目录应被正确计数。"""
        (tmp_path / "pyproject.toml").write_text("")
        (tmp_path / "README.md").write_text("")
        (tmp_path / "LICENSE").write_text("")
        (tmp_path / ".gitignore").write_text("")

        for name in ("pkg_a", "pkg_b", "pkg_c"):
            pkg = tmp_path / name
            pkg.mkdir()
            (pkg / "__init__.py").write_text("")

        errors = l1_files.run_file_check(tmp_path)
        ok = next(e for e in errors if e["type"] == "file_ok")
        assert "3" in ok["message"]

    def test_nested_package_detected(self, tmp_path: Path) -> None:
        """嵌套包（pkg/sub/__init__.py）应被正确识别。"""
        (tmp_path / "pyproject.toml").write_text("")
        (tmp_path / "README.md").write_text("")
        (tmp_path / "LICENSE").write_text("")
        (tmp_path / ".gitignore").write_text("")

        nested = tmp_path / "pkg" / "sub"
        nested.mkdir(parents=True)
        (nested / "__init__.py").write_text("")

        errors = l1_files.run_file_check(tmp_path)
        ok = next(e for e in errors if e["type"] == "file_ok")
        assert "1" in ok["message"]


# ──────────────────────────────────────────────
# 错误条目结构
# ──────────────────────────────────────────────

class TestErrorStructure:
    """错误条目必须包含必要字段。"""

    def test_missing_file_has_type(self, incomplete_project: Path) -> None:
        """file_missing 错误必须有 type 字段。"""
        errors = l1_files.run_file_check(incomplete_project)
        missing = [e for e in errors if e["type"] == "file_missing"]
        assert len(missing) >= 1
        assert missing[0]["type"] == "file_missing"

    def test_missing_file_has_file_field(self, incomplete_project: Path) -> None:
        """file_missing 错误必须有 file 字段（文件名）。"""
        errors = l1_files.run_file_check(incomplete_project)
        missing = [e for e in errors if e["type"] == "file_missing"]
        assert all("file" in e for e in missing)

    def test_missing_file_has_message(self, incomplete_project: Path) -> None:
        """file_missing 错误必须有 message 字段。"""
        errors = l1_files.run_file_check(incomplete_project)
        missing = [e for e in errors if e["type"] == "file_missing"]
        assert all("message" in e and len(e["message"]) > 0 for e in missing)

    def test_file_ok_has_message(self, complete_project: Path) -> None:
        """file_ok 条目必须有 message 字段。"""
        errors = l1_files.run_file_check(complete_project)
        ok = [e for e in errors if e["type"] == "file_ok"]
        assert len(ok) >= 1
        assert "message" in ok[0]


# ──────────────────────────────────────────────
# 空项目
# ──────────────────────────────────────────────

class TestEmptyProject:
    """空项目行为。"""

    def test_empty_dir_has_no_py_files(self, tmp_path: Path) -> None:
        """空目录不应报 Python 文件相关错误。

        注意：run_file_check 会检查 pyproject.toml/README.md 等关键文件，
        空项目会报告 file_missing，但不应报 Python 语法错误。
        """
        errors = l1_files.run_file_check(tmp_path)
        syntax_errors = [e for e in errors if e["type"] == "syntax"]
        assert syntax_errors == []

    def test_returns_list(self, tmp_path: Path) -> None:
        """run_file_check 必须返回 list。"""
        result = l1_files.run_file_check(tmp_path)
        assert isinstance(result, list)
