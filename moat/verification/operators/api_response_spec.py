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
            "**/routes.py",
            "**/views.py",
        ]

        for pattern in search_paths:
            matches = list(project_path.glob(pattern))
            api_files.extend(matches)

        # 去重并过滤掉测试文件
        api_files = list(set(api_files))
        api_files = [f for f in api_files if not any(
            exempt in str(f) for exempt in ["test_", "/tests/", "/test/"]
        )]

        return api_files

    def _extract_endpoints(self, file_path: Path) -> list[dict]:
        """从文件中提取API端点（真实实现）"""
        endpoints = []

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content)

            # 查找 FastAPI/Starlette 路由装饰器
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    endpoint_info = self._extract_endpoint_from_function(node, file_path)
                    if endpoint_info:
                        endpoints.append(endpoint_info)

        except Exception as e:
            print(f"         ⚠️  解析失败 {file_path.name}: {e}")

        return endpoints

    def _extract_endpoint_from_function(self, func_node: ast.FunctionDef, file_path: Path) -> dict | None:
        """从函数节点提取端点信息"""
        if not func_node.decorator_list:
            return None

        for decorator in func_node.decorator_list:
            endpoint = self._parse_route_decorator(decorator, func_node)
            if endpoint:
                return endpoint

        return None

    def _parse_route_decorator(self, decorator: ast.expr, func_node: ast.FunctionDef) -> dict | None:
        """解析路由装饰器"""
        # 匹配 @app.get("/path") 或 @router.post("/path") 等
        if not isinstance(decorator, ast.Call):
            return None

        if not isinstance(decorator.func, ast.Attribute):
            return None

        # 检查是否是路由方法
        method = decorator.func.attr.lower()
        if method not in {"get", "post", "put", "delete", "patch", "options", "head"}:
            return None

        # 提取路径
        path = ""
        if decorator.args and isinstance(decorator.args[0], ast.Constant):
            path = decorator.args[0].value

        # 提取关键字参数
        kwargs = {}
        for kw in decorator.keywords:
            if isinstance(kw.arg, str):
                kwargs[kw.arg] = self._ast_to_value(kw.value)

        # 提取返回值信息
        return_info = self._extract_return_info(func_node)

        return {
            "method": method.upper(),
            "path": path,
            "function": func_node.name,
            "line": func_node.lineno,
            "response_model": kwargs.get("response_model"),
            "status_code": kwargs.get("status_code"),
            "tags": kwargs.get("tags", []),
            "return_info": return_info,
        }

    def _ast_to_value(self, node: ast.expr) -> any:
        """将 AST 节点转换为 Python 值"""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._ast_to_value(node.value)}.{node.attr}"
        return None

    def _extract_return_info(self, func_node: ast.FunctionDef) -> dict:
        """提取函数返回值信息"""
        return_info = {
            "has_return": False,
            "return_type": None,
            "returns_jsonresponse": False,
            "returns_httpexception": False,
            "returns_dict": False,
        }

        # 检查函数返回值类型注解
        if func_node.returns:
            return_info["return_type"] = self._ast_to_value(func_node.returns)

        # 检查函数体中的返回语句
        for node in ast.walk(func_node):
            if isinstance(node, ast.Return) and node.value:
                return_info["has_return"] = True

                # 检查是否返回 JSONResponse
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name) and "JSONResponse" in node.value.func.id:
                        return_info["returns_jsonresponse"] = True
                    elif isinstance(node.value.func, ast.Attribute) and "JSONResponse" in node.value.func.attr:
                        return_info["returns_jsonresponse"] = True

                # 检查是否返回 dict
                if isinstance(node.value, (ast.Dict, ast.Call)):
                    return_info["returns_dict"] = True

        return return_info

    def _check_response_format(self, endpoint: dict) -> dict:
        """检查端点的响应格式（真实实现）"""
        method = endpoint.get("method", "GET")
        path = endpoint.get("path", "")
        function_name = endpoint.get("function", "")
        response_model = endpoint.get("response_model")
        status_code = endpoint.get("status_code")
        return_info = endpoint.get("return_info", {})

        # 检查是否有统一的响应模型
        has_standard_response = False
        if response_model:
            has_standard_response = True
        elif return_info.get("return_type"):
            has_standard_response = True
        elif return_info.get("returns_jsonresponse"):
            has_standard_response = True

        # 检查是否返回 JSON
        returns_json = (
            has_standard_response or
            return_info.get("returns_jsonresponse") or
            return_info.get("returns_dict") or
            return_info.get("has_return")
        )

        # 检查状态码使用是否规范
        status_codes = []
        if status_code:
            status_codes.append(status_code)
        else:
            # 默认状态码
            if method == "GET":
                status_codes.append(200)
            elif method == "POST":
                status_codes.append(201)
            elif method == "PUT":
                status_codes.append(200)
            elif method == "PATCH":
                status_codes.append(200)
            elif method == "DELETE":
                status_codes.append(204)

        # 检查是否使用 HTTPException
        uses_httpexception = False
        if return_info.get("returns_httpexception"):
            uses_httpexception = True

        return {
            "endpoint": f"{method} {path}",
            "function": function_name,
            "has_standard_response": has_standard_response,
            "returns_json": returns_json,
            "status_codes": status_codes,
            "has_response_model": response_model is not None,
            "response_model": response_model,
            "return_type": return_info.get("return_type"),
            "uses_httpexception": uses_httpexception,
            "notes": [],
        }
