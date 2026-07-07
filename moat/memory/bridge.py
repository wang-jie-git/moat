"""共享存储桥接器 — Moat（Python）和 One Memory（TypeScript）通过 SQLite 通信

设计方案：
- Moat 直接写入 .moat/memory.db（Python sqlite3）
- One Memory 直接读取 .moat/memory.db（TypeScript better-sqlite3）
- 文件级共享，无进程通信开销
- 乐观锁 + WAL 模式支持并发读写
"""
import json
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


@dataclass
class BridgeConfig:
    """桥接器配置"""
    db_path: str | Path
    wal_mode: bool = True  # 启用 WAL 模式（并发读写）
    busy_timeout_ms: int = 5000  #  busy timeout


class SharedStorageBridge:
    """共享存储桥接器

    为 Moat（Python）和 One Memory（TypeScript）提供统一的 SQLite 访问接口。
    """

    def __init__(self, config: BridgeConfig):
        self.config = config
        self.db_path = Path(config.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: sqlite3.Connection | None = None

    def initialize(self) -> bool:
        """初始化数据库（创建表结构）"""
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row  # 确保使用 Row factory

            # 启用 WAL 模式（支持并发读写）
            if self.config.wal_mode:
                self.conn.execute("PRAGMA journal_mode=WAL")

            # 设置 busy timeout
            self.conn.execute(f"PRAGMA busy_timeout={self.config.busy_timeout_ms}")

            # 创建表结构
            self._create_tables()

            return True
        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            return False

    def _create_tables(self):
        """创建表结构（供 One Memory 使用）"""
        if not self.conn:
            return

        # Bug 记忆表（元数据）
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bug_memories (
                id TEXT PRIMARY KEY,
                error_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                line INTEGER,
                pain_score REAL NOT NULL,
                message TEXT NOT NULL,
                first_seen TIMESTAMP NOT NULL,
                last_seen TIMESTAMP NOT NULL,
                occurrence_count INTEGER DEFAULT 1,
                avg_pain REAL,
                status TEXT DEFAULT 'active',
                metadata TEXT,
                created_by TEXT DEFAULT 'moat',  -- 'moat' | 'one-memory' | 'manual'
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 修复历史表（v0.5.0 新增）
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS fix_history (
                id TEXT PRIMARY KEY,
                bug_id TEXT NOT NULL,
                fix_type TEXT NOT NULL,  -- 'manual' | 'auto' | 'ai_assisted'
                fixed_by TEXT,  -- 修复者（用户名/commit hash）
                fix_time_seconds REAL,  -- 修复耗时（秒）
                success INTEGER DEFAULT 1,  -- 是否成功
                pain_score_after REAL,  -- 修复后 Pain Score
                notes TEXT,
                fixed_at TIMESTAMP NOT NULL,
                FOREIGN KEY (bug_id) REFERENCES bug_memories(id)
            )
        """)

        # 架构薄弱点表（v0.5.0 新增）
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS weak_points (
                id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                issue_type TEXT NOT NULL,
                frequency INTEGER DEFAULT 0,
                last_occurred TIMESTAMP,
                recommendation TEXT,
                priority INTEGER DEFAULT 0,  -- 0-5，越高越重要
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insight 表（梦境引擎输出）
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS insights (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                module TEXT,
                pattern TEXT NOT NULL,
                confidence REAL,
                evidence_count INTEGER,
                generated_at TIMESTAMP NOT NULL,
                applied BOOLEAN DEFAULT 0,
                applied_at TIMESTAMP,
                metadata TEXT,
                created_by TEXT DEFAULT 'one-memory'
            )
        """)

        # 修复模式表（v0.5.0 新增）
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS fix_patterns (
                id TEXT PRIMARY KEY,
                error_signature TEXT NOT NULL,
                fix_template TEXT,
                success_rate REAL DEFAULT 0.0,
                usage_count INTEGER DEFAULT 0,
                last_used TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insight 表（梦境引擎输出）
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS insights (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                module TEXT,
                pattern TEXT NOT NULL,
                confidence REAL,
                evidence_count INTEGER,
                generated_at TIMESTAMP NOT NULL,
                applied BOOLEAN DEFAULT 0,
                applied_at TIMESTAMP,
                metadata TEXT,
                created_by TEXT DEFAULT 'one-memory'
            )
        """)

        # 同步状态表（用于追踪 One Memory 的处理状态）
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,  -- 'moat' | 'one-memory'
                last_sync TIMESTAMP NOT NULL,
                records_synced INTEGER DEFAULT 0,
                status TEXT DEFAULT 'success'  -- 'success' | 'failed' | 'pending'
            )
        """)

        # 梦境触发表（v0.5.0 新增）
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS dream_triggers (
                id TEXT PRIMARY KEY,
                triggered_by TEXT DEFAULT 'moat',
                trigger_type TEXT DEFAULT 'auto',
                pending_bugs INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 智能提示表（v0.5.0 新增）
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS smart_hints (
                id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                line INTEGER,
                hint_type TEXT NOT NULL,  -- 'repeated_bug' | 'weak_point' | 'suggestion'
                message TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                shown INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 索引优化
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_bug_error_type ON bug_memories(error_type)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_bug_file_path ON bug_memories(file_path)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_bug_pain_score ON bug_memories(pain_score)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_fix_bug_id ON fix_history(bug_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_weak_point_file ON weak_points(file_path)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_insight_type ON insights(type)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_insight_applied ON insights(applied)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_hint_file_line ON smart_hints(file_path, line)")

        self.conn.commit()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Cursor]:
        """事务上下文管理器"""
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.cursor()
        try:
            yield cursor
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def write_bug_memory(self, error: dict[str, Any]) -> str | None:
        """写入 Bug 记忆（供 Moat 调用）

        Args:
            error: 错误信息

        Returns:
            Bug ID 或 None
        """
        if not self.conn:
            return None

        import time
        bug_id = f"bug_{int(time.time() * 1000)}_{hash(error.get('file', '')) % 10000:04d}"
        now = datetime.now().isoformat()
        pain_score = error.get("pain_score", 0.0)

        try:
            with self.transaction() as cursor:
                cursor.execute(
                    """
                    INSERT INTO bug_memories (
                        id, error_type, file_path, line, pain_score,
                        message, first_seen, last_seen, avg_pain, metadata, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        bug_id,
                        error.get("type", "unknown"),
                        error.get("file", ""),
                        error.get("line"),
                        pain_score,
                        error.get("message", ""),
                        now,
                        now,
                        pain_score,
                        json.dumps(error),
                        "moat",
                    ),
                )
            return bug_id
        except Exception as e:
            print(f"❌ 写入失败: {e}")
            return None

    def write_insight(self, insight: dict[str, Any]) -> str | None:
        """写入 Insight（供 One Memory/梦境引擎调用）

        Args:
            insight: Insight 数据

        Returns:
            Insight ID 或 None
        """
        if not self.conn:
            return None

        import time
        insight_id = f"insight_{int(time.time() * 1000)}_{hash(insight.get('pattern', '')) % 10000:04d}"
        now = datetime.now().isoformat()

        try:
            with self.transaction() as cursor:
                cursor.execute(
                    """
                    INSERT INTO insights (
                        id, type, module, pattern, confidence,
                        evidence_count, generated_at, metadata, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        insight_id,
                        insight.get("type", "unknown"),
                        insight.get("module"),
                        insight.get("pattern", ""),
                        insight.get("confidence", 0.0),
                        insight.get("evidence_count", 0),
                        now,
                        json.dumps(insight),
                        insight.get("created_by", "one-memory"),
                    ),
                )
            return insight_id
        except Exception as e:
            print(f"❌ 写入 Insight 失败: {e}")
            return None

    def query_recent_insights(self, limit: int = 10) -> list[dict]:
        """查询最近的 Insights（供 Moat 加载进化规则）

        Args:
            limit: 返回数量

        Returns:
            Insight 列表
        """
        if not self.conn:
            return []

        cursor = self.conn.execute(
            """
            SELECT * FROM insights
            WHERE applied = 0
            ORDER BY generated_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def mark_insight_applied(self, insight_id: str):
        """标记 Insight 已应用"""
        if not self.conn:
            return

        with self.transaction() as cursor:
            cursor.execute(
                """
                UPDATE insights
                SET applied = 1, applied_at = ?
                WHERE id = ?
                """,
                (datetime.now().isoformat(), insight_id),
            )

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        if not self.conn:
            return {}

        bug_count = self.conn.execute("SELECT COUNT(*) FROM bug_memories").fetchone()[0]
        insight_count = self.conn.execute("SELECT COUNT(*) FROM insights").fetchone()[0]
        unapplied_insights = self.conn.execute(
            "SELECT COUNT(*) FROM insights WHERE applied = 0"
        ).fetchone()[0]

        return {
            "bug_memories": bug_count,
            "insights": insight_count,
            "unapplied_insights": unapplied_insights,
        }

    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        """Context manager 支持"""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 支持"""
        self.close()
        return False


from datetime import datetime
