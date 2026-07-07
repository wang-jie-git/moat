"""Tree-sitter AST 感知模块 — 多语言支持

支持语言：
- Python
- TypeScript/JavaScript
- Go
- Rust

功能：
- 构建函数调用图（跨语言）
- 增量对比（语言无关）
- 影响域识别（语言无关）
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any


class TreeSitterBuilder:
    """Tree-sitter AST 构建器

    使用 tree-sitter 库解析多语言代码，构建统一的骨架图。
    """

    # 语言到文件扩展名的映射
    LANGUAGE_EXTENSIONS = {
        "python": [".py"],
        "typescript": [".ts", ".tsx"],
        "javascript": [".js", ".jsx"],
        "go": [".go"],
        "rust": [".rs"],
    }

    def __init__(self, project_root: Path):
        self.project = project_root.resolve()
        self.functions: dict[str, dict[str, Any]] = {}
        self.call_graph: dict[str, list[str]] = {}
        self.reverse_graph: dict[str, list[str]] = {}
        self.language_stats: dict[str, dict[str, int]] = {}

    def build(self, languages: list[str] | None = None) -> dict[str, Any]:
        """构建多语言项目骨架图

        Args:
            languages: 要解析的语言列表（如 ["python", "typescript"]）
                       None 表示自动检测

        Returns:
            统一的骨架图数据
        """
        if languages is None:
            # 自动检测项目语言
            languages = self._detect_languages()

        for language in languages:
            self._build_language(language)

        return self.to_dict()

    def _detect_languages(self) -> list[str]:
        """自动检测项目语言"""
        detected = set()
        for file_path in self.project.rglob("*"):
            if file_path.is_file():
                for lang, exts in self.LANGUAGE_EXTENSIONS.items():
                    if file_path.suffix in exts:
                        detected.add(lang)
        return sorted(detected)

    def _build_language(self, language: str):
        """构建指定语言的骨架图"""
        try:
            from tree_sitter import Parser
        except ImportError:
            raise ImportError(
                "tree-sitter 未安装。请运行：\n"
                "  pip install tree-sitter\n"
                "  pip install tree-sitter-python tree-sitter-typescript tree-sitter-go tree-sitter-rust"
            )

        # 获取文件扩展名
        extensions = self.LANGUAGE_EXTENSIONS.get(language, [])
        if not extensions:
            return

        # 收集文件
        files = []
        for ext in extensions:
            files.extend(self.project.rglob(f"*{ext}"))

        # 过滤
        files = [
            f for f in files
            if not any(p in f.parts for p in (
                ".venv", "venv", "__pycache__", ".git", "node_modules",
                "build", "dist", "tests", "target", "vendor"
            ))
        ]

        if not files:
            return

        # 创建解析器
        try:
            language_module = self._load_language(language)
            parser = Parser()
            parser.language = language_module
        except Exception as e:
            print(f"⚠️  无法加载 {language} 解析器: {e}")
            return

        # 解析文件
        func_count = 0
        call_count = 0
        for file_path in files:
            try:
                source = file_path.read_text(encoding="utf-8")
                tree = parser.parse(bytes(source, "utf-8"))
                rel_path = str(file_path.relative_to(self.project))

                self._extract_functions(tree.root_node, rel_path, language)
                func_count += len([f for f in self.functions.values() if f["file"] == rel_path])
                call_count += sum(len(self.call_graph.get(k, [])) for k in self.call_graph if k.startswith(rel_path))
            except Exception:
                pass  # 跳过无法解析的文件

        self.language_stats[language] = {
            "files": len(files),
            "functions": func_count,
            "calls": call_count,
        }

    def _load_language(self, language: str) -> Any:
        """加载 tree-sitter 语言模块"""
        from tree_sitter import Language

        module_map = {
            "python": "tree_sitter_python",
            "typescript": "tree_sitter_typescript",
            "javascript": "tree_sitter_javascript",
            "go": "tree_sitter_go",
            "rust": "tree_sitter_rust",
        }

        module_name = module_map.get(language)
        if not module_name:
            raise ValueError(f"不支持的语言: {language}")

        module = importlib.import_module(module_name)

        # tree-sitter-typescript 包有两个语言
        if language == "typescript":
            return Language(module.language_typescript())
        elif language == "javascript":
            return Language(module.language_javascript())
        else:
            return Language(module.language())

    def _extract_functions(self, root_node: Any, file_path: str, language: str):
        """提取函数定义（语言无关）

        Args:
            root_node: tree-sitter AST 根节点
            file_path: 相对文件路径
            language: 语言类型
        """
        # 不同语言的函数节点类型
        func_node_types = {
            "python": ["function_definition"],
            "typescript": ["function_declaration", "method_definition", "arrow_function"],
            "javascript": ["function_declaration", "method_definition", "arrow_function"],
            "go": ["function_declaration", "method_declaration"],
            "rust": ["function_item", "function_signature_item"],
        }

        func_types = func_node_types.get(language, [])
        if not func_types:
            return

        # 遍历 AST
        def traverse(node):
            if node.type in func_types:
                # 提取函数名
                func_name = self._extract_function_name(node, language)
                if func_name:
                    func_key = f"{file_path}::{func_name}"

                    # 提取行号
                    start_point = node.start_point
                    line = start_point[0] + 1  # tree-sitter 使用 0-based 行号

                    self.functions[func_key] = {
                        "name": func_name,
                        "file": file_path,
                        "line": line,
                        "language": language,
                    }

                    # 提取函数内调用
                    calls = self._extract_calls(node, language)
                    self.call_graph[func_key] = calls

                    # 构建反向调用图
                    for callee in calls:
                        if callee not in self.reverse_graph:
                            self.reverse_graph[callee] = []
                        self.reverse_graph[callee].append(func_key)

            # 递归遍历子节点
            for child in node.children:
                traverse(child)

        traverse(root_node)

    def _extract_function_name(self, node: Any, language: str) -> str | None:
        """提取函数名（语言相关）"""
        # 查找 identifier 或 name 子节点
        for child in node.children:
            if child.type in ("identifier", "property_identifier", "wildcard_identifier"):
                return child.text.decode("utf-8")
        return None

    def _extract_calls(self, func_node: Any, language: str) -> list[str]:
        """提取函数内调用（语言相关）

        Args:
            func_node: 函数 AST 节点
            language: 语言类型

        Returns:
            调用的函数名列表
        """
        calls = []

        # 调用节点类型
        call_types = {
            "python": ["call"],
            "typescript": ["call_expression"],
            "javascript": ["call_expression"],
            "go": ["call_expression"],
            "rust": ["call_expression"],
        }

        call_type = call_types.get(language, ["call"])

        def traverse(node):
            if node.type in call_type:
                # 提取被调用的函数名
                callee = self._extract_callee_name(node, language)
                if callee:
                    calls.append(callee)

            for child in node.children:
                traverse(child)

        traverse(func_node)
        return calls

    def _extract_callee_name(self, call_node: Any, language: str) -> str | None:
        """提取被调用的函数名"""
        # 查找函数节点（通常是第一个子节点）
        for child in call_node.children:
            if child.type in (
                "identifier",
                "member_access_expression",
                "field_expression",
                "selector_expression",
            ):
                if child.type == "identifier":
                    return child.text.decode("utf-8")
                else:
                    # obj.method() 或 obj.func
                    return self._extract_member_access_name(child, language)
        return None

    def _extract_member_access_name(self, node: Any, language: str) -> str | None:
        """提取成员访问名称（如 obj.method）"""
        parts = []
        for child in node.children:
            if child.type == "identifier":
                parts.append(child.text.decode("utf-8"))
            elif child.type == "field_expression":
                field_name = self._extract_field_name(child)
                if field_name:
                    parts.append(field_name)

        return ".".join(parts) if parts else None

    def _extract_field_name(self, node: Any) -> str | None:
        """提取字段名"""
        for child in node.children:
            if child.type == "field_identifier":
                return child.text.decode("utf-8")
        return None

    def to_dict(self) -> dict[str, Any]:
        """转换为统一的骨架图字典"""
        return {
            "functions": list(self.functions.values()),
            "call_graph": self.call_graph,
            "edges": [],  # TODO: 添加置信度边
            "stats": {
                "total_functions": len(self.functions),
                "total_calls": sum(len(v) for v in self.call_graph.values()),
                "total_edges": 0,
                "avg_confidence": 0.0,
                "by_language": self.language_stats,
            },
        }

    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), indent=indent)


def build_multilang_skeleton(
    project_root: str = ".",
    languages: list[str] | None = None,
) -> dict[str, Any]:
    """构建多语言项目骨架图（便捷函数）

    Args:
        project_root: 项目根目录
        languages: 要解析的语言列表（None 表示自动检测）

    Returns:
        统一的骨架图数据
    """
    root = Path(project_root).resolve()
    builder = TreeSitterBuilder(root)
    return builder.build(languages)


if __name__ == "__main__":
    import sys

    project = sys.argv[1] if len(sys.argv) > 1 else "."
    languages = sys.argv[2:] if len(sys.argv) > 2 else None

    skeleton = build_multilang_skeleton(project, languages)

    print(f"✅ 多语言骨架图构建完成")
    print(f"   总函数数: {skeleton['stats']['total_functions']}")
    print(f"   总调用数: {skeleton['stats']['total_calls']}")

    if skeleton["stats"].get("by_language"):
        print(f"\n📊 按语言统计:")
        for lang, stats in skeleton["stats"]["by_language"].items():
            print(f"   - {lang}: {stats['functions']} 个函数, {stats['calls']} 个调用")

    # 导出到 .moat/skeleton_multilang.json
    moat_dir = Path(project) / ".moat"
    moat_dir.mkdir(exist_ok=True)
    (moat_dir / "skeleton_multilang.json").write_text(
        json.dumps(skeleton, indent=2, ensure_ascii=False)
    )
    print(f"\n   ✅ 骨架图已保存: {moat_dir / 'skeleton_multilang.json'}")
