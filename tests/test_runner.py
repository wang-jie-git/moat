"""Runner 集成测试

覆盖 moat.runner 中未充分测试的功能：
- MoatResult 类（add_check_result, add_legacy_errors, summary 等）
- _run_legacy_check 函数
- _record_check_metrics 函数
- run_all_checks 集成测试
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, create_autospec
import time

from moat.runner import MoatResult, run_all_checks, _run_legacy_check


class TestMoatResult:
    """MoatResult 类测试"""

    def test_initial_state(self):
        """初始状态"""
        result = MoatResult()
        assert result.passed == 0
        assert result.failed == 0
        assert result.skipped == 0
        assert result.warnings == 0
        assert result.errors == []
        assert result.duration >= 0

    def test_add_check_result_pass(self):
        """添加通过结果"""
        result = MoatResult()
        check_result = MagicMock()
        check_result.type = "pass"
        check_result.to_dict.return_value = {"type": "pass"}

        result.add_check_result(check_result)
        assert result.passed == 1
        assert result.failed == 0

    def test_add_check_result_fail(self):
        """添加失败结果"""
        result = MoatResult()
        check_result = MagicMock()
        check_result.type = "fail"
        check_result.to_dict.return_value = {"type": "fail", "message": "error"}

        result.add_check_result(check_result)
        assert result.failed == 1
        assert len(result.errors) == 1

    def test_add_check_result_warn(self):
        """添加警告结果"""
        result = MoatResult()
        check_result = MagicMock()
        check_result.type = "warn"
        check_result.to_dict.return_value = {"type": "warn", "message": "warning"}

        result.add_check_result(check_result)
        assert result.warnings == 1
        assert len(result.errors) == 1

    def test_add_check_result_skip(self):
        """添加跳过结果"""
        result = MoatResult()
        check_result = MagicMock()
        check_result.type = "skip"
        check_result.to_dict.return_value = {}

        result.add_check_result(check_result)
        assert result.skipped == 1

    def test_add_legacy_errors_pass(self):
        """添加旧风格通过错误"""
        result = MoatResult()
        errors = [{"type": "syntax_ok"}]
        result.add_legacy_errors(errors)
        assert result.passed == 1
        assert result.errors == []

    def test_add_legacy_errors_fail(self):
        """添加旧风格失败错误"""
        result = MoatResult()
        errors = [{"type": "syntax_error", "message": "bad syntax"}]
        result.add_legacy_errors(errors)
        assert result.failed == 1
        assert len(result.errors) == 1

    def test_add_legacy_errors_skip(self):
        """添加旧风格跳过"""
        result = MoatResult()
        errors = [{"type": "skip_test"}]
        result.add_legacy_errors(errors)
        assert result.skipped == 1

    def test_add_legacy_errors_mixed(self):
        """混合错误类型"""
        result = MoatResult()
        errors = [
            {"type": "check1_ok"},
            {"type": "check2_error"},
            {"type": "skip_check3"},
            {"type": "check4_error"},
        ]
        result.add_legacy_errors(errors)
        assert result.passed == 1
        assert result.failed == 2
        assert result.skipped == 1
        assert len(result.errors) == 2

    def test_duration_calculation(self):
        """耗时计算"""
        result = MoatResult()
        time.sleep(0.01)
        result.end_time = time.time()
        assert result.duration >= 0.01

    def test_total_checks(self):
        """总检查数"""
        result = MoatResult()
        result.passed = 10
        result.failed = 2
        result.skipped = 3
        result.warnings = 1
        assert result.total_checks == 16

    def test_summary_format(self):
        """总结格式"""
        result = MoatResult()
        result.passed = 10
        result.failed = 2
        result.skipped = 3
        result.warnings = 1
        result.end_time = result.start_time + 1.5

        summary = result.summary()
        assert "通过: 10" in summary
        assert "失败: 2" in summary
        assert "跳过: 3" in summary
        assert "警告: 1" in summary

    def test_is_success_no_failures(self):
        """无失败时成功"""
        result = MoatResult()
        result.passed = 10
        result.warnings = 5
        result.skipped = 2
        assert result.is_success() is True

    def test_is_success_with_failures(self):
        """有失败时不成功"""
        result = MoatResult()
        result.passed = 10
        result.failed = 1
        result.warnings = 5
        assert result.is_success() is False

    def test_end_time_not_set(self):
        """未设置结束时间"""
        result = MoatResult()
        # end_time 为 0，使用当前时间
        duration = result.duration
        assert duration >= 0


class TestRunLegacyCheck:
    """旧风格检查测试"""

    def test_run_legacy_check_syntax(self):
        """运行语法检查"""
        mock_module = MagicMock()
        mock_module.run_syntax_check.return_value = [{"type": "syntax_ok"}]

        result = _run_legacy_check(mock_module, "语法检查", Path("."))
        mock_module.run_syntax_check.assert_called_once()
        assert result == [{"type": "syntax_ok"}]

    def test_run_legacy_check_import(self):
        """运行 import 检查"""
        mock_module = MagicMock()
        mock_module.run_import_check.return_value = [{"type": "import_ok"}]

        result = _run_legacy_check(mock_module, "import检查", Path("."))
        mock_module.run_import_check.assert_called_once()

    def test_run_legacy_check_file(self):
        """运行文件完整性检查"""
        mock_module = MagicMock()
        mock_module.run_file_check.return_value = []

        result = _run_legacy_check(mock_module, "文件完整性", Path("."))
        mock_module.run_file_check.assert_called_once()

    def test_run_legacy_check_modules(self):
        """运行核心模块检查"""
        mock_module = MagicMock()
        mock_module.run_modules_check.return_value = [{"type": "module_ok"}]

        result = _run_legacy_check(mock_module, "核心模块", Path("."))
        mock_module.run_modules_check.assert_called_once()

    def test_run_legacy_check_subsystems(self):
        """运行子系统检查"""
        mock_module = MagicMock()
        mock_module.run_subsystems_check.return_value = []

        result = _run_legacy_check(mock_module, "子系统", Path("."))
        mock_module.run_subsystems_check.assert_called_once()

    def test_run_legacy_check_behavior(self):
        """运行行为检查"""
        mock_module = MagicMock()
        mock_module.run_behavior_check.return_value = []

        result = _run_legacy_check(mock_module, "行为", Path("."))
        mock_module.run_behavior_check.assert_called_once()

    def test_run_legacy_check_unknown(self):
        """未知检查名称"""
        mock_module = MagicMock()
        result = _run_legacy_check(mock_module, "未知检查", Path("."))
        assert result == []

    def test_run_legacy_check_exception(self):
        """检查运行异常"""
        mock_module = MagicMock()
        mock_module.run_syntax_check.side_effect = Exception("Test error")

        result = _run_legacy_check(mock_module, "语法检查", Path("."))
        assert len(result) == 1
        assert result[0]["type"] == "error"
        assert "Test error" in result[0]["message"]


class TestRunAllChecksIntegration:
    """run_all_checks 集成测试"""

    @patch("moat.runner.detect_project_type")
    @patch("moat.runner.create_check_instances")
    def test_run_all_checks_empty_project(self, mock_checks, mock_detect, tmp_path):
        """空项目"""
        mock_detect.return_value = {}
        mock_checks.return_value = []

        result = run_all_checks(str(tmp_path))
        assert isinstance(result, MoatResult)
        assert result.total_checks == 0

    @patch("moat.runner.detect_project_type")
    @patch("moat.runner.create_check_instances")
    def test_run_all_checks_with_new_style_check(self, mock_checks, mock_detect, tmp_path):
        """运行新风格检查"""
        from moat.checks.base import Check, CheckResult

        mock_detect.return_value = {"python": True}

        # 创建一个模拟检查
        mock_check = MagicMock(spec=Check)
        mock_check.name = "test_check"
        mock_check.run.return_value = [
            CheckResult("pass", "测试通过"),
            CheckResult("fail", "测试失败", level="ERROR")
        ]

        mock_checks.return_value = [("test_check", mock_check)]

        result = run_all_checks(str(tmp_path))
        assert result.passed == 1
        assert result.failed == 1
        assert result.total_checks == 2

    @patch("moat.runner.detect_project_type")
    @patch("moat.runner.create_check_instances")
    def test_run_all_checks_with_legacy_check(self, mock_checks, mock_detect, tmp_path):
        """运行旧风格检查"""
        mock_detect.return_value = {"python": True}

        mock_module = MagicMock()
        mock_module.run_syntax_check.return_value = [{"type": "syntax_ok"}]

        mock_checks.return_value = [("语法检查", mock_module)]

        result = run_all_checks(str(tmp_path))
        assert result.passed == 1

    @patch("moat.runner.detect_project_type")
    @patch("moat.runner.create_check_instances")
    def test_run_all_checks_mixed_checks(self, mock_checks, mock_detect, tmp_path):
        """混合新旧风格检查"""
        from moat.checks.base import Check, CheckResult

        mock_detect.return_value = {"python": True, "typescript": True}

        # 新风格检查
        mock_check = MagicMock(spec=Check)
        mock_check.run.return_value = [CheckResult("pass", "新风格检查")]

        # 旧风格检查
        mock_module = MagicMock()
        mock_module.run_import_check.return_value = [{"type": "import_ok"}]

        mock_checks.return_value = [
            ("新风格", mock_check),
            ("import检查", mock_module),
        ]

        result = run_all_checks(str(tmp_path))
        assert result.passed == 2
        assert result.total_checks == 2

    @patch("moat.runner.detect_project_type")
    @patch("moat.runner.create_check_instances")
    @patch("moat.runner._record_check_metrics")
    def test_run_all_checks_records_metrics(self, mock_metrics, mock_checks, mock_detect, tmp_path):
        """记录进化指标"""
        mock_detect.return_value = {}
        mock_checks.return_value = []

        # 创建 .moat 目录
        moat_dir = tmp_path / ".moat"
        moat_dir.mkdir()

        result = run_all_checks(str(tmp_path))
        mock_metrics.assert_called_once_with(tmp_path, result)

    @patch("moat.runner.detect_project_type")
    @patch("moat.runner.create_check_instances")
    def test_run_all_checks_output_summary(self, mock_checks, mock_detect, tmp_path, capsys):
        """输出总结"""
        mock_detect.return_value = {"python": True}
        mock_checks.return_value = []

        result = run_all_checks(str(tmp_path))
        captured = capsys.readouterr()

        assert "Moat" in captured.out
        assert "结果:" in captured.out

    def test_run_all_checks_project_root_resolution(self, tmp_path):
        """项目根目录解析"""
        # 不 mock，直接测试路径解析
        with patch("moat.runner.detect_project_type") as mock_detect, \
             patch("moat.runner.create_check_instances") as mock_checks:

            mock_detect.return_value = {}
            mock_checks.return_value = []

            result = run_all_checks(str(tmp_path / "subdir"))
            assert isinstance(result, MoatResult)


class TestRecordCheckMetrics:
    """记录检查指标测试"""

    @patch("moat.evolution_metrics.EvolutionTracker")
    def test_record_metrics_success(self, mock_tracker_cls, tmp_path):
        """成功记录指标"""
        mock_tracker = MagicMock()
        mock_tracker_cls.return_value = mock_tracker

        moat_dir = tmp_path / ".moat"
        moat_dir.mkdir()

        result = MoatResult()
        result.passed = 8
        result.failed = 2
        result.warnings = 1
        result.skipped = 0

        from moat.runner import _record_check_metrics
        _record_check_metrics(tmp_path, result)

        # 验证记录了指标
        assert mock_tracker.record_refactor_success.called

    @patch("moat.evolution_metrics.EvolutionTracker")
    def test_record_metrics_with_failures(self, mock_tracker_cls, tmp_path):
        """有失败时记录误报"""
        mock_tracker = MagicMock()
        mock_tracker_cls.return_value = mock_tracker

        moat_dir = tmp_path / ".moat"
        moat_dir.mkdir()

        result = MoatResult()
        result.passed = 5
        result.failed = 3
        result.errors = [
            {"type": "test_error", "level": "ERROR", "file": "test.py", "message": "test"}
        ]

        from moat.runner import _record_check_metrics
        _record_check_metrics(tmp_path, result)

        # 应记录误报
        assert mock_tracker.record_false_positive.called

    @patch("moat.evolution_metrics.EvolutionTracker")
    def test_record_metrics_no_moat_dir(self, mock_tracker_cls, tmp_path):
        """无 .moat 目录时不记录"""
        from moat.runner import _record_check_metrics

        result = MoatResult()
        _record_check_metrics(tmp_path, result)

        # 不应创建 tracker
        assert not mock_tracker_cls.called

    @patch("moat.evolution_metrics.EvolutionTracker")
    def test_record_metrics_import_error(self, mock_tracker_cls, tmp_path):
        """EvolutionTracker 导入失败时静默处理"""
        mock_tracker_cls.side_effect = ImportError("not available")

        moat_dir = tmp_path / ".moat"
        moat_dir.mkdir()

        result = MoatResult()

        from moat.runner import _record_check_metrics
        # 不应抛出异常
        _record_check_metrics(tmp_path, result)
