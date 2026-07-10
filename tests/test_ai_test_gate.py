"""
测试 AI 测试门票 Gatekeeper 规则

验证：
1. 规则已注册
2. 检测到缺失测试文件时返回 CRITICAL 违规
3. 有测试文件时不违规
"""

import tempfile
from pathlib import Path
from moat.gatekeeper import ArchitectureGatekeeper, GatekeeperConfig


def test_test_coverage_gate_missing_test():
    """测试：业务代码缺少测试文件时应该被拦截"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # 1. 创建业务代码
        services_dir = tmpdir / "services"
        services_dir.mkdir()
        business_file = services_dir / "user.py"
        business_file.write_text("""
def create_user(email: str, password: str):
    '''创建用户'''
    pass
""", encoding="utf-8")

        # 2. 不创建测试文件（模拟缺失测试）
        # tests/unit/services/test_user.py 不存在

        # 3. 执行 Gatekeeper 检查
        gatekeeper = ArchitectureGatekeeper(tmpdir)
        result = gatekeeper.check_file(str(business_file), business_file.read_text())

        # 4. 验证结果
        assert not result.passed, "应该因为缺少测试文件而失败"
        assert result.should_block, "应该阻止写入"

        # 检查是否有 test_coverage_gate 违规
        test_violations = [v for v in result.violations if v.rule_id == "test_coverage_gate"]
        assert len(test_violations) > 0, "应该有 test_coverage_gate 违规"

        violation = test_violations[0]
        assert violation.severity.value == "critical", "应该是 CRITICAL 级别"
        assert "缺少测试文件" in violation.message, "消息应该包含'缺少测试文件'"

        print("✅ 测试通过：缺失测试文件时正确拦截")
        return True


def test_test_coverage_gate_with_test():
    """测试：有测试文件时不应该拦截"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # 1. 创建业务代码
        services_dir = tmpdir / "services"
        services_dir.mkdir()
        business_file = services_dir / "user.py"
        business_file.write_text("""
def create_user(email: str, password: str):
    '''创建用户'''
    pass
""", encoding="utf-8")

        # 2. 创建测试文件
        tests_dir = tmpdir / "tests" / "unit" / "services"
        tests_dir.mkdir(parents=True)
        test_file = tests_dir / "test_user.py"
        test_file.write_text("""
def test_create_user():
    assert True
""", encoding="utf-8")

        # 3. 执行 Gatekeeper 检查
        gatekeeper = ArchitectureGatekeeper(tmpdir)
        result = gatekeeper.check_file(str(business_file), business_file.read_text())

        # 4. 验证结果（应该通过，因为没有 CRITICAL 违规）
        test_violations = [v for v in result.violations if v.rule_id == "test_coverage_gate"]
        assert len(test_violations) == 0, "有测试文件时不应该有 test_coverage_gate 违规"

        print("✅ 测试通过：有测试文件时不拦截")
        return True


def test_skip_non_business_code():
    """测试：不检查非业务代码（如测试文件、__init__.py）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # 创建测试文件
        test_file = tmpdir / "tests" / "test_something.py"
        test_file.parent.mkdir()
        test_file.write_text("def test_foo(): pass", encoding="utf-8")

        # 创建 __init__.py
        init_file = tmpdir / "services" / "__init__.py"
        init_file.parent.mkdir()
        init_file.write_text("", encoding="utf-8")

        gatekeeper = ArchitectureGatekeeper(tmpdir)

        # 测试文件不应该被检查
        result1 = gatekeeper.check_file(str(test_file), test_file.read_text())
        test_violations1 = [v for v in result1.violations if v.rule_id == "test_coverage_gate"]
        assert len(test_violations1) == 0, "测试文件不应该被检查"

        # __init__.py 不应该被检查
        result2 = gatekeeper.check_file(str(init_file), init_file.read_text())
        test_violations2 = [v for v in result2.violations if v.rule_id == "test_coverage_gate"]
        assert len(test_violations2) == 0, "__init__.py 不应该被检查"

        print("✅ 测试通过：跳过非业务代码")
        return True


if __name__ == "__main__":
    print("\n🧪 测试 AI 测试门票规则\n")

    try:
        test_test_coverage_gate_missing_test()
        test_test_coverage_gate_with_test()
        test_skip_non_business_code()

        print("\n✅ 所有测试通过！")
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        raise
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        raise
