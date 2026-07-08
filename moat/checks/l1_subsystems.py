"""子系统健康检查 — L1: 核心子系统是否存活"""
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


def run_subsystems_check(project_root: Path) -> list[dict]:
    """检测项目中的核心子系统"""
    errors = []
    subsystems = _discover_subsystems(project_root)

    for name, module_path, class_name in subsystems:
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
                errors.append({
                    "file": module_path.replace(".", "/"),
                    "level": "L1",
                    "type": "subsystem_ok",
                    "message": f"子系统 [{name}] 正常 ({class_name})",
                })
        except ImportError as e:
            errors.append({
                "file": module_path.replace(".", "/"),
                "level": "L1",
                "type": "subsystem_import_failed",
                "message": f"子系统 [{name}] 导入失败: {e}",
            })

    return errors


def _discover_subsystems(project_root: Path) -> list[tuple[str, str, str]]:
    """自动发现子系统（根据目录结构和类命名）"""
    subsystems = []
    # 查找命名模式: *manager*, *engine*, *bridge*, *handler*, *service*, *provider*, *agent*
    pattern_keywords = ["manager", "engine", "bridge", "handler", "service", "provider", "agent"]

    for f in project_root.rglob("*.py"):
        rel = f.relative_to(project_root)
        parts = rel.parts
        if any(p in (".venv", "venv", "__pycache__", ".git", "node_modules",
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
                        subsystems.append((sys_name, mod_name, name))
                        break

    return subsystems