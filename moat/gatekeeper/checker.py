"""
架构守门检查器 — 核心检查逻辑
"""

import time
from pathlib import Path

from .rules import RuleEngine
from .types import (
    GatekeeperConfig,
    GatekeeperResult,
    IgnoreMechanism,
    RuleViolation,
    RuleSeverity,
)


class ArchitectureGatekeeper:
    """
    架构守门检查器

    职责：
    1. 加载规则和配置
    2. 执行架构规则检查
    3. 执行 Karpathy Principles 检查
    4. 应用豁免机制
    5. 判断是否应该阻止写入
    6. 记录审计日志
    """

    def __init__(self, project_path: Path, config: GatekeeperConfig | None = None):
        self.project_path = project_path
        self.config = config or GatekeeperConfig.load(project_path)
        self.rule_engine = RuleEngine()

    def check_file(self, file_path: str | Path, content: str) -> GatekeeperResult:
        """
        检查文件是否符合架构规则

        Args:
            file_path: 文件路径
            content: 文件内容

        Returns:
            GatekeeperResult: 检查结果
        """
        start_time = time.time()
        file_path = str(file_path)

        # 1. 检查文件大小
        if len(content) > self.config.max_file_size:
            return GatekeeperResult(
                file_path=file_path,
                passed=True,
                violations=[],
                ignored_violations=[],
                execution_time=(time.time() - start_time) * 1000,
                should_block=False,
            )

        # 2. 执行规则检查
        context = {
            "project_path": str(self.project_path),
            "frameworks": self._detect_frameworks(),
        }

        all_violations = self.rule_engine.check_file(file_path, content, context)

        # 2.5. 执行 Karpathy Principles 检查（简化的文件内容检查）
        karpathy_violations = self._check_karpathy_principles(file_path, content)
        all_violations.extend(karpathy_violations)

        # 3. 应用豁免机制
        violations = []
        ignored_violations = []

        for violation in all_violations:
            if IgnoreMechanism.should_ignore(violation, file_path, self.config):
                ignored_violations.append(violation)
                # 记录豁免到审计日志
                self._log_ignore(violation, file_path)
            else:
                violations.append(violation)

        # 4. 判断是否应该阻止
        should_block = False
        if self.config.block_on_critical:
            should_block = any(v.severity.name == "CRITICAL" for v in violations)
        if not should_block and self.config.block_on_error:
            should_block = any(v.severity.name == "ERROR" for v in violations)
        if not should_block and self.config.block_on_warning:
            should_block = any(v.severity.name == "WARNING" for v in violations)

        # 5. 记录审计日志
        self._log_check(file_path, violations, ignored_violations, should_block)

        # 6. 判断是否通过
        passed = not should_block

        execution_time = (time.time() - start_time) * 1000

        return GatekeeperResult(
            file_path=file_path,
            passed=passed,
            violations=violations,
            ignored_violations=ignored_violations,
            execution_time=execution_time,
            should_block=should_block,
        )

    def _detect_frameworks(self) -> list[str]:
        """检测项目使用的框架"""
        frameworks = []

        requirements_file = self.project_path / "requirements.txt"
        if requirements_file.exists():
            content = requirements_file.read_text().lower()
            if "fastapi" in content:
                frameworks.append("fastapi")
            if "django" in content:
                frameworks.append("django")
            if "flask" in content:
                frameworks.append("flask")

        pyproject_file = self.project_path / "pyproject.toml"
        if pyproject_file.exists():
            content = pyproject_file.read_text().lower()
            if "fastapi" in content:
                frameworks.append("fastapi")
            if "django" in content:
                frameworks.append("django")

        return frameworks

    def _check_karpathy_principles(self, file_path: str, content: str) -> list:
        """
        检查 Karpathy Principles

        在文件级别检查简单原则：
        - Simplicity: 文件行数、函数长度
        """
        from moat.rules import PrinciplesLoader

        violations = []
        loader = PrinciplesLoader()
        principles = loader.load_principles()

        lines = content.split('\n')
        file_lines = len(lines)

        # 检查文件长度
        max_file_lines = principles["simplicity_first"].thresholds.get("max_file_lines", 500)
        if file_lines > max_file_lines:
            violations.append(RuleViolation(
                rule_id="karpathy.simplicity.file_size",
                severity=RuleSeverity.WARNING,
                message=f"文件过大（{file_lines} 行），违反 'Simplicity First' 原则。建议拆分。",
                file_path=file_path,
                suggestion=f"将文件拆分为多个模块，每个文件不超过 {max_file_lines} 行",
            ))

        return violations

    def _log_check(
        self,
        file_path: str,
        violations: list[RuleViolation],
        ignored_violations: list[RuleViolation],
        blocked: bool,
    ) -> None:
        """记录检查日志"""
        if not self.config.audit_log_path:
            return

        log_path = self.project_path / self.config.audit_log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)

        import json
        from datetime import datetime

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "file_path": file_path,
            "violations": [v.to_dict() for v in violations],
            "ignored_violations": [v.to_dict() for v in ignored_violations],
            "blocked": blocked,
        }

        try:
            with open(log_path, "a") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _log_ignore(self, violation: RuleViolation, file_path: str) -> None:
        """记录豁免日志"""
        # 已在_log_check中处理
        pass

    def format_violations(self, result: GatekeeperResult) -> str:
        """
        格式化违规信息用于显示

        Args:
            result: 守门结果

        Returns:
            格式化的字符串
        """
        if result.passed and not result.violations:
            return "✅ 通过"

        lines = []

        # 显示违规
        for v in result.violations:
            severity_icon = {
                "CRITICAL": "🔴",
                "ERROR": "❌",
                "WARNING": "⚠️",
                "INFO": "ℹ️",
            }.get(v.severity.name, "•")

            location = f"{v.file_path}"
            if v.line:
                location += f":{v.line}"

            lines.append(f"{severity_icon} [{v.rule_id}] {v.message}")
            lines.append(f"   📍 {location}")

            if v.suggestion:
                lines.append(f"   💡 {v.suggestion}")

        # 显示被豁免的违规
        if result.ignored_violations:
            lines.append(f"\n⚪ 已豁免 {len(result.ignored_violations)} 个违规")

        # 显示执行时间
        if result.execution_time > 0:
            lines.append(f"\n⏱️  执行时间: {result.execution_time:.1f}ms")

        # 显示是否阻止
        if result.should_block:
            lines.append(f"\n🚫 已阻止写入")

        return "\n".join(lines)
