"""L1 子系统检查测试

l1_subsystems.py 扫描文件名含 manager/engine/bridge/handler/service/provider/agent
关键词的模块，验证其核心类能否被 import。

关键发现：
  - 类必须包含 "(" → `class Foo(object):` 才能被发现
  - 子系统名第三个位置返回类名

测试策略：临时项目 + monkeypatch.syspath_prepend + 参数化测试。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from moat.checks import l1_subsystems


# ──────────────────────────────────────────────
# _discover_subsystems() - 参数化测试
# ──────────────────────────────────────────────

KEYWORD_TEST_CASES = [
    ("user_manager", "UserManager", "manager"),
    ("query_engine", "QueryEngine", "engine"),
    ("memory_bridge", "MemoryBridge", "bridge"),
    ("error_handler", "ErrorHandler", "handler"),
    ("auth_service", "AuthService", "service"),
    ("llm_provider", "LLMProvider", "provider"),
]


class TestDiscoverSubsystems:
    """测试 _discover_subsystems() 的发现能力。"""

    @pytest.mark.parametrize("filename,class_name,keyword", KEYWORD_TEST_CASES)
    def test_discovers_keyword_file(self, tmp_path: Path, filename: str, class_name: str, keyword: str) -> None:
        """文件名含关键词的模块应被识别（参数化覆盖 6 种关键词）。"""
        (tmp_path / f"{filename}.py").write_text(
            f"class {class_name}(object):\n    def __init__(self): pass\n"
        )
        result = l1_subsystems._discover_subsystems(tmp_path)
        assert len(result) >= 1, f"应发现 {filename}"
        _, _, discovered_cls, _ = result[0]  # 4 元组：(name, module_path, class_name, file_path)
        assert discovered_cls == class_name

    def test_ignores_non_keyword_files(self, tmp_path: Path) -> None:
        """不含关键词的文件不应被识别。"""
        (tmp_path / "plain.py").write_text("class Plain(object):\n    pass\n")
        result = l1_subsystems._discover_subsystems(tmp_path)
        assert result == []

    def test_skips_venv(self, tmp_path: Path) -> None:
        """应跳过 .venv 目录。"""
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "session_manager.py").write_text("class SM(object):\n    pass\n")
        result = l1_subsystems._discover_subsystems(tmp_path)
        assert not any("session_manager" in s.lower() for s, _, _, _ in result)  # 4 元组

    def test_returns_tuples(self, tmp_path: Path) -> None:
        """返回格式应为 (name, module_path, class_name, file_path)。"""
        (tmp_path / "test_agent.py").write_text("class TestAgent(object):\n    pass\n")
        result = l1_subsystems._discover_subsystems(tmp_path)
        assert len(result) >= 1
        name, mod_path, cls_name, file_path = result[0]  # 4 元组
        assert all(isinstance(v, (str, Path)) for v in (name, mod_path, cls_name, file_path))

    def test_empty_project(self, tmp_path: Path) -> None:
        """空项目应返回空列表。"""
        assert l1_subsystems._discover_subsystems(tmp_path) == []


# ──────────────────────────────────────────────
# run_subsystems_check()
# ──────────────────────────────────────────────

class TestSubsystemImportCheck:
    """测试 run_subsystems_check()。"""

    @staticmethod
    def _setup_project(base: Path) -> None:
        """在 base 目录中创建多个子系统文件。"""
        (base / "core").mkdir(exist_ok=True)
        (base / "core" / "__init__.py").write_text("")
        (base / "core" / "session_manager.py").write_text(
            "class SessionManager(object):\n    def __init__(self): pass\n"
        )
        (base / "core" / "payment_engine.py").write_text(
            "class PaymentEngine(object):\n    def __init__(self): pass\n"
        )

    def test_successful_import_reports_ok(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """成功导入的子系统应报告 subsystem_ok。"""
        self._setup_project(tmp_path)
        monkeypatch.syspath_prepend(str(tmp_path))
        errors = l1_subsystems.run_subsystems_check(tmp_path)
        ok = [e for e in errors if e["type"] == "subsystem_ok"]
        assert len(ok) >= 1

    def test_no_import_failures(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """所有子系统成功时应无 import_failed 错误。"""
        self._setup_project(tmp_path)
        monkeypatch.syspath_prepend(str(tmp_path))
        errors = l1_subsystems.run_subsystems_check(tmp_path)
        assert not any(e["type"] == "subsystem_import_failed" for e in errors)

    def test_import_failure_reported(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """import 失败应报告 subsystem_import_failed。"""
        (tmp_path / "broken_handler.py").write_text(
            "import nonexistent_dep_xyz\n\nclass BrokenHandler(object):\n    def __init__(self): pass\n"
        )
        monkeypatch.syspath_prepend(str(tmp_path))
        errors = l1_subsystems.run_subsystems_check(tmp_path)
        fails = [e for e in errors if e["type"] == "subsystem_import_failed"]
        assert len(fails) >= 1

    def test_error_level_is_l1(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """所有错误必须标记为 L1。"""
        self._setup_project(tmp_path)
        monkeypatch.syspath_prepend(str(tmp_path))
        errors = l1_subsystems.run_subsystems_check(tmp_path)
        assert all(e["level"] == "L1" for e in errors)

    def test_error_has_required_fields(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """所有错误必须有 file、message、level、type 字段。"""
        self._setup_project(tmp_path)
        monkeypatch.syspath_prepend(str(tmp_path))
        errors = l1_subsystems.run_subsystems_check(tmp_path)
        for e in errors:
            assert "file" in e and "message" in e and "level" in e and "type" in e

    def test_empty_project_no_crash(self, tmp_path: Path) -> None:
        """空项目不应崩溃。"""
        errors = l1_subsystems.run_subsystems_check(tmp_path)
        assert errors == []

    def test_returns_list(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """run_subsystems_check 必须返回 list。"""
        self._setup_project(tmp_path)
        monkeypatch.syspath_prepend(str(tmp_path))
        result = l1_subsystems.run_subsystems_check(tmp_path)
        assert isinstance(result, list)

    def test_skips_check_class_with_project_root(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """需要 project_root/config 的类应被跳过，不报错。"""
        (tmp_path / "checker.py").write_text(
            "class MyCheck(object):\n    def __init__(self, project_root, config=None):\n        pass\n"
        )
        monkeypatch.syspath_prepend(str(tmp_path))
        errors = l1_subsystems.run_subsystems_check(tmp_path)
        assert not any(e["type"] == "subsystem_import_failed" for e in errors)
