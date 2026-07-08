"""
Moat Verification — 架构验收系统

核心能力:
- 审计算子化架构（7个独立算子）
- 编排器组合算子
- CLI命令（moat verify）

设计原则:
- 每个算子独立、可测试、可替换
- 通过组合而非继承实现流程
- 易于扩展新的验收步骤
"""

__version__ = "0.7.0-alpha"

from .types import (
    VerificationContext,
    OperatorResult,
    VerificationReport,
    Violation,
    Severity,
)
from .operator import VerificationOperator
from .orchestrator import VerifyOrchestrator
from .verify_cli import cmd_verify

__all__ = [
    "VerificationContext",
    "OperatorResult",
    "VerificationReport",
    "Violation",
    "Severity",
    "VerificationOperator",
    "VerifyOrchestrator",
    "cmd_verify",
]
