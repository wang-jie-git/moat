"""L1 核心模块检查测试（动态 import 验证）

l1_modules.py 通过 importlib.import_module + inspect 验证每个核心模块能否实例化。

关键发现（来自源码分析）：
  _discover_core_modules() 的类匹配条件：`line.startswith("class ") and "(" in line`
  → 类定义必须包含 "(" 才会被识别，纯 `class MyClass:`（无括号）会被跳过

测试策略：临时项目 + sys.path 注入，类定义使用 `class X(Base):` 格式。
"""
from __future__ import annotations

import sys
import importlib
from pathlib import Path
from textwrap import dedent

import pytest

from tests.fixtures import projects
from moat.checks import l1_modules


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture()
def temp_project(tmp_path: Path) -> Path:
    """返回包含有效 Python 文件的临时项目根目录。"""
    return projects.create_temp_project()


@pytest.fixture()
def project_in_syspath(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """临时项目已注入 sys.path，类使用 (object) 格式（源码匹配规则要求）。"""
    p = projects.create_temp_project()
    # 修复 fixture 中的类定义（源码要求 class X(object): 才匹配 "(" in line）
    (p / "core" / "auth.py").write_text(
        "class AuthService(object):\n    def __init__(self): pass\n"
    )
    (p / "core" / "payment.py").write_text(
        "class PaymentService(object):\n    def __init__(self): pass\n"
    )
    monkeypatch.syspath_prepend(str(p))
    return p


# ──────────────────────────────────────────────
# _discover_core_modules()
# ──────────────────────────────────────────────

class TestDiscoverCoreModules:
    """测试 _discover_core_modules() 的模块发现能力。"""

    def test_discovers_classes_with_base(self, tmp_path: Path) -> None:
        """含 (Base) 的类定义应被发现。"""
        (tmp_path / "mymod.py").write_text("class MyClass(object):\n    def __init__(self): pass\n")

        modules = l1_modules._discover_core_modules(tmp_path)
        assert len(modules) >= 1
        assert modules[0][1] == "MyClass"

    def test_skips_class_without_parens(self, tmp_path: Path) -> None:
        """纯 `class Foo:`（无括号）不被识别。"""
        (tmp_path / "noparen.py").write_text("class NoParen:\n    def __init__(self): pass\n")

        modules = l1_modules._discover_core_modules(tmp_path)
        assert not any("noparen" in m for m, _ in modules)

    def test_returns_module_and_class_name(self, tmp_path: Path) -> None:
        """返回格式应为 (module_name, class_name)。"""
        (tmp_path / "my_mod.py").write_text("class Handler(object):\n    def __init__(self): pass\n")

        modules = l1_modules._discover_core_modules(tmp_path)
        mod_name, class_name = modules[0]
        assert isinstance(mod_name, str)
        assert class_name == "Handler"

    def test_skips_venv(self, tmp_path: Path) -> None:
        """应跳过 .venv 目录。"""
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "venv_mod.py").write_text("class Foo(object):\n    pass\n")

        modules = l1_modules._discover_core_modules(tmp_path)
        assert not any("venv_mod" in m for m, _ in modules)

    def test_skips_private_modules(self, tmp_path: Path) -> None:
        """应跳过 _ 开头的私有模块。"""
        (tmp_path / "_private.py").write_text("class Hidden(object):\n    pass\n")

        modules = l1_modules._discover_core_modules(tmp_path)
        assert not any("_private" in m for m, _ in modules)

    def test_limits_to_50(self, tmp_path: Path) -> None:
        """最多返回 50 个模块。"""
        for i in range(60):
            (tmp_path / f"mod_{i}.py").write_text(f"class C{i}(object):\n    pass\n")

        modules = l1_modules._discover_core_modules(tmp_path)
        assert len(modules) <= 50

    def test_nested_package(self, tmp_path: Path) -> None:
        """嵌套包中的模块应被正确发现。"""
        sub = tmp_path / "pkg" / "sub"
        sub.mkdir(parents=True)
        (sub / "deep.py").write_text("class Deep(object):\n    pass\n")

        modules = l1_modules._discover_core_modules(tmp_path)
        assert any("deep" in m for m, _ in modules)

    def test_no_classes_returns_empty(self, tmp_path: Path) -> None:
        """只含函数的文件不返回条目。"""
        (tmp_path / "functions.py").write_text("def foo():\n    pass\n")

        modules = l1_modules._discover_core_modules(tmp_path)
        assert modules == []

    def test_multiple_classes_first_returned(self, tmp_path: Path) -> None:
        """多类文件只返回第一个类名。"""
        (tmp_path / "multi.py").write_text(
            "class First(object):\n    pass\nclass Second(object):\n    pass\n"
        )

        modules = l1_modules._discover_core_modules(tmp_path)
        assert modules[0][1] == "First"


# ──────────────────────────────────────────────
# run_modules_check() — import + 实例化
# ──────────────────────────────────────────────

class TestModuleImportCheck:
    """测试 run_modules_check() 的 import + 实例化逻辑。"""

    def test_no_errors_for_valid_class(
        self, project_in_syspath: Path
    ) -> None:
        """无参可实例化的有效模块不应有 import_failed。"""
        errors = l1_modules.run_modules_check(project_in_syspath)
        import_errors = [e for e in errors if e["type"] == "module_import_failed"]
        assert import_errors == []

    def test_instantiation_success_reports_ok(
        self, project_in_syspath: Path
    ) -> None:
        """成功实例化应报告 type=module_ok。"""
        errors = l1_modules.run_modules_check(project_in_syspath)
        ok = [e for e in errors if e["type"] == "module_ok"]
        assert len(ok) >= 1

    def test_instantiation_failure_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """构造函数抛异常应报告 module_instantiation_failed。"""
        (tmp_path / "bad_init.py").write_text(
            "class BadInit(object):\n    def __init__(self):\n        raise RuntimeError('boom')\n"
        )
        monkeypatch.syspath_prepend(str(tmp_path))

        errors = l1_modules.run_modules_check(tmp_path)
        fail = [e for e in errors if e["type"] == "module_instantiation_failed"]
        assert len(fail) >= 1

    def test_syntax_error_file_does_not_crash(
        self, project_in_syspath: Path
    ) -> None:
        """语法错误文件不应导致崩溃。"""
        (project_in_syspath / "syntax_err.py").write_text("def broken(:\n    pass\n")

        errors = l1_modules.run_modules_check(project_in_syspath)
        assert isinstance(errors, list)

    def test_skips_check_class_with_project_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """需要 project_root/config 的类应被跳过（module_skipped_ok）。"""
        (tmp_path / "mycheck.py").write_text(
            "class MyCheck(object):\n    def __init__(self, project_root, config=None):\n        pass\n"
        )
        monkeypatch.syspath_prepend(str(tmp_path))

        errors = l1_modules.run_modules_check(tmp_path)
        skipped = [e for e in errors if e["type"] == "module_skipped_ok"]
        assert len(skipped) >= 1

    def test_skips_pydantic_basemodel(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Pydantic BaseModel 应被跳过（module_skipped_ok）。"""
        (tmp_path / "mymodel.py").write_text(
            dedent("""\
                try:
                    from pydantic import BaseModel
                except ImportError:
                    BaseModel = object
                class MyModel(BaseModel):
                    name: str = "default"
            """)
        )
        monkeypatch.syspath_prepend(str(tmp_path))

        errors = l1_modules.run_modules_check(tmp_path)
        skipped = [e for e in errors if e["type"] == "module_skipped_ok"]
        assert len(skipped) >= 1

    def test_error_level_is_l1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """所有错误必须标记为 L1。"""
        (tmp_path / "bad.py").write_text(
            "class BadInit(object):\n    def __init__(self): raise RuntimeError()\n"
        )
        monkeypatch.syspath_prepend(str(tmp_path))

        errors = l1_modules.run_modules_check(tmp_path)
        assert all(e["level"] == "L1" for e in errors)

    def test_error_has_required_fields(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """所有错误条目必须有 file 和 message 字段。"""
        (tmp_path / "bad.py").write_text(
            "class BadInit(object):\n    def __init__(self): raise RuntimeError()\n"
        )
        monkeypatch.syspath_prepend(str(tmp_path))

        errors = l1_modules.run_modules_check(tmp_path)
        for e in errors:
            assert "file" in e
            assert "message" in e
            assert "level" in e
            assert "type" in e

    def test_multiple_modules_all_checked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """多个模块应全部被检查。"""
        (tmp_path / "mod_a.py").write_text("class A(object):\n    def __init__(self): pass\n")
        (tmp_path / "mod_b.py").write_text("class B(object):\n    def __init__(self): pass\n")
        (tmp_path / "mod_c_bad.py").write_text(
            "class CBad(object):\n    def __init__(self): raise RuntimeError()\n"
        )
        monkeypatch.syspath_prepend(str(tmp_path))

        errors = l1_modules.run_modules_check(tmp_path)
        assert len(errors) >= 3

    def test_returns_list(self, tmp_path: Path) -> None:
        """run_modules_check 必须返回 list。"""
        result = l1_modules.run_modules_check(tmp_path)
        assert isinstance(result, list)
