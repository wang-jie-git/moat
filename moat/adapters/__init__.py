"""AI 适配器 — 为各种 AI 工具生成规则"""
from pathlib import Path


def install_claude_adapter(project_root: Path):
    """安装 Claude Code 适配器"""
    claude_path = project_root / "CLAUDE.md"
    rules = _generate_claude_rules(project_root)

    if claude_path.exists():
        existing = claude_path.read_text()
        if "Moat" in existing:
            print("  · CLAUDE.md 已有 Moat 规则，跳过")
            return
        claude_path.write_text(existing + "\n\n" + rules)
    else:
        claude_path.write_text(rules)

    print(f"  ✅ CLAUDE.md 已更新")


def install_cursor_adapter(project_root: Path):
    """安装 Cursor 适配器"""
    cursor_dir = project_root / ".cursor"
    cursor_dir.mkdir(parents=True, exist_ok=True)
    rules = cursor_dir / "rules.mdc"
    if rules.exists():
        existing = rules.read_text()
        if "Moat" in existing:
            return
        rules.write_text(existing + "\n\n" + _generate_cursor_rules(project_root))
    else:
        rules.write_text(_generate_cursor_rules(project_root))
    print(f"  ✅ .cursor/rules.mdc 已更新")


def install_precommit_hook(project_root: Path):
    """安装 pre-commit hook"""
    hooks_dir = project_root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "pre-commit"

    hook_content = """#!/bin/bash
# Moat pre-commit hook — 提交前自动检查
echo "🔍 [Moat] 提交前检查..."
cd "$(git rev-parse --show-toplevel)"

if command -v moat &> /dev/null; then
    moat check
    if [ $? -ne 0 ]; then
        echo "❌ [Moat] 检查失败。修到通过再提交。"
        echo "   moat check"
        exit 1
    fi
    echo "✅ [Moat] 检查通过"
else
    echo "⚠ [Moat] moat 未安装，跳过检查"
fi
"""
    hook_path.write_text(hook_content)
    hook_path.chmod(0o755)
    print(f"  ✅ .git/hooks/pre-commit 已安装")


def _generate_claude_rules(project_root: Path) -> str:
    return f"""## Moat 护城河

Moat 是 AI 编码护城河，防止 AI 改代码时搞坏系统。

### 铁律
1. 改代码**前**跑一次 `moat check`，改代码**后**再跑一次。两次都通过才能提交。
2. 任何 AI 工具接手项目，第一件事就是跑 `moat check`。
3. 如果 `moat check` 报错，修到通过为止，不许跳过。

### 命令
```bash
# 改代码前/后检查（12秒）
moat check

# 实时监控日志错误
moat watch --log {_find_log_relative(project_root)}

# Web 错误看板
moat dashboard

# 更新基线（允许的改动后）
moat baseline save
```

### 四层防线
| 层级 | 作用 |
|------|------|
| L1 存活 | 骨架完整、API 存活 |
| L2 结构 | API 返回字段符合契约 |
| L3 关联 | 改了 A B 还能用 |
| L4 基线 | 文件数/路由数不退化 |
"""


def _generate_cursor_rules(project_root: Path) -> str:
    return f"""---
description: Moat — AI 编码护城河
globs: ["**/*.py"]
---
# Moat 护城河
- 改代码前跑 `moat check`，改代码后跑 `moat check`
- 不通过不允许提交
- `moat watch` 实时监控日志错误
"""


def _find_log_relative(root: Path) -> str:
    for c in ["logs/backend.log", "log/backend.log", "logs/app.log", "log/app.log"]:
        p = root / c
        if p.exists():
            return c
    return "logs/backend.log"