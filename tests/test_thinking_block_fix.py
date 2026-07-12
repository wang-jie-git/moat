"""
测试 _extract_text_from_response 函数
验证 ThinkingBlock 处理的修复
"""

import pytest
from unittest.mock import MagicMock
from moat.immune.unit.generator import _extract_text_from_response


class MockTextBlock:
    """模拟 TextBlock"""
    def __init__(self, text: str):
        self.text = text


class MockThinkingBlock:
    """模拟 ThinkingBlock"""
    def __init__(self, thinking: str):
        self.thinking = thinking
        # ThinkingBlock 可能没有 text 属性
        # 或者有 text 属性但访问会报错


class MockMessage:
    """模拟 Claude API 返回的 message"""
    def __init__(self, content_blocks: list):
        self.content = content_blocks


def test_extract_text_with_text_block():
    """测试提取 TextBlock 的内容"""
    message = MockMessage([
        MockTextBlock("def test_example():\n    pass\n")
    ])

    result = _extract_text_from_response(message)
    assert "def test_example" in result
    assert "pass" in result


def test_extract_text_with_thinking_block_only():
    """测试只有 ThinkingBlock 时抛出异常"""
    message = MockMessage([
        MockThinkingBlock("Let me think about this...")
    ])

    with pytest.raises(ValueError, match="未返回有效的文本内容"):
        _extract_text_from_response(message)


def test_extract_text_with_mixed_blocks():
    """测试混合 blocks（ThinkingBlock + TextBlock）"""
    message = MockMessage([
        MockThinkingBlock("Thinking..."),
        MockTextBlock("def test_real_code():\n    assert True\n")
    ])

    result = _extract_text_from_response(message)
    assert "def test_real_code" in result
    assert "assert True" in result


def test_extract_text_with_thinking_then_text():
    """测试 ThinkingBlock 在前，TextBlock 在后"""
    message = MockMessage([
        MockThinkingBlock("Let me analyze the code..."),
        MockThinkingBlock("More thinking..."),
        MockTextBlock("# Test code here\n")
    ])

    result = _extract_text_from_response(message)
    assert "# Test code here" in result


def test_extract_text_empty_blocks():
    """测试空 content blocks"""
    message = MockMessage([])

    with pytest.raises(ValueError, match="未返回有效的文本内容"):
        _extract_text_from_response(message)


def test_extract_text_handles_attribute_error_on_text():
    """测试处理 text 属性访问失败的场景"""
    class BuggyBlock:
        """模拟有 text 属性但访问会报错的 block"""
        @property
        def text(self):
            raise AttributeError("text property access failed")

    message = MockMessage([
        BuggyBlock(),
        MockTextBlock("valid code")
    ])

    # 应该跳过 buggy block，提取到 valid code
    result = _extract_text_from_response(message)
    assert "valid code" in result


# 导入 pytest（在文件末尾以避免循环导入）
