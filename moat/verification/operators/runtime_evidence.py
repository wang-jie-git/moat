"""
算子5：运行证据包生成

目标：固化项目运行方式

输出：
- 依赖安装命令
- 启动命令
- 服务端口
- 健康检查结果
- 数据库连接验证
- 日志示例
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


class RuntimeEvidenceOperator:
    """
    算子5：运行证据包生成

    固化项目运行方式
    """

    name = "runtime_evidence"
    description = "生成运行证据包（启动、配置、数据库、日志）"

    def verify(self, context: VerificationContext) -> OperatorResult:
        """生成运行证据包"""
        print(f"   🔍 生成运行证据包...")

        violations = []
        evidence = {}
        suggestions = []

        project_path = context.project_path

        # 1. 检查依赖文件
        requirements_files = []
        for pattern in ["requirements.txt", "pyproject.toml", "Pipfile", "poetry.lock"]:
            req_file = project_path / pattern
            if req_file.exists():
                requirements_files.append({
                    "file": pattern,
                    "exists": True,
                })

        evidence["requirements_files"] = requirements_files

        # 2. 检查启动文件
        entry_points = []
        for pattern in ["main.py", "app.py", "server.py", "manage.py"]:
            entry_file = project_path / pattern
            if entry_file.exists():
                entry_points.append({
                    "file": pattern,
                    "exists": True,
                })

        evidence["entry_points"] = entry_points

        # 3. 检查配置文件
        config_files = []
        config_patterns = [
            ".env", ".env.example", ".env.template",
            "config/*.yaml", "config/*.yml", "config/*.json",
            "settings.py", "settings/*.py"
        ]

        for pattern in config_patterns:
            matches = list(project_path.glob(pattern))
            if matches:
                for match in matches:
                    config_files.append({
                        "file": str(match.relative_to(project_path)),
                        "exists": True,
                    })

        evidence["config_files"] = config_files

        # 4. 检查健康检查端点（尝试多种检测方式）
        has_health_check = False
        health_check_locations = []

        # 方式1：检查代码中是否有/health路径
        py_files = list(iter_python_files(project_path))
        for py_file in py_files[:20]:  # 限制检查数量
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                if '/health' in content or '/healthz' in content or '/ping' in content:
                    has_health_check = True
                    health_check_locations.append(str(py_file.relative_to(project_path)))
            except Exception:
                pass

        evidence["has_health_check"] = has_health_check
        evidence["health_check_locations"] = health_check_locations

        if not has_health_check:
            violations.append(
                Violation(
                    rule="health_check",
                    message="未检测到健康检查端点",
                    severity=Severity.INFO,  # 降低严重程度
                    suggestion="建议添加 /health 或 /healthz 端点用于服务健康检查",
                )
            )

        # 5. 检查数据库迁移工具
        migration_tools = []
        if (project_path / "alembic.ini").exists():
            migration_tools.append({
                "tool": "alembic",
                "config": "alembic.ini",
            })
        if (project_path / "prisma").exists():
            migration_tools.append({
                "tool": "prisma",
                "config": "prisma/schema.prisma",
            })
        if (project_path / "migrations").exists():
            migration_tools.append({
                "tool": "migrations",
                "config": "migrations/",
            })

        evidence["migration_tools"] = migration_tools

        # 6. 检查Docker配置
        docker_configs = []
        if (project_path / "Dockerfile").exists():
            docker_configs.append("Dockerfile")
        if (project_path / "docker-compose.yml").exists():
            docker_configs.append("docker-compose.yml")
        if (project_path / "docker-compose.yaml").exists():
            docker_configs.append("docker-compose.yaml")

        evidence["docker_configs"] = docker_configs

        # 7. 生成运行证据摘要
        evidence_summary = {
            "dependencies": len(requirements_files) > 0,
            "entry_point": len(entry_points) > 0,
            "config": len(config_files) > 0,
            "health_check": has_health_check,
            "database_migration": len(migration_tools) > 0,
            "docker": len(docker_configs) > 0,
        }

        evidence["summary"] = evidence_summary

        # 生成建议
        if not requirements_files:
            suggestions.append("未找到依赖文件，建议创建 requirements.txt 或 pyproject.toml")

        if not entry_points:
            suggestions.append("未找到启动文件，建议创建 main.py 或 app.py")

        if not config_files:
            suggestions.append("未找到配置文件，建议添加 .env 或 config/ 目录")

        if not has_health_check:
            suggestions.append("建议添加健康检查端点用于容器编排和监控")

        if len(migration_tools) == 0:
            suggestions.append("建议使用数据库迁移工具（如Alembic）")

        suggestions.append("运行证据包已收集")
        suggestions.append("注意：此版本仅收集证据，未执行实际验证")
        suggestions.append("下一版本将实际执行：依赖安装、启动服务、访问健康检查")

        passed = True  # 证据收集本身不会失败

        return OperatorResult(
            operator_name=self.name,
            passed=passed,
            evidence=evidence,
            violations=violations,
            suggestions=suggestions,
        )
