"""
Moat Gatekeeper — 实时架构守门系统

核心能力：
- 文件写入前的架构规则检查
- 三层豁免机制（文件级/行级/配置级）
- Claude Code Pre-Tool Hook集成
- 守护进程模式

设计原则：
- 默认拦截
- 显式豁免
- 审计追踪
- 定期清理提醒
"""

__version__ = "0.7.0-beta"

from .types import (
    GatekeeperConfig,
    RuleViolation,
    GatekeeperResult,
    IgnoreMechanism,
)
from .rules import RuleEngine, ArchitectureRule
from .checker import ArchitectureGatekeeper

__all__ = [
    "GatekeeperConfig",
    "RuleViolation",
    "GatekeeperResult",
    "IgnoreMechanism",
    "RuleEngine",
    "ArchitectureRule",
    "ArchitectureGatekeeper",
]
