"""Moat 检查模块（插件化架构）

所有检查（Python/TypeScript/Go/Rust...）都通过统一的 Check 基类。
检查运行器自动检测项目类型，只运行相关的检查。
"""
from pathlib import Path
from typing import Any


def detect_project_type(project_root: Path) -> dict[str, bool]:
    """检测项目支持的语言/框架"""
    root = project_root.resolve()

    return {
        "python": any(root.rglob("*.py")),
        "typescript": any(root.rglob("*.ts")) or any(root.rglob("*.tsx")),
        "go": any(root.rglob("*.go")),
        "rust": any(root.rglob("*.rs")),
    }


def create_check_instances(project_type: dict[str, bool], project_root: Path, config: dict[str, Any] | None = None) -> list[tuple[str, Any]]:
    """根据项目类型创建检查实例"""
    checks = []

    # Python 检查（原有，保持向后兼容）
    if project_type.get("python"):
        from moat.checks import l1_import, l1_files, l1_modules, l1_subsystems, l1_behavior
        # 这些是旧风格的函数（返回 list[dict]）
        checks.extend([
            ("L0 Python 语法", l1_import),
            ("L1 Python import", l1_import),
            ("L1 文件完整性", l1_files),
            ("L1 核心模块", l1_modules),
            ("L1 子系统", l1_subsystems),
            ("L1 行为验证", l1_behavior),
        ])

    # TypeScript 检查（新增，基于 Check 基类）
    if project_type.get("typescript"):
        from moat.checks.typescript import (
            TypeScriptSyntaxCheck,
            TypeScriptDedupCheck,
            TypeScriptRaceConditionCheck,
            TypeScriptTimingDocCheck,
        )
        ts_config = (config or {}).get("typescript", {})
        checks.extend([
            ("L0 TypeScript 语法", TypeScriptSyntaxCheck(project_root, ts_config)),
            ("L1 TypeScript 去重", TypeScriptDedupCheck(project_root, ts_config)),
            ("L1 TypeScript 竞态", TypeScriptRaceConditionCheck(project_root, ts_config)),
            ("L1 TypeScript 时序文档", TypeScriptTimingDocCheck(project_root, ts_config)),
        ])

    return checks
