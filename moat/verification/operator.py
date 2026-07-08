"""
审计算子基类 — 所有算子必须实现此协议
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import VerificationContext, OperatorResult


class VerificationOperator(ABC):
    """
    审计算子基类

    所有验收步骤（7个算子）都必须继承此类并实现verify方法。

    示例:
        class DirectoryResponsibilityOperator(VerificationOperator):
            name = "directory_responsibility"
            description = "验证每个目录的责任是否清晰"

            def verify(self, context: VerificationContext) -> OperatorResult:
                # 实现检查逻辑
                ...
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        算子名称（如 'directory_responsibility'）

        用于CLI参数和报告标识
        """
        ...

    @property
    def description(self) -> str:
        """
        算子描述（默认实现，子类可覆盖）

        用于帮助文本
        """
        return self.__class__.__doc__ or "未描述"

    @abstractmethod
    def verify(self, context: VerificationContext) -> "OperatorResult":
        """
        执行审计算法

        Args:
            context: 验收上下文（项目路径、配置等）

        Returns:
            OperatorResult包含:
                - passed: 是否通过
                - violations: 违规列表
                - evidence: 证据数据
                - suggestions: 改进建议
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
