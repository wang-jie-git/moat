"""痛觉评分模块 — 标准化错误危险系数

核心功能：
- Pain Score 计算（0-100）
- 错误危险等级评估
- 结构化 JSON 输出
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PainScore:
    """痛觉评分"""

    score: float  # 0-100
    level: str  # LOW/MEDIUM/HIGH/CRITICAL
    error: dict[str, Any]
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "level": self.level,
            "error": self.error,
            "context": self.context,
        }


class PainScorer:
    """痛觉评分器

    评分规则：
    - 核心业务文件：+30
    - 鉴权/支付逻辑：+40
    - API 端点：+20
    - 竞态条件：+25
    - 语法错误：+15
    - 文档缺失：+5
    - 第三方代码：-50（降低权重）

    变更风险维度（v1.3.0 新增）：
    - async/sync 签名变更：+40（影响所有调用方）
    - 消防水带模式：+35（create_task 返回值丢弃）
    - 删除函数：+30（影响调用方）
    - 高调用方影响：+20（>3 个调用方）
    """

    # 权重配置
    WEIGHTS = {
        "core_business": 30,
        "auth_payment": 40,
        "api_endpoint": 20,
        "race_condition": 25,
        "syntax_error": 15,
        "missing_doc": 5,
        "third_party": -50,
        # 变更风险维度（v1.3.0）
        "async_signature_change": 40,
        "fire_and_forget": 35,
        "function_deleted": 30,
        "high_caller_impact": 20,
    }

    # 核心业务关键词
    CORE_KEYWORDS = {
        "auth", "login", "session", "token", "payment", "checkout",
        "billing", "user", "account", "security",
    }

    # 鉴权/支付关键词
    CRITICAL_KEYWORDS = {
        "auth", "login", "session", "token", "password", "credential",
        "payment", "checkout", "billing", "stripe", "paypal",
    }

    # 竞态条件关键词
    RACE_KEYWORDS = {
        "race", "pending", "lock", "mutex", "concurrent",
        "async", "await", "promise", "deferred",
    }

    def __init__(self, core_areas: list[dict] | None = None):
        self.core_areas = core_areas or []

    def calculate(self, error: dict[str, Any], context: dict[str, Any] | None = None) -> PainScore:
        """计算错误危险系数

        Args:
            error: 错误信息
            context: 上下文信息

        Returns:
            PainScore 对象
        """
        context = context or {}
        score = 0.0
        factors = []

        file_path = error.get("file", "").lower()
        error_type = error.get("type", "").lower()
        message = error.get("message", "").lower()

        # 1. 核心业务文件检测
        if self._is_core_business(file_path, context):
            score += self.WEIGHTS["core_business"]
            factors.append("核心业务文件")

        # 2. 鉴权/支付逻辑检测
        if self._is_critical_logic(file_path, error_type, message):
            score += self.WEIGHTS["auth_payment"]
            factors.append("鉴权/支付逻辑")

        # 3. API 端点检测
        if self._is_api_endpoint(error_type, message):
            score += self.WEIGHTS["api_endpoint"]
            factors.append("API 端点")

        # 4. 竞态条件检测
        if self._is_race_condition(error_type, message):
            score += self.WEIGHTS["race_condition"]
            factors.append("竞态条件")

        # 5. 语法错误检测
        if self._is_syntax_error(error_type, message):
            score += self.WEIGHTS["syntax_error"]
            factors.append("语法错误")

        # 6. 文档缺失检测
        if self._is_missing_doc(error_type, message):
            score += self.WEIGHTS["missing_doc"]
            factors.append("文档缺失")

        # 7. 第三方代码检测（降低权重）
        if self._is_third_party(file_path):
            score += self.WEIGHTS["third_party"]
            factors.append("第三方代码")

        # 8. 变更风险维度（v1.3.0）
        if self._is_async_signature_change(error_type, message):
            score += self.WEIGHTS["async_signature_change"]
            factors.append("async/sync 签名变更")

        if self._is_fire_and_forget(error_type, message):
            score += self.WEIGHTS["fire_and_forget"]
            factors.append("消防水带模式")

        if self._is_function_deleted(error_type, message):
            score += self.WEIGHTS["function_deleted"]
            factors.append("删除函数")

        if self._is_high_caller_impact(error_type, message):
            score += self.WEIGHTS["high_caller_impact"]
            factors.append("高调用方影响")

        # 限制在 0-100
        score = max(0.0, min(100.0, score))

        # 确定等级
        level = self._score_to_level(score)

        return PainScore(
            score=score,
            level=level,
            error=error,
            context={"factors": factors, **(context or {})},
        )

    def _is_core_business(self, file_path: str, context: dict) -> bool:
        """是否为核心业务文件"""
        # 检查配置的核心区域
        for area in self.core_areas:
            pattern = area.get("pattern", "")
            if pattern and self._match_pattern(file_path, pattern):
                return True

        # 检查关键词
        return any(kw in file_path for kw in self.CORE_KEYWORDS)

    def _is_critical_logic(self, file_path: str, error_type: str, message: str) -> bool:
        """是否为鉴权/支付逻辑"""
        return any(kw in file_path or kw in error_type or kw in message
                   for kw in self.CRITICAL_KEYWORDS)

    def _is_api_endpoint(self, error_type: str, message: str) -> bool:
        """是否为 API 端点"""
        api_indicators = {"api", "endpoint", "route", "handler", "controller"}
        return any(ind in error_type or ind in message for ind in api_indicators)

    def _is_race_condition(self, error_type: str, message: str) -> bool:
        """是否为竞态条件"""
        return any(kw in error_type or kw in message for kw in self.RACE_KEYWORDS)

    def _is_syntax_error(self, error_type: str, message: str) -> bool:
        """是否为语法错误"""
        return "syntax" in error_type or "语法" in error_type or "语法错误" in message

    def _is_missing_doc(self, error_type: str, message: str) -> bool:
        """是否为文档缺失"""
        return "missing" in error_type or "缺失" in error_type or "缺少" in message

    def _is_third_party(self, file_path: str) -> bool:
        """是否为第三方代码"""
        return any(p in file_path for p in (
            "node_modules", ".venv", "venv", "site-packages",
            "third_party", "external",
        ))

    def _is_async_signature_change(self, error_type: str, message: str) -> bool:
        """是否为 async/sync 签名变更"""
        return "async_signature" in error_type or "签名变更" in message

    def _is_fire_and_forget(self, error_type: str, message: str) -> bool:
        """是否为消防水带模式"""
        return "fire_and_forget" in error_type or "消防水带" in message

    def _is_function_deleted(self, error_type: str, message: str) -> bool:
        """是否为删除函数"""
        return "deleted" in error_type or "删除" in error_type or "被删除" in message

    def _is_high_caller_impact(self, error_type: str, message: str) -> bool:
        """是否为高调用方影响"""
        return "caller_impact" in error_type or "调用方" in message

    def _match_pattern(self, file_path: str, pattern: str) -> bool:
        """简单通配符匹配"""
        import fnmatch
        return fnmatch.fnmatch(file_path, pattern)

    def _score_to_level(self, score: float) -> str:
        """分数转等级"""
        if score >= 75:
            return "CRITICAL"
        elif score >= 50:
            return "HIGH"
        elif score >= 25:
            return "MEDIUM"
        else:
            return "LOW"


def calculate_pain_score(error: dict[str, Any], core_areas: list[dict] | None = None,
                         context: dict[str, Any] | None = None) -> dict[str, Any]:
    """计算痛觉评分（便捷函数）

    Args:
        error: 错误信息
        core_areas: 核心业务区域配置
        context: 上下文信息

    Returns:
        痛觉评分字典
    """
    scorer = PainScorer(core_areas)
    pain = scorer.calculate(error, context)
    return pain.to_dict()


def calculate_total_pain(errors: list[dict[str, Any]], core_areas: list[dict] | None = None) -> dict[str, Any]:
    """计算总痛觉评分

    Args:
        errors: 错误列表
        core_areas: 核心业务区域配置

    Returns:
        总痛觉评分
    """
    scorer = PainScorer(core_areas)

    scores = []
    for error in errors:
        pain = scorer.calculate(error)
        scores.append(pain.to_dict())

    # 计算总分（加权平均，最高 CRITICAL 权重更高）
    total_score = sum(s["score"] for s in scores)
    avg_score = total_score / len(scores) if scores else 0.0

    # 确定整体等级
    if any(s["level"] == "CRITICAL" for s in scores):
        overall_level = "CRITICAL"
    elif any(s["level"] == "HIGH" for s in scores):
        overall_level = "HIGH"
    elif any(s["level"] == "MEDIUM" for s in scores):
        overall_level = "MEDIUM"
    else:
        overall_level = "LOW"

    return {
        "total_score": round(avg_score, 1),
        "overall_level": overall_level,
        "error_count": len(errors),
        "scores": scores,
        "recommended_action": _get_recommended_action(overall_level),
    }


def _get_recommended_action(level: str) -> str:
    """获取建议操作"""
    actions = {
        "CRITICAL": "立即修复（停止当前工作，优先处理）",
        "HIGH": "尽快修复（本工作周期内处理）",
        "MEDIUM": "计划修复（下一个迭代处理）",
        "LOW": "可选修复（不影响核心功能）",
    }
    return actions.get(level, "评估后决定")
