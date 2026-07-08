"""
IgnoreMechanism 测试
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from moat.gatekeeper.types import (
    GatekeeperConfig,
    IgnoreMechanism,
    RuleSeverity,
    RuleViolation,
)


@pytest.fixture
def temp_file(tmp_path):
    """创建临时文件"""
    test_file = tmp_path / "test.py"
    test_file.write_text("# test file\n")
    return test_file


@pytest.fixture
def violation():
    """创建测试违规"""
    return RuleViolation(
        rule_id="test_rule",
        rule_name="Test Rule",
        message="Test violation",
        severity=RuleSeverity.WARNING,
        file_path="test.py",
        line=5,
    )


def test_ignore_mechanism_line_ignore(temp_file, violation):
    """测试行内豁免"""
    # 在违规行附近添加豁免注释
    content = temp_file.read_text()
    lines = content.split('\n')
    lines.insert(5, "# moat-ignore: test_rule")
    temp_file.write_text('\n'.join(lines))

    config = GatekeeperConfig()
    assert IgnoreMechanism.should_ignore(violation, str(temp_file), config) is True


def test_ignore_mechanism_file_ignore(temp_file, violation):
    """测试文件级豁免"""
    # 在文件头部添加豁免注释
    content = "# moat-ignore: test_rule\n" + temp_file.read_text()
    temp_file.write_text(content)

    config = GatekeeperConfig()
    assert IgnoreMechanism.should_ignore(violation, str(temp_file), config) is True


def test_ignore_mechanism_config_ignore(temp_file, violation):
    """测试配置文件豁免"""
    # 简化：使用通配符匹配所有.py文件
    config = GatekeeperConfig(
        ignore_rules={
            "test_rule": ["*.py"]
        }
    )

    assert IgnoreMechanism.should_ignore(violation, str(temp_file), config) is True


def test_ignore_mechanism_no_ignore(temp_file, violation):
    """测试无豁免"""
    config = GatekeeperConfig()
    assert IgnoreMechanism.should_ignore(violation, str(temp_file), config) is False


def test_ignore_mechanism_line_priority(temp_file, violation):
    """测试行内豁免优先级最高"""
    # 配置文件豁免不包含此文件
    config = GatekeeperConfig(
        ignore_rules={
            "test_rule": ["other.py"]
        }
    )

    # 但在文件头部有豁免注释
    content = "# moat-ignore: test_rule\n" + temp_file.read_text()
    temp_file.write_text(content)

    # 应该仍然豁免（行内优先级最高）
    assert IgnoreMechanism.should_ignore(violation, str(temp_file), config) is True


def test_add_ignore_comment(temp_file):
    """测试添加豁免注释"""
    IgnoreMechanism.add_ignore_comment(str(temp_file), "test_rule")

    content = temp_file.read_text()
    assert "# moat-ignore: test_rule" in content


def test_add_ignore_comment_at_line(temp_file):
    """测试在指定行添加豁免注释"""
    IgnoreMechanism.add_ignore_comment(str(temp_file), "test_rule", line=3)

    lines = temp_file.read_text().split('\n')
    assert "# moat-ignore: test_rule" in lines


def test_ignore_mechanism_pattern_matching(tmp_path):
    """测试模式匹配"""
    violation = RuleViolation(
        rule_id="test_rule",
        rule_name="Test Rule",
        message="Test",
        severity=RuleSeverity.WARNING,
        file_path="test.py",
    )

    # 使用简单的文件名模式
    config = GatekeeperConfig(
        ignore_rules={
            "test_rule": ["test_*.py", "*.test.py"]
        }
    )

    # 匹配test_*.py模式
    assert IgnoreMechanism.should_ignore(violation, "test_something.py", config) is True

    # 匹配*.test.py后缀
    assert IgnoreMechanism.should_ignore(violation, "something.test.py", config) is True

    # 不匹配
    assert IgnoreMechanism.should_ignore(violation, "src.py", config) is False
