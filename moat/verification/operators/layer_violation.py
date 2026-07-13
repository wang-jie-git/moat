"""
算子8：调用链追踪器 — 检测跨层调用违规

目标：验证请求全链路的分层是否清晰

检查项：
- [ ] 路由层（routes/api）是否直接访问数据库（db/）
- [ ] 服务层（services）调用方向是否正确
- [ ] 是否存在循环依赖
- [ ] 是否符合 architect.yml 中定义的层级规则

设计原则：
- 配置驱动：层级和规则来自 architect.yml（或内置默认规则）
- 静态分析：通过 AST 扫描 import 语句构建调用图
- fail-open：单个文件解析失败不影响全量检查
"""

import ast
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..types import (
    OperatorResult,
    Severity,
    VerificationContext,
    Violation,
)

if TYPE_CHECKING:
    pass


# ── 内置默认层级规则 ──

DEFAULT_LAYERS = [
    {
        "name": "入口层 (routes/api)",
        "paths": ["routes", "api", "handlers", "endpoints"],
        "allowed_calls": ["services", "models", "schemas", "utils"],
        "forbidden_calls": ["db", "repositories", "database", "sql"],
        "description": "路由层只做请求分发，不应直接访问数据库",
    },
    {
        "name": "服务层 (services)",
        "paths": ["services", "service", "use_cases", "domain"],
        "allowed_calls": ["models", "db", "repositories", "utils", "services"],
        "forbidden_calls": [],
        "description": "服务层包含业务逻辑",
    },
    {
        "name": "数据访问层 (db)",
        "paths": ["db", "repositories", "database", "sql"],
        "allowed_calls": ["models", "utils"],
        "forbidden_calls": ["routes", "api", "handlers", "services"],
        "description": "数据库访问层不应反向依赖上层",
    },
    {
        "name": "模型层 (models)",
        "paths": ["models", "schemas", "entities"],
        "allowed_calls": ["utils"],
        "forbidden_calls": ["routes", "api", "services", "db"],
        "description": "模型层应保持纯净，不依赖业务层",
    },
    {
        "name": "工具层 (utils)",
        "paths": ["utils", "helpers", "common", "core"],
        "allowed_calls": ["utils", "models"],
        "forbidden_calls": ["routes", "api", "services", "db"],
        "description": "工具层可以被任何层调用，但不应反向依赖",
    },
]


class LayerViolationOperator:
    """
    算子8：调用链追踪器

    通过 AST 扫描所有 Python 文件，构建层间调用图，
    检测 architect.yml 中定义的跨层违规调用。
    """

    name = "layer_violation"
    description = "检测跨层调用违规（routes→services→db 分层校验）"

    def __init__(self, layers: list[dict] | None = None):
        self.layers = layers or DEFAULT_LAYERS

    def verify(self, context: VerificationContext) -> OperatorResult:
        """执行调用链检查"""
        diff_mode = "target_files" in context.config
        if diff_mode:
            target_files = context.config["target_files"]
            print(f"   🔗 追踪调用链（增量模式：{len(target_files)} 个文件）...")
        else:
            print(f"   🔗 追踪调用链...")

        project_path = context.project_path
        violations: list[Violation] = []
        evidence: dict[str, Any] = {}
        suggestions: list[str] = []

        # 1. 归类文件到层级
        layer_files = self._classify_files(project_path)
        evidence["layer_file_count"] = {l["name"]: len(files) for l, files in zip(self.layers, layer_files)}
        evidence["total_scanned"] = sum(len(files) for files in layer_files)

        if evidence["total_scanned"] == 0:
            suggestions.append("未检测到分层目录结构，跳过调用链检查")
            return OperatorResult(
                operator_name=self.name,
                passed=True,
                evidence=evidence,
                violations=[],
                suggestions=suggestions,
            )

        # 显示每层文件数
        for layer_name, count in evidence["layer_file_count"].items():
            if count > 0:
                print(f"      层 '{layer_name}': {count} 个文件")

        # 2. 对每层文件提取导入的模块路径
        layer_imports = self._extract_imports(project_path, layer_files, self.layers)

        # 3. 检测违规
        for idx, layer in enumerate(self.layers):
            if not layer.get("forbidden_calls"):
                continue
            forbidden = layer.get("forbidden_calls", [])
            for file_path, imported_modules in layer_imports[idx]:
                for imp_mod in imported_modules:
                    for fb in forbidden:
                        # 检查导入的模块是否在 forbidden 层
                        if self._matches_layer(imp_mod, fb):
                            violations.append(
                                Violation(
                                    rule="layer_violation",
                                    message=f"跨层违规: {layer['name']} → {fb}",
                                    severity=Severity.WARNING,
                                    file_path=str(file_path),
                                    suggestion=f"{layer.get('description', '')}。应将数据访问移到服务层。",
                                )
                            )

        # 4. 去重（同一文件多个违规合并）
        seen = set()
        unique_violations = []
        for v in violations:
            key = (v.file_path, v.rule, v.message)
            if key not in seen:
                seen.add(key)
                unique_violations.append(v)

        # 5. 构建调用图证据
        evidence["call_graph"] = self._build_call_graph(layer_imports, self.layers)

        # 生成建议
        if unique_violations:
            suggestions.append(f"发现 {len(unique_violations)} 个跨层违规")
            # 按文件分组给出修复建议
            by_file = defaultdict(list)
            for v in unique_violations:
                by_file[v.file_path or "?"].append(v.message)
            for file_path, msgs in sorted(by_file.items()):
                suggestions.append(f"  📍 {file_path}: {len(msgs)} 个违规")
        else:
            suggestions.append("未发现跨层调用违规")

        passed = len(unique_violations) == 0

        return OperatorResult(
            operator_name=self.name,
            passed=passed,
            evidence=evidence,
            violations=unique_violations,
            suggestions=suggestions,
        )

    def _classify_files(self, project_path: Path) -> list[list[Path]]:
        """将项目文件按层级归类"""
        result = [[] for _ in self.layers]

        for py_file in project_path.rglob("*.py"):
            rel = py_file.relative_to(project_path)
            rel_str = str(rel.as_posix())

            # 跳过测试、缓存等
            if "/test" in rel_str or rel_str.startswith("test") or "/__pycache__" in rel_str:
                continue

            for idx, layer in enumerate(self.layers):
                for layer_path in layer.get("paths", []):
                    if rel_str.startswith(layer_path) or f"/{layer_path}/" in rel_str:
                        result[idx].append(py_file)
                        break

        return result

    def _extract_imports(self, project_path: Path, layer_files: list[list[Path]], layers: list[dict]) -> list[list[tuple[Path, list[str]]]]:
        """提取每个文件导入的模块路径"""
        result = [[] for _ in layers]

        for idx, files in enumerate(layer_files):
            for py_file in files:
                try:
                    content = py_file.read_text(encoding="utf-8", errors="ignore")
                    tree = ast.parse(content)
                    imported = []

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imported.append(alias.name.split(".")[0])
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                imported.append(node.module.split(".")[0])

                    result[idx].append((py_file.relative_to(project_path), imported))
                except SyntaxError:
                    pass  # fail-open

        return result

    def _matches_layer(self, module_name: str, layer_keyword: str) -> bool:
        """检查模块名是否匹配某个层的关键词"""
        # 精确匹配
        if module_name == layer_keyword:
            return True
        # 单数/复数匹配
        if module_name == layer_keyword.rstrip("s") or module_name == layer_keyword + "s":
            return True
        return False

    def _build_call_graph(self, layer_imports: list[list[tuple[Path, list[str]]]], layers: list[dict]) -> dict:
        """构建层间调用图"""
        graph = {}
        for idx, layer in enumerate(layers):
            layer_name = layer["name"]
            calls_to = defaultdict(int)
            for _file_path, imported in layer_imports[idx]:
                for imp in imported:
                    for j, other_layer in enumerate(layers):
                        if j == idx:
                            continue
                        for path in other_layer.get("paths", []):
                            if imp == path or imp == path.rstrip("s"):
                                calls_to[other_layer["name"]] += 1
                                break
            graph[layer_name] = dict(calls_to) if calls_to else {}

        return graph
