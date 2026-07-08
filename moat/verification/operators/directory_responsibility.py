"""
算子1：目录责任验收

目标：验证每个目录的责任是否清晰

检查项：
- [ ] 每个目录是否有且仅有一个主要职责
- [ ] 是否明确说明"应该放什么"和"禁止放什么"
- [ ] 是否区分"框架推荐"vs"项目自定义"
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


class DirectoryResponsibilityOperator:
    """
    算子1：目录责任验收

    验证每个目录的责任是否清晰
    """

    name = "directory_responsibility"
    description = "验证每个目录的责任是否清晰"

    def verify(self, context: VerificationContext) -> OperatorResult:
        """
        执行目录责任验收

        策略：
        1. 扫描项目目录结构
        2. 识别常见框架目录（api/, services/, repositories/等）
        3. 检查每个目录的文件是否符合预期职责
        4. 生成目录责任表
        """
        import json
        import os

        project_path = context.project_path
        violations = []
        evidence = {}
        suggestions = []

        print(f"   🔍 扫描目录结构...")

        # 1. 扫描所有一级目录
        directories = self._scan_directories(project_path)
        print(f"      发现 {len(directories)} 个一级目录")

        # 2. 识别框架目录
        framework_dirs = self._identify_framework_directories(directories)
        print(f"      识别 {len(framework_dirs)} 个框架目录")

        # 3. 检查每个目录的职责
        dir_responsibilities = []
        for dir_name in sorted(directories.keys()):
            dir_info = directories[dir_name]

            # 分析目录职责
            responsibility = self._analyze_directory_responsibility(
                dir_name, dir_info
            )

            # 检查是否有职责冲突
            conflicts = self._check_responsibility_conflicts(
                dir_name, responsibility, dir_info
            )

            dir_responsibilities.append(
                {
                    "directory": dir_name,
                    "file_count": dir_info["file_count"],
                    "responsibility": responsibility,
                    "conflicts": conflicts,
                }
            )

            # 如果有冲突，添加违规
            if conflicts:
                for conflict in conflicts:
                    violations.append(
                        Violation(
                            rule="directory_responsibility",
                            message=conflict["message"],
                            severity=Severity.WARNING,
                            file_path=conflict.get("file"),
                            line=conflict.get("line"),
                            suggestion=conflict.get("suggestion"),
                        )
                    )

        # 4. 生成证据
        evidence = {
            "total_directories": len(directories),
            "framework_directories": len(framework_dirs),
            "directory_responsibilities": dir_responsibilities,
        }

        # 5. 检查是否所有目录都有清晰职责
        unclear_dirs = [
            d for d in dir_responsibilities if d["responsibility"] == "未明确"
        ]

        if unclear_dirs:
            suggestions.append(
                f"为以下目录定义清晰的责任: "
                f"{', '.join(d['directory'] for d in unclear_dirs)}"
            )

        # 6. 判断是否通过
        # 条件：没有CRITICAL违规，且明确职责的目录占比 > 60%
        critical_violations = [v for v in violations if v.severity == Severity.CRITICAL]
        clear_responsibility_count = len(
            [d for d in dir_responsibilities if d["responsibility"] not in {None, "未明确"}]
        )
        clarity_ratio = clear_responsibility_count / len(dir_responsibilities) if dir_responsibilities else 0

        passed = (
            len(critical_violations) == 0
            and clarity_ratio >= 0.6
        )

        # 生成目录责任表（Markdown格式）
        markdown_table = self._generate_directory_responsibility_table(
            dir_responsibilities
        )
        evidence["directory_responsibility_table"] = markdown_table

        return OperatorResult(
            operator_name=self.name,
            passed=passed,
            evidence=evidence,
            violations=violations,
            suggestions=suggestions,
        )

    def _scan_directories(self, project_path: Path) -> dict[str, dict]:
        """扫描一级目录"""
        directories = {}

        try:
            for item in sorted(project_path.iterdir()):
                if not item.is_dir():
                    continue

                # 跳过隐藏目录和常见忽略目录
                if item.name.startswith("."):
                    continue
                if item.name in {
                    "node_modules",
                    "__pycache__",
                    ".git",
                    ".venv",
                    "venv",
                    "dist",
                    "build",
                }:
                    continue

                # 统计文件数（只统计一级）
                files = [
                    f for f in item.iterdir() if f.is_file() and not f.name.startswith(".")
                ]

                directories[item.name] = {
                    "path": str(item),
                    "file_count": len(files),
                    "sample_files": [f.name for f in files[:5]],
                }

        except PermissionError:
            pass

        return directories

    def _identify_framework_directories(self, directories: dict) -> list[str]:
        """识别框架推荐目录"""
        framework_patterns = {
            # FastAPI / Web框架
            "api": "FastAPI/Web框架推荐",
            "app": "FastAPI/Web框架推荐",
            "routers": "FastAPI推荐",
            # 分层架构
            "services": "分层架构推荐",
            "service": "分层架构推荐",
            "repositories": "分层架构推荐",
            "repository": "分层架构推荐",
            "repos": "分层架构推荐",
            # 数据模型
            "models": "ORM推荐",
            "schemas": "Pydantic推荐",
            # 核心模块
            "core": "核心模块",
            "config": "配置管理",
            "utils": "工具函数",
            "helpers": "工具函数",
            # 测试
            "tests": "测试目录",
            "test": "测试目录",
            # Moat项目核心目录（特殊处理）
            "moat": "Moat框架核心",
            "scripts": "项目脚本",
            "docs": "项目文档",
        }

        framework_dirs = []
        for dir_name in directories.keys():
            if dir_name in framework_patterns:
                framework_dirs.append(dir_name)

        return framework_dirs

    def _analyze_directory_responsibility(self, dir_name: str, dir_info: dict) -> str:
        """分析目录职责"""
        sample_files = " ".join(dir_info.get("sample_files", [])).lower()

        # 基于常见模式判断职责
        if dir_name in {"api", "app", "routers"}:
            if any(f.endswith(".py") for f in dir_info.get("sample_files", [])):
                return "路由和API端点"
            return "应用入口"

        if dir_name in {"services", "service"}:
            return "业务逻辑层"

        if dir_name in {"repositories", "repository", "repos"}:
            return "数据访问层"

        if dir_name == "models":
            return "数据模型定义"

        if dir_name == "schemas":
            return "数据验证模型（Pydantic）"

        if dir_name == "core":
            return "核心基础模块"

        if dir_name == "config":
            return "配置管理"

        if dir_name in {"utils", "helpers"}:
            return "工具函数"

        if dir_name in {"tests", "test"}:
            return "测试代码"

        if dir_name == "migrations":
            return "数据库迁移"

        if dir_name == "static" or dir_name == "assets":
            return "静态资源"

        if dir_name == "docs" or dir_name == "documentation":
            return "文档"

        if dir_name == "moat":
            # 特殊处理：moat目录是Moat框架本身的核心代码
            return "Moat框架核心模块"

        if dir_name == "scripts":
            return "项目脚本"

        return "未明确"

    def _check_responsibility_conflicts(
        self, dir_name: str, responsibility: str, dir_info: dict
    ) -> list[dict]:
        """检查职责冲突"""
        conflicts = []
        sample_files = dir_info.get("sample_files", [])

        # 检查路由目录是否混入业务逻辑
        if dir_name in {"api", "routers"}:
            for file in sample_files:
                if file.endswith(".py"):
                    # 检查文件中是否有业务逻辑关键词
                    file_path = Path(dir_info["path"]) / file
                    try:
                        content = file_path.read_text(errors="ignore")
                        if any(
                            keyword in content
                            for keyword in ["def calculate_", "def process_", "def handle_"]
                        ):
                            conflicts.append(
                                {
                                    "message": f"路由目录 '{dir_name}' 可能混入了业务逻辑",
                                    "file": str(file_path),
                                    "suggestion": "将业务逻辑移到 services/ 目录",
                                }
                            )
                    except Exception:
                        pass

        # 检查业务层是否混入HTTP处理
        if dir_name in {"services", "service"}:
            for file in sample_files:
                if file.endswith(".py"):
                    file_path = Path(dir_info["path"]) / file
                    try:
                        content = file_path.read_text(errors="ignore")
                        if any(
                            keyword in content
                            for keyword in ["@app.route", "@router", "request.", "response."]
                        ):
                            conflicts.append(
                                {
                                    "message": f"业务层 '{dir_name}' 可能混入了HTTP处理",
                                    "file": str(file_path),
                                    "suggestion": "HTTP处理应在路由层",
                                }
                            )
                    except Exception:
                        pass

        return conflicts

    def _generate_directory_responsibility_table(
        self, dir_responsibilities: list[dict]
    ) -> str:
        """生成目录责任表（Markdown格式）"""
        lines = [
            "## 目录责任表",
            "",
            "| 目录 | 文件数 | 主要职责 | 状态 |",
            "|------|--------|---------|------|",
        ]

        for dir_info in dir_responsibilities:
            dir_name = dir_info["directory"]
            file_count = dir_info["file_count"]
            responsibility = dir_info["responsibility"]

            status = "✅" if responsibility != "未明确" else "⚠️"

            lines.append(
                f"| {dir_name} | {file_count} | {responsibility} | {status} |"
            )

        lines.append("")
        return "\n".join(lines)
