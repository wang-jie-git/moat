"""Tree-sitter AST 感知模块测试"""
import tempfile
from pathlib import Path

import pytest

from moat.ast.tree_sitter import TreeSitterBuilder


@pytest.fixture
def sample_python_project():
    """创建临时 Python 项目"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        # 创建 Python 文件
        (project / "main.py").write_text(
            """
def foo():
    return bar()

def bar():
    return 42

def baz():
    result = foo()
    return result * 2
"""
        )

        yield project


@pytest.fixture
def sample_typescript_project():
    """创建临时 TypeScript 项目"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        # 创建 TypeScript 文件
        (project / "main.ts").write_text(
            """
function foo(): number {
    return bar();
}

function bar(): number {
    return 42;
}

function baz(): number {
    const result = foo();
    return result * 2;
}
"""
        )

        yield project


@pytest.fixture
def sample_multilang_project():
    """创建多语言项目"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        # Python 文件
        (project / "python_module.py").write_text(
            """
def python_func():
    return 42
"""
        )

        # TypeScript 文件
        (project / "ts_module.ts").write_text(
            """
function tsFunc(): number {
    return 42;
}
"""
        )

        yield project


class TestTreeSitterBuilder:
    """Tree-sitter Builder 测试"""

    def test_import_tree_sitter(self):
        """测试导入 tree-sitter"""
        try:
            import tree_sitter  # noqa: F401
        except ImportError:
            pytest.skip("tree-sitter 未安装")

    def test_build_python_project(self, sample_python_project):
        """测试构建 Python 项目骨架图"""
        try:
            import tree_sitter  # noqa: F401
        except ImportError:
            pytest.skip("tree-sitter 未安装")

        builder = TreeSitterBuilder(sample_python_project)
        skeleton = builder.build(languages=["python"])

        assert skeleton["stats"]["total_functions"] >= 3
        assert skeleton["stats"]["total_calls"] >= 2  # foo 调用 bar，baz 调用 foo

        # 检查语言统计
        assert "python" in skeleton["stats"]["by_language"]
        assert skeleton["stats"]["by_language"]["python"]["functions"] >= 3

    def test_build_typescript_project(self, sample_typescript_project):
        """测试构建 TypeScript 项目骨架图"""
        try:
            import tree_sitter  # noqa: F401
        except ImportError:
            pytest.skip("tree-sitter 未安装")

        builder = TreeSitterBuilder(sample_typescript_project)
        skeleton = builder.build(languages=["typescript"])

        assert skeleton["stats"]["total_functions"] >= 3
        assert skeleton["stats"]["total_calls"] >= 2  # 至少 foo 调用 bar

        # 检查语言统计
        assert "typescript" in skeleton["stats"]["by_language"]
        assert skeleton["stats"]["by_language"]["typescript"]["functions"] >= 3

    def test_auto_detect_languages(self, sample_multilang_project):
        """测试自动检测项目语言"""
        try:
            import tree_sitter  # noqa: F401
        except ImportError:
            pytest.skip("tree-sitter 未安装")

        builder = TreeSitterBuilder(sample_multilang_project)
        languages = builder._detect_languages()

        assert "python" in languages
        assert "typescript" in languages

    def test_build_multilang_project(self, sample_multilang_project):
        """测试构建多语言项目"""
        try:
            import tree_sitter  # noqa: F401
        except ImportError:
            pytest.skip("tree-sitter 未安装")

        builder = TreeSitterBuilder(sample_multilang_project)
        skeleton = builder.build()  # 自动检测

        assert skeleton["stats"]["total_functions"] >= 2
        assert "python" in skeleton["stats"]["by_language"]
        assert "typescript" in skeleton["stats"]["by_language"]

    def test_function_names_extracted(self, sample_python_project):
        """测试函数名提取"""
        try:
            import tree_sitter  # noqa: F401
        except ImportError:
            pytest.skip("tree-sitter 未安装")

        builder = TreeSitterBuilder(sample_python_project)
        builder.build(languages=["python"])

        func_names = [f["name"] for f in builder.functions.values()]
        assert "foo" in func_names
        assert "bar" in func_names
        assert "baz" in func_names

    def test_call_graph_built(self, sample_python_project):
        """测试调用图构建"""
        try:
            import tree_sitter  # noqa: F401
        except ImportError:
            pytest.skip("tree-sitter 未安装")

        builder = TreeSitterBuilder(sample_python_project)
        builder.build(languages=["python"])

        # 检查 foo 被 baz 调用
        foo_callers = builder.reverse_graph.get("foo", [])
        assert len(foo_callers) >= 1
        assert any("baz" in caller for caller in foo_callers)

    def test_to_json_serializable(self, sample_python_project):
        """测试 JSON 序列化"""
        try:
            import tree_sitter  # noqa: F401
        except ImportError:
            pytest.skip("tree-sitter 未安装")

        builder = TreeSitterBuilder(sample_python_project)
        skeleton = builder.build(languages=["python"])

        json_str = builder.to_json()
        assert isinstance(json_str, str)

        # 可以解析回 JSON
        import json

        parsed = json.loads(json_str)
        assert "functions" in parsed
        assert "call_graph" in parsed
        assert "stats" in parsed

    def test_convenience_function(self, sample_python_project):
        """测试便捷函数"""
        try:
            import tree_sitter  # noqa: F401
        except ImportError:
            pytest.skip("tree-sitter 未安装")

        from moat.ast.tree_sitter import build_multilang_skeleton

        skeleton = build_multilang_skeleton(sample_python_project, languages=["python"])
        assert skeleton["stats"]["total_functions"] >= 3
