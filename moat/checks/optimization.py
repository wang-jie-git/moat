"""
代码优化检查器（Ponytail 集成）

基于 Ponytail 的优化原则：
1. YAGNI (You Ain't Gonna Need It)
2. 复杂度控制（圈复杂度、认知复杂度）
3. 过度工程化检测
4. 标准库优先原则

战术设计（基于用户反馈）：
1. 异步触发：默认不跑，--optimize 或配置开启才跑
2. 技术债务：在报告中分类显示
3. 数据驱动：每条规则有 rule_id

参考：
- 原 Ponytail: https://github.com/DietrichGebert/ponytail
- Moat 检查基类: moat.checks.base.Check
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult


# ==================== 规则定义（数据驱动） ====================

OPTIMIZATION_RULES = {
    # YAGNI 原则规则
    "yagni_unused_imports": {
        "id": "YAGNI-001",
        "name": "未使用的导入",
        "category": "code_simplification",
        "description": "检测未使用的 import，避免冗余依赖",
        "severity": "low",
    },
    "yagni_todo_fixme": {
        "id": "YAGNI-002",
        "name": "未处理的 TODO/FIXME",
        "category": "code_simplification",
        "description": "检测过多的 TODO/FIXME 注释，建议及时处理",
        "severity": "low",
    },
    "yagni_over_abstraction": {
        "id": "YAGNI-003",
        "name": "过度抽象",
        "category": "code_simplification",
        "description": "检测过多的 interface/type 定义，可能存在过度设计",
        "severity": "medium",
    },
    "yagni_dead_code": {
        "id": "YAGNI-004",
        "name": "死代码检测",
        "category": "code_simplification",
        "description": "检测无法访问的代码（return 后、except 块中）",
        "severity": "medium",
    },
    "yagni_excessive_comments": {
        "id": "YAGNI-005",
        "name": "过度注释",
        "category": "code_simplification",
        "description": "注释行数超过代码行数的 30%，建议精简",
        "severity": "low",
    },
    "yagni_duplicate_code": {
        "id": "YAGNI-006",
        "name": "重复代码",
        "category": "code_simplification",
        "description": "检测相似代码块（>=5 行），建议提取函数",
        "severity": "medium",
    },

    # 复杂度规则
    "complexity_cyclomatic": {
        "id": "COMPLEX-001",
        "name": "圈复杂度超标",
        "category": "complexity",
        "description": "函数圈复杂度超过阈值，建议拆分",
        "severity": "medium",
    },
    "complexity_function_length": {
        "id": "COMPLEX-002",
        "name": "函数过长",
        "category": "complexity",
        "description": "函数长度超过 50 行，建议拆分",
        "severity": "low",
    },
    "complexity_cognitive": {
        "id": "COMPLEX-003",
        "name": "认知复杂度超标",
        "category": "complexity",
        "description": "函数认知复杂度超过阈值，建议简化逻辑",
        "severity": "medium",
    },

    # 标准库优先规则
    "stdlib_requests": {
        "id": "STDLIB-001",
        "name": "使用标准库替代 requests",
        "category": "standard_library",
        "description": "轻度使用可考虑 urllib.request (标准库)",
        "severity": "info",
    },
}


class OptimizationCheck(Check):
    """代码优化检查器（Ponytail 集成）

    检查项：
    1. YAGNI 原则：检测过度抽象、未使用的代码
    2. 复杂度控制：圈复杂度、认知复杂度
    3. 过度工程化：检测过度设计
    4. 标准库优先：避免重复造轮子

    战术设计：
    - 默认不启用，需 --optimize 或配置 optimization: true
    - 每条规则有 rule_id，便于报告统计
    - 结果分为技术债务类别：code_simplification / complexity / standard_library
    """

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        super().__init__(project_root, config)
        self.name = "OptimizationCheck"
        self.config = config or {}

        # 配置参数
        self.max_complexity = self.config.get("max_complexity", 10)
        self.max_function_length = self.config.get("max_function_length", 50)
        self.max_cognitive_complexity = self.config.get("max_cognitive_complexity", 15)
        self.check_yagni = self.config.get("check_yagni", True)
        self.check_dead_code = self.config.get("check_dead_code", True)
        self.check_duplicate_code = self.config.get("check_duplicate_code", False)  # 默认关闭（性能）
        self.check_stdlib = self.config.get("check_stdlib", True)
        self.enabled = self.config.get("optimization", False)  # 默认关闭

    def run(self) -> list[CheckResult]:
        """运行优化检查

        如果未启用（默认），直接返回空列表。
        需通过 --optimize 或配置开启。
        """
        if not self.enabled:
            return [CheckResult(
                type="skip",
                level="INFO",
                message="优化检查未启用（使用 --optimize 或配置 optimization: true 开启）",
            )]

        results = []

        # 1. 检查修改的文件（快速模式）
        changed_files = self._get_changed_files()
        if not changed_files:
            return [CheckResult(
                type="pass",
                level="INFO",
                message="没有检测到修改的文件",
            )]

        # 2. 逐个检查文件
        for file_path in changed_files:
            if file_path.suffix in [".py", ".ts", ".tsx", ".js", ".jsx"]:
                file_results = self._check_file(file_path)
                results.extend(file_results)

        return results

    def _get_changed_files(self) -> list[Path]:
        """获取修改的文件列表（git diff）"""
        import subprocess
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=ACMR"],
                cwd=str(self.project.resolve()),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return []
            files = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    file_path = self.project / line
                    if file_path.exists():
                        files.append(file_path)
            return files
        except Exception:
            return []

    def _check_file(self, file_path: Path) -> list[CheckResult]:
        """检查单个文件"""
        results = []

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return [CheckResult(
                type="warn",
                level="WARN",
                file=str(file_path.relative_to(self.project)),
                message="无法读取文件",
            )]

        # Python 文件：AST 分析
        if file_path.suffix == ".py":
            results.extend(self._check_python(file_path, content))

        # TypeScript/JavaScript 文件：正则检查
        elif file_path.suffix in [".ts", ".tsx", ".js", ".jsx"]:
            results.extend(self._check_typescript(file_path, content))

        return results

    # ==================== Python 检查 ====================

    def _check_python(self, file_path: Path, content: str) -> list[CheckResult]:
        """检查 Python 文件"""
        results = []

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return [self.fail(
                "Python 语法错误",
                file=str(file_path.relative_to(self.project)),
            )]

        # 1. 复杂度检查
        if self.config.get("check_complexity", True):
            results.extend(self._check_complexity(file_path, tree))
            results.extend(self._check_cognitive_complexity(file_path, tree))

        # 2. YAGNI 检查
        if self.check_yagni:
            results.extend(self._check_yagni_python(file_path, content, tree))
            results.extend(self._check_dead_code(file_path, tree))
            results.extend(self._check_excessive_comments(file_path, content))

        # 2.1 重复代码检查（可选，性能消耗大）
        if self.check_duplicate_code:
            results.extend(self._check_duplicate_code(file_path, content))

        # 3. 标准库优先检查
        if self.check_stdlib:
            results.extend(self._check_stdlib_python(file_path, content))

        return results

    # ==================== TypeScript 检查 ====================

    def _check_typescript(self, file_path: Path, content: str) -> list[CheckResult]:
        """检查 TypeScript/JavaScript 文件"""
        results = []

        # 1. 复杂度检查（基于函数长度和条件数量）
        if self.config.get("check_complexity", True):
            results.extend(self._check_complexity_ts(file_path, content))

        # 2. YAGNI 检查
        if self.check_yagni:
            results.extend(self._check_yagni_ts(file_path, content))

        return results

    # ==================== 复杂度检查 ====================

    def _check_complexity(self, file_path: Path, tree: ast.AST) -> list[CheckResult]:
        """检查圈复杂度（Python）"""
        results = []
        rule = OPTIMIZATION_RULES["complexity_cyclomatic"]

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = self._calculate_cyclomatic_complexity(node)
                if complexity > self.max_complexity:
                    results.append(self.warn(
                        f"[{rule['id']}] {rule['name']}: {complexity} > {self.max_complexity}，建议拆分",
                        file=str(file_path.relative_to(self.project)),
                        line=node.lineno,
                    ))

        return results

    def _calculate_cyclomatic_complexity(self, node: ast.AST) -> int:
        """计算圈复杂度（McCabe）"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (
                ast.If, ast.While, ast.For, ast.AsyncFor,
                ast.ExceptHandler, ast.With, ast.AsyncWith,
            )):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.IfExp,)):
                complexity += 1
        return complexity

    def _check_cognitive_complexity(self, file_path: Path, tree: ast.AST) -> list[CheckResult]:
        """检查认知复杂度（Cognitive Complexity）

        认知复杂度衡量代码的可读性和理解难度。
        与圈复杂度不同，它更关注人类理解代码的难度。

        评分规则（SonarSource）：
        - 顺序执行：+1（每个结构）
        - if/else：+1（每个分支）
        - switch/case：+1（每个 case）
        - for/while/do-while：+2（循环）
        - 嵌套结构：+1（每增加一层嵌套）
        - 递归：+3
        """
        results = []
        rule = OPTIMIZATION_RULES["complexity_cognitive"]

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = self._calculate_cognitive_complexity(node)
                if complexity > self.max_cognitive_complexity:
                    results.append(self.warn(
                        f"[{rule['id']}] {rule['name']}: {complexity} > {self.max_cognitive_complexity}，建议简化逻辑",
                        file=str(file_path.relative_to(self.project)),
                        line=node.lineno,
                    ))

        return results

    def _calculate_cognitive_complexity(self, func_node: ast.AST) -> int:
        """计算认知复杂度

        参考：SonarSource 认知复杂度规范
        https://www.sonarsource.com/resources/why-cognitive-complexity/
        """
        complexity = 0
        nesting_level = 0

        # 递归遍历函数体
        def visit(node, nesting: int = 0):
            nonlocal complexity

            # 1. 顺序执行结构：+1（每个）
            if isinstance(node, ast.If):
                complexity += 1
                # if-else：else 分支额外 +1
                if node.orelse:
                    complexity += 1
                    # 遍历 else 分支
                    for child in node.orelse:
                        visit(child, nesting + 1)
                # 遍历 if 分支
                for child in node.body:
                    visit(child, nesting + 1)
                return

            elif isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
                # 循环：+2
                complexity += 2
                # 遍历循环体
                for child in node.body:
                    visit(child, nesting + 1)
                # 遍历 else 分支（循环正常结束）
                if node.orelse:
                    for child in node.orelse:
                        visit(child, nesting + 1)
                return

            elif isinstance(node, (ast.With, ast.AsyncWith)):
                # with 语句：+1
                complexity += 1
                for child in node.body:
                    visit(child, nesting + 1)
                return

            elif isinstance(node, ast.Try):
                # try 块：+1
                complexity += 1
                # 遍历 try 块
                for child in node.body:
                    visit(child, nesting + 1)
                # 遍历 except 处理器
                for handler in node.handlers:
                    visit(handler, nesting + 1)
                # 遍历 else 和 finally
                for child in node.orelse:
                    visit(child, nesting + 1)
                for child in node.finalbody:
                    visit(child, nesting + 1)
                return

            elif isinstance(node, ast.ExceptHandler):
                # except 处理器：+1
                complexity += 1
                for child in node.body:
                    visit(child, nesting + 1)
                return

            elif isinstance(node, ast.Match):
                # match-case：+1（每个 case）
                complexity += 1
                for case in node.cases:
                    for child in case.body:
                        visit(child, nesting + 1)
                return

            # 2. 嵌套惩罚：+1（每增加一层嵌套）
            # 递归遍历子节点
            for child in ast.iter_child_nodes(node):
                visit(child, nesting + 1)

        visit(func_node)
        return complexity

    def _check_complexity_ts(self, file_path: Path, content: str) -> list[CheckResult]:
        """检查 TypeScript 复杂度（简化版）"""
        results = []
        rule = OPTIMIZATION_RULES["complexity_function_length"]
        lines = content.split("\n")

        in_function = False
        function_start = 0
        function_name = ""
        brace_depth = 0

        for i, line in enumerate(lines, 1):
            if re.match(r'\s*(async\s+)?function\s+\w+', line) or \
               re.match(r'\s*\w+\s*\(.*\)\s*{', line) or \
               '=>' in line:
                if not in_function:
                    in_function = True
                    function_start = i
                    match = re.search(r'function\s+(\w+)|(\w+)\s*\(', line)
                    function_name = match.group(1) or match.group(2) if match else "anonymous"
                    brace_depth = line.count('{') - line.count('}')

            if in_function:
                brace_depth += line.count('{') - line.count('}')
                if brace_depth <= 0:
                    function_length = i - function_start + 1
                    if function_length > self.max_function_length:
                        results.append(self.warn(
                            f"[{rule['id']}] {rule['name']}: {function_length} 行，建议拆分",
                            file=str(file_path.relative_to(self.project)),
                            line=function_start,
                        ))
                    in_function = False

        return results

    # ==================== YAGNI 检查 ====================

    def _check_yagni_python(self, file_path: Path, content: str, tree: ast.AST) -> list[CheckResult]:
        """检查 Python YAGNI 原则"""
        results = []
        rule_unused = OPTIMIZATION_RULES["yagni_unused_imports"]
        rule_todo = OPTIMIZATION_RULES["yagni_todo_fixme"]
        rule_abstract = OPTIMIZATION_RULES["yagni_over_abstraction"]

        # 1. 检测未使用的 import（简化版：数量过多警告）
        if content.count('import ') > 5:
            results.append(self.warn(
                f"[{rule_unused['id']}] {rule_unused['name']}",
                file=str(file_path.relative_to(self.project)),
            ))

        # 2. 检测 TODO/FIXME
        todo_count = len(re.findall(r'#\s*TODO|#\s*FIXME|#\s*XXX', content, re.IGNORECASE))
        if todo_count > 3:
            results.append(self.warn(
                f"[{rule_todo['id']}] {rule_todo['name']}: {todo_count} 个",
                file=str(file_path.relative_to(self.project)),
            ))

        # 3. 检测过度抽象（函数/类定义过多）
        func_count = len([n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))])
        class_count = len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)])
        if func_count + class_count > 20:
            results.append(self.warn(
                f"[{rule_abstract['id']}] {rule_abstract['name']}: {func_count} 函数 + {class_count} 类",
                file=str(file_path.relative_to(self.project)),
            ))

        return results

    def _check_dead_code(self, file_path: Path, tree: ast.AST) -> list[CheckResult]:
        """检查死代码（无法访问的代码）

        检测场景：
        1. return 语句后的代码
        2. raise 语句后的代码
        3. break/continue 后的代码（在循环中）
        4. except 块中已捕获的异常后
        """
        results = []
        rule = OPTIMIZATION_RULES["yagni_dead_code"]
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.split('\n')

        class DeadCodeDetector(ast.NodeVisitor):
            def __init__(self):
                self.issues = []
                self.current_function = None

            def visit_FunctionDef(self, node: ast.FunctionDef):
                old_func = self.current_function
                self.current_function = node.name
                self.generic_visit(node)
                self.current_function = old_func

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                self.visit_FunctionDef(node)

            def _check_after_return(self, node: ast.AST, return_lines: set[int]):
                """检查 return 语句后的代码"""
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, ast.Expr) and hasattr(child, 'lineno'):
                        if child.lineno in return_lines:
                            # 检查是否是字符串字面量（文档字符串）
                            if isinstance(child.value, ast.Constant) and isinstance(child.value.value, str):
                                continue
                            # 检查是否是注释
                            line_content = lines[child.lineno - 1].strip() if child.lineno <= len(lines) else ""
                            if line_content.startswith('#'):
                                continue
                            self.issues.append({
                                'line': child.lineno,
                                'message': f"return 后的不可达代码"
                            })

            def visit_If(self, node: ast.If):
                # 检查 if 和 else 分支
                self._check_after_return(node, {n.lineno for n in ast.walk(node) if isinstance(n, ast.Return)})
                self.generic_visit(node)

            def visit_For(self, node: ast.For):
                self._check_after_return(node, {n.lineno for n in ast.walk(node) if isinstance(n, ast.Return)})
                self.generic_visit(node)

            def visit_While(self, node: ast.While):
                self._check_after_return(node, {n.lineno for n in ast.walk(node) if isinstance(n, ast.Return)})
                self.generic_visit(node)

            def visit_Try(self, node: ast.Try):
                # 检查每个 except 块
                for handler in node.handlers:
                    self._check_after_return(handler, {n.lineno for n in ast.walk(handler) if isinstance(n, ast.Return)})
                self.generic_visit(node)

        try:
            detector = DeadCodeDetector()
            detector.visit(tree)

            # 去重：同一行只报告一次
            seen_lines = set()
            for issue in detector.issues:
                if issue['line'] not in seen_lines:
                    seen_lines.add(issue['line'])
                    results.append(self.warn(
                        f"[{rule['id']}] {rule['name']}: {issue['message']}",
                        file=str(file_path.relative_to(self.project)),
                        line=issue['line'],
                    ))
        except Exception:
            pass  # 静默失败

        return results

    def _check_excessive_comments(self, file_path: Path, content: str) -> list[CheckResult]:
        """检查过度注释

        规则：
        - 注释行数 > 代码行数的 30%，提示精简
        - 单个函数注释 > 10 行，建议精简
        """
        results = []
        rule = OPTIMIZATION_RULES["yagni_excessive_comments"]
        lines = content.split('\n')

        # 统计代码行和注释行
        code_lines = 0
        comment_lines = 0
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if stripped.startswith('#'):
                comment_lines += 1
            else:
                code_lines += 1

        # 整体注释比例检查
        if code_lines > 0:
            comment_ratio = comment_lines / code_lines
            if comment_ratio > 0.3:
                results.append(self.warn(
                    f"[{rule['id']}] {rule['name']}: {comment_lines}/{code_lines} ({comment_ratio:.0%})",
                    file=str(file_path.relative_to(self.project)),
                ))

        # 单个函数注释检查（简化版：检查大段连续注释）
        consecutive_comments = 0
        max_consecutive = 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#'):
                consecutive_comments += 1
                max_consecutive = max(max_consecutive, consecutive_comments)
            else:
                consecutive_comments = 0

        if max_consecutive > 10:
            results.append(self.warn(
                f"[{rule['id']}] {rule['name']}: 连续注释 {max_consecutive} 行，建议精简",
                file=str(file_path.relative_to(self.project)),
            ))

        return results

    def _check_duplicate_code(self, file_path: Path, content: str) -> list[CheckResult]:
        """检查重复代码（简化版）

        性能优化：
        - 默认关闭（--check-duplicate-code 启用）
        - 只检查 >=5 行的代码块
        - 使用简单的字符串匹配（非精确 AST）
        """
        results = []
        rule = OPTIMIZATION_RULES["yagni_duplicate_code"]
        lines = content.split('\n')

        # 简单的滑动窗口检测（>=5 行）
        min_duplicate_lines = 5
        code_blocks = {}

        for i in range(len(lines) - min_duplicate_lines + 1):
            block = '\n'.join(lines[i:i + min_duplicate_lines])
            # 忽略空行和注释块
            if block.strip() and not all(l.strip().startswith('#') or not l.strip() for l in lines[i:i + min_duplicate_lines]):
                if block in code_blocks:
                    code_blocks[block].append(i + 1)
                else:
                    code_blocks[block] = [i + 1]

        # 报告重复块（出现 >=2 次）
        for block, line_numbers in code_blocks.items():
            if len(line_numbers) >= 2:
                results.append(self.warn(
                    f"[{rule['id']}] {rule['name']}: 在行 {line_numbers} 发现重复代码块",
                    file=str(file_path.relative_to(self.project)),
                    line=line_numbers[0],
                ))
                break  # 只报告第一组

        return results

    def _check_yagni_ts(self, file_path: Path, content: str) -> list[CheckResult]:
        """检查 TypeScript YAGNI 原则"""
        results = []
        rule_unused = OPTIMIZATION_RULES["yagni_unused_imports"]
        rule_todo = OPTIMIZATION_RULES["yagni_todo_fixme"]
        rule_abstract = OPTIMIZATION_RULES["yagni_over_abstraction"]

        # 1. 检测 unused import
        import_lines = [line for line in content.split('\n') if 'import ' in line and 'from ' in line]
        if len(import_lines) > 10:
            results.append(self.warn(
                f"[{rule_unused['id']}] {rule_unused['name']}",
                file=str(file_path.relative_to(self.project)),
            ))

        # 2. 检测 TODO/FIXME
        todo_count = len(re.findall(r'//\s*TODO|//\s*FIXME|//\s*XXX', content, re.IGNORECASE))
        if todo_count > 3:
            results.append(self.warn(
                f"[{rule_todo['id']}] {rule_todo['name']}: {todo_count} 个",
                file=str(file_path.relative_to(self.project)),
            ))

        # 3. 检测过度抽象（接口/类型定义过多）
        interface_count = len(re.findall(r'\binterface\s+\w+', content))
        type_count = len(re.findall(r'\btype\s+\w+', content))
        if interface_count + type_count > 10:
            results.append(self.warn(
                f"[{rule_abstract['id']}] {rule_abstract['name']}: {interface_count + type_count} 个",
                file=str(file_path.relative_to(self.project)),
            ))

        # 4. TypeScript 专项检查
        results.extend(self._check_typescript_specifics(file_path, content))

        return results

    def _check_typescript_specifics(self, file_path: Path, content: str) -> list[CheckResult]:
        """TypeScript 专项检查

        检查项：
        1. any 类型滥用
        2. 过度嵌套的三元运算符
        3. 未使用的类型定义（简化版）
        """
        results = []
        lines = content.split('\n')

        # 规则定义
        rule_any = {
            "id": "TS-001",
            "name": "any 类型滥用",
            "category": "type_safety",
            "description": "使用 any 类型会失去 TypeScript 的类型安全优势",
            "severity": "medium",
        }
        rule_nested_ternary = {
            "id": "TS-002",
            "name": "过度嵌套的三元运算符",
            "category": "readability",
            "description": "嵌套三元运算符难以阅读，建议改用 if-else",
            "severity": "medium",
        }

        # 1. 检查 any 类型滥用
        any_count = len(re.findall(r':\s*any\b|\bany\s*[,\]=\)]', content))
        if any_count > 3:
            results.append(self.warn(
                f"[{rule_any['id']}] {rule_any['name']}: {any_count} 个",
                file=str(file_path.relative_to(self.project)),
            ))
        elif any_count > 0:
            # 单个 any 也提示（低优先级）
            for i, line in enumerate(lines, 1):
                if re.search(r':\s*any\b|\bany\s*[,\]=\)]', line):
                    results.append(self.info(
                        f"[{rule_any['id']}] {rule_any['name']}: 考虑使用更具体的类型",
                        file=str(file_path.relative_to(self.project)),
                        line=i,
                    ))
                    break  # 只提示一次

        # 2. 检查过度嵌套的三元运算符
        max_nesting = 0
        current_nesting = 0
        for line in lines:
            # 简单的嵌套检测：一行中多个 ?:
            ternary_count = len(re.findall(r'\?.*:.*\?', line))
            if ternary_count > 0:
                current_nesting = ternary_count + 1
                max_nesting = max(max_nesting, current_nesting)

        if max_nesting > 2:
            results.append(self.warn(
                f"[{rule_nested_ternary['id']}] {rule_nested_ternary['name']}: 嵌套 {max_nesting} 层",
                file=str(file_path.relative_to(self.project)),
            ))

        return results

    # ==================== 标准库优先检查 ====================

    def _check_stdlib_python(self, file_path: Path, content: str) -> list[CheckResult]:
        """检查 Python 标准库优先原则"""
        results = []
        rule = OPTIMIZATION_RULES["stdlib_requests"]

        # 常见可被标准库替代的第三方包
        third_party_alternatives = {
            'requests': 'urllib.request (标准库)',
            'numpy': 'array module (标准库，轻度使用)',
            'pandas': 'csv module (标准库，轻度使用)',
            'tqdm': '手动进度条 (10行内实现)',
        }

        for package, alternative in third_party_alternatives.items():
            if f'import {package}' in content or f'from {package}' in content:
                results.append(self.warn(
                    f"[{rule['id']}] {rule['name']}: 使用 {package} → {alternative}",
                    file=str(file_path.relative_to(self.project)),
                ))

        return results

    # ==================== 辅助方法 ====================

    def get_rule_statistics(self) -> dict[str, Any]:
        """获取规则统计信息（用于报告）

        返回：
            {
                "total_rules": 6,
                "categories": {
                    "code_simplification": 3,
                    "complexity": 2,
                    "standard_library": 1
                }
            }
        """
        categories = {}
        for rule in OPTIMIZATION_RULES.values():
            cat = rule["category"]
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_rules": len(OPTIMIZATION_RULES),
            "categories": categories,
            "rules": OPTIMIZATION_RULES,
        }

    def categorize_result(self, result: CheckResult) -> str:
        """将结果分类为技术债务类型

        返回：code_simplification / complexity / standard_library
        """
        msg = result.message
        if "[YAGNI-" in msg:
            return "code_simplification"
        elif "[COMPLEX-" in msg:
            return "complexity"
        elif "[STDLIB-" in msg:
            return "standard_library"
        else:
            return "other"
