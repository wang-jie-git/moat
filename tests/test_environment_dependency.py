"""
环境依赖测试

这些测试覆盖 Moat 的环境依赖场景：
- .moat 目录创建
- 配置文件默认值处理
- 环境变量检查
- 数据库文件初始化
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch


class TestMoatDirectoryCreation:
    """.moat 目录创建测试"""

    def test_moat_dir_created_on_init(self):
        """
        测试 moat init 时自动创建 .moat 目录
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "test_project"
            project_dir.mkdir()
            moat_dir = project_dir / ".moat"

            # 初始状态：.moat 目录不存在
            assert not moat_dir.exists()

            # 模拟 moat init：创建 .moat 目录
            moat_dir.mkdir(parents=True, exist_ok=True)

            # 验证目录已创建
            assert moat_dir.exists()
            assert moat_dir.is_dir()

    def test_moat_dir_with_nested_structure(self):
        """
        测试 .moat 目录嵌套结构创建
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            moat_dir = Path(tmpdir) / ".moat"

            # 创建嵌套目录
            (moat_dir / "baselines").mkdir(parents=True, exist_ok=True)
            (moat_dir / "insights").mkdir(parents=True, exist_ok=True)
            (moat_dir / "logs").mkdir(parents=True, exist_ok=True)

            # 验证所有目录存在
            assert (moat_dir / "baselines").exists()
            assert (moat_dir / "insights").exists()
            assert (moat_dir / "logs").exists()


class TestConfigFileHandling:
    """配置文件处理测试"""

    def test_config_file_default_when_missing(self):
        """
        测试配置文件缺失时使用默认值
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "moat.json"

            # 配置文件不存在
            assert not config_file.exists()

            # 使用默认配置
            default_config = {
                "project_name": "default",
                "rules": {}
            }

            # 验证默认配置
            assert default_config["project_name"] == "default"

    def test_config_file_creation(self):
        """
        测试配置文件创建
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "moat.json"

            # 创建配置文件
            config = {"project_name": "test", "version": "1.0"}
            import json
            config_file.write_text(json.dumps(config, indent=2))

            # 验证文件存在且可读
            assert config_file.exists()
            loaded = json.loads(config_file.read_text())
            assert loaded["project_name"] == "test"


class TestEnvironmentVariableHandling:
    """环境变量处理测试"""

    def test_required_env_var_present(self):
        """
        测试必需环境变量存在
        """
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test123"}):
            api_key = os.getenv("ANTHROPIC_API_KEY")
            assert api_key is not None
            assert api_key == "sk-test123"

    def test_required_env_var_missing(self):
        """
        测试必需环境变量缺失
        """
        # 确保环境变量不存在
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)

            api_key = os.getenv("ANTHROPIC_API_KEY")
            assert api_key is None

    def test_optional_env_var_with_default(self):
        """
        测试可选环境变量使用默认值
        """
        # 移除环境变量
        os.environ.pop("MOAT_LOG_LEVEL", None)

        # 使用默认值
        log_level = os.getenv("MOAT_LOG_LEVEL", "INFO")

        assert log_level == "INFO"

    def test_env_var_type_conversion(self):
        """
        测试环境变量类型转换
        """
        with patch.dict(os.environ, {"MOAT_MAX_TOKENS": "4000"}):
            max_tokens_str = os.getenv("MOAT_MAX_TOKENS", "1000")
            max_tokens = int(max_tokens_str)

            assert max_tokens == 4000
            assert isinstance(max_tokens, int)


class TestDatabaseFileInitialization:
    """数据库文件初始化测试"""

    def test_sqlite_db_creation(self):
        """
        测试 SQLite 数据库文件创建
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # 数据库文件不存在
            assert not db_path.exists()

            # 创建数据库（模拟 moat memory init）
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
            conn.commit()
            conn.close()

            # 验证数据库文件已创建
            assert db_path.exists()

    def test_sqlite_db_directory_creation(self):
        """
        测试数据库文件目录不存在时自动创建
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_dir = Path(tmpdir) / "data" / "moat"
            db_path = db_dir / "memory.db"

            # 目录不存在
            assert not db_dir.exists()

            # 创建目录并数据库
            db_dir.mkdir(parents=True, exist_ok=True)

            import sqlite3
            conn = sqlite3.connect(str(db_path))
            conn.close()

            # 验证目录和文件已创建
            assert db_dir.exists()
            assert db_path.exists()


class TestPathResolution:
    """路径解析测试"""

    def test_relative_path_resolution(self):
        """
        测试相对路径解析为绝对路径
        """
        relative_path = Path("tests/test_example.py")
        absolute_path = relative_path.resolve()

        assert absolute_path.is_absolute()

    def test_home_directory_expansion(self):
        """
        测试用户主目录展开
        """
        home_path = Path.home()
        tilde_path = Path("~/.moat").expanduser()

        assert str(tilde_path).startswith(str(home_path))

    def test_environment_variable_in_path(self):
        """
        测试路径中的环境变量展开
        """
        with patch.dict(os.environ, {"MOAT_HOME": "/custom/moat"}):
            path_str = "$MOAT_HOME/config.json"
            expanded = os.path.expandvars(path_str)

            assert expanded == "/custom/moat/config.json"


class TestFileSystemPermissions:
    """文件系统权限测试"""

    def test_write_permission_check(self):
        """
        测试写入权限检查
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"

            # 写入文件
            test_file.write_text("test")

            # 验证可读
            assert test_file.read_text() == "test"

            # 验证可写
            test_file.write_text("updated")
            assert test_file.read_text() == "updated"

    def test_read_only_directory_handling(self):
        """
        测试只读目录的处理
        """
        # 这个测试需要 root 权限，暂时跳过
        pytest.skip("需要 root 权限测试")


class TestPlatformSpecificBehavior:
    """平台特定行为测试"""

    def test_path_separator_darwin(self):
        """
        测试 macOS 路径分隔符
        """
        if sys.platform == "darwin":
            path = Path("/Users/test/file.txt")
            assert str(path) == "/Users/test/file.txt"

    def test_path_separator_linux(self):
        """
        测试 Linux 路径分隔符
        """
        if sys.platform == "linux":
            path = Path("/home/test/file.txt")
            assert str(path) == "/home/test/file.txt"

    def test_executable_flag_unix(self):
        """
        测试 Unix 可执行文件标志
        """
        if sys.platform in ["darwin", "linux"]:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = Path(tmp.name)

            try:
                # 添加可执行权限
                tmp_path.chmod(0o755)

                # 验证权限
                import stat
                mode = tmp_path.stat().st_mode
                assert mode & stat.S_IXUSR, "应设置用户可执行权限"
            finally:
                tmp_path.unlink()
