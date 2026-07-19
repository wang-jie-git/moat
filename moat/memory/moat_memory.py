"""moat-memory — Moat 自有记忆系统

提供高层 API 操作四种记忆类型：
- redlines: 项目红线（架构规则、编码边界）
- lessons:  踩坑记录（每次 check 失败）
- templates: 经验模版（思维框架、模式）
- skills:    AI 工具技能指令

所有数据存储在 .moat/memory.db（SQLite），
不依赖任何外部服务。
"""
import json
import hashlib
import time
from pathlib import Path
from typing import Any

from moat.memory.bridge import SharedStorageBridge, BridgeConfig


class MoatMemory:
    """moat-memory 高层操作接口。"""

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root).resolve()
        db_path = self.project_root / ".moat" / "memory.db"
        config = BridgeConfig(db_path=db_path)
        self.bridge = SharedStorageBridge(config)
        self.bridge.initialize()

    # ── 红线 ──────────────────────────────────────────────

    def add_redline(
        self,
        title: str,
        description: str,
        severity: str = "warning",
        category: str = "general",
        source: str = "manual",
        file_glob: str | None = None,
    ) -> str | None:
        """添加一条红线。

        Args:
            title: 简短标题
            description: 具体描述
            severity: critical / warning / info
            category: architecture / security / style / dependency / general
            source: auto / manual / template
            file_glob: 适用文件的 glob 模式（可选）
        """
        return self.bridge.write_redline({
            "title": title,
            "description": description,
            "severity": severity,
            "category": category,
            "source": source,
            "file_glob": file_glob,
        })

    def list_redlines(self, category: str | None = None) -> list[dict]:
        """列出红线。"""
        return self.bridge.query_redlines(category=category)

    def remove_redline(self, redline_id: str) -> bool:
        """删除一条红线。"""
        return self.bridge.delete_redline(redline_id)

    # ── 踩坑 ──────────────────────────────────────────────

    def add_lesson(
        self,
        failed_tests: list[str],
        error_summary: str,
        principles: list[str] | None = None,
        negative_examples: list[dict] | None = None,
    ) -> str | None:
        """添加一条踩坑记录。

        Args:
            failed_tests: 失败测试名称列表
            error_summary: 错误摘要
            principles: 应遵守的原则
            negative_examples: 反模式列表
        """
        content_key = json.dumps(failed_tests, sort_keys=True)
        content_hash = hashlib.sha256(content_key.encode()).hexdigest()[:12]

        return self.bridge.write_lesson({
            "title": f"MOAT 门禁失败: {failed_tests[0].split('::')[0] if '::' in failed_tests[0] else failed_tests[0]}",
            "failed_tests": failed_tests,
            "error_summary": error_summary,
            "failure_count": len(failed_tests),
            "principles": principles or [
                "修改代码后必须运行 MOAT 门禁，不通过不能提交",
                "测试失败说明改动引入了预期之外的副作用，需要回溯排查",
            ],
            "negative_examples": negative_examples or [
                {
                    "scenario": "MOAT 门禁失败时强行提交",
                    "why_fails": "跳过的失败测试可能掩盖了系统性退化",
                    "better_approach": "先修复失败的测试再提交",
                }
            ],
            "content_hash": content_hash,
            "captured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

    def list_lessons(self, limit: int = 20) -> list[dict]:
        """列出踩坑记录。"""
        return self.bridge.query_lessons(limit=limit)

    def remove_lesson(self, lesson_id: str) -> bool:
        """删除一条踩坑记录。"""
        return self.bridge.delete_lesson(lesson_id)

    # ── 模版 ──────────────────────────────────────────────

    def add_template(
        self,
        domain: str,
        title: str,
        elements: dict | None = None,
        principles: list[str] | None = None,
        negative_examples: list[dict] | None = None,
        tags: list[str] | None = None,
        importance: int = 5,
        source: str = "manual",
    ) -> str | None:
        """添加一条经验模版。

        Args:
            domain: 领域（如 api_design, error_handling）
            title: 模版标题
            elements: 核心要素（dict）
            principles: 设计原则
            negative_examples: 反模式
            tags: 标签
            importance: 重要性 1-10
            source: manual / auto_extracted
        """
        content_key = json.dumps({"domain": domain, "title": title}, sort_keys=True)
        content_hash = hashlib.sha256(content_key.encode()).hexdigest()[:12]
        return self.bridge.write_template_entry({
            "domain": domain,
            "title": title,
            "source": source,
            "elements": elements or {},
            "principles": principles or [],
            "negative_examples": negative_examples or [],
            "tags": tags or [],
            "importance": importance,
            "content_hash": content_hash,
        })

    def list_templates(self, domain: str | None = None) -> list[dict]:
        """列出模版。"""
        return self.bridge.query_templates(domain=domain)

    def remove_template(self, template_id: str) -> bool:
        """删除一条模版。"""
        return self.bridge.delete_template_entry(template_id)

    # ── 技能 ──────────────────────────────────────────────

    def add_skill(self, tool: str, instruction: str, priority: int = 0) -> str | None:
        """添加一条技能指令。

        Args:
            tool: 工具名（claude / codex / opencode / cursor）
            instruction: 指令内容
            priority: 优先级（越高越优先注入）
        """
        return self.bridge.write_skill({
            "tool": tool,
            "instruction": instruction,
            "priority": priority,
        })

    def list_skills(self, tool: str | None = None) -> list[dict]:
        """列出技能指令。"""
        return self.bridge.query_skills(tool=tool)

    # ── 统计 ──────────────────────────────────────────────

    def stats(self) -> dict[str, int]:
        """获取记忆统计概览。"""
        return self.bridge.get_memory_stats()

    def format_redlines_for_ai(self) -> str:
        """将红线格式化为 AI 可读的文本。"""
        redlines = self.list_redlines()
        if not redlines:
            return ""
        lines = ["📏 项目红线:"]
        for rl in redlines:
            icon = {"critical": "🔴", "warning": "🟡", "info": "ℹ️"}.get(rl.get("severity", "warning"), "⚠️")
            lines.append(f"  {icon} {rl['title']}: {rl['description']}")
        return "\n".join(lines)

    def format_lessons_for_ai(self, limit: int = 5) -> str:
        """将踩坑记录格式化为 AI 可读的文本。"""
        lessons = self.list_lessons(limit=limit)
        if not lessons:
            return ""
        lines = ["📝 项目踩坑记录（最近）:"]
        for lsn in lessons:
            tests = json.loads(lsn.get("failed_tests", "[]")) if isinstance(lsn.get("failed_tests"), str) else lsn.get("failed_tests", [])
            lines.append(f"  • {lsn['title']}")
            if tests:
                lines.append(f"    失败: {'; '.join(t[:60] for t in tests[:3])}")
        return "\n".join(lines)

    # ── 生命周期 ──────────────────────────────────────────

    def close(self):
        self.bridge.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
