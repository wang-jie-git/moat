"""Moat Accept — 架构验收系统

`moat accept` 命令将项目代码审计结果按照"Vibe Coding 验收 8 步法"
输出结构化验收报告，并自动生成架构实施真元文档。

用法:
    moat accept                         # 执行完整验收（自动检测 architect.yml）
    moat accept --generate-rules        # 生成默认 architect.yml 模板
    moat accept --output report.md      # 指定输出文件
    moat accept --json                  # JSON 格式输出
    moat accept --fail-on-score 60      # 评分阈值门禁
"""

from .rule_registry import RuleRegistry, RuleDefinition
from .architect_runner import ArchitectRunner, AcceptanceReport
from .report_generator import AcceptanceReportGenerator

__all__ = [
    "RuleRegistry",
    "RuleDefinition",
    "ArchitectRunner",
    "AcceptanceReport",
    "AcceptanceReportGenerator",
]
