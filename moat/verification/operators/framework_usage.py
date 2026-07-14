"""
算子4：框架利用验收

目标：验证是否充分利用框架能力

检查项：
- [ ] 参数校验是否使用框架推荐机制（如Pydantic）
- [ ] 错误处理是否使用框架机制
- [ ] 认证授权是否使用框架中间件
- [ ] 日志是否使用框架内置机制
"""

from pathlib import Path
from typing import TYPE_CHECKING

from ..types import (
    OperatorResult,
    Severity,
    VerificationContext,
    Violation,
    iter_python_files,
)

if TYPE_CHECKING:
    pass


class FrameworkUsageOperator:
    """
    算子4：框架利用验收

    验证是否充分利用框架能力
    """

    name = "framework_usage"
    description = "验证是否充分利用框架能力"

    def verify(self, context: VerificationContext) -> OperatorResult:
        """执行框架利用验收"""
        print(f"   🔍 检查框架能力利用...")

        violations = []
        evidence = {}
        suggestions = []

        project_path = context.project_path

        # 1. 检测项目类型和框架
        detected_frameworks = self._detect_frameworks(project_path)
        evidence["detected_frameworks"] = detected_frameworks

        # 2. 定义框架能力清单
        framework_capabilities = self._get_framework_capabilities(detected_frameworks)
        evidence["framework_capabilities"] = framework_capabilities

        # 3. 扫描代码，检查框架能力利用情况
        usage_checks = self._scan_framework_usage(project_path, detected_frameworks)
        evidence["usage_checks"] = usage_checks

        # 4. 生成违规和建议
        for check in usage_checks:
            if not check["using_framework_feature"] and check["importance"] == "high":
                violations.append(
                    Violation(
                        rule="framework_usage",
                        message=f"未使用框架推荐机制: {check['feature']}",
                        severity=Severity.WARNING,
                        file_path=check.get("example_file"),
                        suggestion=check.get("recommendation"),
                    )
                )

        suggestions.append(f"检测到 {len(detected_frameworks)} 个框架")

        if not violations:
            suggestions.append("框架能力利用良好")
        else:
            suggestions.append(f"发现 {len(violations)} 处未充分利用框架能力的场景")

        passed = len([v for v in violations if v.severity == Severity.ERROR]) == 0

        return OperatorResult(
            operator_name=self.name,
            passed=passed,
            evidence=evidence,
            violations=violations,
            suggestions=suggestions,
        )

    def _detect_frameworks(self, project_path: Path) -> list[str]:
        """检测项目使用的框架

        策略：
        1. 扫描源码中 import 语句（最准确）
        2. 回退检查依赖声明文件（仅 main dependencies）
        """
        # 策略1：扫描源码 import 语句
        frameworks_from_imports = set()
        py_files = list(iter_python_files(project_path))
        for py_file in py_files[:200]:  # 限制扫描数量
            try:
                # 只检查前 50 行（import 通常在文件顶部）
                lines = py_file.read_text(encoding="utf-8", errors="ignore").split("\n")[:50]
                for line in lines:
                    line = line.strip()
                    if line.startswith("import ") or line.startswith("from "):
                        for fw_keyword in ["fastapi", "django", "flask"]:
                            if fw_keyword in line:
                                frameworks_from_imports.add(fw_keyword)
            except Exception:
                pass

        # 策略2：检查依赖声明文件（requirements.txt + pyproject.toml main deps）
        frameworks_from_deps = set()

        # 检查 requirements.txt
        req_file = project_path / "requirements.txt"
        if req_file.exists():
            try:
                req_text = req_file.read_text(encoding="utf-8").lower()
                for fw, kw in [("fastapi", "fastapi"), ("django", "django"), ("flask", "flask")]:
                    if kw in req_text:
                        frameworks_from_deps.add(fw)
            except Exception:
                pass

        # 检查 pyproject.toml (仅 main dependencies)
        if project_path / "pyproject.toml":
            try:
                # 使用 toml 解析（如果有），否则简单 grep
                try:
                    import tomllib  # Python 3.11+
                    with open(project_path / "pyproject.toml", "rb") as f:
                        data = tomllib.load(f)
                    deps = data.get("project", {}).get("dependencies", [])
                    dep_text = " ".join(deps).lower()
                except (ImportError, Exception):
                    # fallback: 只检查 [project] 下的 dependencies，跳过 optional-dependencies
                    content = (project_path / "pyproject.toml").read_text(encoding="utf-8")
                    # 提取 [project] 到下一个 [ 之间的内容
                    in_project = False
                    dep_section = []
                    for line in content.split("\n"):
                        stripped = line.strip()
                        if stripped.startswith("[project]"):
                            in_project = True
                            continue
                        if in_project:
                            if stripped.startswith("["):
                                break
                            dep_section.append(line)
                    dep_text = " ".join(dep_section).lower()

                for fw, kw in [("fastapi", "fastapi"), ("django", "django"), ("flask", "flask")]:
                    if kw in dep_text:
                        frameworks_from_deps.add(fw)
            except Exception:
                pass

        # 合并：优先使用 import 检测结果，回退使用依赖声明
        frameworks = list(frameworks_from_imports) if frameworks_from_imports else list(frameworks_from_deps)
        return frameworks

    def _get_framework_capabilities(self, frameworks: list[str]) -> dict:
        """获取框架能力清单"""
        capabilities = {}

        for framework in frameworks:
            if framework == "fastapi":
                capabilities["fastapi"] = {
                    "validation": {
                        "recommended": "Pydantic模型 (BaseModel)",
                        "custom": "手动解析JSON (request.json())",
                        "why": "自动类型检查、文档生成、错误处理",
                    },
                    "error_handling": {
                        "recommended": "Exception Handlers (@app.exception_handler)",
                        "custom": "try-except块",
                        "why": "统一错误处理、减少样板代码",
                    },
                    "auth": {
                        "recommended": "Dependencies (Depends)",
                        "custom": "手动验证token",
                        "why": "依赖注入、可测试性、可复用性",
                    },
                    "logging": {
                        "recommended": "Built-in logging",
                        "custom": "自定义logger",
                        "why": "集成性、性能、配置简单",
                    },
                    "routing": {
                        "recommended": "APIRouter分组",
                        "custom": "所有路由在一个文件",
                        "why": "模块化、可维护性",
                    },
                }

            elif framework == "django":
                capabilities["django"] = {
                    "validation": {
                        "recommended": "Django Forms / Serializers",
                        "custom": "手动验证",
                        "why": "自动验证、错误消息、CSRF保护",
                    },
                    "orm": {
                        "recommended": "Django ORM (Models)",
                        "custom": "原生SQL",
                        "why": "数据库无关、安全、便捷",
                    },
                }

            elif framework == "flask":
                capabilities["flask"] = {
                    "validation": {
                        "recommended": "Flask-Marshmallow / Pydantic",
                        "custom": "手动验证",
                        "why": "序列化、验证、文档",
                    },
                }

        return capabilities

    def _scan_framework_usage(self, project_path: Path, frameworks: list[str]) -> list[dict]:
        """扫描代码，检查框架能力利用情况（真实实现）"""
        usage_checks = []

        # 定义豁免目录和文件
        exempt_patterns = {
            "test", "tests", "__pycache__", ".git",
            "venv", ".venv", "node_modules", "dist", "build",
            "migrations", "alembic"  # 数据库迁移文件通常不遵循业务代码规范
        }

        # 只扫描源代码目录（排除tests等）
        source_dirs = ["moat", "app", "src", "api", "routers", "services", "controllers", "views"]

        python_files = []
        for source_dir in source_dirs:
            dir_path = project_path / source_dir
            if dir_path.exists() and dir_path.is_dir():
                python_files.extend(iter_python_files(dir_path))

        # 如果没找到源代码，扫描所有Python文件但过滤测试
        if not python_files:
            all_py_files = list(iter_python_files(project_path))
            python_files = [
                f for f in all_py_files
                if not any(exempt in str(f) for exempt in exempt_patterns)
            ]

        # 对于每个框架，先找出实际使用该框架的文件
        framework_files: dict[str, list[str]] = {}
        for fw in frameworks:
            framework_files[fw] = []

        for py_file in python_files:
            try:
                file_path_str = str(py_file.relative_to(project_path))

                # 跳过测试文件
                if any(pattern in file_path_str for pattern in ["test_", "_test.py", "/tests/"]):
                    continue

                content = py_file.read_text(encoding="utf-8", errors="ignore")

                # 对每个框架，检查文件是否实际 import 了该框架
                for fw in frameworks:
                    is_relevant = False
                    for fw_keyword in [fw, fw.replace("-", "_")]:
                        if f"import {fw_keyword}" in content or f"from {fw_keyword}" in content:
                            is_relevant = True
                            break
                    if is_relevant:
                        framework_files[fw].append((file_path_str, content))

            except Exception:
                pass

        print(f"      扫描 {len(python_files)} 个Python文件...")
        for fw in frameworks:
            fw_count = len(framework_files[fw])
            print(f"      框架 {fw}: {fw_count} 个相关文件")

        # 对每个框架的相关文件执行特性检查
        for fw in frameworks:
            if fw == "fastapi":
                for file_path_str, content in framework_files["fastapi"]:
                    usage_checks.extend(self._check_fastapi_features(content, file_path_str))

            elif fw == "django":
                for file_path_str, content in framework_files["django"]:
                    usage_checks.extend(self._check_django_features(content, file_path_str))

            elif fw == "flask":
                for file_path_str, content in framework_files["flask"]:
                    usage_checks.extend(self._check_flask_features(content, file_path_str))

        return usage_checks

    def _check_fastapi_features(self, content: str, file_path: str) -> list[dict]:
        """检查 FastAPI 特性使用情况"""
        checks = []

        # 1. Pydantic 验证（已实现）
        has_base_model = "BaseModel" in content or "from pydantic import" in content
        has_manual_json = "json.loads" in content or "request.json()" in content

        if has_manual_json and not has_base_model:
            checks.append({
                "feature": "Pydantic BaseModel",
                "file": file_path,
                "using_framework_feature": False,
                "importance": "high",
                "recommendation": "使用 Pydantic BaseModel 替代手动 JSON 解析",
            })
        elif has_base_model:
            checks.append({
                "feature": "Pydantic BaseModel",
                "file": file_path,
                "using_framework_feature": True,
                "importance": "high",
            })

        # 2. FastAPI 异常处理
        has_exception_handler = "@app.exception_handler" in content or "@app.exception_handler" in content
        has_try_except = "try:" in content and "except" in content

        if has_try_except and not has_exception_handler:
            checks.append({
                "feature": "FastAPI Exception Handler",
                "file": file_path,
                "using_framework_feature": False,
                "importance": "high",
                "recommendation": "使用 @app.exception_handler 统一处理异常，减少样板 try-except 代码",
            })
        elif has_exception_handler:
            checks.append({
                "feature": "FastAPI Exception Handler",
                "file": file_path,
                "using_framework_feature": True,
                "importance": "high",
            })

        # 3. FastAPI 依赖注入 (Depends)
        has_depends = "Depends(" in content or "from fastapi import Depends" in content
        has_auth_logic = any(kw in content for kw in ["token", "auth", "login", "current_user", "get_current_user"])

        if has_auth_logic and not has_depends:
            checks.append({
                "feature": "FastAPI Depends (依赖注入)",
                "file": file_path,
                "using_framework_feature": False,
                "importance": "high",
                "recommendation": "使用 Depends() 实现鉴权依赖，避免在每个路由中重复验证 token",
            })
        elif has_depends:
            checks.append({
                "feature": "FastAPI Depends (依赖注入)",
                "file": file_path,
                "using_framework_feature": True,
                "importance": "high",
            })

        # 4. FastAPI APIRouter 路由分组
        has_apirouter = "APIRouter" in content or "from fastapi import APIRouter" in content
        has_app_route = "@app." in content or "@router." in content

        if has_app_route and not has_apirouter:
            # 统计路由数量
            route_count = content.count("@app.get") + content.count("@app.post") + \
                         content.count("@app.put") + content.count("@app.delete")

            if route_count > 5:
                checks.append({
                    "feature": "FastAPI APIRouter (路由分组)",
                    "file": file_path,
                    "using_framework_feature": False,
                    "importance": "medium",
                    "recommendation": f"文件中有 {route_count} 个路由，建议使用 APIRouter 按模块分组",
                })
        elif has_apirouter:
            checks.append({
                "feature": "FastAPI APIRouter (路由分组)",
                "file": file_path,
                "using_framework_feature": True,
                "importance": "medium",
            })

        # 5. FastAPI BackgroundTasks 后台任务
        has_background_tasks = "BackgroundTasks" in content or "from fastapi import BackgroundTasks"
        has_slow_operation = any(kw in content for kw in ["time.sleep", "asyncio.sleep", "send_email", "process_file"])

        if has_slow_operation and not has_background_tasks:
            checks.append({
                "feature": "FastAPI BackgroundTasks (后台任务)",
                "file": file_path,
                "using_framework_feature": False,
                "importance": "low",
                "recommendation": "检测到可能耗时操作，建议使用 BackgroundTasks 异步处理",
            })
        elif has_background_tasks:
            checks.append({
                "feature": "FastAPI BackgroundTasks (后台任务)",
                "file": file_path,
                "using_framework_feature": True,
                "importance": "low",
            })

        return checks

    def _check_django_features(self, content: str, file_path: str) -> list[dict]:
        """检查 Django 特性使用情况"""
        checks = []

        # 1. Django ORM
        has_orm = ".objects." in content or "Model.objects" in content
        has_raw_sql = "cursor()" in content or "raw(" in content

        if has_raw_sql and has_orm:
            checks.append({
                "feature": "Django ORM",
                "file": file_path,
                "using_framework_feature": False,
                "importance": "medium",
                "recommendation": "检测到原生 SQL，建议优先使用 Django ORM",
            })
        elif has_orm:
            checks.append({
                "feature": "Django ORM",
                "file": file_path,
                "using_framework_feature": True,
                "importance": "high",
            })

        # 2. Django Forms/Serializers
        has_forms = "forms.Form" in content or "forms.ModelForm" in content
        has_serializers = "serializers." in content or "from rest_framework import serializers" in content
        has_manual_validation = "is_valid()" in content and not (has_forms or has_serializers)

        if has_manual_validation:
            checks.append({
                "feature": "Django Forms/Serializers",
                "file": file_path,
                "using_framework_feature": False,
                "importance": "high",
                "recommendation": "使用 Django Forms 或 DRF Serializers 进行数据验证",
            })
        elif has_forms or has_serializers:
            checks.append({
                "feature": "Django Forms/Serializers",
                "file": file_path,
                "using_framework_feature": True,
                "importance": "high",
            })

        # 3. get_object_or_404
        has_get_object = "get_object_or_404" in content or "get_list_or_404" in content
        has_try_except_doesnotexist = "DoesNotExist" in content or "try:" in content

        if has_try_except_doesnotexist and not has_get_object:
            checks.append({
                "feature": "Django get_object_or_404",
                "file": file_path,
                "using_framework_feature": False,
                "importance": "medium",
                "recommendation": "使用 get_object_or_404() 替代手动 try-except 捕获 DoesNotExist",
            })
        elif has_get_object:
            checks.append({
                "feature": "Django get_object_or_404",
                "file": file_path,
                "using_framework_feature": True,
                "importance": "medium",
            })

        return checks

    def _check_flask_features(self, content: str, file_path: str) -> list[dict]:
        """检查 Flask 特性使用情况"""
        checks = []

        # 1. Flask-Marshmallow / Pydantic
        has_marshmallow = "marshmallow" in content or "flask_marshmallow" in content
        has_pydantic = "BaseModel" in content
        has_manual_validation = "request." in content and ("json" in content or "form" in content)

        if has_manual_validation and not (has_marshmallow or has_pydantic):
            checks.append({
                "feature": "Flask-Marshmallow / Pydantic",
                "file": file_path,
                "using_framework_feature": False,
                "importance": "high",
                "recommendation": "使用 Flask-Marshmallow 或 Pydantic 进行请求验证",
            })
        elif has_marshmallow or has_pydantic:
            checks.append({
                "feature": "Flask-Marshmallow / Pydantic",
                "file": file_path,
                "using_framework_feature": True,
                "importance": "high",
            })

        # 2. Flask 错误处理
        has_errorhandler = "@app.errorhandler" in content
        has_try_except = "try:" in content and "except" in content

        if has_try_except and not has_errorhandler:
            checks.append({
                "feature": "Flask ErrorHandler",
                "file": file_path,
                "using_framework_feature": False,
                "importance": "medium",
                "recommendation": "使用 @app.errorhandler 统一处理错误",
            })
        elif has_errorhandler:
            checks.append({
                "feature": "Flask ErrorHandler",
                "file": file_path,
                "using_framework_feature": True,
                "importance": "medium",
            })

        return checks
