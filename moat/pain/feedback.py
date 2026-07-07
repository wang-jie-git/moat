"""Pain Score 自我校准模块

通过用户反馈闭环动态调整权重。
当用户标记某个错误为"误报（False Positive）"时，
系统降低该模式的权重；当用户确认是高优先级时，
系统提高权重。
"""
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass
class Feedback:
    """用户反馈"""
    id: str
    error_type: str
    file_pattern: str
    user_rating: str  # "false_positive" | "confirmed" | "low_priority" | "high_priority"
    timestamp: float
    context: dict[str, Any] | None = None


class FeedbackStore:
    """反馈存储"""

    def __init__(self, moat_dir: Path):
        self.moat_dir = moat_dir
        self.feedback_file = moat_dir / "feedback.json"
        self.feedback: list[Feedback] = []
        self._load()

    def _load(self):
        """加载反馈历史"""
        if self.feedback_file.exists():
            try:
                data = json.loads(self.feedback_file.read_text(encoding="utf-8"))
                self.feedback = [Feedback(**item) for item in data]
            except Exception:
                self.feedback = []

    def save(self):
        """保存反馈"""
        self.feedback_file.write_text(
            json.dumps([asdict(f) for f in self.feedback], indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def add_feedback(self, error_type: str, file_pattern: str, user_rating: str,
                     context: dict[str, Any] | None = None) -> Feedback:
        """添加反馈"""
        import time

        feedback = Feedback(
            id=f"fb_{int(time.time() * 1000)}",
            error_type=error_type,
            file_pattern=file_pattern,
            user_rating=user_rating,
            timestamp=time.time(),
            context=context,
        )
        self.feedback.append(feedback)
        self.save()
        return feedback

    def get_pattern_stats(self, error_type: str | None = None,
                          file_pattern: str | None = None) -> dict[str, Any]:
        """获取模式统计"""
        filtered = self.feedback

        if error_type:
            filtered = [f for f in filtered if f.error_type == error_type]
        if file_pattern:
            filtered = [f for f in filtered if self._match_pattern(f.file_pattern, file_pattern)]

        if not filtered:
            return {"count": 0, "false_positive_rate": 0.0}

        total = len(filtered)
        false_positives = sum(1 for f in filtered if f.user_rating == "false_positive")
        confirmed = sum(1 for f in filtered if f.user_rating == "confirmed")
        low_priority = sum(1 for f in filtered if f.user_rating == "low_priority")
        high_priority = sum(1 for f in filtered if f.user_rating == "high_priority")

        return {
            "count": total,
            "false_positive_rate": false_positives / total if total > 0 else 0.0,
            "confirmed_rate": confirmed / total if total > 0 else 0.0,
            "low_priority_rate": low_priority / total if total > 0 else 0.0,
            "high_priority_rate": high_priority / total if total > 0 else 0.0,
        }

    def _match_pattern(self, pattern: str, file_path: str) -> bool:
        """简单通配符匹配"""
        import fnmatch
        return fnmatch.fnmatch(file_path, pattern)


class AdaptivePainScorer:
    """自适应痛觉评分器（支持自我校准）"""

    # 基础权重
    BASE_WEIGHTS = {
        "core_business": 30,
        "auth_payment": 40,
        "api_endpoint": 20,
        "race_condition": 25,
        "syntax_error": 15,
        "missing_doc": 5,
        "third_party": -50,
    }

    def __init__(self, feedback_store: FeedbackStore | None = None,
                 core_areas: list[dict] | None = None):
        self.feedback_store = feedback_store or FeedbackStore(Path(".moat"))
        self.core_areas = core_areas or []
        self.weights = self.BASE_WEIGHTS.copy()
        self._calibrate()

    def _calibrate(self):
        """根据反馈历史校准权重"""
        if not self.feedback_store.feedback:
            return

        # 对每种错误类型进行校准
        error_types = set(f.error_type for f in self.feedback_store.feedback)

        for error_type in error_types:
            stats = self.feedback_store.get_pattern_stats(error_type=error_type)

            # 如果误报率 > 50%，降低权重
            if stats["false_positive_rate"] > 0.5 and stats["count"] >= 3:
                self.weights[error_type] = int(self.weights.get(error_type, 20) * 0.7)
            # 如果确认率 > 80%，提高权重
            elif stats["confirmed_rate"] > 0.8 and stats["count"] >= 3:
                self.weights[error_type] = int(self.weights.get(error_type, 20) * 1.3)

    def add_feedback(self, error_type: str, file_pattern: str, user_rating: str,
                     context: dict[str, Any] | None = None):
        """添加用户反馈并重新校准"""
        self.feedback_store.add_feedback(error_type, file_pattern, user_rating, context)
        self._calibrate()  # 重新校准

    def calculate(self, error: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        """计算痛觉评分（返回字典格式）"""
        context = context or {}
        score = 0.0
        factors = []

        file_path = error.get("file", "").lower()
        error_type = error.get("type", "").lower()
        message = error.get("message", "").lower()

        # 1. 核心业务文件检测
        if self._is_core_business(file_path, context):
            score += self.weights.get("core_business", 30)
            factors.append("核心业务文件")

        # 2. 鉴权/支付逻辑检测
        if self._is_critical_logic(file_path, error_type, message):
            score += self.weights.get("auth_payment", 40)
            factors.append("鉴权/支付逻辑")

        # 3. API 端点检测
        if self._is_api_endpoint(error_type, message):
            score += self.weights.get("api_endpoint", 20)
            factors.append("API 端点")

        # 4. 竞态条件检测
        if self._is_race_condition(error_type, message):
            score += self.weights.get("race_condition", 25)
            factors.append("竞态条件")

        # 5. 语法错误检测
        if self._is_syntax_error(error_type, message):
            score += self.weights.get("syntax_error", 15)
            factors.append("语法错误")

        # 6. 文档缺失检测
        if self._is_missing_doc(error_type, message):
            score += self.weights.get("missing_doc", 5)
            factors.append("文档缺失")

        # 7. 第三方代码检测（降低权重）
        if self._is_third_party(file_path):
            score += self.weights.get("third_party", -50)
            factors.append("第三方代码")

        # 限制在 0-100
        score = max(0.0, min(100.0, score))

        # 确定等级
        level = self._score_to_level(score)

        return {
            "score": round(score, 1),
            "level": level,
            "factors": factors,
            "weights_used": {k: v for k, v in self.weights.items() if v > 0},
        }

    def _is_core_business(self, file_path: str, context: dict) -> bool:
        """是否为核心业务文件"""
        for area in self.core_areas:
            pattern = area.get("pattern", "")
            if pattern and self._match_pattern(file_path, pattern):
                return True
        return any(kw in file_path for kw in {"auth", "login", "session", "token",
                                               "payment", "checkout", "billing"})

    def _is_critical_logic(self, file_path: str, error_type: str, message: str) -> bool:
        """是否为鉴权/支付逻辑"""
        keywords = {"auth", "login", "session", "token", "password", "credential",
                    "payment", "checkout", "billing"}
        return any(kw in file_path or kw in error_type or kw in message for kw in keywords)

    def _is_api_endpoint(self, error_type: str, message: str) -> bool:
        """是否为 API 端点"""
        indicators = {"api", "endpoint", "route", "handler", "controller"}
        return any(ind in error_type or ind in message for ind in indicators)

    def _is_race_condition(self, error_type: str, message: str) -> bool:
        """是否为竞态条件"""
        keywords = {"race", "pending", "lock", "mutex", "concurrent", "async", "await"}
        return any(kw in error_type or kw in message for kw in keywords)

    def _is_syntax_error(self, error_type: str, message: str) -> bool:
        """是否为语法错误"""
        return "syntax" in error_type or "语法" in error_type

    def _is_missing_doc(self, error_type: str, message: str) -> bool:
        """是否为文档缺失"""
        return "missing" in error_type or "缺失" in error_type or "缺少" in message

    def _is_third_party(self, file_path: str) -> bool:
        """是否为第三方代码"""
        return any(p in file_path for p in ("node_modules", ".venv", "venv", "site-packages"))

    def _match_pattern(self, file_path: str, pattern: str) -> bool:
        """通配符匹配"""
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


def submit_feedback(error_type: str, file_path: str, user_rating: str,
                    moat_dir: str | Path = ".moat", context: dict[str, Any] | None = None):
    """提交用户反馈（便捷函数）

    Args:
        error_type: 错误类型
        file_path: 文件路径
        user_rating: 用户评分（false_positive/confirmed/low_priority/high_priority）
        moat_dir: Moat 目录
        context: 上下文信息
    """
    moat_path = Path(moat_dir)
    store = FeedbackStore(moat_path)
    scorer = AdaptivePainScorer(store)
    scorer.add_feedback(error_type, file_path, user_rating, context)
    print(f"✅ 反馈已记录，权重已调整")


def get_feedback_stats(moat_dir: str | Path = ".moat", error_type: str | None = None) -> dict[str, Any]:
    """获取反馈统计（便捷函数）"""
    store = FeedbackStore(Path(moat_dir))
    return store.get_pattern_stats(error_type=error_type)
