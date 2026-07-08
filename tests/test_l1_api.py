"""L1 API 检查测试

覆盖：
- detect_api_type()
- _discover_endpoints()
- run_api_check()
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import httpx

from moat.checks.l1_api import (
    detect_api_type,
    run_api_check,
    _discover_endpoints,
)


class TestDetectAPIType:
    """API 框架检测测试"""

    def test_detect_fastapi(self, tmp_path):
        """检测 FastAPI 框架"""
        server_file = tmp_path / "server.py"
        server_file.write_text("""
from fastapi import FastAPI
app = FastAPI()
""")
        api_type = detect_api_type(tmp_path)
        assert api_type == "fastapi"

    def test_detect_fastapi_in_text(self, tmp_path):
        """从代码文本检测 FastAPI"""
        py_file = tmp_path / "main.py"
        py_file.write_text("""
from fastapi import APIRouter
router = APIRouter()
""")
        api_type = detect_api_type(tmp_path)
        assert api_type == "fastapi"

    def test_detect_flask(self, tmp_path):
        """检测 Flask 框架"""
        app_file = tmp_path / "app.py"
        app_file.write_text("""
from flask import Flask
app = Flask(__name__)
""")
        api_type = detect_api_type(tmp_path)
        assert api_type == "flask"

    def test_detect_no_framework(self, tmp_path):
        """未检测到框架"""
        py_file = tmp_path / "test.py"
        py_file.write_text("print('hello')")
        api_type = detect_api_type(tmp_path)
        assert api_type is None


class TestDiscoverEndpoints:
    """端点发现测试"""

    def test_discover_get_endpoint(self, tmp_path):
        """发现 GET 端点"""
        py_file = tmp_path / "routes.py"
        py_file.write_text("""
from fastapi import APIRouter
router = APIRouter()

@router.get("/users")
def get_users():
    pass
""")
        endpoints = _discover_endpoints(tmp_path)
        assert len(endpoints) >= 1
        methods = {ep["method"] for ep in endpoints}
        assert "GET" in methods

    def test_discover_all_http_methods(self, tmp_path):
        """发现所有 HTTP 方法"""
        py_file = tmp_path / "api.py"
        py_file.write_text("""
@app.get("/resource")
def get_resource(): pass

@app.post("/resource")
def create_resource(): pass

@app.put("/resource")
def update_resource(): pass

@app.delete("/resource")
def delete_resource(): pass

@app.patch("/resource")
def patch_resource(): pass
""")
        endpoints = _discover_endpoints(tmp_path)
        methods = {ep["method"] for ep in endpoints}
        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "DELETE" in methods
        assert "PATCH" in methods

    def test_discover_no_endpoints(self, tmp_path):
        """无端点时返回空列表"""
        py_file = tmp_path / "test.py"
        py_file.write_text("print('hello')")
        endpoints = _discover_endpoints(tmp_path)
        assert endpoints == []

    def test_discover_skip_venv(self, tmp_path):
        """跳过 .venv 目录"""
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()
        venv_file = venv_dir / "routes.py"
        venv_file.write_text("@app.get('/skip')\ndef skip(): pass")
        endpoints = _discover_endpoints(tmp_path)
        assert not any(".venv" in ep.get("path", "") for ep in endpoints)

    def test_discover_extract_path(self, tmp_path):
        """正确提取端点路径"""
        py_file = tmp_path / "routes.py"
        py_file.write_text("""
@app.get("/users/{user_id}")
def get_user(user_id: int):
    pass
""")
        endpoints = _discover_endpoints(tmp_path)
        assert any("/users/{user_id}" in ep["path"] for ep in endpoints)

    def test_discover_multiple_files(self, tmp_path):
        """从多个文件发现端点"""
        file1 = tmp_path / "users.py"
        file1.write_text("@app.get('/users')\ndef users(): pass")

        file2 = tmp_path / "posts.py"
        file2.write_text("@app.get('/posts')\ndef posts(): pass")

        endpoints = _discover_endpoints(tmp_path)
        paths = {ep["path"] for ep in endpoints}
        assert "/users" in paths
        assert "/posts" in paths


class TestRunAPICheck:
    """API 检查运行测试"""

    def test_run_api_check_no_endpoints(self, tmp_path):
        """无端点时应返回空列表"""
        errors = run_api_check(tmp_path, "http://localhost:9999")
        assert errors == []


    @patch("moat.checks.l1_api._discover_endpoints")
    def test_run_api_check_server_error(self, mock_discover, tmp_path):
        """检测服务器错误"""
        mock_discover.return_value = [
            {"path": "/error", "method": "GET", "name": ""}
        ]

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client_instance.get.return_value = mock_response

        with patch("httpx.Client", return_value=mock_client_instance):
            errors = run_api_check(tmp_path, "http://localhost:8000")
            assert len(errors) > 0
            assert errors[0]["type"] == "api_error"
            assert errors[0]["level"] == "L1"

    @patch("moat.checks.l1_api._discover_endpoints")
    def test_run_api_check_timeout(self, mock_discover, tmp_path):
        """检测超时"""
        mock_discover.return_value = [
            {"path": "/slow", "method": "GET", "name": ""}
        ]

        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client_instance.get.side_effect = httpx.TimeoutException("Timeout")

        with patch("httpx.Client", return_value=mock_client_instance):
            errors = run_api_check(tmp_path, "http://localhost:8000")
            assert len(errors) > 0
            assert errors[0]["type"] == "api_timeout"

    @patch("moat.checks.l1_api._discover_endpoints")
    def test_run_api_check_connection_error(self, mock_discover, tmp_path):
        """检测连接错误"""
        mock_discover.return_value = [
            {"path": "/test", "method": "GET", "name": ""}
        ]

        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client_instance.get.side_effect = ConnectionError("Connection refused")

        with patch("httpx.Client", return_value=mock_client_instance):
            errors = run_api_check(tmp_path, "http://localhost:8000")
            assert len(errors) > 0
            assert errors[0]["type"] == "api_exception"
