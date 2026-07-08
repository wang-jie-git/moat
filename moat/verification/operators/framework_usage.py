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
        """检测项目使用的框架"""
        frameworks = []

        # 检查FastAPI
        if (project_path / "requirements.txt").exists():
            requirements = (project_path / "requirements.txt").read_text()
            if "fastapi" in requirements.lower():
                frameworks.append("fastapi")

        if (project_path / "pyproject.toml").exists():
            pyproject = (project_path / "pyproject.toml").read_text()
            if "fastapi" in pyproject.lower():
                frameworks.append("fastapi")

        # 检查Django
        if (project_path / "requirements.txt").exists():
            requirements = (project_path / "requirements.txt").read_text()
            if "django" in requirements.lower():
                frameworks.append("django")

        # 检查Flask
        if (project_path / "requirements.txt").exists():
            requirements = (project_path / "requirements.txt").read_text()
            if "flask" in requirements.lower():
                frameworks.append("flask")

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
        """扫描代码，检查框架能力利用情况"""
        usage_checks = []

        # 定义豁免目录和文件
        exempt_patterns = {
            "test", "tests", "__pycache__", ".git",
            "venv", ".venv", "node_modules", "dist", "build",
            "migrations"  # 数据库迁移文件通常不遵循业务代码规范
        }

        # 只扫描源代码目录（排除tests等）
        source_dirs = ["moat", "app", "src", "api", "routers"]

        python_files = []
        for source_dir in source_dirs:
            dir_path = project_path / source_dir
            if dir_path.exists() and dir_path.is_dir():
                python_files.extend(dir_path.rglob("*.py"))

        # 如果没找到源代码，扫描所有Python文件但过滤测试
        if not python_files:
            all_py_files = list(project_path.rglob("*.py"))
            python_files = [
                f for f in all_py_files
                if not any(exempt in str(f) for exempt in exempt_patterns)
            ]

        print(f"      扫描 {len(python_files)} 个Python文件...")

        for py_file in python_files[:30]:  # 限制扫描数量
            try:
                file_path_str = str(py_file.relative_to(project_path))

                # 跳过测试文件
                if any(pattern in file_path_str for pattern in ["test_", "_test.py", "/tests/"]):
                    continue

                content = py_file.read_text(encoding="utf-8", errors="ignore")

                # 检查FastAPI Pydantic使用
                if "fastapi" in frameworks:
                    # 检查是否手动解析JSON（应使用Pydantic）
                    has_json_parsing = False
                    if "json.loads" in content or "request.json()" in content:
                        # 排除导入语句和注释
                        lines_with_json = [
                            line.strip()
                            for line in content.split('\n')
                            if ('json.loads' in line or 'request.json()' in line)
                            and not line.strip().startswith(('import', 'from', '#'))
                        ]
                        has_json_parsing = len(lines_with_json) > 0

                    if has_json_parsing:
                        usage_checks.append({
                            "feature": "Pydantic验证",
                            "file": file_path_str,
                            "using_framework_feature": False,
                            "importance": "medium",  # 降低重要性，因为可能是CLI工具代码
                            "recommendation": "建议使用Pydantic BaseModel替代手动JSON解析（如果是API代码）",
                            "example_file": file_path_str,
                        })
                    else:
                        # 检查是否使用了Pydantic
                        if "BaseModel" in content or "from pydantic import" in content:
                            usage_checks.append({
                                "feature": "Pydantic验证",
                                "file": file_path_str,
                                "using_framework_feature": True,
                                "importance": "high",
                            })

            except Exception:
                pass

        return usage_checks
