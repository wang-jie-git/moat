"""CONTRACT.md 生成器"""
from pathlib import Path


def generate_contract(project_root: Path) -> str:
    """生成项目行为契约文档"""
    from moat.discovery import discover_project

    info = discover_project(project_root)

    lines = [
        f"# {info['name']} — 行为契约",
        "",
        "> 自动生成。改代码前跑 `moat check`，改代码后跑 `moat check`。",
        "> 两次都通过才能提交。",
        "",
        "## 项目概览",
        "",
        f"- **Python**: {info['python_version']}",
        f"- **框架**: {info['framework'] or '未检测'}",
        f"- **Python 文件**: {info['py_files']}",
        f"- **代码行数**: {info['total_lines']}",
        f"- **测试目录**: {'有' if info['has_tests'] else '无'}",
        f"- **CI 配置**: {'有' if info['has_ci'] else '无'}",
        f"- **入口文件**: {', '.join(info['entry_points']) or '未检测'}",
        "",
        "## 护城河四层防线",
        "",
        "| 层级 | 作用 | 命令 |",
        "|------|------|------|",
        "| L1 存活 | 骨架完整、API 存活 | `moat check` |",
        "| L2 结构 | API 返回字段符合契约 | `moat check` |",
        "| L3 关联 | 改了 A B 还能用 | `moat check` |",
        "| L4 基线 | 文件数/路由数不退化 | `moat check` |",
        "",
        "## 使用方式",
        "",
        "```bash",
        "# 改代码前/后",
        "moat check",
        "",
        "# 实时监控",
        "moat watch --log " + (info['log_path'] or 'logs/backend.log'),
        "",
        "# 更新基线",
        "moat baseline save",
        "```",
        "",
        "## 铁律",
        "",
        "1. 改代码**前**跑一次 `moat check`，改代码**后**再跑一次。两次都通过才能提交。",
        "2. 任何 AI 工具接手项目，第一件事就是跑 `moat check`。",
        "3. 如果 `moat check` 报错，修到通过为止，不许跳过。",
        "",
    ]

    return "\n".join(lines) + "\n"