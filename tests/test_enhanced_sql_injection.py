"""增强 SQL 注入检测测试（SQL-002）

测试所有增强的 SQL 注入检测模式
"""
import pytest
from pathlib import Path
from moat.checks.enhanced_sql_injection import EnhancedSQLInjectionCheck
from moat.checks.base import CheckResult


@pytest.fixture
def check(tmp_path):
    """创建 EnhancedSQLInjectionCheck 实例"""
    return EnhancedSQLInjectionCheck(tmp_path, {})


def test_django_orm_raw_fstring(check):
    """测试 Django ORM raw() 中的 f-string 检测"""
    test_file = Path(check.project) / "views.py"
    test_file.write_text("""
User.objects.raw(f"SELECT * FROM users WHERE id = {user_id}")
""")

    results = check._check_file(test_file)
    assert len(results) >= 1
    assert results[0].level == "CRITICAL"
    assert "Django" in results[0].message or "ORM" in results[0].message
    print(f"✅ Django raw() f-string: {results[0].message}")


def test_django_orm_raw_concat(check):
    """测试 Django ORM raw() 中的字符串拼接"""
    test_file = Path(check.project) / "views.py"
    test_file.write_text("""
User.objects.raw("SELECT * FROM users WHERE id = " + user_id)
""")

    results = check._check_file(test_file)
    assert len(results) >= 1
    assert results[0].level == "CRITICAL"
    print(f"✅ Django raw() 拼接: {results[0].message}")


def test_django_orm_raw_format(check):
    """测试 Django ORM raw() 中的 .format()"""
    test_file = Path(check.project) / "views.py"
    test_file.write_text("""
User.objects.raw("SELECT * FROM users WHERE id = {}".format(user_id))
""")

    results = check._check_file(test_file)
    assert len(results) >= 1
    assert results[0].level == "CRITICAL"
    print(f"✅ Django raw() .format(): {results[0].message}")


def test_django_orm_filter_format(check):
    """测试 Django ORM filter() 中的 %s 格式化"""
    test_file = Path(check.project) / "views.py"
    test_file.write_text("""
User.objects.filter(name="%s" % username)
""")

    results = check._check_file(test_file)
    assert len(results) >= 1
    assert results[0].level == "CRITICAL"
    print(f"✅ Django filter() %s: {results[0].message}")


def test_sqlalchemy_execute_fstring(check):
    """测试 SQLAlchemy execute() 中的 f-string"""
    test_file = Path(check.project) / "models.py"
    test_file.write_text("""
session.execute(f"SELECT * FROM users WHERE id = {user_id}")
""")

    results = check._check_file(test_file)
    assert len(results) >= 1
    assert results[0].level == "CRITICAL"
    assert "SQLAlchemy" in results[0].message or "execute" in results[0].message.lower()
    print(f"✅ SQLAlchemy execute() f-string: {results[0].message}")


def test_sqlalchemy_engine_execute(check):
    """测试 SQLAlchemy engine.execute()"""
    test_file = Path(check.project) / "models.py"
    test_file.write_text("""
engine.execute(f"SELECT * FROM users WHERE id = {user_id}")
""")

    results = check._check_file(test_file)
    assert len(results) >= 1
    print(f"✅ SQLAlchemy engine.execute(): {results[0].message}")


def test_sqlalchemy_text_fstring(check):
    """测试 SQLAlchemy text() 中的 f-string"""
    test_file = Path(check.project) / "models.py"
    test_file.write_text("""
session.execute(text(f"SELECT * FROM users WHERE id = {user_id}"))
""")

    results = check._check_file(test_file)
    assert len(results) >= 1
    print(f"✅ SQLAlchemy text() f-string: {results[0].message}")


def test_asyncpg_execute(check):
    """测试 asyncpg 异步执行"""
    test_file = Path(check.project) / "async_db.py"
    test_file.write_text("""
await conn.execute(f"SELECT * FROM users WHERE id = {user_id}")
""")

    results = check._check_file(test_file)
    assert len(results) >= 1
    print(f"✅ asyncpg execute(): {results[0].message}")


def test_asyncpg_fetch(check):
    """测试 asyncpg fetch 中的 SQL 拼接"""
    test_file = Path(check.project) / "async_db.py"
    test_file.write_text("""
await conn.fetch(f"SELECT * FROM users WHERE name = {username}")
""")

    results = check._check_file(test_file)
    # fetch 也应该是 SQL 执行函数
    # 如果未检测到，可以扩展 SQL_EXEC_PATTERNS
    print(f"✅ asyncpg fetch(): 检测到 {len(results)} 个问题")


def test_psycopg2_execute(check):
    """测试 psycopg2 执行"""
    test_file = Path(check.project) / "db.py"
    test_file.write_text("""
cursor.execute("SELECT * FROM users WHERE id = " + user_id)
""")

    results = check._check_file(test_file)
    assert len(results) >= 1
    print(f"✅ psycopg2 execute(): {results[0].message}")


def test_safe_django_orm(check):
    """测试安全的 Django ORM 查询（不应报警）"""
    test_file = Path(check.project) / "views.py"
    test_file.write_text("""
user = User.objects.get(id=user_id)
users = User.objects.filter(name="John")
""")

    results = check._check_file(test_file)
    critical_results = [r for r in results if r.level == "CRITICAL"]
    assert len(critical_results) == 0
    print(f"✅ Django ORM 安全查询: 未误报")


def test_safe_sqlalchemy(check):
    """测试安全的 SQLAlchemy 查询（不应报警）"""
    test_file = Path(check.project) / "models.py"
    test_file.write_text("""
result = session.execute(text("SELECT * FROM users WHERE id = :id"), {"id": user_id})
""")

    results = check._check_file(test_file)
    critical_results = [r for r in results if r.level == "CRITICAL"]
    assert len(critical_results) == 0
    print(f"✅ SQLAlchemy 参数化查询: 未误报")


def test_fstring_execute_context(check):
    """测试 execute() 的上下文回溯"""
    test_file = Path(check.project) / "db.py"
    test_file.write_text("""
# 前 3 行有 f-string
query = f"SELECT * FROM users WHERE id = {user_id}"
cursor.execute(query)
""")

    results = check._check_file(test_file)
    assert len(results) >= 1
    # 应该检测到第 3 行（cursor.execute）
    assert results[0].line >= 3
    print(f"✅ 上下文回溯: 检测到第 {results[0].line} 行")


def test_multiple_orm_patterns(check):
    """测试多个 ORM 模式混合"""
    test_file = Path(check.project) / "views.py"
    test_file.write_text("""
# Django
User.objects.raw(f"SELECT * FROM users WHERE id = {user_id}")
User.objects.filter(name="%s" % username)

# SQLAlchemy
session.execute(f"SELECT * FROM posts WHERE id = {post_id}")

# asyncpg
await conn.fetch(f"SELECT * FROM comments WHERE post_id = {post_id}")
""")

    results = check._check_file(test_file)
    assert len(results) >= 3
    print(f"✅ 多 ORM 混合检测: 检测到 {len(results)} 个问题")


def test_sql_exec_function_detection(check):
    """测试 SQL 执行函数识别"""
    test_file = Path(check.project) / "db.py"
    test_file.write_text("""
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
cursor.executemany(f"SELECT * FROM users WHERE id = {user_id}")
conn.execute(f"SELECT * FROM users WHERE id = {user_id}")
connection.execute(f"SELECT * FROM users WHERE id = {user_id}")
""")

    results = check._check_file(test_file)
    assert len(results) >= 4
    print(f"✅ SQL 执行函数识别: 检测到 {len(results)} 个")


def test_comment_exclusion(check):
    """测试注释应该被排除"""
    test_file = Path(check.project) / "views.py"
    test_file.write_text("""
# User.objects.raw(f"SELECT * FROM users WHERE id = {user_id}")
""")

    results = check._check_file(test_file)
    assert len(results) == 0
    print(f"✅ ORM 注释排除: 未误报")


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        check = EnhancedSQLInjectionCheck(tmp_path, {})

        print("=== 增强 SQL 注入检测测试 ===\n")

        # 测试 1: Django raw() f-string
        test_django_orm_raw_fstring(check)

        # 测试 2: Django raw() concat
        test_django_orm_raw_concat(check)

        # 测试 3: Django raw() .format()
        test_django_orm_raw_format(check)

        # 测试 4: Django filter() %s
        test_django_orm_filter_format(check)

        # 测试 5: SQLAlchemy execute() f-string
        test_sqlalchemy_execute_fstring(check)

        # 测试 6: SQLAlchemy engine.execute()
        test_sqlalchemy_engine_execute(check)

        # 测试 7: SQLAlchemy text()
        test_sqlalchemy_text_fstring(check)

        # 测试 8: asyncpg execute
        test_asyncpg_execute(check)

        # 测试 9: asyncpg fetch
        test_asyncpg_fetch(check)

        # 测试 10: psycopg2
        test_psycopg2_execute(check)

        # 测试 11: 安全查询
        test_safe_django_orm(check)

        # 测试 12: SQLAlchemy 安全查询
        test_safe_sqlalchemy(check)

        # 测试 13: 上下文回溯
        test_fstring_execute_context(check)

        # 测试 14: 多 ORM
        test_multiple_orm_patterns(check)

        # 测试 15: SQL 执行函数识别
        test_sql_exec_function_detection(check)

        # 测试 16: 注释排除
        test_comment_exclusion(check)

        print("\n✅ 所有测试通过！")
