"""
算子注册表 — 导入所有算子
"""

from .directory_responsibility import DirectoryResponsibilityOperator
from .minimal_module_drill import MinimalModuleDrillOperator
from .api_response_spec import APIResponseSpecOperator
from .framework_usage import FrameworkUsageOperator
from .runtime_evidence import RuntimeEvidenceOperator
from .architecture_health_score import ArchitectureHealthScoreOperator
from .truth_document import TruthDocumentGeneratorOperator

__all__ = [
    "DirectoryResponsibilityOperator",
    "MinimalModuleDrillOperator",
    "APIResponseSpecOperator",
    "FrameworkUsageOperator",
    "RuntimeEvidenceOperator",
    "ArchitectureHealthScoreOperator",
    "TruthDocumentGeneratorOperator",
]
