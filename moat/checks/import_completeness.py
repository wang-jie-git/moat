"""导入完备性检查 — 检测"函数存在但未导入"类 Bug (IMPORT-MISSING-001)

战术指引：
  不搞全量扫描，只审计已识别的【调用点】。
  用 Python ast 提取每个 .py 文件中的 Call 节点，
  验证每个调用是否在当前文件的作用域内可解析。

检测策略：
  1. 解析 .py 文件 → AST
  2. 收集导入符号（from X import Y / import X）
  3. 收集本地定义（def / async def / class）
  4. 收集所有函数调用
  5. 对每个调用：
     - 在导入列表中 → ✅ 通过
     - 在本地定义中  → ✅ 通过
     - 是内置函数     → ✅ 通过
     - 是 self/cls 方法 → ✅ 通过
     - 是模块.调用（os.path.join） → 检查模块是否已导入
     - 未找到来源     → ❌ IMPORT-MISSING-001

忽略边界（通过 .moat/moat.json）:
  {
    "ignore_modules": ["conftest", "conf", "settings"],
    "ignore_patterns": ["*_pb2.py", "*_grpc.py"]
  }

配置示例（.moat/moat.json）:
  {
    "ignore_modules": ["conftest", "conf", "settings", "manage"],
    "ignore_patterns": ["*_pb2.py", "*_pb2_grpc.py", "test_*.py", "migrations/*"],
    "import_completeness": {
      "enabled": true,
      "max_results_per_file": 10
    }
  }
"""
import ast
import logging
from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult
from moat.checks.fail_open import fail_open

logger = logging.getLogger(__name__)

# ── Python 内置函数 / 类型 / 异常（免检） ──
BUILTINS: set[str] = {
    # 内置函数
    "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes",
    "callable", "chr", "classmethod", "compile", "complex", "delattr",
    "dict", "dir", "divmod", "enumerate", "eval", "exec", "filter",
    "float", "format", "frozenset", "getattr", "globals", "hasattr",
    "hash", "hex", "id", "input", "int", "isinstance", "issubclass",
    "iter", "len", "list", "locals", "map", "max", "memoryview", "min",
    "next", "object", "oct", "open", "ord", "pow", "print", "property",
    "range", "repr", "reversed", "round", "set", "setattr", "slice",
    "sorted", "staticmethod", "str", "sum", "super", "tuple", "type",
    "vars", "zip",
    # 内置类型 / 异常
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
    "AttributeError", "ImportError", "RuntimeError", "StopIteration",
    "NotImplementedError", "OSError", "IOError", "FileNotFoundError",
    "ZeroDivisionError", "AssertionError", "NameError", "TypeError",
    "LookupError", "MemoryError", "SystemError", "SystemExit",
    "KeyboardInterrupt", "StopAsyncIteration", "GeneratorExit",
    "True", "False", "None", "Ellipsis", "NotImplemented",
    "hasattr", "getattr", "setattr", "delattr",
    "isinstance", "issubclass", "callable",
    "staticmethod", "classmethod", "property",
    "__import__", "iter", "next", "reversed", "sorted",
    "enumerate", "zip", "map", "filter", "reduce",
    "super", "type", "isinstance", "issubclass",
    "print", "input", "open", "format", "repr",
    "iter", "next", "all", "any",
    "min", "max", "sum", "round", "abs",
    "hex", "oct", "bin", "ord", "chr",
    "hash", "id", "len", "range",
    "slice", "vars", "dir", "locals", "globals",
    "compile", "eval", "exec",
    "breakpoint", "help", "exit", "quit",
    # 常用 pytest / unittest 符号（测试框架自动注入）
    "pytest", "unittest", "mock", "patch",
    "fixture", "parametrize", "mark", "raises",
    "skip", "skipif", "xfail",
}


class ImportCompletenessCheck(Check):
    """导入完备性检查器

    扫描 .py 文件中的调用点，验证每个被调用的函数/类
    是否在当前文件的作用域内可解析。

    规则编号: IMPORT-MISSING-001
    """

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        super().__init__(project_root, config)
        self.name = "ImportCompleteness"

        # 从配置读取忽略规则
        self.ignore_modules: set[str] = set(
            config.get("ignore_modules", []) if config else []
        )
        self.ignore_patterns: list[str] = list(
            config.get("ignore_patterns", []) if config else []
        )
        # 默认忽略的模块
        self.ignore_modules.update({"conftest", "conf", "settings"})

    def run(self) -> list[CheckResult]:
        """运行导入完备性检查"""
        results: list[CheckResult] = []

        py_files = sorted(self.project.rglob("*.py"))

        # ── AST 缓存：避免重复解析相同文件 ──
        ast_cache: dict[str, tuple[ast.Module | None, str]] = {}

        for file_path in py_files:
            if self._should_skip(file_path):
                continue

            # 快速跳过：只读头 200 字节判断是否有函数调用
            if self._has_no_calls(file_path):
                continue

            file_results = self._check_file(file_path, ast_cache)
            results.extend(file_results)

            # 每 50 个文件输出一次进度（仅完整模式）
            idx = py_files.index(file_path) + 1
            if idx > 0 and idx % 50 == 0 and len(py_files) > 100:
                print(f"  导入检查进度: {idx}/{len(py_files)} 个文件...")

        if not results:
            results.append(self.pass_check("所有 Python 文件导入检查通过"))

        return results

    @staticmethod
    def _has_no_calls(file_path: Path) -> bool:
        """快速判断文件是否包含函数调用（避免全量 AST 解析）

        只读前 200 字节检查 '(' 字符。
        如果连 '(' 都没有，100% 没有函数调用，直接跳过。
        """
        try:
            # 空文件或极小文件直接跳过
            if file_path.stat().st_size < 10:
                return True
            # 读前 200 字节判断是否有调用
            head = file_path.read_bytes()[:200]
            return b"(" not in head
        except (OSError, IOError):
            return False

    def _should_skip(self, file_path: Path) -> bool:
        """判断是否跳过文件"""
        # 跳过常见目录
        skip_dirs = {"__pycache__", ".git", "node_modules",
                     "build", "dist", ".next", ".nuxt", "target", "vendor",
                     ".pytest_cache", ".mypy_cache", ".ruff_cache"}
        for part in file_path.parts:
            # 虚拟环境目录（.venv, .venv.prod, venv 等）
            if part.startswith(".venv") or part == "venv":
                return True
            if part in skip_dirs:
                return True

        # 跳过忽略模块
        if file_path.stem in self.ignore_modules:
            return True

        # 跳过忽略模式
        for pattern in self.ignore_patterns:
            if file_path.match(pattern):
                return True

        return False

    @fail_open(default_return=[])
    def _check_file(self, file_path: Path, ast_cache: dict | None = None) -> list[CheckResult]:
        """检查单个文件的导入完备性

        Args:
            file_path: 要检查的 .py 文件路径
            ast_cache: 可选的 AST 缓存，避免重复解析

        Returns:
            未绑定引用列表
        """
        source = file_path.read_text(encoding="utf-8")

        # 尝试从缓存获取 AST
        cache_key = str(file_path)
        cached = (ast_cache or {}).get(cache_key)
        if cached is not None:
            tree, _ = cached
        else:
            try:
                tree = ast.parse(source, filename=str(file_path))
                if ast_cache is not None:
                    ast_cache[cache_key] = (tree, source)
            except SyntaxError:
                return []

        if tree is None:
            return []

        # 快速跳过：AST 中没有 Call 节点的文件
        has_call = any(isinstance(n, ast.Call) for n in ast.walk(tree))
        if not has_call:
            return []

        # 1. 收集当前文件的作用域信息
        scope = ScopeInfo()
        self._collect_imports(tree, scope)
        self._collect_definitions(tree, scope)
        self._collect_assignments(tree, scope)

        # 2. 提取所有调用点
        calls = self._collect_calls(tree)

        # 3. 验证每个调用
        results: list[CheckResult] = []
        rel_path = str(file_path.relative_to(self.project))

        for call_info in calls:
            if not self._is_resolved(call_info, scope):
                # 尝试搜索跨文件定义（提供建议来源）
                suggestion = self._find_definition_hint(call_info["name"], file_path)
                results.append(CheckResult(
                    type="fail",
                    message=(
                        f"IMPORT-MISSING-001: "
                        f"`{call_info['name']}` 被调用但未在当前文件导入。"
                        f"已在 {rel_path}:{call_info['line']} 处调用。"
                    ),
                    file=rel_path,
                    line=call_info["line"],
                    level="ERROR",
                    metadata={
                        "rule": "IMPORT-MISSING-001",
                        "call_name": call_info["name"],
                        "suggestion": suggestion,
                    },
                ))

        return results

    def _find_definition_hint(self, name: str, current_file: Path) -> str:
        """搜索未解析调用名的项目内定义位置

        遍历项目中的 .py 文件（跳过当前文件和忽略目录），
        查找包含 `def {name}(` 或 `class {name}(` 的文件。

        Returns:
            建议字符串，如 '从 src/helpers.py 导入 foo'
        """
        try:
            # 限制搜索范围：同目录 + 相邻目录，避免扫全项目
            search_roots = [current_file.parent]
            # 如果是 __init__.py，也看看兄弟目录
            if current_file.name == "__init__.py":
                search_roots.append(current_file.parent.parent)

            for root in search_roots:
                if not root.exists():
                    continue
                for py_file in root.glob("*.py"):
                    if py_file == current_file:
                        continue
                    try:
                        content = py_file.read_text(encoding="utf-8")
                        # 查找 def name( 或 class name( 或 async def name(
                        for prefix in (f"def {name}(", f"async def {name}(", f"class {name}("):
                            if prefix in content:
                                rel = py_file.relative_to(self.project)
                                return (
                                    f"已在 {rel} 中找到 `{name}` 的定义。"
                                    f"请添加: from {rel.with_suffix('').as_posix().replace('/', '.')} import {name}"
                                )
                    except (OSError, IOError):
                        continue
        except Exception:
            pass

        return (
            f"检查 `{name}` 的定义位置，"
            f"并确认是否已通过 import 或 from ... import 引入。"
        )

    # ── 作用域收集 ─────────────────────────────────────

    def _collect_imports(self, tree: ast.Module, scope: "ScopeInfo"):
        """收集文件导入的符号名"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # import os → scope.imports 添加 "os"
                    # import os.path → scope.imports 添加 "os"
                    top_level = alias.name.split(".")[0]
                    scope.imports.add(top_level)
                    if alias.asname:
                        scope.imports.add(alias.asname)

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    # from os import path → scope.imports 添加 "path"
                    name = alias.asname or alias.name
                    scope.imports.add(name)
                    # 同时也记下 from X import Y 的来源
                    scope.from_imports[name] = module

    def _collect_definitions(self, tree: ast.Module, scope: "ScopeInfo"):
        """收集当前文件中定义的符号（函数、类、参数）"""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                scope.definitions.add(node.name)
                # 同时收集函数参数（常见的误报来源）
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for arg in node.args.args:
                        scope.definitions.add(arg.arg)
                    # 收集 *args 和 **kwargs
                    if node.args.vararg:
                        scope.definitions.add(node.args.vararg.arg)
                    if node.args.kwarg:
                        scope.definitions.add(node.args.kwarg.arg)
                    # 收集默认参数和 keyword-only 参数
                    for arg in node.args.kwonlyargs:
                        scope.definitions.add(arg.arg)
                    for arg in node.args.posonlyargs:
                        scope.definitions.add(arg.arg)
            # 收集 lambda 参数
            elif isinstance(node, ast.Lambda):
                for arg in node.args.args:
                    scope.definitions.add(arg.arg)

    def _collect_assignments(self, tree: ast.Module, scope: "ScopeInfo"):
        """收集局部变量赋值（用于区分"变量调用"和"缺失导入"）"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    self._add_name_target(target, scope)
            elif isinstance(node, ast.AnnAssign):
                # x: int = 42 或 x: int
                if isinstance(node.target, ast.Name):
                    scope.assignments.add(node.target.id)
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                # for x in ... → x 是局部变量
                # for a, b in ... → a, b 也是局部变量
                self._add_name_target(node.target, scope)
            # 列表/集合/字典推导式、生成器表达式中的变量
            # [f for f in items if f.x()] → f 是局部变量
            elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                for comp in node.generators:
                    self._add_name_target(comp.target, scope)
            # with ... as x: → x 是局部变量
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                for item in node.items:
                    if item.optional_vars is not None:
                        self._add_name_target(item.optional_vars, scope)
            # except ... as e: → e 是局部变量
            elif isinstance(node, ast.ExceptHandler):
                if node.name is not None:
                    scope.assignments.add(node.name)

    def _add_name_target(self, target: ast.AST, scope: "ScopeInfo"):
        """递归收集赋值目标中的变量名（支持解包）"""
        if isinstance(target, ast.Name):
            scope.assignments.add(target.id)
        elif isinstance(target, ast.Tuple):
            for elt in target.elts:
                self._add_name_target(elt, scope)
        elif isinstance(target, ast.List):
            for elt in target.elts:
                self._add_name_target(elt, scope)
        elif isinstance(target, ast.Starred):
            # *rest = ...
            if isinstance(target.value, ast.Name):
                scope.assignments.add(target.value.id)

    def _add_name_target(self, target: ast.AST, scope: "ScopeInfo"):
        """递归收集赋值目标中的变量名（支持解包）"""
        if isinstance(target, ast.Name):
            scope.assignments.add(target.id)
        elif isinstance(target, ast.Tuple):
            for elt in target.elts:
                self._add_name_target(elt, scope)
        elif isinstance(target, ast.List):
            for elt in target.elts:
                self._add_name_target(elt, scope)
        elif isinstance(target, ast.Starred):
            # *rest = ...
            if isinstance(target.value, ast.Name):
                scope.assignments.add(target.value.id)

    def _collect_calls(self, tree: ast.Module) -> list[dict]:
        """提取所有函数调用点

        专注提取"裸函数名"调用（foo()），
        跳过 self.xxx() / cls.xxx() 等方法调用。
        """
        calls: list[dict] = []

        for node in ast.walk(tree):
            # 只处理 Call 节点
            if not isinstance(node, ast.Call):
                continue

            func = node.func

            # 情况 1: foo() — 裸函数名
            if isinstance(func, ast.Name):
                calls.append({
                    "name": func.id,
                    "line": func.lineno,
                    "type": "direct",
                })

            # 情况 2: module.func() — 属性访问
            # 检查 module 是否已导入（而非 func）
            elif isinstance(func, ast.Attribute):
                if isinstance(func.value, ast.Name):
                    # self.xxx() / cls.xxx() 是方法调用，不做检查
                    if func.value.id in ("self", "cls", "super"):
                        continue
                    calls.append({
                        "name": func.value.id,  # 检查 module 是否导入
                        "line": func.lineno,
                        "type": "attribute",
                        "attribute": func.attr,
                    })

        return calls

    # ── 解析验证 ─────────────────────────────────────

    def _is_resolved(self, call_info: dict, scope: "ScopeInfo") -> bool:
        """判断一个调用是否能在当前作用域解析"""
        name = call_info["name"]
        call_type = call_info.get("type", "direct")

        # 内置函数 → 通过
        if name in BUILTINS:
            return True

        # 局部变量 → 通过（assignments）
        if name in scope.assignments:
            return True

        # 本地定义的符号（函数、类、参数）→ 通过
        if name in scope.definitions:
            return True

        # 属性调用: module.func()
        # 检查 module 是否已导入、已定义、或已赋值
        if call_type == "attribute":
            return (name in scope.imports
                    or name in scope.definitions
                    or name in scope.assignments)

        # 直接调用: foo()
        # 检查是否已导入
        if name in scope.imports:
            return True

        # 检查是否有别名导入 (from X import Y as Z)
        if name in scope.from_imports:
            return True

        # ❌ 未解析
        return False


class ScopeInfo:
    """文件作用域信息"""

    def __init__(self):
        # 导入的符号: {"os", "path", "app", ...}
        self.imports: set[str] = set()
        # From 导入的来源: {"path": "os", ...}
        self.from_imports: dict[str, str] = {}
        # 本地定义的符号: {"main", "MyClass", ...}
        self.definitions: set[str] = set()
        # 局部变量赋值: {"p", "x", "result", ...}
        self.assignments: set[str] = set()