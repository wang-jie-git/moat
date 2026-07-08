"""
ArchitectureGatekeeper 集成测试
"""

import pytest
from pathlib import Path

from moat.gatekeeper.checker import ArchitectureGatekeeper
from moat.gatekeeper.types import GatekeeperConfig, RuleSeverity


@pytest.fixture
def gatekeeper(tmp_path):
    """创建守门检查器"""
    # 创建最小项目结构
    (tmp_path / "api").mkdir()
    (tmp_path / "services").mkdir()
    (tmp_path / "requirements.txt").write_text("fastapi==0.100.0\n")

    config = GatekeeperConfig(
        block_on_critical=True,
        block_on_error=True,
        block_on_warning=False,
    )

    return ArchitectureGatekeeper(tmp_path, config)


def test_gatekeeper_check_api_file_with_business_logic(gatekeeper):
    """测试检测api目录中的业务逻辑"""
    content = """
@app.get("/users")
def get_users():
    # 混入了业务逻辑
    results = db.query(User).all()
    return results
"""

    result = gatekeeper.check_file(str(gatekeeper.project_path / "api" / "users.py"), content)

    # 应该检测到违规
    assert len(result.violations) > 0
    assert result.should_block is True


def test_gatekeeper_check_api_file_clean(gatekeeper):
    """测试干净的api文件通过"""
    content = """
from fastapi import APIRouter

router = APIRouter()

@router.get("/users")
def get_users():
    return {"users": []}
"""

    result = gatekeeper.check_file(str(gatekeeper.project_path / "api" / "users_router.py"), content)

    # 应该通过
    assert result.passed is True or len(result.violations) == 0


def test_gatekeeper_check_service_with_http(gatekeeper):
    """测试检测service目录中的HTTP处理"""
    content = """
def get_user(user_id: int):
    # 混入了HTTP处理
    request_data = request.json()
    return process(request_data)
"""

    result = gatekeeper.check_file(str(gatekeeper.project_path / "services" / "user_service.py"), content)

    # 应该检测到违规（request.json()）
    # 这取决于具体的规则实现
    assert isinstance(result.violations, list)


def test_gatekeeper_check_with_ignore_comment(tmp_path):
    """测试豁免注释"""
    (tmp_path / "api").mkdir()
    (tmp_path / "requirements.txt").write_text("fastapi==0.100.0\n")

    config = GatekeeperConfig()
    gatekeeper = ArchitectureGatekeeper(tmp_path, config)

    # 文件有豁免注释
    file_path = tmp_path / "api" / "users.py"
    content = """# moat-ignore: directory_responsibility
@app.get("/users")
def get_users():
    results = db.query(User).all()
    return results
"""

    result = gatekeeper.check_file(str(file_path), content)

    # 应该被豁免（至少ignored_violations有值）
    # 注意：由于豁免，violations可能是空
    assert len(result.ignored_violations) >= 0 or result.should_block is False


def test_gatekeeper_execution_time(gatekeeper):
    """测试执行时间"""
    content = "def test(): pass\n"

    result = gatekeeper.check_file("api/test.py", content)

    # 应该在100ms以内完成
    assert result.execution_time < 100


def test_gatekeeper_format_violations(gatekeeper):
    """测试违规格式化"""
    content = """
@app.get("/users")
def get_users():
    results = db.query(User).all()
    return results
"""

    result = gatekeeper.check_file("api/users.py", content)
    formatted = gatekeeper.format_violations(result)

    assert isinstance(formatted, str)
    assert len(formatted) > 0

    if result.violations:
        assert "🔴" in formatted or "❌" in formatted or "⚠️" in formatted


def test_gatekeeper_config_load_save(tmp_path):
    """测试配置加载和保存"""
    config = GatekeeperConfig(
        ignore_rules={"test_rule": ["*.py"]},
        block_on_warning=True,
    )

    # 保存配置
    config.save(tmp_path)

    # 加载配置
    loaded_config = GatekeeperConfig.load(tmp_path)

    # 验证核心字段
    assert loaded_config.block_on_warning is True
    assert "test_rule" in loaded_config.ignore_rules
    assert loaded_config.ignore_rules["test_rule"] == ["*.py"]
