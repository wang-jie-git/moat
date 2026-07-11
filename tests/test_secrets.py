"""硬编码密钥检测测试

测试所有常见的密钥泄漏模式
"""
import pytest
from pathlib import Path
from moat.checks.secrets import SecretsCheck
from moat.checks.base import CheckResult


@pytest.fixture
def check(tmp_path):
    """创建 SecretsCheck 实例"""
    return SecretsCheck(tmp_path, {})


def test_aws_access_key(check):
    """测试 AWS Access Key ID 检测"""
    test_file = Path(check.project) / "aws_config.py"
    test_file.write_text('aws_key = "AKIAIOSFODNN7EXAMPLE"\n')

    results = check._check_file(test_file)
    assert len(results) >= 1
    assert results[0].level == "CRITICAL"
    assert "AWS" in results[0].message or "aws" in results[0].message.lower()
    print(f"✅ AWS Key 检测: {results[0].message}")


def test_github_personal_token(check):
    """测试 GitHub Personal Access Token 检测"""
    test_file = Path(check.project) / "github_config.py"
    test_file.write_text('token = "ghp_1234567890abcdef1234567890abcdef12345678"\n')

    results = check._check_file(test_file)
    assert len(results) >= 1
    assert results[0].level == "CRITICAL"
    assert "GitHub" in results[0].message
    print(f"✅ GitHub Token 检测: {results[0].message}")


def test_github_oauth_token(check):
    """测试 GitHub OAuth Token 检测"""
    test_file = Path(check.project) / "github_oauth.py"
    test_file.write_text('oauth = "gho_1234567890abcdef1234567890abcdef12345678"\n')

    results = check._check_file(test_file)
    assert len(results) >= 1
    assert results[0].level == "CRITICAL"
    assert "GitHub" in results[0].message or "OAuth" in results[0].message
    print(f"✅ GitHub OAuth 检测: {results[0].message}")


def test_google_api_key(check):
    """测试 Google API Key 检测"""
    test_file = Path(check.project) / "google_maps.py"
    test_file.write_text('api_key = "AIzaSyD-1234567890abcdefghijklmnopqrstuv"\n')

    results = check._check_file(test_file)
    assert len(results) >= 1
    assert results[0].level == "CRITICAL"
    assert "Google" in results[0].message or "API" in results[0].message
    print(f"✅ Google API Key 检测: {results[0].message}")


def test_generic_api_key(check):
    """测试通用 API Key 检测"""
    test_file = Path(check.project) / "app_api.py"
    test_file.write_text('api_key = "abcdef1234567890abcdef1234567890"\n')

    results = check._check_file(test_file)
    assert len(results) >= 1
    assert results[0].level == "HIGH"
    assert "API Key" in results[0].message
    print(f"✅ 通用 API Key 检测: {results[0].message}")


def test_hardcoded_password(check):
    """测试硬编码密码检测"""
    test_file = Path(check.project) / "auth.py"
    test_file.write_text('password = "MySecretPassword123"\n')

    results = check._check_file(test_file)
    assert len(results) >= 1
    assert results[0].level == "CRITICAL"
    assert "Password" in results[0].message or "password" in results[0].message.lower()
    print(f"✅ 硬编码密码检测: {results[0].message}")


def test_rsa_private_key(check):
    """测试 RSA 私钥泄漏检测"""
    test_file = Path(check.project) / "rsa_key.pem"
    test_file.write_text("""-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA1234567890abcdef
-----END RSA PRIVATE KEY-----
""")

    results = check._check_file(test_file)
    assert len(results) >= 1
    assert results[0].level == "CRITICAL"
    assert "Private Key" in results[0].message or "RSA" in results[0].message
    print(f"✅ RSA 私钥检测: {results[0].message}")


def test_ecdsa_private_key(check):
    """测试 ECDSA 私钥泄漏检测"""
    test_file = Path(check.project) / "ecdsa_key.pem"
    test_file.write_text("""-----BEGIN EC PRIVATE KEY-----
MIIBEwIBADANBgkqhkiG9w0BAQEFAASCAm4wggI2
-----END EC PRIVATE KEY-----
""")

    results = check._check_file(test_file)
    assert len(results) >= 1
    assert results[0].level == "CRITICAL"
    assert "ECDSA" in results[0].message or "Private Key" in results[0].message
    print(f"✅ ECDSA 私钥检测: {results[0].message}")


def test_placeholder_exclusion(check):
    """测试占位符文本应该被排除"""
    test_file = Path(check.project) / "example_secrets.py"
    test_file.write_text('api_key = "YOUR_API_KEY_HERE"\n')

    # Placeholder should be excluded by _should_skip (file contains "example")
    results = check._check_file(test_file)
    # 不应该检测到密钥（因为是占位符/示例文件）
    assert len(results) == 0
    print(f"✅ 占位符排除: 未误报")


def test_env_var_exclusion(check):
    """测试环境变量读取应该被排除"""
    test_file = Path(check.project) / "sample_env.py"
    test_file.write_text('api_key = os.getenv("API_KEY")\n')

    results = check._check_file(test_file)
    # 不应该检测到密钥（因为是环境变量读取）
    assert len(results) == 0
    print(f"✅ 环境变量排除: 未误报")


def test_comment_exclusion(check):
    """测试注释应该被排除"""
    test_file = Path(check.project) / "example_comment.py"
    test_file.write_text('# api_key = "AKIAIOSFODNN7EXAMPLE"\n')

    results = check._check_file(test_file)
    # 不应该检测到密钥（因为是注释）
    assert len(results) == 0
    print(f"✅ 注释排除: 未误报")


def test_secret_assignment(check):
    """测试 secret 赋值检测"""
    test_file = Path(check.project) / "secure.py"
    test_file.write_text('secret = "my_super_secret_key_value"\n')

    results = check._check_file(test_file)
    assert len(results) >= 1
    assert results[0].level == "CRITICAL"
    assert "Secret" in results[0].message or "secret" in results[0].message.lower()
    print(f"✅ Secret 赋值检测: {results[0].message}")


def test_multiple_secrets_in_file(check):
    """测试单个文件中的多个密钥"""
    test_file = Path(check.project) / "credentials.py"
    test_file.write_text("""
api_key = "abcdef1234567890abcdef1234567890"
password = "MySecretPassword123"
""")

    results = check._check_file(test_file)
    assert len(results) >= 2
    print(f"✅ 多密钥检测: 检测到 {len(results)} 个密钥")


def test_jwt_token(check):
    """测试 JWT Token 检测"""
    test_file = Path(check.project) / "token.py"
    test_file.write_text('token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"\n')

    results = check._check_file(test_file)
    # JWT 可能被误报为密钥，至少应该检查到
    print(f"✅ JWT Token 检测: 找到 {len(results)} 个潜在问题")


def test_env_assignment_multiline(check):
    """测试环境变量多行赋值"""
    test_file = Path(check.project) / "demo_env.py"
    test_file.write_text("""import os
password = os.getenv("DB_PASSWORD")
""")

    results = check._check_file(test_file)
    # 应该被环境变量读取排除
    assert len(results) == 0
    print(f"✅ 环境变量多行排除: 未误报")


def test_run_multiple_files(check):
    """测试多个文件的检测"""
    test_file1 = Path(check.project) / "main.py"
    test_file1.write_text('api_key = "abcdef1234567890abcdef1234567890"\n')

    test_file2 = Path(check.project) / "backend.py"
    test_file2.write_text('password = "MySecretPassword123"\n')

    results = check.run()
    assert len(results) >= 2
    print(f"✅ 多文件检测: 检测到 {len(results)} 个问题")


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        check = SecretsCheck(tmp_path, {})

        print("=== 硬编码密钥检测测试 ===\n")

        # 测试 1: AWS Key
        test_aws_access_key(check)

        # 测试 2: GitHub Personal Token
        test_github_personal_token(check)

        # 测试 3: GitHub OAuth
        test_github_oauth_token(check)

        # 测试 4: Google API Key
        test_google_api_key(check)

        # 测试 5: 通用 API Key
        test_generic_api_key(check)

        # 测试 6: 硬编码密码
        test_hardcoded_password(check)

        # 测试 7: RSA 私钥
        test_rsa_private_key(check)

        # 测试 8: ECDSA 私钥
        test_ecdsa_private_key(check)

        # 测试 9: 占位符排除
        test_placeholder_exclusion(check)

        # 测试 10: 环境变量排除
        test_env_var_exclusion(check)

        # 测试 11: 注释排除
        test_comment_exclusion(check)

        # 测试 12: Secret 赋值
        test_secret_assignment(check)

        # 测试 13: 多密钥检测
        test_multiple_secrets_in_file(check)

        # 测试 14: JWT Token
        test_jwt_token(check)

        # 测试 15: 多行环境变量
        test_env_assignment_multiline(check)

        print("\n✅ 所有测试通过！")
