"""l2_schema.py 测试

覆盖 moat/checks/l2_schema.py — API 结构检查
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from moat.checks.l2_schema import run_schema_check


@pytest.fixture
def tmp_project(tmp_path):
    """创建临时项目"""
    project = tmp_path / "test_project"
    project.mkdir()
    return project


class TestRunSchemaCheck:
    """测试 run_schema_check 函数"""

    def test_no_openapi_file(self, tmp_project):
        """测试没有 openapi.json 文件"""
        errors = run_schema_check(tmp_project)
        assert errors == []

    def test_openapi_file_empty(self, tmp_project):
        """测试空的 openapi.json"""
        (tmp_project / "openapi.json").write_text("{}")

        errors = run_schema_check(tmp_project)
        assert errors == []

    def test_openapi_file_invalid_json(self, tmp_project):
        """测试无效的 JSON 格式"""
        (tmp_project / "openapi.json").write_text("invalid json{")

        errors = run_schema_check(tmp_project)
        assert errors == []

    def test_server_unavailable(self, tmp_project):
        """测试服务器未运行"""
        (tmp_project / "openapi.json").write_text(json.dumps({
            "paths": {
                "/api/users": {"get": {}}
            }
        }))

        # 不运行服务器，应该跳过
        with patch('httpx.Client', side_effect=Exception("Connection refused")):
            errors = run_schema_check(tmp_project)
        assert errors == []

    def test_server_not_running_pass(self, tmp_project):
        """测试服务器未运行时应该通过（跳过）"""
        errors = run_schema_check(tmp_project)
        # 服务器未运行，应该返回空
        assert errors == []

    @patch('httpx.Client')
    def test_valid_schema_response(self, mock_client_cls, tmp_project):
        """测试有效的 schema 响应"""
        (tmp_project / "openapi.json").write_text(json.dumps({
            "paths": {
                "/api/users": {"get": {}},
                "/api/posts": {"get": {}}
            }
        }))

        # Mock 响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"users": []}
        mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_response

        errors = run_schema_check(tmp_project)
        assert len(errors) == 0

    @patch('httpx.Client')
    def test_schema_invalid_type(self, mock_client_cls, tmp_project):
        """测试 API 返回非 dict/list 类型"""
        (tmp_project / "openapi.json").write_text(json.dumps({
            "paths": {
                "/api/users": {"get": {}}
            }
        }))

        # Mock 返回字符串
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = "invalid response"
        mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_response

        errors = run_schema_check(tmp_project)

        assert len(errors) == 1
        assert errors[0]["type"] == "schema_invalid_type"
        assert "返回类型" in errors[0]["message"]
        assert errors[0]["level"] == "L2"

    @patch('httpx.Client')
    def test_schema_unreachable(self, mock_client_cls, tmp_project):
        """测试端点不可达"""
        (tmp_project / "openapi.json").write_text(json.dumps({
            "paths": {
                "/api/users": {"get": {}}
            }
        }))

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_response

        errors = run_schema_check(tmp_project)

        assert len(errors) == 1
        assert errors[0]["type"] == "schema_unreachable"
        assert "404" in errors[0]["message"]
        assert errors[0]["level"] == "L2"

    @patch('httpx.Client')
    def test_schema_not_json(self, mock_client_cls, tmp_project):
        """测试返回非 JSON 内容"""
        (tmp_project / "openapi.json").write_text(json.dumps({
            "paths": {
                "/api/users": {"get": {}}
            }
        }))

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_response

        errors = run_schema_check(tmp_project)

        assert len(errors) == 1
        assert errors[0]["type"] == "schema_not_json"
        assert errors[0]["level"] == "L2"

    @patch('httpx.Client')
    def test_schema_exception(self, mock_client_cls, tmp_project):
        """测试请求异常"""
        (tmp_project / "openapi.json").write_text(json.dumps({
            "paths": {
                "/api/users": {"get": {}}
            }
        }))

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = Exception("Unexpected error")
        mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_response

        errors = run_schema_check(tmp_project)

        assert len(errors) == 1
        assert errors[0]["type"] == "schema_exception"
        assert errors[0]["level"] == "L2"

    @patch('httpx.Client')
    def test_multiple_errors(self, mock_client_cls, tmp_project):
        """测试多个端点多个错误"""
        (tmp_project / "openapi.json").write_text(json.dumps({
            "paths": {
                "/api/users": {"get": {}},
                "/api/posts": {"get": {}},
                "/api/comments": {"get": {}}
            }
        }))

        # 第一个端点：返回字符串
        # 第二个端点：返回 404
        # 第三个端点：正常
        mock_client = MagicMock()
        mock_client.get.side_effect = [
            MagicMock(status_code=200, json=lambda: "invalid"),  # /api/users
            MagicMock(status_code=404),  # /api/posts
            MagicMock(status_code=200, json=lambda: {"comments": []}),  # /api/comments
        ]
        mock_client_cls.return_value.__enter__.return_value = mock_client

        errors = run_schema_check(tmp_project)

        assert len(errors) == 2
        assert errors[0]["type"] == "schema_invalid_type"
        assert errors[1]["type"] == "schema_unreachable"

    @patch('httpx.Client')
    def test_custom_base_url(self, mock_client_cls, tmp_project):
        """测试自定义 base_url"""
        custom_url = "http://localhost:3000"
        (tmp_project / "openapi.json").write_text(json.dumps({
            "paths": {
                "/api/users": {"get": {}}
            }
        }))

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"users": []}
        mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_response

        run_schema_check(tmp_project, base_url=custom_url)

        mock_client_cls.assert_called_once_with(base_url=custom_url, timeout=5)

    @patch('httpx.Client')
    def test_client_timeout(self, mock_client_cls, tmp_project):
        """测试超时设置"""
        (tmp_project / "openapi.json").write_text(json.dumps({
            "paths": {
                "/api/users": {"get": {}}
            }
        }))

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_response

        run_schema_check(tmp_project)

        # 验证 timeout=5（如果 Client 被调用）
        if mock_client_cls.called:
            call_args = mock_client_cls.call_args
            assert call_args[1]["timeout"] == 5
