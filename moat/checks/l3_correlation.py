"""跨系统关联检查 — L3: 改 A 不影响 B"""
from pathlib import Path


def run_correlation_check(project_root: Path) -> list[dict]:
    """检查模块间的依赖关系是否健康"""
    import subprocess
    import sys

    errors = []
    imports_map = _build_import_graph(project_root)

    # 检查循环依赖
    cycles = _find_cycles(imports_map)
    for cycle in cycles[:10]:
        errors.append({
            "file": " -> ".join(cycle[:5]),
            "level": "L3",
            "type": "circular_import",
            "message": f"循环依赖: {' → '.join(cycle[:6])}",
        })

    # 检查核心模块不能依赖边缘模块
    core_modules = _find_core_modules(imports_map, project_root)
    core_set = set(core_modules)

    for mod, deps in imports_map.items():
        if mod in core_set:
            continue
        for dep in deps:
            if dep in core_set:
                # OK: 边缘依赖核心
                pass
    # 检查核心模块之间的依赖
    for mod in core_modules:
        for dep in imports_map.get(mod, []):
            if dep not in core_set and dep:
                errors.append({
                    "file": mod,
                    "level": "L3",
                    "type": "core_depends_on_edge",
                    "message": f"核心模块 {mod} 依赖于非核心模块 {dep}",
                })

    return errors


def _build_import_graph(project_root: Path) -> dict[str, list[str]]:
    """构建模块导入关系图"""
    import ast
    imports = {}

    for f in project_root.rglob("*.py"):
        rel = f.relative_to(project_root)
        parts = rel.parts
        if any(p in (".venv", "venv", "__pycache__", ".git", "node_modules",
                      "build", "dist") for p in parts):
            continue

        mod_name = ".".join(parts[:-1] + (f.stem,))
        if mod_name.startswith("."):
            continue

        try:
            tree = ast.parse(f.read_text())
        except SyntaxError:
            continue

        deps = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    deps.append(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    deps.append(node.module.split(".")[0])

        imports[mod_name] = list(set(deps))

    return imports


def _find_core_modules(imports_map: dict[str, list[str]], project_root: Path) -> list[str]:
    """找到被最多依赖的核心模块"""
    # 计算被引用次数
    ref_count = {}
    for mod, deps in imports_map.items():
        for dep in deps:
            ref_count[dep] = ref_count.get(dep, 0) + 1

    # 被引用最多的前 10% 模块被认为是核心
    if not ref_count:
        return []

    sorted_deps = sorted(ref_count.items(), key=lambda x: -x[1])
    threshold = max(3, len(sorted_deps) // 10)
    return [mod for mod, count in sorted_deps[:threshold]]


def _find_cycles(imports_map: dict[str, list[str]]) -> list[list[str]]:
    """检测循环依赖"""
    cycles = []
    visited = set()
    path = []
    path_set = set()

    def dfs(node):
        if node in path_set:
            cycle_start = path.index(node)
            cycles.append(path[cycle_start:] + [node])
            return
        if node in visited:
            return
        visited.add(node)
        path.append(node)
        path_set.add(node)
        for neighbor in imports_map.get(node, []):
            if neighbor in imports_map:  # 只跟踪项目中存在的模块
                dfs(neighbor)
        path.pop()
        path_set.discard(node)

    for node in imports_map:
        if node not in visited:
            dfs(node)

    return cycles