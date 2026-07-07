"""AST 感知模块 — 构建项目骨架图

当前实现：基于 Python ast 模块
未来升级：tree-sitter（多语言支持）

功能：
- 构建函数调用图
- 增量对比（变更影响分析）
- 影响域识别
"""
import ast
import json
from pathlib import Path
from typing import Any


class FunctionInfo:
    """函数信息"""

    def __init__(self, name: str, file_path: str, line: int, calls: list[str] | None = None):
        self.name = name
        self.file_path = file_path
        self.line = line
        self.calls = calls or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "file": self.file_path,
            "line": self.line,
            "calls": self.calls,
        }


class ProjectSkeleton:
    """项目骨架图"""

    def __init__(self, project_root: Path):
        self.project = project_root.resolve()
        self.functions: dict[str, FunctionInfo] = {}
        self.call_graph: dict[str, list[str]] = {}  # caller -> [callees]
        self.reverse_graph: dict[str, list[str]] = {}  # callee -> [callers]

    def build(self, language: str = "python") -> dict[str, Any]:
        """构建项目骨架图

        Args:
            language: 语言类型（当前仅支持 python）

        Returns:
            骨架图数据
        """
        if language == "python":
            self._build_python()
        else:
            raise NotImplementedError(f"Language {language} not supported yet")

        return self.to_dict()

    def _build_python(self):
        """构建 Python 项目骨架图"""
        py_files = list(self.project.rglob("*.py"))

        # 过滤掉不需要的文件
        py_files = [
            f for f in py_files
            if not any(p in f.parts for p in (
                ".venv", "venv", "__pycache__", ".git", "node_modules",
                "build", "dist", "tests", "moat/checks"
            ))
        ]

        # 第一遍：提取所有函数定义
        for file_path in py_files:
            self._extract_functions_from_file(file_path)

        # 第二遍：构建调用图
        for file_path in py_files:
            self._build_call_graph_from_file(file_path)

    def _extract_functions_from_file(self, file_path: Path):
        """从文件提取函数定义"""
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source)

            rel_path = str(file_path.relative_to(self.project))

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_name = node.name
                    key = f"{rel_path}::{func_name}"

                    self.functions[key] = FunctionInfo(
                        name=func_name,
                        file_path=rel_path,
                        line=node.lineno,
                    )
        except Exception:
            pass  # 跳过无法解析的文件

    def _build_call_graph_from_file(self, file_path: Path):
        """从文件构建调用图"""
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source)

            rel_path = str(file_path.relative_to(self.project))

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    caller_name = node.name
                    caller_key = f"{rel_path}::{caller_name}"

                    # 查找函数内的调用
                    callees = []
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            if isinstance(child.func, ast.Name):
                                callees.append(child.func.id)
                            elif isinstance(child.func, ast.Attribute):
                                # method call: obj.method()
                                if isinstance(child.func.value, ast.Name):
                                    callees.append(f"{child.func.value.id}.{child.func.attr}")

                    # 更新函数信息
                    if caller_key in self.functions:
                        self.functions[caller_key].calls = callees

                    # 更新调用图
                    self.call_graph[caller_key] = callees
                    for callee in callees:
                        if callee not in self.reverse_graph:
                            self.reverse_graph[callee] = []
                        self.reverse_graph[callee].append(caller_key)

        except Exception:
            pass

    def find_callers(self, func_name: str) -> list[FunctionInfo]:
        """查找调用某个函数的所有位置

        Args:
            func_name: 函数名称

        Returns:
            调用者函数列表
        """
        callers = []
        for caller_key in self.reverse_graph.get(func_name, []):
            if caller_key in self.functions:
                callers.append(self.functions[caller_key])
        return callers

    def find_impacts(self, file_path: str, line: int) -> list[dict[str, Any]]:
        """查找某个位置的变更影响

        Args:
            file_path: 文件路径
            line: 行号

        Returns:
            影响列表
        """
        # 找到该位置定义的函数
        target_func = None
        for func_key, func_info in self.functions.items():
            if func_info.file_path == file_path and func_info.line == line:
                target_func = func_info
                break

        if not target_func:
            return []

        # 找到所有调用者
        impacts = []
        for caller in self.find_callers(target_func.name):
            impacts.append({
                "file": caller.file_path,
                "line": caller.line,
                "function": caller.name,
                "type": "direct_caller",
            })

        return impacts

    def analyze_impacts(self, changes: list[dict], skeleton_dict: dict) -> list[dict[str, Any]]:
        """分析变更影响

        Args:
            changes: 变更列表（字典列表）
            skeleton_dict: 项目骨架图字典

        Returns:
            影响分析结果
        """
        impacts = []

        call_graph = skeleton_dict.get("call_graph", {})

        for change in changes:
            func_name = change.get("function")
            if func_name:
                # 查找所有调用者
                callers = []
                for caller, callees in call_graph.items():
                    if func_name in callees:
                        callers.append(caller)

                if callers:
                    impacts.append({
                        "change": change,
                        "callers": callers,
                        "risk_level": "high" if len(callers) > 3 else "medium",
                    })

        return impacts

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "functions": [f.to_dict() for f in self.functions.values()],
            "call_graph": self.call_graph,
            "stats": {
                "total_functions": len(self.functions),
                "total_calls": sum(len(v) for v in self.call_graph.values()),
            },
        }

    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), indent=indent)


def build_skeleton(project_root: str = ".") -> ProjectSkeleton:
    """构建项目骨架图（便捷函数）

    Args:
        project_root: 项目根目录

    Returns:
        ProjectSkeleton 实例
    """
    root = Path(project_root).resolve()
    skeleton = ProjectSkeleton(root)
    skeleton.build()
    return skeleton


if __name__ == "__main__":
    # 测试
    import sys

    project = sys.argv[1] if len(sys.argv) > 1 else "."
    skeleton = build_skeleton(project)

    print(f"✅ 项目骨架图构建完成")
    print(f"   函数数: {skeleton.to_dict()['stats']['total_functions']}")
    print(f"   调用数: {skeleton.to_dict()['stats']['total_calls']}")

    # 导出到 .moat/skeleton.json
    moat_dir = Path(project) / ".moat"
    moat_dir.mkdir(exist_ok=True)
    (moat_dir / "skeleton.json").write_text(skeleton.to_json())
    print(f"   ✅ 骨架图已保存: {moat_dir / 'skeleton.json'}")
