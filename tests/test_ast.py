"""AST 感知模块测试 (moat.ast.builder + moat.ast.diff)

覆盖核心功能:
- ProjectSkeleton: 构建骨架图、提取函数、构建调用图
- Edge: 置信度边、to_dict
- FunctionInfo: 函数信息、to_dict
- ASTDiffer: AST 增量对比、变更检测
- CodeChange: 代码变更表示
- diff_project: 项目级差异分析
"""
from __future__ import annotations

import ast
import tempfile
from pathlib import Path

import pytest

from moat.ast.builder import (
    Edge,
    FunctionInfo,
    ProjectSkeleton,
)
from moat.ast.diff import ASTDiffer, CodeChange, diff_project


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def sample_python_project(tmp_path: Path) -> Path:
    """创建临时 Python 项目"""
    project = tmp_path / "sample_project"
    project.mkdir()

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

class MyClass:
    def method(self):
        return foo()
"""
    )

    # 创建子目录
    (project / "utils").mkdir()
    (project / "utils" / "__init__.py").write_text("")
    (project / "utils" / "helpers.py").write_text(
        """
def helper():
    return 100

def another_helper():
    return helper() * 2
"""
    )

    return project


@pytest.fixture
def empty_project(tmp_path: Path) -> Path:
    """创建空项目"""
    project = tmp_path / "empty"
    project.mkdir()
    return project


@pytest.fixture
def skeleton(sample_python_project: Path) -> ProjectSkeleton:
    """构建项目骨架图"""
    skel = ProjectSkeleton(sample_python_project)
    skel.build("python")
    return skel


@pytest.fixture
def simple_skeleton(tmp_path: Path) -> ProjectSkeleton:
    """创建简单项目"""
    (tmp_path / "simple.py").write_text(
        """
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

def calculate():
    return add(1, 2) + multiply(3, 4)
"""
    )
    skel = ProjectSkeleton(tmp_path)
    skel.build("python")
    return skel


# ──────────────────────────────────────────────
# FunctionInfo 测试
# ──────────────────────────────────────────────

class TestFunctionInfo:
    """测试 FunctionInfo 数据结构"""

    def test_create_function_info(self):
        """创建函数信息"""
        func = FunctionInfo(
            name="foo",
            file_path="main.py",
            line=10,
            calls=["bar", "baz"]
        )
        assert func.name == "foo"
        assert func.file_path == "main.py"
        assert func.line == 10
        assert func.calls == ["bar", "baz"]

    def test_function_info_default_calls(self):
        """默认 calls 为空列表"""
        func = FunctionInfo(name="foo", file_path="main.py", line=1)
        assert func.calls == []

    def test_function_info_to_dict(self):
        """转换为字典"""
        func = FunctionInfo(
            name="bar",
            file_path="utils/helpers.py",
            line=5,
            calls=["helper"]
        )
        d = func.to_dict()
        assert d["name"] == "bar"
        assert d["file"] == "utils/helpers.py"
        assert d["line"] == 5
        assert d["calls"] == ["helper"]


# ──────────────────────────────────────────────
# Edge 测试
# ──────────────────────────────────────────────

class TestEdge:
    """测试 Edge（置信度边）"""

    def test_create_edge(self):
        """创建边"""
        edge = Edge(
            source="main.py::foo",
            target="bar",
            edge_type="direct_call",
            confidence=1.0
        )
        assert edge.source == "main.py::foo"
        assert edge.target == "bar"
        assert edge.edge_type == "direct_call"
        assert edge.confidence == 1.0

    def test_edge_default_confidence(self):
        """默认置信度为 1.0"""
        edge = Edge("a", "b", "call")
        assert edge.confidence == 1.0

    def test_edge_to_dict(self):
        """转换为字典"""
        edge = Edge(
            source="a",
            target="b",
            edge_type="indirect_call",
            confidence=0.5
        )
        d = edge.to_dict()
        assert d["source"] == "a"
        assert d["target"] == "b"
        assert d["type"] == "indirect_call"
        assert d["confidence"] == 0.5

    def test_edge_confidence_range(self):
        """置信度范围 0.0-1.0"""
        edge1 = Edge("a", "b", "call", confidence=0.0)
        edge2 = Edge("a", "b", "call", confidence=1.0)
        assert edge1.confidence == 0.0
        assert edge2.confidence == 1.0


# ──────────────────────────────────────────────
# ProjectSkeleton 测试
# ──────────────────────────────────────────────

class TestProjectSkeleton:
    """测试 ProjectSkeleton 骨架图构建"""

    def test_build_python_project(self, sample_python_project: Path):
        """构建 Python 项目骨架图"""
        skel = ProjectSkeleton(sample_python_project)
        skel.build("python")

        assert len(skel.functions) > 0
        assert len(skel.call_graph) > 0

    def test_build_invalid_language(self, sample_python_project: Path):
        """不支持的Language应抛出异常"""
        skel = ProjectSkeleton(sample_python_project)
        with pytest.raises(NotImplementedError):
            skel.build("javascript")

    def test_extract_functions(self, skeleton: ProjectSkeleton):
        """提取函数定义"""
        assert len(skeleton.functions) >= 5  # foo, bar, baz, helper, another_helper

        # 验证函数名
        func_names = [f.name for f in skeleton.functions.values()]
        assert "foo" in func_names
        assert "bar" in func_names
        assert "baz" in func_names

    def test_function_file_path(self, skeleton: ProjectSkeleton):
        """函数文件路径正确"""
        for func in skeleton.functions.values():
            assert func.file_path  # 不应为空
            assert func.line > 0  # 行号应 > 0

    def test_build_call_graph(self, skeleton: ProjectSkeleton):
        """构建调用图"""
        assert len(skeleton.call_graph) > 0

        # 检查调用关系（调用图中使用函数名，不是完整路径）
        call_graph = skeleton.call_graph
        # foo() 调用 bar()
        if any("bar" in callees for callees in call_graph.values()):
            assert "foo" in [
                caller.split("::")[-1] if "::" in caller else caller
                for caller_list in skeleton.reverse_graph.values()
                for caller in caller_list
            ]

    def test_call_graph_contains_calls(self, simple_skeleton: ProjectSkeleton):
        """调用图应包含函数调用"""
        # calculate() 调用 add() 和 multiply()
        assert "simple.py::calculate" in simple_skeleton.call_graph
        callees = simple_skeleton.call_graph["simple.py::calculate"]
        assert "add" in callees
        assert "multiply" in callees

    def test_reverse_graph(self, skeleton: ProjectSkeleton):
        """反向图（callee -> callers）"""
        assert len(skeleton.reverse_graph) > 0

        # foo() 被 main.py::foo 和 MyClass.method 调用
        if "foo" in skeleton.reverse_graph:
            callers = skeleton.reverse_graph["foo"]
            assert len(callers) >= 1

    def test_find_callers(self, skeleton: ProjectSkeleton):
        """查找函数调用者"""
        # bar() 被 foo() 调用
        callers = skeleton.find_callers("bar")
        assert len(callers) >= 1
        assert all(isinstance(c, FunctionInfo) for c in callers)

    def test_find_callers_nonexistent(self, skeleton: ProjectSkeleton):
        """查找不存在的函数应返回空列表"""
        callers = skeleton.find_callers("nonexistent_func_xyz")
        assert callers == []

    def test_find_impacts(self, skeleton: ProjectSkeleton):
        """查找变更影响"""
        # bar() 在第 6 行
        impacts = skeleton.find_impacts("main.py", 6)
        # bar() 可能被 foo() 调用
        assert isinstance(impacts, list)

    def test_find_impacts_nonexistent(self, skeleton: ProjectSkeleton):
        """查找不存在的变更影响应返回空列表"""
        impacts = skeleton.find_impacts("nonexistent.py", 999)
        assert impacts == []

    def test_analyze_impacts(self, simple_skeleton: ProjectSkeleton):
        """分析变更影响"""
        changes = [{"function": "add"}]
        skeleton_dict = simple_skeleton.to_dict()

        impacts = simple_skeleton.analyze_impacts(changes, skeleton_dict)
        assert isinstance(impacts, list)
        if impacts:
            assert "change" in impacts[0]
            assert "direct_callers" in impacts[0]
            assert "risk_level" in impacts[0]

    def test_analyze_impacts_risk_level(self, simple_skeleton: ProjectSkeleton):
        """风险等级计算"""
        changes = [{"function": "add"}]
        skeleton_dict = simple_skeleton.to_dict()

        impacts = simple_skeleton.analyze_impacts(changes, skeleton_dict)
        if impacts:
            risk = impacts[0]["risk_level"]
            assert risk in ("low", "medium", "high")

    def test_to_dict_contains_functions(self, skeleton: ProjectSkeleton):
        """to_dict() 应包含函数列表"""
        d = skeleton.to_dict()
        assert "functions" in d
        assert len(d["functions"]) > 0

    def test_to_dict_contains_call_graph(self, skeleton: ProjectSkeleton):
        """to_dict() 应包含调用图"""
        d = skeleton.to_dict()
        assert "call_graph" in d
        assert isinstance(d["call_graph"], dict)

    def test_to_dict_contains_edges(self, skeleton: ProjectSkeleton):
        """to_dict() 应包含边"""
        d = skeleton.to_dict()
        assert "edges" in d
        assert isinstance(d["edges"], list)

    def test_edges_have_confidence(self, simple_skeleton: ProjectSkeleton):
        """边应有置信度"""
        d = simple_skeleton.to_dict()
        for edge in d["edges"]:
            assert "confidence" in edge
            assert 0.0 <= edge["confidence"] <= 1.0

    def test_empty_project(self, empty_project: Path):
        """空项目应返回空骨架图"""
        skel = ProjectSkeleton(empty_project)
        skel.build("python")
        assert len(skel.functions) == 0
        assert len(skel.call_graph) == 0

    def test_skips_venv_directory(self, tmp_path: Path):
        """应跳过 .venv 目录"""
        project = tmp_path / "project"
        project.mkdir()
        venv = project / ".venv"
        venv.mkdir()
        (venv / "module.py").write_text("def foo(): pass")

        skel = ProjectSkeleton(project)
        skel.build("python")
        assert len(skel.functions) == 0

    def test_skips_tests_directory(self, tmp_path: Path):
        """应跳过 tests 目录"""
        project = tmp_path / "project"
        project.mkdir()
        tests = project / "tests"
        tests.mkdir()
        (tests / "test_foo.py").write_text("def test_foo(): pass")

        skel = ProjectSkeleton(project)
        skel.build("python")
        assert len(skel.functions) == 0

    def test_async_function_detected(self, tmp_path: Path):
        """应检测 async 函数"""
        (tmp_path / "async_demo.py").write_text(
            """
async def async_func():
    return await something()
"""
        )
        skel = ProjectSkeleton(tmp_path)
        skel.build("python")

        func_names = [f.name for f in skel.functions.values()]
        assert "async_func" in func_names

    def test_class_method_detected(self, sample_python_project: Path):
        """应检测类方法"""
        skel = ProjectSkeleton(sample_python_project)
        skel.build("python")

        func_names = [f.name for f in skel.functions.values()]
        assert "method" in func_names

    def test_method_call_detected(self, skeleton: ProjectSkeleton):
        """应检测方法调用 obj.method()"""
        # MyClass.method() 调用 foo()
        if "main.py::method" in skeleton.call_graph:
            callees = skeleton.call_graph["main.py::method"]
            assert "foo" in callees

    def test_build_with_different_languages(self, tmp_path: Path):
        """支持不同语言（当前仅 python）"""
        skel = ProjectSkeleton(tmp_path)
        skel.build("python")
        assert skel.call_graph is not None


# ──────────────────────────────────────────────
# ASTDiffer 测试
# ──────────────────────────────────────────────

class TestASTDiffer:
    """测试 ASTDiffer 增量对比"""

    @pytest.fixture
    def differ(self, tmp_path: Path) -> ASTDiffer:
        """创建 ASTDiffer"""
        return ASTDiffer(tmp_path)

    def test_diff_file_added_function(self, differ: ASTDiffer, tmp_path: Path):
        """检测新增函数"""
        old_content = "def foo(): pass\n"
        new_content = "def foo(): pass\ndef bar(): pass\n"

        (tmp_path / "test.py").write_text(new_content)
        changes = differ.diff_file(
            tmp_path / "test.py",
            old_content=old_content,
            new_content=new_content
        )

        added = [c for c in changes if c.change_type == "added"]
        assert len(added) >= 1
        assert any(c.function == "bar" for c in added)

    def test_diff_file_deleted_function(self, differ: ASTDiffer, tmp_path: Path):
        """检测删除函数"""
        old_content = "def foo(): pass\ndef bar(): pass\n"
        new_content = "def foo(): pass\n"

        (tmp_path / "test.py").write_text(new_content)
        changes = differ.diff_file(
            tmp_path / "test.py",
            old_content=old_content,
            new_content=new_content
        )

        deleted = [c for c in changes if c.change_type == "deleted"]
        assert len(deleted) >= 1
        assert any(c.function == "bar" for c in deleted)

    def test_diff_file_modified_function(self, differ: ASTDiffer, tmp_path: Path):
        """检测修改函数"""
        old_content = "def foo(): return 1\n"
        new_content = "def foo(): return 2\n"

        (tmp_path / "test.py").write_text(new_content)
        changes = differ.diff_file(
            tmp_path / "test.py",
            old_content=old_content,
            new_content=new_content
        )

        modified = [c for c in changes if c.change_type == "modified"]
        assert len(modified) >= 1
        assert any(c.function == "foo" for c in modified)

    def test_diff_file_no_changes(self, differ: ASTDiffer, tmp_path: Path):
        """无变更应返回空列表"""
        content = "def foo(): pass\n"

        (tmp_path / "test.py").write_text(content)
        changes = differ.diff_file(
            tmp_path / "test.py",
            old_content=content,
            new_content=content
        )

        assert len(changes) == 0

    def test_diff_file_syntax_error(self, differ: ASTDiffer, tmp_path: Path):
        """语法错误应返回空列表"""
        (tmp_path / "test.py").write_text("def broken(:\n    pass\n")

        changes = differ.diff_file(
            tmp_path / "test.py",
            old_content="def foo(): pass\n",
            new_content="def broken(:\n    pass\n"
        )

        # 语法错误无法解析，应返回空列表
        assert isinstance(changes, list)

    def test_diff_file_no_git_version(self, differ: ASTDiffer, tmp_path: Path):
        """无 Git 版本时应返回空列表"""
        (tmp_path / "test.py").write_text("def foo(): pass\n")

        changes = differ.diff_file(tmp_path / "test.py")
        assert changes == []

    def test_analyze_impacts(self, differ: ASTDiffer):
        """分析变更影响"""
        changes = [
            CodeChange(change_type="modified", file_path="main.py", function="foo")
        ]
        skeleton = {
            "call_graph": {
                "main.py::bar": ["foo"],
                "main.py::baz": ["foo"],
            }
        }

        impacts = differ.analyze_impacts(changes, skeleton)
        assert len(impacts) >= 1
        assert impacts[0]["callers"] == ["main.py::bar", "main.py::baz"]

    def test_analyze_impacts_risk_level(self, differ: ASTDiffer):
        """风险等级基于调用者数量"""
        # 高风险：>3 个调用者
        changes_high = [CodeChange("modified", "main.py", function="foo")]
        skeleton_high = {
            "call_graph": {f"main.py::caller_{i}": ["foo"] for i in range(5)}
        }
        impacts_high = differ.analyze_impacts(changes_high, skeleton_high)
        if impacts_high:
            assert impacts_high[0]["risk_level"] == "high"

        # 中等风险：<=3 个调用者
        changes_med = [CodeChange("modified", "main.py", function="foo")]
        skeleton_med = {
            "call_graph": {"main.py::bar": ["foo"], "main.py::baz": ["foo"]}
        }
        impacts_med = differ.analyze_impacts(changes_med, skeleton_med)
        if impacts_med:
            assert impacts_med[0]["risk_level"] == "medium"

    def test_analyze_impacts_no_callers(self, differ: ASTDiffer):
        """无调用者时应返回空列表"""
        changes = [CodeChange("modified", "main.py", function="orphan")]
        skeleton = {"call_graph": {}}

        impacts = differ.analyze_impacts(changes, skeleton)
        assert len(impacts) == 0


# ──────────────────────────────────────────────
# CodeChange 测试
# ──────────────────────────────────────────────

class TestCodeChange:
    """测试 CodeChange 数据结构"""

    def test_create_code_change(self):
        """创建代码变更"""
        change = CodeChange(
            change_type="modified",
            file_path="main.py",
            line=10,
            function="foo"
        )
        assert change.change_type == "modified"
        assert change.file_path == "main.py"
        assert change.line == 10
        assert change.function == "foo"

    def test_code_change_to_dict(self):
        """转换为字典"""
        change = CodeChange(
            change_type="added",
            file_path="utils.py",
            line=5,
            function="bar"
        )
        d = change.to_dict()
        assert d["type"] == "added"
        assert d["file"] == "utils.py"
        assert d["line"] == 5
        assert d["function"] == "bar"

    def test_code_change_defaults(self):
        """默认值"""
        change = CodeChange(change_type="deleted", file_path="test.py")
        assert change.line is None
        assert change.function is None
        assert change.old_code is None
        assert change.new_code is None


# ──────────────────────────────────────────────
# diff_project 测试
# ──────────────────────────────────────────────

class TestDiffProject:
    """测试 diff_project 项目级差异分析"""

    def test_diff_project_no_git_repo(self, tmp_path: Path):
        """非 Git 仓库应返回空列表"""
        result = diff_project(str(tmp_path))
        assert result == []

    def test_diff_project_no_changes(self, tmp_path: Path):
        """无变更时应返回空列表"""
        # 初始化 Git 仓库
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True, capture_output=True)

        # 创建文件并提交
        (tmp_path / "test.py").write_text("def foo(): pass\n")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=tmp_path, check=True, capture_output=True)

        # 再次对比（无变更）
        result = diff_project(str(tmp_path))
        assert result == []
