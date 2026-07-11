"""增强 SQL 注入检测器（SQL-002）

基于 SQL-001，扩展检测能力：
1. Django ORM raw() 中的 SQL 拼接
2. SQLAlchemy execute()/text() 检测
3. 异步数据库驱动（asyncpg, aiomysql, psycopg2）
4. ORM filter() 中的字符串拼接

检测策略：
- Tree-sitter AST：精准定位函数调用和参数拼接
- 正则匹配：快速扫描常见模式
- 上下文分析：检查前 5 行的字符串拼接
"""
import logging
import re
from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult
from moat.checks.fail_open import fail_open

logger = logging.getLogger(__name__)

# 尝试导入 tree-sitter
try:
    import tree_sitter_python as tspython
    from tree_sitter import Language, Parser

    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False


class EnhancedSQLInjectionCheck(Check):
    """增强 SQL 注入检测器（SQL-002）

    检测模式：
    - cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    - cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)
    - cursor.execute("SELECT * FROM users WHERE id = " + user_id)
    - cursor.execute("SELECT * FROM users WHERE id = {}".format(user_id))
    - User.objects.raw(f"SELECT * FROM users WHERE id = {user_id}")
    - session.execute(f"SELECT * FROM users WHERE id = {user_id}")
    - await conn.execute(f"SELECT * FROM users WHERE id = {user_id}")
    - User.objects.filter(name="%s" % user_id)
    """

    # SQL 执行函数模式（增强版）
    SQL_EXEC_PATTERNS = [
        # 通用 execute
        r'\.execute\(',
        r'\.executemany\(',
        # ORM raw 查询
        r'\.raw\(',
        r'\.query\(',
        # 数据库驱动
        r'db\.execute\(',
        r'cursor\.execute\(',
        r'conn\.execute\(',
        r'connection\.execute\(',
        # SQLAlchemy
        r'session\.execute\(',
        r'engine\.execute\(',
        r'text\(',
        # Django ORM
        r'objects\.raw\(',
        r'objects\.filter\(',
        r'objects\.get\(',
    ]

    # ORM 特有的危险模式
    ORM_DANGER_PATTERNS = [
        # Django raw() with f-string
        (r'\.raw\(f["\']', 'Django ORM raw() with f-string', 'CRITICAL'),
        (r'\.raw\(["\']\s*\+', 'Django ORM raw() with concatenation', 'CRITICAL'),
        (r'\.raw\(.*\.format\(', 'Django ORM raw() with .format()', 'CRITICAL'),
        # Django filter() with string formatting
        (r'\.filter\(.*%s', 'Django ORM filter() with %s', 'CRITICAL'),
        (r'\.filter\(.*%d', 'Django ORM filter() with %d', 'CRITICAL'),
        # SQLAlchemy text() with f-string
        (r'text\(f["\']', 'SQLAlchemy text() with f-string', 'CRITICAL'),
        (r'text\(["\']\s*\+', 'SQLAlchemy text() with concatenation', 'CRITICAL'),
        # SQLAlchemy execute with f-string
        (r'session\.execute\(f["\']', 'SQLAlchemy execute() with f-string', 'CRITICAL'),
        (r'engine\.execute\(f["\']', 'SQLAlchemy engine.execute() with f-string', 'CRITICAL'),
    ]

    # 字符串拼接模式
    INTERPOLATION_PATTERNS = [
        (r'f["\']', 'f-string'),
        (r'\.format\(', '.format()'),
        (r'["\'].*%s.*["\']', '%s 格式化'),
        (r'["\'].*%d.*["\']', '%d 格式化'),
        (r'["\']\s*\+', '字符串拼接 (+)'),
        (r'\+\s*["\']', '字符串拼接 (+)'),
    ]

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        super().__init__(project_root, config)
        self.name = "EnhancedSQLInjection"

    def run(self) -> list[CheckResult]:
        """运行增强 SQL 注入检测

        Returns:
            检查结果列表
        """
        results = []

        # 扫描所有 Python 文件
        py_files = list(self.project.rglob("**/*.py"))

        for file_path in py_files:
            if self._should_skip(file_path):
                continue

            file_results = self._check_file(file_path)
            results.extend(file_results)

        return results

    def _should_skip(self, file_path: Path) -> bool:
        """判断是否跳过文件"""
        skip_patterns = [
            ".venv", "venv", "__pycache__", ".git",
            "node_modules", "test_", "_test.py", "tests/",
            "migrations/", "fixtures/",
        ]
        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)

    @fail_open(default_return=[], log_level=logging.DEBUG)
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

        # 1. AST 检测（优先）
        if HAS_TREE_SITTER:
            ast_results = self._check_with_ast(content, file_path)
            results.extend(ast_results)

        # 2. ORM 特有模式检测
        orm_results = self._check_orm_patterns(content, file_path)
        results.extend(orm_results)

        # 3. 正则后备检查
        if not results:
            regex_results = self._check_with_regex(content, file_path)
            results.extend(regex_results)

        return results

    def _check_with_ast(self, content: str, file_path: Path) -> list[CheckResult]:
        """使用 Tree-sitter AST 检测 SQL 注入"""
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
                if node.type == "call":
                    func_name = self._get_function_name(node)
                    if func_name and self._is_sql_exec_function(func_name):
                        # 检查参数中是否有字符串拼接
                        sql_arg = self._get_sql_argument(node)
                        if sql_arg and self._has_string_concat(sql_arg):
                            line = node.start_point[0] + 1
                            results.append(CheckResult(
                                type="fail",
                                level="CRITICAL",
                                file=str(file_path.resolve().relative_to(self.project.resolve())),
                                line=line,
                                message=f"[SQL 注入] 第 {line} 行检测到字符串拼接 SQL（{func_name}）。修复建议：使用参数化查询",
                                metadata={"rule": "sql_injection", "method": "ast", "function": func_name},
                            ))

                for child in node.children:
                    traverse(child)

            traverse(root_node)

        except Exception:
            pass

        return results

    def _check_orm_patterns(self, content: str, file_path: Path) -> list[CheckResult]:
        """检查 ORM 特有模式

        Args:
            content: 文件内容
            file_path: 文件路径

        Returns:
            检查结果列表
        """
        results = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # 跳过注释行
            if self._is_comment_line(line):
                continue

            # 检查 ORM 危险模式
            for pattern, description, severity in self.ORM_DANGER_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    results.append(
                        CheckResult(
                            type="fail",
                            level=severity,
                            file=str(file_path.resolve().relative_to(self.project.resolve())),
                            line=line_num,
                            message=f"[SQL 注入] 第 {line_num} 行检测到 {description}。修复建议：使用参数化查询",
                            metadata={
                                "rule": "sql_injection",
                                "method": "orm_pattern",
                                "orm_type": description.split()[0],
                            },
                        )
                    )

        return results

    def _check_with_regex(self, content: str, file_path: Path) -> list[CheckResult]:
        """使用正则表达式检查（后备方案）"""
        results = []

        sql_exec_lines = self._find_sql_exec_points(content)
        if not sql_exec_lines:
            return []

        for exec_line_num in sql_exec_lines:
            context_results = self._check_context(content, exec_line_num, file_path)
            results.extend(context_results)

        return results

    def _get_function_name(self, call_node) -> str | None:
        """获取函数调用名"""
        if call_node.child_count == 0:
            return None

        func_node = call_node.child(0)
        if func_node.type == "identifier":
            return func_node.text.decode("utf8")
        elif func_node.type == "attribute":
            if func_node.child_count >= 2:
                attr = func_node.child(2)
                if attr.type == "identifier":
                    return attr.text.decode("utf8")

        return None

    def _get_sql_argument(self, call_node) -> Any:
        """获取 SQL 查询参数（第一个参数）"""
        if call_node.child_count < 2:
            return None

        for child in call_node.children:
            if child.type == "argument_list":
                if child.child_count >= 1:
                    return child.child(0)
        return None

    def _has_string_concat(self, node) -> bool:
        """检查 AST 节点是否有字符串拼接"""
        if node.type == "binary_operator":
            if node.child_count >= 2:
                op = node.child(1)
                if op.type == "+":
                    return True

        for child in node.children:
            if self._has_string_concat(child):
                return True

        return False

    def _is_sql_exec_function(self, func_name: str) -> bool:
        """判断是否为 SQL 执行函数"""
        sql_patterns = [
            "execute", "executemany", "raw", "query",
            "text",
        ]

        return any(
            func_name.lower().endswith(pattern.lower())
            for pattern in sql_patterns
        )

    def _find_sql_exec_points(self, content: str) -> list[int]:
        """找到所有 SQL 执行点"""
        lines = content.split("\n")
        exec_lines = []

        for i, line in enumerate(lines, 1):
            for pattern in self.SQL_EXEC_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    exec_lines.append(i)
                    break

        return exec_lines

    def _check_context(self, content: str, exec_line: int, file_path: Path) -> list[CheckResult]:
        """检查 SQL 执行点的上下文"""
        results = []
        lines = content.split("\n")

        start_line = max(0, exec_line - 6)
        end_line = exec_line

        context_lines = lines[start_line:end_line]
        context_text = "\n".join(context_lines)

        # 过滤掉注释行
        non_comment_lines = [l for l in context_lines if not self._is_comment_line(l)]
        non_comment_text = "\n".join(non_comment_lines)

        has_interpolation = False
        interpolation_type = None

        for pattern, pattern_name in self.INTERPOLATION_PATTERNS:
            if re.search(pattern, non_comment_text):
                has_interpolation = True
                interpolation_type = pattern_name
                break

        if has_interpolation:
            results.append(
                CheckResult(
                    type="fail",
                    level="CRITICAL",
                    file=str(file_path.resolve().relative_to(self.project.resolve())),
                    line=exec_line,
                    message=f"[SQL 注入] 第 {exec_line} 行检测到 SQL 拼接（{interpolation_type}），请使用参数化查询",
                    metadata={
                        "rule": "sql_injection",
                        "exec_line": exec_line,
                        "interpolation_type": interpolation_type,
                    },
                )
            )

        return results

    def _is_comment_line(self, line: str) -> bool:
        """检查是否为注释行"""
        stripped = line.strip()
        return stripped.startswith("#") or stripped.startswith("//")
