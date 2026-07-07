"""知识图谱记忆扩展测试"""
import tempfile
import time
from pathlib import Path
from datetime import datetime

import pytest

from moat.memory.bridge import SharedStorageBridge, BridgeConfig


@pytest.fixture
def temp_db():
    """创建临时数据库"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        bridge = SharedStorageBridge(BridgeConfig(db_path=db_path))
        bridge.initialize()
        yield bridge
        bridge.close()


class TestKnowledgeGraphExtensions:
    """知识图谱扩展测试"""

    def test_fix_history_table_exists(self, temp_db):
        """测试修复历史表已创建"""
        import sqlite3

        conn = sqlite3.connect(str(temp_db.config.db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='fix_history'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_weak_points_table_exists(self, temp_db):
        """测试架构薄弱点表已创建"""
        import sqlite3

        conn = sqlite3.connect(str(temp_db.config.db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='weak_points'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_fix_patterns_table_exists(self, temp_db):
        """测试修复模式表已创建"""
        import sqlite3

        conn = sqlite3.connect(str(temp_db.config.db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='fix_patterns'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_dream_triggers_table_exists(self, temp_db):
        """测试梦境触发表已创建"""
        import sqlite3

        conn = sqlite3.connect(str(temp_db.config.db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='dream_triggers'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_smart_hints_table_exists(self, temp_db):
        """测试智能提示表已创建"""
        import sqlite3

        conn = sqlite3.connect(str(temp_db.config.db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='smart_hints'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_write_and_query_bug_memory(self, temp_db):
        """测试写入和查询 Bug 记忆"""
        error = {
            "type": "race_condition",
            "file": "src/auth/session.py",
            "line": 142,
            "message": "pendingMessageRef 缺少时序注释",
            "pain_score": 85.0,
        }

        bug_id = temp_db.write_bug_memory(error)
        assert bug_id is not None
        assert bug_id.startswith("bug_")

        # 查询统计
        stats = temp_db.get_statistics()
        assert stats["bug_memories"] >= 1

    def test_repeated_bug_detection(self, temp_db):
        """测试重复 Bug 检测"""
        import sqlite3

        # 写入 3 次相同 Bug（手动更新 occurrence_count）
        bug_id = "bug_test_001"
        now = datetime.now().isoformat()

        conn = sqlite3.connect(str(temp_db.config.db_path))
        for i in range(3):
            occurrence_count = i + 1
            conn.execute("""
                INSERT OR REPLACE INTO bug_memories (
                    id, error_type, file_path, line, pain_score,
                    message, first_seen, last_seen, occurrence_count, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bug_id,
                "race_condition",
                "src/auth/session.py",
                142,
                85.0,
                "pendingMessageRef 缺少时序注释",
                now,
                now,
                occurrence_count,
                "moat",
            ))
        conn.commit()
        conn.close()

        # 查询 Bug
        conn = sqlite3.connect(str(temp_db.config.db_path))
        result = conn.execute(
            "SELECT occurrence_count FROM bug_memories WHERE id = ?", (bug_id,)
        ).fetchone()

        assert result is not None
        assert result[0] == 3  # occurrence_count
        conn.close()

    def test_weak_point_identification(self, temp_db):
        """测试架构薄弱点识别"""
        import sqlite3

        # 手动添加薄弱点记录
        conn = sqlite3.connect(str(temp_db.config.db_path))
        conn.execute(
            """
            INSERT INTO weak_points (id, file_path, issue_type, frequency, recommendation, priority)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("wp_001", "src/auth/session.py", "race_condition", 10, "重构 session 管理逻辑", 5),
        )
        conn.commit()

        # 查询薄弱点
        result = conn.execute(
            "SELECT * FROM weak_points WHERE file_path = ?", ("src/auth/session.py",)
        ).fetchone()

        assert result is not None
        # weak_points 表结构: id, file_path, issue_type, frequency, last_occurred, recommendation, priority, created_at, updated_at
        assert result[3] == 10  # frequency
        assert result[6] == 5  # priority
        conn.close()

    def test_fix_pattern_storage(self, temp_db):
        """测试修复模式存储"""
        import sqlite3

        pattern = {
            "id": "fp_001",
            "error_signature": "race_condition|auth/*.py|pendingMessageRef",
            "fix_template": "添加 @critical 注释说明时序依赖",
            "success_rate": 0.9,
        }

        conn = sqlite3.connect(str(temp_db.config.db_path))
        conn.execute(
            """
            INSERT INTO fix_patterns (id, error_signature, fix_template, success_rate)
            VALUES (?, ?, ?, ?)
            """,
            (pattern["id"], pattern["error_signature"], pattern["fix_template"], pattern["success_rate"]),
        )
        conn.commit()

        # 查询修复模式
        result = conn.execute(
            "SELECT * FROM fix_patterns WHERE id = ?", (pattern["id"],)
        ).fetchone()

        assert result is not None
        assert result[3] == 0.9  # success_rate
        conn.close()

    def test_smart_hint_generation(self, temp_db):
        """测试智能提示生成"""
        import sqlite3

        # 写入 Bug 记忆
        error = {
            "type": "race_condition",
            "file": "src/auth/session.py",
            "line": 142,
            "message": "pendingMessageRef 缺少时序注释",
            "pain_score": 85.0,
        }
        bug_id = temp_db.write_bug_memory(error)
        assert bug_id is not None

        # 生成智能提示
        hint_id = f"hint_{int(time.time() * 1000)}"
        conn = sqlite3.connect(str(temp_db.config.db_path))
        conn.execute(
            """
            INSERT INTO smart_hints (id, file_path, line, hint_type, message, priority)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                hint_id,
                "src/auth/session.py",
                142,
                "repeated_bug",
                "此位置已出现 1 次 race_condition Bug（avg pain: 85.0）",
                4,
            ),
        )
        conn.commit()

        # 查询提示
        result = conn.execute(
            "SELECT * FROM smart_hints WHERE id = ?", (hint_id,)
        ).fetchone()

        assert result is not None
        assert result[3] == "repeated_bug"  # hint_type
        assert result[5] == 4  # priority
        conn.close()

    def test_get_statistics_with_new_tables(self, temp_db):
        """测试统计信息包含新表"""
        # 写入一些测试数据
        error = {
            "type": "race_condition",
            "file": "src/auth/session.py",
            "line": 142,
            "message": "test",
            "pain_score": 85.0,
        }
        temp_db.write_bug_memory(error)

        import sqlite3
        conn = sqlite3.connect(str(temp_db.config.db_path))
        conn.execute("""
            INSERT INTO fix_history (id, bug_id, fix_type, fixed_by, success, fixed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("fh_001", "bug_test", "manual", "developer", 1, datetime.now().isoformat()))
        conn.commit()
        conn.close()

        stats = temp_db.get_statistics()
        assert "bug_memories" in stats
        assert stats["bug_memories"] >= 1
