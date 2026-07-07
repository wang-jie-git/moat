"""Tests for Moat Fix Engine"""
import pytest
from pathlib import Path
from moat.fix_strategies import get_strategy, get_all_strategies, FixStrategy


def test_get_strategy_by_type():
    """测试按错误类型获取策略"""
    strategy = get_strategy("syntax_error", "some message")
    assert strategy is not None
    assert strategy.error_type == "syntax_error"


def test_get_strategy_by_pattern():
    """测试按模式匹配策略"""
    strategy = get_strategy("unknown", "ImportError: No module named 'xxx'")
    assert strategy is not None
    assert "import" in strategy.error_type or "import" in strategy.pattern.lower()


def test_get_strategy_not_found():
    """测试未找到策略"""
    strategy = get_strategy("unknown", "completely unknown error xyz")
    assert strategy is None


def test_all_strategies():
    """测试所有策略"""
    strategies = get_all_strategies()
    assert len(strategies) > 0
    assert all(isinstance(s, FixStrategy) for s in strategies)


def test_strategy_has_required_fields():
    """测试策略包含必需字段"""
    strategies = get_all_strategies()
    for strategy in strategies:
        assert hasattr(strategy, "error_type")
        assert hasattr(strategy, "pattern")
        assert hasattr(strategy, "suggestion")
        assert hasattr(strategy, "auto_fixable")
        assert hasattr(strategy, "example")
        assert 0 <= strategy.confidence <= 1
