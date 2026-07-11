"""基线对比检查 — L4: 路由数/文件数/响应时间不退化
增强版：增加文件哈希对比和代码熵增检测
"""
import hashlib
from datetime import datetime
from pathlib import Path


def run_baseline_check(project_root: Path, baseline: dict | None = None) -> list[dict]:
    """对比当前状态与基线

    Args:
        project_root: 项目根目录
        baseline: 基线数据（可选）

    Returns:
        检查结果列表
    """
    errors = []
    current = _capture_enhanced_state(project_root)

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

    # 1. 对比文件数
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

    # 2. 对比代码行数
    prev_lines = baseline.get("total_lines", 0)
    curr_lines = current["total_lines"]
    if prev_lines > 0 and curr_lines < prev_lines * 0.9:
        errors.append({
            "file": "codebase",
            "level": "L4",
            "type": "line_count_drop",
            "message": f"代码行数从 {prev_lines} 降到 {curr_lines}（减少 >10%）",
        })

    # 🆕 新增：文件哈希对比
    hash_errors = _compare_file_hashes(current, baseline)
    errors.extend(hash_errors)

    # 🆕 新增：代码熵增检测
    entropy_errors = _detect_code_entropy(current, baseline)
    errors.extend(entropy_errors)

    return errors


def capture_baseline(project_root: Path) -> dict:
    """捕获当前状态作为基线

    Returns:
        基线数据字典
    """
    state = _capture_enhanced_state(project_root)
    return {
        "file_count": len(state["py_files"]),
        "total_lines": state["total_lines"],
        "file_hashes": state.get("file_hashes", {}),
        "line_counts": state.get("line_counts", {}),
        "timestamp": datetime.now().isoformat(),
    }


def _capture_enhanced_state(project_root: Path) -> dict:
    """捕获项目当前状态（增强版，包含文件哈希和行数统计）

    使用哈希缓存优化性能

    Returns:
        项目状态字典
    """
    from moat.cache import capture_state_with_cache

    return capture_state_with_cache(project_root)


def _compare_file_hashes(current: dict, baseline: dict) -> list[dict]:
    """对比文件哈希，检测内容变更

    Args:
        current: 当前状态
        baseline: 基线状态

    Returns:
        检查结果列表
    """
    errors = []
    curr_hashes = current.get("file_hashes", {})
    base_hashes = baseline.get("file_hashes", {})

    changed_count = 0
    for file_path, curr_hash in curr_hashes.items():
        base_hash = base_hashes.get(file_path)
        if base_hash and curr_hash != base_hash:
            changed_count += 1
            # 只报告前 5 个变更，避免报告过长
            if changed_count <= 5:
                errors.append({
                    "file": file_path,
                    "level": "L2",
                    "type": "file_content_changed",
                    "message": f"文件内容已变更（基线: {base_hash[:8]}...，当前: {curr_hash[:8]}...）",
                })

    if changed_count > 5:
        errors.append({
            "file": "codebase",
            "level": "L2",
            "type": "file_content_changed_summary",
            "message": f"还有 {changed_count - 5} 个文件内容已变更（使用 --full 查看详情）",
        })

    return errors


def _detect_code_entropy(current: dict, baseline: dict) -> list[dict]:
    """检测代码熵增（文件行数异常增长）

    Args:
        current: 当前状态
        baseline: 基线状态

    Returns:
        检查结果列表
    """
    errors = []
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
            "message": f"代码熵增预警：文件增长 {change_pct:+.1f}%（{base_count} → {curr_count} 行）",
        })

    # 报告中熵增文件（前 3 个）
    for file_path, base_count, curr_count, change_pct in medium_entropy_files[:3]:
        errors.append({
            "file": file_path,
            "level": "L2",
            "type": "medium_entropy",
            "message": f"代码增长较快：{change_pct:+.1f}%（{base_count} → {curr_count} 行）",
        })

    # 汇总
    total_entropy = len(high_entropy_files) + len(medium_entropy_files)
    if total_entropy > 6:
        errors.append({
            "file": "codebase",
            "level": "L2",
            "type": "entropy_summary",
            "message": f"还有 {total_entropy - 6} 个文件存在熵增风险（使用 --full 查看详情）",
        })

    return errors
