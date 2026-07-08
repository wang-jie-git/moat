"""Monitor 模块测试

覆盖 moat.monitor 功能：
- start_monitor()
- _count_existing_errors()
- read_recent_errors()
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from moat.monitor import (
    start_monitor,
    _count_existing_errors,
    read_recent_errors,
)


class TestCountExistingErrors:
    """统计已有错误测试"""

    def test_count_errors_with_matches(self, tmp_path):
        """统计匹配的错误"""
        log_file = tmp_path / "app.log"
        log_file.write_text(
            "2024-01-01 ERROR: Something went wrong\n"
            "2024-01-01 INFO: Normal message\n"
            "2024-01-01 ERROR: Another error\n"
            "2024-01-01 WARNING: Be careful\n"
            "2024-01-01 ERROR: Third error\n"
        )

        count = _count_existing_errors(log_file, "ERROR|Traceback")
        assert count == 3

    def test_count_errors_no_matches(self, tmp_path):
        """无匹配错误"""
        log_file = tmp_path / "app.log"
        log_file.write_text("2024-01-01 INFO: All good\n")

        count = _count_existing_errors(log_file, "ERROR|Traceback")
        assert count == 0

    def test_count_errors_empty_file(self, tmp_path):
        """空文件"""
        log_file = tmp_path / "app.log"
        log_file.write_text("")

        count = _count_existing_errors(log_file, "ERROR")
        assert count == 0

    def test_count_errors_file_not_exist(self, tmp_path):
        """文件不存在"""
        count = _count_existing_errors(tmp_path / "nonexistent.log", "ERROR")
        assert count == 0

    def test_count_errors_with_traceback(self, tmp_path):
        """统计 Traceback"""
        log_file = tmp_path / "error.log"
        log_file.write_text(
            "Traceback (most recent call last):\n"
            '  File "app.py", line 10, in main\n'
            '    raise ValueError("test")\n'
            "Traceback (most recent call last):\n"
            '  File "app.py", line 20, in worker\n'
            '    raise TypeError("test2")\n'
        )

        count = _count_existing_errors(log_file, "ERROR|Traceback")
        assert count == 2

    def test_count_errors_complex_pattern(self, tmp_path):
        """复杂过滤模式"""
        log_file = tmp_path / "app.log"
        log_file.write_text(
            "ERROR: Database connection failed\n"
            "WARNING: Memory usage high\n"
            "ERROR: API timeout\n"
            "INFO: Request completed\n"
            "CRITICAL: System failure\n"
        )

        count = _count_existing_errors(log_file, "ERROR|CRITICAL")
        assert count == 3  # ERROR x2 + CRITICAL x1


class TestReadRecentErrors:
    """读取最近错误测试"""

    def test_read_errors_with_matches(self, tmp_path):
        """读取匹配的错误"""
        log_file = tmp_path / "app.log"
        log_file.write_text(
            "2024-01-01 10:00:00 ERROR: First error\n"
            "2024-01-01 10:01:00 INFO: Normal message\n"
            "2024-01-01 10:02:00 ERROR: Second error\n"
            "2024-01-01 10:03:00 WARNING: Warning\n"
            "2024-01-01 10:04:00 ERROR: Third error\n"
        )

        errors = read_recent_errors(log_file, lines=10)
        assert len(errors) == 3
        assert all(e["level"] == "ERROR" for e in errors)

    def test_read_errors_limit(self, tmp_path):
        """限制返回数量"""
        log_file = tmp_path / "app.log"
        errors_text = "\n".join([f"2024-01-01 ERROR: Error {i}" for i in range(10)])
        log_file.write_text(errors_text + "\n")

        errors = read_recent_errors(log_file, lines=5)
        assert len(errors) == 5

    def test_read_errors_file_not_exist(self, tmp_path):
        """文件不存在返回空列表"""
        errors = read_recent_errors(tmp_path / "nonexistent.log")
        assert errors == []

    def test_read_errors_empty_file(self, tmp_path):
        """空文件"""
        log_file = tmp_path / "app.log"
        log_file.write_text("")

        errors = read_recent_errors(log_file)
        assert errors == []

    def test_read_errors_no_matches(self, tmp_path):
        """无匹配"""
        log_file = tmp_path / "app.log"
        log_file.write_text("2024-01-01 INFO: All good\n")

        errors = read_recent_errors(log_file, filter_pattern="ERROR")
        assert errors == []

    def test_read_errors_detects_traceback(self, tmp_path):
        """检测 Traceback"""
        log_file = tmp_path / "error.log"
        log_file.write_text(
            "Traceback (most recent call last):\n"
            '  File "app.py", line 10, in main\n'
            '    raise ValueError("test")\n'
            "Some normal log\n"
        )

        errors = read_recent_errors(log_file, filter_pattern="ERROR|Traceback")
        assert len(errors) == 1
        assert "Traceback" in errors[0]["message"]

    def test_read_errors_custom_filter(self, tmp_path):
        """自定义过滤"""
        log_file = tmp_path / "app.log"
        log_file.write_text(
            "ERROR: Database error\n"
            "WARNING: Memory high\n"
            "CRITICAL: System failure\n"
            "INFO: Normal\n"
        )

        errors = read_recent_errors(log_file, filter_pattern="ERROR|CRITICAL")
        assert len(errors) == 2
        levels = {e["level"] for e in errors}
        assert "ERROR" in levels

    def test_read_errors_has_timestamp(self, tmp_path):
        """错误包含时间戳"""
        log_file = tmp_path / "app.log"
        log_file.write_text("2024-01-01 ERROR: Test error\n")

        errors = read_recent_errors(log_file)
        assert len(errors) == 1
        assert "timestamp" in errors[0]
        assert "message" in errors[0]
        assert "level" in errors[0]


class TestStartMonitor:
    """启动监控测试"""

    def test_start_monitor_file_not_exist(self, tmp_path):
        """日志文件不存在"""
        with patch("builtins.print") as mock_print:
            start_monitor(tmp_path / "nonexistent.log")
            mock_print.assert_called_once()
            assert "不存在" in mock_print.call_args[0][0]

    def test_start_monitor_keyboard_interrupt(self, tmp_path):
        """处理 Ctrl+C"""
        log_file = tmp_path / "app.log"
        log_file.write_text("2024-01-01 INFO: Test\n")

        with patch("moat.monitor._count_existing_errors", return_value=0), \
             patch("builtins.print") as mock_print, \
             patch("subprocess.Popen") as mock_popen:

            mock_process = MagicMock()
            mock_process.stdout.readline.side_effect = ["", KeyboardInterrupt()]
            mock_popen.return_value = mock_process

            start_monitor(log_file)

            printed_messages = [str(c[0][0]) for c in mock_print.call_args_list]
            assert any("监控共发现" in msg for msg in printed_messages)

    def test_start_monitor_tail_command(self, tmp_path):
        """使用 tail -f 命令"""
        log_file = tmp_path / "app.log"
        log_file.write_text("2024-01-01 INFO: Test\n")

        with patch("moat.monitor._count_existing_errors", return_value=0), \
             patch("subprocess.Popen") as mock_popen:

            mock_process = MagicMock()
            mock_process.stdout.readline.side_effect = ["", KeyboardInterrupt()]
            mock_popen.return_value = mock_process

            start_monitor(log_file)

            mock_popen.assert_called_once()
            call_args = mock_popen.call_args[0][0]
            assert call_args == ["tail", "-f", "-n", "0", str(log_file)]
