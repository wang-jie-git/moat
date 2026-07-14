"""未使用的导出检测器（UNUSED-001）

检测策略：
1. Python：检测 __all__ 中未使用的导出
2. TypeScript/JavaScript：检测 export 后未使用的函数/类型
3. Go：检测 export 后未使用的函数
4. 基于 AST 分析，精准定位

这是"守门员"的本能：代码质量第一，但优先级低于安全问题。
"""
import ast
import logging
import re
from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult
from moat.checks.fail_open import fail_open

logger = logging.getLogger(__name__)


class UnusedExportsCheck(Check):
    """未使用的导出检测器

    检测模式：
    - Python：__all__ 中未使用的导出
    - TypeScript：export 后未使用的函数/类型
    - Go：export 后未使用的函数
    """

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        super().__init__(project_root, config)
        self.name = "UnusedExports"

    @fail_open(default_return=[], log_level=logging.DEBUG)
    def _check_file(self, file_path: Path) -> list[CheckResult]:
        """检查单个文件的未使用导出

        Args:
            file_path: 文件路径

        Returns:
            检查结果列表
        """
        suffix = file_path.suffix.lower()

        if suffix == ".py":
            return self._check_python_file(file_path)
        elif suffix in [".ts", ".tsx", ".js", ".jsx"]:
            return self._check_typescript_file(file_path)
        elif suffix == ".go":
            return self._check_go_file(file_path)

        return []

    def run(self) -> list[CheckResult]:
        """运行未使用导出检测

        Returns:
            检查结果列表
        """
        results = []

        # 扫描 Python 文件
        py_files = list(self.project.rglob("**/*.py"))
        for file_path in py_files:
            if self._should_skip(file_path):
                continue

            file_results = self._check_file(file_path)
            results.extend(file_results)

        # 扫描 TypeScript/JavaScript 文件
        ts_files = list(self.project.rglob("**/*.ts")) + list(self.project.rglob("**/*.tsx"))
        for file_path in ts_files:
            if self._should_skip(file_path):
                continue

            file_results = self._check_file(file_path)
            results.extend(file_results)

        # 扫描 Go 文件
        go_files = list(self.project.rglob("**/*.go"))
        for file_path in go_files:
            if self._should_skip(file_path):
                continue

            file_results = self._check_file(file_path)
            results.extend(file_results)

        return results

    @fail_open(default_return=[], log_level=logging.DEBUG)
    def _check_file(self, file_path: Path) -> list[CheckResult]:
        """检查单个文件的未使用导出

        Args:
            file_path: 文件路径

        Returns:
            检查结果列表
        """
        suffix = file_path.suffix.lower()

        if suffix == ".py":
            return self._check_python_file(file_path)
        elif suffix in [".ts", ".tsx", ".js", ".jsx"]:
            return self._check_typescript_file(file_path)
        elif suffix == ".go":
            return self._check_go_file(file_path)

        return []

    def _should_skip(self, file_path: Path) -> bool:
        """判断是否跳过文件"""
        # 跳过常见目录
        skip_dirs = {"__pycache__", ".git", "node_modules", ".next", ".nuxt"}
        for part in file_path.parts:
            if part.startswith(".venv") or part == "venv":
                return True
            if part in skip_dirs:
                return True

        # 跳过测试文件（只匹配文件名，不匹配路径中的 test_）
        file_name = file_path.name
        if file_name.startswith("test_") or file_name.endswith("_test.py"):
            return True

        # 跳过 tests/ 目录
        if "tests/" in str(file_path) or "/tests/" in str(file_path):
            return True

        return False

    @fail_open(default_return=[], log_level=logging.DEBUG)
    def _check_python_file(self, file_path: Path) -> list[CheckResult]:
        """检查 Python 文件的未使用导出

        Args:
            file_path: 文件路径

        Returns:
            检查结果列表
        """
        results = []

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []

        # 1. 提取 __all__ 列表
        all_exports = self._extract_python_all(tree)

        if not all_exports:
            return []

        # 2. 提取所有定义（函数、类、变量）
        defined_names = self._extract_python_definitions(tree)

        # 3. 提取所有使用
        used_names = self._extract_python_usage(tree)

        # 4. 检查哪些 __all__ 中的导出未被使用
        for name in all_exports:
            if name not in used_names and name in defined_names:
                # 找到定义位置
                line_num = self._find_definition_line(tree, name)
                results.append(
                    CheckResult(
                        type="warn",
                        level="LOW",
                        file=str(file_path.resolve().relative_to(self.project.resolve())),
                        line=line_num,
                        message=f"[未使用导出] '{name}' 在 __all__ 中导出但未被使用",
                        metadata={
                            "rule": "unused_exports",
                            "language": "python",
                            "export_name": name,
                        },
                    )
                )

        return results

    @fail_open(default_return=[], log_level=logging.DEBUG)
    def _check_typescript_file(self, file_path: Path) -> list[CheckResult]:
        """检查 TypeScript/JavaScript 文件的未使用导出

        Args:
            file_path: 文件路径

        Returns:
            检查结果列表
        """
        results = []

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        # 使用正则快速扫描（简化版）
        # 提取所有 export 声明
        export_pattern = r'export\s+(?:default\s+)?(?:function|const|class|interface|type)\s+(\w+)'
        exports = re.findall(export_pattern, content)

        if not exports:
            return []

        # 提取所有使用（简化：检查其他地方是否引用）
        lines = content.split("\n")
        for export_name in exports:
            # 跳过 default export
            if export_name == "default":
                continue

            # 计算使用次数
            usage_count = 0
            export_line = None
            # 匹配 export 声明的正则
            export_decl_pattern = re.compile(r'export\s+(?:default\s+)?(?:function|const|class|interface|type)\s+' + re.escape(export_name) + r'\b')

            for line_num, line in enumerate(lines, 1):
                # 检查是否是 export 声明行
                if export_decl_pattern.search(line):
                    export_line = line_num
                    continue

                # 检查是否使用了该名称（排除注释行）
                if not line.strip().startswith("//") and not line.strip().startswith("/*"):
                    if re.search(r'\b' + re.escape(export_name) + r'\b', line):
                        usage_count += 1

            # 如果只导出但从未在其他地方使用
            if usage_count == 0 and export_line:
                results.append(
                    CheckResult(
                        type="warn",
                        level="LOW",
                        file=str(file_path.resolve().relative_to(self.project.resolve())),
                        line=export_line,
                        message=f"[未使用导出] '{export_name}' 被导出但未被使用",
                        metadata={
                            "rule": "unused_exports",
                            "language": "typescript",
                            "export_name": export_name,
                        },
                    )
                )

        return results

    @fail_open(default_return=[], log_level=logging.DEBUG)
    def _check_go_file(self, file_path: Path) -> list[CheckResult]:
        """检查 Go 文件的未使用导出

        Args:
            file_path: 文件路径

        Returns:
            检查结果列表
        """
        results = []

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        # 使用正则快速扫描
        # Go 的导出是以大写字母开头的标识符
        lines = content.split("\n")

        # 提取导出函数/类型
        export_pattern = r'^func\s+([A-Z]\w*)\s*\('
        type_pattern = r'^type\s+([A-Z]\w*)\s+'

        exports = []

        for line_num, line in enumerate(lines, 1):
            # 跳过注释
            if line.strip().startswith("//") or line.strip().startswith("/*"):
                continue

            func_match = re.match(export_pattern, line)
            if func_match:
                exports.append((func_match.group(1), line_num))

            type_match = re.match(type_pattern, line)
            if type_match:
                exports.append((type_match.group(1), line_num))

        if not exports:
            return []

        # 检查使用情况
        for export_name, export_line in exports:
            usage_count = 0

            for line_num, line in enumerate(lines, 1):
                if line_num == export_line:
                    continue

                # 跳过注释
                if line.strip().startswith("//") or line.strip().startswith("/*"):
                    continue

                if re.search(r'\b' + re.escape(export_name) + r'\b', line):
                    usage_count += 1

            # 如果只导出但从未使用
            if usage_count == 0:
                results.append(
                    CheckResult(
                        type="warn",
                        level="LOW",
                        file=str(file_path.resolve().relative_to(self.project.resolve())),
                        line=export_line,
                        message=f"[未使用导出] '{export_name}' 被导出但未被使用",
                        metadata={
                            "rule": "unused_exports",
                            "language": "go",
                            "export_name": export_name,
                        },
                    )
                )

        return results

    def _extract_python_all(self, tree: ast.AST) -> list[str]:
        """提取 __all__ 列表

        Args:
            tree: AST 树

        Returns:
            __all__ 中的导出名列表
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, ast.List):
                            exports = []
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    exports.append(elt.value)
                            return exports
                        elif isinstance(node.value, ast.Tuple):
                            exports = []
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    exports.append(elt.value)
                            return exports
        return []

    def _extract_python_definitions(self, tree: ast.AST) -> set[str]:
        """提取所有定义（函数、类、变量）

        Args:
            tree: AST 树

        Returns:
            定义名集合
        """
        defined = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                defined.add(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                defined.add(node.name)
            elif isinstance(node, ast.ClassDef):
                defined.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined.add(target.id)

        return defined

    def _extract_python_usage(self, tree: ast.AST) -> set[str]:
        """提取所有使用

        Args:
            tree: AST 树

        Returns:
            使用的名字集合
        """
        used = set()

        for node in ast.walk(tree):
            # Name 节点表示变量使用
            if isinstance(node, ast.Name):
                used.add(node.id)
            # Attribute 节点表示属性访问
            elif isinstance(node, ast.Attribute):
                used.add(node.attr)

        return used

    def _find_definition_line(self, tree: ast.AST, name: str) -> int:
        """找到定义的代码行

        Args:
            tree: AST 树
            name: 名称

        Returns:
            行号
        """
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name == name:
                    return node.lineno
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == name:
                        return node.lineno

        return 1
