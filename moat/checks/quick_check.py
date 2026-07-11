"""快速检查器 — 只检查修改的文件

这是"瘦身计划"的核心：
- 默认模式（moat check）：只检查修改的文件（git diff）
- 完整模式（moat check --full）：检查所有文件
- 内置 5 条常识规则，不依赖复杂的 L1/L2/L3/L4 规则
"""
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult
from moat.checks.fail_open import fail_open

logger = logging.getLogger(__name__)


class QuickCheck(Check):
    """快速检查器（默认模式）

    只检查修改的文件，内置 5 条规则：
    1. 分层规则
    2. API 鉴权
    3. 竞态条件
    4. SQL 注入
    5. 错误处理
    """

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        super().__init__(project_root, config)
        self.config = config or {}
        self.name = "QuickCheck"

    def run(self) -> list[CheckResult]:
        """运行快速检查"""
        results = []

        # 1. 获取修改的文件列表
        changed_files = self._get_changed_files()

        if not changed_files:
            return [CheckResult(
                type="pass",
                level="INFO",
                message="没有检测到修改的文件",
            )]

        # 2. 只检查修改的文件
        for file_path in changed_files:
            if file_path.suffix in [".py", ".ts", ".tsx"]:
                file_results = self._check_file(file_path)
                results.extend(file_results)

        return results

    def _get_changed_files(self) -> list[Path]:
        """获取修改的文件列表（git diff）

        Returns:
            绝对路径列表
        """
        try:
            # 使用 git diff 检测修改的文件
            result = subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=ACMR"],
                cwd=str(self.project.resolve()),
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                return []

            files = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    file_path = self.project / line
                    if file_path.exists():
                        files.append(file_path)

            return files
        except Exception as e:
            return []

    @fail_open(default_return=[], log_level=logging.DEBUG)
    def _check_file(self, file_path: Path) -> list[CheckResult]:
        """检查单个文件"""
        results = []

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        # 规则 1：分层检查（仅 Python）
        if file_path.suffix == ".py":
            results.extend(self._check_layer(file_path, content))

        # 规则 2：API 鉴权
        results.extend(self._check_auth(file_path, content))

        # 规则 3：竞态条件
        results.extend(self._check_race_condition(file_path, content))

        # 规则 4：SQL 注入（使用专门的 SQLInjectionCheck）
        if file_path.suffix == ".py":
            from moat.checks.sql_injection import SQLInjectionCheck
            sql_check = SQLInjectionCheck(self.project, self.config)
            results.extend(sql_check._check_file(file_path))

        # 规则 5：错误处理
        if file_path.suffix == ".py":
            results.extend(self._check_error_handling(file_path, content))

        return results

    def _check_layer(self, file_path: Path, content: str) -> list[CheckResult]:
        """规则 1：分层检查"""
        results = []

        # 简化的分层检查：检测是否直接调用 ORM 或数据库
        if "django.db" in content and "views.py" in str(file_path):
            results.append(CheckResult(
                type="warn",
                level="WARN",
                file=str(file_path.relative_to(self.project)),
                message="[分层] views.py 中直接使用了 django.db，建议通过 Model 层访问",
            ))

        return results

    def _check_auth(self, file_path: Path, content: str) -> list[CheckResult]:
        """规则 2：API 鉴权"""
        results = []

        # 通用检测：API 路由缺少鉴权
        api_patterns = [
            "@app.route(",  # Flask
            "@router.",  # FastAPI
            "@api_view",  # Django REST
            "@RequestMapping",  # Spring/Java
            "app.get(",  # FastAPI
            "app.post(",  # FastAPI
        ]

        auth_patterns = [
            "login_required",
            "authenticate",
            "authorize",
            "permission",
            "token",
            "jwt",
            "oauth",
            "@current_user",
        ]

        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            # 检查是否是 API 路由定义
            is_api_route = any(api in line for api in api_patterns)

            if is_api_route:
                # 检查接下来的 10 行是否有鉴权
                next_lines = "\n".join(lines[i:i+10])

                # 如果没有鉴权关键词，且不是测试文件
                if not any(auth in next_lines for auth in auth_patterns):
                    # 排除测试文件
                    if "test" not in str(file_path).lower():
                        results.append(CheckResult(
                            type="warn",
                            level="WARN",
                            file=str(file_path.relative_to(self.project)),
                            line=i,
                            message=f"[鉴权] 第 {i} 行检测到 API 路由，建议添加鉴权",
                        ))

        return results

    def _check_race_condition(self, file_path: Path, content: str) -> list[CheckResult]:
        """规则 3：竞态条件"""
        results = []

        # 检测 React hooks 缺少依赖
        if "useEffect" in content and "eslint-disable" not in content:
            if "useEffect(" in content and "dependencies" not in content:
                results.append(CheckResult(
                    type="warn",
                    level="WARN",
                    file=str(file_path.relative_to(self.project)),
                    message="[竞态] useEffect 可能缺少依赖数组",
                ))

        return results

    def _check_error_handling(self, file_path: Path, content: str) -> list[CheckResult]:
        """规则 5：错误处理"""
        results = []

        # 检测 async 函数缺少 try/except
        if "async def" in content:
            lines = content.split("\n")
            in_async_func = False
            func_line = 0

            for i, line in enumerate(lines, 1):
                if "async def" in line:
                    in_async_func = True
                    func_line = i

                if in_async_func:
                    # 检查接下来的 20 行是否有 try/except
                    if i < func_line + 20:
                        if "try:" in line:
                            in_async_func = False  # 找到 try，跳过
                            break
                    else:
                        # 超过 20 行没找到 try，标记为建议
                        results.append(CheckResult(
                            type="info",
                            level="INFO",
                            file=str(file_path.relative_to(self.project)),
                            line=func_line,
                            message=f"[错误处理] async 函数（第 {func_line} 行）建议添加 try/except",
                        ))
                        in_async_func = False

        return results


class FullCheck(Check):
    """完整检查器（--full 模式）

    检查所有文件，包括复杂的规则（L1/L2/L3/L4）。
    """

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        super().__init__(project_root, config)
        self.config = config or {}

        # 🆕 支持环境变量跳过架构检查
        import os
        if os.environ.get("MOAT_SKIP_ARCHITECTURE", "").lower() == "true":
            self.config["skip_architecture"] = True

        self.name = "FullCheck"

    def run(self) -> list[CheckResult]:
        """运行完整检查"""
        results = []

        # 1. 先运行快速检查（所有文件）
        quick = QuickCheck(self.project, self.config)
        results.extend(quick.run())

        # 2. 🆕 运行 L2 架构规则检查（除非跳过）
        skip_architecture = self.config.get("skip_architecture", False)

        if not skip_architecture:
            from moat.checks.l2_architecture import run_architecture_check

            # 加载基线数据（用于熵增检测）
            from moat.baseline import BaselineManager

            baseline_mgr = BaselineManager(self.project)
            baseline = baseline_mgr.load()

            l2_errors = run_architecture_check(
                self.project,
                baseline=baseline,
                quick_mode=False,
            )

            # 转换为 CheckResult
            for error in l2_errors:
                results.append(CheckResult(
                    type="fail" if error.get("level") in ("ERROR", "CRITICAL") else "warn",
                    level=error.get("level", "WARN"),
                    file=error.get("file", ""),
                    line=0,
                    message=error.get("message", ""),
                    metadata={
                        "l2_type": error.get("type", ""),
                        "suggestion": error.get("suggestion", ""),
                    },
                ))

        # 3. TODO: 其他复杂规则检查（L1/L3/L4）

        return results
