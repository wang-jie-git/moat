"""TypeScript 检查模块"""

from moat.checks.typescript.syntax import TypeScriptSyntaxCheck
from moat.checks.typescript.dedup import TypeScriptDedupCheck
from moat.checks.typescript.race_condition import TypeScriptRaceConditionCheck
from moat.checks.typescript.timing_doc import TypeScriptTimingDocCheck
from moat.checks.typescript.error_handling import TypeScriptErrorHandlingCheck

__all__ = [
    "TypeScriptSyntaxCheck",
    "TypeScriptDedupCheck",
    "TypeScriptRaceConditionCheck",
    "TypeScriptTimingDocCheck",
    "TypeScriptErrorHandlingCheck",
]
