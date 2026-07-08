"""
算子6：架构健康度评分

目标：量化架构健康度

评分维度（总分100）：
- 目录责任清晰度：20分
- 分层架构遵守度：20分
- 接口响应一致性：20分
- 框架利用合理性：20分
- 命名规范遵守度：20分
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


class ArchitectureHealthScoreOperator:
    """
    算子6：架构健康度评分

    量化架构健康度（0-100分）
    """

    name = "architecture_health_score"
    description = "量化架构健康度（0-100分）"

    def verify(self, context: VerificationContext) -> OperatorResult:
        """计算架构健康度评分"""
        print(f"   🔍 计算架构健康度...")

        violations = []
        evidence = {}
        suggestions = []

        project_path = context.project_path

        # 1. 目录责任清晰度（20分）
        dir_score = self._check_directory_responsibility(project_path)

        # 2. 分层架构遵守度（20分）
        layer_score = self._check_layer_separation(project_path)

        # 3. 接口响应一致性（20分）
        api_score = self._check_api_consistency(project_path)

        # 4. 框架利用合理性（20分）
        framework_score = self._check_framework_usage(project_path)

        # 5. 命名规范遵守度（20分）
        naming_score = self._check_naming_consistency(project_path)

        # 计算总分
        total_score = dir_score + layer_score + api_score + framework_score + naming_score

        evidence = {
            "directory_responsibility": {"score": dir_score, "max": 20},
            "layer_separation": {"score": layer_score, "max": 20},
            "api_consistency": {"score": api_score, "max": 20},
            "framework_usage": {"score": framework_score, "max": 20},
            "naming_consistency": {"score": naming_score, "max": 20},
            "total_score": round(total_score, 1),
        }

        # 判断是否通过（≥70分即可通过，后续逐步提高）
        passed = total_score >= 70

        # 根据分数给出建议
        if total_score >= 80:
            suggestions.append("✅ 架构健康度优秀，可以继续开发")
        elif total_score >= 70:
            suggestions.append("✅ 架构健康度良好，可以继续开发（建议优化到80+）")
        elif total_score >= 60:
            suggestions.append("⚠️  架构一般，建议优化后再新增功能")
            violations.append(
                Violation(
                    rule="architecture_health",
                    message=f"架构健康度评分偏低: {total_score}/100",
                    severity=Severity.WARNING,
                    suggestion="建议优化后再新增功能",
                )
            )
        else:
            suggestions.append("❌ 架构不健康，禁止新增功能，必须先修复")
            violations.append(
                Violation(
                    rule="architecture_health",
                    message=f"架构健康度评分过低: {total_score}/100",
                    severity=Severity.CRITICAL,
                    suggestion="禁止新增功能，必须先修复架构问题",
                )
            )

        # 添加具体问题点
        if dir_score < 15:
            suggestions.append(f"💡 目录责任清晰度较低({dir_score}/20)，建议明确各目录职责")
        if layer_score < 15:
            suggestions.append(f"💡 分层架构遵守度较低({layer_score}/20)，建议分离各层关注点")
        if framework_score < 15:
            suggestions.append(f"💡 框架利用不足({framework_score}/20)，建议充分利用框架能力")

        return OperatorResult(
            operator_name=self.name,
            passed=passed,
            evidence=evidence,
            violations=violations,
            suggestions=suggestions,
        )

    def _check_directory_responsibility(self, project_path: Path) -> float:
        """检查目录责任清晰度（20分）"""
        score = 0.0

        # 1. 是否有清晰的目录结构（5分）
        directories = self._get_top_directories(project_path)
        if len(directories) >= 3:
            score += 5.0

        # 2. 是否有框架推荐的目录（5分）
        framework_dirs = {"api", "services", "repositories", "models", "schemas", "core"}
        if any(d in directories for d in framework_dirs):
            score += 5.0

        # 3. 目录命名是否清晰（5分）
        unclear_dirs = {"misc", "other", "temp", "test"}
        unclear_count = sum(1 for d in directories if d in unclear_dirs)
        if unclear_count == 0:
            score += 5.0
        elif unclear_count <= 1:
            score += 3.0

        # 4. 是否有测试目录（5分）
        if "tests" in directories or "test" in directories:
            score += 5.0

        return score

    def _check_layer_separation(self, project_path: Path) -> float:
        """检查分层架构遵守度（20分）"""
        # 检测项目类型
        has_api = (project_path / "api").exists() or (project_path / "app").exists()
        has_services = (project_path / "services").exists()
        has_repos = (project_path / "repositories").exists() or (project_path / "repos").exists()

        # CLI工具或库项目
        is_cli_tool = (project_path / "cli.py").exists() or (project_path / "__main__.py").exists()

        if not has_api and not has_services and not has_repos:
            # 没有分层架构目录，可能是CLI工具、库或其他类型项目
            if is_cli_tool:
                # CLI工具项目，给基础分
                return 12.0
            else:
                # 其他项目，也给基础分但略低
                return 10.0

        # Web应用项目，检查分层架构完整性
        score = 0.0
        if has_api:
            score += 5.0
        if has_services:
            score += 5.0
        if has_repos:
            score += 5.0

        # 检查分层是否清晰（通过文件命名）
        if has_api:
            api_files = list((project_path / "api").rglob("*.py"))
            router_count = sum(1 for f in api_files if "router" in f.name.lower())
            if router_count > 0:
                score += 2.5

        if has_services:
            service_files = list((project_path / "services").rglob("*.py"))
            service_count = sum(1 for f in service_files if "service" in f.name.lower())
            if service_count > 0:
                score += 2.5

        return score

    def _check_api_consistency(self, project_path: Path) -> float:
        """检查接口响应一致性（20分）"""
        score = 15.0  # 基础分

        # TODO: 实际扫描API响应格式
        # 当前版本：假设基本一致

        return score

    def _check_framework_usage(self, project_path: Path) -> float:
        """检查框架利用合理性（20分）"""
        score = 10.0  # 基础分

        # 检查是否使用了框架推荐的工具
        if (project_path / "pyproject.toml").exists():
            pyproject = (project_path / "pyproject.toml").read_text()
            if "fastapi" in pyproject.lower():
                score += 5.0
            if "pydantic" in pyproject.lower():
                score += 5.0

        return score

    def _check_naming_consistency(self, project_path: Path) -> float:
        """检查命名规范遵守度（20分）"""
        score = 15.0  # 基础分

        # TODO: 实际扫描命名风格
        # 当前版本：假设基本一致

        return score

    def _get_top_directories(self, project_path: Path) -> set[str]:
        """获取顶层目录名集合"""
        directories = set()

        try:
            for item in sorted(project_path.iterdir()):
                if item.is_dir() and not item.name.startswith("."):
                    if item.name not in {"node_modules", "__pycache__", ".git", ".venv", "venv"}:
                        directories.add(item.name)
        except Exception:
            pass

        return directories
