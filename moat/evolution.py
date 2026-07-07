"""元知识反向驱动机制 — 梦境引擎的 Insight 驱动 Moat 进化

核心概念：
- One Memory 的梦境引擎提炼 Insight
- Insight 生成 .moat/evolved_rules.json
- Moat 在下一次启动时加载并应用这些规则
- 实现"被动检查" → "主动进化"
"""
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class EvolvedRule:
    """进化规则"""
    id: str
    type: str  # "pain_weight" | "check_priority" | "new_check"
    module: str
    pattern: str
    confidence: float
    source_insight_id: str
    generated_at: str
    applied: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EvolutionEngine:
    """进化引擎

    将 One Memory 的 Insight 转换为 Moat 可执行的规则。
    """

    def __init__(self, project_root: Path, bridge: Any = None):
        self.project = project_root.resolve()
        self.moat_dir = self.project / ".moat"
        self.moat_dir.mkdir(exist_ok=True)
        self.evolved_rules_file = self.moat_dir / "evolved_rules.json"
        self.bridge = bridge

    def generate_evolved_rules(self) -> list[EvolvedRule]:
        """生成进化规则

        从 One Memory 的 Insights 生成 Moat 可执行的规则。
        """
        if not self.bridge:
            return []

        # 1. 查询未应用的 Insights
        insights = self.bridge.query_recent_insights(limit=50)

        if not insights:
            return []

        # 2. 转换为进化规则
        rules = []
        for insight in insights:
            rule = self._insight_to_rule(insight)
            if rule:
                rules.append(rule)

        # 3. 保存到文件
        self._save_rules(rules)

        # 4. 标记 Insights 已应用
        for rule in rules:
            self.bridge.mark_insight_applied(rule.source_insight_id)

        return rules

    def _insight_to_rule(self, insight: dict) -> EvolvedRule | None:
        """将 Insight 转换为进化规则

        Args:
            insight: One Memory 的 Insight

        Returns:
            EvolvedRule 或 None
        """
        insight_type = insight.get("type", "")
        module = insight.get("module", "")
        pattern = insight.get("pattern", "")
        confidence = insight.get("confidence", 0.0)
        insight_id = insight.get("id", "")

        # 映射 Insight 类型到规则类型
        if insight_type == "repeated_bug":
            rule_type = "pain_weight"
            rule = EvolvedRule(
                id=f"rule_{insight_id}",
                type=rule_type,
                module=module or "unknown",
                pattern=pattern,
                confidence=confidence,
                source_insight_id=insight_id,
                generated_at=datetime.now().isoformat(),
            )
            return rule

        elif insight_type == "architectural_weakness":
            rule_type = "check_priority"
            rule = EvolvedRule(
                id=f"rule_{insight_id}",
                type=rule_type,
                module=module or "unknown",
                pattern=pattern,
                confidence=confidence,
                source_insight_id=insight_id,
                generated_at=datetime.now().isoformat(),
            )
            return rule

        elif insight_type == "evolution_suggestion":
            rule_type = "new_check"
            rule = EvolvedRule(
                id=f"rule_{insight_id}",
                type=rule_type,
                module=module or "unknown",
                pattern=pattern,
                confidence=confidence,
                source_insight_id=insight_id,
                generated_at=datetime.now().isoformat(),
            )
            return rule

        return None

    def _save_rules(self, rules: list[EvolvedRule]):
        """保存规则到文件"""
        rules_data = {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "rules": [rule.to_dict() for rule in rules],
            "metadata": {
                "total_rules": len(rules),
                "rule_types": list(set(r.type for r in rules)),
                "affected_modules": list(set(r.module for r in rules)),
            },
        }

        self.evolved_rules_file.write_text(
            json.dumps(rules_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def load_evolved_rules(self) -> dict[str, Any] | None:
        """加载进化规则

        Returns:
            规则字典或 None
        """
        if not self.evolved_rules_file.exists():
            return None

        try:
            return json.loads(self.evolved_rules_file.read_text(encoding="utf-8"))
        except Exception:
            return None


class EnhancedPainScorer:
    """增强版痛觉评分器（加载进化规则）

    在原有 PainScorer 基础上，根据进化规则动态调整权重。
    """

    def __init__(self, evolution_engine: EvolutionEngine | None = None):
        self.evolution_engine = evolution_engine
        self.evolved_rules: dict[str, Any] | None = None

        if evolution_engine:
            self.evolved_rules = evolution_engine.load_evolved_rules()

    def calculate(self, error: dict[str, Any], base_score: float) -> float:
        """计算增强后的 Pain Score

        Args:
            error: 错误信息
            base_score: 基础 Pain Score

        Returns:
            调整后的 Pain Score
        """
        if not self.evolved_rules:
            return base_score

        # 查找匹配的规则
        module = self._extract_module(error.get("file", ""))
        error_type = error.get("type", "")

        for rule in self.evolved_rules.get("rules", []):
            if rule.get("applied"):
                continue

            # 检查规则是否匹配
            if self._rule_matches(rule, module, error_type):
                # 应用规则调整
                base_score = self._apply_rule(rule, base_score)

        return min(100.0, max(0.0, base_score))

    def _extract_module(self, file_path: str) -> str:
        """提取模块名"""
        parts = file_path.split("/")
        if len(parts) >= 2:
            return parts[-2]
        return file_path

    def _rule_matches(self, rule: dict, module: str, error_type: str) -> bool:
        """检查规则是否匹配"""
        rule_module = rule.get("module", "")
        rule_pattern = rule.get("pattern", "")

        # 模块匹配
        if rule_module and rule_module != module:
            return False

        # 模式匹配
        if rule_pattern:
            import fnmatch
            return fnmatch.fnmatch(error_type, rule_pattern)

        return True

    def _apply_rule(self, rule: dict, base_score: float) -> float:
        """应用规则调整分数"""
        rule_type = rule.get("type", "")
        confidence = rule.get("confidence", 0.5)

        if rule_type == "pain_weight":
            # 提高 Pain Score 权重
            multiplier = 1.0 + (confidence * 0.5)  # 最高 +50%
            return base_score * multiplier

        elif rule_type == "check_priority":
            # 提高检查优先级（也反映在 Pain Score 上）
            multiplier = 1.0 + (confidence * 0.3)  # 最高 +30%
            return base_score * multiplier

        elif rule_type == "new_check":
            # 新检查规则（暂时不调整分数，只记录）
            pass

        return base_score


def evolve_from_insights(project_root: str = ".", bridge: Any = None) -> list[EvolvedRule]:
    """从 Insights 生成进化规则（便捷函数）

    Args:
        project_root: 项目根目录
        bridge: SharedStorageBridge 实例

    Returns:
        生成的规则列表
    """
    root = Path(project_root).resolve()

    if not bridge:
        from moat.memory.bridge import SharedStorageBridge
        bridge = SharedStorageBridge(
            BridgeConfig(db_path=root / ".moat" / "memory.db")
        )
        bridge.initialize()

    engine = EvolutionEngine(root, bridge)
    return engine.generate_evolved_rules()


def load_enhanced_pain_scorer(project_root: str = ".") -> EnhancedPainScorer:
    """加载增强版 Pain Scorer（便捷函数）

    Args:
        project_root: 项目根目录

    Returns:
        EnhancedPainScorer 实例
    """
    from moat.memory.bridge import SharedStorageBridge

    root = Path(project_root).resolve()
    bridge = SharedStorageBridge(
        BridgeConfig(db_path=root / ".moat" / "memory.db")
    )
    bridge.initialize()

    engine = EvolutionEngine(root, bridge)
    return EnhancedPainScorer(engine)
