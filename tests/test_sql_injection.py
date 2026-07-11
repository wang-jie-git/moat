"""SQL 注入检测测试

测试所有常见的 SQL 注入模式
"""
import pytest
from pathlib import Path
from moat.checks.sql_injection import SQLInjectionCheck
from moat.checks.base import CheckResult


@pytest.fixture
def check(tmp_path):
    """创建 SQLInjectionCheck 实例"""
    return SQLInjectionCheck(tmp_path, {})


def test_fstring_injection(check):
    """测试 f-string SQL 注入（同一行）"""
    test_file = Path(check.project) / "test_fstring.py"
    test_file.write_text('cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")\n')

    results = check._check_file(test_file)
    assert len(results) >= 1
    assert results[0].level == "CRITICAL"
    assert "SQL 注入" in results[0].message
    print(f"✅ f-string 检测: {results[0].message}")


def test_format_injection(check):
    """测试 .format() SQL 注入"""
    test_file = Path(check.project) / "test_format.py"
    test_file.write_text("""
query = "SELECT * FROM users WHERE id = {}".format(user_id)
cursor.execute(query)
""")

    results = check._check_file(test_file)
    assert len(results) >= 1
    assert results[0].level == "CRITICAL"
    print(f"✅ .format() 检测: {results[0].message}")


def test_percent_format_injection(check):
    """测试 % 格式化 SQL 注入"""
    test_file = Path(check.project) / "test_percent.py"
    test_file.write_text("""
query = "SELECT * FROM users WHERE id = %s" % user_id
cursor.execute(query)
""")

    results = check._check_file(test_file)
    assert len(results) >= 1
    assert results[0].level == "CRITICAL"
    print(f"✅ % 格式化 检测: {results[0].message}")


def test_concat_injection(check):
    """测试字符串拼接 SQL 注入"""
    test_file = Path(check.project) / "test_concat.py"
    test_file.write_text('query = "SELECT * FROM users WHERE id = " + user_id\ncursor.execute(query)\n')

    results = check._check_file(test_file)
    assert len(results) >= 1
    assert results[0].level == "CRITICAL"
    print(f"✅ 字符串拼接 检测: {results[0].message}")


def test_safe_query(check):
    """测试安全的参数化查询（不应该报警）"""
    test_file = Path(check.project) / "test_safe.py"
    test_file.write_text("""
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
""")

    results = check._check_file(test_file)
    # 应该没有 CRITICAL 警告
    critical_results = [r for r in results if r.level == "CRITICAL"]
    assert len(critical_results) == 0
    print(f"✅ 参数化查询: 未误报")


def test_find_sql_exec_points(check):
    """测试 SQL 执行点定位"""
    content = """
cursor.execute("SELECT * FROM users")
db.query("DELETE FROM logs")
engine.raw("SELECT * FROM posts")
"""
    lines = content.split("\n")
    exec_points = check._find_sql_exec_points(content)

    assert len(exec_points) == 3
    assert exec_points[0] == 2  # cursor.execute
    assert exec_points[1] == 3  # db.query
    assert exec_points[2] == 4  # engine.raw
    print(f"✅ SQL 执行点定位: {exec_points}")


def test_context_check(check):
    """测试上下文回溯"""
    test_file = Path(check.project) / "test_context.py"
    test_file.write_text("""
# 前 3 行有 f-string
query = f"SELECT * FROM users WHERE id = {user_id}"
cursor.execute(query)
""")

    results = check._check_file(test_file)
    assert len(results) >= 1
    assert results[0].line == 4  # cursor.execute 在第 4 行（包含前导空行）
    print(f"✅ 上下文回溯: 检测到第 {results[0].line} 行的 SQL 注入")


if __name__ == "__main__":
    # 手动运行测试
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        check = SQLInjectionCheck(tmp_path, {})

        print("=== SQL 注入检测测试 ===\n")

        # 测试 1: f-string
        test_fstring_injection(check)

        # 测试 2: .format()
        test_format_injection(check)

        # 测试 3: % 格式化
        test_percent_format_injection(check)

        # 测试 4: 字符串拼接
        test_concat_injection(check)

        # 测试 5: 安全查询
        test_safe_query(check)

        # 测试 6: SQL 执行点定位
        test_find_sql_exec_points(check)

        # 测试 7: 上下文回溯
        test_context_check(check)

        print("\n✅ 所有测试通过！")
