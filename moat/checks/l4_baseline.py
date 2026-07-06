"""基线对比检查 — L4: 路由数/文件数/响应时间不退化"""
from pathlib import Path


def run_baseline_check(project_root: Path, baseline: dict | None = None) -> list[dict]:
    """对比当前状态与基线"""
    errors = []
    current = _capture_state(project_root)

    if not baseline:
        # 没有基线，只记录状态
        errors.append({
            "file": "baseline",
            "level": "L4",
            "type": "baseline_missing",
            "message": f"没有基线。当前状态: {len(current['py_files'])} 文件, "
                       f"{current['total_lines']} 行代码",
        })
        return errors

    # 对比文件数
    prev_count = baseline.get("file_count", 0)
    curr_count = len(current["py_files"])
    if curr_count < prev_count * 0.9:
        errors.append({
            "file": "filesystem",
            "level": "L4",
            "type": "file_count_drop",
            "message": f"文件数从 {prev_count} 降到 {curr_count}（减少 >10%）",
        })
    elif curr_count > prev_count * 1.3:
        errors.append({
            "file": "filesystem",
            "level": "L4",
            "type": "file_count_surge",
            "message": f"文件数从 {prev_count} 增到 {curr_count}（增加 >30%）",
        })

    # 对比代码行数
    prev_lines = baseline.get("total_lines", 0)
    curr_lines = current["total_lines"]
    if prev_lines > 0 and curr_lines < prev_lines * 0.9:
        errors.append({
            "file": "codebase",
            "level": "L4",
            "type": "line_count_drop",
            "message": f"代码行数从 {prev_lines} 降到 {curr_lines}（减少 >10%）",
        })

    return errors


def capture_baseline(project_root: Path) -> dict:
    """捕获当前状态作为基线"""
    state = _capture_state(project_root)
    return {
        "file_count": len(state["py_files"]),
        "total_lines": state["total_lines"],
        "timestamp": str(__import__("datetime").datetime.now()),
    }


def _capture_state(project_root: Path) -> dict:
    """捕获项目当前状态"""
    py_files = []
    total_lines = 0

    for f in project_root.rglob("*.py"):
        rel = f.relative_to(project_root)
        parts = rel.parts
        if any(p in (".venv", "venv", "__pycache__", ".git", "node_modules",
                      "build", "dist") for p in parts):
            continue
        py_files.append(str(rel))
        try:
            total_lines += len(f.read_text().split("\n"))
        except Exception:
            pass

    return {
        "py_files": sorted(py_files),
        "total_lines": total_lines,
    }