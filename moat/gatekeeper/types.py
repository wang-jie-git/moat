"""
类型定义 — Gatekeeper守门系统
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class RuleSeverity(str, Enum):
    """规则严重程度"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class RuleViolation:
    """规则违规"""

    rule_id: str
    """规则ID"""

    rule_name: str
    """规则名称"""

    message: str
    """违规描述"""

    severity: RuleSeverity
    """严重程度"""

    file_path: str
    """违规文件路径"""

    line: int | None = None
    """违规行号"""

    suggestion: str | None = None
    """修复建议"""

    context: dict[str, Any] = field(default_factory=dict)
    """上下文信息"""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "message": self.message,
            "severity": self.severity.value,
            "file_path": self.file_path,
            "line": self.line,
            "suggestion": self.suggestion,
            "context": self.context,
        }


@dataclass
class GatekeeperResult:
    """守门检查结果"""

    file_path: str
    """检查的文件路径"""

    passed: bool
    """是否通过（无CRITICAL/ERROR违规）"""

    violations: list[RuleViolation]
    """违规列表"""

    ignored_violations: list[RuleViolation]
    """被豁免的违规列表"""

    execution_time: float = 0.0
    """执行时间（毫秒）"""

    should_block: bool = False
    """是否应该阻止写入"""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "file_path": self.file_path,
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
            "ignored_violations": [v.to_dict() for v in self.ignored_violations],
            "execution_time": self.execution_time,
            "should_block": self.should_block,
        }


@dataclass
class GatekeeperConfig:
    """守门配置"""

    # 豁免规则
    ignore_rules: dict[str, list[str]] = field(default_factory=dict)
    """
    配置文件级豁免
    格式: {"rule_id": ["path/pattern1", "path/pattern2"]}
    """

    # 审计日志
    audit_log_path: Path | None = None
    """审计日志路径"""

    # 拦截策略
    block_on_critical: bool = True
    """CRITICAL违规是否阻止写入"""

    block_on_error: bool = True
    """ERROR违规是否阻止写入"""

    block_on_warning: bool = False
    """WARNING违规是否阻止写入"""

    # 性能
    max_file_size: int = 1024 * 1024  # 1MB
    """最大检查文件大小"""

    timeout: float = 100.0  # 100ms
    """检查超时时间（毫秒）"""

    @classmethod
    def load(cls, project_path: Path) -> "GatekeeperConfig":
        """从项目加载配置"""
        config_path = project_path / ".moat" / "gatekeeper_config.json"

        if not config_path.exists():
            return cls()

        import json

        try:
            with open(config_path) as f:
                data = json.load(f)

            audit_log_path_str = data.get("audit_log_path")
            audit_log_path = Path(audit_log_path_str) if audit_log_path_str else None

            return cls(
                ignore_rules=data.get("ignore_rules", {}),
                audit_log_path=audit_log_path,
                block_on_critical=data.get("block_on_critical", True),
                block_on_error=data.get("block_on_error", True),
                block_on_warning=data.get("block_on_warning", False),
            )
        except Exception:
            return cls()

    def save(self, project_path: Path) -> None:
        """保存配置到项目"""
        config_path = project_path / ".moat" / "gatekeeper_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        import json

        data = {
            "ignore_rules": self.ignore_rules,
            "audit_log_path": str(self.audit_log_path) if self.audit_log_path else None,
            "block_on_critical": self.block_on_critical,
            "block_on_error": self.block_on_error,
            "block_on_warning": self.block_on_warning,
        }

        with open(config_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # 验证写入成功
        with open(config_path) as f:
            saved_data = json.load(f)

        if "ignore_rules" not in saved_data:
            raise RuntimeError("配置保存失败：ignore_rules不在保存的数据中")

    def get_ignore_list(self, rule_id: str | None = None) -> dict[str, list[str]]:
        """获取豁免列表"""
        if rule_id:
            return {rule_id: self.ignore_rules.get(rule_id, [])}
        return self.ignore_rules


class IgnoreMechanism:
    """
    三层豁免机制

    层级1：文件注释（最细粒度）
    层级2：行内注释（单行豁免）
    层级3：项目配置（整文件/整目录豁免）
    """

    @staticmethod
    def should_ignore(violation: RuleViolation, file_path: str, config: GatekeeperConfig) -> bool:
        """
        检查是否应该豁免该违规

        Args:
            violation: 违规对象
            file_path: 文件路径
            config: 守门配置

        Returns:
            True表示应该豁免，False表示应该拦截
        """
        # 层级1：行内注释（优先级最高，最细粒度）
        if IgnoreMechanism._has_line_ignore(violation, file_path):
            return True

        # 层级2：文件注释
        if IgnoreMechanism._has_file_ignore(violation, file_path):
            return True

        # 层级3：配置文件
        if IgnoreMechanism._has_config_ignore(violation, file_path, config):
            return True

        return False

    @staticmethod
    def _has_line_ignore(violation: RuleViolation, file_path: str) -> bool:
        """层级1：行内豁免注释"""
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            lines = content.split('\n')

            # 检查违规行上下5行
            start = max(0, (violation.line or 0) - 5)
            end = min(len(lines), (violation.line or 0) + 5)
            context = '\n'.join(lines[start:end])

            ignore_pattern = f"# moat-ignore: {violation.rule_id}"
            return ignore_pattern in context

        except Exception:
            return False

    @staticmethod
    def _has_file_ignore(violation: RuleViolation, file_path: str) -> bool:
        """层级2：文件级豁免注释"""
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            # 只检查前10行（文件头部）
            header = '\n'.join(content.split('\n')[:10])

            ignore_pattern = f"# moat-ignore: {violation.rule_id}"
            return ignore_pattern in header

        except Exception:
            return False

    @staticmethod
    def _has_config_ignore(violation: RuleViolation, file_path: str, config: GatekeeperConfig) -> bool:
        """层级3：配置文件豁免"""
        import fnmatch

        # 获取该规则的豁免列表
        ignore_list = config.ignore_rules.get(violation.rule_id, [])
        if not ignore_list:
            return False

        # 检查文件路径是否匹配任何豁免模式
        for pattern in ignore_list:
            if fnmatch.fnmatch(file_path, pattern):
                return True

        return False

    @staticmethod
    def add_ignore_comment(file_path: str, rule_id: str, line: int | None = None) -> None:
        """
        添加豁免注释到文件

        Args:
            file_path: 文件路径
            rule_id: 规则ID
            line: 行号（None表示添加到文件头部）
        """
        ignore_comment = f"# moat-ignore: {rule_id}"

        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            lines = content.split('\n')

            if line:
                # 添加到指定行
                insert_pos = min(line, len(lines))
                lines.insert(insert_pos, ignore_comment)
            else:
                # 添加到文件头部（前10行内）
                insert_pos = 0
                for i, line_content in enumerate(lines[:10]):
                    if line_content.strip() and not line_content.startswith("#"):
                        insert_pos = i
                        break

                lines.insert(insert_pos, ignore_comment)

            Path(file_path).write_text('\n'.join(lines), encoding="utf-8")

        except Exception as e:
            raise RuntimeError(f"添加豁免注释失败: {e}")
