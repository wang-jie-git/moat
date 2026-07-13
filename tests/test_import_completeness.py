"""测试 ImportCompletenessCheck — 导入完备性检查器 (IMPORT-MISSING-001)"""
import ast
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from moat.checks.import_completeness import ImportCompletenessCheck, BUILTINS, ScopeInfo


# ── 辅助函数 ────────────────────────────────────────

def _make_file(tmp_path: Path, name: str, content: str) -> Path:
    """在临时目录中创建 .py 文件"""
    file_path = tmp_path / name
    file_path.write_text(content, encoding="utf-8")
    return file_path


def _run_check(tmp_path: Path, config: dict | None = None) -> list:
    """运行检查并返回结果"""
    check = ImportCompletenessCheck(tmp_path, config or {})
    return check.run()


# ── 基础测试 ────────────────────────────────────────

class TestBasic:
    """基础功能测试"""

    def test_clean_file(self, tmp_path: Path):
        """文件完整导入，无错误"""
        _make_file(tmp_path, "test.py", """
import os
from pathlib import Path

def foo():
    return os.getenv("HOME")

def bar():
    p = Path("/tmp")
    return p.exists()
""")
        results = _run_check(tmp_path)
        assert len(results) == 0 or (len(results) == 1 and results[0].type == "pass")

    def test_missing_import(self, tmp_path: Path):
        """调用未导入的函数，应报错"""
        _make_file(tmp_path, "test.py", """
def foo():
    return _build_system_prompt("test")
""")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 1
        assert "IMPORT-MISSING-001" in fails[0].message
        assert "_build_system_prompt" in fails[0].message

    def test_missing_import_only_reports_call_not_definition(self, tmp_path: Path):
        """只报告调用点的缺失导入，不报定义点的"""
        _make_file(tmp_path, "test.py", """
import os

def foo():
    return bar()

def bar():
    return os.getenv("HOME")
""")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        # bar() 在 foo 中被调用，但在文件中定义了，所以不应报错
        # 如果有错误，只能是其他原因
        assert len(fails) == 0 or (len(fails) == 1 and "IMPORT" not in fails[0].message)

    def test_builtin_ignored(self, tmp_path: Path):
        """内置函数不应报错"""
        _make_file(tmp_path, "test.py", """
def foo():
    print("hello")
    return len([1, 2, 3])
""")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 0


# ── 作用域测试 ──────────────────────────────────────

class TestScope:
    """作用域解析测试"""

    def test_from_import_works(self, tmp_path: Path):
        """from X import Y 后调用 Y 应通过"""
        _make_file(tmp_path, "test.py", """
from pathlib import Path
Path("/tmp")
""")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 0

    def test_module_attribute_call(self, tmp_path: Path):
        """模块.方法 调用应检查模块导入"""
        _make_file(tmp_path, "test.py", """
import os
os.path.join("a", "b")
""")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 0

    def test_module_attribute_missing_import(self, tmp_path: Path):
        """模块.方法 但模块未导入应报错"""
        _make_file(tmp_path, "test.py", """
nonexistent_module.some_function()
""")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 1
        assert "nonexistent_module" in fails[0].message

    def test_import_with_alias(self, tmp_path: Path):
        """import X as Y 后调用 Y 应通过"""
        _make_file(tmp_path, "test.py", """
import os as operating_system
operating_system.getenv("HOME")
""")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 0

    def test_from_import_with_alias(self, tmp_path: Path):
        """from X import Y as Z 后调用 Z 应通过"""
        _make_file(tmp_path, "test.py", """
from pathlib import Path as P
P("/tmp")
""")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 0

    def test_class_definition(self, tmp_path: Path):
        """类中定义的方法调用自身应通过"""
        _make_file(tmp_path, "test.py", """
class MyClass:
    def foo(self):
        return self.bar()

    def bar(self):
        return 42
""")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 0

    def test_async_function(self, tmp_path: Path):
        """异步函数调用应通过"""
        _make_file(tmp_path, "test.py", """
import asyncio

async def foo():
    await asyncio.sleep(1)

async def bar():
    await foo()
""")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 0


# ── 忽略边界测试 ──────────────────────────────────

class TestIgnore:
    """忽略配置测试"""

    def test_ignore_module(self, tmp_path: Path):
        """配置中忽略的模块不应被检查"""
        _make_file(tmp_path, "conftest.py", "pytest_plugins = []")
        results = _run_check(tmp_path)
        # conftest.py 默认被忽略，不应有结果
        fails = [r for r in results if r.type == "fail"]
        pass_results = [r for r in results if r.type == "pass"]
        assert len(fails) == 0
        # 如果只有 conftest.py，应该有 pass 结果

    def test_ignore_pattern(self, tmp_path: Path):
        """配置中忽略的模式不应被检查"""
        _make_file(tmp_path, "generated_pb2.py", "import nonexistent")
        results = _run_check(tmp_path, {"ignore_patterns": ["*_pb2.py"]})
        fails = [r for r in results if r.type == "fail"]
        # 即使有无效调用，也因为忽略模式而不检查
        # 如果没有其他文件，应该有 pass 结果
        assert all(r.type != "fail" for r in results)


# ── 真实场景测试 ──────────────────────────────────

class TestRealWorld:
    """真实场景测试"""

    def test_multiple_missing_imports(self, tmp_path: Path):
        """多个缺失导入均应报出"""
        _make_file(tmp_path, "test.py", """
def foo():
    _build_system_prompt("test")
    _load_session("test")
    _persist_state("test")
""")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 3
        names = {f.metadata.get("call_name", "") for f in fails}
        assert "_build_system_prompt" in names
        assert "_load_session" in names
        assert "_persist_state" in names

    def test_mixed_imported_and_missing(self, tmp_path: Path):
        """混合导入应只报未导入的"""
        _make_file(tmp_path, "test.py", """
import os

def foo():
    os.getenv("HOME")          # ✅ 已导入
    _build_system_prompt("x")  # ❌ 未导入
    print("hello")             # ✅ 内置函数
""")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 1
        assert "_build_system_prompt" in fails[0].message

    def test_skip_venv(self, tmp_path: Path):
        """跳过虚拟环境目录"""
        venv_dir = tmp_path / ".venv" / "lib" / "python3.12" / "site-packages"
        venv_dir.mkdir(parents=True)
        _make_file(venv_dir, "bad_module.py", "import nonexistent")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 0


# ── 内置函数完整性测试 ─────────────────────────────

class TestBuiltins:
    """内置函数列表完整性测试"""

    def test_common_builtins_covered(self):
        """常用内置函数都应在 BUILTINS 中"""
        common = {
            "print", "len", "str", "int", "list", "dict", "set", "tuple",
            "range", "open", "type", "super", "isinstance", "hasattr",
            "getattr", "setattr", "min", "max", "sum", "abs", "sorted",
            "enumerate", "zip", "map", "filter", "any", "all",
            "True", "False", "None", "Exception", "ValueError",
            "TypeError", "KeyError", "IndexError", "AttributeError",
            "ImportError", "RuntimeError", "FileNotFoundError",
            "property", "staticmethod", "classmethod",
            "iter", "next", "reversed", "eval", "exec", "compile",
            "repr", "format", "bin", "hex", "oct", "ord", "chr",
            "hash", "id", "dir", "vars", "locals", "globals",
            "callable", "delattr", "breakpoint",
        }
        missing = common - BUILTINS
        assert not missing, f"内置函数缺失: {missing}"

    def test_scope_info_init(self):
        """ScopeInfo 初始化正确"""
        scope = ScopeInfo()
        assert scope.imports == set()
        assert scope.from_imports == {}
        assert scope.definitions == set()


# ── 边缘情况测试 ──────────────────────────────────

class TestEdgeCases:
    """边缘情况测试"""

    def test_empty_file(self, tmp_path: Path):
        """空文件不应报错"""
        _make_file(tmp_path, "empty.py", "")
        results = _run_check(tmp_path)
        # 空文件 + 没有其他 .py 文件 → 应看到 pass 结果
        # 取决于是否有其他 .py 文件，这里只检查没有 fail
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 0

    def test_syntax_error_file(self, tmp_path: Path):
        """语法错误的文件不应报错（L0 语法检查会处理）"""
        _make_file(tmp_path, "broken.py", "def foo( bar")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 0

    def test_only_comments(self, tmp_path: Path):
        """只有注释的文件不应报错"""
        _make_file(tmp_path, "comments.py", "# This is a comment\n# Another comment\n")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 0

    def test_relative_import(self, tmp_path: Path):
        """相对导入 (.xxx) 不应报错"""
        _make_file(tmp_path, "test.py", """
from .helpers import foo
foo()
""")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 0


# ── 性能测试 ──────────────────────────────────────

class TestPerformance:
    """性能测试"""

    def test_large_file_does_not_crash(self, tmp_path: Path):
        """大文件不应崩溃"""
        lines = ["import os\n"] * 1000
        lines.extend(["def foo():\n"] + [f"    os.getenv('VAR_{i}')\n" for i in range(500)])
        _make_file(tmp_path, "large.py", "".join(lines))
        results = _run_check(tmp_path)
        # 不应崩溃，不应有错误
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 0


# ── 扩展作用域测试 ──────────────────────────────

class TestExtendedScope:
    """扩展作用域：函数参数、解包、推导式、with 语句"""

    def test_func_param_as_call(self, tmp_path: Path):
        """函数参数用作属性调用 → 不应报错"""
        _make_file(tmp_path, "mod.py", """
def process(project_root):
    files = project_root.rglob("*.py")
    return files
""")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 0, f"函数参数 project_root 被误报: {fails}"

    def test_func_param_with_args(self, tmp_path: Path):
        """函数参数用作调度调用 → 不应报错"""
        _make_file(tmp_path, "mod.py", """
def dispatch(client, request):
    return client(request)
""")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 0, f"参数 client 被误报: {fails}"

    def test_tuple_unpacking_in_for(self, tmp_path: Path):
        """for a, b in ... → a, b 不应报错"""
        _make_file(tmp_path, "mod.py", """
import inspect
for name, obj in inspect.getmembers({}):
    if name.lower() == "test":
        pass
""")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 0, f"解包变量被误报: {fails}"

    def test_list_comprehension_var(self, tmp_path: Path):
        """[f for f in items if f.x()] → f 不应报错"""
        _make_file(tmp_path, "mod.py", """
changed = ["a.py", "b.py"]
py_files = [f for f in changed if f.endswith(".py")]
""")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 0, f"推导式变量被打标: {fails}"

    def test_with_as_var(self, tmp_path: Path):
        """with ... as x: 中 x 不应报错"""
        _make_file(tmp_path, "mod.py", """
import tarfile
import tempfile
with tempfile.NamedTemporaryFile() as f:
    with tarfile.open("test.tar", "w:gz") as tar:
        tar.add(".")
""")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 0, f"with-as 变量被误报: {fails}"

    def test_except_as_var(self, tmp_path: Path):
        """except ... as e: 中 e 不应报错"""
        _make_file(tmp_path, "mod.py", """
try:
    pass
except ValueError as e:
    print(str(e))
""")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 0, f"except-as 变量被误报: {fails}"

    def test_kwarg_param(self, tmp_path: Path):
        """**kwargs 参数不应误报"""
        _make_file(tmp_path, "mod.py", """
def wrapper(**kwargs):
    for k, v in kwargs.items():
        print(f"{k}={v}")
""")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 0, f"kwargs 参数被误报: {fails}"

    def test_lambda_param(self, tmp_path: Path):
        """lambda 参数不应误报"""
        _make_file(tmp_path, "mod.py", """
f = lambda x: x.upper()
result = f("hello")
""")
        results = _run_check(tmp_path)
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) == 0, f"lambda 参数被误报: {fails}"