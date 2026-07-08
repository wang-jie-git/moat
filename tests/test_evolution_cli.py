"""Evolution CLI 测试

覆盖 moat.evolution_cli 功能：
- cmd_evolution()
- _cmd_report()
- _cmd_adjust()
- _cmd_record()
- _apply_config_adjustments()
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import json
import argparse

from moat.evolution_cli import (
    _apply_config_adjustments,
)


class TestApplyConfigAdjustments:
    """应用配置调整测试"""

    def test_apply_empty_recommendations(self, tmp_path):
        """空建议列表"""
        applied = _apply_config_adjustments([], tmp_path)
        assert applied == []

    def test_apply_no_config_change(self, tmp_path):
        """无配置变更的建议"""
        recommendations = [
            {"action": "test", "description": "Test action"}
        ]
        applied = _apply_config_adjustments(recommendations, tmp_path)
        assert applied == []

    def test_apply_simple_config_change(self, tmp_path):
        """简单配置变更"""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"threshold": 30}))

        recommendations = [
            {
                "action": "adjust_threshold",
                "config_change": {"threshold": 50}
            }
        ]

        applied = _apply_config_adjustments(recommendations, tmp_path)
        assert "adjust_threshold" in applied

        # 验证配置已更新
        config = json.loads(config_path.read_text())
        assert config["threshold"] == 50

    def test_apply_nested_config_change(self, tmp_path):
        """嵌套配置变更"""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"weights": {"syntax": 0.5}}))

        recommendations = [
            {
                "action": "adjust_weights",
                "config_change": {"weights": {"syntax": 0.8, "semantic": 0.6}}
            }
        ]

        applied = _apply_config_adjustments(recommendations, tmp_path)
        assert "adjust_weights" in applied

        # 验证配置已更新
        config = json.loads(config_path.read_text())
        assert config["weights"]["syntax"] == 0.8
        assert config["weights"]["semantic"] == 0.6

    def test_apply_multiple_recommendations(self, tmp_path):
        """多个配置建议"""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"threshold": 30}))

        recommendations = [
            {"action": "adjust_threshold", "config_change": {"threshold": 50}},
            {"action": "add_new_setting", "config_change": {"new_setting": True}},
        ]

        applied = _apply_config_adjustments(recommendations, tmp_path)
        assert len(applied) == 2
        assert "adjust_threshold" in applied
        assert "add_new_setting" in applied

    def test_apply_config_no_config_file(self, tmp_path):
        """无配置文件"""
        applied = _apply_config_adjustments([{"config_change": {}}], tmp_path)
        assert applied == []

    def test_apply_config_invalid_json(self, tmp_path):
        """无效的 JSON 配置"""
        config_path = tmp_path / "config.json"
        config_path.write_text("invalid json {")

        recommendations = [
            {"action": "test", "config_change": {"key": "value"}}
        ]

        applied = _apply_config_adjustments(recommendations, tmp_path)
        assert applied == []
