"""核心模块检查 — L1: 检测关键模块能否实例化"""
import importlib
import inspect
from pathlib import Path


def run_modules_check(project_root: Path) -> list[dict]:
    """检测关键模块能否被实例化"""
    errors = []
    modules = _discover_core_modules(project_root)

    for mod_name, class_name in modules:
        try:
            mod = importlib.import_module(mod_name)
            if class_name:
                cls = getattr(mod, class_name, None)
                if cls is None:
                    # 查找同名函数
                    for name, obj in inspect.getmembers(mod):
                        if name.lower() == class_name.lower():
                            cls = obj
                            break
                if cls is None:
                    errors.append({
                        "file": mod_name.replace(".", "/"),
                        "level": "L1",
                        "type": "module_missing_class",
                        "message": f"{mod_name} 中没有 {class_name}",
                    })
                    continue

                # 检查构造函数参数
                sig = inspect.signature(cls.__init__)
                required_params = [
                    p for p in sig.parameters.values()
                    if p.default == inspect.Parameter.empty and p.name != 'self'
                ]

                # 跳过检查类（需要 project_root/config 参数）
                if required_params and any(
                    p.name in ('project_root', 'config') for p in required_params
                ):
                    errors.append({
                        "file": mod_name.replace(".", "/"),
                        "level": "L1",
                        "type": "module_skipped_ok",
                        "message": f"{class_name} 是检查类（需要 project_root/config），跳过实例化",
                    })
                    continue

                # 跳过 Pydantic BaseModel（需要必填字段）
                try:
                    from pydantic import BaseModel
                    if issubclass(cls, BaseModel):
                        errors.append({
                            "file": mod_name.replace(".", "/"),
                            "level": "L1",
                            "type": "module_skipped_ok",
                            "message": f"{class_name} 是 Pydantic BaseModel（需要必填字段），跳过实例化",
                        })
                        continue
                except ImportError:
                    pass  # Pydantic 未安装，继续正常逻辑

                # 尝试实例化
                if inspect.isclass(cls) and not inspect.isabstract(cls):
                    try:
                        instance = cls()
                        errors.append({
                            "file": mod_name.replace(".", "/"),
                            "level": "L1",
                            "type": "module_ok",
                            "message": f"{class_name}() 实例化成功",
                        })
                    except Exception as e:
                        errors.append({
                            "file": mod_name.replace(".", "/"),
                            "level": "L1",
                            "type": "module_instantiation_failed",
                            "message": f"{class_name}() 实例化失败: {e}",
                        })
        except ImportError as e:
            errors.append({
                "file": mod_name.replace(".", "/"),
                "level": "L1",
                "type": "module_import_failed",
                "message": f"import {mod_name} 失败: {e}",
            })

    return errors


def _discover_core_modules(project_root: Path) -> list[tuple[str, str | None]]:
    """自动发现核心模块"""
    modules = []
    py_files = list(project_root.rglob("*.py"))

    for f in py_files:
        rel = f.relative_to(project_root)
        parts = rel.parts
        if any(p in (".venv", "venv", "__pycache__", ".git", "node_modules",
                      "build", "dist", "tests", "moat/checks") for p in parts):
            continue
        if f.name.startswith("_"):
            continue

        text = f.read_text(errors="ignore")
        # 查找类定义
        class_names = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("class ") and "(" in line:
                name = line.split("(")[0].replace("class ", "").strip()
                if name not in ("BaseException", "Exception", "object"):
                    class_names.append(name)

        if class_names:
            mod_name = ".".join(parts[:-1] + (f.stem,))
            modules.append((mod_name, class_names[0]))

    return modules[:50]  # 最多 50 个模块