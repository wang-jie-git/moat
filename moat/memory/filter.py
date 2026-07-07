"""记忆写入过滤器 — 防止记忆碎片化

核心策略：
1. 只写入重要 Bug（Pain Score > 50）
2. 统计重复出现的 Bug（类型 + 位置）
3. 过滤低级错误（语法错误、导入错误等）
4. 合并相似记忆，避免冗余
"""
import hashlib
import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class MemoryFilterConfig:
    """记忆过滤器配置"""
    min_pain_score: float = 50.0  # 最低 Pain Score
    min_repetitions: int = 2  # 最少重复次数
    dedup_window_hours: int = 168  # 去重时间窗口（7 天）
    low_priority_patterns: list[str] = field(default_factory=lambda: [
        "syntax_error", "import_error", "doc_missing",
        "语法错误", "import", "文档缺失"
    ])


class MemoryFilter:
    """记忆过滤器"""

    def __init__(self, config: MemoryFilterConfig | None = None):
        self.config = config or MemoryFilterConfig()
        self.statistics: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "last_seen": None, "total_pain": 0.0}
        )

    def should_write(self, error: dict[str, Any]) -> tuple[bool, str]:
        """判断是否应该写入记忆

        Args:
            error: 错误信息

        Returns:
            (是否写入, 原因)
        """
        error_type = error.get("type", "").lower()
        pain_score = error.get("pain_score", 0.0)
        file_path = error.get("file", "")

        # 1. 检查 Pain Score
        if pain_score < self.config.min_pain_score:
            return False, f"Pain Score ({pain_score}) 低于阈值 ({self.config.min_pain_score})"

        # 2. 检查是否属于低优先级模式
        if self._is_low_priority(error_type):
            # 即使是低优先级，如果重复出现，也要写入
            key = self._get_error_key(error)
            stats = self.statistics[key]
            if stats["count"] < self.config.min_repetitions:
                return False, f"低优先级错误类型 ({error_type})，未达到重复阈值"

        # 3. 更新统计
        key = self._get_error_key(error)
        self.statistics[key]["count"] += 1
        self.statistics[key]["last_seen"] = datetime.now().isoformat()
        self.statistics[key]["total_pain"] += pain_score

        return True, "通过过滤器"

    def _is_low_priority(self, error_type: str) -> bool:
        """是否属于低优先级"""
        return any(pattern in error_type for pattern in self.config.low_priority_patterns)

    def _get_error_key(self, error: dict[str, Any]) -> str:
        """生成错误唯一标识（用于去重统计）"""
        error_type = error.get("type", "unknown")
        file_path = error.get("file", "unknown")

        # 提取文件相对路径（忽略具体行号）
        if "/" in file_path:
            file_key = "/".join(file_path.split("/")[-2:])
        else:
            file_key = file_path

        return f"{error_type}::{file_key}"

    def get_statistics(self) -> dict[str, Any]:
        """获取过滤统计"""
        return dict(self.statistics)


class SharedMemoryStore:
    """共享记忆存储（SQLite，Moat 和 One Memory 共用）

    设计原则：
    - 轻量级：只有元数据，不含完整文本
    - 跨语言：纯 SQL，Python 和 TypeScript 都能读写
    - 高性能：索引优化，避免全表扫描
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: sqlite3.Connection | None = None

    def connect(self) -> bool:
        """连接数据库"""
        if not self.db_path.exists():
            self._init_db()

        try:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
            return True
        except Exception:
            return False

    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Bug 记忆表（元数据）
        cursor.execute("""
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
                status TEXT DEFAULT 'active',  -- active/resolved/ignored
                metadata TEXT  -- JSON
            )
        """)

        # 索引优化
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_type ON bug_memories(error_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_path ON bug_memories(file_path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pain_score ON bug_memories(pain_score)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON bug_memories(status)")

        # Insight 表（梦境引擎输出）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS insights (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,  -- repeated_bug/architectural_weakness/evolution_suggestion
                module TEXT,
                pattern TEXT NOT NULL,
                confidence REAL,
                evidence_count INTEGER,
                generated_at TIMESTAMP NOT NULL,
                applied BOOLEAN DEFAULT 0,
                metadata TEXT  -- JSON
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_insight_type ON insights(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_applied ON insights(applied)")

        conn.commit()
        conn.close()

    def write_bug_memory(self, error: dict[str, Any]) -> str | None:
        """写入 Bug 记忆

        Args:
            error: 错误信息

        Returns:
            Bug ID 或 None（如果未通过过滤器）
        """
        if not self.conn:
            return None

        # 应用过滤器
        mem_filter = MemoryFilter()
        should_write, reason = mem_filter.should_write(error)

        if not should_write:
            return None

        # 检查是否已存在（去重）
        existing = self._find_similar(error)
        if existing:
            # 更新已有记录
            return self._update_existing(existing["id"], error)
        else:
            # 创建新记录
            return self._create_new(error)

    def _find_similar(self, error: dict[str, Any]) -> dict | None:
        """查找相似的 Bug 记忆"""
        if not self.conn:
            return None

        error_type = error.get("type", "").lower()
        file_path = error.get("file", "")

        cursor = self.conn.execute(
            """
            SELECT * FROM bug_memories
            WHERE error_type = ? AND file_path = ? AND status = 'active'
            ORDER BY last_seen DESC
            LIMIT 1
            """,
            (error_type, file_path),
        )
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def _update_existing(self, bug_id: str, error: dict[str, Any]) -> str:
        """更新已有记录"""
        if not self.conn:
            return bug_id

        pain_score = error.get("pain_score", 0.0)
        now = datetime.now().isoformat()

        self.conn.execute(
            """
            UPDATE bug_memories
            SET occurrence_count = occurrence_count + 1,
                last_seen = ?,
                avg_pain = (avg_pain * (occurrence_count - 1) + ?) / occurrence_count
            WHERE id = ?
            """,
            (now, pain_score, bug_id),
        )
        self.conn.commit()
        return bug_id

    def _create_new(self, error: dict[str, Any]) -> str | None:
        """创建新记录"""
        if not self.conn:
            return None

        import time

        bug_id = f"bug_{int(time.time() * 1000)}_{hashlib.md5(error.get('file', '').encode()).hexdigest()[:8]}"
        now = datetime.now().isoformat()
        pain_score = error.get("pain_score", 0.0)

        try:
            self.conn.execute(
                """
                INSERT INTO bug_memories (
                    id, error_type, file_path, line, pain_score,
                    message, first_seen, last_seen, avg_pain, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    json.dumps(error.get("context", {})),
                ),
            )
            self.conn.commit()
            return bug_id
        except Exception:
            return None

    def query_repeated_bugs(self, min_occurrences: int = 2) -> list[dict]:
        """查询重复出现的 Bug"""
        if not self.conn:
            return []

        cursor = self.conn.execute(
            """
            SELECT * FROM bug_memories
            WHERE occurrence_count >= ? AND status = 'active'
            ORDER BY occurrence_count DESC, avg_pain DESC
            """,
            (min_occurrences,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_statistics(self) -> dict[str, Any]:
        """获取记忆库统计"""
        if not self.conn:
            return {}

        total = self.conn.execute("SELECT COUNT(*) FROM bug_memories").fetchone()[0]
        repeated = self.conn.execute(
            "SELECT COUNT(*) FROM bug_memories WHERE occurrence_count >= 2"
        ).fetchone()[0]
        avg_pain = self.conn.execute(
            "SELECT AVG(avg_pain) FROM bug_memories WHERE status = 'active'"
        ).fetchone()[0] or 0.0

        return {
            "total_memories": total,
            "repeated_bugs": repeated,
            "avg_pain_score": round(avg_pain, 1),
        }

    def __enter__(self):
        """Context manager 支持"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 支持"""
        self.close()
        return False


def write_memory_with_filter(error: dict[str, Any], db_path: str | Path = ".moat/memory.db") -> str | None:
    """便捷函数：应用过滤器后写入记忆

    Args:
        error: 错误信息
        db_path: 数据库路径

    Returns:
        Bug ID 或 None
    """
    with SharedMemoryStore(db_path) as store:
        return store.write_bug_memory(error)


def get_memory_statistics(db_path: str | Path = ".moat/memory.db") -> dict[str, Any]:
    """便捷函数：获取记忆统计"""
    with SharedMemoryStore(db_path) as store:
        return store.get_statistics()
