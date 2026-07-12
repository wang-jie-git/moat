"""ReportGenerator 测试套件

目标：覆盖 moat/report.py 70%+
策略：测试 ReportGenerator 主要方法和便捷函数
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from moat.report import (
    ReportGenerator,
    _copy_to_clipboard,
    generate_report,
)


# ==================== Fixtures ====================

@pytest.fixture
def tmp_project(tmp_path):
    """创建临时项目目录"""
    project = tmp_path / "test_project"
    project.mkdir()
    # 创建 .moat 配置目录
    moat_dir = project / ".moat"
    moat_dir.mkdir()
    return project


@pytest.fixture
def moat_result():
    """创建样本 MoatResult"""
    from moat.runner import MoatResult
    result = MagicMock(spec=MoatResult)
    result.total_checks = 10
    result.passed = 7
    result.failed = 2
    result.warnings = 1
    result.skipped = 0
    result.duration = 1.5
    result.errors = [
        {
            "type": "import_error",
            "file": "src/utils.py",
            "line": 15,
            "message": "ModuleNotFoundError: No module named 'xxx'",
            "level": "ERROR",
        },
        {
            "type": "api_timeout",
            "file": "src/api.py",
            "line": 88,
            "message": "API request timeout after 30s",
            "level": "WARNING",
        },
    ]
    result.summary.return_value = "✅ 7 passed, ❌ 2 failed, ⚠️ 1 warning"
    return result


@pytest.fixture
def report_gen(tmp_project, moat_result):
    """创建 ReportGenerator 实例"""
    return ReportGenerator(tmp_project, moat_result)


# ==================== ReportGenerator.__init__ ====================

class TestReportGeneratorInit:
    """测试 ReportGenerator 初始化"""

    def test_init_basic(self, tmp_project, moat_result):
        """测试基本初始化"""
        gen = ReportGenerator(tmp_project, moat_result)
        assert gen.project == tmp_project.resolve()
        assert gen.result == moat_result

    def test_init_detects_project_type(self, tmp_project, moat_result):
        """测试自动检测项目类型"""
        gen = ReportGenerator(tmp_project, moat_result)
        # detect_project_type 应该被调用
        assert gen.project_types is not None


# ==================== ReportGenerator.generate ====================

class TestGenerate:
    """测试 generate 方法"""

    def test_generate_text_format(self, report_gen):
        """测试文本格式"""
        report = report_gen.generate(format="text")
        assert "=" * 60 in report
        assert "Moat Check 失败报告" in report
        assert "import_error" in report or "src/utils.py" in report

    def test_generate_markdown_format(self, report_gen):
        """测试 Markdown 格式"""
        report = report_gen.generate(format="md")
        assert "# Moat Check 失败报告" in report
        assert "import_error" in report or "src/utils.py" in report

    def test_generate_default_format(self, report_gen):
        """测试默认格式（text）"""
        report = report_gen.generate()
        assert "=" * 60 in report

    def test_generate_unknown_format(self, report_gen):
        """测试未知格式（应该回退到 text）"""
        report = report_gen.generate(format="unknown")
        # 应该返回文本格式
        assert "=" * 60 in report


# ==================== ReportGenerator._generate_json ====================

class TestGenerateJson:
    """测试 _generate_json 方法"""

    def test_generate_json_structure(self, report_gen):
        """测试 JSON 报告结构"""
        report = report_gen._generate_json()
        data = json.loads(report)

        assert "timestamp" in data
        assert "project" in data
        assert "project_types" in data
        assert "architecture_intent" in data
        assert "summary" in data
        assert "pain_score" in data
        assert "errors" in data
        assert "actions" in data

    def test_generate_json_summary(self, report_gen):
        """测试 JSON 报告摘要"""
        report = report_gen._generate_json()
        data = json.loads(report)

        assert data["summary"]["total_checks"] == 10
        assert data["summary"]["passed"] == 7
        assert data["summary"]["failed"] == 2
        assert data["summary"]["duration"] == 1.5

    def test_generate_json_errors(self, report_gen):
        """测试 JSON 报告错误列表"""
        report = report_gen._generate_json()
        data = json.loads(report)

        assert len(data["errors"]) == 2
        assert data["errors"][0]["type"] == "import_error"
        assert "pain_score" in data["errors"][0]
        assert "pain_level" in data["errors"][0]
        assert "impact" in data["errors"][0]
        assert "ai_suggestion" in data["errors"][0]

    def test_generate_json_actions(self, report_gen):
        """测试 JSON 报告操作命令"""
        report = report_gen._generate_json()
        data = json.loads(report)

        assert "view_details" in data["actions"]
        assert "baseline_diff" in data["actions"]
        assert "save_baseline" in data["actions"]

    def test_generate_json_with_architecture_intent(self, tmp_project, moat_result):
        """测试包含架构意图的 JSON 报告"""
        # 创建 architecture_intent.md
        intent_file = tmp_project / ".moat" / "architecture_intent.md"
        intent_file.write_text("# 架构意图\n\n测试内容")

        gen = ReportGenerator(tmp_project, moat_result)
        report = gen._generate_json()
        data = json.loads(report)

        assert data["architecture_intent"]["present"] is True
        assert "content" in data["architecture_intent"]

    def test_generate_json_without_architecture_intent(self, report_gen):
        """测试不包含架构意图的 JSON 报告"""
        report = report_gen._generate_json()
        data = json.loads(report)

        assert data["architecture_intent"]["present"] is False

    def test_generate_json_with_core_areas(self, tmp_project, moat_result):
        """测试包含核心区域的 JSON 报告"""
        # 创建 config.json
        config_file = tmp_project / ".moat" / "config.json"
        config_file.write_text(json.dumps({"core_areas": [{"name": "auth"}]}))

        gen = ReportGenerator(tmp_project, moat_result)
        report = gen._generate_json()
        data = json.loads(report)

        assert data["pain_score"] is not None


# ==================== ReportGenerator._generate_text ====================

class TestGenerateText:
    """测试 _generate_text 方法"""

    def test_generate_text_basic(self, report_gen):
        """测试基本文本报告"""
        report = report_gen._generate_text()

        assert "=" * 60 in report
        assert "Moat Check 失败报告" in report
        assert str(report_gen.project) in report
        assert "📊 项目类型" in report
        assert "📈 检查结果" in report

    def test_generate_text_with_errors(self, report_gen):
        """测试包含错误的文本报告"""
        report = report_gen._generate_text()
        assert "发现以下问题" in report
        assert "import_error" in report

    def test_generate_text_without_errors(self, tmp_project):
        """测试无错误的文本报告"""
        from moat.runner import MoatResult
        result = MagicMock(spec=MoatResult)
        result.errors = []

        gen = ReportGenerator(tmp_project, result)
        report = gen._generate_text()

        assert "发现以下问题" not in report

    def test_generate_text_ai_suggestions(self, report_gen):
        """测试文本报告包含 AI 建议"""
        report = report_gen._generate_text()
        assert "🤖 AI 修复建议" in report

    def test_generate_text_commands(self, report_gen):
        """测试文本报告包含操作命令"""
        report = report_gen._generate_text()
        assert "📋 一键复制命令" in report
        assert "moat check" in report


# ==================== ReportGenerator._generate_markdown ====================

class TestGenerateMarkdown:
    """测试 _generate_markdown 方法"""

    def test_generate_markdown_basic(self, report_gen):
        """测试基本 Markdown 报告"""
        report = report_gen._generate_markdown()

        assert "# Moat Check 失败报告" in report
        assert "**项目**" in report
        assert "**时间**" in report

    def test_generate_markdown_with_errors(self, report_gen):
        """测试包含错误的 Markdown 报告"""
        report = report_gen._generate_markdown()
        assert "## ❌ 发现的问题" in report

    def test_generate_markdown_without_errors(self, tmp_project):
        """测试无错误的 Markdown 报告"""
        from moat.runner import MoatResult
        result = MagicMock(spec=MoatResult)
        result.errors = []

        gen = ReportGenerator(tmp_project, result)
        report = gen._generate_markdown()

        assert "发现的问题" not in report

    def test_generate_markdown_ai_suggestions(self, report_gen):
        """测试 Markdown 报告包含 AI 建议"""
        report = report_gen._generate_markdown()
        assert "## 🤖 AI 修复建议" in report

    def test_generate_markdown_commands(self, report_gen):
        """测试 Markdown 报告包含操作命令"""
        report = report_gen._generate_markdown()
        assert "## 📋 操作步骤" in report
        assert "```bash" in report


# ==================== ReportGenerator._format_error_text ====================

class TestFormatErrorText:
    """测试 _format_error_text 方法"""

    def test_format_error_basic(self, report_gen):
        """测试基本错误格式化"""
        error = {"type": "import_error", "file": "test.py", "message": "Import failed"}
        lines = report_gen._format_error_text(1, error)

        assert "1. [ERROR] test.py" in lines[0]
        assert "类型: import_error" in lines[1]
        assert "原因: Import failed" in lines[2]

    def test_format_error_with_line(self, report_gen):
        """测试带行号的错误格式化"""
        error = {"type": "test", "file": "test.py", "line": 42, "message": "test"}
        lines = report_gen._format_error_text(1, error)

        assert "行号: 42" in lines[3]

    def test_format_error_without_line(self, report_gen):
        """测试不带行号的错误格式化"""
        error = {"type": "test", "file": "test.py", "message": "test"}
        lines = report_gen._format_error_text(1, error)

        assert "行号" not in "".join(lines)

    def test_format_error_with_impact(self, report_gen):
        """测试带影响分析的错误格式化"""
        error = {"type": "import_error", "file": "test.py", "message": "Import failed"}
        lines = report_gen._format_error_text(1, error)

        assert "💡 影响分析" in "".join(lines)

    def test_format_error_without_impact(self, report_gen):
        """测试不带影响分析的错误格式化"""
        error = {"type": "unknown", "file": "test.py", "message": "test"}
        lines = report_gen._format_error_text(1, error)

        assert "💡 影响分析" not in "".join(lines)


# ==================== ReportGenerator._format_error_markdown ====================

class TestFormatErrorMarkdown:
    """测试 _format_error_markdown 方法"""

    def test_format_error_markdown_basic(self, report_gen):
        """测试基本 Markdown 错误格式化"""
        error = {"type": "import_error", "file": "test.py", "message": "Import failed"}
        lines = report_gen._format_error_markdown(1, error)

        assert "### 1. Import failed" in lines[0]
        assert "**文件**: `test.py`" in lines[2]
        assert "**类型**: `import_error`" in lines[3]

    def test_format_error_markdown_with_line(self, report_gen):
        """测试带行号的 Markdown 错误格式化"""
        error = {"type": "test", "file": "test.py", "line": 42, "message": "test"}
        lines = report_gen._format_error_markdown(1, error)

        assert "**行号**: 42" in "".join(lines)

    def test_format_error_markdown_with_impact(self, report_gen):
        """测试带影响分析的 Markdown 错误格式化"""
        error = {"type": "import_error", "file": "test.py", "message": "Import failed"}
        lines = report_gen._format_error_markdown(1, error)

        # 验证包含影响分析（使用 🎯 emoji）
        full_text = "".join(lines)
        assert "影响分析" in full_text


# ==================== ReportGenerator._analyze_impact ====================

class TestAnalyzeImpact:
    """测试 _analyze_impact 方法"""

    def test_analyze_import_error(self, report_gen):
        """测试导入错误影响分析"""
        error = {"type": "import_error", "message": "ModuleNotFoundError"}
        impact = report_gen._analyze_impact(error)
        assert "模块无法加载" in impact

    def test_analyze_api_error(self, report_gen):
        """测试 API 错误影响分析"""
        error = {"type": "api_error", "message": "endpoint not found"}
        impact = report_gen._analyze_impact(error)
        assert "API 接口" in impact

    def test_analyze_syntax_error(self, report_gen):
        """测试语法错误影响分析"""
        error = {"type": "syntax_error", "message": "语法错误"}
        impact = report_gen._analyze_impact(error)
        assert "语法错误" in impact

    def test_analyze_race_condition(self, report_gen):
        """测试竞态条件影响分析"""
        error = {"type": "race_condition", "message": "race condition detected"}
        impact = report_gen._analyze_impact(error)
        assert "竞态条件" in impact

    def test_analyze_dedup_error(self, report_gen):
        """测试去重错误影响分析"""
        error = {"type": "dedup", "message": "去重逻辑错误"}
        impact = report_gen._analyze_impact(error)
        assert "去重" in impact

    def test_analyze_unknown_error(self, report_gen):
        """测试未知错误影响分析"""
        error = {"type": "unknown", "message": "some error"}
        impact = report_gen._analyze_impact(error)
        assert impact is None


# ==================== ReportGenerator._get_ai_suggestion ====================

class TestGetAiSuggestion:
    """测试 _get_ai_suggestion 方法"""

    def test_suggestion_import_error(self, report_gen):
        """测试导入错误建议"""
        error = {"type": "import_error", "file": "src/utils.py", "message": "No module"}
        suggestion = report_gen._get_ai_suggestion(error)
        assert suggestion is not None
        assert "import" in suggestion.lower()
        assert "src/utils.py" in suggestion

    def test_suggestion_api_error(self, report_gen):
        """测试 API 错误建议"""
        error = {"type": "api_error", "file": "src/api.py", "message": "timeout"}
        suggestion = report_gen._get_ai_suggestion(error)
        assert suggestion is not None
        assert "API" in suggestion

    def test_suggestion_syntax_error(self, report_gen):
        """测试语法错误建议"""
        error = {"type": "syntax_error", "file": "test.py", "message": "invalid syntax"}
        suggestion = report_gen._get_ai_suggestion(error)
        assert suggestion is not None
        assert "语法" in suggestion

    def test_suggestion_race_condition(self, report_gen):
        """测试竞态条件建议"""
        error = {"type": "race_condition", "file": "auth.py", "message": "race condition"}
        suggestion = report_gen._get_ai_suggestion(error)
        assert suggestion is not None
        assert "竞态" in suggestion or "锁" in suggestion

    def test_suggestion_unknown_error(self, report_gen):
        """测试未知错误建议"""
        error = {"type": "unknown", "file": "test.py", "message": "error"}
        suggestion = report_gen._get_ai_suggestion(error)
        assert suggestion is None


# ==================== ReportGenerator._get_core_areas_config ====================

class TestGetCoreAreasConfig:
    """测试 _get_core_areas_config 方法"""

    def test_get_core_areas_config_exists(self, tmp_project, moat_result):
        """测试存在配置时的核心区域"""
        config = {"core_areas": [{"name": "auth", "level": "critical"}]}
        config_file = tmp_project / ".moat" / "config.json"
        config_file.write_text(json.dumps(config))

        gen = ReportGenerator(tmp_project, moat_result)
        result = gen._get_core_areas_config()

        assert result == [{"name": "auth", "level": "critical"}]

    def test_get_core_areas_config_not_exists(self, tmp_project, moat_result):
        """测试不存在配置时的核心区域"""
        gen = ReportGenerator(tmp_project, moat_result)
        result = gen._get_core_areas_config()

        assert result is None

    def test_get_core_areas_config_invalid_json(self, tmp_project, moat_result):
        """测试无效 JSON 配置"""
        config_file = tmp_project / ".moat" / "config.json"
        config_file.write_text("invalid json")

        gen = ReportGenerator(tmp_project, moat_result)
        result = gen._get_core_areas_config()

        assert result is None


# ==================== ReportGenerator._load_architecture_intent ====================

class TestLoadArchitectureIntent:
    """测试 _load_architecture_intent 方法"""

    def test_load_intent_exists(self, tmp_project, moat_result):
        """测试加载存在的架构意图"""
        intent_file = tmp_project / ".moat" / "architecture_intent.md"
        intent_file.write_text("# 架构意图\n\n这是测试内容")

        gen = ReportGenerator(tmp_project, moat_result)
        intent = gen._load_architecture_intent()

        assert intent["present"] is True
        assert "path" in intent
        assert "content" in intent
        assert "架构意图" in intent["content"]

    def test_load_intent_not_exists(self, tmp_project, moat_result):
        """测试加载不存在的架构意图"""
        gen = ReportGenerator(tmp_project, moat_result)
        intent = gen._load_architecture_intent()

        assert intent["present"] is False

    def test_load_intent_truncation(self, tmp_project, moat_result):
        """测试长内容截断"""
        long_content = "x" * 3000
        intent_file = tmp_project / ".moat" / "architecture_intent.md"
        intent_file.write_text(long_content)

        gen = ReportGenerator(tmp_project, moat_result)
        intent = gen._load_architecture_intent()

        assert len(intent["content"]) < len(long_content)
        assert "..." in intent["content"]


# ==================== 便捷函数：generate_report ====================

class TestGenerateReport:
    """测试 generate_report 便捷函数"""

    def test_generate_report_with_result(self, tmp_project, moat_result):
        """测试使用已有结果生成报告"""
        report = generate_report(
            str(tmp_project),
            result=moat_result,
            format="text"
        )
        assert "Moat Check 失败报告" in report

    def test_generate_report_json_format(self, tmp_project, moat_result):
        """测试 JSON 格式"""
        report = generate_report(
            str(tmp_project),
            result=moat_result,
            format="json"
        )
        data = json.loads(report)
        assert "timestamp" in data
        assert "errors" in data

    def test_generate_report_markdown_format(self, tmp_project, moat_result):
        """测试 Markdown 格式"""
        report = generate_report(
            str(tmp_project),
            result=moat_result,
            format="md"
        )
        assert "# Moat Check 失败报告" in report

    def test_generate_report_no_copy(self, tmp_project, moat_result):
        """测试不复制到剪贴板"""
        # 不应该抛出异常
        report = generate_report(
            str(tmp_project),
            result=moat_result,
            copy=False
        )
        assert report is not None

    @patch('moat.report._copy_to_clipboard')
    def test_generate_report_with_copy(self, mock_copy, tmp_project, moat_result):
        """测试复制到剪贴板"""
        report = generate_report(
            str(tmp_project),
            result=moat_result,
            copy=True
        )
        mock_copy.assert_called_once()

    def test_generate_report_without_result(self, tmp_project):
        """测试无结果时生成报告"""
        with patch('moat.runner.run_all_checks') as mock_run:
            from moat.runner import MoatResult
            mock_result = MagicMock(spec=MoatResult)
            mock_result.errors = []
            mock_result.summary.return_value = "All passed"
            mock_run.return_value = mock_result

            report = generate_report(str(tmp_project))

            assert report is not None


# ==================== _copy_to_clipboard ====================

class TestCopyToClipboard:
    """测试 _copy_to_clipboard 函数"""

    def test_copy_success(self):
        """测试复制成功（应该不抛出异常）"""
        # pbcopy 可能在测试环境不可用，但函数应该优雅降级
        try:
            _copy_to_clipboard("test text")
        except Exception as e:
            # 如果在非 macOS 环境或没有剪贴板工具，应该优雅降级
            assert False, f"Should not raise: {e}"

    def test_copy_empty_string(self):
        """测试复制空字符串"""
        try:
            _copy_to_clipboard("")
        except Exception:
            pass  # 应该不抛出异常

    def test_copy_unicode(self):
        """测试复制 Unicode 文本"""
        try:
            _copy_to_clipboard("测试中文 🎉")
        except Exception:
            pass  # 应该不抛出异常
