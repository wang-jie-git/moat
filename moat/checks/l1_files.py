"""文件完整性检查 — L1: 关键文件是否存在"""
from pathlib import Path


COMMON_KEY_FILES = [
    "pyproject.toml",
    "README.md",
    "LICENSE",
    ".gitignore",
]


def run_file_check(project_root: Path) -> list[dict]:
    """检查关键文件是否存在"""
    errors = []

    # 检查常见关键文件
    for file in COMMON_KEY_FILES:
        p = project_root / file
        if not p.exists():
            errors.append({
                "file": file,
                "level": "L1",
                "type": "file_missing",
                "message": f"关键文件缺失: {file}",
            })

    # 检查 __init__.py 覆盖率
    init_dirs = []
    for f in project_root.rglob("__init__.py"):
        init_dirs.append(f.parent.relative_to(project_root))

    # 报告健康状况
    if not errors:
        errors.append({
            "file": "filesystem",
            "level": "L1",
            "type": "file_ok",
            "message": f"文件系统健康，{len(init_dirs)} 个包目录",
        })

    return errors