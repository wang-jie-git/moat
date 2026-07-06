"""Moat 监控模块测试"""
import pytest
from pathlib import Path
from moat.monitor import read_recent_errors, _count_existing_errors


class TestMonitor:
    def test_read_recent_errors_no_log(self, tmp_path):
        """日志文件不存在时返回空列表"""
        errors = read_recent_errors(tmp_path / "nonexistent.log")
        assert errors == []

    def test_read_recent_errors_finds_errors(self, tmp_path):
        """能正确读取日志中的错误"""
        log = tmp_path / "test.log"
        log.write_text(
            "INFO: something\n"
            "ERROR: failed to connect\n"
            "WARNING: something\n"
            "ERROR: timeout\n"
            "DEBUG: xyz\n"
            "Traceback (most recent call last):\n"
        )
        errors = read_recent_errors(log, lines=50, filter_pattern="ERROR|Traceback")
        assert len(errors) >= 3  # 两个 ERROR + 一个 Traceback
        for e in errors:
            assert "message" in e
            assert "level" in e

    def test_read_recent_errors_empty_log(self, tmp_path):
        """空日志返回空列表"""
        log = tmp_path / "empty.log"
        log.write_text("")
        errors = read_recent_errors(log)
        assert errors == []

    def test_count_existing_errors(self, tmp_path):
        """能统计已有错误数"""
        log = tmp_path / "test.log"
        log.write_text(
            "INFO: ok\n"
            "ERROR: err1\n"
            "ERROR: err2\n"
        )
        count = _count_existing_errors(log, "ERROR")
        assert count == 2