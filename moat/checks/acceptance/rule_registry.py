"""规则注册表 — YAML 驱动的架构验收规则定义

架构师（或 AI）通过 `architect.yml` 定义项目的架构规则，
`moat accept` 根据规则逐项验证并输出验收证据。

设计原则（来自创始人建议）:
- 配置驱动：不给每个规则写死一个类，用 YAML 声明验证模式
- 半自动化：能自动检查的走现有算子，不能的输出人工核查清单
- 证据追溯：每条规则的结果有文件/行号/证据链
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ──────────────────────────────────────────────
# 规则定义模型
# ──────────────────────────────────────────────


@dataclass
class RuleDefinition:
    """单条架构规则定义"""

    id: str
    """唯一标识 (如 DIR_BOUNDARIES)"""

    title: str
    """规则中文标题"""

    description: str
    """规则描述"""

    step: int
    """对应验收步骤 (1-8)"""

    # 验证模式
    type: str = "ast_pattern"
    """
    验证模式:
    - "structure"      → 复用 moat structure 检查
    - "ast_pattern"    → 复用 AST 扫描模式
    - "call_chain"     → 复用 CodeGraph 调用链分析
    - "api_contract"   → 复用 API 响应规范检查
    - "manual"         → 人工核查（自动生成证据包）
    - "runtime"        → 运行时证据验证
    """

    severity: str = "HIGH"
    """严重级别: CRITICAL / HIGH / RECOMMENDED"""

    config: dict[str, Any] = field(default_factory=dict)
    """验证配置 (模式相关参数)"""

    operator: str | None = None
    """对应 verification operator 的名称 (如果可自动)"""

    auto_checkable: bool = False
    """是否能自动检查"""


@dataclass
class RuleResult:
    """单条规则的验收结果"""

    rule: RuleDefinition
    """规则定义"""

    passed: bool = False
    """是否通过"""

    auto_checked: bool = False
    """是否通过自动检查"""

    evidence: list[str] = field(default_factory=list)
    """证据链 (文件路径/行号/摘要)"""

    violations: list[dict] = field(default_factory=list)
    """违规详情"""

    manual_check_items: list[str] = field(default_factory=list)
    """人工核查项"""

    suggestion: str | None = None
    """建议"""

    execution_time: float = 0.0
    """执行耗时"""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.rule.id,
            "title": self.rule.title,
            "step": self.rule.step,
            "passed": self.passed,
            "auto_checked": self.auto_checked,
            "evidence_count": len(self.evidence),
            "violations": len(self.violations),
            "manual_check_items": self.manual_check_items,
            "suggestion": self.suggestion,
            "execution_time": round(self.execution_time, 2),
        }


# ──────────────────────────────────────────────
# 内置默认规则（8 步验收标准）
# ──────────────────────────────────────────────

DEFAULT_RULES = [
    RuleDefinition(
        id="ARCH_RULES",
        title="架构规则审计",
        description="依据业务及架构设计文档，对项目做全面代码审计。逐项明确规则来源、对应文件、验证方式、通过与否。",
        step=1,
        type="manual",
        severity="CRITICAL",
        auto_checkable=False,
        config={
            "items": [
                "规则来源是否清晰标注（架构文档/项目规范/框架约定）",
                "每条规则是否有对应的代码检查覆盖",
                "来源不明的规则是否标注为『待验证』",
            ]
        },
    ),
    RuleDefinition(
        id="DIR_BOUNDARIES",
        title="目录责任边界",
        description="验证每个目录的职责是否唯一、存放规则清晰、区分框架和自定义目录。",
        step=2,
        type="structure",
        severity="CRITICAL",
        operator="directory_responsibility",
        auto_checkable=True,
    ),
    RuleDefinition(
        id="MODULE_DRILL",
        title="最小模块演练",
        description="通过极简模块验证理论规则落地性：文件放置逻辑可延续、调用链路分层清晰。",
        step=3,
        type="call_chain",
        severity="HIGH",
        operator="minimal_module_drill",
        auto_checkable=True,
    ),
    RuleDefinition(
        id="LAYER_VIOLATION",
        title="调用链分层校验",
        description="检测跨层调用违规：路由层不应直接访问数据库，服务层调用方向需正确，无循环依赖。",
        step=3,
        type="call_chain",
        severity="CRITICAL",
        operator="layer_violation",
        auto_checkable=True,
    ),
    RuleDefinition(
        id="API_CONSISTENCY",
        title="接口统一返回规范",
        description="所有 API 接口响应格式统一：HTTP 状态码 + JSON 结构 + 错误处理，覆盖全场景。",
        step=4,
        type="api_contract",
        severity="CRITICAL",
        operator="api_response_spec",
        auto_checkable=True,
    ),
    RuleDefinition(
        id="FRAMEWORK_BOUNDARY",
        title="框架复用与封装边界",
        description="优先复用框架成熟能力，避免无效冗余封装。所有自定义封装需说明必要性。",
        step=5,
        type="ast_pattern",
        severity="HIGH",
        operator="framework_usage",
        auto_checkable=True,
    ),
    RuleDefinition(
        id="RUNTIME_EVIDENCE",
        title="启动、配置、数据库与日志规则",
        description="固定运行标准：依赖安装、服务启动、健康检查、端口/配置/数据库/日志都应有实际证据。",
        step=6,
        type="runtime",
        severity="HIGH",
        operator="runtime_evidence",
        auto_checkable=True,
    ),
    RuleDefinition(
        id="LEAKAGE_DETECTION",
        title="代码泄露风险检测",
        description="检测 AI 工具跨目录读取痕迹、敏感文件暴露、symlink 泄露、硬编码敏感路径。",
        step=5,
        type="structure",
        severity="CRITICAL",
        operator="leakage_detection",
        auto_checkable=True,
    ),
    RuleDefinition(
        id="TRUTH_DOC",
        title="收口验收结果，输出标准化文档",
        description="汇总所有验收项，明确通过/未通过/未验证，生成后端架构实施真元文档。",
        step=7,
        type="structure",
        severity="RECOMMENDED",
        operator="truth_document",
        auto_checkable=True,
    ),
    RuleDefinition(
        id="GIT_BASELINE",
        title="固化版本，留存稳定基线",
        description="验收通过后提交 Git 版本，首个稳定版本标记为基线，后续迭代基于此基线。",
        step=8,
        type="runtime",
        severity="RECOMMENDED",
        operator="git_baseline",
        auto_checkable=True,
        config={
            "items": [
                "当前是否有 Git 仓库",
                "上次提交时间",
                "是否有未提交的变更",
                "是否已创建基线 Tag（建议 v1.0）",
            ]
        },
    ),
]

# ──────────────────────────────────────────────
# 规则注册表
# ──────────────────────────────────────────────

DEFAULT_YAML_TEMPLATE = """# architect.yml — 架构验收规则定义
# 由 `moat accept --generate-rules` 自动生成
# 根据项目实际情况修改后，`moat accept` 将按此规则验收

project: "{project_name}"
version: 1.0

rules:
  # ── 步骤 1：架构规则审计（人工核查） ──
  - id: ARCH_RULES
    title: "架构规则审计"
    description: "依据架构设计文档，逐项明确规则来源、对应文件、验证方式、通过与否"
    step: 1
    type: manual
    severity: CRITICAL
    config:
      items:
        - "规则来源是否清晰标注（架构文档/项目规范/框架约定）"
        - "每条规则是否有对应的代码检查覆盖"
        - "来源不明的规则是否标注为『待验证』"

  # ── 步骤 2：目录责任边界 ──
  - id: DIR_BOUNDARIES
    title: "目录责任边界"
    description: "验证每个目录的职责是否唯一、存放规则清晰"
    step: 2
    type: structure
    severity: CRITICAL
    operator: directory_responsibility

  # ── 步骤 3：最小模块演练 ──
  - id: MODULE_DRILL
    title: "最小模块演练"
    description: "通过极简模块验证理论规则落地性"
    step: 3
    type: call_chain
    severity: HIGH
    operator: minimal_module_drill

  # ── 步骤 4：接口统一返回规范 ──
  - id: API_CONSISTENCY
    title: "接口统一返回规范"
    description: "所有 API 接口响应格式统一"
    step: 4
    type: api_contract
    severity: CRITICAL
    operator: api_response_spec

  # ── 步骤 5：框架复用与封装边界 ──
  - id: FRAMEWORK_BOUNDARY
    title: "框架复用与封装边界"
    description: "优先复用框架能力，避免无效冗余封装"
    step: 5
    type: ast_pattern
    severity: HIGH
    operator: framework_usage

  # ── 步骤 6：运行证据 ──
  - id: RUNTIME_EVIDENCE
    title: "启动、配置、数据库与日志规则"
    description: "固定运行标准，留存实际证据"
    step: 6
    type: runtime
    severity: HIGH
    operator: runtime_evidence

  # ── 步骤 7：收口验收结果 ──
  - id: TRUTH_DOC
    title: "输出架构实施真元文档"
    description: "汇总所有验收项，生成标准化文档"
    step: 7
    type: structure
    severity: RECOMMENDED
    operator: truth_document

  # ── 步骤 8：固化版本 ──
  - id: GIT_BASELINE
    title: "固化版本，留存稳定基线"
    description: "提交 Git 版本，创建基线"
    step: 8
    type: manual
    severity: RECOMMENDED
    config:
      items:
        - "当前是否有 Git 仓库"
        - "上次提交时间"
        - "是否有未提交的变更"
        - "是否已创建基线 Tag（建议 v1.0）"
"""


class RuleRegistry:
    """规则注册表 — 加载、保存、管理架构验收规则"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.rules: list[RuleDefinition] = []
        self._loaded = False

    # ── 加载规则 ──

    def load(self, path: str | Path | None = None) -> list[RuleDefinition]:
        """加载架构规则

        加载顺序:
        1. 指定路径 → 2. 项目下 architect.yml / architect.json → 3. 内置默认规则
        """
        # 已加载过，直接返回
        if self._loaded and not path:
            return self.rules

        # 尝试从文件加载
        if path:
            rules_path = Path(path)
        else:
            rules_path = self.project_root / "architect.yml"
            if not rules_path.exists():
                rules_path = self.project_root / "architect.json"

        if rules_path.exists():
            self.rules = self._load_file(rules_path)
        else:
            # 使用内置默认规则
            self.rules = DEFAULT_RULES

        self._loaded = True
        return self.rules

    def _load_file(self, path: Path) -> list[RuleDefinition]:
        """从 YAML/JSON 文件加载规则"""
        try:
            raw = path.read_text(encoding="utf-8")
            if path.suffix in (".yaml", ".yml"):
                # 尝试用 pyyaml，如果不可用则用内置 JSON fallback
                try:
                    import yaml
                    data = yaml.safe_load(raw)
                except ImportError:
                    return DEFAULT_RULES
            elif path.suffix == ".json":
                data = json.loads(raw)
            else:
                return DEFAULT_RULES

            rules_data = data.get("rules", [])
            return [self._parse_rule(r) for r in rules_data]

        except Exception as e:
            print(f"  ⚠ 规则文件加载失败: {e}")
            print(f"  ℹ️  使用内置默认规则")
            return DEFAULT_RULES

    def _parse_rule(self, data: dict) -> RuleDefinition:
        """解析单条规则定义"""
        return RuleDefinition(
            id=data.get("id", "UNKNOWN"),
            title=data.get("title", "未命名规则"),
            description=data.get("description", ""),
            step=data.get("step", 0),
            type=data.get("type", "manual"),
            severity=data.get("severity", "HIGH"),
            config=data.get("config", {}),
            operator=data.get("operator"),
            auto_checkable=data.get("operator") is not None,
        )

    # ── 规则查询 ──

    def get_by_step(self, step: int) -> list[RuleDefinition]:
        """按验收步骤获取规则"""
        return [r for r in self.rules if r.step == step]

    def get_by_id(self, rule_id: str) -> RuleDefinition | None:
        """按 ID 获取规则"""
        for r in self.rules:
            if r.id == rule_id:
                return r
        return None

    def get_auto_checkable(self) -> list[RuleDefinition]:
        """获取可自动检查的规则"""
        return [r for r in self.rules if r.auto_checkable]

    def get_manual(self) -> list[RuleDefinition]:
        """获取需要人工核查的规则"""
        return [r for r in self.rules if not r.auto_checkable]

    def summary(self) -> dict[str, int]:
        """规则汇总"""
        auto = len(self.get_auto_checkable())
        manual = len(self.get_manual())
        return {
            "total": len(self.rules),
            "auto_checkable": auto,
            "manual": manual,
        }

    # ── 模板生成 ──

    @staticmethod
    def generate_template(project_name: str = "my-project") -> str:
        """生成 architect.yml 模板"""
        return DEFAULT_YAML_TEMPLATE.format(project_name=project_name)

    @staticmethod
    def save_template(project_root: Path, project_name: str | None = None) -> Path:
        """保存 architect.yml 模板到项目根目录"""
        if project_name is None:
            project_name = project_root.name
        content = DEFAULT_YAML_TEMPLATE.format(project_name=project_name)
        path = project_root / "architect.yml"
        path.write_text(content, encoding="utf-8")
        return path

    # ── 默认规则查询 ──

    @staticmethod
    def get_default_steps_info() -> dict[int, dict[str, str]]:
        """获取 8 步验收的步骤信息（用于报告生成）"""
        return {
            1: {"title": "架构规则审计", "description": "逐项审计架构规则的来源、覆盖和验证方式"},
            2: {"title": "目录责任边界", "description": "验证目录职责唯一性、存放规则清晰度"},
            3: {"title": "最小模块演练", "description": "验证理论规则的落地能力"},
            4: {"title": "接口统一返回规范", "description": "全场景接口响应格式校验"},
            5: {"title": "框架复用与封装边界", "description": "框架能力复用 vs 自定义封装的必要性"},
            6: {"title": "运行证据固定", "description": "启动、配置、数据库、日志的实际证据"},
            7: {"title": "收口验收结果", "description": "汇总验收结论，生成真元文档"},
            8: {"title": "固化版本基线", "description": "Git 版本标签化，留存稳定基线"},
        }
