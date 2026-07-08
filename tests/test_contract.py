"""contract.py 测试

覆盖 moat/contract.py — CONTRACT.md 生成器
"""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from moat.contract import generate_contract


@pytest.fixture
def tmp_project(tmp_path):
    """创建临时项目"""
    project = tmp_path / "test_project"
    project.mkdir()
    return project


class TestGenerateContract:
    """测试 generate_contract 函数"""

    def test_basic_contract_generation(self, tmp_project):
        """测试基本契约文档生成"""
        contract = generate_contract(tmp_project)

        assert contract.startswith("# test_project — 行为契约")
        assert "## 项目概览" in contract
        assert "## 护城河四层防线" in contract
        assert "## 使用方式" in contract
        assert "## 铁律" in contract
        assert "moat check" in contract
        assert "改代码前" in contract
        assert "改代码后" in contract

    def test_contract_contains_sections(self, tmp_project):
        """测试契约包含所有必要章节"""
        contract = generate_contract(tmp_project)

        required_sections = [
            "项目概览",
            "护城河四层防线",
            "使用方式",
            "铁律",
        ]
        for section in required_sections:
            assert section in contract, f"Missing section: {section}"

    def test_contract_four_layers(self, tmp_project):
        """测试契约包含四层防线说明"""
        contract = generate_contract(tmp_project)

        assert "L1 存活" in contract
        assert "L2 结构" in contract
        assert "L3 关联" in contract
        assert "L4 基线" in contract

    def test_contract_usage_examples(self, tmp_project):
        """测试契约包含使用示例"""
        contract = generate_contract(tmp_project)

        assert "moat check" in contract
        assert "moat watch" in contract
        assert "moat baseline" in contract
        assert "bash" in contract

    def test_contract_iron_rules(self, tmp_project):
        """测试契约包含三条铁律"""
        contract = generate_contract(tmp_project)

        assert "1." in contract
        assert "2." in contract
        assert "3." in contract

    def test_contract_warning_message(self, tmp_project):
        """测试契约包含警告信息"""
        contract = generate_contract(tmp_project)

        assert "改代码**前**" in contract
        assert "改代码**后**" in contract
        assert "两次都通过才能提交" in contract

    def test_contract_markdown_format(self, tmp_project):
        """测试契约是标准 Markdown 格式"""
        contract = generate_contract(tmp_project)

        # 检查 Markdown 语法
        assert "#" in contract  # 标题
        assert "|" in contract  # 表格
        assert "```" in contract  # 代码块
        assert ">" in contract  # 引用

    def test_contract_returns_string(self, tmp_project):
        """测试契约返回字符串"""
        contract = generate_contract(tmp_project)
        assert isinstance(contract, str)

    def test_contract_not_empty(self, tmp_project):
        """测试契约非空"""
        contract = generate_contract(tmp_project)
        assert len(contract) > 100  # 保证有一定长度

    def test_contract_mentions_python(self, tmp_project):
        """测试契约提及 Python"""
        contract = generate_contract(tmp_project)
        assert "Python" in contract

    def test_contract_mentions_ai_tools(self, tmp_project):
        """测试契约提及 AI 工具"""
        contract = generate_contract(tmp_project)
        assert "AI 工具" in contract or "moat check" in contract

    def test_contract_default_values(self, tmp_project):
        """测试契约使用默认值（当 discover 返回默认值时）"""
        # 直接调用，不 mock，验证默认行为
        contract = generate_contract(tmp_project)

        # 应该包含一些默认信息
        assert "Python" in contract
        assert len(contract) > 0
