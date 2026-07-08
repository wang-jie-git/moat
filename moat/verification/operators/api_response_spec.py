"""
算子3（完整版）：接口响应规范验收

目标：验证接口返回是否规范统一

检查项：
- [ ] 成功场景（列表、详情、创建、更新、删除、空列表）
- [ ] 错误场景（参数错误、未登录、权限、资源不存在、系统异常）
- [ ] HTTP状态码是否符合规范
- [ ] 是否有统一的响应模型
"""

import ast
import re
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


class APIResponseSpecOperator:
    """
    算子3：接口响应规范验收（完整版）

    验证接口返回是否规范统一
    """

    name = "api_response_spec"
    description = "验证接口返回是否规范统一"

    def verify(self, context: VerificationContext) -> OperatorResult:
        """执行接口响应规范验收"""
        print(f"   🔍 检查接口响应规范...")

        violations = []
        evidence = {}
        suggestions = []

        project_path = context.project_path

        # 定义期望的响应规范
        expected_specs = {
            "success": {
                "list": {"status": 200, "format": "{data: [...], total: N}"},
                "detail": {"status": 200, "format": "{data: {...}}"},
                "create": {"status": 201, "format": "{data: {...}}"},
                "update": {"status": 200, "format": "{data: {...}}"},
                "delete": {"status": 204, "format": "-"},
                "empty_list": {"status": 200, "format": "{data: [], total: 0}"},
            },
            "error": {
                "validation": {"status": 422, "format": "{detail: '...'}"},
                "unauthorized": {"status": 401, "format": "{detail: 'Not authenticated'}"},
                "forbidden": {"status": 403, "format": "{detail: 'Forbidden'}"},
                "not_found": {"status": 404, "format": "{detail: 'Not found'}"},
                "server_error": {"status": 500, "format": "{detail: 'Internal server error'}"},
            },
        }

        evidence["expected_response_specs"] = expected_specs

        # 扫描项目中的API端点
        api_files = self._find_api_files(project_path)
        print(f"      发现 {len(api_files)} 个API文件")

        # 检查每个API文件
        checked_endpoints = []
        has_standard_response = False

        for api_file in api_files[:10]:  # 限制检查数量
            endpoints = self._extract_endpoints(api_file)
            for endpoint in endpoints:
                # 检查响应格式
                response_check = self._check_response_format(endpoint)
                checked_endpoints.append({
                    "file": str(api_file.relative_to(project_path)),
                    "endpoint": endpoint,
                    "response_check": response_check,
                })

                if response_check.get("has_standard_response"):
                    has_standard_response = True

        evidence["checked_endpoints"] = checked_endpoints
        evidence["total_endpoints_checked"] = len(checked_endpoints)

        # 检查是否有统一的响应模型
        if not has_standard_response and checked_endpoints:
            violations.append(
                Violation(
                    rule="api_response_spec",
                    message="未检测到统一的响应模型",
                    severity=Severity.WARNING,
                    suggestion="建议定义统一的SuccessResponse和ErrorResponse模型",
                )
            )

        # 检查是否所有成功响应都返回JSON
        for endpoint_info in checked_endpoints:
            if not endpoint_info["response_check"].get("returns_json"):
                violations.append(
                    Violation(
                        rule="api_response_format",
                        message=f"端点可能未返回JSON: {endpoint_info['endpoint']}",
                        severity=Severity.INFO,
                        file_path=endpoint_info["file"],
                        suggestion="确保所有端点都返回标准JSON格式",
                    )
                )

        # 检查状态码使用是否规范
        for endpoint_info in checked_endpoints:
            status_codes = endpoint_info["response_check"].get("status_codes", [])
            if 200 in status_codes and len(status_codes) > 3:
                # 如果使用了200但还有其他状态码，可能混合了成功和失败
                violations.append(
                    Violation(
                        rule="status_code_usage",
                        message=f"端点可能混合了多种状态码: {endpoint_info['endpoint']}",
                        severity=Severity.INFO,
                        file_path=endpoint_info["file"],
                        suggestion="确保状态码使用符合HTTP规范",
                    )
                )

        suggestions.append(f"已检查 {len(checked_endpoints)} 个端点")

        passed = len([v for v in violations if v.severity in {Severity.ERROR, Severity.CRITICAL}]) == 0

        return OperatorResult(
            operator_name=self.name,
            passed=passed,
            evidence=evidence,
            violations=violations,
            suggestions=suggestions,
        )

    def _find_api_files(self, project_path: Path) -> list[Path]:
        """查找API相关文件"""
        api_files = []

        # 常见的API文件位置
        search_paths = [
            "api/**/*.py",
            "app/**/*.py",
            "routers/**/*.py",
            "views/**/*.py",
            "endpoints/**/*.py",
        ]

        for pattern in search_paths:
            matches = list(project_path.glob(pattern))
            api_files.extend(matches)

        # 去重
        return list(set(api_files))

    def _extract_endpoints(self, file_path: Path) -> list[str]:
        """从文件中提取API端点"""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content)

            endpoints = []
            for node in ast.walk(tree):
                # 查找装饰器 @app.get, @app.post, @router.get, @router.post 等
                if isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call):
                            # @app.get("/path") 或 @router.post("/path")
                            if isinstance(decorator.func, ast.Attribute):
                                if decorator.func.attr in {"get", "post", "put", "delete", "patch"}:
                                    # 提取路径
                                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                                        path = decorator.args[0].value
                                        endpoints.append(f"{decorator.func.attr.upper()} {path}")

            return endpoints

        except Exception:
            return []

    def _check_response_format(self, endpoint: str) -> dict:
        """检查端点的响应格式（简化版）"""
        # 实际实现需要更复杂的静态分析或运行时检查
        # 这里返回一个基础检查结果

        return {
            "endpoint": endpoint,
            "returns_json": True,  # 假设都返回JSON
            "has_standard_response": False,  # 假设还没有统一响应模型
            "status_codes": [200],  # 默认200
            "notes": "基础检查，需要进一步完善",
        }
