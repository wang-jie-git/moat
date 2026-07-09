"""
Moat 规则定义：Karpathy Principles Constitution

将软原则转化为硬规则，通过 Gatekeeper 和 Verification 系统强制执行。
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml
from dataclasses import dataclass, field


@dataclass
class Principle:
    """原则定义"""
    name: str
    description: str
    check_type: str
    enforcement: str  # "critical", "warning", "info"
    metrics: List[str] = field(default_factory=list)
    thresholds: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PrincipleViolation:
    """原则违规记录"""
    principle_name: str
    severity: str
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    context: Dict[str, Any] = field(default_factory=dict)


class PrinciplesLoader:
    """原则加载器"""

    def __init__(self, rules_dir: Optional[Path] = None):
        if rules_dir is None:
            # 默认使用项目根目录下的 moat/rules/
            rules_dir = Path(__file__).parent
        self.rules_dir = Path(rules_dir)
        self.principles: Dict[str, Principle] = {}

    def load_principles(self, filename: str = "karpathy_principles.yaml") -> Dict[str, Principle]:
        """加载原则定义"""
        yaml_path = self.rules_dir / filename

        if not yaml_path.exists():
            raise FileNotFoundError(f"规则文件不存在: {yaml_path}")

        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 解析原则定义
        for name, config in data.get('principles', {}).items():
            self.principles[name] = Principle(
                name=name,
                description=config.get('description', ''),
                check_type=config.get('check_type', 'manual'),
                enforcement=config.get('enforcement', 'info'),
                metrics=config.get('metrics', []),
                thresholds=config.get('thresholds', {})
            )

        return self.principles

    def get_principle(self, name: str) -> Optional[Principle]:
        """获取单个原则"""
        return self.principles.get(name)

    def get_enforcement_level(self, name: str) -> str:
        """获取原则的执行级别"""
        principle = self.principles.get(name)
        return principle.enforcement if principle else "info"

    def get_all_principles(self) -> Dict[str, Principle]:
        """获取所有原则"""
        return self.principles


# 延迟导入检查器，避免循环依赖
def get_surgical_checker():
    """获取手术刀检查器"""
    from moat.rules.surgical_changes import SurgicalChangesChecker
    return SurgicalChangesChecker


def get_simplicity_checker():
    """获取简单性检查器"""
    from moat.rules.simplicity_checker import SimplicityChecker
    return SimplicityChecker


__all__ = [
    "Principle",
    "PrincipleViolation",
    "PrinciplesLoader",
    "get_surgical_checker",
    "get_simplicity_checker",
]
