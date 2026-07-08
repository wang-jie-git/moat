"""项目自动发现"""
import ast
import json
from pathlib import Path
from typing import Any


def init_project(project_root: Path, interactive: bool = True):
    """初始化 Moat 到项目

    Args:
        project_root: 项目根目录
        interactive: 是否启用交互式引导
    """
    root = project_root.resolve()

    # 1. 检测项目类型
    project_types = _detect_project_types(root)

    # 2. 交互式引导
    config: dict[str, Any] = {}
    if interactive and (project_types["python"] or project_types["typescript"]):
        config = _interactive_setup(root, project_types)
    else:
        # 非交互模式，使用默认配置
        config = _generate_default_config(root, project_types)

    # 3. 创建 .moat 目录
    moat_dir = root / ".moat"
    moat_dir.mkdir(parents=True, exist_ok=True)

    # 4. 生成配置文件
    (moat_dir / "claude.md").write_text(_generate_claude_md(root))
    (moat_dir / "config.json").write_text(json.dumps(config, indent=2))

    # 5. 保存基线
    from moat.baseline import BaselineManager
    bm = BaselineManager(root)
    bm.save()

    # 6. 如果启用了 Claude Code，生成 Hook 配置
    if config.get("claude_code", {}).get("enabled"):
        _generate_claude_settings(root)

    print(f"\n✅ Moat 已初始化到 {root}")
    print(f"   .moat/config.json — 项目配置")
    print(f"   .moat/claude.md — AI 适配规则")
    print(f"   .moat/baseline.json — 基线数据")
    if config.get("claude_code", {}).get("enabled"):
        print(f"   .claude/settings.json — Claude Code Hook 配置")
    print(f"\n🚀 下一步: 运行 moat check")


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


def _detect_project_types(root: Path) -> dict[str, bool]:
    """检测项目支持的语言/框架"""
    return {
        "python": any(root.rglob("*.py")),
        "typescript": any(root.rglob("*.ts")) or any(root.rglob("*.tsx")),
        "go": any(root.rglob("*.go")),
        "rust": any(root.rglob("*.rs")),
    }


def _detect_python_framework(root: Path) -> str | None:
    """检测 Python 框架"""
    for f in root.rglob("*.py"):
        if any(p in f.parts for p in (".venv", "venv", "__pycache__", ".git")):
            continue
        try:
            text = f.read_text(errors="ignore").lower()
            if "fastapi" in text:
                return "fastapi"
            if "flask" in text:
                return "flask"
            if "django" in text:
                return "django"
        except Exception:
            pass
    return None


def _detect_typescript_framework(root: Path) -> str | None:
    """检测 TypeScript 框架"""
    for f in list(root.rglob("*.tsx")) + list(root.rglob("*.ts")):
        if any(p in f.parts for p in ("node_modules", ".git", "dist")):
            continue
        try:
            text = f.read_text(errors="ignore").lower()
            if "react" in text or "react-native" in text:
                return "react"
            if "vue" in text:
                return "vue"
            if "angular" in text:
                return "angular"
            if "next" in text:
                return "nextjs"
            if "nuxt" in text:
                return "nuxt"
        except Exception:
            pass
    return None


def _interactive_setup(root: Path, project_types: dict[str, bool]) -> dict[str, Any]:
    """交互式引导设置"""
    print(f"\n{'=' * 50}")
    print(f"  🏰 Moat — 交互式初始化")
    print(f"  {root}")
    print(f"{'=' * 50}\n")

    print("📊 检测到项目类型:")
    if project_types.get("python"):
        print(f"   ✓ Python")
    if project_types.get("typescript"):
        print(f"   ✓ TypeScript")
    if not any(project_types.values()):
        print(f"   ⚠️  未检测到已知语言")

    config: dict[str, Any] = {}

    # Python 框架检测
    if project_types.get("python"):
        py_framework = _detect_python_framework(root)
        if py_framework:
            print(f"\n🐍 检测到 Python 框架: {py_framework}")
            use_py = input(f"   是否为 {py_framework} 启用定制化检查？(Y/n): ").strip().lower()
            if use_py != "n":
                config["python"] = {"framework": py_framework}
                print(f"   ✓ 已启用 {py_framework} 检查")
        else:
            print(f"\n🐍 检测到 Python 项目")
            print(f"   支持的框架: fastapi, flask, django")
            framework = input(f"   请输入框架名称（直接回车跳过）: ").strip().lower()
            if framework:
                config["python"] = {"framework": framework}
                print(f"   ✓ 已启用 {framework} 检查")

    # TypeScript 框架检测
    if project_types.get("typescript"):
        ts_framework = _detect_typescript_framework(root)
        if ts_framework:
            print(f"\n⚡ 检测到 TypeScript 框架: {ts_framework}")
            use_ts = input(f"   是否为 {ts_framework} 启用定制化检查？(Y/n): ").strip().lower()
            if use_ts != "n":
                ts_config: dict[str, Any] = {"framework": ts_framework}
                print(f"   ✓ 已启用 {ts_framework} 检查")

                # TypeScript 额外选项
                print(f"\n   TypeScript 检查选项:")
                enable_semantic = input(f"   - 启用 CodeGraph 语义分析？(y/N): ").strip().lower()
                if enable_semantic == "y":
                    ts_config["enable_semantic_checks"] = True
                    print(f"     ✓ 语义分析已启用")

                config["typescript"] = ts_config
        else:
            print(f"\n⚡ 检测到 TypeScript 项目")
            print(f"   支持的框架: react, vue, angular, nextjs, nuxt")
            framework = input(f"   请输入框架名称（直接回车跳过）: ").strip().lower()
            if framework:
                config["typescript"] = {"framework": framework}

    # 日志路径
    print(f"\n📝 日志配置:")
    log_path = _find_log(root)
    if log_path:
        print(f"   检测到日志路径: {log_path}")
        use_detected = input(f"   使用此路径？(Y/n): ").strip().lower()
        if use_detected != "n":
            config["log_path"] = log_path
        else:
            custom_log = input(f"   请输入自定义日志路径: ").strip()
            if custom_log:
                config["log_path"] = custom_log
    else:
        custom_log = input(f"   未检测到日志，请输入日志路径（直接回车跳过）: ").strip()
        if custom_log:
            config["log_path"] = custom_log

    # Claude Code 集成
    print(f"\n🤖 Claude Code 集成:")
    claude_dir = root / ".claude"
    if claude_dir.exists():
        print(f"   检测到 .claude 目录")

        enable_claude_hook = input(f"   是否将 Moat 守护进程集成至 Claude Code？(Y/n): ").strip().lower()
        if enable_claude_hook != "n":
            config["claude_code"] = {"enabled": True}
            print(f"   ✓ Claude Code Hook 已启用")

            # 自动生成 .claude/settings.json
            _generate_claude_settings(root)
    else:
        print(f"   未检测到 .claude 目录（跳过 Claude Code 集成）")

    # 核心业务探测
    print(f"\n⚡ 核心业务探测:")
    from moat.core_areas import detect_core_areas, CoreAreaDetector

    core_areas = detect_core_areas(str(root), auto_confirm=False)

    if core_areas:
        print(f"   检测到 {len(core_areas)} 个核心区域:")
        for area in core_areas:
            print(f"     ✓ {area.pattern} ({area.name}) — {area.description}")

        use_core = input(f"\n   是否启用核心区域保护？(Y/n): ").strip().lower()
        if use_core != "n":
            from moat.core_areas import CoreAreaDetector
            detector = CoreAreaDetector(root)
            config.update(detector.to_config(core_areas))
            print(f"   ✓ 核心区域保护已启用")
    else:
        print(f"   ⚠️  未检测到核心业务区域")

    # 保存配置供未来使用
    config.setdefault("project_name", root.name)
    config.setdefault("check_on_commit", True)
    config.setdefault("auto_monitor", False)

    return config


def _generate_claude_settings(root: Path) -> None:
    """生成 Claude Code Hook 配置"""
    claude_dir = root / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    settings_path = claude_dir / "settings.json"

    # 读取现有配置（如果存在）
    existing_settings = {}
    if settings_path.exists():
        try:
            existing_settings = json.loads(settings_path.read_text())
        except Exception:
            pass

    # 生成 Hook 配置
    moat_hooks = {
        "PreToolUse": [
            {
                "matcher": "Write|Edit",
                "hooks": [
                    {
                        "type": "command",
                        "command": "moat gatekeeper check --file ${file}",
                        "timeout": 5000,
                    }
                ],
            }
        ],
        "PostToolUse": [
            {
                "matcher": "Write|Edit",
                "hooks": [
                    {
                        "type": "command",
                        "command": "moat check --diff",
                        "timeout": 10000,
                    }
                ],
            }
        ],
    }

    # 合并到现有配置
    existing_settings["hooks"] = moat_hooks

    # 写入配置
    settings_path.write_text(json.dumps(existing_settings, indent=2))
    print(f"   ✓ 已生成 {settings_path}")


def _generate_default_config(root: Path, project_types: dict[str, bool]) -> dict[str, Any]:
    """生成默认配置（非交互模式）"""
    config: dict[str, Any] = {
        "project_name": root.name,
        "log_path": str(_find_log(root) or "logs/backend.log"),
        "filter_pattern": "ERROR|Traceback|Process exited",
        "check_on_commit": True,
        "auto_monitor": False,
    }

    if project_types.get("python"):
        framework = _detect_python_framework(root)
        if framework:
            config["python"] = {"framework": framework}

    if project_types.get("typescript"):
        framework = _detect_typescript_framework(root)
        if framework:
            config["typescript"] = {"framework": framework}

    return config


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