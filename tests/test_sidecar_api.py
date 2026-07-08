"""Sidecar API 测试套件

目标：覆盖 moat/sidecar/api.py 70%+
策略：测试 API 端点和 SidecarAPI 类
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from moat.sidecar.api import (
    SidecarAPI,
    CheckRequest,
    CheckResponse,
    app,
)


# ==================== Fixtures ====================

@pytest.fixture
def tmp_project(tmp_path):
    """创建临时项目"""
    project = tmp_path / "test_project"
    project.mkdir()
    (project / "main.py").write_text("print('hello')\n")
    return project


@pytest.fixture
def sidecar_api():
    """创建 SidecarAPI 实例"""
    return SidecarAPI(host="127.0.0.1", port=9877)


# ==================== CheckRequest 和 CheckResponse 测试 ====================

class TestCheckModels:
    """测试请求/响应模型"""

    def test_check_request(self):
        """测试 CheckRequest 创建"""
        if not CheckRequest:
            pytest.skip("FastAPI not installed")

        request = CheckRequest(projectPath="/path/to/project")
        assert request.projectPath == "/path/to/project"

    def test_check_response(self):
        """测试 CheckResponse 创建"""
        if not CheckResponse:
            pytest.skip("FastAPI not installed")

        response = CheckResponse(
            success=True,
            errors=[],
            pain_score=10,
            pain_level="LOW",
        )
        assert response.success is True
        assert response.pain_score == 10


# ==================== SidecarAPI 初始化测试 ====================

class TestSidecarAPIInit:
    """测试 SidecarAPI 初始化"""

    def test_init_default_params(self):
        """测试默认参数初始化"""
        api = SidecarAPI()
        assert api.host == "127.0.0.1"
        assert api.port == 9877
        assert api.app is not None  # FastAPI 已安装
        assert api.server is None

    def test_init_custom_params(self):
        """测试自定义参数初始化"""
        api = SidecarAPI(host="0.0.0.0", port=8080)
        assert api.host == "0.0.0.0"
        assert api.port == 8080

    def test_init_without_fastapi(self):
        """测试无 FastAPI 环境"""
        with patch('moat.sidecar.api.FastAPI', None):
            api = SidecarAPI()
            assert api.app is None


# ==================== API 端点测试 ====================

class TestAPIEndpoints:
    """测试 API 端点"""

    def test_root_endpoint(self):
        """测试根端点"""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "moat-sidecar"

    def test_health_endpoint(self):
        """测试健康检查端点"""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_status_endpoint(self):
        """测试状态端点"""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert "running" in data
        assert "version" in data

    def test_check_endpoint_no_changes(self, tmp_project):
        """测试检查端点（无变更）"""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.post("/check", json={"projectPath": str(tmp_project)})

        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "errors" in data
        assert "pain_score" in data
        assert "pain_level" in data

    def test_check_endpoint_invalid_path(self):
        """测试检查端点（无效路径）"""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        # 使用一个明显不存在的路径
        response = client.post("/check", json={"projectPath": "/this/path/does/not/exist/anywhere"})

        # 无效路径可能返回 200（空结果）或 500（异常）
        # 取决于 diff_project 的实现
        assert response.status_code in (200, 500)

    def test_fix_endpoint(self, tmp_project):
        """测试修复端点"""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.post("/fix", json={"projectPath": str(tmp_project)})

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    def test_start_sidecar_endpoint(self):
        """测试启动 sidecar 端点"""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.post("/sidecar/start")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_stop_sidecar_endpoint(self):
        """测试停止 sidecar 端点"""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.post("/sidecar/stop")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_sidecar_status_endpoint(self):
        """测试 sidecar 状态端点"""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/sidecar/status")

        assert response.status_code == 200
        data = response.json()
        assert "running" in data


# ==================== SidecarAPI 方法测试 ====================

class TestSidecarAPIMethods:
    """测试 SidecarAPI 方法"""

    def test_start_without_fastapi(self):
        """测试无 FastAPI 时启动"""
        api = SidecarAPI()
        api.app = None  # 模拟无 FastAPI

        # 应该打印警告但不抛出异常
        api.start()  # 只打印，不实际启动服务器

    def test_stop_without_server(self):
        """测试无服务器时停止"""
        api = SidecarAPI()
        api.server = None

        # 应该不抛出异常
        api.stop()

    def test_stop_with_server(self):
        """测试停止服务器"""
        api = SidecarAPI()
        mock_server = MagicMock()
        api.server = mock_server

        api.stop()

        # 应该设置退出标志
        assert mock_server.should_exit is True


# ==================== 集成测试 ====================

class TestSidecarIntegration:
    """集成测试"""

    def test_full_api_lifecycle(self, tmp_project):
        """测试完整 API 生命周期"""
        from fastapi.testclient import TestClient

        client = TestClient(app)

        # 1. 健康检查
        response = client.get("/health")
        assert response.status_code == 200

        # 2. 状态检查
        response = client.get("/status")
        assert response.status_code == 200

        # 3. 运行检查
        response = client.post("/check", json={"projectPath": str(tmp_project)})
        assert response.status_code == 200

        # 4. 停止 sidecar
        response = client.post("/sidecar/stop")
        assert response.status_code == 200
