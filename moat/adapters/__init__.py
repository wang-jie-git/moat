"""AI 适配器 — 为各种 AI 工具生成规则，强制使用 Moat"""

import os
import stat
from pathlib import Path


# ── AI 工具适配器 ──────────────────────────────────────────

def install_claude_adapter(project_root: Path):
    """安装 Claude Code 适配器（CLAUDE.md）"""
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


def install_codex_adapter(project_root: Path):
    """安装 Codex CLI 适配器（.codex/skills/）"""
    _install_skill_file(project_root, ".codex", "Codex CLI")


def install_agents_adapter(project_root: Path):
    """安装 AI Agents 适配器（.agents/skills/）"""
    _install_skill_file(project_root, ".agents", "AI Agents")


def install_openharness_adapter(project_root: Path):
    """安装 OpenHarness 适配器（.openharness/skills/）"""
    _install_skill_file(project_root, ".openharness", "OpenHarness")


def install_windsurf_adapter(project_root: Path):
    """安装 Windsurf 适配器（.windsurf/rules/）"""
    rules_dir = project_root / ".windsurf" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    rules = rules_dir / "moat.md"
    if rules.exists():
        existing = rules.read_text()
        if "Moat" in existing:
            return
        rules.write_text(existing + "\n\n" + _generate_windsurf_rules(project_root))
    else:
        rules.write_text(_generate_windsurf_rules(project_root))
    print(f"  ✅ .windsurf/rules/moat.md 已更新")


def _install_skill_file(project_root: Path, tool_dir: str, tool_name: str):
    """通用 SKILL.md 安装"""
    skill_dir = project_root / tool_dir / "skills" / "moat"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_path = skill_dir / "SKILL.md"
    content = _generate_skill_md(project_root, tool_name)
    if skill_path.exists():
        existing = skill_path.read_text()
        if "Moat" in existing and "moat check" in existing:
            print(f"  · {tool_dir}/skills/moat/SKILL.md 已有 Moat 规则，跳过")
            return
    skill_path.write_text(content)
    print(f"  ✅ {tool_dir}/skills/moat/SKILL.md 已安装")


# ── Git 提交包装器 ──────────────────────────────────────────

def install_precommit_hook(project_root: Path):
    """兼容旧版 API — 安装 git 包装器（含 --no-verify 拦截 + prepare-commit-msg）"""
    install_git_wrapper(project_root)


def install_git_wrapper(project_root: Path):
    """安装 git commit 包装器，拦截 --no-verify 绕过"""
    hooks_dir = project_root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # 1. 升级 pre-commit hook（加 --no-verify 拦截 + 强制检查）
    hook_path = hooks_dir / "pre-commit"
    hook_content = _generate_precommit_hook()
    hook_path.write_text(hook_content)
    hook_path.chmod(0o755)

    # 2. 安装 prepare-commit-msg hook（二次拦截）
    prepare_path = hooks_dir / "prepare-commit-msg"
    prepare_content = _generate_prepare_commit_msg_hook()
    prepare_path.write_text(prepare_content)
    prepare_path.chmod(0o755)

    print(f"  ✅ .git/hooks/pre-commit 已升级（含 --no-verify 拦截）")
    print(f"  ✅ .git/hooks/prepare-commit-msg 已安装（二次拦截）")


def _generate_precommit_hook() -> str:
    return """#!/bin/bash
# Moat pre-commit hook — 提交前自动检查，拦截 --no-verify 绕过
set -e

# 环境变量豁免（用于 CI/CD 等自动化场景）
if [ "$MOAT_SKIP_CHECK" = "1" ]; then
    exit 0
fi

# 检测 --no-verify 绕过
# 如果用户使用了 --no-verify，在 commit 消息中标记
HAS_NO_VERIFY=false
for arg in "$@"; do
    if [ "$arg" = "--no-verify" ] || [ "$arg" = "-n" ]; then
        HAS_NO_VERIFY=true
    fi
done

if [ "$HAS_NO_VERIFY" = true ]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  🚫 MOAT: --no-verify 已被拦截                              ║"
    echo "║  你不能绕过 Moat 门禁检查。                                 ║"
    echo "║                                                              ║"
    echo "║  如需豁免（仅限 CI/CD 场景），设置环境变量:                  ║"
    echo "║    export MOAT_SKIP_CHECK=1                                  ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    exit 1
fi

echo "🔍 [Moat] 提交前检查..."
cd "$(git rev-parse --show-toplevel)"

if command -v moat &> /dev/null; then
    moat check
    if [ $? -ne 0 ]; then
        echo ""
        echo "╔══════════════════════════════════════════════════════════════╗"
        echo "║  ❌ [Moat] 检查失败！                                      ║"
        echo "║  修到通过再提交:                                            ║"
        echo "║    moat check                                               ║"
        echo "║  或查看详情:                                                ║"
        echo "║    moat dashboard                                           ║"
        echo "╚══════════════════════════════════════════════════════════════╝"
        echo ""
        exit 1
    fi
    echo "✅ [Moat] 检查通过"
else
    echo "⚠ [Moat] moat 未安装，安装后使用:"
    echo "   pip install moat-ai"
    echo "   moat init"
    exit 1
fi
"""


def _generate_prepare_commit_msg_hook() -> str:
    return """#!/bin/bash
# Moat prepare-commit-msg hook — 二次拦截，检测绕过痕迹
# 如果 commit 消息包含 MOAT_BYPASSED 标记，拒绝提交

MSG_FILE="$1"
MSG=$(cat "$MSG_FILE")

if echo "$MSG" | grep -qi "MOAT_BYPASSED\|NO_MOAT\|SKIP_MOAT"; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  🚫 MOAT: commit 消息包含绕过标记，拒绝提交                  ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    exit 1
fi
"""


# ── AI 启动检测 ──────────────────────────────────────────────

INSTALL_STARTUP_CHECK_SCRIPT = """#!/bin/bash
# Moat AI 启动检测 — AI 工具进入项目时自动运行
# 由 moat init 安装到 .moat/startup_check.sh

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR" || exit 0

# 检查 moat 是否安装
if ! command -v moat &> /dev/null; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  🛡️  Moat 护城河未安装                                       ║"
    echo "║                                                              ║"
    echo "║  本项目使用 Moat 保护代码质量，请在修改代码前安装:           ║"
    echo "║    pip install moat-ai                                        ║"
    echo "║    moat init                                                  ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    exit 1
fi

# 检查 moat 是否已初始化
if [ ! -f ".moat/moat.json" ]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  🛡️  Moat 未初始化                                           ║"
    echo "║  运行 moat init 初始化项目                                   ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    moat init
    exit 0
fi

# 显示项目记忆摘要
echo "🛡️  [Moat] 护城河已激活 | $(moat --version 2>/dev/null || echo '?')"
echo ""

# 同步 AI 上下文文件（供 AI 工具自动读取）
moat memory sync 2>/dev/null

# 检查是否有未读的踩坑记录
LESSONS_DIR=".moat/lessons"
if [ -d "$LESSONS_DIR" ]; then
    LESSON_COUNT=$(ls -1 "$LESSONS_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')
    if [ "$LESSON_COUNT" -gt 0 ]; then
        echo "⚠️  项目有 $LESSON_COUNT 条踩坑记录，建议先查看:"
        echo "   moat memory list lessons"
        echo ""
    fi
fi

# 检查是否有红线
REDLINE_COUNT=$(moat memory list redlines 2>/dev/null | grep -c "^-" || echo "0")
if [ "$REDLINE_COUNT" -gt 0 ]; then
    echo "📋 项目有 $REDLINE_COUNT 条红线规则"
    echo "   查看: moat memory list redlines"
    echo ""
fi

echo "🔍 改代码前: moat check"
echo "✅ 改代码后: moat check"
echo "📊 Web 看板: moat dashboard"
echo ""
"""


def install_startup_check(project_root: Path):
    """安装 AI 启动检测脚本"""
    moat_dir = project_root / ".moat"
    moat_dir.mkdir(parents=True, exist_ok=True)
    script_path = moat_dir / "startup_check.sh"
    script_path.write_text(INSTALL_STARTUP_CHECK_SCRIPT)
    script_path.chmod(0o755)
    print(f"  ✅ .moat/startup_check.sh 已安装（AI 工具启动检测）")


# ── 全量安装 ────────────────────────────────────────────────

def install_all(project_root: Path):
    """安装所有适配器"""
    print(f"\n🔧 安装 Moat 适配器到 {project_root}")
    print()

    # AI 工具适配器
    install_claude_adapter(project_root)
    install_cursor_adapter(project_root)
    install_codex_adapter(project_root)
    install_agents_adapter(project_root)
    install_openharness_adapter(project_root)
    install_windsurf_adapter(project_root)

    # Git 提交包装器
    install_git_wrapper(project_root)

    # AI 启动检测
    install_startup_check(project_root)

    print()
    print("✅ 所有适配器安装完成")
    print("   下次 AI 工具进入项目时会自动检测并运行 Moat")
    print()


# ── 规则生成 ────────────────────────────────────────────────

def _generate_claude_rules(project_root: Path) -> str:
    return f"""## Moat 护城河

Moat 是 AI 编码护城河，防止 AI 改代码时搞坏系统。

### 铁律
1. 改代码**前**跑一次 `moat check`，改代码**后**再跑一次。两次都通过才能提交。
2. 任何 AI 工具接手项目，第一件事就是跑 `moat check`。
3. 如果 `moat check` 报错，修到通过为止，不许跳过。
4. **禁止使用 `git commit --no-verify` 绕过检查**。会被拦截。

### 项目记忆（moat-memory）
这个项目积累了一些记忆，改代码前先查看：
```bash
# 查看项目红线（架构规则、编码边界）
moat memory list redlines

# 查看踩坑记录（以前 MOAT 检查失败的地方）
moat memory list lessons

# 查看经验模版
moat memory list templates
```

**自动同步的文件**: `.moat/ai_context.md` 包含上述全部记忆，AI 工具可自动读取。

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
- 禁止使用 `git commit --no-verify` 绕过
- `moat watch` 实时监控日志错误

# moat-memory 项目记忆
改代码前先查看:
- `moat memory list redlines` — 项目红线
- `moat memory list lessons` — 踩坑记录
- `moat memory list templates` — 经验模版
- `.moat/ai_context.md` — 自动同步的记忆快照
"""


def _generate_skill_md(project_root: Path, tool_name: str) -> str:
    """生成 SKILL.md 内容（用于 codex/agents/openharness）"""
    return f"""---
name: moat
description: Moat — AI 编码护城河。每次改代码前后必须运行的门禁检查。
---

# Moat — AI 编码护城河

## ⚠️ 重要：你必须遵守以下工作流

> 你是 AI 编码工具，**不是人类开发者**。人类可以靠经验判断，你需要靠工具检查。
> **不执行 moat check 就改代码，等于闭着眼睛开车。**

## 强制工作流

### 第 1 步：读项目记忆
```bash
cat .moat/ai_context.md
```

### 第 2 步：改代码前 — 跑 moat check
```bash
moat check
```
如果失败 → 先修，不要跳过。

### 第 3 步：改代码

### 第 4 步：改代码后 — 再跑 moat check
```bash
moat check
```
如果失败 → 修到通过。

### 第 5 步：提交
```bash
git add .
git commit -m "描述你的改动"
```

## 禁止
- ❌ 不要跳过 moat check
- ❌ 不要使用 `git commit --no-verify`（会被拦截）
- ❌ 不要"我以为没问题"——跑 moat check 确认

## 为什么？
moat check 会检查文件完整性、API 存活、跨系统关联、基线退化。
这些你靠"看代码"看不出来，必须跑工具。
"""


def _generate_windsurf_rules(project_root: Path) -> str:
    return f"""# Moat — AI 编码护城河

## 铁律
- 改代码前跑 `moat check`，改代码后跑 `moat check`
- 不通过不允许提交
- 禁止使用 `git commit --no-verify` 绕过

## 项目记忆
改代码前先查看:
- `moat memory list redlines` — 项目红线
- `moat memory list lessons` — 踩坑记录
- `moat memory list templates` — 经验模版
- `.moat/ai_context.md` — 自动同步的记忆快照

## 命令
```bash
moat check           # 改代码前/后检查
moat dashboard       # Web 看板
moat memory list     # 查看项目记忆
```
"""


def _find_log_relative(root: Path) -> str:
    for c in ["logs/backend.log", "log/backend.log", "logs/app.log", "log/app.log"]:
        p = root / c
        if p.exists():
            return c
    return "logs/backend.log"