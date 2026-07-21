"""
AST 自动注入传感器 — 按目录模式选择性安装 @moat_sensor

策略:
  1. 读取 moat.sensor.yml 配置（或使用默认保守值）
  2. 按 include 模式扫描文件
  3. 对每个 .py 文件解析 AST
  4. 跳过 exclude 模式、已有传感器、私有方法、魔术方法
  5. 关键路径函数自动标记 critical=True
  6. 写回文件（或 dry-run 预览）
"""

import ast
import fnmatch
import json
import logging
import shutil
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("moat.injector")

# ── 备份管理 ─────────────────────────────────────────────

BACKUP_DIR_NAME = ".moat/sensor_backups"


def _backup_dir(project_root: str) -> Path:
    """获取当前会话的备份目录"""
    ts = time.strftime("%Y%m%d_%H%M%S")
    return Path(project_root) / BACKUP_DIR_NAME / ts


def _save_backup(backup_root: Path, file_path: Path, project_root: Path) -> str | None:
    """备份文件到备份目录，返回备份路径"""
    try:
        rel = str(file_path.relative_to(project_root))
    except ValueError:
        rel = file_path.name
    backup_path = backup_root / rel
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file_path, backup_path)
    return str(backup_path)


def _write_manifest(backup_root: Path, entries: list[dict]):
    """写入备份清单"""
    manifest = backup_root / "manifest.json"
    manifest.write_text(json.dumps(entries, indent=2, ensure_ascii=False))


def list_backups(project_root: str = ".") -> list[dict]:
    """列出所有可用备份"""
    base = Path(project_root) / BACKUP_DIR_NAME
    if not base.exists():
        return []

    backups = []
    for d in sorted(base.iterdir(), reverse=True):
        if d.is_dir():
            manifest = d / "manifest.json"
            if manifest.exists():
                try:
                    data = json.loads(manifest.read_text())
                except Exception:
                    data = []
                backups.append({
                    "timestamp": d.name,
                    "files": len(data),
                    "path": str(d),
                })
    return backups


def revert_backup(backup_timestamp: str, project_root: str = ".") -> list[dict]:
    """回退指定备份

    Args:
        backup_timestamp: 备份时间戳 (YYYYmmdd_HHMMSS)
        project_root: 项目根目录

    Returns:
        恢复的文件列表
    """
    backup_path = Path(project_root) / BACKUP_DIR_NAME / backup_timestamp
    manifest_path = backup_path / "manifest.json"

    if not manifest_path.exists():
        return []

    manifest = json.loads(manifest_path.read_text())
    root = Path(project_root).resolve()

    restored = []
    for entry in manifest:
        rel_path = entry.get("rel_path", "")
        backup_file = backup_path / rel_path
        original = root / rel_path

        if backup_file.exists() and original.exists():
            shutil.copy2(backup_file, original)
            restored.append({"file": rel_path, "status": "restored"})
        elif backup_file.exists():
            # 原文件已被删除，恢复它
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_file, original)
            restored.append({"file": rel_path, "status": "restored (recreated)"})
        else:
            restored.append({"file": rel_path, "status": "backup missing"})

    return restored

# ── AST 转换器 ───────────────────────────────────────────

class SensorInjector(ast.NodeTransformer):
    """AST 节点转换器 — 自动注入 @moat_sensor"""

    def __init__(self, file_path: str, critical_patterns: list[str], project_root: str = ""):
        self.file_path = file_path
        self.critical_patterns = critical_patterns
        self.project_root = project_root
        self.injected_count = 0
        self._has_import = False

    def _component_id(self, func_name: str) -> str:
        """生成组件 ID（相对于项目根目录的路径）"""
        if self.project_root and self.file_path.startswith(self.project_root):
            rel = self.file_path[len(self.project_root):].lstrip("/")
        else:
            rel = self.file_path
        return f"{rel}:{func_name}"

    def visit_Module(self, node):
        # 检查是否已有 moat_sensor 导入
        for item in node.body:
            if (isinstance(item, ast.ImportFrom)
                    and item.module
                    and "moat.pain.sensor" in item.module):
                self._has_import = True
                break
            if isinstance(item, ast.Import):
                for alias in item.names:
                    if "moat.pain.sensor" in (alias.name or ""):
                        self._has_import = True
                        break
        self.generic_visit(node)
        return node

    def _should_inject(self, node) -> bool:
        """判断是否应该注入传感器"""
        # 跳过私有方法
        if node.name.startswith("_") and not node.name.startswith("__"):
            return False
        # 跳过魔术方法
        if node.name.startswith("__") and node.name.endswith("__"):
            return False
        # 跳过已有传感器（同步 + 异步）
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call):
                func = dec.func
                dec_name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else "")
                if dec_name in ("moat_sensor", "moat_sensor_async"):
                    return False
            elif isinstance(dec, ast.Name) and dec.id in ("moat_sensor", "moat_sensor_async"):
                return False
        return True

    def _is_critical(self, node) -> bool:
        """判断是否为关键路径"""
        name_lower = node.name.lower()
        path_lower = self.file_path.lower()
        for pattern in self.critical_patterns:
            p = pattern.strip("*").lower()
            if p in name_lower or p in path_lower:
                return True
        return False

    def _build_decorator(self, node, component_id: str, critical: bool) -> ast.Call:
        """构建 @moat_sensor(component_id=..., critical=...) 装饰器节点"""
        keywords = [
            ast.keyword(
                arg="component_id",
                value=ast.Constant(value=component_id),
            ),
        ]
        if critical:
            keywords.append(
                ast.keyword(arg="critical", value=ast.Constant(value=True)),
            )
        return ast.Call(
            func=ast.Name(id="moat_sensor", ctx=ast.Load()),
            args=[],
            keywords=keywords,
        )

    def visit_FunctionDef(self, node):
        if not self._should_inject(node):
            return node

        is_critical = self._is_critical(node)
        component_id = self._component_id(node.name)

        decorator = self._build_decorator(node, component_id, is_critical)
        node.decorator_list.insert(0, decorator)
        self.injected_count += 1
        return node

    def visit_AsyncFunctionDef(self, node):
        # 异步函数使用 moat_sensor_async 装饰器
        if not self._should_inject(node):
            return node

        is_critical = self._is_critical(node)
        component_id = self._component_id(node.name)

        # 异步函数用 moat_sensor_async
        keywords = [
            ast.keyword(
                arg="component_id",
                value=ast.Constant(value=component_id),
            ),
        ]
        if is_critical:
            keywords.append(
                ast.keyword(arg="critical", value=ast.Constant(value=True)),
            )
        decorator = ast.Call(
            func=ast.Name(id="moat_sensor_async", ctx=ast.Load()),
            args=[],
            keywords=keywords,
        )
        node.decorator_list.insert(0, decorator)
        self.injected_count += 1
        return node


# ── 文件级注入 ───────────────────────────────────────────

def inject_file(
    file_path: Path,
    critical_patterns: list[str],
    dry_run: bool = False,
    project_root: str = "",
) -> dict:
    """为单个 .py 文件注入传感器

    Returns:
        {"injected": int, "file": str, "error": Optional[str]}
    """
    try:
        source = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return {"injected": 0, "file": str(file_path), "error": f"读取失败: {e}"}

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as e:
        return {"injected": 0, "file": str(file_path), "error": f"语法错误: {e}"}

    injector = SensorInjector(str(file_path), critical_patterns, project_root=project_root)
    modified_tree = injector.visit(tree)

    if injector.injected_count == 0:
        return {"injected": 0, "file": str(file_path)}

    ast.fix_missing_locations(modified_tree)

    # 添加 import（如果没有的话）
    if not injector._has_import:
        # 判断文件是否包含 async 函数
        has_async = any(
            isinstance(n, ast.AsyncFunctionDef)
            for n in ast.walk(modified_tree)
        )
        names = ["moat_sensor", "moat_sensor_async"] if has_async else ["moat_sensor"]
        import_node = ast.ImportFrom(
            module="moat.pain.sensor",
            names=[ast.alias(name=n, asname=None) for n in names],
            level=0,
        )

        # 找到插入位置：跳过 __future__ imports（必须留在最前面）
        insert_pos = 0
        for i, stmt in enumerate(modified_tree.body):
            if isinstance(stmt, ast.ImportFrom) and stmt.module == "__future__":
                insert_pos = i + 1
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, (ast.Constant, ast.Str)):
                # 模块文档字符串也保留在最前面
                insert_pos = i + 1
            else:
                break

        modified_tree.body.insert(insert_pos, import_node)

    new_source = ast.unparse(modified_tree)

    if not dry_run:
        try:
            file_path.write_text(new_source, encoding="utf-8")
        except Exception as e:
            return {"injected": 0, "file": str(file_path), "error": f"写入失败: {e}"}

    return {
        "injected": injector.injected_count,
        "file": str(file_path),
    }


# ── 项目级注入 ───────────────────────────────────────────

def inject_project(
    project_root: str = ".",
    config: Optional[dict] = None,
    dry_run: bool = True,
) -> list[dict]:
    """为项目注入传感器

    Args:
        project_root: 项目根目录
        config: sensor 配置字典（包含 include/exclude/critical_patterns）
        dry_run: 预览模式（不改文件）

    Returns:
        每个文件的注入结果列表
    """
    if config is None:
        from moat.pain.config import load_config
        config = load_config(project_root)

    sensor_cfg = config.get("sensor", {})
    include_patterns = sensor_cfg.get("include", [])
    exclude_patterns = sensor_cfg.get("exclude", [])
    critical_patterns = sensor_cfg.get("critical_patterns", [])
    auto_inject = sensor_cfg.get("auto_inject", False)

    if not auto_inject or not include_patterns:
        return []

    root = Path(project_root).resolve()
    results = []

    # 搜集所有匹配 include 的文件
    matched_files: set[Path] = set()
    for pattern in include_patterns:
        for f in root.rglob(pattern):
            if f.suffix == ".py" and f.is_file():
                matched_files.add(f)

    # 剔除 exclude 模式
    def _match_glob(path_str: str, pattern: str) -> bool:
        """支持 ** 的 glob 匹配"""
        import fnmatch as fm
        if "**" in pattern:
            import re
            parts = pattern.split("**")
            regex = ""
            for i, part in enumerate(parts):
                if part:
                    t = fm.translate(part)
                    inner = t
                    for prefix in ["(?s:", "^"]:
                        if inner.startswith(prefix):
                            inner = inner[len(prefix):]
                    for suffix in [")\\Z", "\\Z", "$"]:
                        if inner.endswith(suffix):
                            inner = inner[:-len(suffix)]
                    if inner.startswith("/"):
                        inner = "/?" + inner[1:]
                    regex += inner
                if i < len(parts) - 1:
                    regex += r".*"
            return bool(re.search(regex, path_str))
        return fm.fnmatch(path_str, pattern)
    filtered: list[Path] = []
    for f in sorted(matched_files):
        try:
            rel = str(f.relative_to(root))
        except ValueError:
            rel = f.name
        if any(_match_glob(rel, pat) for pat in exclude_patterns):
            continue
        # 排除 __init__.py（容易造成循环导入风险）
        if f.name == "__init__.py":
            continue
        filtered.append(f)

    if not filtered:
        return []

    # 非 dry-run 模式：先备份所有待修改文件
    backup_root: Path | None = None
    backup_manifest: list[dict] = []
    if not dry_run:
        backup_root = _backup_dir(str(root))
        for py_file in filtered:
            try:
                rel = str(py_file.relative_to(root))
            except ValueError:
                rel = py_file.name
            backup_path = _save_backup(backup_root, py_file, root)
            if backup_path:
                backup_manifest.append({
                    "rel_path": rel,
                    "backup_path": backup_path,
                    "timestamp": time.time(),
                })
        _write_manifest(backup_root, backup_manifest)
        logger.info("已备份 %d 个文件到 %s", len(backup_manifest), backup_root)

    for py_file in filtered:
        result = inject_file(
            py_file, critical_patterns,
            dry_run=dry_run,
            project_root=str(root),
        )
        results.append(result)

    return results, backup_root, len(backup_manifest) if not dry_run else 0
