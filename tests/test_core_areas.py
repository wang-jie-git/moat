"""CoreAreaDetector 测试套件

目标：覆盖 moat/core_areas.py 80%+
策略：测试核心业务探测、验证逻辑、配置生成
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from moat.core_areas import (
    CoreArea,
    CoreAreaDetector,
    detect_core_areas,
)


# ==================== Fixtures ====================

@pytest.fixture
def tmp_project(tmp_path):
    """创建临时项目目录，包含核心业务目录结构"""
    project = tmp_path / "test_project"
    project.mkdir()

    # 创建核心业务目录
    (project / "src" / "auth").mkdir(parents=True)
    (project / "src" / "auth" / "login.py").write_text("# login module")

    (project / "src" / "payment").mkdir(parents=True)
    (project / "src" / "payment" / "checkout.py").write_text("# checkout module")

    (project / "src" / "api").mkdir(parents=True)
    (project / "src" / "api" / "routes.py").write_text("# api routes")

    # 创建应该被排除的目录
    (project / ".venv").mkdir()
    (project / "node_modules").mkdir()

    return project


@pytest.fixture
def empty_project(tmp_path):
    """创建空项目"""
    project = tmp_path / "empty_project"
    project.mkdir()
    return project


@pytest.fixture
def sample_core_area():
    """创建样本 CoreArea"""
    return CoreArea(
        pattern="src/auth/**/*",
        name="鉴权",
        sensitivity="critical",
        pain_multiplier=2.5,
        description="用户鉴权与会话管理",
    )


# ==================== CoreArea 验证测试 ====================

class TestCoreAreaValidation:
    """测试 CoreArea 数据验证"""

    def test_valid_core_area(self):
        """测试有效 CoreArea 创建"""
        area = CoreArea(
            pattern="src/auth/**/*",
            name="鉴权",
            sensitivity="critical",
            pain_multiplier=2.5,
            description="Auth module",
        )
        assert area.pattern == "src/auth/**/*"
        assert area.name == "鉴权"
        assert area.sensitivity == "critical"
        assert area.pain_multiplier == 2.5
        assert area.description == "Auth module"

    def test_invalid_sensitivity(self):
        """测试无效敏感级别"""
        with pytest.raises(ValueError, match="Invalid sensitivity"):
            CoreArea(
                pattern="src/**/*",
                name="test",
                sensitivity="invalid",
                pain_multiplier=1.0,
            )

    def test_invalid_pain_multiplier_too_high(self):
        """测试超出上限的 Pain Multiplier"""
        with pytest.raises(ValueError, match="Invalid pain_multiplier"):
            CoreArea(
                pattern="src/**/*",
                name="test",
                sensitivity="critical",
                pain_multiplier=3.5,
            )

    def test_invalid_pain_multiplier_too_low(self):
        """测试低于下限的 Pain Multiplier"""
        with pytest.raises(ValueError, match="Invalid pain_multiplier"):
            CoreArea(
                pattern="src/**/*",
                name="test",
                sensitivity="critical",
                pain_multiplier=0.5,
            )

    def test_valid_all_sensitivity_levels(self):
        """测试所有有效敏感级别"""
        for sensitivity in ["critical", "high", "medium", "low"]:
            area = CoreArea(
                pattern="src/**/*",
                name="test",
                sensitivity=sensitivity,
                pain_multiplier=1.5,
            )
            assert area.sensitivity == sensitivity

    def test_valid_pain_multiplier_boundaries(self):
        """测试 Pain Multiplier 边界值"""
        # 下限
        area_low = CoreArea(
            pattern="src/**/*",
            name="test",
            sensitivity="low",
            pain_multiplier=1.0,
        )
        assert area_low.pain_multiplier == 1.0

        # 上限
        area_high = CoreArea(
            pattern="src/**/*",
            name="test",
            sensitivity="critical",
            pain_multiplier=3.0,
        )
        assert area_high.pain_multiplier == 3.0

    def test_default_description(self):
        """测试默认描述为空"""
        area = CoreArea(
            pattern="src/**/*",
            name="test",
            sensitivity="medium",
            pain_multiplier=1.5,
        )
        assert area.description == ""


# ==================== CoreAreaDetector 检测测试 ====================

class TestCoreAreaDetector:
    """测试 CoreAreaDetector"""

    def test_detect_basic(self, tmp_project):
        """测试基本检测功能"""
        detector = CoreAreaDetector(tmp_project)
        areas = detector.detect(auto_confirm=True)

        assert isinstance(areas, list)
        assert len(areas) > 0

        # 验证每个区域都有必要字段
        for area in areas:
            assert isinstance(area, CoreArea)
            assert area.pattern
            assert area.name
            assert area.sensitivity in {"critical", "high", "medium", "low"}
            assert 1.0 <= area.pain_multiplier <= 3.0

    def test_detect_auth_area(self, tmp_project):
        """测试鉴权区域检测"""
        detector = CoreAreaDetector(tmp_project)
        areas = detector.detect(auto_confirm=True)

        # 查找鉴权区域
        auth_areas = [a for a in areas if a.name == "鉴权"]
        assert len(auth_areas) >= 1
        assert auth_areas[0].sensitivity == "critical"

    def test_detect_payment_area(self, tmp_project):
        """测试支付区域检测"""
        detector = CoreAreaDetector(tmp_project)
        areas = detector.detect(auto_confirm=True)

        # 查找支付区域
        payment_areas = [a for a in areas if a.name == "支付"]
        assert len(payment_areas) >= 1

    def test_detect_api_area(self, tmp_project):
        """测试 API 网关区域检测"""
        detector = CoreAreaDetector(tmp_project)
        areas = detector.detect(auto_confirm=True)

        # 查找 API 区域
        api_areas = [a for a in areas if a.name == "API 网关"]
        assert len(api_areas) >= 1

    def test_detect_excludes_venv(self, tmp_project):
        """测试排除虚拟环境"""
        detector = CoreAreaDetector(tmp_project)
        paths = detector._find_matching_paths(["lib"])

        # 应该找到 src/lib（如果有），但不应该包含 .venv
        for path in paths:
            assert ".venv" not in path
            assert "venv" not in path or "src/venv" in path  # src/venv 是有效的

    def test_detect_excludes_node_modules(self, tmp_project):
        """测试排除 node_modules"""
        detector = CoreAreaDetector(tmp_project)
        paths = detector._find_matching_paths(["lib"])

        for path in paths:
            assert "node_modules" not in path

    def test_detect_empty_project(self, empty_project):
        """测试空项目"""
        detector = CoreAreaDetector(empty_project)
        areas = detector.detect(auto_confirm=True)

        # 空项目不应该检测到任何核心区域
        assert len(areas) == 0

    def test_detect_no_interactive(self, tmp_project):
        """测试非交互模式"""
        detector = CoreAreaDetector(tmp_project)
        areas = detector.detect(auto_confirm=True)

        # 应该返回检测到的区域，不进行交互
        assert isinstance(areas, list)
        assert len(areas) >= 1

    def test_find_matching_paths_empty(self, empty_project):
        """测试无匹配路径"""
        detector = CoreAreaDetector(empty_project)
        paths = detector._find_matching_paths(["auth", "payment"])

        assert paths == []

    def test_find_matching_paths_keyword_match(self, tmp_project):
        """测试关键词匹配"""
        detector = CoreAreaDetector(tmp_project)
        paths = detector._find_matching_paths(["auth"])

        assert len(paths) >= 1
        assert any("auth" in p.lower() for p in paths)

    def test_generate_pattern(self, tmp_project):
        """测试路径模式生成"""
        detector = CoreAreaDetector(tmp_project)
        paths = ["src/auth/login", "src/auth/utils"]
        pattern = detector._generate_pattern(paths)

        assert pattern.endswith("/**/*")
        assert "src" in pattern

    def test_generate_pattern_empty(self, tmp_project):
        """测试空路径的模式生成"""
        detector = CoreAreaDetector(tmp_project)
        pattern = detector._generate_pattern([])

        assert pattern == ""


# ==================== 交互模式测试 ====================

class TestInteractiveConfirm:
    """测试交互式确认"""

    def test_interactive_confirm_all_critical(self, tmp_project):
        """测试选项 1：全部设为 critical"""
        detector = CoreAreaDetector(tmp_project)
        areas = detector.detect(auto_confirm=True)

        # 模拟用户输入 "1" 和 TTY 环境
        with patch('sys.stdin.isatty', return_value=True), patch('builtins.input', return_value='1'):
            confirmed = detector._interactive_confirm(areas)

        assert len(confirmed) >= 1
        for area in confirmed:
            assert area.sensitivity == "critical"
            assert area.pain_multiplier == 2.5

    def test_interactive_confirm_mixed(self, tmp_project):
        """测试选项 2：混合敏感级别"""
        detector = CoreAreaDetector(tmp_project)
        areas = detector.detect(auto_confirm=True)

        # 模拟用户输入 "2"
        with patch('builtins.input', return_value='2'):
            confirmed = detector._interactive_confirm(areas)

        assert len(confirmed) >= 1
        # 验证特定区域
        for area in confirmed:
            if area.name in ("鉴权", "支付"):
                assert area.sensitivity == "critical"
            elif area.name in ("数据核心", "API 网关", "配置中心"):
                assert area.sensitivity == "high"

    def test_interactive_confirm_all_medium(self, tmp_project):
        """测试选项 3：全部设为 medium"""
        detector = CoreAreaDetector(tmp_project)
        areas = detector.detect(auto_confirm=True)

        # 模拟用户输入 "3" 和 TTY 环境
        with patch('sys.stdin.isatty', return_value=True), patch('builtins.input', return_value='3'):
            confirmed = detector._interactive_confirm(areas)

        assert len(confirmed) >= 1
        for area in confirmed:
            assert area.sensitivity == "medium"
            assert area.pain_multiplier == 1.5

    def test_interactive_confirm_default(self, tmp_project):
        """测试默认选项（Enter）"""
        detector = CoreAreaDetector(tmp_project)
        areas = detector.detect(auto_confirm=True)

        # 模拟用户输入 ""
        with patch('builtins.input', return_value=''):
            confirmed = detector._interactive_confirm(areas)

        assert len(confirmed) >= 1
        # 应该保持原始敏感级别
        for area in confirmed:
            assert area.sensitivity in {"critical", "high", "medium"}

    def test_interactive_confirm_non_tty(self, tmp_project):
        """测试非 TTY 环境"""
        detector = CoreAreaDetector(tmp_project)
        areas = detector.detect(auto_confirm=True)

        # 模拟非 TTY
        with patch('sys.stdin.isatty', return_value=False):
            confirmed = detector._interactive_confirm(areas)

        # 应该返回原样，不修改
        assert len(confirmed) == len(areas)


# ==================== CoreAreaDetector.to_config ====================

class TestToConfig:
    """测试 to_config 方法"""

    def test_to_config_basic(self, sample_core_area):
        """测试基本配置生成"""
        detector = CoreAreaDetector(Path("."))
        config = detector.to_config([sample_core_area])

        assert "core_areas" in config
        assert len(config["core_areas"]) == 1

        area_config = config["core_areas"][0]
        assert area_config["name"] == "鉴权"
        assert area_config["sensitivity"] == "critical"
        assert area_config["pain_multiplier"] == 2.5
        assert "description" in area_config

    def test_to_config_multiple_areas(self, sample_core_area):
        """测试多个区域的配置生成"""
        area2 = CoreArea(
            pattern="src/payment/**/*",
            name="支付",
            sensitivity="critical",
            pain_multiplier=2.5,
            description="Payment module",
        )

        detector = CoreAreaDetector(Path("."))
        config = detector.to_config([sample_core_area, area2])

        assert len(config["core_areas"]) == 2
        assert config["core_areas"][0]["name"] == "鉴权"
        assert config["core_areas"][1]["name"] == "支付"

    def test_to_config_empty(self):
        """测试空列表"""
        detector = CoreAreaDetector(Path("."))
        config = detector.to_config([])

        assert config["core_areas"] == []


# ==================== detect_core_areas 便捷函数 ====================

class TestDetectCoreAreas:
    """测试 detect_core_areas 便捷函数"""

    def test_detect_core_areas_basic(self, tmp_project):
        """测试基本检测"""
        areas = detect_core_areas(str(tmp_project), auto_confirm=True)

        assert isinstance(areas, list)
        assert len(areas) >= 1

    def test_detect_core_areas_no_confirm(self, tmp_project):
        """测试非自动确认模式"""
        with patch('builtins.input', return_value=''):
            areas = detect_core_areas(str(tmp_project), auto_confirm=False)

        assert isinstance(areas, list)
        assert len(areas) >= 1

    def test_detect_core_areas_empty_project(self, empty_project):
        """测试空项目"""
        areas = detect_core_areas(str(empty_project), auto_confirm=True)
        assert len(areas) == 0

    def test_detect_core_areas_returns_core_area(self, tmp_project):
        """测试返回 CoreArea 类型"""
        areas = detect_core_areas(str(tmp_project), auto_confirm=True)

        for area in areas:
            assert isinstance(area, CoreArea)


# ==================== CORE_AREA_PATTERNS 测试 ====================

class TestCoreAreaPatterns:
    """测试预定义的核心区域模式"""

    def test_all_patterns_have_required_fields(self):
        """测试所有预定义模式包含必要字段"""
        detector = CoreAreaDetector(Path("."))
        patterns = detector.CORE_AREA_PATTERNS

        for name, config in patterns.items():
            assert "keywords" in config
            assert "sensitivity" in config
            assert "pain_multiplier" in config
            assert "description" in config
            assert isinstance(config["keywords"], list)
            assert len(config["keywords"]) >= 1

    def test_pattern_sensitivity_values(self):
        """测试模式敏感级别值"""
        detector = CoreAreaDetector(Path("."))
        patterns = detector.CORE_AREA_PATTERNS

        valid_sensitivities = {"critical", "high", "medium", "low"}
        for name, config in patterns.items():
            assert config["sensitivity"] in valid_sensitivities

    def test_pattern_pain_multiplier_range(self):
        """测试 Pain Multiplier 范围"""
        detector = CoreAreaDetector(Path("."))
        patterns = detector.CORE_AREA_PATTERNS

        for name, config in patterns.items():
            multiplier = config["pain_multiplier"]
            assert 1.0 <= multiplier <= 3.0

    def test_expected_patterns_exist(self):
        """测试预期的核心区域都存在"""
        detector = CoreAreaDetector(Path("."))
        patterns = detector.CORE_AREA_PATTERNS

        expected_areas = {"鉴权", "支付", "数据核心", "API 网关", "配置中心", "用户核心"}
        assert set(patterns.keys()) == expected_areas
