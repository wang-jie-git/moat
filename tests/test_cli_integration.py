"""CLI 集成测试

覆盖 moat.cli 中未测试的功能：
- build_parser() 边界测试
- _detect_log_path() 测试
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import argparse

from moat.cli import (
    build_parser,
    cmd_init,
    cmd_baseline,
    cmd_adapter,
    _detect_log_path,
)


class TestCLIParserEdgeCases:
    """CLI 解析器边界测试"""

    def test_all_commands_exist(self):
        """所有命令都存在"""
        parser = build_parser()
        commands = {"check", "watch", "init", "report", "baseline",
                    "dashboard", "fix", "sidecar", "adapter", "evolution"}
        choices = parser._subparsers._group_actions[0].choices
        for cmd in commands:
            assert cmd in choices, f"缺少子命令: {cmd}"

    def test_check_with_diff_flag(self):
        """check --diff 参数"""
        parser = build_parser()
        args = parser.parse_args(["check", "--diff"])
        assert args.command == "check"
        assert args.diff is True

    def test_watch_with_log_path(self):
        """watch --log 参数"""
        parser = build_parser()
        args = parser.parse_args(["watch", "--log", "/var/log/app.log"])
        assert args.command == "watch"
        assert args.log == "/var/log/app.log"

    def test_init_non_interactive(self):
        """init --no-interactive 参数"""
        parser = build_parser()
        args = parser.parse_args(["init", "--no-interactive"])
        assert args.command == "init"
        assert args.no_interactive is True

    def test_report_all_formats(self):
        """report --format 所有格式"""
        parser = build_parser()
        for fmt in ["text", "md", "json"]:
            args = parser.parse_args(["report", "--format", fmt])
            assert args.format == fmt

    def test_report_copy_flag(self):
        """report --copy 参数"""
        parser = build_parser()
        args = parser.parse_args(["report", "--copy"])
        assert args.command == "report"
        assert args.copy is True

    def test_baseline_all_actions(self):
        """baseline 所有操作"""
        parser = build_parser()
        for action in ["save", "show", "diff"]:
            args = parser.parse_args(["baseline", action])
            assert args.action == action

    def test_shared_args_verbose(self):
        """--verbose 参数"""
        parser = build_parser()
        args = parser.parse_args(["check", "--verbose"])
        assert args.verbose is True

    def test_shared_args_project(self):
        """--project 参数"""
        parser = build_parser()
        args = parser.parse_args(["check", "--project", "/custom/path"])
        assert args.project == "/custom/path"


class TestDetectLogPath:
    """日志路径检测测试"""

    def test_detect_log_path_backend_found(self, tmp_path):
        """检测到 backend.log"""
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        log_file = log_dir / "backend.log"
        log_file.write_text("test log")

        result = _detect_log_path(str(tmp_path))
        assert result is not None
        assert "backend.log" in result

    def test_detect_log_path_app_found(self, tmp_path):
        """检测到 app.log"""
        log_dir = tmp_path / "log"
        log_dir.mkdir()
        log_file = log_dir / "app.log"
        log_file.write_text("test log")

        result = _detect_log_path(str(tmp_path))
        assert result is not None
        assert "app.log" in result

    def test_detect_log_path_priority(self, tmp_path):
        """backend.log 优先级高于 app.log"""
        (tmp_path / "logs").mkdir()
        (tmp_path / "logs" / "backend.log").write_text("backend")

        (tmp_path / "log").mkdir()
        (tmp_path / "log" / "app.log").write_text("app")

        result = _detect_log_path(str(tmp_path))
        assert result is not None
        assert "backend.log" in result

    def test_detect_log_path_not_found(self, tmp_path):
        """未找到日志文件"""
        result = _detect_log_path(str(tmp_path))
        assert result is None
