"""项目自动发现"""
import ast
from pathlib import Path


def init_project(project_root: Path):
    """初始化 Moat 到项目"""
    root = project_root.resolve()

    # 创建 .moat 目录
    moat_dir = root / ".moat"
    moat_dir.mkdir(parents=True, exist_ok=True)

    # 创建基础文件
    (moat_dir / "claude.md").write_text(_generate_claude_md(root))
    (moat_dir / "config.json").write_text(_generate_config(root))

    # 保存基线
    from moat.baseline import BaselineManager
    bm = BaselineManager(root)
    bm.save()

    print(f"✅ Moat 已初始化到 {root}")
    print(f"   .moat/baseline.json — 基线数据")
    print(f"   .moat/claude.md — AI 适配规则")
    print(f"   .moat/config.json — 项目配置")


def discover_project(project_root: Path) -> dict:
    """发现项目结构"""
    root = project_root.resolve()
    info = {
        "name": root.name,
        "python_version": _detect_python_version(root),
        "framework": _detect_framework(root),
        "has_tests": any((root / d).exists() for d in ["tests", "test"]),
        "has_ci": any((root / f).exists() for f in [
            ".github/workflows", ".gitlab-ci.yml", "Jenkinsfile"]),
        "py_files": _count_py_files(root),
        "total_lines": _count_lines(root),
        "log_path": _find_log(root),
        "entry_points": _find_entry_points(root),
    }
    return info


def _detect_python_version(root: Path) -> str:
    """检测 Python 版本"""
    import sys
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def _detect_framework(root: Path) -> str | None:
    """检测框架"""
    has_fastapi = any("fastapi" in f.read_text(errors="ignore").lower()
                      for f in root.rglob("*.py") if "fastapi" in f.read_text(errors="ignore").lower())
    if has_fastapi:
        return "fastapi"
    has_flask = any("flask" in f.read_text(errors="ignore").lower()
                    for f in root.rglob("*.py"))
    if has_flask:
        return "flask"
    return None


def _count_py_files(root: Path) -> int:
    count = 0
    for f in root.rglob("*.py"):
        if any(p in f.parts for p in (".venv", "venv", "__pycache__", ".git")):
            continue
        count += 1
    return count


def _count_lines(root: Path) -> int:
    total = 0
    for f in root.rglob("*.py"):
        if any(p in f.parts for p in (".venv", "venv", "__pycache__", ".git")):
            continue
        try:
            total += len(f.read_text().split("\n"))
        except Exception:
            pass
    return total


def _find_log(root: Path) -> str | None:
    for c in ["logs/backend.log", "log/backend.log", "logs/app.log", "log/app.log"]:
        p = root / c
        if p.exists():
            return str(p)
    return None


def _find_entry_points(root: Path) -> list[str]:
    entries = []
    for f in root.rglob("server.py"):
        if any(p in f.parts for p in (".venv", "venv", "__pycache__", ".git")):
            continue
        text = f.read_text(errors="ignore")
        if "app" in text and ("FastAPI" in text or "Flask" in text):
            entries.append(str(f.relative_to(root)))
    return entries


def _generate_claude_md(root: Path) -> str:
    """生成 CLAUDE.md 适配规则"""
    return f"""# Moat — AI 编码护城河

## 铁律
改代码**前**跑一次，改代码**后**再跑一次。两次都通过才能提交。

```bash
moat check
```

## 基线
系统状态基线保存在 `.moat/baseline.json`。
如果允许的改动会导致基线变化，先更新基线：

```bash
moat baseline save
```

## 实时监控
服务器运行中，实时查看错误：

```bash
moat watch --log logs/backend.log
```

## 规则
1. 修完 bug 必须 `moat check` 确认没有引入新问题
2. 不做测试覆盖的改动不能提交
3. 如果 `moat check` 报错，修到通过为止
"""


def _generate_config(root: Path) -> str:
    """生成项目配置"""
    import json
    config = {
        "project_name": root.name,
        "log_path": str(_find_log(root) or "logs/backend.log"),
        "filter_pattern": "ERROR|Traceback|Process exited",
        "check_on_commit": True,
        "auto_monitor": False,
    }
    return json.dumps(config, indent=2)