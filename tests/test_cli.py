"""Moat CLI 测试"""
import pytest
from pathlib import Path
from moat.cli import build_parser


class TestCLI:
    def test_parser_created(self):
        """CLI 解析器能创建"""
        parser = build_parser()
        assert parser is not None
        assert parser.prog == "moat"

    def test_parser_has_all_commands(self):
        """所有子命令都存在"""
        parser = build_parser()
        # 所有子命令名
        commands = {"check", "watch", "init", "report", "baseline", "dashboard", "adapter"}
        choices = parser._subparsers._group_actions[0].choices
        for cmd in commands:
            assert cmd in choices, f"缺少子命令: {cmd}"

    def test_check_command_args(self):
        """check 命令参数"""
        parser = build_parser()
        args = parser.parse_args(["check"])
        assert args.command == "check"
        assert args.project == "."

    def test_watch_command_args(self):
        """watch 命令参数"""
        parser = build_parser()
        args = parser.parse_args(["watch", "--log", "test.log"])
        assert args.command == "watch"
        assert args.log == "test.log"

    def test_adapter_command_args(self):
        """adapter 命令参数"""
        parser = build_parser()
        args = parser.parse_args(["adapter", "claude"])
        assert args.command == "adapter"
        assert args.type == "claude"

    def test_baseline_command_args(self):
        """baseline 命令参数"""
        parser = build_parser()
        args = parser.parse_args(["baseline", "save"])
        assert args.command == "baseline"
        assert args.action == "save"

    def test_report_command_args(self):
        """report 命令参数"""
        parser = build_parser()
        args = parser.parse_args(["report"])
        assert args.command == "report"
        assert args.format == "text"
        assert args.copy is False

    def test_report_command_with_copy(self):
        """report --copy 参数"""
        parser = build_parser()
        args = parser.parse_args(["report", "--copy"])
        assert args.command == "report"
        assert args.copy is True

    def test_report_command_with_format(self):
        """report --format 参数"""
        parser = build_parser()
        args = parser.parse_args(["report", "--format", "md"])
        assert args.command == "report"
        assert args.format == "md"

    def test_dashboard_command_args(self):
        """dashboard 命令参数"""
        parser = build_parser()
        args = parser.parse_args(["dashboard", "--port", "9999"])
        assert args.command == "dashboard"
        assert args.port == 9999

    def test_check_command_with_diff(self):
        """check 命令的 --diff 参数"""
        parser = build_parser()
        args = parser.parse_args(["check", "--diff"])
        assert args.command == "check"
        assert args.diff is True

    def test_watch_command_without_log(self):
        """watch 命令无日志路径"""
        parser = build_parser()
        args = parser.parse_args(["watch"])
        assert args.command == "watch"
        assert args.log is None
        assert args.color is True

    def test_baseline_command_show(self):
        """baseline show 命令"""
        parser = build_parser()
        args = parser.parse_args(["baseline", "show"])
        assert args.command == "baseline"
        assert args.action == "show"

    def test_init_command_non_interactive(self):
        """init 命令的非交互模式"""
        parser = build_parser()
        args = parser.parse_args(["init", "--no-interactive"])
        assert args.command == "init"
        assert args.no_interactive is True

    def test_report_command_markdown(self):
        """report 命令的 markdown 格式"""
        parser = build_parser()
        args = parser.parse_args(["report", "--format", "md"])
        assert args.command == "report"
        assert args.format == "md"

    def test_report_command_json(self):
        """report 命令的 JSON 格式"""
        parser = build_parser()
        args = parser.parse_args(["report", "--format", "json"])
        assert args.command == "report"
        assert args.format == "json"