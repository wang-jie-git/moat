"""L2 架构规则检查 — 代码熵增 + 依赖枢纽识别

这是 Moat v1.0 Phase 2 的核心功能：
1. 代码熵增检测：识别增长过快的文件
2. 依赖枢纽识别：找出被引用最多的核心模块

设计原则：
- 与 L1/L4 检查共享基线数据
- 只检查 Python 文件（可扩展其他语言）
- 性能优先：增量计算，避免全量扫描
"""
import ast
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any


def run_architecture_check(
    project_root: Path,
    baseline: dict[str, Any] | None = None,
    quick_mode: bool = False,
) -> list[dict]:
    """运行 L2 架构规则检查

    Args:
        project_root: 项目根目录
        baseline: 基线数据（可选），用于对比分析
        quick_mode: 是否快速模式（只检查修改的文件）

    Returns:
        检查结果列表
    """
    errors = []

    # 1. 代码熵增检测
    entropy_errors = _detect_code_entropy(project_root, baseline)
    errors.extend(entropy_errors)

    # 2. 依赖枢纽识别（完整模式才运行）
    if not quick_mode:
        hub_errors = _identify_dependency_hubs(project_root)
        errors.extend(hub_errors)

    return errors


def _detect_code_entropy(
    project_root: Path,
    baseline: dict[str, Any] | None = None,
) -> list[dict]:
    """检测代码熵增（文件行数异常增长）

    熵增定义：
    - 高熵增：行数增加 >100%（红色预警）
    - 中熵增：行数增加 >50%（黄色预警）

    Args:
        project_root: 项目根目录
        baseline: 基线数据

    Returns:
        检查结果列表
    """
    errors = []

    # 捕获当前状态
    from moat.checks.l4_baseline import _capture_enhanced_state

    current = _capture_enhanced_state(project_root)

    if not baseline:
        # 无基线，跳过熵增检测
        return errors

    curr_lines = current.get("line_counts", {})
    base_lines = baseline.get("line_counts", {})

    high_entropy_files = []
    medium_entropy_files = []

    for file_path, curr_count in curr_lines.items():
        base_count = base_lines.get(file_path, 0)
        if base_count > 0:
            change_pct = (curr_count - base_count) / base_count * 100

            # 高熵增：行数增加 >100%
            if change_pct > 100:
                high_entropy_files.append((file_path, base_count, curr_count, change_pct))
            # 中熵增：行数增加 >50%
            elif change_pct > 50:
                medium_entropy_files.append((file_path, base_count, curr_count, change_pct))

    # 报告高熵增文件（前 3 个）
    for file_path, base_count, curr_count, change_pct in high_entropy_files[:3]:
        errors.append({
            "file": file_path,
            "level": "L2",
            "type": "high_entropy",
            "message": f"[L2 架构] 代码熵增预警：文件增长 {change_pct:+.1f}%（{base_count} → {curr_count} 行）",
            "suggestion": _generate_entropy_suggestion(file_path, change_pct),
        })

    # 报告中熵增文件（前 3 个）
    for file_path, base_count, curr_count, change_pct in medium_entropy_files[:3]:
        errors.append({
            "file": file_path,
            "level": "L2",
            "type": "medium_entropy",
            "message": f"[L2 架构] 代码增长较快：{change_pct:+.1f}%（{base_count} → {curr_count} 行）",
            "suggestion": "建议检查是否违反单一职责原则，考虑拆分为多个模块",
        })

    # 汇总
    total_entropy = len(high_entropy_files) + len(medium_entropy_files)
    if total_entropy > 6:
        errors.append({
            "file": "codebase",
            "level": "L2",
            "type": "entropy_summary",
            "message": f"[L2 架构] 还有 {total_entropy - 6} 个文件存在熵增风险（使用 --full 查看详情）",
            "suggestion": "建议使用 moat baseline diff 查看完整的熵增报告",
        })

    return errors


def _generate_entropy_suggestion(file_path: str, change_pct: float) -> str:
    """根据熵增程度生成修复建议

    Args:
        file_path: 文件路径
        change_pct: 增长率

    Returns:
        修复建议文本
    """
    if change_pct > 200:
        return "🔴 严重熵增：建议立即拆分为多个职责清晰的模块"
    elif change_pct > 100:
        return "⚠️  高熵增：建议审查文件职责，考虑提取独立模块"
    else:
        return "📈 中等增长：建议定期重构，避免进一步膨胀"


def _identify_dependency_hubs(project_root: Path) -> list[dict]:
    """识别依赖枢纽（被引用最多的模块）

    依赖枢纽定义：
    - 被其他模块导入/引用次数 > N 次的模块
    - 通常是核心基础设施（config, utils, base 等）

    Args:
        project_root: 项目根目录

    Returns:
        检查结果列表（Top 10 依赖枢纽）
    """
    errors = []

    # 统计导入关系
    import_counts = _count_imports(project_root)

    if not import_counts:
        return errors

    # 排序，取 Top 10
    top_hubs = sorted(import_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # 只报告被引用 >5 次的模块
    threshold = 5
    significant_hubs = [(mod, count) for mod, count in top_hubs if count >= threshold]

    if not significant_hubs:
        return errors

    # 报告 Top 5 依赖枢纽
    for rank, (module_path, import_count) in enumerate(significant_hubs[:5], 1):
        errors.append({
            "file": module_path,
            "level": "L2",
            "type": "dependency_hub",
            "message": f"[L2 架构] 依赖枢纽 #{rank}: {module_path}（被引用 {import_count} 次）",
            "suggestion": "核心模块修改需要谨慎，建议增加单元测试覆盖",
        })

    # 汇总
    if len(significant_hubs) > 5:
        errors.append({
            "file": "codebase",
            "level": "L2",
            "type": "dependency_hub_summary",
            "message": f"[L2 架构] 还有 {len(significant_hubs) - 5} 个依赖枢纽（使用 --full 查看详情）",
            "suggestion": "核心模块的修改建议在低峰期进行，并充分测试",
        })

    return errors


def _count_imports(project_root: Path) -> dict[str, int]:
    """统计每个模块被引用的次数

    Args:
        project_root: 项目根目录

    Returns:
        字典 {module_path: import_count}
    """
    import_counts = defaultdict(int)

    # 遍历所有 Python 文件
    for py_file in project_root.rglob("*.py"):
        rel_path = py_file.relative_to(project_root)
        parts = rel_path.parts

        # 跳过虚拟环境、测试文件等
        if any(p.startswith(".venv") or p == "venv" or p in ("__pycache__", ".git", "node_modules",
                     "build", "dist", "tests", "test") for p in parts):
            continue

        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content)

            # 提取所有 import 语句
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        _count_import_from_name(alias.name, project_root, import_counts)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        _count_import_from_name(node.module, project_root, import_counts)

        except Exception:
            # 语法错误或无法解析，跳过
            continue

    return dict(import_counts)


def _count_import_from_name(import_name: str, project_root: Path, import_counts: dict[str, int]) -> None:
    """从导入语句中提取模块路径并计数

    Args:
        import_name: 导入名称（如 "core.session_manager" 或 "os"）
        project_root: 项目根目录
        import_counts: 计数字典（会原地修改）
    """
    # 只统计项目内部模块
    if import_name.startswith("."):
        # 相对导入，暂时跳过
        return

    # 检查是否可能是项目内部模块
    parts = import_name.split(".")
    if len(parts) < 2:
        # 标准库或第三方库（如 os, json, requests），跳过
        return

    # 尝试找到对应的文件
    possible_paths = [
        project_root / import_name.replace(".", "/") / "__init__.py",
        project_root / import_name.replace(".", "/") / ".py",
        project_root / import_name.replace(".", "/") / "py",
    ]

    for path in possible_paths:
        if path.exists():
            rel_path = str(path.relative_to(project_root))
            import_counts[rel_path] += 1
            return

    # 如果没找到精确匹配，尝试作为模块名
    # 例如：from core.session_manager import SessionManager
    module_path = import_name.replace(".", "/") + ".py"
    if (project_root / module_path).exists():
        rel_path = str((project_root / module_path).relative_to(project_root))
        import_counts[rel_path] += 1
        return
