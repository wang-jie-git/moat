"""启动链检查 — L1: 核心模块能否 import"""
import os
import sys
import subprocess
import importlib
from pathlib import Path


def run_import_check(project_root: Path) -> list[dict]:
    """扫描所有 .py 文件，检查语法和 import"""
    errors = []
    py_files = list(project_root.rglob("*.py"))

    for f in py_files:
        # 跳过 venv / .venv / __pycache__ / tests / examples
        rel = f.relative_to(project_root)
        parts = rel.parts
        if any(p in (".venv", "venv", "env", "__pycache__", "node_modules",
                      ".git", ".tox", "build", "dist", ".egg-info",
                      "tests", "test", "examples") for p in parts):
            continue

        # 语法检查
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(f)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            errors.append({
                "file": str(rel),
                "level": "L1",
                "type": "syntax",
                "message": result.stderr.strip(),
            })
            continue

        # 尝试 import
        module_path = str(f.with_suffix(""))
        # 转为模块名
        mod_name = ".".join(parts[:-1] + (f.stem,))
        if mod_name.startswith("."):
            continue
        try:
            importlib.import_module(mod_name)
        except Exception as e:
            errors.append({
                "file": str(rel),
                "level": "L1",
                "type": "import",
                "message": f"{type(e).__name__}: {e}",
            })

    return errors


def run_syntax_check(project_root: Path) -> list[dict]:
    """只做语法检查（更快）"""
    errors = []
    py_files = list(project_root.rglob("*.py"))

    for f in py_files:
        rel = f.relative_to(project_root)
        parts = rel.parts
        if any(p in (".venv", "venv", "env", "__pycache__", "node_modules",
                      ".git", ".tox", "build", "dist", ".egg-info") for p in parts):
            continue

        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(f)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            errors.append({
                "file": str(rel),
                "level": "L0",
                "type": "syntax",
                "message": result.stderr.strip(),
            })

    return errors