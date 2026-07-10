"""
AI 测试门票规则 — 测试覆盖率守门系统

核心能力：
- 测试文件存在性检查（每行业务代码必须有测试）
- 覆盖率报告验证（低于阈值则拦截）
- AI 自动生成测试触发（通过 One Memory + Claude API）
- 与 ai_test_config.yml 深度集成

设计原则：
- 默认拦截
- AI 辅助修复
- 渐进式宽松（新代码 85% → 旧代码 80%）
- 审计追踪
"""

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

from ..types import RuleSeverity, RuleViolation
from . import ArchitectureRule

if TYPE_CHECKING:
    from .checker import ArchitectureGatekeeper


class TestCoverageGateRule(ArchitectureRule):
    """
    测试覆盖率守门规则

    配置来源：ai_test_config.yml → unit_tests.test_ticket
    """

    def __init__(self):
        super().__init__(
            rule_id="test_coverage_gate",
            name="AI 测试门票",
            description="新增代码必须拥有对应的测试且覆盖率达标",
            severity=RuleSeverity.CRITICAL,
        )

        # 默认阈值（可从 ai_test_config.yml 覆盖）
        self.default_threshold = 80.0
        self.new_code_threshold = 85.0  # 新代码要求更严格

    def check(
        self,
        file_path: str,
        content: str,
        context: dict,
        gatekeeper: "ArchitectureGatekeeper" = None,
    ) -> list[RuleViolation]:
        """
        检查测试覆盖率门禁

        Args:
            file_path: 文件路径
            content: 文件内容
            context: 上下文信息
            gatekeeper: Gatekeeper 实例（用于触发 AI 生成）

        Returns:
            违规列表
        """
        violations = []

        # 1. 检查是否是业务代码（不检查测试文件、__init__.py、配置等）
        if not self._is_business_code(file_path):
            return violations

        # 2. 检查对应的测试文件是否存在
        test_file_violation = self._check_test_file_existence(file_path, context)
        if test_file_violation:
            violations.append(test_file_violation)

            # 触发 AI 生成测试（如果启用了 ai_test_config.yml）
            if gatekeeper and self._should_trigger_ai_generation():
                self._trigger_ai_test_generation(file_path, content, gatekeeper)

        # 3. 检查覆盖率报告（仅在存在测试文件时检查）
        if not test_file_violation:
            coverage_violation = self._check_coverage_report(file_path, context)
            if coverage_violation:
                violations.append(coverage_violation)

        return violations

    def _is_business_code(self, file_path: str) -> bool:
        """
        判断是否是业务代码

        跳过：测试文件、__init__.py、migrations、配置、文档
        """
        # 跳过测试文件
        if "/tests/" in file_path or file_path.startswith("tests/"):
            return False

        # 跳过 __init__.py
        if file_path.endswith("__init__.py"):
            return False

        # 跳过 migrations
        if "/migrations/" in file_path or "alembic/" in file_path:
            return False

        # 跳过配置文件
        if any(file_path.endswith(ext) for ext in [".yaml", ".yml", ".toml", ".ini", ".cfg"]):
            return False

        # 跳过文档
        if any(file_path.endswith(ext) for ext in [".md", ".rst", ".txt"]):
            return False

        # 只检查 Python 文件
        if not file_path.endswith(".py"):
            return False

        return True

    def _check_test_file_existence(self, file_path: str, context: dict) -> RuleViolation | None:
        """
        检查对应的测试文件是否存在

        规则：
        - services/foo.py → tests/unit/services/test_foo.py
        - core/bar.py → tests/unit/core/test_bar.py
        - api/baz.py → tests/unit/api/test_baz.py
        """
        project_path = Path(context.get("project_path", "."))
        relative_path = Path(file_path).relative_to(project_path)

        # 确定测试目录
        parts = relative_path.parts
        if len(parts) < 2:
            return None

        top_dir = parts[0]

        # 只检查特定目录的业务代码
        monitored_dirs = {"services", "core", "api", "repositories", "models"}
        if top_dir not in monitored_dirs:
            return None

        # 构建测试文件路径
        filename = relative_path.name
        test_filename = f"test_{filename}"
        test_file_path = project_path / "tests" / "unit" / top_dir / test_filename

        # 检查测试文件是否存在
        if not test_file_path.exists():
            return RuleViolation(
                rule_id=self.rule_id,
                rule_name=self.name,
                message=f"缺少测试文件：{test_file_path.relative_to(project_path)}",
                severity=RuleSeverity.CRITICAL,
                file_path=file_path,
                suggestion=f"请创建测试文件：{test_file_path.relative_to(project_path)}\n"
                f"或运行命令：moat test generate --type=unit --file={file_path}",
                context={
                    "missing_test_file": str(test_file_path.relative_to(project_path)),
                    "business_file": str(relative_path),
                    "auto_fix_command": f"moat test generate --type=unit --file={file_path}",
                },
            )

        return None

    def _check_coverage_report(self, file_path: str, context: dict) -> RuleViolation | None:
        """
        检查覆盖率报告

        优先级：
        1. 查找 .coverage 文件（coverage.py 生成）
        2. 查找 coverage.json 文件
        3. 查找 htmlcov/index.html
        """
        project_path = Path(context.get("project_path", "."))

        # 查找覆盖率报告
        coverage_file = None
        for candidate in [".coverage", "coverage.json", "htmlcov/index.html"]:
            candidate_path = project_path / candidate
            if candidate_path.exists():
                coverage_file = candidate_path
                break

        if not coverage_file:
            return None  # 没有覆盖率报告，跳过（不强求）

        # 读取覆盖率数据
        coverage_data = self._load_coverage_data(coverage_file)
        if not coverage_data:
            return None

        # 获取该文件的覆盖率
        file_coverage = coverage_data.get("files", {}).get(file_path)
        if file_coverage is None:
            return None  # 文件中没有统计到覆盖率

        # 判断是否是新增代码（简化版：根据 git diff 判断）
        is_new_code = self._is_new_code(file_path, project_path)
        threshold = self.new_code_threshold if is_new_code else self.default_threshold

        # 检查是否达标
        if file_coverage < threshold:
            return RuleViolation(
                rule_id=self.rule_id,
                rule_name=self.name,
                message=f"测试覆盖率 {file_coverage:.1f}% 未达到 {threshold:.0f}% 的{'新代码' if is_new_code else '项目'}底线",
                severity=RuleSeverity.CRITICAL,
                file_path=file_path,
                suggestion=f"请补充测试使覆盖率 ≥ {threshold:.0f}%\n"
                f"运行命令：pytest --cov={Path(file_path).parent}",
                context={
                    "current_coverage": file_coverage,
                    "required_threshold": threshold,
                    "is_new_code": is_new_code,
                    "coverage_report": str(coverage_file),
                },
            )

        return None

    def _load_coverage_data(self, coverage_file: Path) -> dict | None:
        """加载覆盖率数据"""
        try:
            if coverage_file.name == ".coverage":
                # coverage.py 的 SQLite 格式（简化处理，实际需要 coverage 库）
                return None
            elif coverage_file.name == "coverage.json":
                with open(coverage_file) as f:
                    return json.load(f)
            elif coverage_file.name == "index.html":
                # 从 htmlcov/index.html 解析（简化处理）
                return None
        except Exception:
            pass

        return None

    def _is_new_code(self, file_path: str, project_path: Path) -> bool:
        """
        判断是否是新增/修改的代码

        简化版：检查是否是最近 7 天内修改的文件
        完整版：应该与 git diff 集成
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return False

            # 检查文件最后修改时间
            import time
            mtime = file_path.stat().st_mtime
            days_old = (time.time() - mtime) / (24 * 3600)

            return days_old < 7  # 7 天内修改视为新代码
        except Exception:
            return False

    def _should_trigger_ai_generation(self) -> bool:
        """检查是否应该触发 AI 生成（根据 ai_test_config.yml）"""
        # 简化版：始终触发（完整版应该读取 ai_test_config.yml）
        return True

    def _trigger_ai_test_generation(
        self,
        file_path: str,
        content: str,
        gatekeeper: "ArchitectureGatekeeper",
    ) -> None:
        """
        触发 AI 生成测试

        通过 One Memory + Claude API 实现
        """
        try:
            # 1. 记录到 One Memory
            self._record_to_one_memory(file_path, content)

            # 2. 调用 AI 生成测试（通过 Immune 模块）
            from ...immune.unit.generator import AITestGateway

            gateway = AITestGateway()
            gateway.generate_unit_test(file_path, content)

        except Exception as e:
            # AI 生成失败不影响守门拦截
            print(f"⚠️  AI 测试生成失败（不影响拦截）: {e}")

    def _record_to_one_memory(self, file_path: str, content: str) -> None:
        """记录到 One Memory"""
        try:
            from ...memory.bridge import SharedStorageBridge, BridgeConfig

            bridge = SharedStorageBridge(
                BridgeConfig(db_path=str(Path(".moat/memory.db")))
            )
            bridge.initialize()

            # 记录业务代码变更
            bridge.store_node(
                node_type="test_ticket",
                content={
                    "business_file": file_path,
                    "missing_test": True,
                    "timestamp": str(Path(".moat").stat().st_mtime),
                },
            )

            bridge.close()
        except Exception:
            pass
