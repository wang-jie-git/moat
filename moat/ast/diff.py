"""AST 增量对比模块

检测代码变更并分析影响范围。
"""
import ast
from pathlib import Path
from typing import Any


class CodeChange:
    """代码变更"""

    def __init__(self, change_type: str, file_path: str, line: int | None = None,
                 function: str | None = None, old_code: str | None = None,
                 new_code: str | None = None):
        self.change_type = change_type  # modified/added/deleted
        self.file_path = file_path
        self.line = line
        self.function = function
        self.old_code = old_code
        self.new_code = new_code

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.change_type,
            "file": self.file_path,
            "line": self.line,
            "function": self.function,
        }


class ASTDiffer:
    """AST 增量对比器"""

    def __init__(self, project_root: Path, skeleton: dict | None = None):
        self.project = project_root.resolve()
        self.skeleton = skeleton or {}

    def diff_file(self, file_path: Path, old_content: str | None = None,
                  new_content: str | None = None) -> list[CodeChange]:
        """对比单个文件的变更

        Args:
            file_path: 文件路径
            old_content: 旧内容（如果为 None，尝试从 Git 获取）
            new_content: 新内容（如果为 None，读取当前文件）

        Returns:
            变更列表
        """
        if new_content is None:
            new_content = file_path.read_text(encoding="utf-8")

        if old_content is None:
            # 尝试从 Git 获取旧版本
            old_content = self._get_git_version(file_path)
            if old_content is None:
                return []  # 无法获取旧版本

        # 解析 AST
        try:
            old_tree = ast.parse(old_content)
            new_tree = ast.parse(new_content)
        except SyntaxError:
            return []  # 语法错误，无法对比

        # 对比函数定义
        changes = self._diff_functions(old_tree, new_tree, str(file_path.relative_to(self.project)))

        return changes

    def _diff_functions(self, old_tree: ast.AST, new_tree: ast.AST,
                        file_path: str) -> list[CodeChange]:
        """对比函数定义变更"""
        changes = []

        # 提取函数
        old_funcs = self._extract_funcs(old_tree)
        new_funcs = self._extract_funcs(new_tree)

        # 查找修改的函数
        for name, new_node in new_funcs.items():
            if name in old_funcs:
                old_node = old_funcs[name]
                # 检查是否有实质性变更
                if self._has_substantial_change(old_node, new_node):
                    changes.append(CodeChange(
                        change_type="modified",
                        file_path=file_path,
                        line=new_node.lineno,
                        function=name,
                    ))
            else:
                # 新增函数
                changes.append(CodeChange(
                    change_type="added",
                    file_path=file_path,
                    line=new_node.lineno,
                    function=name,
                ))

        # 查找删除的函数
        for name in old_funcs:
            if name not in new_funcs:
                changes.append(CodeChange(
                    change_type="deleted",
                    file_path=file_path,
                    function=name,
                ))

        return changes

    def _extract_funcs(self, tree: ast.AST) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
        """提取函数定义"""
        funcs = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcs[node.name] = node
        return funcs

    def _has_substantial_change(self, old: ast.AST, new: ast.AST) -> bool:
        """检查是否有实质性变更"""
        # 简化：对比行号或代码哈希
        # TODO: 更精确的 AST diff 算法
        return old.lineno != new.lineno or ast.dump(old) != ast.dump(new)

    def _get_git_version(self, file_path: Path) -> str | None:
        """从 Git 获取文件旧版本"""
        import subprocess

        try:
            rel_path = file_path.relative_to(self.project)
            result = subprocess.run(
                ["git", "show", f"HEAD:{rel_path}"],
                capture_output=True,
                text=True,
                cwd=self.project,
            )
            if result.returncode == 0:
                return result.stdout
        except Exception:
            pass

        return None

    def analyze_impacts(self, changes: list[CodeChange], skeleton: dict) -> list[dict[str, Any]]:
        """分析变更影响

        Args:
            changes: 变更列表
            skeleton: 项目骨架图

        Returns:
            影响分析结果
        """
        impacts = []

        call_graph = skeleton.get("call_graph", {})

        for change in changes:
            if change.function:
                # 查找所有调用者
                callers = []
                for caller, callees in call_graph.items():
                    if change.function in callees:
                        callers.append(caller)

                if callers:
                    impacts.append({
                        "change": change.to_dict(),
                        "callers": callers,
                        "risk_level": "high" if len(callers) > 3 else "medium",
                    })

        return impacts


def diff_project(project_root: str = ".", since: str = "HEAD") -> list[dict[str, Any]]:
    """对比项目变更（基于 Git）

    Args:
        project_root: 项目根目录
        since: Git 参考点（如 HEAD~1）

    Returns:
        变更列表
    """
    import subprocess

    root = Path(project_root).resolve()

    # 获取变更文件
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", since],
            capture_output=True,
            text=True,
            cwd=root,
        )
        if result.returncode != 0:
            return []

        changed_files = result.stdout.strip().split("\n")
        changed_files = [f for f in changed_files if f]  # 过滤空行
    except Exception:
        return []

    # 过滤 Python 文件
    py_files = [f for f in changed_files if f.endswith(".py")]

    # 对比每个文件
    differ = ASTDiffer(root)
    all_changes = []

    for rel_path in py_files:
        file_path = root / rel_path
        if file_path.exists():
            changes = differ.diff_file(file_path)
            for change in changes:
                change_dict = change.to_dict()
                all_changes.append(change_dict)

    return all_changes
