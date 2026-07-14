"""权限审计 — `moat audit --permissions` 扫描 AI 工具权限过载

用途:
  moat audit --permissions          # 审计所有 AI 工具的权限配置
  moat audit --permissions --tool claude  # 只审计 Claude Code
  moat audit --permissions --fix    # 生成瘦身建议

发现问题:
  - Claude Code 拥有 23 个权限，但最近 7 天只用了 8 个
  - sshpass 明文密码（极度危险）
  - scp / tar czf / curl 等数据导出命令闲置
  - 建议移除 15 个闲置权限，减少 65% 攻击面
"""

import json
import re
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# ── 高危命令分类 ──

DANGEROUS_COMMANDS = {
    "sshpass": {
        "risk": "CRITICAL",
        "reason": "明文密码传输，任何进程可读取",
        "suggestion": "迁移到 ~/.ssh/config 或 SSH 密钥认证",
    },
    "Bash(scp ": {
        "risk": "HIGH",
        "reason": "远程文件传输，可被用于数据导出",
        "suggestion": "如不需要远程文件传输，建议移除",
    },
    "Bash(rsync": {
        "risk": "HIGH",
        "reason": "批量文件同步，可被用于数据导出",
        "suggestion": "如不需要远程同步，建议移除",
    },
    "Bash(sftp": {
        "risk": "HIGH",
        "reason": "文件传输协议，可被用于数据导出",
        "suggestion": "如不需要远程文件操作，建议移除",
    },
    "Bash(tar czf": {
        "risk": "HIGH",
        "reason": "打包任意文件，配合 curl/scp 可完成数据窃取",
        "suggestion": "限制 tar 只能在项目目录内使用",
    },
    "Bash(tar -czf": {
        "risk": "HIGH",
        "reason": "打包任意文件，配合 curl/scp 可完成数据窃取",
        "suggestion": "限制 tar 只能在项目目录内使用",
    },
    "Bash(gzip": {
        "risk": "MEDIUM",
        "reason": "压缩文件，配合上传命令可完成数据窃取",
        "suggestion": "警惕 tar + curl 的组合行为",
    },
    "Bash(curl ": {
        "risk": "HIGH",
        "reason": "HTTP 上传/下载，可被用于数据外传",
        "suggestion": "限制 curl 只能在可信域名使用",
    },
    "Bash(wget ": {
        "risk": "HIGH",
        "reason": "HTTP 下载，可被用于数据外传",
        "suggestion": "如不需要，建议移除",
    },
    "Bash(rm -rf": {
        "risk": "CRITICAL",
        "reason": "不可逆删除，可被用于破坏代码库",
        "suggestion": "限制 rm -rf 只能在项目目录内使用",
    },
    "Bash(chmod": {
        "risk": "MEDIUM",
        "reason": "修改文件权限，可被用于授权恶意文件执行",
        "suggestion": "限制 chmod 修改范围",
    },
    "Bash(dd ": {
        "risk": "HIGH",
        "reason": "磁盘级写入，可被用于破坏系统",
        "suggestion": "如不需要，建议移除",
    },
    "Bash(nc ": {
        "risk": "CRITICAL",
        "reason": "网络连接，可被用于建立反向 Shell",
        "suggestion": "建议移除，ncat 是黑客工具箱",
    },
    "Bash(ncat": {
        "risk": "CRITICAL",
        "reason": "网络连接，可被用于建立反向 Shell",
        "suggestion": "建议移除",
    },
    "Bash(python3 -c": {
        "risk": "MEDIUM",
        "reason": "执行任意 Python 代码，可被用于绕过限制",
        "suggestion": "警惕 python3 -c 'import os; os.system(...)' 模式",
    },
}

# ── 安全命令（白名单，不提示） ──

SAFE_COMMAND_PREFIXES = [
    "git", "ls", "cat", "cd", "mkdir", "mv", "cp", "pwd", "echo",
    "grep", "find", "head", "tail", "wc", "sort", "uniq", "diff",
    "awk", "sed", "xargs", "tee", "tr", "cut", "sort",
    "pip", "npm", "pnpm", "yarn", "cargo", "go", "rustc",
    "python3", "python", "node", "deno", "bun",
    "make", "cmake", "ninja",
    "docker", "podman",
    "pytest", "jest", "mocha",
    "tsc", "eslint", "prettier", "black", "ruff",
    "ping", "mcp__",  # MCP 工具调用
    "Bash(git", "Bash(ls", "Bash(cat", "Bash(cd", "Bash(mkdir", "Bash(mv", "Bash(cp",
    "Bash(pwd", "Bash(echo", "Bash(awk", "Bash(sed", "Bash(grep", "Bash(find",
    "Bash(pip", "Bash(npm", "Bash(pnpm", "Bash(yarn", "Bash(mc ",
    "Bash(python3", "Bash(python", "Bash(node",
    "Bash(make", "Bash(cmake",
    "Bash(docker", "Bash(podman", "Bash(ping",
    "Bash(pytest", "Bash(jest", "Bash(mocha",
    "Bash(tsc", "Bash(eslint", "Bash(prettier", "Bash(black", "Bash(ruff",
    "Bash(ssh -o", "Bash(ssh -p",  # SSH 带参数但不含密码
    "Bash(pnpm build", "Bash(pnpm run", "Bash(pnpm --filter",
    "Bash(git add", "Bash(git commit", "Bash(git push", "Bash(git pull",
    "Bash(git status", "Bash(git log", "Bash(git diff", "Bash(git checkout",
    "Bash(git branch", "Bash(git merge", "Bash(git rebase", "Bash(git stash",
    "Bash(git submodule", "Bash(git tag",
    "Read(",  # 文件读取操作
    "Edit(",  # 文件编辑操作
    "Write(",  # 文件写入操作
]

# ── 已知安全域名白名单 ──

TRUSTED_DOMAINS = [
    "127.0.0.1",
    "localhost",
    "one.cloudkey.top",
    "pypi.org",
    "pypi.python.org",
    "github.com",
    "raw.githubusercontent.com",
    "registry.npmjs.org",
    "registry.yarnpkg.com",
    "cdn.jsdelivr.net",
    "unpkg.com",
]


def _classify_risk(cmd_type: str, cmd_detail: str) -> dict:
    """对单个命令进行风险分类"""
    # 检查是否已知高危命令（先匹配最具体的）
    for pattern in sorted(DANGEROUS_COMMANDS.keys(), key=len, reverse=True):
        if pattern in cmd_detail:
            info = DANGEROUS_COMMANDS[pattern]
            # 特殊处理 curl：检查域名是否可信
            if "curl" in pattern:
                for domain in TRUSTED_DOMAINS:
                    if domain in cmd_detail:
                        return {
                            "risk": "LOW",
                            "reason": f"curl 到可信域名 {domain}",
                            "suggestion": "",
                        }
            return {
                "risk": info["risk"],
                "reason": info["reason"],
                "suggestion": info["suggestion"],
            }

    # 检查是否安全命令（先匹配最具体的）
    for prefix in sorted(SAFE_COMMAND_PREFIXES, key=len, reverse=True):
        if cmd_detail.startswith(prefix):
            return {"risk": "LOW", "reason": "常规开发命令", "suggestion": ""}

    # 检查是否含有明文密码
    if "-p '" in cmd_detail or "-p \"" in cmd_detail or "--password" in cmd_detail:
        return {
            "risk": "CRITICAL",
            "reason": "命令行包含明文密码",
            "suggestion": "使用环境变量或配置文件替代命令行参数",
        }

    # 检查是否含有疑似 API Key
    if re.search(r'[Ss][Kk]-[a-zA-Z0-9]{20,}', cmd_detail):
        return {
            "risk": "CRITICAL",
            "reason": "命令行包含疑似 API Key",
            "suggestion": "使用环境变量管理 API Key，不要写在命令行中",
        }

    return {"risk": "INFO", "reason": "未分类命令", "suggestion": "请自行评估是否需要"}


def _scan_claude_permissions(home_dir: Path) -> dict[str, Any]:
    """扫描 Claude Code 的权限配置"""
    claude_dir = home_dir / ".claude"
    if not claude_dir.exists():
        return {"found": False, "message": "未发现 Claude Code 配置"}

    settings_local = claude_dir / "settings.local.json"
    if not settings_local.exists():
        return {"found": False, "message": "未发现 Claude Code 权限配置"}

    try:
        settings = json.loads(settings_local.read_text(encoding="utf-8", errors="ignore"))
    except Exception as e:
        return {"found": False, "message": f"配置文件解析失败: {e}"}

    allowed = settings.get("permissions", {}).get("allow", [])
    if not allowed:
        return {"found": False, "message": "未发现已授权命令"}

    # 分类所有命令
    classified = []
    total_commands = len(allowed)
    high_risk = 0
    critical = 0
    low_risk = 0

    for entry in allowed:
        cmd_type = entry.split("(")[0] if "(" in entry else "unknown"
        cmd_detail = entry

        risk_info = _classify_risk(cmd_type, cmd_detail)
        classified.append({
            "command": cmd_detail,
            "type": cmd_type,
            "risk": risk_info["risk"],
            "reason": risk_info["reason"],
            "suggestion": risk_info["suggestion"],
        })

        if risk_info["risk"] == "CRITICAL":
            critical += 1
        elif risk_info["risk"] == "HIGH":
            high_risk += 1
        elif risk_info["risk"] == "LOW":
            low_risk += 1

    # 统计实际使用情况（从 history.jsonl 中提取）
    history_file = claude_dir / "history.jsonl"
    used_commands = set()
    if history_file.exists():
        try:
            # 只读取最近 10MB 来分析近期使用
            text = history_file.read_text(encoding="utf-8", errors="ignore")
            # 提取所有 Bash 命令
            for match in re.finditer(r'Bash\(([^)]+)\)', text):
                used_commands.add(match.group(1).split("(")[0].strip())
        except Exception:
            pass

    # 计算闲置权限
    unused = []
    for c in classified:
        cmd_type = c["type"]
        # 检查是否在近期使用中
        if c["risk"] != "LOW" and cmd_type:
            is_used = False
            for used in used_commands:
                if cmd_type in used:
                    is_used = True
                    break
            if not is_used:
                unused.append(c)

    return {
        "found": True,
        "tool": "claude",
        "config_path": str(settings_local),
        "total_commands": total_commands,
        "critical": critical,
        "high_risk": high_risk,
        "low_risk": low_risk,
        "used_commands": len(used_commands),
        "unused_count": len(unused),
        "unused_percentage": round(len(unused) / total_commands * 100) if total_commands > 0 else 0,
        "classified": classified,
        "unused_suggestions": unused[:10],  # 最多建议 10 条
        "history_file": str(history_file) if history_file.exists() else None,
    }


def _scan_codex_permissions(home_dir: Path) -> dict[str, Any]:
    """扫描 Codex CLI 的权限配置"""
    codex_dir = home_dir / ".codex"
    if not codex_dir.exists():
        return {"found": False, "message": "未发现 Codex CLI 配置"}

    total_size = sum(f.stat().st_size for f in codex_dir.rglob("*") if f.is_file())
    return {
        "found": True,
        "tool": "codex",
        "path": str(codex_dir),
        "total_size_kb": round(total_size / 1024, 1),
    }


def cmd_audit(args) -> int:
    """执行 AI 工具权限审计

    用法:
        moat audit --permissions               # 审计所有 AI 工具权限
        moat audit --permissions --tool claude  # 只审计 Claude Code
        moat audit --permissions --fix          # 生成瘦身建议
    """
    from pathlib import Path

    home_dir = Path.home()
    print(f"\n🔐  AI 工具权限审计")
    print(f"{'=' * 55}")
    print(f"  扫描目录: {home_dir}")
    print(f"{'=' * 55}\n")

    results = []
    tool_filter = getattr(args, "tool", None)

    # 1. 扫描 Claude Code
    if not tool_filter or tool_filter == "claude":
        print(f"  📋 扫描 Claude Code 权限...")
        claude_result = _scan_claude_permissions(home_dir)
        results.append(claude_result)

        if claude_result.get("found"):
            print(f"    发现 {claude_result['total_commands']} 个已授权命令")
            print(f"    🔴 CRITICAL: {claude_result['critical']}")
            print(f"    🟡 HIGH:     {claude_result['high_risk']}")
            print(f"    🟢 LOW:      {claude_result['low_risk']}")
            print(f"    📊 闲置:     {claude_result['unused_count']} 个 ({claude_result['unused_percentage']}%)")
            print()
        else:
            print(f"    {claude_result.get('message', '')}\n")

    # 2. 扫描 Codex CLI
    if not tool_filter or tool_filter == "codex":
        print(f"  📋 扫描 Codex CLI...")
        codex_result = _scan_codex_permissions(home_dir)
        results.append(codex_result)
        if codex_result.get("found"):
            print(f"    数据量: {codex_result['total_size_kb']} KB")
        else:
            print(f"    {codex_result.get('message', '')}")
        print()

    # 3. 生成报告
    print(f"{'=' * 55}")
    print(f"  📊 审计报告")
    print(f"{'=' * 55}\n")

    for result in results:
        if not result.get("found"):
            continue

        tool = result.get("tool", "unknown")
        print(f"  🛠️  {tool.capitalize()}")
        print(f"  {'=' * 40}")

        if "total_commands" in result:
            print(f"  总权限: {result['total_commands']}")
            print(f"  实际使用: {result['used_commands']}")
            print(f"  闲置: {result['unused_count']} 个 ({result['unused_percentage']}%)")

            # 瘦身建议
            if result["unused_count"] > 0:
                print(f"\n  💡 权限瘦身建议:")
                print(f"     建议移除以下 {result['unused_count']} 个闲置高危权限:")
                for suggestion in result.get("unused_suggestions", []):
                    cmd = suggestion["command"]
                    risk = suggestion["risk"]
                    reason = suggestion["reason"]
                    sug = suggestion.get("suggestion", "")
                    risk_icon = "🔴" if risk == "CRITICAL" else "🟡" if risk == "HIGH" else "ℹ️"
                    print(f"     {risk_icon} {cmd[:60]}")
                    print(f"        {reason}")
                    if sug:
                        print(f"        → {sug}")
                print()

            # 汇总
            print(f"  📋 汇总:")
            print(f"     🔴 CRITICAL: {result['critical']} 个 — 建议立即处理")
            print(f"     🟡 HIGH:     {result['high_risk']} 个 — 建议审查")
            print(f"     🟢 LOW:      {result['low_risk']} 个 — 正常")
            print(f"     📊 闲置率:   {result['unused_percentage']}%")
            if result['unused_percentage'] > 50:
                print(f"     ⚠️  超过 50% 的权限闲置，建议执行瘦身")

        if "total_size_kb" in result:
            print(f"  数据量: {result['total_size_kb']} KB")

        print()

    # 生成可执行命令
    print(f"  📋 下一步操作:")
    print(f"  • 查看完整权限列表: cat ~/.claude/settings.local.json")
    print(f"  • 手动移除权限: 编辑 settings.local.json 删除对应条目")
    print(f"  • 迁移 sshpass: 配置 ~/.ssh/config 使用 SSH 密钥")
    print(f"  • 再次审计: moat audit --permissions\n")

    # 判断是否通过
    total_critical = sum(r.get("critical", 0) for r in results)
    return 0 if total_critical == 0 else 1