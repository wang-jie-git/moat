"""
子系统健康检查 — L1: 核心子系统是否存活
增强版：增加内容哈希检查和代码行数突变检测
"""
import hashlib
import importlib
import inspect
from pathlib import Path


def _cleanup_module_cache(module_path: str) -> None:
    """清理模块缓存，避免不同测试项目互相污染。

    当多个测试使用 `core.foo` 这样的通用模块路径时，
    需要先清理 sys.modules 中旧的缓存，确保导入的是正确的文件。

    Args:
        module_path: 模块路径（如 "core.session_manager"）
    """
    # 清理主模块和父模块
    parts = module_path.split(".")
    for i in range(len(parts)):
        key = ".".join(parts[:i+1])
        if key in importlib.sys.modules:
            importlib.sys.modules.pop(key)


def run_subsystems_check(project_root: Path, baseline: dict | None = None) -> list[dict]:
    """检测项目中的核心子系统

    Args:
        project_root: 项目根目录
        baseline: 基线数据（可选），用于内容级检查

    Returns:
        检查结果列表
    """
    errors = []
    subsystems = _discover_subsystems(project_root)

    for name, module_path, class_name, file_path in subsystems:
        # 清理同名模块缓存，避免不同测试项目互相污染
        _cleanup_module_cache(module_path)

        try:
            mod = importlib.import_module(module_path)
            if class_name:
                cls = getattr(mod, class_name, None)
                if cls is None:
                    errors.append({
                        "file": module_path.replace(".", "/"),
                        "level": "L1",
                        "type": "subsystem_missing",
                        "message": f"子系统 [{name}] 中找不到 {class_name}",
                    })
                    continue

                # 导入成功
                errors.append({
                    "file": module_path.replace(".", "/"),
                    "level": "L1",
                    "type": "subsystem_ok",
                    "message": f"子系统 [{name}] 正常 ({class_name})",
                })

                # 🆕 新增：内容级检查（如果有基线）
                if baseline and file_path:
                    content_errors = _check_subsystem_content(
                        name, file_path, baseline
                    )
                    errors.extend(content_errors)

        except ImportError as e:
            errors.append({
                "file": module_path.replace(".", "/"),
                "level": "L1",
                "type": "subsystem_import_failed",
                "message": f"子系统 [{name}] 导入失败: {e}",
            })

    return errors


def _check_subsystem_content(name: str, file_path: Path, baseline: dict) -> list[dict]:
    """检查子系统内容级健康（新增功能）

    Args:
        name: 子系统名称
        file_path: 文件路径
        baseline: 基线数据

    Returns:
        检查结果列表
    """
    errors = []
    rel_path = str(file_path.relative_to(Path.cwd()))

    # 1. 文件哈希检查
    try:
        current_hash = _compute_file_hash(file_path)
        baseline_hashes = baseline.get("file_hashes", {})
        baseline_hash = baseline_hashes.get(rel_path)

        if baseline_hash and current_hash != baseline_hash:
            errors.append({
                "file": rel_path,
                "level": "L1",
                "type": "subsystem_content_changed",
                "message": f"[{name}] 文件内容已变更（基线: {baseline_hash[:8]}...，当前: {current_hash[:8]}...）",
            })
    except Exception:
        pass  # 文件无法读取，跳过

    # 2. 代码行数检查
    try:
        current_lines = _count_lines(file_path)
        baseline_lines_dict = baseline.get("line_counts", {})
        baseline_lines = baseline_lines_dict.get(rel_path, 0)

        if baseline_lines > 0:
            change_pct = (current_lines - baseline_lines) / baseline_lines * 100

            # 行数突变 >50%
            if abs(change_pct) > 50:
                errors.append({
                    "file": rel_path,
                    "level": "L1",
                    "type": "subsystem_line_spike",
                    "message": f"[{name}] 代码行数突变 {change_pct:+.1f}%（{baseline_lines} → {current_lines} 行）",
                })
    except Exception:
        pass

    return errors


def _compute_file_hash(file_path: Path) -> str:
    """计算文件 SHA256 哈希（前 16 位）"""
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _count_lines(file_path: Path) -> int:
    """统计文件行数"""
    try:
        return len(file_path.read_text(encoding="utf-8", errors="ignore").split("\n"))
    except Exception:
        return 0


def _discover_subsystems(project_root: Path) -> list[tuple[str, str, str, Path | None]]:
    """自动发现子系统（根据目录结构和类命名）

    Returns:
        列表，每项为 (name, module_path, class_name, file_path)
    """
    subsystems = []
    # 查找命名模式: *manager*, *engine*, *bridge*, *handler*, *service*, *provider*, *agent*
    pattern_keywords = ["manager", "engine", "bridge", "handler", "service", "provider", "agent"]

    for f in project_root.rglob("*.py"):
        rel = f.relative_to(project_root)
        parts = rel.parts
        if any(p.startswith(".venv") or p == "venv" or p in ("__pycache__", ".git", "node_modules",
                      "build", "dist") for p in parts):
            continue
        if f.name.startswith("_"):
            continue

        # 检查文件名或父目录名是否包含关键词
        name_match = any(k in f.stem.lower() for k in pattern_keywords)
        dir_match = any(any(k in p.lower() for k in pattern_keywords) for p in parts[:-1])

        if name_match or dir_match:
            text = f.read_text(errors="ignore")
            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("class ") and "(" in line:
                    name = line.split("(")[0].replace("class ", "").strip()
                    if not name.startswith("_"):
                        mod_name = ".".join(parts[:-1] + (f.stem,))
                        # 生成子系统名
                        sys_name = (parts[-2] + "/" + f.stem if len(parts) > 1 else f.stem).replace("_", " ").title()
                        subsystems.append((sys_name, mod_name, name, f))
                        break

    return subsystems
