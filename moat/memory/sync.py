"""双向同步管理器 — Moat ↔ One Memory

功能：
1. 自动触发 One Memory 梦境引擎
2. 追踪同步状态
3. 记忆质量报告
4. 故障恢复机制
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class SyncStatus:
    """同步状态"""

    last_sync_at: float | None = None
    last_dream_at: float | None = None
    total_insights: int = 0
    applied_insights: int = 0
    pending_insights: int = 0
    last_error: str | None = None
    sync_history: list[dict[str, Any]] | None = None

    def __post_init__(self):
        if self.sync_history is None:
            self.sync_history = []


class MemorySyncManager:
    """记忆同步管理器

    管理 Moat 和 One Memory 之间的双向同步。
    """

    def __init__(self, bridge: Any, project_root: Path):
        self.bridge = bridge
        self.project = project_root.resolve()
        self.moat_dir = self.project / ".moat"
        self.status_file = self.moat_dir / "memory_sync_status.json"
        self.status = self._load_status()

    def _load_status(self) -> SyncStatus:
        """加载同步状态"""
        if self.status_file.exists():
            try:
                data = json.loads(self.status_file.read_text(encoding="utf-8"))
                return SyncStatus(**data)
            except Exception:
                pass
        return SyncStatus()

    def _save_status(self):
        """保存同步状态"""
        self.status_file.write_text(
            json.dumps(asdict(self.status), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def trigger_dream_engine(self) -> dict[str, Any]:
        """触发 One Memory 梦境引擎

        Returns:
            触发结果
        """
        try:
            # 1. 检查 One Memory 是否可用
            if not self._check_one_memory_available():
                return {
                    "success": False,
                    "error": "One Memory 未安装或不可用",
                }

            # 2. 统计待处理的 Bug 记忆
            pending_bugs = self._count_pending_bugs()

            if pending_bugs == 0:
                return {
                    "success": True,
                    "message": "没有待处理的 Bug 记忆",
                    "insights_generated": 0,
                }

            # 3. 触发梦境引擎（通过 One Memory 的 CLI 或 API）
            insights = self._invoke_dream_engine(pending_bugs)

            # 4. 更新状态
            self.status.last_dream_at = time.time()
            self.status.total_insights += len(insights)
            self.status.pending_insights += len(insights)
            self.status.sync_history.append(
                {
                    "timestamp": time.time(),
                    "type": "dream_triggered",
                    "pending_bugs": pending_bugs,
                    "insights_generated": len(insights),
                }
            )
            self._save_status()

            return {
                "success": True,
                "message": f"梦境引擎已触发，生成 {len(insights)} 个 Insights",
                "insights_generated": len(insights),
                "insights": insights,
            }

        except Exception as e:
            self.status.last_error = str(e)
            self._save_status()
            return {
                "success": False,
                "error": str(e),
            }

    def _check_one_memory_available(self) -> bool:
        """检查 One Memory 是否可用

        检查方式：
        1. 检查 One Memory 的数据库文件是否存在
        2. 尝试读取最新的 Insights
        """
        # 检查 One Memory 项目目录
        one_memory_dirs = [
            self.project.parent / "one-memory",
            Path.home() / "projects" / "one-memory",
            Path("/Users/mac/Desktop/one-memory"),
        ]

        for om_dir in one_memory_dirs:
            if om_dir.exists():
                return True

        # 检查 .moat/memory.db 是否有 Insights 表
        try:
            insights = self.bridge.query_recent_insights(limit=1)
            return True
        except Exception:
            return False

    def _count_pending_bugs(self) -> int:
        """统计待处理的 Bug 记忆"""
        try:
            # 查询最近 24 小时内新增的 Bug
            import sqlite3

            db_path = self.bridge.config.db_path
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row

            cutoff = time.time() - (24 * 3600)
            result = conn.execute(
                "SELECT COUNT(*) as count FROM bug_memories WHERE first_seen > ?",
                (cutoff,),
            ).fetchone()

            count = result["count"] if result else 0
            conn.close()
            return count

        except Exception:
            return 0

    def _invoke_dream_engine(self, pending_bugs: int) -> list[dict[str, Any]]:
        """调用 One Memory 梦境引擎

        触发方式：
        1. 通过 One Memory CLI（如果可用）
        2. 通过 HTTP API（如果 One Memory 运行了 Dream Server）
        3. 通过直接写入 trigger_dream 表（高级用法）

        这里实现方式 3（最通用）：
        """
        try:
            import sqlite3

            db_path = self.bridge.config.db_path
            conn = sqlite3.connect(str(db_path))

            # 创建梦境触发表（如果不存在）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dream_triggers (
                    id TEXT PRIMARY KEY,
                    triggered_by TEXT DEFAULT 'moat',
                    trigger_type TEXT DEFAULT 'auto',
                    pending_bugs INTEGER,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 插入触发记录
            import uuid

            trigger_id = f"dream_{uuid.uuid4().hex[:8]}"
            conn.execute(
                "INSERT INTO dream_triggers (id, pending_bugs) VALUES (?, ?)",
                (trigger_id, pending_bugs),
            )
            conn.commit()
            conn.close()

            # 返回空列表（One Memory 后台异步处理）
            # 实际 Insights 会在下次查询时出现
            return []

        except Exception as e:
            raise RuntimeError(f"触发梦境引擎失败: {e}")

    def sync_insights(self) -> dict[str, Any]:
        """同步 Insights（从 One Memory 到 Moat）

        Returns:
            同步结果
        """
        try:
            # 1. 查询未应用的 Insights
            unapplied = self.bridge.query_unapplied_insights()

            if not unapplied:
                return {
                    "success": True,
                    "message": "没有未应用的 Insights",
                    "synced": 0,
                }

            # 2. 生成进化规则
            from moat.evolution import EvolutionEngine

            engine = EvolutionEngine(self.project, self.bridge)
            rules = engine.generate_evolved_rules()

            # 3. 更新状态
            self.status.applied_insights += len(unapplied)
            self.status.pending_insights -= len(unapplied)
            self.status.last_sync_at = time.time()

            self.status.sync_history.append(
                {
                    "timestamp": time.time(),
                    "type": "insights_synced",
                    "insights_count": len(unapplied),
                    "rules_generated": len(rules),
                }
            )
            self._save_status()

            return {
                "success": True,
                "message": f"同步了 {len(unapplied)} 个 Insights，生成 {len(rules)} 条规则",
                "synced": len(unapplied),
                "rules": [r.to_dict() for r in rules],
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def get_memory_quality_report(self) -> dict[str, Any]:
        """生成记忆质量报告

        Returns:
            报告字典
        """
        try:
            import sqlite3

            db_path = self.bridge.config.db_path
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row

            # Bug 记忆统计
            bug_stats = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    AVG(pain_score) as avg_pain,
                    MAX(pain_score) as max_pain,
                    MIN(pain_score) as min_pain,
                    SUM(occurrence_count) as total_occurrences,
                    COUNT(DISTINCT error_type) as unique_errors,
                    COUNT(DISTINCT file_path) as affected_files
                FROM bug_memories
            """).fetchone()

            # Insight 统计
            insight_stats = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN applied = 1 THEN 1 ELSE 0 END) as applied,
                    SUM(CASE WHEN applied = 0 THEN 1 ELSE 0 END) as unapplied,
                    AVG(confidence) as avg_confidence
                FROM insights
            """).fetchone()

            # 高频 Bug（Top 10）
            top_bugs = conn.execute("""
                SELECT error_type, file_path, COUNT(*) as count, AVG(pain_score) as avg_pain
                FROM bug_memories
                GROUP BY error_type, file_path
                ORDER BY count DESC
                LIMIT 10
            """).fetchall()

            # 最近 7 天趋势
            week_ago = time.time() - (7 * 24 * 3600)
            daily_trend = conn.execute("""
                SELECT
                    DATE(first_seen) as date,
                    COUNT(*) as count,
                    AVG(pain_score) as avg_pain
                FROM bug_memories
                WHERE first_seen > ?
                GROUP BY DATE(first_seen)
                ORDER BY date
            """, (week_ago,)).fetchall()

            conn.close()

            return {
                "generated_at": datetime.now().isoformat(),
                "bug_memories": dict(bug_stats) if bug_stats else {},
                "insights": dict(insight_stats) if insight_stats else {},
                "top_recurring_bugs": [dict(row) for row in top_bugs],
                "daily_trend": [dict(row) for row in daily_trend],
                "sync_status": asdict(self.status),
                "quality_score": self._calculate_quality_score(bug_stats, insight_stats),
            }

        except Exception as e:
            return {
                "error": str(e),
            }

    def _calculate_quality_score(
        self, bug_stats: sqlite3.Row | None, insight_stats: sqlite3.Row | None
    ) -> dict[str, Any]:
        """计算记忆质量评分（0-100）"""
        if not bug_stats or not insight_stats:
            return {"score": 0, "level": "unknown"}

        score = 50.0  # 基础分

        # 正向指标
        if insight_stats["applied"] > 0:
            # Insights 应用率
            apply_rate = insight_stats["applied"] / max(insight_stats["total"], 1)
            score += apply_rate * 20  # 最高 +20

        if bug_stats["avg_pain"] and bug_stats["avg_pain"] > 50:
            # 平均 Pain Score 高（说明记忆的都是重要 Bug）
            score += 10

        # 负向指标
        if bug_stats["total_occurrences"] and bug_stats["total_occurrences"] > 100:
            # Bug 重复次数太多（可能缺乏有效修复）
            score -= 10

        if bug_stats["unique_errors"] and bug_stats["unique_errors"] > 50:
            # 错误类型太多（可能缺乏规范化）
            score -= 10

        score = max(0, min(100, score))

        if score >= 80:
            level = "excellent"
        elif score >= 60:
            level = "good"
        elif score >= 40:
            level = "fair"
        else:
            level = "poor"

        return {
            "score": round(score, 1),
            "level": level,
        }

    def print_quality_report(self):
        """打印记忆质量报告"""
        report = self.get_memory_quality_report()

        print("\n" + "=" * 60)
        print("  💾 记忆质量报告")
        print("=" * 60)

        if "error" in report:
            print(f"❌ 生成报告失败: {report['error']}")
            return

        # Bug 记忆统计
        bug = report.get("bug_memories", {})
        print(f"\n📊 Bug 记忆统计:")
        print(f"   总 Bug 数: {bug.get('total', 0)}")
        print(f"   平均 Pain Score: {bug.get('avg_pain', 0):.1f}")
        print(f"   最高 Pain Score: {bug.get('max_pain', 0):.1f}")
        print(f"   总出现次数: {bug.get('total_occurrences', 0)}")
        print(f"   影响文件数: {bug.get('affected_files', 0)}")

        # Insight 统计
        insights = report.get("insights", {})
        print(f"\n💡 Insight 统计:")
        print(f"   总 Insight 数: {insights.get('total', 0)}")
        print(f"   已应用: {insights.get('applied', 0)}")
        print(f"   未应用: {insights.get('unapplied', 0)}")
        print(f"   平均置信度: {insights.get('avg_confidence', 0):.2f}")

        # 质量评分
        quality = report.get("quality_score", {})
        print(f"\n⭐ 质量评分: {quality.get('score', 0)}/100 ({quality.get('level', 'unknown')})")

        # 高频 Bug
        top_bugs = report.get("top_recurring_bugs", [])
        if top_bugs:
            print(f"\n🔄 高频 Bug (Top {min(5, len(top_bugs))}):")
            for i, bug in enumerate(top_bugs[:5], 1):
                print(
                    f"   {i}. {bug.get('error_type', 'unknown')} "
                    f"in {bug.get('file_path', 'unknown')} "
                    f"({bug.get('count', 0)} 次, avg pain: {bug.get('avg_pain', 0):.1f})"
                )

        # 每日趋势
        trend = report.get("daily_trend", [])
        if trend:
            print(f"\n📈 最近 7 天趋势:")
            for day in trend:
                print(
                    f"   {day.get('date', '?')}: "
                    f"{day.get('count', 0)} 个 Bug "
                    f"(avg pain: {day.get('avg_pain', 0):.1f})"
                )

        print("=" * 60)


def create_memory_command_handler(bridge: Any, project_root: Path):
    """创建 moat memory 命令处理器

    Args:
        bridge: SharedStorageBridge 实例
        project_root: 项目根目录

    Returns:
        命令处理函数
    """

    def handler(args):
        sync_mgr = MemorySyncManager(bridge, project_root)

        if args.action == "status":
            # 显示同步状态
            print("\n📊 记忆同步状态:")
            print(f"   最后同步: {sync_mgr.status.last_sync_at or '从未'}")
            print(f"   最后梦境: {sync_mgr.status.last_dream_at or '从未'}")
            print(f"   总 Insights: {sync_mgr.status.total_insights}")
            print(f"   已应用: {sync_mgr.status.applied_insights}")
            print(f"   待处理: {sync_mgr.status.pending_insights}")
            if sync_mgr.status.last_error:
                print(f"   最后错误: {sync_mgr.status.last_error}")

        elif args.action == "dream":
            # 触发梦境引擎
            print("\n🌙 触发 One Memory 梦境引擎...")
            result = sync_mgr.trigger_dream_engine()
            if result["success"]:
                print(f"✅ {result.get('message', '成功')}")
                if result.get("insights"):
                    for insight in result["insights"]:
                        print(f"   - {insight.get('type', 'unknown')}: {insight.get('pattern', '')}")
            else:
                print(f"❌ {result.get('error', '失败')}")

        elif args.action == "sync":
            # 同步 Insights
            print("\n🔄 同步 Insights...")
            result = sync_mgr.sync_insights()
            if result["success"]:
                print(f"✅ {result.get('message', '成功')}")
            else:
                print(f"❌ {result.get('error', '失败')}")

        elif args.action == "report":
            # 生成记忆质量报告
            sync_mgr.print_quality_report()

        else:
            print(f"❌ 未知动作: {args.action}")

        return 0

    return handler
