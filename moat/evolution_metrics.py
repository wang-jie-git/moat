"""进化指标系统 — 定义"进化方向性"，防止"神经衰弱"

核心目标：
1. 不只记录 Bug，也记录"成功"
2. 定义什么叫做"好的进化"
3. 动态调整监控策略（收紧 vs 鼓励）

进化指标：
- 重构成功率（Refactor Success Rate）
- 性能提升率（Performance Improvement Rate）
- Bug 修复时效（Bug Fix Time）
- 误报率（False Positive Rate）
- 开发效率（Dev Velocity）
- Pain Score 趋势（Pain Score Trend）
"""

import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass
class EvolutionMetric:
    """进化指标"""
    id: str
    type: str  # "refactor_success" | "performance_improvement" | "bug_fix" | "false_positive" | "dev_velocity"
    value: float
    weight: float  # 指标权重（0-1）
    timestamp: float
    context: dict[str, Any] | None = None
    is_positive: bool = True  # 是否为正向指标


@dataclass
class EvolutionWindow:
    """进化时间窗口"""
    start: float
    end: float
    metrics: list[EvolutionMetric]
    summary: dict[str, Any]


class EvolutionMetricsStore:
    """进化指标存储"""

    def __init__(self, moat_dir: Path):
        self.moat_dir = moat_dir
        self.metrics_file = moat_dir / "evolution_metrics.json"
        self.metrics: list[EvolutionMetric] = []
        self._load()

    def _load(self):
        """加载历史指标"""
        if self.metrics_file.exists():
            try:
                data = json.loads(self.metrics_file.read_text(encoding="utf-8"))
                self.metrics = [EvolutionMetric(**item) for item in data]
            except Exception:
                self.metrics = []

    def save(self):
        """保存指标"""
        self.metrics_file.write_text(
            json.dumps([asdict(m) for m in self.metrics], indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def add_metric(self, metric: EvolutionMetric) -> None:
        """添加指标"""
        self.metrics.append(metric)
        # 只保留最近 1000 条
        self.metrics = self.metrics[-1000:]
        self.save()

    def get_metrics_in_window(self, start: float, end: float) -> list[EvolutionMetric]:
        """获取时间窗口内的指标"""
        return [m for m in self.metrics if start <= m.timestamp <= end]

    def get_recent_metrics(self, hours: int = 24) -> list[EvolutionMetric]:
        """获取最近的指标"""
        cutoff = time.time() - (hours * 3600)
        return self.get_metrics_in_window(cutoff, time.time())


class EvolutionEvaluator:
    """进化评估器

    核心职责：
    1. 评估进化方向性（正向 vs 负向）
    2. 识别"神经衰弱"风险
    3. 推荐监控策略调整
    """

    # 指标权重
    METRIC_WEIGHTS = {
        "refactor_success": 0.25,      # 重构成功率
        "performance_improvement": 0.20,  # 性能提升率
        "bug_fix_time": 0.20,           # Bug 修复时效
        "false_positive_rate": -0.15,   # 误报率（负向）
        "dev_velocity": 0.20,           # 开发效率
    }

    # 阈值定义
    THRESHOLDS = {
        "neural_fatigue_warning": 0.3,   # 神经衰弱警告（负向指标占比超过 30%）
        "neural_fatigue_critical": 0.5,  # 神经衰弱临界
        "encourage_mode_threshold": 0.7, # 鼓励模式阈值（正向指标占比超过 70%）
    }

    def __init__(self, metrics_store: EvolutionMetricsStore):
        self.store = metrics_store

    def evaluate_evolution(self, window_hours: int = 24) -> dict[str, Any]:
        """评估进化方向

        Args:
            window_hours: 评估时间窗口（小时）

        Returns:
            评估结果
        """
        metrics = self.store.get_recent_metrics(window_hours)

        if not metrics:
            return {
                "status": "insufficient_data",
                "score": 0.0,
                "message": "数据不足，无法评估",
            }

        # 1. 计算各维度得分
        dimension_scores = self._calculate_dimension_scores(metrics)

        # 2. 计算综合得分
        total_score = sum(
            score * self.METRIC_WEIGHTS.get(dim, 0)
            for dim, score in dimension_scores.items()
        )

        # 3. 检测"神经衰弱"
        fatigue_status = self._detect_neural_fatigue(dimension_scores)

        # 4. 生成建议
        recommendation = self._generate_recommendation(total_score, fatigue_status, dimension_scores)

        return {
            "status": "success",
            "window_hours": window_hours,
            "total_score": round(total_score, 3),
            "dimension_scores": dimension_scores,
            "fatigue_status": fatigue_status,
            "recommendation": recommendation,
            "metrics_count": len(metrics),
        }

    def _calculate_dimension_scores(self, metrics: list[EvolutionMetric]) -> dict[str, float]:
        """计算各维度得分（0-1）"""
        dimensions = {
            "refactor_success": [],
            "performance_improvement": [],
            "bug_fix_time": [],
            "false_positive_rate": [],
            "dev_velocity": [],
        }

        for m in metrics:
            if m.type in dimensions:
                dimensions[m.type].append(m.value)

        scores = {}
        for dim, values in dimensions.items():
            if not values:
                scores[dim] = 0.5  # 默认中性
            else:
                avg = sum(values) / len(values)
                # 归一化到 0-1
                scores[dim] = max(0.0, min(1.0, avg))

        return scores

    def _detect_neural_fatigue(self, dimension_scores: dict[str, float]) -> dict[str, Any]:
        """检测"神经衰弱"

        当负向指标（如误报率）占比过高时，系统会变得越来越保守，
        导致开发效率下降。
        """
        # 方法1：基于维度得分的负向占比
        negative_dimensions = 0
        total_dimensions = len(dimension_scores)

        for dim, score in dimension_scores.items():
            weight = self.METRIC_WEIGHTS.get(dim, 0)
            if weight < 0 and score > 0.5:  # 负向维度且得分偏高
                negative_dimensions += 1

        dimension_ratio = negative_dimensions / total_dimensions if total_dimensions > 0 else 0.0

        # 方法2：基于负向权重的影响
        negative_weight_sum = 0
        total_weight_sum = 0

        for dim, score in dimension_scores.items():
            weight = abs(self.METRIC_WEIGHTS.get(dim, 0))
            total_weight_sum += weight
            if self.METRIC_WEIGHTS.get(dim, 0) < 0:
                negative_weight_sum += weight * score  # 负向维度得分越高，影响越大

        weight_ratio = negative_weight_sum / total_weight_sum if total_weight_sum > 0 else 0.0

        # 综合两种方法的平均值
        negative_ratio = (dimension_ratio + weight_ratio) / 2

        # 判断状态
        if negative_ratio >= self.THRESHOLDS["neural_fatigue_critical"]:
            status = "critical"
            message = "⚠️  系统神经衰弱严重！负向指标过高，建议降低 Pain Score 阈值"
        elif negative_ratio >= self.THRESHOLDS["neural_fatigue_warning"]:
            status = "warning"
            message = "⚡ 系统趋向保守，建议调整策略"
        elif negative_ratio <= (1 - self.THRESHOLDS["encourage_mode_threshold"]) / 2:
            status = "encourage"
            message = "✅ 进化方向良好，建议保持并鼓励创新"
        else:
            status = "normal"
            message = "👍 进化状态正常"

        return {
            "status": status,
            "negative_ratio": round(negative_ratio, 3),
            "dimension_ratio": round(dimension_ratio, 3),
            "weight_ratio": round(weight_ratio, 3),
            "message": message,
        }

    def _generate_recommendation(
        self,
        total_score: float,
        fatigue_status: dict[str, Any],
        dimension_scores: dict[str, float],
    ) -> dict[str, Any]:
        """生成策略建议"""
        recommendations = []

        # 基于疲劳状态建议
        if fatigue_status["status"] == "critical":
            recommendations.append({
                "action": "reduce_pain_threshold",
                "priority": "high",
                "description": "降低 Pain Score 阈值（例如从 50 降到 40），避免过度拦截",
                "config_change": {"pain_threshold": 40},
            })
            recommendations.append({
                "action": "increase_false_positive_tolerance",
                "priority": "high",
                "description": "提高误报容忍度（允许 3 次误报后再调整权重）",
                "config_change": {"false_positive_tolerance": 3},
            })

        elif fatigue_status["status"] == "warning":
            recommendations.append({
                "action": "adjust_pain_weights",
                "priority": "medium",
                "description": "轻微降低核心业务/鉴权类错误的权重",
                "config_change": {"weight_adjustment": {"core_business": -5, "auth_payment": -5}},
            })

        elif fatigue_status["status"] == "encourage":
            recommendations.append({
                "action": "enable_innovation_mode",
                "priority": "low",
                "description": "鼓励创新：降低对实验性代码的拦截强度",
                "config_change": {"experimental_code_tolerance": True},
            })

        # 基于维度得分建议
        if dimension_scores.get("false_positive_rate", 0) > 0.5:
            recommendations.append({
                "action": "review_false_positives",
                "priority": "medium",
                "description": "误报率过高，建议检查最近引入的检查规则",
            })

        if dimension_scores.get("dev_velocity", 0) < 0.3:
            recommendations.append({
                "action": "optimize_check_speed",
                "priority": "medium",
                "description": "开发效率偏低，建议优化检查速度或减少检查项",
            })

        return {
            "overall_score": round(total_score, 3),
            "actions": recommendations,
        }


class EvolutionTracker:
    """进化追踪器

    负责追踪项目的进化历程，记录"成功"和"失败"。
    """

    def __init__(self, moat_dir: Path):
        self.moat_dir = moat_dir
        self.metrics_store = EvolutionMetricsStore(moat_dir)
        self.evaluator = EvolutionEvaluator(self.metrics_store)

    def record_refactor_success(
        self,
        files_changed: int,
        tests_passed: bool,
        pain_score_before: float,
        pain_score_after: float,
        context: dict[str, Any] | None = None,
    ) -> EvolutionMetric:
        """记录重构成功

        Args:
            files_changed: 变更文件数
            tests_passed: 测试是否通过
            pain_score_before: 重构前 Pain Score
            pain_score_after: 重构后 Pain Score
            context: 额外上下文

        Returns:
            创建的指标
        """
        # 计算成功得分（0-1）
        score = 0.0

        # 1. 测试通过（基础分 0.5）
        if tests_passed:
            score += 0.5

        # 2. Pain Score 降低（0-0.5）
        if pain_score_before > 0:
            pain_improvement = (pain_score_before - pain_score_after) / pain_score_before
            score += min(0.5, max(0, pain_improvement * 0.5))

        metric = EvolutionMetric(
            id=f"refactor_{int(time.time() * 1000)}",
            type="refactor_success",
            value=score,
            weight=0.25,
            timestamp=time.time(),
            context={
                "files_changed": files_changed,
                "tests_passed": tests_passed,
                "pain_score_before": pain_score_before,
                "pain_score_after": pain_score_after,
                **(context or {}),
            },
            is_positive=True,
        )

        self.metrics_store.add_metric(metric)
        return metric

    def record_performance_improvement(
        self,
        metric_name: str,
        before: float,
        after: float,
        unit: str = "ms",
        context: dict[str, Any] | None = None,
    ) -> EvolutionMetric:
        """记录性能提升

        Args:
            metric_name: 指标名称（如 "api_response_time"）
            before: 优化前数值
            after: 优化后数值
            unit: 单位
            context: 额外上下文

        Returns:
            创建的指标
        """
        if before <= 0:
            score = 0.0
        else:
            improvement_ratio = (before - after) / before
            score = min(1.0, max(0.0, improvement_ratio))

        metric = EvolutionMetric(
            id=f"perf_{int(time.time() * 1000)}",
            type="performance_improvement",
            value=score,
            weight=0.20,
            timestamp=time.time(),
            context={
                "metric_name": metric_name,
                "before": before,
                "after": after,
                "unit": unit,
                "improvement_percent": round((before - after) / before * 100, 2) if before > 0 else 0,
                **(context or {}),
            },
            is_positive=True,
        )

        self.metrics_store.add_metric(metric)
        return metric

    def record_bug_fix(
        self,
        bug_type: str,
        fix_time_seconds: float,
        pain_score: float,
        context: dict[str, Any] | None = None,
    ) -> EvolutionMetric:
        """记录 Bug 修复

        Args:
            bug_type: Bug 类型
            fix_time_seconds: 修复耗时（秒）
            pain_score: Bug 的 Pain Score
            context: 额外上下文

        Returns:
            创建的指标
        """
        # 修复时效得分（修复越快得分越高，0-1）
        # 假设 1 小时是最佳，24 小时是最差
        if fix_time_seconds <= 3600:
            time_score = 1.0
        elif fix_time_seconds >= 86400:
            time_score = 0.0
        else:
            time_score = 1.0 - ((fix_time_seconds - 3600) / (86400 - 3600))

        # Bug 严重性加权（高 Pain Score 的 Bug 修复得分更高）
        severity_multiplier = 1.0 + (pain_score / 100.0)

        score = min(1.0, time_score * severity_multiplier)

        metric = EvolutionMetric(
            id=f"bugfix_{int(time.time() * 1000)}",
            type="bug_fix_time",
            value=score,
            weight=0.20,
            timestamp=time.time(),
            context={
                "bug_type": bug_type,
                "fix_time_seconds": fix_time_seconds,
                "pain_score": pain_score,
                **(context or {}),
            },
            is_positive=True,
        )

        self.metrics_store.add_metric(metric)
        return metric

    def record_false_positive(
        self,
        error_type: str,
        file_path: str,
        context: dict[str, Any] | None = None,
    ) -> EvolutionMetric:
        """记录误报

        Args:
            error_type: 错误类型
            file_path: 文件路径
            context: 额外上下文

        Returns:
            创建的指标
        """
        # 误报是负向指标，但需要记录以避免"神经衰弱"
        metric = EvolutionMetric(
            id=f"fp_{int(time.time() * 1000)}",
            type="false_positive_rate",
            value=1.0,  # 误报是负面事件
            weight=-0.15,  # 负向权重
            timestamp=time.time(),
            context={
                "error_type": error_type,
                "file_path": file_path,
                **(context or {}),
            },
            is_positive=False,
        )

        self.metrics_store.add_metric(metric)
        return metric

    def get_evolution_report(self, window_hours: int = 24) -> str:
        """生成进化报告

        Args:
            window_hours: 报告时间窗口

        Returns:
            格式化报告
        """
        evaluation = self.evaluator.evaluate_evolution(window_hours)

        lines = [
            "=" * 60,
            "  进化指标报告",
            f"  时间窗口: {window_hours} 小时",
            "=" * 60,
            "",
            f"📊 综合得分: {evaluation.get('total_score', 0):.3f} / 1.000",
            "",
        ]

        # 各维度得分
        dimensions = evaluation.get("dimension_scores", {})
        lines.append("📈 各维度得分:")
        for dim, score in dimensions.items():
            status = "🟢" if score >= 0.7 else "🟡" if score >= 0.4 else "🔴"
            lines.append(f"   {status} {dim}: {score:.2f}")

        lines.append("")

        # 神经衰弱检测
        fatigue = evaluation.get("fatigue_status", {})
        lines.extend([
            "🧠 神经衰弱检测:",
            f"   状态: {fatigue.get('status', 'unknown')}",
            f"   负向指标占比: {fatigue.get('negative_ratio', 0):.1%}",
            f"   {fatigue.get('message', '')}",
            "",
        ])

        # 建议
        recommendation = evaluation.get("recommendation", {})
        if recommendation.get("actions"):
            lines.append("💡 建议:")
            for action in recommendation["actions"]:
                priority_icon = "🔴" if action["priority"] == "high" else "🟡" if action["priority"] == "medium" else "🟢"
                lines.append(f"   {priority_icon} [{action['action']}] {action['description']}")

        lines.extend([
            "",
            "=" * 60,
        ])

        return "\n".join(lines)
