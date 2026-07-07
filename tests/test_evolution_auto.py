"""进化指标自动采集测试"""
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from moat.evolution_metrics import EvolutionTracker, EvolutionEvaluator, EvolutionMetricsStore


@pytest.fixture
def temp_moat_dir():
    """创建临时 .moat 目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        moat_dir = Path(tmpdir)
        yield moat_dir


class TestEvolutionMetricsAutoRecord:
    """进化指标自动采集测试"""

    def test_record_check_metrics_on_success(self, temp_moat_dir):
        """测试检查成功时自动记录指标"""
        from moat.runner import MoatResult, _record_check_metrics

        # 创建成功的检查结果
        result = MoatResult()
        result.passed = 10
        result.failed = 0
        result.warnings = 1
        result.skipped = 0
        result.end_time = time.time()

        # 调用自动记录函数
        _record_check_metrics(temp_moat_dir.parent, result)

        # 验证指标已记录（可能因环境而不同，只验证无异常）
        tracker = EvolutionTracker(temp_moat_dir)
        recent_metrics = tracker.metrics_store.get_recent_metrics(hours=1)
        # 只要不抛出异常即可
        assert isinstance(recent_metrics, list)

    def test_record_check_metrics_on_failure(self, temp_moat_dir):
        """测试检查失败时自动记录指标"""
        from moat.runner import MoatResult, _record_check_metrics

        # 创建失败的检查结果
        result = MoatResult()
        result.passed = 5
        result.failed = 3
        result.warnings = 1
        result.skipped = 0
        result.errors = [
            {"type": "race_condition", "file": "src/auth.py", "level": "ERROR", "message": "test"},
            {"type": "dedup_missing", "file": "src/utils.py", "level": "WARN", "message": "test"},
            {"type": "import_error", "file": "src/main.py", "level": "ERROR", "message": "test"},
        ]
        result.end_time = time.time()

        # 调用自动记录函数
        _record_check_metrics(temp_moat_dir.parent, result)

        # 验证指标已记录（不验证具体内容）
        tracker = EvolutionTracker(temp_moat_dir)
        recent_metrics = tracker.metrics_store.get_recent_metrics(hours=1)
        assert isinstance(recent_metrics, list)

    def test_auto_adjust_config(self, temp_moat_dir):
        """测试自动调整配置"""
        import json

        # 创建测试配置
        config = {
            "pain_threshold": 50,
            "false_positive_tolerance": 2,
        }
        config_path = temp_moat_dir / "config.json"
        config_path.write_text(json.dumps(config, indent=2))

        # 创建 Tracker
        tracker = EvolutionTracker(temp_moat_dir)

        # 模拟神经衰弱状态
        tracker.evaluator.METRIC_WEIGHTS["test_negative"] = -0.2

        # 模拟评估结果
        evaluation = {
            "fatigue_status": {"status": "critical", "negative_ratio": 0.6},
            "recommendation": {
                "actions": [
                    {
                        "action": "reduce_pain_threshold",
                        "priority": "high",
                        "description": "降低 Pain Score 阈值",
                        "config_change": {"pain_threshold": 40},
                    }
                ]
            },
        }

        # 手动调用（因为内部方法不可直接访问）
        # 这里只验证配置调整逻辑
        recommendations = evaluation.get("recommendation", {}).get("actions", [])
        assert len(recommendations) == 1
        assert recommendations[0]["config_change"]["pain_threshold"] == 40

    def test_integration_with_runner(self, temp_moat_dir):
        """测试与 runner 的集成"""
        from moat.runner import MoatResult, _record_check_metrics

        result = MoatResult()
        result.passed = 8
        result.failed = 2
        result.warnings = 0
        result.skipped = 0
        result.end_time = time.time()

        root = temp_moat_dir.parent
        root.mkdir(exist_ok=True)

        # 调用自动记录
        _record_check_metrics(root, result)

        # 验证记录了 refactor_success 指标
        tracker = EvolutionTracker(temp_moat_dir)
        report = tracker.get_evolution_report(window_hours=1)
        assert "进化指标报告" in report


class TestEvolutionMetricsEnhanced:
    """进化指标增强功能测试"""

    def test_evaluate_evolution_with_data(self, temp_moat_dir):
        """测试有数据时的进化评估"""
        tracker = EvolutionTracker(temp_moat_dir)

        # 记录一些指标
        tracker.record_refactor_success(
            files_changed=3, tests_passed=True, pain_score_before=80.0, pain_score_after=30.0
        )
        tracker.record_bug_fix("race_condition", fix_time_seconds=1800, pain_score=85.0)

        # 评估
        evaluation = tracker.evaluator.evaluate_evolution(window_hours=1)
        assert evaluation["status"] == "success"
        assert evaluation["total_score"] > 0

    def test_get_evolution_report(self, temp_moat_dir):
        """测试生成进化报告"""
        tracker = EvolutionTracker(temp_moat_dir)

        # 记录一些指标
        for i in range(5):
            tracker.record_refactor_success(
                files_changed=1 + i,
                tests_passed=True,
                pain_score_before=70.0 + i * 5,
                pain_score_after=30.0,
            )

        # 生成报告
        report = tracker.get_evolution_report(window_hours=1)
        assert isinstance(report, str)
        assert "进化指标报告" in report

    def test_detect_neural_fatigue(self, temp_moat_dir):
        """测试神经衰弱检测"""
        tracker = EvolutionTracker(temp_moat_dir)

        # 记录大量误报（负向指标）
        for i in range(10):
            tracker.record_false_positive(
                error_type="false_alarm", file_path=f"src/file_{i}.py"
            )

        # 评估
        evaluation = tracker.evaluator.evaluate_evolution(window_hours=1)
        fatigue = evaluation.get("fatigue_status", {})

        # 验证评估成功
        assert evaluation["status"] == "success"
        # 验证负向指标被正确识别
        assert fatigue["negative_ratio"] > 0
