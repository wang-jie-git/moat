"""
算子9：泄露检测器 — 检测 AI 工具是否跨目录读取敏感文件

背景：Grok CLI 被曝在用户不知情时打包整个代码库上传，并跨目录读取
~/.claude/ 等配置文件。Moat LeakageChecker 静态扫描当前项目，
检测已知 AI 工具配置残留、跨目录读取痕迹、以及敏感文件泄露风险。

检查项：
- [ ] 是否在项目内发现 ~/.claude/ ~/.grok/ 等 AI 工具配置的引用
- [ ] 是否有 .env 文件暴露在版本控制中
- [ ] 是否有 symlink 指向项目外敏感目录
- [ ] 是否有 .gitignore 未覆盖的敏感文件
- [ ] 是否有 AI 工具历史记录中包含非项目文件路径

设计原则：
- 静态审计：不实时监控，只在用户主动调用时扫描
- 默认黑名单：内置 .ssh, .aws, .claude, .grok 等敏感目录
- fail-open：单个文件解析失败不影响全量检查
"""

import os
import re
from pathlib import Path
from typing import Any

from ..types import (
    OperatorResult,
    Severity,
    VerificationContext,
    Violation,
    iter_python_files,
)

# ── 内置敏感目录黑名单 ──

SENSITIVE_DIRS = [
    ".ssh",
    ".aws",
    ".grok",
    ".claude",
    ".codex",
    ".kube",
    ".config",
    ".npmrc",
    ".docker",
    ".credentials",
    ".secret",
    "secrets",
    "credentials",
]

SENSITIVE_FILES = [
    ".env",
    ".env.local",
    ".env.prod",
    ".env.production",
    ".env.dev",
    "credentials.json",
    "service-account.json",
    "*.pem",
    "*.key",
    "id_rsa",
    "id_ed25519",
    "config.json",
]

AI_TOOL_PATTERNS = [
    # Grok CLI
    (".grok", "Grok CLI 会话目录"),
    ("grok-code-session-traces", "Grok 上传痕迹"),
    ("before_codebase.tar.gz", "Grok 代码库快照"),
    ("after_codebase.tar.gz", "Grok 代码库快照"),
    # Claude Code 敏感目录
    (".claude", "Claude Code 配置目录"),
    ("claude.json", "Claude Code 配置文件"),
    # Codex
    (".codex", "Codex CLI 会话目录"),
    # OpenAI
    (".openai", "OpenAI 工具配置"),
]


class LeakageDetectionOperator:
    """
    算子9：泄露检测器

    静态扫描当前项目，检测已知 AI 工具配置残留、跨目录读取痕迹、
    以及敏感文件泄露风险。
    """

    name = "leakage_detection"
    description = "检测 AI 工具跨目录读取敏感文件、代码泄露风险"

    def __init__(self, sensitive_dirs: list[str] | None = None):
        self.sensitive_dirs = sensitive_dirs or SENSITIVE_DIRS

    def verify(self, context: VerificationContext) -> OperatorResult:
        """执行泄露检测"""
        project_path = context.project_path
        violations: list[Violation] = []
        evidence: dict[str, Any] = {}
        suggestions: list[str] = []

        # AI 工具系统配置扫描模式
        scan_ai = context.config.get("scan_ai", False)
        if scan_ai:
            print(f"   🕵️ 扫描 AI 工具系统配置...")
            ai_violations = self._scan_ai_configs()
            violations.extend(ai_violations)

            # 聚合系统扫描结果
            critical_count = sum(1 for v in violations if v.severity == Severity.CRITICAL)
            warning_count = sum(1 for v in violations if v.severity == Severity.WARNING)

            if ai_violations:
                evidence["scan_ai_summary"] = {
                    "total_findings": len(ai_violations),
                    "critical": critical_count,
                    "warning": warning_count,
                }
                suggestions.append(f"AI 工具审计: 发现 {len(ai_violations)} 项")
                if critical_count > 0:
                    suggestions.append(f"  🔴 {critical_count} 项严重风险")
            else:
                suggestions.append("未发现已知 AI 工具配置")

            passed = critical_count == 0
            return OperatorResult(
                operator_name=self.name,
                passed=passed,
                evidence=evidence,
                violations=violations,
                suggestions=suggestions,
            )

        print(f"   🔍 扫描泄露风险...")

        # 1. 检测项目内是否存在 AI 工具配置引用
        ai_tool_findings = self._check_ai_tool_traces(project_path)
        evidence["ai_tool_traces"] = ai_tool_findings

        if ai_tool_findings:
            for finding in ai_tool_findings:
                violations.append(
                    Violation(
                        rule="leakage_detection",
                        message=f"发现 AI 工具痕迹: {finding['pattern']} ({finding['description']})",
                        severity=Severity.CRITICAL,
                        file_path=finding.get("file_path"),
                        suggestion=f"检查 {finding['pattern']} 是否引入了敏感配置。如不需要，请从项目中移除。",
                    )
                )

        # 2. 检测 .env 文件是否暴露在版本控制中
        env_findings = self._check_env_exposure(project_path)
        evidence["env_exposure"] = env_findings

        if env_findings:
            for finding in env_findings:
                violations.append(
                    Violation(
                        rule="leakage_detection",
                        message=f"敏感文件暴露: {finding['file']}",
                        severity=Severity.CRITICAL,
                        file_path=finding["file"],
                        suggestion=f"将 {finding['file']} 加入 .gitignore。使用 .env.example 作为模板提交。",
                    )
                )

        # 3. 检测 symlink 是否指向项目外
        symlink_findings = self._check_symlink_leaks(project_path)
        evidence["symlink_leaks"] = symlink_findings

        if symlink_findings:
            for finding in symlink_findings:
                violations.append(
                    Violation(
                        rule="leakage_detection",
                        message=f"符号链接指向项目外: {finding['file']} → {finding['target']}",
                        severity=Severity.WARNING,
                        file_path=finding["file"],
                        suggestion="使用相对路径或复制文件到项目内，避免 symlink \"引狼入室\"。",
                    )
                )

        # 4. 检测 .gitignore 是否覆盖了敏感文件
        gitignore_findings = self._check_gitignore_coverage(project_path)
        evidence["gitignore_coverage"] = gitignore_findings

        # 5. 检测项目代码中是否硬编码了敏感路径
        hardcoded_findings = self._check_hardcoded_paths(project_path)
        evidence["hardcoded_paths"] = hardcoded_findings

        if hardcoded_findings:
            for finding in hardcoded_findings:
                violations.append(
                    Violation(
                        rule="leakage_detection",
                        message=f"代码中硬编码了敏感路径: {finding['path']}",
                        severity=Severity.WARNING,
                        file_path=finding["file"],
                        line=finding.get("line"),
                        suggestion="使用环境变量或配置文件替代硬编码的绝对路径。",
                    )
                )

        # 聚合建议
        if violations:
            suggestions.append(f"发现 {len(violations)} 个泄露风险")
            critical_count = sum(1 for v in violations if v.severity == Severity.CRITICAL)
            warning_count = sum(1 for v in violations if v.severity == Severity.WARNING)
            if critical_count > 0:
                suggestions.append(f"  🔴 {critical_count} 个 CRITICAL 风险，建议立即修复")
            if warning_count > 0:
                suggestions.append(f"  🟡 {warning_count} 个 WARNING 风险，建议尽快检查")

            # 按严重程度排序给出建议
            for v in violations:
                if v.severity == Severity.CRITICAL:
                    suggestions.append(f"  📍 {v.file_path}: {v.message}")
        else:
            suggestions.append("未检测到代码泄露风险")

        # 总结
        evidence["total_checks"] = {
            "ai_tool_traces": len(ai_tool_findings),
            "env_exposure": len(env_findings),
            "symlink_leaks": len(symlink_findings),
            "hardcoded_paths": len(hardcoded_findings),
        }

        passed = len([v for v in violations if v.severity == Severity.CRITICAL]) == 0

        return OperatorResult(
            operator_name=self.name,
            passed=passed,
            evidence=evidence,
            violations=violations,
            suggestions=suggestions,
        )

    def _check_ai_tool_traces(self, project_path: Path) -> list[dict]:
        """检测 AI 工具配置残留"""
        findings = []

        for pattern, description in AI_TOOL_PATTERNS:
            # 检查项目根目录
            for item in project_path.iterdir():
                name = item.name
                if pattern in name:
                    findings.append({
                        "pattern": pattern,
                        "description": description,
                        "file_path": str(item),
                    })

        # 扫描 .gitignore 中是否引用了敏感目录
        gitignore = project_path / ".gitignore"
        if gitignore.exists():
            content = gitignore.read_text()
            for pattern, description in AI_TOOL_PATTERNS:
                if pattern in content:
                    pass  # 已排除，安全

        # 检查 .moat 缓存中是否有外部路径引用
        moat_cache = project_path / ".moat"
        if moat_cache.exists():
            for cache_file in moat_cache.rglob("*"):
                if cache_file.is_file() and cache_file.suffix in (".json", ".txt", ".log"):
                    try:
                        text = cache_file.read_text(encoding="utf-8", errors="ignore")
                        # 检测 home 目录引用
                        home = Path.home()
                        home_str = str(home)
                        if home_str in text:
                            # 提取具体路径
                            for line in text.split("\n"):
                                if home_str in line:
                                    findings.append({
                                        "pattern": "~/.moat 缓存包含外部路径",
                                        "description": "Moat 缓存中发现了 home 目录引用",
                                        "file_path": str(cache_file),
                                    })
                                    break
                    except Exception:
                        pass

        return findings

    def _scan_ai_configs(self, home_dir: Path | None = None) -> list[Violation]:
        """扫描 AI 工具系统配置目录 — 检测数据窃取风险

        扫描 ~/.claude/, ~/.grok/, ~/.codex/ 等目录，检查：
        - telemetry / 遥测配置
        - 敏感命令授权（sshpass, scp, tar czf 等）
        - 会话日志大小和内容
        - 项目索引覆盖范围
        """
        if home_dir is None:
            home_dir = Path.home()

        violations: list[Violation] = []
        total_data_size = 0

        # ── 1. Claude Code ──
        claude_dir = home_dir / ".claude"
        if claude_dir.exists():
            print(f"   📋 发现 Claude Code 配置: {claude_dir}")

            # 检查 telemetry 目录
            telemetry_dir = claude_dir / "telemetry"
            if telemetry_dir.exists():
                telemetry_files = list(telemetry_dir.rglob("*"))
                telemetry_size = sum(f.stat().st_size for f in telemetry_files if f.is_file())
                total_data_size += telemetry_size
                violations.append(
                    Violation(
                        rule="ai_agent_audit",
                        message=f"Claude Code 遥测数据: {len(telemetry_files)} 个文件, {telemetry_size / 1024:.1f} KB",
                        severity=Severity.WARNING,
                        file_path=str(telemetry_dir),
                        suggestion="检查 telemetry 目录内容。如需关闭遥测，检查 settings.json 中的 telemetry_enabled 配置。",
                    )
                )

            # 检查会话日志
            history_file = claude_dir / "history.jsonl"
            if history_file.exists():
                history_size = history_file.stat().st_size
                total_data_size += history_size
                # 检查会话日志中是否包含敏感信息
                try:
                    sample = history_file.read_text(encoding="utf-8", errors="ignore")[:2000]
                    # 检测 API keys
                    if re.search(r'[Ss][Kk]-[a-zA-Z0-9]{20,}', sample):
                        violations.append(
                            Violation(
                                rule="ai_agent_audit",
                                message="Claude Code 会话日志包含疑似 API Key",
                                severity=Severity.CRITICAL,
                                file_path=str(history_file),
                                suggestion="立即检查并清理 history.jsonl 中的 API Key。考虑使用环境变量而非明文配置。",
                            )
                        )
                except Exception:
                    pass
                violations.append(
                    Violation(
                        rule="ai_agent_audit",
                        message=f"Claude Code 会话历史: {history_size / 1024:.1f} KB",
                        severity=Severity.INFO,
                        file_path=str(history_file),
                        suggestion=f"会话日志包含所有对话历史。如涉及敏感信息，建议定期清理。",
                    )
                )

            # 检查 settings.local.json 中的危险命令授权
            settings_local = claude_dir / "settings.local.json"
            if settings_local.exists():
                try:
                    import json
                    settings = json.loads(settings_local.read_text(encoding="utf-8", errors="ignore"))
                    allowed = settings.get("permissions", {}).get("allow", [])
                    dangerous_commands = ["sshpass", "scp ", "tar czf", "curl ", "rm -rf", "chmod"]
                    found_dangerous = []
                    for cmd in dangerous_commands:
                        for entry in allowed:
                            if cmd in entry:
                                found_dangerous.append(entry[:80])
                    if found_dangerous:
                        violations.append(
                            Violation(
                                rule="ai_agent_audit",
                                message=f"Claude Code 已授权 {len(found_dangerous)} 个敏感命令",
                                severity=Severity.WARNING,
                                file_path=str(settings_local),
                                suggestion="检查授权列表中的敏感命令（sshpass, scp, tar czf 等）。如需撤销，编辑 settings.local.json 移除对应条目。",
                                evidence={"dangerous_commands": found_dangerous},
                            )
                        )
                except Exception:
                    pass

            # 检查 sessions 目录
            sessions_dir = claude_dir / "sessions"
            if sessions_dir.exists():
                session_files = list(sessions_dir.rglob("*"))
                session_size = sum(f.stat().st_size for f in session_files if f.is_file())
                total_data_size += session_size
                if session_size > 1024 * 100:  # > 100KB
                    violations.append(
                        Violation(
                            rule="ai_agent_audit",
                            message=f"Claude Code 会话数据: {session_size / 1024:.1f} KB",
                            severity=Severity.INFO,
                            file_path=str(sessions_dir),
                            suggestion="会话数据包含 AI 交互历史，涉及项目代码和决策记录。",
                        )
                    )

        # ── 2. Grok CLI ──
        grok_dir = home_dir / ".grok"
        if grok_dir.exists():
            grok_size = sum(f.stat().st_size for f in grok_dir.rglob("*") if f.is_file())
            total_data_size += grok_size
            violations.append(
                Violation(
                    rule="ai_agent_audit",
                    message=f"Grok CLI 配置存在: {grok_size / 1024:.1f} KB 数据",
                    severity=Severity.CRITICAL,
                    file_path=str(grok_dir),
                    suggestion="Grok CLI 已被曝自动打包上传代码库。建议立即卸载: npm uninstall -g @xai-official/grok",
                )
            )

        # ── 3. Codex CLI ──
        codex_dir = home_dir / ".codex"
        if codex_dir.exists():
            codex_size = sum(f.stat().st_size for f in codex_dir.rglob("*") if f.is_file())
            total_data_size += codex_size
            violations.append(
                Violation(
                    rule="ai_agent_audit",
                    message=f"Codex CLI 配置存在: {codex_size / 1024:.1f} KB 数据",
                    severity=Severity.WARNING,
                    file_path=str(codex_dir),
                    suggestion="Codex CLI 会记录会话数据。请确认其隐私政策。",
                )
            )

        # ── 聚合报告 ──
        if violations:
            print(f"   📊 AI 工具数据总量: {total_data_size / 1024:.1f} KB")

        return violations

    def _check_env_exposure(self, project_path: Path) -> list[dict]:
        """检测 .env 文件暴露"""
        findings = []

        for pattern in SENSITIVE_FILES:
            if "*" in pattern:
                continue  # 暂时跳过 glob 模式
            env_file = project_path / pattern
            if env_file.exists() and env_file.is_file():
                gitignore = project_path / ".gitignore"
                pattern_in_gitignore = False
                if gitignore.exists():
                    for line in gitignore.read_text().split("\n"):
                        line = line.strip()
                        if line and not line.startswith("#") and pattern in line:
                            pattern_in_gitignore = True
                            break

                if not pattern_in_gitignore:
                    findings.append({
                        "file": pattern,
                        "exposed": True,
                        "in_gitignore": False,
                    })

        return findings

    def _check_symlink_leaks(self, project_path: Path) -> list[dict]:
        """检测 symlink 是否指向项目外"""
        findings = []
        project_root = project_path.resolve()

        for item in project_path.rglob("*"):
            if item.is_symlink():
                try:
                    target = item.readlink()
                    # 解析相对路径
                    if not target.is_absolute():
                        target = item.parent / target
                    target = target.resolve()

                    # 检查是否指向项目外
                    if not str(target).startswith(str(project_root)):
                        # 检查目标是否在敏感目录列表中
                        for sensitive in self.sensitive_dirs:
                            if sensitive in str(target):
                                findings.append({
                                    "file": str(item),
                                    "target": str(target),
                                    "sensitive": sensitive,
                                })
                                break
                        else:
                            # 非敏感但也指向外部，记录低风险
                            pass
                except Exception:
                    pass

        return findings

    def _check_gitignore_coverage(self, project_path: Path) -> list[dict]:
        """检测 .gitignore 覆盖范围"""
        findings = []

        gitignore = project_path / ".gitignore"
        if not gitignore.exists():
            findings.append({
                "issue": "缺少 .gitignore",
                "recommendation": "创建 .gitignore 文件，至少排除 .env 和敏感目录",
            })
            return findings

        content = gitignore.read_text()
        missing = []

        # 检查是否覆盖了敏感目录
        for sensitive in SENSITIVE_DIRS:
            if sensitive not in content:
                missing.append(sensitive)

        # 检查是否覆盖了敏感文件
        for sensitive_file in [".env", ".env.local", ".env.prod", "credentials.json"]:
            if sensitive_file not in content:
                missing.append(sensitive_file)

        if missing:
            findings.append({
                "issue": ".gitignore 未覆盖的敏感条目",
                "missing": missing,
                "count": len(missing),
            })

        return findings

    def _check_hardcoded_paths(self, project_path: Path) -> list[dict]:
        """检测代码中硬编码的敏感路径"""
        findings = []
        home = Path.home()
        home_str = str(home)

        # 常见敏感路径模式
        sensitive_path_patterns = [
            re.compile(rf"['\"]{re.escape(home_str)}/(\.\w+)/?['\"]"),
            re.compile(rf"['\"]~/(\.\w+)/?['\"]"),
            re.compile(r"['\"](/.+?/\.ssh/?)['\"]"),
            re.compile(r"['\"](/.+?/\.aws/?)['\"]"),
            re.compile(r"['\"](/.+?/\.claude/?)['\"]"),
            re.compile(r"['\"](/.+?/\.grok/?)['\"]"),
        ]

        for py_file in iter_python_files(project_path):
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                for idx, line in enumerate(content.split("\n"), 1):
                    for pattern in sensitive_path_patterns:
                        match = pattern.search(line)
                        if match:
                            # 忽略注释行
                            stripped = line.strip()
                            if stripped.startswith("#") or stripped.startswith("//"):
                                continue
                            findings.append({
                                "file": str(py_file),
                                "line": idx,
                                "path": match.group(1) if match.lastindex else match.group(0),
                                "preview": line.strip()[:80],
                            })
                            break
            except Exception:
                pass

        return findings