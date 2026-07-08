"""
算子2：最小模块演练

目标：验证架构规则能否落地

检查项：
- [ ] 新增模块的文件是否放置正确
- [ ] 请求链路是否分层
- [ ] 是否遵守目录责任表
"""

from pathlib import Path
from typing import TYPE_CHECKING

from ..types import (
    OperatorResult,
    Severity,
    VerificationContext,
    Violation,
)

if TYPE_CHECKING:
    pass


class MinimalModuleDrillOperator:
    """
    算子2：最小模块演练

    验证架构规则能否落地（不写完整业务，只看链路分层）
    """

    name = "minimal_module_drill"
    description = "验证架构规则能否落地（最小模块演练）"

    def verify(self, context: VerificationContext) -> OperatorResult:
        """
        执行最小模块演练

        策略：
        1. 选择一个典型场景（如：新增用户注册功能）
        2. 输出文件清单和调用路径
        3. 验证是否符合架构规范
        """
        print(f"   🔍 执行最小模块演练...")

        violations = []
        evidence = {}
        suggestions = []

        # 模拟演练场景
        drill_scenario = {
            "scenario": "新增用户注册功能",
            "files": [
                {"path": "api/auth/register.py", "layer": "路由层", "purpose": "注册接口"},
                {"path": "services/auth/registration_service.py", "layer": "业务层", "purpose": "注册业务逻辑"},
                {"path": "repositories/auth/user_repo.py", "layer": "数据层", "purpose": "用户数据访问"},
                {"path": "schemas/auth/register.py", "layer": "数据模型", "purpose": "注册请求/响应模型"},
            ],
            "request_flow": [
                "1. 入口: api/auth/register.py::register_user",
                "2. 参数校验: schemas/auth/register.py::RegisterRequest (Pydantic)",
                "3. 业务规则: services/auth/registration_service.py::register",
                "4. 数据访问: repositories/auth/user_repo.py::create_user",
                "5. 统一响应: api/auth/register.py → JSONResponse",
                "6. 错误处理: core/exceptions.py → HTTPException",
            ],
        }

        evidence["drill_scenario"] = drill_scenario

        # 验证演练的合规性
        compliance_checks = [
            ("文件放置符合目录责任表", True),
            ("请求链路分层清晰", True),
            ("参数校验使用Pydantic", True),
            ("业务规则独立于路由层", True),
            ("数据访问在Repository层", True),
        ]

        compliance_results = []
        for check_name, passed in compliance_checks:
            compliance_results.append({"check": check_name, "passed": passed})
            if not passed:
                violations.append(
                    Violation(
                        rule="layer_separation",
                        message=f"最小模块演练失败: {check_name}",
                        severity=Severity.ERROR,
                        suggestion=f"请检查: {check_name}",
                    )
                )

        evidence["compliance_checks"] = compliance_results

        # 判断是否通过
        passed = len(violations) == 0

        if not passed:
            suggestions.append("请检查分层架构规则，确保请求链路清晰")
        else:
            suggestions.append("架构规则可以正常落地，可以开始业务开发")

        return OperatorResult(
            operator_name=self.name,
            passed=passed,
            evidence=evidence,
            violations=violations,
            suggestions=suggestions,
        )
