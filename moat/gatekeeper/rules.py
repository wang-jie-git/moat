"""
规则引擎 — 架构守门规则系统
"""

from pathlib import Path
from typing import TYPE_CHECKING

from .types import RuleSeverity, RuleViolation

if TYPE_CHECKING:
    pass


class ArchitectureRule:
    """
    架构规则

    定义单个架构规则的检查逻辑
    """

    def __init__(
        self,
        rule_id: str,
        name: str,
        description: str,
        severity: RuleSeverity = RuleSeverity.WARNING,
    ):
        self.rule_id = rule_id
        self.name = name
        self.description = description
        self.severity = severity

    def check(self, file_path: str, content: str, context: dict) -> list[RuleViolation]:
        """
        检查规则

        Args:
            file_path: 文件路径
            content: 文件内容
            context: 上下文信息（项目路径等）

        Returns:
            违规列表
        """
        raise NotImplementedError


class DirectoryResponsibilityRule(ArchitectureRule):
    """目录责任规则：检查文件是否在正确的目录"""

    def __init__(self):
        super().__init__(
            rule_id="directory_responsibility",
            name="目录责任",
            description="文件应该放在符合其职责的目录",
            severity=RuleSeverity.ERROR,
        )

        # 目录职责映射
        self.directory_responsibilities = {
            "api": {
                "should_contain": ["router", "APIRouter", "@app.", "@router."],
                "should_not_contain": ["def calculate_", "def process_", "db.", "session.query"],
                "description": "仅包含路由定义和参数校验",
            },
            "services": {
                "should_contain": ["业务逻辑", "def handle_", "def process_"],
                "should_not_contain": ["@app.route", "@router.", "request.", "response."],
                "description": "仅包含业务逻辑",
            },
            "repositories": {
                "should_contain": ["db.", "session.query", "select(", "insert("],
                "should_not_contain": ["@app.", "@router.", "业务逻辑"],
                "description": "仅包含数据访问",
            },
        }

    def check(self, file_path: str, content: str, context: dict) -> list[RuleViolation]:
        violations = []

        # 解析文件所在目录
        path = Path(file_path)
        relative_path = path.relative_to(context.get("project_path", path.parent))

        # 获取顶层目录（如 api/users/router.py → api）
        parts = relative_path.parts
        if len(parts) < 2:
            return violations

        top_dir = parts[0]

        # 检查是否在定义的目录中
        if top_dir not in self.directory_responsibilities:
            return violations

        responsibility = self.directory_responsibilities[top_dir]

        # 检查禁止内容
        for keyword in responsibility.get("should_not_contain", []):
            if keyword in content:
                violations.append(
                    RuleViolation(
                        rule_id=self.rule_id,
                        rule_name=self.name,
                        message=f"'{top_dir}' 目录不应包含: {keyword}",
                        severity=self.severity,
                        file_path=file_path,
                        suggestion=f"'{top_dir}' 目录应该{responsibility['description']}",
                    )
                )

        return violations


class LayerSeparationRule(ArchitectureRule):
    """分层架构规则：检查import是否违反分层"""

    def __init__(self):
        super().__init__(
            rule_id="layer_separation",
            name="分层架构",
            description="检查import是否违反分层架构",
            severity=RuleSeverity.ERROR,
        )

        # 分层规则
        self.layer_rules = {
            "api": {
                "can_import": ["schemas", "services", "core.exceptions"],
                "cannot_import": ["repositories", "database", "models", "db"],
                "description": "路由层只能调用Service层",
            },
            "services": {
                "can_import": ["repositories", "schemas", "core.exceptions"],
                "cannot_import": ["api", "fastapi", "flask", "django"],
                "description": "业务层只能调用Repository层",
            },
            "repositories": {
                "can_import": ["models", "database", "core.exceptions"],
                "cannot_import": ["api", "services", "fastapi", "flask"],
                "description": "数据层只能访问数据库模型",
            },
        }

    def check(self, file_path: str, content: str, context: dict) -> list[RuleViolation]:
        violations = []

        # 解析文件所在目录
        path = Path(file_path)

        try:
            project_path = Path(context.get("project_path", path.parent))
            relative_path = path.relative_to(project_path)
        except ValueError:
            # 文件不在项目路径下，无法确定目录结构
            return violations

        parts = relative_path.parts
        if len(parts) < 2:
            return violations

        top_dir = parts[0]

        # 检查是否在定义的目录中
        if top_dir not in self.layer_rules:
            return violations

        layer_rule = self.layer_rules[top_dir]
        cannot_import = layer_rule["cannot_import"]

        # 解析import语句
        import_lines = [line.strip() for line in content.split('\n') if line.strip().startswith(('import ', 'from '))]

        for import_line in import_lines:
            # 检查是否导入了禁止的模块
            for forbidden_module in cannot_import:
                if f"import {forbidden_module}" in import_line or f"from {forbidden_module}" in import_line:
                    violations.append(
                        RuleViolation(
                            rule_id=self.rule_id,
                            rule_name=self.name,
                            message=f"'{top_dir}' 层不应导入: {forbidden_module}",
                            severity=self.severity,
                            file_path=file_path,
                            suggestion=layer_rule["description"],
                        )
                    )

        return violations


class NamingConventionRule(ArchitectureRule):
    """命名规范规则：检查文件命名是否符合规范"""

    def __init__(self):
        super().__init__(
            rule_id="naming_convention",
            name="命名规范",
            description="文件命名应符合项目规范",
            severity=RuleSeverity.WARNING,
        )

        # 命名规范
        self.naming_patterns = {
            "api/**/router.py": r"^[a-z_]+_router\.py$",
            "services/**/*_service.py": r"^[a-z_]+_service\.py$",
            "repositories/**/*_repo.py": r"^[a-z_]+_repo\.py$",
            "schemas/**/*.py": r"^[A-Z][a-zA-Z]*\.py$",  # PascalCase
        }

    def check(self, file_path: str, content: str, context: dict) -> list[RuleViolation]:
        violations = []

        # 简化版：只检查文件名
        filename = Path(file_path).name

        # 检查router文件
        if "router.py" in filename and not filename.endswith("_router.py"):
            violations.append(
                RuleViolation(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    message=f"路由文件应以 '_router.py' 结尾: {filename}",
                    severity=self.severity,
                    file_path=file_path,
                    suggestion="重命名为: {filename}",
                )
            )

        return violations


class FrameworkUsageRule(ArchitectureRule):
    """框架利用规则：检查是否使用框架推荐机制"""

    def __init__(self):
        super().__init__(
            rule_id="framework_usage",
            name="框架利用",
            description="优先使用框架推荐机制",
            severity=RuleSeverity.WARNING,
        )

    def check(self, file_path: str, content: str, context: dict) -> list[RuleViolation]:
        violations = []

        # 检查FastAPI项目是否手动解析JSON
        if "fastapi" in context.get("frameworks", []):
            # 排除导入语句和注释
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith(('import ', 'from ', '#')):
                    continue

                if 'json.loads' in line or 'request.json()' in line:
                    violations.append(
                        RuleViolation(
                            rule_id=self.rule_id,
                            rule_name=self.name,
                            message="检测到手动JSON解析，建议使用Pydantic模型",
                            severity=self.severity,
                            file_path=file_path,
                            line=i,
                            suggestion="使用 Pydantic BaseModel 替代手动JSON解析",
                        )
                    )

        return violations


class RuleEngine:
    """
    规则引擎

    管理所有架构规则，执行检查
    """

    def __init__(self):
        self.rules: list[ArchitectureRule] = []
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        """注册默认规则"""
        self.rules = [
            DirectoryResponsibilityRule(),
            LayerSeparationRule(),
            NamingConventionRule(),
            FrameworkUsageRule(),
        ]

    def add_rule(self, rule: ArchitectureRule) -> None:
        """添加自定义规则"""
        self.rules.append(rule)

    def check_file(self, file_path: str, content: str, context: dict) -> list[RuleViolation]:
        """
        检查单个文件

        Args:
            file_path: 文件路径
            content: 文件内容
            context: 上下文信息

        Returns:
            所有违规列表
        """
        violations = []

        for rule in self.rules:
            try:
                rule_violations = rule.check(file_path, content, context)
                violations.extend(rule_violations)
            except Exception:
                # 单个规则失败不影响其他规则
                pass

        return violations

    def list_rules(self) -> list[dict]:
        """列出所有规则"""
        return [
            {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "description": rule.description,
                "severity": rule.severity.value,
            }
            for rule in self.rules
        ]
