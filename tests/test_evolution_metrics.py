"""Tests for Evolution Metrics System"""
import pytest
import time
from pathlib import Path
from moat.evolution_metrics import (
    EvolutionMetric,
    EvolutionMetricsStore,
    EvolutionEvaluator,
    EvolutionTracker,
)


@pytest.fixture
def temp_moat_dir(tmp_path):
    """创建临时 moat 目录"""
    moat_dir = tmp_path / ".moat"
    moat_dir.mkdir()
    return moat_dir


@pytest.fixture
def metrics_store(temp_moat_dir):
    """创建指标存储"""
    return EvolutionMetricsStore(temp_moat_dir)


@pytest.fixture
def tracker(temp_moat_dir):
    """创建追踪器"""
    return EvolutionTracker(temp_moat_dir)


class TestEvolutionMetric:
    """测试进化指标"""

    def test_create_metric(self):
        """测试创建指标"""
        metric = EvolutionMetric(
            id="test_1",
            type="refactor_success",
            value=0.8,
            weight=0.25,
            timestamp=time.time(),
            context={"test": True},
            is_positive=True,
        )
        assert metric.id == "test_1"
        assert metric.value == 0.8
        assert metric.is_positive is True


class TestEvolutionMetricsStore:
    """测试指标存储"""

    def test_add_and_save(self, metrics_store):
        """测试添加和保存指标"""
        metric = EvolutionMetric(
            id="test_1",
            type="refactor_success",
            value=0.8,
            weight=0.25,
            timestamp=time.time(),
        )
        metrics_store.add_metric(metric)
        assert len(metrics_store.metrics) == 1

    def test_get_recent_metrics(self, metrics_store):
        """测试获取最近指标"""
        now = time.time()
        for i in range(5):
            metric = EvolutionMetric(
                id=f"test_{i}",
                type="refactor_success",
                value=0.5 + i * 0.1,
                weight=0.25,
                timestamp=now - (i * 3600),  # 每小时一个
            )
            metrics_store.add_metric(metric)

        # 获取最近 3 小时的指标
        recent = metrics_store.get_recent_metrics(hours=3)
        assert len(recent) == 3  # 最近 3 个


class TestEvolutionEvaluator:
    """测试进化评估器"""

    def test_evaluate_with_sufficient_data(self, tracker):
        """测试有足够数据时的评估"""
        now = time.time()

        # 添加正向指标
        for i in range(10):
            metric = EvolutionMetric(
                id=f"positive_{i}",
                type="refactor_success",
                value=0.8,
                weight=0.25,
                timestamp=now - (i * 3600),
                is_positive=True,
            )
            tracker.metrics_store.add_metric(metric)

        # 添加少量负向指标
        metric = EvolutionMetric(
            id="negative_1",
            type="false_positive_rate",
            value=1.0,
            weight=-0.15,
            timestamp=now,
            is_positive=False,
        )
        tracker.metrics_store.add_metric(metric)

        evaluation = tracker.evaluator.evaluate_evolution(window_hours=24)

        assert evaluation["status"] == "success"
        assert "total_score" in evaluation
        assert "dimension_scores" in evaluation
        assert "fatigue_status" in evaluation

    def test_detect_neural_fatigue(self, tracker):
        """测试神经衰弱检测"""
        now = time.time()

        # 添加大量误报（负向维度且得分高）
        for i in range(20):
            metric = EvolutionMetric(
                id=f"fp_{i}",
                type="false_positive_rate",
                value=1.0,  # 高分
                weight=-0.15,
                timestamp=now - (i * 3600),
                is_positive=False,
            )
            tracker.metrics_store.add_metric(metric)

        # 添加一些正向指标
        for i in range(5):
            metric = EvolutionMetric(
                id=f"pos_{i}",
                type="refactor_success",
                value=0.5,
                weight=0.25,
                timestamp=now - (i * 3600),
                is_positive=True,
            )
            tracker.metrics_store.add_metric(metric)

        evaluation = tracker.evaluator.evaluate_evolution(window_hours=24)
        fatigue = evaluation.get("fatigue_status", {})

        # 应该检测到负向维度占比高（1/5 = 0.2）
        # 由于权重影响，negative_ratio 应该 > 0.15
        assert fatigue.get("negative_ratio", 0) >= 0.15


class TestEvolutionTracker:
    """测试进化追踪器"""

    def test_record_refactor_success(self, tracker):
        """测试记录重构成功"""
        metric = tracker.record_refactor_success(
            files_changed=5,
            tests_passed=True,
            pain_score_before=65.0,
            pain_score_after=25.0,
        )

        assert metric.type == "refactor_success"
        assert 0 <= metric.value <= 1.0
        assert len(tracker.metrics_store.metrics) == 1

    def test_record_performance_improvement(self, tracker):
        """测试记录性能提升"""
        metric = tracker.record_performance_improvement(
            metric_name="api_response_time",
            before=250.0,
            after=80.0,
        )

        assert metric.type == "performance_improvement"
        assert metric.value > 0  # 应该为正
        assert metric.context["improvement_percent"] > 0

    def test_record_bug_fix(self, tracker):
        """测试记录 Bug 修复"""
        metric = tracker.record_bug_fix(
            bug_type="race_condition",
            fix_time_seconds=3600,  # 1 小时
            pain_score=75.0,
        )

        assert metric.type == "bug_fix_time"
        assert 0 <= metric.value <= 1.0

    def test_record_false_positive(self, tracker):
        """测试记录误报"""
        metric = tracker.record_false_positive(
            error_type="race_condition",
            file_path="src/utils.py",
        )

        assert metric.type == "false_positive_rate"
        assert metric.is_positive is False
        assert metric.weight < 0  # 负向权重

    def test_get_evolution_report(self, tracker):
        """测试生成进化报告"""
        # 添加一些指标
        tracker.record_refactor_success(
            files_changed=3,
            tests_passed=True,
            pain_score_before=50.0,
            pain_score_after=30.0,
        )

        report = tracker.get_evolution_report(window_hours=24)

        assert "进化指标报告" in report
        assert "综合得分" in report
        assert "各维度得分" in report
        assert "神经衰弱检测" in report
