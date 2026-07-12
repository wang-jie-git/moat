"""增强的增量扫描模块（v1.0.8）

改进点：
1. 基于 AST diff 而非纯 git diff
2. 检测函数签名变更的影响域
3. 检测导入变更的影响域
4. 精确识别需要检查的文件和函数
"""
import ast
import hashlib
import subprocess
from pathlib import Path
from typing import Any


class EnhancedChange:
    """增强的代码变更"""

    def __init__(self, change_type: str, file_path: str, line: int | None = None,
                 function: str | None = None, function_signature: str | None = None,
                 old_code: str | None = None, new_code: str | None = None,
                 change_type_detail: str = "body"):
        self.change_type = change_type  # modified/added/deleted
        self.file_path = file_path
        self.line = line
        self.function = function
        self.function_signature = function_signature
        self.old_code = old_code
        self.new_code = new_code
        self.change_type_detail = change_type_detail  # signature/body/import/added/deleted

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.change_type,
            "file": self.file_path,
            "line": self.line,
            "function": self.function,
            "signature": self.function_signature,
            "detail": self.change_type_detail,
        }


class EnhancedASTDiffer:
    """增强的 AST 增量对比器

    特性：
    - 检测函数签名变更
    - 检测函数体变更
    - 检测导入变更
    - 分析变更影响域
    """

    def __init__(self, project_root: Path):
        self.project = project_root.resolve()

    def diff_file(self, file_path: Path, old_content: str | None = None,
                  new_content: str | None = None) -> list[EnhancedChange]:
        """对比单个文件的变更

        Args:
            file_path: 文件路径
            old_content: 旧内容
            new_content: 新内容

        Returns:
            变更列表
        """
        if new_content is None:
            try:
                new_content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                return []

        if old_content is None:
            old_content = self._get_git_version(file_path)
            if old_content is None:
                return []

        changes = []

        # 1. 解析 AST
        try:
            old_tree = ast.parse(old_content)
            new_tree = ast.parse(new_content)
        except SyntaxError:
            return []

        # 2. 检测导入变更
        import_changes = self._diff_imports(old_tree, new_tree, file_path)
        changes.extend(import_changes)

        # 3. 检测函数/类变更
        func_changes = self._diff_functions(old_tree, new_tree, file_path)
        changes.extend(func_changes)

        # 4. 检测全局变量变更
        var_changes = self._diff_globals(old_tree, new_tree, file_path)
        changes.extend(var_changes)

        return changes

    def _diff_imports(self, old_tree: ast.AST, new_tree: ast.AST,
                      file_path: Path) -> list[EnhancedChange]:
        """检测导入变更"""
        changes = []
        # macOS 兼容：使用 resolved 路径解决 /var vs /private/var 符号链接问题
        rel_path = str(file_path.resolve().relative_to(self.project.resolve()))

        old_imports = self._extract_imports(old_tree)
        new_imports = self._extract_imports(new_tree)

        # 新增的导入
        for module, names in new_imports.items():
            if module not in old_imports:
                line = self._find_import_line(new_tree, module)
                changes.append(EnhancedChange(
                    change_type="added",
                    file_path=rel_path,
                    line=line,
                    change_type_detail="import",
                ))
            else:
                # 检查是否增加了新的导入名
                old_names = {name for name, _ in old_imports[module]}
                for name, alias in names:
                    if (name, alias) not in old_names:
                        line = self._find_import_line(new_tree, module)
                        changes.append(EnhancedChange(
                            change_type="added",
                            file_path=rel_path,
                            line=line,
                            change_type_detail="import",
                        ))

        # 删除的导入
        for module in old_imports:
            if module not in new_imports:
                line = self._find_import_line(old_tree, module)
                changes.append(EnhancedChange(
                    change_type="deleted",
                    file_path=rel_path,
                    line=line,
                    change_type_detail="import",
                ))

        return changes

    def _diff_functions(self, old_tree: ast.AST, new_tree: ast.AST,
                        file_path: Path) -> list[EnhancedChange]:
        """检测函数变更"""
        changes = []
        # macOS 兼容：使用 resolved 路径解决 /var vs /private/var 符号链接问题
        rel_path = str(file_path.resolve().relative_to(self.project.resolve()))

        old_funcs = self._extract_functions(old_tree)
        new_funcs = self._extract_functions(new_tree)

        # 新增/修改的函数
        for name, new_node in new_funcs.items():
            old_sig = old_funcs.get(name)

            if old_sig is None:
                # 新增函数
                changes.append(EnhancedChange(
                    change_type="added",
                    file_path=rel_path,
                    line=new_node.lineno,
                    function=name,
                    function_signature=self._get_function_signature(new_node),
                    change_type_detail="added",
                ))
            else:
                # 检查签名变更
                old_sig_str = self._get_function_signature(old_sig)
                new_sig_str = self._get_function_signature(new_node)

                if old_sig_str != new_sig_str:
                    # 签名变更
                    changes.append(EnhancedChange(
                        change_type="modified",
                        file_path=rel_path,
                        line=new_node.lineno,
                        function=name,
                        function_signature=new_sig_str,
                        change_type_detail="signature",
                    ))
                elif self._has_body_change(old_sig, new_node):
                    # 函数体变更
                    changes.append(EnhancedChange(
                        change_type="modified",
                        file_path=rel_path,
                        line=new_node.lineno,
                        function=name,
                        function_signature=new_sig_str,
                        change_type_detail="body",
                    ))

        # 删除的函数
        for name in old_funcs:
            if name not in new_funcs:
                changes.append(EnhancedChange(
                    change_type="deleted",
                    file_path=rel_path,
                    function=name,
                    change_type_detail="deleted",
                ))

        return changes

    def _diff_globals(self, old_tree: ast.AST, new_tree: ast.AST,
                      file_path: Path) -> list[EnhancedChange]:
        """检测全局变量变更"""
        changes = []
        # macOS 兼容：使用 resolved 路径解决 /var vs /private/var 符号链接问题
        rel_path = str(file_path.resolve().relative_to(self.project.resolve()))

        old_globals = self._extract_globals(old_tree)
        new_globals = self._extract_globals(new_tree)

        for name in new_globals:
            if name not in old_globals:
                line = new_globals[name]
                changes.append(EnhancedChange(
                    change_type="added",
                    file_path=rel_path,
                    line=line,
                    function=name,
                    change_type_detail="global",
                ))

        for name in old_globals:
            if name not in new_globals:
                line = old_globals[name]
                changes.append(EnhancedChange(
                    change_type="deleted",
                    file_path=rel_path,
                    line=line,
                    function=name,
                    change_type_detail="global",
                ))

        return changes

    def _extract_imports(self, tree: ast.AST) -> dict[str, list[tuple[str, str]]]:
        """提取导入信息"""
        imports = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                module = node.names[0].name.split('.')[0]
                imports[module] = [(n.name, n.asname) for n in node.names]
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports[module] = [(n.name, n.asname) for n in node.names]

        return imports

    def _extract_functions(self, tree: ast.AST) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
        """提取函数定义"""
        funcs = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcs[node.name] = node
        return funcs

    def _extract_globals(self, tree: ast.AST) -> dict[str, int]:
        """提取全局变量"""
        globals_dict = {}
        for node in tree.body if hasattr(tree, 'body') else []:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        globals_dict[target.id] = node.lineno
        return globals_dict

    def _find_import_line(self, tree: ast.AST, module: str) -> int:
        """找到导入语句的行号"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if node.names[0].name.split('.')[0] == module:
                    return node.lineno
            elif isinstance(node, ast.ImportFrom) and node.module == module:
                return node.lineno
        return 1

    def _get_function_signature(self, func_node: ast.FunctionDef) -> str:
        """获取函数签名"""
        args = func_node.args
        params = []

        # 位置参数
        for arg in args.args:
            params.append(arg.arg)

        # *args
        if args.vararg:
            params.append(f"*{args.vararg.arg}")

        # **kwargs
        if args.kwarg:
            params.append(f"**{args.kwarg.arg}")

        return f"({', '.join(params)})"

    def _has_body_change(self, old: ast.FunctionDef, new: ast.FunctionDef) -> bool:
        """检查函数体是否有变更"""
        old_body_hash = self._hash_ast(old.body)
        new_body_hash = self._hash_ast(new.body)
        return old_body_hash != new_body_hash

    def _hash_ast(self, nodes: list[ast.AST]) -> str:
        """计算 AST 节点的哈希"""
        try:
            code = ast.dump(nodes)
            return hashlib.sha256(code.encode()).hexdigest()[:16]
        except Exception:
            return ""

    def _get_git_version(self, file_path: Path) -> str | None:
        """从 Git 获取文件旧版本"""
        try:
            # macOS 兼容：使用 resolved 路径解决 /var vs /private/var 符号链接问题
            rel_path = file_path.resolve().relative_to(self.project.resolve())
            result = subprocess.run(
                ["git", "show", f"HEAD:{rel_path}"],
                capture_output=True,
                text=True,
                cwd=self.project,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout
        except Exception:
            pass
        return None


def get_affected_files(project_root: Path) -> list[Path]:
    """获取受影响的文件列表（基于 AST diff）

    Args:
        project_root: 项目根目录

    Returns:
        文件路径列表
    """
    differ = EnhancedASTDiffer(project_root)

    # 获取修改的文件
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMR"],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=5,
        )
        if result.returncode != 0:
            return []

        changed_files = [f.strip() for f in result.stdout.split("\n") if f.strip()]
    except Exception:
        return []

    # 过滤并检查实际变更
    affected = []
    for rel_path in changed_files:
        file_path = project_root / rel_path
        if not file_path.exists():
            continue

        if file_path.suffix != ".py":
            continue

        # 检查 AST diff
        changes = differ.diff_file(file_path)
        if changes:
            affected.append(file_path)

    return affected


def analyze_change_impact(project_root: Path, changes: list[EnhancedChange]) -> dict[str, Any]:
    """分析变更影响

    Args:
        project_root: 项目根目录
        changes: 变更列表

    Returns:
        影响分析结果
    """
    impacts = {
        "total_changes": len(changes),
        "added": [],
        "modified": [],
        "deleted": [],
        "affected_files": set(),
    }

    for change in changes:
        impacts["affected_files"].add(change.file_path)

        if change.change_type == "added":
            impacts["added"].append(change.to_dict())
        elif change.change_type == "modified":
            impacts["modified"].append(change.to_dict())
        elif change.change_type == "deleted":
            impacts["deleted"].append(change.to_dict())

    impacts["affected_files"] = sorted(list(impacts["affected_files"]))

    # 计算影响级别
    if len(impacts["modified"]) > 10:
        impacts["risk_level"] = "high"
    elif len(impacts["modified"]) > 5:
        impacts["risk_level"] = "medium"
    else:
        impacts["risk_level"] = "low"

    return impacts
