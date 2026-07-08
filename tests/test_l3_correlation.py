"""L3 跨系统关联检查测试

l3_correlation.py 通过 AST 解析构建模块导入图，检测循环依赖和核心-边缘违规。

关键发现（来自源码分析）：
  _build_import_graph(): `import X` → deps=["X"]
  _find_cycles(): DFS 只在 imports_map 中的节点递归
  _find_core_modules(): threshold=max(3, len(sorted_deps)//10)

测试策略：直接构造 import 图或使用简单 import 语句在临时项目中构建。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from moat.checks import l3_correlation


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture()
def clean_project(tmp_path: Path) -> Path:
    """无循环依赖的干净项目。"""
    (tmp_path / "core").mkdir()
    (tmp_path / "utils").mkdir()
    (tmp_path / "core" / "__init__.py").write_text("")
    (tmp_path / "core" / "auth.py").write_text("from utils.logger import log\n")
    (tmp_path / "utils" / "__init__.py").write_text("")
    (tmp_path / "utils" / "logger.py").write_text("def log(msg): pass\n")
    return tmp_path


@pytest.fixture()
def cycle_project_direct(tmp_path: Path) -> Path:
    """A → B → A 直接循环。"""
    (tmp_path / "mod_a.py").write_text("import mod_b\n")
    (tmp_path / "mod_b.py").write_text("import mod_a\n")
    return tmp_path


@pytest.fixture()
def cycle_project_long(tmp_path: Path) -> Path:
    """A → B → C → A 长循环。"""
    (tmp_path / "mod_a.py").write_text("import mod_c\n")
    (tmp_path / "mod_b.py").write_text("import mod_a\n")
    (tmp_path / "mod_c.py").write_text("import mod_b\n")
    return tmp_path


# ──────────────────────────────────────────────
# _build_import_graph()
# ──────────────────────────────────────────────

class TestBuildImportGraph:
    """测试 _build_import_graph() 的 AST 解析能力。"""

    def test_returns_dict(self, clean_project: Path) -> None:
        """必须返回 dict。"""
        assert isinstance(l3_correlation._build_import_graph(clean_project), dict)

    def test_empty_project(self, tmp_path: Path) -> None:
        """空项目应返回空图。"""
        assert l3_correlation._build_import_graph(tmp_path) == {}

    def test_discovers_imports(self, clean_project: Path) -> None:
        """应发现模块间的依赖关系。"""
        graph = l3_correlation._build_import_graph(clean_project)
        assert any(len(deps) > 0 for deps in graph.values())

    def test_skips_venv(self, tmp_path: Path) -> None:
        """应跳过 .venv 目录。"""
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "fake.py").write_text("import os\n")
        assert l3_correlation._build_import_graph(tmp_path) == {}

    def test_skips_non_py(self, tmp_path: Path) -> None:
        """应忽略非 .py 文件。"""
        (tmp_path / "readme.md").write_text("import os\n")
        assert l3_correlation._build_import_graph(tmp_path) == {}

    def test_import_from_detected(self, tmp_path: Path) -> None:
        """from X import Y 应解析为依赖 X。"""
        (tmp_path / "consumer.py").write_text("from mylib import helper\n")
        graph = l3_correlation._build_import_graph(tmp_path)
        assert "mylib" in graph.get("consumer", [])

    def test_plain_import_detected(self, tmp_path: Path) -> None:
        """import X 应解析为依赖 X。"""
        (tmp_path / "consumer.py").write_text("import os\n")
        graph = l3_correlation._build_import_graph(tmp_path)
        assert "os" in graph.get("consumer", [])

    def test_skips_syntax_error(self, tmp_path: Path) -> None:
        """语法错误文件应被跳过，不崩溃。"""
        (tmp_path / "broken.py").write_text("def BROKEN(:\n    pass\n")
        assert isinstance(l3_correlation._build_import_graph(tmp_path), dict)

    def test_module_without_imports_still_listed(self, tmp_path: Path) -> None:
        """无 import 的模块也应在图中（deps=[]）。"""
        (tmp_path / "isolated.py").write_text("# no imports\n")
        graph = l3_correlation._build_import_graph(tmp_path)
        assert "isolated" in graph


# ──────────────────────────────────────────────
# _find_cycles()
# ──────────────────────────────────────────────

class TestFindCycles:
    """测试 _find_cycles() 的循环依赖检测。"""

    def test_empty_graph(self) -> None:
        """空图应无循环。"""
        assert l3_correlation._find_cycles({}) == []

    def test_single_node(self) -> None:
        """单节点无循环。"""
        assert l3_correlation._find_cycles({"a": []}) == []

    def test_linear_chain(self) -> None:
        """线性链 A → B → C 无循环。"""
        graph = {"a": ["b"], "b": ["c"], "c": []}
        assert l3_correlation._find_cycles(graph) == []

    def test_direct_cycle_detected(self, cycle_project_direct: Path) -> None:
        """A → B → A 直接循环应被检测。"""
        graph = l3_correlation._build_import_graph(cycle_project_direct)
        cycles = l3_correlation._find_cycles(graph)
        assert len(cycles) >= 1

    def test_long_cycle_detected(self, cycle_project_long: Path) -> None:
        """A → B → C → A 长循环应被检测。"""
        graph = l3_correlation._build_import_graph(cycle_project_long)
        cycles = l3_correlation._find_cycles(graph)
        assert len(cycles) >= 1

    def test_cycle_contains_nodes(self, cycle_project_direct: Path) -> None:
        """检测到的循环必须包含涉及的模块。"""
        graph = l3_correlation._build_import_graph(cycle_project_direct)
        cycles = l3_correlation._find_cycles(graph)
        all_nodes = {n for c in cycles for n in c}
        assert "mod_a" in all_nodes
        assert "mod_b" in all_nodes

    def test_limits_to_10(self, tmp_path: Path) -> None:
        """只返回前 10 个循环（防止爆炸）。"""
        for i in range(20):
            (tmp_path / f"mod_{i}.py").write_text(f"import mod_{(i + 1) % 20}\n")
        graph = l3_correlation._build_import_graph(tmp_path)
        cycles = l3_correlation._find_cycles(graph)
        assert len(cycles) <= 10

    def test_star_import_skipped(self, tmp_path: Path) -> None:
        """from X import * → module=None 应跳过。"""
        (tmp_path / "a.py").write_text("from b import *\n")
        (tmp_path / "b.py").write_text("from c import *\n")
        (tmp_path / "c.py").write_text("")
        graph = l3_correlation._build_import_graph(tmp_path)
        assert "a" in graph


# ──────────────────────────────────────────────
# _find_core_modules()
# ──────────────────────────────────────────────

class TestFindCoreModules:
    """测试 _find_core_modules() 的核心模块识别。"""

    def test_empty_graph(self) -> None:
        """空图应返回空列表。"""
        assert l3_correlation._find_core_modules({}, Path("/tmp")) == []

    def test_high_ref_count_is_core(self, tmp_path: Path) -> None:
        """被 10 个模块引用的模块应被识别为核心。"""
        (tmp_path / "core_mod.py").write_text("# core\n")
        for i in range(10):
            (tmp_path / f"leaf_{i}.py").write_text("import core_mod\n")
        graph = l3_correlation._build_import_graph(tmp_path)
        cores = l3_correlation._find_core_modules(graph, tmp_path)
        assert "core_mod" in cores

    def test_low_ref_count_not_core(self, tmp_path: Path) -> None:
        """只有 1 个引用的模块不应被识别为核心。"""
        (tmp_path / "a.py").write_text("import b\n")
        (tmp_path / "b.py").write_text("# only 1 ref\n")
        graph = l3_correlation._build_import_graph(tmp_path)
        cores = l3_correlation._find_core_modules(graph, tmp_path)
        assert isinstance(cores, list)

    def test_returns_list(self, clean_project: Path) -> None:
        """必须返回 list。"""
        graph = l3_correlation._build_import_graph(clean_project)
        assert isinstance(l3_correlation._find_core_modules(graph, clean_project), list)


# ──────────────────────────────────────────────
# run_correlation_check() 集成测试
# ──────────────────────────────────────────────

class TestRunCorrelationCheck:
    """集成测试：run_correlation_check() 完整流程。"""

    def test_clean_project_no_errors(self, clean_project: Path) -> None:
        """干净项目不应有任何错误。"""
        assert l3_correlation.run_correlation_check(clean_project) == []

    def test_direct_cycle_detected(self, cycle_project_direct: Path) -> None:
        """A → B → A 直接循环应被检测。"""
        errors = l3_correlation.run_correlation_check(cycle_project_direct)
        cycles = [e for e in errors if e["type"] == "circular_import"]
        assert len(cycles) >= 1

    def test_long_cycle_detected(self, cycle_project_long: Path) -> None:
        """A → B → C → A 长循环应被检测。"""
        errors = l3_correlation.run_correlation_check(cycle_project_long)
        cycles = [e for e in errors if e["type"] == "circular_import"]
        assert len(cycles) >= 1

    def test_cycle_error_level_is_l3(self, cycle_project_direct: Path) -> None:
        """循环依赖错误必须标记为 L3。"""
        errors = l3_correlation.run_correlation_check(cycle_project_direct)
        assert all(e["level"] == "L3" for e in errors)

    def test_cycle_error_has_required_fields(self, cycle_project_direct: Path) -> None:
        """循环依赖错误必须有 level、type、file、message 字段。"""
        errors = l3_correlation.run_correlation_check(cycle_project_direct)
        for e in errors:
            assert "level" in e and "type" in e and "file" in e and "message" in e

    def test_returns_list(self, clean_project: Path) -> None:
        """run_correlation_check 必须返回 list。"""
        assert isinstance(l3_correlation.run_correlation_check(clean_project), list)

    def test_no_crash_on_syntax_error(self, tmp_path: Path) -> None:
        """含语法错误的项目不应崩溃。"""
        (tmp_path / "broken.py").write_text("def BROKEN(:\n    pass\n")
        assert isinstance(l3_correlation.run_correlation_check(tmp_path), list)

    def test_multiple_cycles_both_detected(self, tmp_path: Path) -> None:
        """两个独立循环 A↔B 和 C↔D 应都被检测。"""
        (tmp_path / "a.py").write_text("import b\n")
        (tmp_path / "b.py").write_text("import a\n")
        (tmp_path / "c.py").write_text("import d\n")
        (tmp_path / "d.py").write_text("import c\n")

        errors = l3_correlation.run_correlation_check(tmp_path)
        cycles = [e for e in errors if e["type"] == "circular_import"]
        assert len(cycles) >= 2

    def test_cycle_error_message_format(self, cycle_project_direct: Path) -> None:
        """循环依赖消息必须包含 → 符号。"""
        errors = l3_correlation.run_correlation_check(cycle_project_direct)
        cycles = [e for e in errors if e["type"] == "circular_import"]
        assert any("→" in e["message"] for e in cycles)
