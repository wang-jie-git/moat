"""SQL 注入检测守门员

检测策略：
1. Tree-sitter AST：定位 execute() 调用和 BinaryExpression（+ 拼接）
2. 上下文回溯：检查前 3-5 行是否有 f-string、.format()、% 格式化
3. 报错 + 处方：不仅拦截，还提供修复建议

这是"守门员"的本能：安全第一，误报可接受。
"""
import re
from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult

# 尝试导入 tree-sitter
try:
    import tree_sitter_python as tspython
    from tree_sitter import Language, Parser

    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False


class SQLInjectionCheck(Check):
    """SQL 注入检测器

    检测模式：
    - cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    - cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)
    - cursor.execute("SELECT * FROM users WHERE id = " + user_id)
    - cursor.execute("SELECT * FROM users WHERE id = {}".format(user_id))
    """

    # SQL 执行函数模式
    SQL_EXEC_PATTERNS = [
        r'\.execute\(',
        r'\.executemany\(',
        r'\.raw\(',
        r'\.query\(',
        r'db\.execute\(',
        r'cursor\.execute\(',
    ]

    # 字符串拼接模式（在前 5 行内检测）
    INTERPOLATION_PATTERNS = [
        (r'f["\']', 'f-string'),
        (r'\.format\(', '.format()'),
        (r'["\'].*%s.*["\']', '%s 格式化'),
        (r'["\'].*%d.*["\']', '%d 格式化'),
        (r'["\']\s*\+', '字符串拼接 (+)'),  # 匹配 "..." + ...
        (r'\+\s*["\']', '字符串拼接 (+)'),  # 匹配 ... + "..."
    ]

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        super().__init__(project_root, config)
        self.name = "SQLInjection"

    def run(self) -> list[CheckResult]:
        """运行 SQL 注入检测

        Returns:
            检查结果列表
        """
        results = []

        # 1. 扫描所有 Python 文件（只扫描修改的文件会更快，但为了完整性先扫描所有）
        py_files = list(self.project.rglob("**/*.py"))

        for file_path in py_files:
            # 跳过虚拟环境、测试文件
            if self._should_skip(file_path):
                continue

            # 2. 检查文件
            file_results = self._check_file(file_path)
            results.extend(file_results)

        return results

    def _should_skip(self, file_path: Path) -> bool:
        """判断是否跳过文件"""
        skip_patterns = [
            ".venv", "venv", "__pycache__", ".git",
            "node_modules", "test_", "_test.py", "tests/",
        ]
        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)

    def _check_file(self, file_path: Path) -> list[CheckResult]:
        """检查单个文件的 SQL 注入风险

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

        # 1. Tree-sitter AST 检测（优先）
        if HAS_TREE_SITTER:
            ast_results = self._check_with_ast(content, file_path)
            results.extend(ast_results)

        # 2. 如果 AST 没检测到，用正则做后备检查
        if not results:
            regex_results = self._check_with_regex(content, file_path)
            results.extend(regex_results)

        return results

    def _check_with_ast(self, content: str, file_path: Path) -> list[CheckResult]:
        """使用 Tree-sitter AST 检测 SQL 注入

        检测 BinaryExpression（+ 拼接）在 execute() 调用中
        """
        if not HAS_TREE_SITTER:
            return []

        results = []

        try:
            parser = Parser(
                language=Language(tspython.language())
            )
            tree = parser.parse(bytes(content, "utf8"))
            root_node = tree.root_node

            # 遍历所有节点
            def traverse(node):
                # 查找函数调用节点
                if node.type == "call":
                    # 检查是否是 execute() 调用
                    func_name = self._get_function_name(node)
                    if func_name and any(
                        func_name.endswith(p.replace(r"\.", "").replace(r"\(", ""))
                        for p in self.SQL_EXEC_PATTERNS
                    ):
                        # 检查参数中是否有 BinaryExpression（+ 拼接）
                        sql_arg = self._get_sql_argument(node)
                        if sql_arg and self._has_string_concat(sql_arg):
                            line = node.start_point[0] + 1
                            results.append(CheckResult(
                                type="fail",
                                level="CRITICAL",
                                file=str(file_path.resolve().relative_to(self.project.resolve())),
                                line=line,
                                message=f"[SQL 注入] 第 {line} 行检测到字符串拼接 SQL。修复建议：使用参数化查询 -> {func_name}(\"SELECT ... WHERE id = %s\", (user_id,))",
                                metadata={"rule": "sql_injection", "method": "ast"},
                            ))

                # 递归遍历子节点
                for child in node.children:
                    traverse(child)

            traverse(root_node)

        except Exception:
            pass  # AST 解析失败，降级到正则

        return results

    def _get_function_name(self, call_node) -> str | None:
        """获取函数调用名"""
        if call_node.child_count == 0:
            return None

        func_node = call_node.child(0)
        if func_node.type == "identifier":
            return func_node.text.decode("utf8")
        elif func_node.type == "attribute":
            # 处理 obj.method() 形式
            if func_node.child_count >= 2:
                attr = func_node.child(2)
                if attr.type == "identifier":
                    return attr.text.decode("utf8")

        return None

    def _get_sql_argument(self, call_node) -> Any:
        """获取 SQL 查询参数（第一个参数）"""
        if call_node.child_count < 2:
            return None

        # 找到 arguments 节点
        for child in call_node.children:
            if child.type == "argument_list":
                if child.child_count >= 1:
                    return child.child(0)  # 第一个参数
        return None

    def _has_string_concat(self, node) -> bool:
        """检查 AST 节点是否有字符串拼接（BinaryExpression with +）"""
        if node.type == "binary_operator":
            # 检查操作符是 +
            if node.child_count >= 2:
                op = node.child(1)
                if op.type == "+":
                    return True

        # 递归检查子节点
        for child in node.children:
            if self._has_string_concat(child):
                return True

        return False

    def _check_with_regex(self, content: str, file_path: Path) -> list[CheckResult]:
        """使用正则表达式检查（后备方案）"""
        results = []

        # 查找所有 SQL 执行点
        sql_exec_lines = self._find_sql_exec_points(content)

        if not sql_exec_lines:
            return []

        # 对每个 SQL 执行点，检查前 5 行是否有拼接
        for exec_line_num in sql_exec_lines:
            context_results = self._check_context(content, exec_line_num, file_path)
            results.extend(context_results)

        return results

    def _find_sql_exec_points(self, content: str) -> list[int]:
        """找到所有 SQL 执行点（行号）

        Args:
            content: 文件内容

        Returns:
            行号列表（1-based）
        """
        lines = content.split("\n")
        exec_lines = []

        for i, line in enumerate(lines, 1):
            for pattern in self.SQL_EXEC_PATTERNS:
                if re.search(pattern, line):
                    exec_lines.append(i)
                    break

        return exec_lines

    def _check_context(self, content: str, exec_line: int, file_path: Path) -> list[CheckResult]:
        """检查 SQL 执行点的前 5 行上下文 + 当前行

        Args:
            content: 文件内容
            exec_line: SQL 执行点行号（1-based）
            file_path: 文件路径

        Returns:
            检查结果列表
        """
        results = []
        lines = content.split("\n")

        # 检查前 5 行 + 当前行（最多回溯到第 1 行）
        start_line = max(0, exec_line - 6)  # 0-based
        end_line = exec_line  # 0-based（包含当前行，用于检测同行的 f-string）

        context_lines = lines[start_line:end_line]
        context_text = "\n".join(context_lines)

        # 检查是否有字符串拼接
        has_interpolation = False
        interpolation_type = None

        for pattern, pattern_name in self.INTERPOLATION_PATTERNS:
            if re.search(pattern, context_text):
                has_interpolation = True
                interpolation_type = pattern_name
                break

        # 额外的检查：如果 execute() 的参数是变量而不是字符串常量
        if has_interpolation:
            results.append(CheckResult(
                type="fail",
                level="CRITICAL",
                file=str(file_path.resolve().relative_to(self.project.resolve())),
                line=exec_line,
                message=f"[SQL 注入] 第 {exec_line} 行检测到 SQL 拼接（{interpolation_type}），请使用参数化查询",
                metadata={
                    "rule": "sql_injection",
                    "exec_line": exec_line,
                    "interpolation_type": interpolation_type,
                }
            ))

        return results
