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


class Edge:
    """依赖边（带置信度）"""

    def __init__(self, source: str, target: str, edge_type: str, confidence: float = 1.0):
        self.source = source
        self.target = target
        self.edge_type = edge_type  # "direct_call" | "event_bus" | "config_read" | "import"
        self.confidence = confidence  # 0.0-1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.edge_type,
            "confidence": self.confidence,
        }


class ProjectSkeleton:
    """项目骨架图"""

    def __init__(self, project_root: Path):
        self.project = project_root.resolve()
        self.functions: dict[str, FunctionInfo] = {}
        self.call_graph: dict[str, list[str]] = {}  # caller -> [callees]
        self.reverse_graph: dict[str, list[str]] = {}  # callee -> [callers]
        self.edges: list[Edge] = []  # 带置信度的边

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

                        # 添加带置信度的边
                        confidence = self._detect_call_confidence(child, callee)
                        self.edges.append(Edge(
                            source=caller_key,
                            target=callee,
                            edge_type="direct_call" if confidence >= 0.8 else "indirect_call",
                            confidence=confidence,
                        ))

        except Exception:
            pass

    def _detect_call_confidence(self, call_node: ast.Call, callee_name: str) -> float:
        """检测调用的置信度（0.0-1.0）

        规则：
        - 直接函数调用：1.0
        - 通过对象方法调用：0.9
        - 通过事件总线/回调：0.5
        - 通过配置/字符串动态调用：0.3
        """
        if isinstance(call_node.func, ast.Name):
            # func()
            return 1.0
        elif isinstance(call_node.func, ast.Attribute):
            # obj.method() 或 module.func()
            return 0.9
        elif isinstance(call_node.func, ast.Subscript):
            # config[func_name]() — 动态调用
            return 0.3
        else:
            return 0.7  # 其他情况默认 0.7

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
        """分析变更影响（基于置信度权重）

        Args:
            changes: 变更列表（字典列表）
            skeleton_dict: 项目骨架图字典

        Returns:
            影响分析结果
        """
        impacts = []

        call_graph = skeleton_dict.get("call_graph", {})
        edges = skeleton_dict.get("edges", [])

        # 构建函数到 caller 的映射
        for change in changes:
            func_name = change.get("function")
            if not func_name:
                continue

            # 查找直接调用者
            direct_callers = []
            indirect_callers = []

            for caller, callees in call_graph.items():
                if func_name in callees:
                    # 检查置信度
                    edge = next((e for e in edges if e["target"] == func_name
                                 and e["source"] == caller), None)
                    confidence = edge["confidence"] if edge else 1.0

                    if confidence >= 0.8:
                        direct_callers.append({"caller": caller, "confidence": confidence})
                    else:
                        indirect_callers.append({"caller": caller, "confidence": confidence})

            # 计算风险等级
            total_callers = len(direct_callers) + len(indirect_callers)
            confidence_weight = sum(c["confidence"] for c in direct_callers + indirect_callers)

            if len(direct_callers) >= 5 or confidence_weight >= 4.0:
                risk_level = "high"
            elif len(direct_callers) >= 2 or total_callers >= 5:
                risk_level = "medium"
            else:
                risk_level = "low"

            if direct_callers or indirect_callers:
                all_callers = direct_callers + indirect_callers
                impacts.append({
                    "change": change,
                    "callers": all_callers,  # 兼容 cli.py 的访问方式
                    "direct_callers": direct_callers,
                    "indirect_callers": indirect_callers,
                    "total_callers": total_callers,
                    "confidence_weight": round(confidence_weight, 2),
                    "risk_level": risk_level,
                })

        return impacts

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "functions": [f.to_dict() for f in self.functions.values()],
            "call_graph": self.call_graph,
            "edges": [e.to_dict() for e in self.edges],
            "stats": {
                "total_functions": len(self.functions),
                "total_calls": sum(len(v) for v in self.call_graph.values()),
                "total_edges": len(self.edges),
                "avg_confidence": round(sum(e.confidence for e in self.edges) / len(self.edges), 2)
                if self.edges else 0.0,
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
