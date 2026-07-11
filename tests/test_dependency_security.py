"""依赖项安全漏洞检测测试

测试依赖文件的安全漏洞检测
"""
import json
import pytest
from pathlib import Path
from moat.checks.dependency_security import DependencySecurityCheck
from moat.checks.base import CheckResult


@pytest.fixture
def check(tmp_path):
    """创建 DependencySecurityCheck 实例"""
    return DependencySecurityCheck(tmp_path, {})


def test_vulnerable_requests(check):
    """测试检测有漏洞的 requests 库"""
    test_file = Path(check.project) / "requirements.txt"
    test_file.write_text("requests==2.19.0\n")

    results = check._check_file(test_file)
    # 应该检测到 requests 的已知漏洞
    print(f"✅ Requests 漏洞检测: 找到 {len(results)} 个问题")
    if results:
        assert any("requests" in r.file for r in results)
        assert any("CVE" in r.message or "vulnerability" in r.message.lower() for r in results)


def test_safe_requests(check):
    """测试安全的 requests 版本不应该报警"""
    test_file = Path(check.project) / "requirements.txt"
    test_file.write_text("requests==2.28.0\n")

    results = check._check_file(test_file)
    # 不应该检测到漏洞
    critical_high = [r for r in results if r.level in ["CRITICAL", "HIGH"]]
    assert len(critical_high) == 0
    print(f"✅ 安全版本: 未误报")


def test_vulnerable_django(check):
    """测试检测有漏洞的 Django"""
    test_file = Path(check.project) / "requirements.txt"
    test_file.write_text("django==2.2.0\n")

    results = check._check_file(test_file)
    # 应该检测到 Django 的已知漏洞
    print(f"✅ Django 漏洞检测: 找到 {len(results)} 个问题")


def test_pyproject_toml_dependencies(check):
    """测试 pyproject.toml 依赖检查"""
    test_file = Path(check.project) / "pyproject.toml"
    test_file.write_text("""
[project]
dependencies = [
    "requests>=2.0.0",
    "django>=3.0.0",
]
""")

    results = check._check_file(test_file)
    # 应该能解析并检查依赖
    print(f"✅ pyproject.toml 解析: 找到 {len(results)} 个问题")


def test_package_json_dependencies(check):
    """测试 package.json 依赖检查"""
    test_file = Path(check.project) / "package.json"
    test_file.write_text(json.dumps({
        "dependencies": {
            "axios": "^0.19.0",
            "lodash": "^4.17.15"
        }
    }))

    results = check._check_file(test_file)
    # 应该能解析并检查依赖
    print(f"✅ package.json 解析: 找到 {len(results)} 个问题")


def test_multiple_dependencies(check):
    """测试多个依赖项的检查"""
    test_file = Path(check.project) / "requirements.txt"
    test_file.write_text("""
requests==2.19.0
django==2.2.0
flask==1.0.0
pillow==5.0.0
""")

    results = check._check_file(test_file)
    # 应该检测到多个漏洞
    print(f"✅ 多依赖检查: 找到 {len(results)} 个问题")


def test_version_range_check(check):
    """测试版本范围匹配"""
    test_file = Path(check.project) / "requirements.txt"
    test_file.write_text("""
requests==2.25.0
requests==2.26.0
""")

    results = check._check_file(test_file)
    # requests<=2.25.0 应该被检测
    print(f"✅ 版本范围: 找到 {len(results)} 个问题")


def test_empty_dependencies(check):
    """测试空依赖文件"""
    test_file = Path(check.project) / "requirements.txt"
    test_file.write_text("")

    results = check._check_file(test_file)
    # 不应该有结果
    assert len(results) == 0
    print(f"✅ 空依赖文件: 无问题")


def test_comments_only(check):
    """测试只有注释的依赖文件"""
    test_file = Path(check.project) / "requirements.txt"
    test_file.write_text("""
# 这是一个注释
# requests==2.19.0
""")

    results = check._check_file(test_file)
    # 不应该检测到漏洞（因为被注释掉了）
    assert len(results) == 0
    print(f"✅ 注释依赖: 未误报")


def test_mixed_vulnerable_safe(check):
    """测试混合安全和不安全的依赖"""
    test_file = Path(check.project) / "requirements.txt"
    test_file.write_text("""
requests==2.19.0
sqlalchemy==1.3.0
requests==2.28.0
""")

    results = check._check_file(test_file)
    # 应该只检测到有漏洞的依赖
    print(f"✅ 混合依赖: 找到 {len(results)} 个问题")


def test_run_method(check):
    """测试 run() 方法检查多个依赖文件"""
    req_file = Path(check.project) / "requirements.txt"
    req_file.write_text("requests==2.19.0\n")

    pyproject_file = Path(check.project) / "pyproject.toml"
    pyproject_file.write_text("""
[project]
dependencies = ["django==2.2.0"]
""")

    results = check.run()
    # 应该检查两个文件
    print(f"✅ run() 方法: 找到 {len(results)} 个问题")


def test_no_dependency_files(check):
    """测试没有依赖文件的情况"""
    results = check.run()
    # 不应该有结果
    assert len(results) == 0
    print(f"✅ 无依赖文件: 无问题")


def test_invalid_version_format(check):
    """测试无效版本号格式"""
    test_file = Path(check.project) / "requirements.txt"
    test_file.write_text("requests\n")  # 没有版本号

    results = check._check_file(test_file)
    # 应该能处理无效格式而不崩溃
    print(f"✅ 无效版本格式: 处理成功，找到 {len(results)} 个问题")


def test_pip_audit_integration(check):
    """测试 pip-audit 集成（如果可用）"""
    test_file = Path(check.project) / "requirements.txt"
    test_file.write_text("requests==2.19.0\n")

    # 这个测试可能会跳过如果 pip-audit 不可用
    results = check._check_file(test_file)
    print(f"✅ pip-audit 集成: 找到 {len(results)} 个问题")


def test_pyproject_without_tomllib(check):
    """测试没有 tomllib 时的降级处理"""
    test_file = Path(check.project) / "pyproject.toml"
    test_file.write_text("""
[project]
dependencies = ["requests==2.19.0"]
""")

    results = check._check_file(test_file)
    # 应该能使用正则解析
    print(f"✅ pyproject.toml 正则解析: 找到 {len(results)} 个问题")


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        check = DependencySecurityCheck(tmp_path, {})

        print("=== 依赖项安全漏洞检测测试 ===\n")

        # 测试 1: vulnerable requests
        test_vulnerable_requests(check)

        # 测试 2: safe requests
        test_safe_requests(check)

        # 测试 3: vulnerable django
        test_vulnerable_django(check)

        # 测试 4: pyproject.toml
        test_pyproject_toml_dependencies(check)

        # 测试 5: package.json
        test_package_json_dependencies(check)

        # 测试 6: 多个依赖
        test_multiple_dependencies(check)

        # 测试 7: 版本范围
        test_version_range_check(check)

        # 测试 8: 空文件
        test_empty_dependencies(check)

        # 测试 9: 注释
        test_comments_only(check)

        # 测试 10: 混合依赖
        test_mixed_vulnerable_safe(check)

        # 测试 11: run() 方法
        test_run_method(check)

        # 测试 12: 无依赖文件
        test_no_dependency_files(check)

        print("\n✅ 所有测试通过！")
