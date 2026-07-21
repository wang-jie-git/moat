"""
类型定义 — 架构验收系统
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


# 默认排除的目录 — 避免扫描虚拟环境 / 第三方依赖
DEFAULT_EXCLUDE_DIRS = {".venv", "venv", ".venv.prod", ".venv.dev",
                        "__pycache__", ".git", "node_modules",
                        "dist", "build", ".tox", ".eggs", "egg-info"}


def iter_python_files(project_path: Path, *, exclude_dirs: set[str] | None = None, target_files: list[str] | None = None) -> list[Path]:
    """遍历 Python 文件，自动排除虚拟环境等目录

    Args:
        project_path: 项目根路径
        exclude_dirs: 要排除的目录名集合（默认 DEFAULT_EXCLUDE_DIRS）
        target_files: 增量模式 — 只返回这些文件中的 Python 文件

    Returns:
        Python 文件列表
    """
    if target_files is not None:
        # 增量模式：只返回指定文件中的 Python 文件
        return [project_path / f for f in target_files if (project_path / f).exists() and (project_path / f).suffix == ".py"]

    exclude = exclude_dirs or DEFAULT_EXCLUDE_DIRS
    files: list[Path] = []
    for py_file in project_path.rglob("*.py"):
        # 跳过排除目录中的文件
        if any(part in exclude for part in py_file.parts):
            continue
        files.append(py_file)
    return files


class Severity(str, Enum):
    """违规严重程度"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Violation:
    """架构违规"""

    rule: str
    """违规规则名称"""

    message: str
    """违规描述"""

    severity: Severity
    """严重程度"""

    file_path: str | None = None
    """违规文件路径"""

    line: int | None = None
    """违规行号"""

    suggestion: str | None = None
    """修复建议"""

    evidence: dict[str, Any] = field(default_factory=dict)
    """证据数据"""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "rule": self.rule,
            "message": self.message,
            "severity": self.severity.value,
            "file_path": self.file_path,
            "line": self.line,
            "suggestion": self.suggestion,
            "evidence": self.evidence,
        }


@dataclass
class OperatorResult:
    """单个算子的验收结果"""

    operator_name: str
    """算子名称"""

    passed: bool
    """是否通过"""

    evidence: dict[str, Any] = field(default_factory=dict)
    """证据数据"""

    violations: list[Violation] = field(default_factory=list)
    """违规列表"""

    suggestions: list[str] = field(default_factory=list)
    """改进建议"""

    execution_time: float = 0.0
    """执行时间（秒）"""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "operator_name": self.operator_name,
            "passed": self.passed,
            "evidence": self.evidence,
            "violations": [v.to_dict() for v in self.violations],
            "suggestions": self.suggestions,
            "execution_time": self.execution_time,
        }


@dataclass
class VerificationContext:
    """验收上下文"""

    project_path: Path
    """项目根路径"""

    target_files: list[str] | None = None
    """增量模式下限定检查的文件列表（None = 全量检查）"""

    config: dict[str, Any] = field(default_factory=dict)
    """配置参数"""

    timestamp: datetime = field(default_factory=datetime.now)
    """验收时间戳"""


@dataclass
class VerificationReport:
    """完整验收报告"""

    project_path: Path
    """项目路径"""

    operators: list[OperatorResult]
    """所有算子结果"""

    overall_score: float = 0.0
    """总体评分（0-100）"""

    passed: bool = False
    """是否全部通过"""

    timestamp: datetime = field(default_factory=datetime.now)
    """报告生成时间"""

    def get_violations(self) -> list[Violation]:
        """获取所有违规"""
        violations = []
        for operator in self.operators:
            violations.extend(operator.violations)
        return violations

    def get_critical_violations(self) -> list[Violation]:
        """获取CRITICAL级别违规"""
        return [v for v in self.get_violations() if v.severity == Severity.CRITICAL]

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "project_path": str(self.project_path),
            "timestamp": self.timestamp.isoformat(),
            "overall_score": self.overall_score,
            "passed": self.passed,
            "operators": [op.to_dict() for op in self.operators],
            "total_violations": len(self.get_violations()),
            "critical_violations": len(self.get_critical_violations()),
        }

    def to_markdown(self) -> str:
        """生成Markdown报告"""
        lines = [
            "# 架构验收报告",
            "",
            f"**项目路径**: {self.project_path}",
            f"**验收时间**: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**总体评分**: {self.overall_score}/100",
            f"**状态**: {'✅ 通过' if self.passed else '❌ 未通过'}",
            "",
            "---",
            "",
        ]

        # 添加每个算子的结果
        for operator in self.operators:
            status = "✅" if operator.passed else "❌"
            lines.append(f"## {status} {operator.operator_name}")
            lines.append("")

            if operator.evidence:
                lines.append("**证据**:")
                for key, value in operator.evidence.items():
                    lines.append(f"- {key}: {value}")
                lines.append("")

            if operator.violations:
                lines.append("**违规**:")
                for violation in operator.violations:
                    severity_icon = {
                        Severity.INFO: "ℹ️",
                        Severity.WARNING: "⚠️",
                        Severity.ERROR: "❌",
                        Severity.CRITICAL: "🔴",
                    }[violation.severity]

                    lines.append(f"- {severity_icon} **{violation.rule}** ({violation.severity.value})")
                    lines.append(f"  - {violation.message}")
                    if violation.file_path:
                        location = f"{violation.file_path}"
                        if violation.line:
                            location += f":{violation.line}"
                        lines.append(f"  - 📍 {location}")
                    if violation.suggestion:
                        lines.append(f"  - 💡 {violation.suggestion}")
                lines.append("")

            if operator.suggestions:
                lines.append("**建议**:")
                for suggestion in operator.suggestions:
                    lines.append(f"- {suggestion}")
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)
