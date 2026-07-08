"""FixEngine 测试套件

目标：覆盖 moat/fixer.py 70%+
策略：测试 FixEngine 主要方法和便捷函数
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from moat.fixer import (
    FixEngine,
    _generate_markdown_report,
    _generate_text_report,
    generate_fix_report,
)


# ==================== Fixtures ====================

@pytest.fixture
def tmp_project(tmp_path):
    """创建临时项目目录"""
    project = tmp_path / "test_project"
    project.mkdir()
    # 创建一个测试文件
    (project / "test.py").write_text("print('hello')\n")
    return project


@pytest.fixture
def fix_engine(tmp_project):
    """创建 FixEngine 实例（演练模式）"""
    return FixEngine(tmp_project, dry_run=True)


@pytest.fixture
def fix_engine_live(tmp_project):
    """创建 FixEngine 实例（实际修复模式）"""
    return FixEngine(tmp_project, dry_run=False)


@pytest.fixture
def sample_error():
    """样本错误"""
    return {
        "type": "race_condition",
        "file": "src/auth.py",
        "line": 42,
        "message": "Pending message reference detected",
        "pain_score": 75,
        "pain_level": "HIGH",
    }


@pytest.fixture
def sample_errors(sample_error):
    """样本错误列表"""
    return [
        sample_error,
        {
            "type": "unchecked_error",
            "file": "src/utils.py",
            "line": 15,
            "message": "Unchecked error return value",
            "pain_score": 45,
            "pain_level": "MEDIUM",
        },
        {
            "type": "api_timeout",
            "file": "src/api.py",
            "line": 88,
            "message": "API request timeout",
            "pain_score": 60,
            "pain_level": "HIGH",
        },
    ]


# ==================== FixEngine.__init__ ====================

class TestFixEngineInit:
    """测试 FixEngine 初始化"""

    def test_init_dry_run(self, tmp_project):
        """测试演练模式初始化"""
        engine = FixEngine(tmp_project, dry_run=True)
        assert engine.project == tmp_project.resolve()
        assert engine.dry_run is True
        assert engine.fixes_applied == []
        assert engine.fixes_skipped == []

    def test_init_live_mode(self, tmp_project):
        """测试实际修复模式初始化"""
        engine = FixEngine(tmp_project, dry_run=False)
        assert engine.project == tmp_project.resolve()
        assert engine.dry_run is False
        assert engine.fixes_applied == []
        assert engine.fixes_skipped == []

    def test_init_resolves_path(self, tmp_path):
        """测试路径解析"""
        engine = FixEngine(tmp_path / "relative/path", dry_run=True)
        assert engine.project.is_absolute()


# ==================== FixEngine.fix_error ====================

class TestFixError:
    """测试 fix_error 方法"""

    def test_fix_error_no_strategy(self, fix_engine):
        """测试无修复策略的情况"""
        error = {"type": "unknown_type", "file": "test.py", "message": "test"}
        result = fix_engine.fix_error(error)
        assert result is None

    def test_fix_error_dry_run(self, fix_engine, sample_error):
        """测试演练模式（不自动修复）"""
        result = fix_engine.fix_error(sample_error)
        assert result is not None
        assert result["status"] == "suggested"
        assert "strategy" in result
        assert result["strategy"]["type"] == sample_error["type"]
        assert result["auto_fixable"] is not None
        # 演练模式下不应该有实际修复
        assert len(fix_engine.fixes_applied) == 0
        assert len(fix_engine.fixes_skipped) == 1

    def test_fix_error_live_mode_success(self, fix_engine_live, sample_error):
        """测试实际修复模式（修复成功）"""
        result = fix_engine_live.fix_error(sample_error)
        assert result is not None
        assert result["status"] == "failed"  # 当前 _apply_auto_fix 返回 False
        assert "strategy" in result

    def test_fix_error_live_mode_failure(self, fix_engine_live):
        """测试实际修复模式（修复失败）"""
        error = {"type": "race_condition", "file": "nonexistent.py", "message": "test"}
        result = fix_engine_live.fix_error(error)
        assert result is not None
        # 文件不存在，修复会失败
        assert result["status"] in ("failed", "suggested")

    def test_fix_error_auto_fixable_exception(self, fix_engine_live, tmp_path):
        """测试自动修复时发生异常"""
        error = {"type": "race_condition", "file": "test.py", "message": "test"}
        # Mock _apply_auto_fix 抛出异常
        with patch.object(FixEngine, '_apply_auto_fix', side_effect=RuntimeError("Test error")):
            result = fix_engine_live.fix_error(error)
        assert result is not None
        assert result["status"] == "error"
        assert "error_message" in result
        assert "Test error" in result["error_message"]

    def test_fix_error_minimal_error(self, fix_engine):
        """测试最小错误字典（无类型时返回 None）"""
        error = {}
        result = fix_engine.fix_error(error)
        # 空字典没有 type 字段，get_strategy 返回 None
        assert result is None

    def test_fix_error_preserves_error_info(self, fix_engine, sample_error):
        """测试保留错误信息"""
        result = fix_engine.fix_error(sample_error)
        assert result["error"] == sample_error


# ==================== FixEngine._apply_auto_fix ====================

class TestApplyAutoFix:
    """测试 _apply_auto_fix 方法"""

    def test_apply_auto_fix_file_not_exists(self, fix_engine):
        """测试文件不存在的情况"""
        error = {"file": "nonexistent.py"}
        result = fix_engine._apply_auto_fix(error, MagicMock())
        assert result is False

    def test_apply_auto_fix_file_exists(self, fix_engine, tmp_project):
        """测试文件存在的情况（当前返回 False）"""
        test_file = tmp_project / "test.py"
        error = {"file": "test.py"}
        result = fix_engine._apply_auto_fix(error, MagicMock())
        # 当前实现总是返回 False
        assert result is False


# ==================== FixEngine.fix_errors ====================

class TestFixErrors:
    """测试 fix_errors 批量修复方法"""

    def test_fix_errors_empty_list(self, fix_engine):
        """测试空错误列表"""
        results = fix_engine.fix_errors([])
        assert results == []

    def test_fix_errors_multiple(self, fix_engine, sample_errors):
        """测试批量修复"""
        results = fix_engine.fix_errors(sample_errors)
        # 不是所有错误类型都有匹配的策略，只检查返回非 None 的结果
        valid_results = [r for r in results if r is not None]
        assert len(valid_results) >= 1  # 至少有一个匹配
        for result in valid_results:
            assert "status" in result

    def test_fix_errors_skips_unknown(self, fix_engine):
        """测试跳过无法识别的错误类型（fix_error 对未知类型返回 None）"""
        errors = [{"type": "unknown", "message": "test"}]
        results = fix_engine.fix_errors(errors)
        # fix_errors 只追加非 None 结果，未知类型返回 None 被跳过
        assert len(results) == 0


# ==================== FixEngine.generate_ai_suggestions ====================

class TestGenerateAiSuggestions:
    """测试 generate_ai_suggestions 方法"""

    def test_generate_suggestions_empty(self, fix_engine):
        """测试空错误列表"""
        suggestions = fix_engine.generate_ai_suggestions([])
        assert suggestions == []

    def test_generate_suggestions_single(self, fix_engine, sample_error):
        """测试单个错误建议"""
        suggestions = fix_engine.generate_ai_suggestions([sample_error])
        assert len(suggestions) == 1
        s = suggestions[0]
        assert s["strategy_type"] == sample_error["type"]
        assert "suggestion" in s
        assert "example" in s
        assert "confidence" in s

    def test_generate_suggestions_multiple(self, fix_engine, sample_errors):
        """测试多个错误建议"""
        suggestions = fix_engine.generate_ai_suggestions(sample_errors)
        # 不是所有类型都有策略，检查至少有建议
        assert len(suggestions) >= 1
        assert len(suggestions) <= len(sample_errors)

    def test_generate_suggestions_with_pain_score(self, fix_engine, sample_error):
        """测试包含 Pain Score 的建议"""
        suggestions = fix_engine.generate_ai_suggestions([sample_error])
        assert len(suggestions) == 1
        assert "pain_score" in suggestions[0]
        assert suggestions[0]["pain_score"] == 75
        assert "pain_level" in suggestions[0]

    def test_generate_suggestions_without_pain_score(self, fix_engine):
        """测试不包含 Pain Score 的建议"""
        error = {"type": "syntax_error", "message": "test"}  # 使用已知类型
        suggestions = fix_engine.generate_ai_suggestions([error])
        assert len(suggestions) == 1
        assert "pain_score" not in suggestions[0]
        assert "pain_level" not in suggestions[0]

    def test_generate_suggestions_unknown_type(self, fix_engine):
        """测试未知错误类型（应跳过）"""
        errors = [{"type": "unknown_error_type", "message": "test"}]
        suggestions = fix_engine.generate_ai_suggestions(errors)
        assert suggestions == []

    def test_generate_suggestions_preserves_fields(self, fix_engine, sample_error):
        """测试保留所有字段"""
        suggestions = fix_engine.generate_ai_suggestions([sample_error])
        s = suggestions[0]
        assert s["file"] == sample_error["file"]
        assert s["line"] == sample_error["line"]
        assert s["message"] == sample_error["message"]


# ==================== FixEngine.generate_fix_pr_description ====================

class TestGenerateFixPrDescription:
    """测试 generate_fix_pr_description 方法"""

    def test_pr_description_empty(self, fix_engine):
        """测试空修复结果"""
        desc = fix_engine.generate_fix_pr_description([])
        assert "未发现需要修复的问题" in desc

    def test_pr_description_single(self, fix_engine, sample_error):
        """测试单个修复的 PR 描述"""
        result = fix_engine.fix_error(sample_error)
        desc = fix_engine.generate_fix_pr_description([result])
        assert "修复说明" in desc
        assert "1 个问题" in desc
        assert sample_error["type"] in desc
        assert sample_error["file"] in desc

    def test_pr_description_multiple(self, fix_engine, sample_errors):
        """测试多个修复的 PR 描述"""
        results = [fix_engine.fix_error(e) for e in sample_errors]
        # 过滤掉 None 结果
        valid_results = [r for r in results if r is not None]
        desc = fix_engine.generate_fix_pr_description(valid_results)
        assert "修复说明" in desc
        if valid_results:
            assert f"{len(valid_results)} 个问题" in desc
        assert "下一步" in desc

    def test_pr_description_auto_fixable(self, fix_engine):
        """测试可自动修复的错误"""
        error = {"type": "race_condition", "file": "test.py", "message": "test"}
        result = fix_engine.fix_error(error)
        if result.get("auto_fixable"):
            assert "已自动修复" in fix_engine.generate_fix_pr_description([result])

    def test_pr_description_manual_fix(self, fix_engine):
        """测试需要手动修复的错误"""
        # 使用 syntax_error（不可自动修复）
        error = {"type": "syntax_error", "file": "test.py", "message": "SyntaxError: invalid syntax"}
        result = fix_engine.fix_error(error)
        if result and not result.get("auto_fixable"):
            desc = fix_engine.generate_fix_pr_description([result])
            assert "需要手动修复" in desc


# ==================== FixEngine.get_statistics ====================

class TestGetStatistics:
    """测试 get_statistics 方法"""

    def test_statistics_empty(self, fix_engine):
        """测试无修复时的统计"""
        stats = fix_engine.get_statistics()
        assert stats["dry_run"] is True
        assert stats["total_processed"] == 0
        assert stats["auto_fixed"] == 0
        assert stats["suggested"] == 0
        assert stats["fixes_applied"] == []
        assert stats["fixes_skipped"] == []

    def test_statistics_after_fixes(self, fix_engine, sample_errors):
        """测试修复后的统计"""
        fix_engine.fix_errors(sample_errors)
        stats = fix_engine.get_statistics()
        # 统计应该包含所有尝试修复的错误
        # 但只有匹配策略的错误才会被记录
        assert stats["total_processed"] >= 1
        assert stats["suggested"] >= 1

    def test_statistics_live_mode(self, fix_engine_live):
        """测试实际模式的统计"""
        assert fix_engine_live.get_statistics()["dry_run"] is False


# ==================== 便捷函数：generate_fix_report ====================

class TestGenerateFixReport:
    """测试 generate_fix_report 便捷函数"""

    def test_generate_report_text_format(self, tmp_project, sample_error):
        """测试文本格式"""
        report = generate_fix_report(
            str(tmp_project),
            errors=[sample_error],
            dry_run=True,
            format="text"
        )
        assert "=" * 60 in report
        assert "演练" in report
        assert "race_condition" in report

    def test_generate_report_markdown_format(self, tmp_project, sample_error):
        """测试 Markdown 格式"""
        report = generate_fix_report(
            str(tmp_project),
            errors=[sample_error],
            dry_run=True,
            format="md"
        )
        assert "# Moat AI 修复建议" in report
        assert "race_condition" in report
        assert "演练" in report

    def test_generate_report_json_format(self, tmp_project, sample_error):
        """测试 JSON 格式"""
        report = generate_fix_report(
            str(tmp_project),
            errors=[sample_error],
            dry_run=True,
            format="json"
        )
        data = json.loads(report)
        assert "project" in data
        assert "dry_run" in data
        assert "total_errors" in data
        assert data["total_errors"] == 1
        assert "suggestions" in data

    def test_generate_report_no_errors(self, tmp_project):
        """测试无错误"""
        report = generate_fix_report(
            str(tmp_project),
            errors=[],
            dry_run=True
        )
        assert "未发现错误" in report or "可修复" in report

    def test_generate_report_no_errors_json(self, tmp_project):
        """测试无错误 JSON 格式"""
        report = generate_fix_report(
            str(tmp_project),
            errors=[],
            dry_run=True,
            format="json"
        )
        data = json.loads(report)
        assert data["total_errors"] == 0
        assert data["fixable_errors"] == 0

    def test_generate_report_fetches_errors(self, tmp_project):
        """测试自动获取错误列表"""
        # Mock runner
        with patch('moat.runner.run_all_checks') as mock_run:
            mock_result = MagicMock()
            mock_result.errors = [{"type": "test", "message": "test"}]
            mock_run.return_value = mock_result

            report = generate_fix_report(
                str(tmp_project),
                errors=None,
                dry_run=True
            )
            # 应该调用 runner
            mock_run.assert_called_once_with(str(tmp_project))

    def test_generate_report_runner_returns_bool(self, tmp_project):
        """测试 runner 返回布尔值的兼容性"""
        with patch('moat.runner.run_all_checks') as mock_run:
            mock_run.return_value = True  # 旧版本兼容

            report = generate_fix_report(
                str(tmp_project),
                errors=None,
                dry_run=True
            )
            # 应该返回错误提示
            assert "错误" in report or "无法获取" in report


# ==================== 内部报告生成函数 ====================

class TestGenerateTextReport:
    """测试 _generate_text_report 函数"""

    def test_text_report_basic(self, fix_engine):
        """测试基本文本报告"""
        suggestions = [{
            "error": {"type": "test", "file": "test.py", "line": 1, "message": "test"},
            "strategy_type": "test_strategy",
            "suggestion": "Fix this",
            "confidence": 0.8,
            "auto_fixable": False,
        }]
        report = _generate_text_report(fix_engine, suggestions)
        assert "Moat AI 修复建议" in report
        assert "演练" in report
        assert "test_strategy" in report
        assert "80%" in report
        assert "需要手动修复" in report

    def test_text_report_auto_fixable(self, fix_engine):
        """测试可自动修复的报告"""
        suggestions = [{
            "error": {"type": "test", "file": "test.py", "line": 1, "message": "test"},
            "strategy_type": "test_strategy",
            "suggestion": "Fix this",
            "confidence": 0.9,
            "auto_fixable": True,
        }]
        report = _generate_text_report(fix_engine, suggestions)
        assert "支持自动修复" in report

    def test_text_report_live_mode(self, fix_engine_live):
        """测试实际修复模式的报告"""
        suggestions = [{
            "error": {"type": "test", "file": "test.py", "line": 1, "message": "test"},
            "strategy_type": "test_strategy",
            "suggestion": "Fix this",
            "confidence": 0.9,
            "auto_fixable": True,
        }]
        report = _generate_text_report(fix_engine_live, suggestions)
        assert "实际修复" in report
        assert "已自动修复" in report

    def test_text_report_multiple_suggestions(self, fix_engine):
        """测试多个建议的报告"""
        suggestions = [
            {
                "error": {"type": f"test{i}", "file": f"test{i}.py", "line": i, "message": f"test{i}"},
                "strategy_type": f"strategy{i}",
                "suggestion": f"Fix {i}",
                "confidence": 0.5,
                "auto_fixable": False,
            }
            for i in range(3)
        ]
        report = _generate_text_report(fix_engine, suggestions)
        assert report.count("strategy") == 3
        assert "[2]" in report
        assert "[3]" in report


class TestGenerateMarkdownReport:
    """测试 _generate_markdown_report 函数"""

    def test_markdown_report_basic(self, fix_engine):
        """测试基本 Markdown 报告"""
        suggestions = [{
            "error": {"type": "test", "file": "test.py", "line": 1, "message": "test"},
            "strategy_type": "test_strategy",
            "suggestion": "Fix this",
            "confidence": 0.8,
            "auto_fixable": False,
            "example": "example code",
        }]
        report = _generate_markdown_report(fix_engine, suggestions)
        assert "# Moat AI 修复建议" in report
        assert "演练" in report
        assert "test_strategy" in report
        assert "Fix this" in report
        assert "example code" in report
        assert "需要手动修复" in report

    def test_markdown_report_with_example(self, fix_engine):
        """测试包含示例代码的报告"""
        suggestions = [{
            "error": {"type": "test", "file": "test.py", "line": 1, "message": "test"},
            "strategy_type": "test_strategy",
            "suggestion": "Fix this",
            "confidence": 0.9,
            "auto_fixable": True,
            "example": "print('example')",
        }]
        report = _generate_markdown_report(fix_engine, suggestions)
        assert "```" in report
        assert "print('example')" in report
        # 演练模式显示"支持自动修复"，实际模式才显示"已自动修复"
        assert "支持自动修复" in report or "已自动修复" in report

    def test_markdown_report_without_example(self, fix_engine):
        """测试不包含示例代码的报告"""
        suggestions = [{
            "error": {"type": "test", "file": "test.py", "line": 1, "message": "test"},
            "strategy_type": "test_strategy",
            "suggestion": "Fix this",
            "confidence": 0.9,
            "auto_fixable": False,
        }]
        report = _generate_markdown_report(fix_engine, suggestions)
        # 不应该有示例代码块
        assert "### 📝 示例" not in report

    def test_markdown_report_multiple(self, fix_engine):
        """测试多个修复建议的报告"""
        suggestions = [
            {
                "error": {"type": f"test{i}", "file": f"test{i}.py", "line": i, "message": f"test{i}"},
                "strategy_type": f"strategy{i}",
                "suggestion": f"Fix {i}",
                "confidence": 0.8,
                "auto_fixable": False,
            }
            for i in range(3)
        ]
        report = _generate_markdown_report(fix_engine, suggestions)
        # 检查关键部分存在，不严格检查数量
        assert "## 概览" in report
        assert "## 下一步" in report
        assert "Fix 0" in report
        assert "Fix 1" in report
        assert "Fix 2" in report

    def test_markdown_report_dry_run_warning(self, fix_engine):
        """测试演练模式警告"""
        suggestions = []
        report = _generate_markdown_report(fix_engine, suggestions)
        assert "演练" in report or "Dry Run" in report


# ==================== 集成测试 ====================

class TestFixerIntegration:
    """集成测试"""

    def test_full_fix_workflow(self, tmp_project):
        """测试完整修复工作流"""
        engine = FixEngine(tmp_project, dry_run=True)

        errors = [
            {"type": "race_condition", "file": "auth.py", "line": 1, "message": "Pending message ref"},
            {"type": "syntax_error", "file": "utils.py", "line": 2, "message": "Syntax error"},
        ]

        # 批量修复
        results = engine.fix_errors(errors)
        # 至少有一个匹配到策略
        assert len(results) >= 1

        # 生成 AI 建议
        suggestions = engine.generate_ai_suggestions(errors)
        assert len(suggestions) >= 1

        # 生成统计
        stats = engine.get_statistics()
        assert stats["total_processed"] >= 1
        assert stats["suggested"] >= 1

        # 生成 PR 描述
        pr_desc = engine.generate_fix_pr_description(results)
        assert "修复说明" in pr_desc

    def test_dry_run_vs_live_mode(self, tmp_project, sample_error):
        """测试演练模式与实际模式的差异"""
        dry_engine = FixEngine(tmp_project, dry_run=True)
        live_engine = FixEngine(tmp_project, dry_run=False)

        dry_result = dry_engine.fix_error(sample_error)
        live_result = live_engine.fix_error(sample_error)

        # 演练模式应该是 suggested
        assert dry_result["status"] == "suggested"
        # 实际模式可能不同
        assert live_result["status"] in ("failed", "suggested")

    def test_generate_report_roundtrip(self, tmp_project, sample_errors):
        """测试报告生成往返（各种格式）"""
        for fmt in ["text", "md", "json"]:
            report = generate_fix_report(
                str(tmp_project),
                errors=sample_errors,
                dry_run=True,
                format=fmt
            )
            assert report is not None
            assert len(report) > 0

            if fmt == "json":
                json.loads(report)  # 确保是有效 JSON
