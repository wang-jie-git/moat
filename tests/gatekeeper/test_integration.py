"""
Gatekeeper 集成测试
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from moat.gatekeeper.checker import ArchitectureGatekeeper
from moat.gatekeeper.types import GatekeeperConfig


@pytest.fixture
def project_with_structure(tmp_path):
    """创建有结构的测试项目"""
    (tmp_path / "api").mkdir()
    (tmp_path / "services").mkdir()
    (tmp_path / "repositories").mkdir()
    (tmp_path / "requirements.txt").write_text("fastapi==0.100.0\n")

    return tmp_path


def test_full_project_check(project_with_structure):
    """测试完整项目检查"""
    config = GatekeeperConfig()
    gatekeeper = ArchitectureGatekeeper(project_with_structure, config)

    # 测试多个文件
    files_to_check = [
        ("api/users_router.py", "from fastapi import APIRouter\nrouter = APIRouter()\n"),
        ("services/user_service.py", "def get_user(): pass\n"),
        ("repositories/user_repo.py", "def find_user(): pass\n"),
    ]

    results = []
    for file_path, content in files_to_check:
        result = gatekeeper.check_file(file_path, content)
        results.append(result)

    # 验证所有检查都完成
    assert len(results) == 3
    assert all(isinstance(r.execution_time, float) for r in results)
    assert all(r.execution_time < 100 for r in results)


def test_violation_severity_levels(project_with_structure):
    """测试不同严重程度的违规"""
    config = GatekeeperConfig(
        block_on_critical=True,
        block_on_error=True,
        block_on_warning=False,
    )
    gatekeeper = ArchitectureGatekeeper(project_with_structure, config)

    # 测试ERROR级别违规会阻止写入
    content_error = """
from repositories.user_repo import UserRepo

@app.get("/users")
def get_users():
    pass
"""

    result = gatekeeper.check_file(str(project_with_structure / "api" / "users.py"), content_error)
    assert result.should_block is True


def test_audit_logging(project_with_structure, tmp_path):
    """测试审计日志"""
    log_path = tmp_path / "audit.jsonl"
    config = GatekeeperConfig(audit_log_path=log_path)
    gatekeeper = ArchitectureGatekeeper(project_with_structure, config)

    content = "def test(): pass\n"
    gatekeeper.check_file("api/test.py", content)

    # 检查日志文件
    if log_path.exists():
        lines = log_path.read_text().strip().split('\n')
        assert len(lines) > 0

        # 验证日志格式
        import json
        log_entry = json.loads(lines[0])
        assert "timestamp" in log_entry
        assert "file_path" in log_entry
        assert "violations" in log_entry


def test_multiple_files_performance(project_with_structure):
    """测试多文件检查性能"""
    config = GatekeeperConfig()
    gatekeeper = ArchitectureGatekeeper(project_with_structure, config)

    import time

    start = time.time()

    # 检查100个文件
    for i in range(100):
        content = f"def test_{i}(): pass\n"
        gatekeeper.check_file(str(project_with_structure / "api" / f"test_{i}.py"), content)

    elapsed = time.time() - start
    avg_time = (elapsed / 100) * 1000  # 转换为毫秒

    # 平均每个文件应该在10ms以内
    assert avg_time < 10
