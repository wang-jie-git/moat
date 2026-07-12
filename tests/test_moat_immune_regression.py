"""
Moat Immune Bug 修复回归测试（精简版）

**战术要点**: "修好一个，又崩了另一个"是最高风险。
本测试确保 Moat Immune 的核心功能正常。

**来源**: One 项目 Bug 检测战术指导（2026-07-12）
"""

import pytest
from unittest.mock import patch
from moat.immune.unit.generator import _extract_text_from_response


class MockTextBlock:
    def __init__(self, text: str):
        self.text = text


class MockThinkingBlock:
    def __init__(self, thinking: str):
        self.thinking = thinking


class MockMessage:
    def __init__(self, content_blocks: list):
        self.content = content_blocks


class TestMoatImmuneRegression:
    """Moat Immune 核心回归测试"""

    def test_extract_text_normal_case(self):
        """基础功能：正常提取文本"""
        message = MockMessage([MockTextBlock("def test(): pass")])
        result = _extract_text_from_response(message)
        assert "def test()" in result

    def test_extract_text_handles_thinking_block(self):
        """Bug 修复：处理 ThinkingBlock"""
        message = MockMessage([
            MockThinkingBlock("Let me think..."),
            MockTextBlock("def test(): pass")
        ])
        result = _extract_text_from_response(message)
        assert "def test()" in result

    def test_extract_text_empty_message(self):
        """异常处理：空消息"""
        message = MockMessage([])
        with pytest.raises(ValueError, match="未返回有效的文本内容"):
            _extract_text_from_response(message)

    def test_extract_text_multiple_blocks(self):
        """边界情况：多个 blocks"""
        message = MockMessage([
            MockThinkingBlock("Thinking 1"),
            MockThinkingBlock("Thinking 2"),
            MockTextBlock("real code")
        ])
        result = _extract_text_from_response(message)
        assert "real code" in result

    def test_extract_text_skips_thinking_only(self):
        """边界情况：只有 ThinkingBlock"""
        message = MockMessage([MockThinkingBlock("Only thinking")])
        with pytest.raises(ValueError):
            _extract_text_from_response(message)


class TestMoatCoreIntegration:
    """Moat Core 集成测试（确保接口兼容）"""

    def test_gatekeeper_import(self):
        """接口兼容：Moat Core 能导入 Immune 模块"""
        try:
            from moat.immune.unit import generator
            assert True
        except ImportError as e:
            pytest.fail(f"导入失败: {e}")

    def test_extract_function_signature(self):
        """接口兼容：函数签名不变"""
        import inspect
        sig = inspect.signature(_extract_text_from_response)
        params = list(sig.parameters.keys())
        assert params == ["message"], f"函数签名变化: {params}"
