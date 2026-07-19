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

        # 契约基线表（v0.9.0 新增 - Phase 2）
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS contract_baselines (
                id TEXT PRIMARY KEY,
                service_name TEXT NOT NULL,
                version TEXT NOT NULL,
                baseline_hash TEXT NOT NULL,
                contract_count INTEGER DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(service_name, version)
            )
        """)

        # API 契约表（v0.9.0 新增 - Phase 2）
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS api_contracts (
                id TEXT PRIMARY KEY,
                service_name TEXT NOT NULL,
                version TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                contract_hash TEXT NOT NULL,
                request_schema TEXT,
                response_schema TEXT,
                status_code INTEGER,
                description TEXT,
                is_breaking BOOLEAN DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                last_modified TIMESTAMP,
                FOREIGN KEY (service_name, version) REFERENCES contract_baselines(service_name, version)
            )
        """)

        # ── moat-memory 表（v1.2.0 新增） ──

        # 红线：项目特定的架构规则
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS redlines (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                severity TEXT DEFAULT 'warning',
                category TEXT DEFAULT 'general',
                source TEXT DEFAULT 'auto',
                file_glob TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 踩坑：每次 check 失败的结构化记录
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS lessons (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                failed_tests TEXT NOT NULL,
                error_summary TEXT NOT NULL,
                failure_count INTEGER DEFAULT 1,
                principles TEXT,
                negative_examples TEXT,
                content_hash TEXT,
                captured_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 模版：经验总结 / 思维框架
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                title TEXT NOT NULL,
                source TEXT DEFAULT 'manual',
                elements TEXT,
                principles TEXT,
                negative_examples TEXT,
                tags TEXT,
                importance INTEGER DEFAULT 5,
                content_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # AI 工具技能：告诉 AI 如何与 moat 互动
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY,
                tool TEXT NOT NULL,
                instruction TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_contract_service ON contract_baselines(service_name)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_contract_endpoint ON api_contracts(service_name, endpoint, method)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_redline_category ON redlines(category)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_lesson_hash ON lessons(content_hash)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_template_domain ON templates(domain)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_skill_tool ON skills(tool)")

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
        contract_count = self.conn.execute("SELECT COUNT(*) FROM api_contracts").fetchone()[0]

        return {
            "bug_memories": bug_count,
            "insights": insight_count,
            "unapplied_insights": unapplied_insights,
            "api_contracts": contract_count,
        }

    # ========================================
    # 契约存储方法（v0.9.0 Phase 2 新增）
    # ========================================

    def store_contract_baseline(self, baseline_data: dict[str, Any]) -> bool:
        """保存契约基线

        Args:
            baseline_data: 基线数据

        Returns:
            是否成功
        """
        if not self.conn:
            return False

        try:
            import time
            baseline_id = f"baseline_{int(time.time() * 1000)}_{hash(baseline_data.get('service_name', '')) % 10000:04d}"

            with self.transaction() as cursor:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO contract_baselines (
                        id, service_name, version, baseline_hash,
                        contract_count, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        baseline_id,
                        baseline_data["service_name"],
                        baseline_data["version"],
                        baseline_data["baseline_hash"],
                        baseline_data.get("contract_count", 0),
                        baseline_data.get("created_at", datetime.now().isoformat()),
                        datetime.now().isoformat(),
                    ),
                )
            return True
        except Exception as e:
            print(f"❌ 保存契约基线失败: {e}")
            return False

    def store_api_contract(self, contract_data: dict[str, Any]) -> bool:
        """保存单个 API 契约

        Args:
            contract_data: 契约数据

        Returns:
            是否成功
        """
        if not self.conn:
            return False

        try:
            import time
            contract_id = f"contract_{int(time.time() * 1000)}_{hash(contract_data.get('endpoint', '')) % 10000:04d}"

            with self.transaction() as cursor:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO api_contracts (
                        id, service_name, version, endpoint, method,
                        contract_hash, request_schema, response_schema,
                        status_code, description, is_breaking,
                        created_at, last_modified
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        contract_id,
                        contract_data["service_name"],
                        contract_data["version"],
                        contract_data["endpoint"],
                        contract_data["method"],
                        contract_data["contract_hash"],
                        json.dumps(contract_data.get("request_schema", {})),
                        json.dumps(contract_data.get("response_schema", {})),
                        contract_data.get("status_code", 200),
                        contract_data.get("description", ""),
                        contract_data.get("is_breaking", False),
                        contract_data.get("created_at", datetime.now().isoformat()),
                        contract_data.get("last_modified", datetime.now().isoformat()),
                    ),
                )
            return True
        except Exception as e:
            print(f"❌ 保存 API 契约失败: {e}")
            return False

    def query_contract_baseline(self, service_name: str, version: str | None = None) -> dict | None:
        """查询契约基线

        Args:
            service_name: 服务名称
            version: 版本（可选，默认查询最新）

        Returns:
            基线数据或 None
        """
        if not self.conn:
            return None

        try:
            if version:
                cursor = self.conn.execute(
                    "SELECT * FROM contract_baselines WHERE service_name = ? AND version = ?",
                    (service_name, version),
                )
            else:
                cursor = self.conn.execute(
                    "SELECT * FROM contract_baselines WHERE service_name = ? ORDER BY created_at DESC LIMIT 1",
                    (service_name,),
                )

            row = cursor.fetchone()
            if not row:
                return None

            return dict(row)
        except Exception as e:
            print(f"❌ 查询契约基线失败: {e}")
            return None

    def query_api_contracts(self, service_name: str, version: str | None = None) -> list[dict]:
        """查询 API 契约列表

        Args:
            service_name: 服务名称
            version: 版本（可选）

        Returns:
            契约列表
        """
        if not self.conn:
            return []

        try:
            if version:
                cursor = self.conn.execute(
                    "SELECT * FROM api_contracts WHERE service_name = ? AND version = ?",
                    (service_name, version),
                )
            else:
                cursor = self.conn.execute(
                    "SELECT * FROM api_contracts WHERE service_name = ?",
                    (service_name,),
                )

            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"❌ 查询 API 契约失败: {e}")
            return []

    # ── moat-memory: 红线 CRUD ─────────────────────────────

    def write_redline(self, redline: dict[str, Any]) -> str | None:
        """写入一条红线。"""
        if not self.conn:
            return None
        import time
        rid = f"rl_{int(time.time() * 1000)}_{hash(redline.get('title', '')) % 10000:04d}"
        try:
            with self.transaction() as cursor:
                cursor.execute(
                    "INSERT INTO redlines (id, title, description, severity, category, source, file_glob) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        rid,
                        redline.get("title", ""),
                        redline.get("description", ""),
                        redline.get("severity", "warning"),
                        redline.get("category", "general"),
                        redline.get("source", "manual"),
                        redline.get("file_glob"),
                    ),
                )
            return rid
        except Exception as e:
            print(f"❌ 写入红线失败: {e}")
            return None

    def query_redlines(self, category: str | None = None, active_only: bool = True) -> list[dict]:
        """查询红线。"""
        if not self.conn:
            return []
        try:
            if category:
                cursor = self.conn.execute(
                    "SELECT * FROM redlines WHERE category=? ORDER BY severity DESC, created_at DESC", (category,)
                )
            else:
                cursor = self.conn.execute(
                    "SELECT * FROM redlines ORDER BY severity DESC, created_at DESC"
                )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"❌ 查询红线失败: {e}")
            return []

    def delete_redline(self, redline_id: str) -> bool:
        """删除一条红线。"""
        if not self.conn:
            return False
        try:
            with self.transaction() as cursor:
                cursor.execute("DELETE FROM redlines WHERE id LIKE ?", (f"%{redline_id}%",))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ 删除红线失败: {e}")
            return False

    # ── moat-memory: 踩坑 CRUD ─────────────────────────────

    def write_lesson(self, lesson: dict[str, Any]) -> str | None:
        """写入一条踩坑记录。"""
        if not self.conn:
            return None
        import time
        lid = f"lsn_{int(time.time() * 1000)}"
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with self.transaction() as cursor:
                cursor.execute(
                    "INSERT OR IGNORE INTO lessons "
                    "(id, title, failed_tests, error_summary, failure_count, principles, negative_examples, content_hash, captured_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        lid,
                        lesson.get("title", "MOAT 门禁失败"),
                        json.dumps(lesson.get("failed_tests", [])),
                        lesson.get("error_summary", ""),
                        lesson.get("failure_count", 1),
                        json.dumps(lesson.get("principles", [])),
                        json.dumps(lesson.get("negative_examples", [])),
                        lesson.get("content_hash", ""),
                        lesson.get("captured_at", now),
                    ),
                )
            return lid
        except Exception as e:
            print(f"❌ 写入踩坑失败: {e}")
            return None

    def query_lessons(self, limit: int = 20, offset: int = 0) -> list[dict]:
        """查询踩坑记录。"""
        if not self.conn:
            return []
        try:
            cursor = self.conn.execute(
                "SELECT * FROM lessons ORDER BY captured_at DESC LIMIT ? OFFSET ?", (limit, offset)
            )
            rows = []
            for row in cursor.fetchall():
                d = dict(row)
                for f in ("failed_tests", "principles", "negative_examples"):
                    if isinstance(d.get(f), str):
                        try:
                            d[f] = json.loads(d[f])
                        except (json.JSONDecodeError, TypeError):
                            pass
                rows.append(d)
            return rows
        except Exception as e:
            print(f"❌ 查询踩坑失败: {e}")
            return []

    def delete_lesson(self, lesson_id: str) -> bool:
        """删除一条踩坑记录。"""
        if not self.conn:
            return False
        try:
            with self.transaction() as cursor:
                cursor.execute("DELETE FROM lessons WHERE id LIKE ?", (f"%{lesson_id}%",))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ 删除踩坑失败: {e}")
            return False

    # ── moat-memory: 模版 CRUD ─────────────────────────────

    def write_template_entry(self, template: dict[str, Any]) -> str | None:
        """写入一条模版。"""
        if not self.conn:
            return None
        import time
        tid = f"tpl_{int(time.time() * 1000)}"
        try:
            with self.transaction() as cursor:
                cursor.execute(
                    "INSERT OR IGNORE INTO templates "
                    "(id, domain, title, source, elements, principles, negative_examples, tags, importance, content_hash) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        tid,
                        template.get("domain", "general"),
                        template.get("title", ""),
                        template.get("source", "manual"),
                        json.dumps(template.get("elements", {})),
                        json.dumps(template.get("principles", [])),
                        json.dumps(template.get("negative_examples", [])),
                        json.dumps(template.get("tags", [])),
                        template.get("importance", 5),
                        template.get("content_hash", ""),
                    ),
                )
            return tid
        except Exception as e:
            print(f"❌ 写入模版失败: {e}")
            return None

    def query_templates(self, domain: str | None = None, limit: int = 20) -> list[dict]:
        """查询模版。"""
        if not self.conn:
            return []
        try:
            if domain:
                cursor = self.conn.execute(
                    "SELECT * FROM templates WHERE domain=? ORDER BY importance DESC, created_at DESC LIMIT ?",
                    (domain, limit),
                )
            else:
                cursor = self.conn.execute(
                    "SELECT * FROM templates ORDER BY importance DESC, created_at DESC LIMIT ?", (limit,)
                )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"❌ 查询模版失败: {e}")
            return []

    def delete_template_entry(self, template_id: str) -> bool:
        """删除一条模版。"""
        if not self.conn:
            return False
        try:
            with self.transaction() as cursor:
                cursor.execute("DELETE FROM templates WHERE id LIKE ?", (f"%{template_id}%",))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ 删除模版失败: {e}")
            return False

    # ── moat-memory: 技能 CRUD ─────────────────────────────

    def write_skill(self, skill: dict[str, Any]) -> str | None:
        """写入一条技能指令。"""
        if not self.conn:
            return None
        import time
        sid = f"sk_{int(time.time() * 1000)}"
        try:
            with self.transaction() as cursor:
                cursor.execute(
                    "INSERT OR REPLACE INTO skills (id, tool, instruction, priority, is_active) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        sid,
                        skill.get("tool", "general"),
                        skill.get("instruction", ""),
                        skill.get("priority", 0),
                        1 if skill.get("is_active", True) else 0,
                    ),
                )
            return sid
        except Exception as e:
            print(f"❌ 写入技能失败: {e}")
            return None

    def query_skills(self, tool: str | None = None) -> list[dict]:
        """查询技能指令。"""
        if not self.conn:
            return []
        try:
            if tool:
                cursor = self.conn.execute(
                    "SELECT * FROM skills WHERE tool=? AND is_active=1 ORDER BY priority DESC", (tool,)
                )
            else:
                cursor = self.conn.execute(
                    "SELECT * FROM skills WHERE is_active=1 ORDER BY tool, priority DESC"
                )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"❌ 查询技能失败: {e}")
            return []

    # ── moat-memory: 统计 ──────────────────────────────────

    def get_memory_stats(self) -> dict[str, int]:
        """获取各类记忆的数量统计。"""
        stats = {}
        tables = {"redlines", "lessons", "templates", "skills"}
        for table in tables:
            try:
                cursor = self.conn.execute(
                    "SELECT COUNT(*) as cnt FROM " + table  # table 来自硬编码集合，安全
                )
                row = cursor.fetchone()
                stats[table] = row["cnt"] if row else 0
            except Exception:
                stats[table] = 0
        return stats

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
