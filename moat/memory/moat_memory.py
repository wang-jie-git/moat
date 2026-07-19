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

    # ── 从 git diff 提取模版 ────────────────────────────

    def extract_template_from_git(
        self,
        commit: str = "HEAD",
        repo_path: str | None = None,
        use_llm: bool = False,
        llm_model: str | None = None,
        llm_base_url: str | None = None,
    ) -> dict | None:
        """从 git commit 的 diff 中提取经验模版。

        分析最近一次（或指定）commit 的变更：
        - commit message → 模版标题
        - 变更文件路径 → 推断领域
        - diff 内容 → 提取原则和反模式

        Args:
            commit: git commit 引用（默认 HEAD，即最新一次提交）
            repo_path: git 仓库路径（默认当前项目根目录）
            use_llm: 是否启用 LLM 语义分析（需配置 OPENAI_API_KEY 环境变量）
            llm_model: LLM 模型名（覆盖默认值 gpt-4o-mini）
            llm_base_url: LLM API 地址（覆盖默认值）

        Returns:
            生成的模版 dict，或 None（没有变更/出错）
        """
        import subprocess
        import re

        git_dir = repo_path or str(self.project_root)

        try:
            # 1. 获取 commit message
            msg_result = subprocess.run(
                ["git", "log", "-1", "--format=%s%n%b", commit],
                capture_output=True, text=True, cwd=git_dir, timeout=10,
            )
            if msg_result.returncode != 0:
                print(f"❌ git log 失败: {msg_result.stderr.strip()}")
                return None
            full_msg = msg_result.stdout.strip()
            msg_lines = full_msg.split("\n", 1)
            title = msg_lines[0][:80] if msg_lines else "无标题"
            body = msg_lines[1].strip() if len(msg_lines) > 1 else ""

            # 2. 获取 diff stat（文件变更摘要）
            stat_result = subprocess.run(
                ["git", "diff", f"{commit}~1", "--stat"],
                capture_output=True, text=True, cwd=git_dir, timeout=10,
            )
            stat_output = stat_result.stdout.strip()

            # 3. 解析变更文件列表
            changed_files = []
            for line in stat_output.split("\n"):
                line = line.strip()
                if "|" in line and not line.startswith(" ") and not line.startswith("("):
                    parts = line.split("|")[0].strip()
                    changed_files.append(parts)

            if not changed_files:
                print("⚠️  没有检测到文件变更")
                return None

            # 检查去重：已存在相同模版则跳过
            existing = self.list_templates()
            for t in existing:
                existing_title = t.get("title", "").lower()
                if title.lower() in existing_title or existing_title in title.lower():
                    print(f"⏭️  模版已存在，跳过: {title}")
                    return {"id": t.get("id"), "domain": t.get("domain"), "title": title, "principles": t.get("principles", []), "skipped": True}

            # 4. 选择提取方式
            if use_llm:
                return self._extract_with_llm(
                    commit=commit, git_dir=git_dir,
                    msg=full_msg, changed_files=changed_files,
                    model=llm_model, base_url=llm_base_url,
                )

            # 关键词规则（默认，零依赖）
            domain = self._infer_domain_from_files(changed_files)
            principles = self._infer_principles(full_msg, changed_files)

            template = self.add_template(
                domain=domain,
                title=title,
                elements={
                    "files_changed": changed_files[:10],
                    "commit_message": body if body else title,
                    "total_files": len(changed_files),
                },
                principles=principles,
                source="auto_extracted",
                importance=6,
                tags=[domain, "auto_extracted"],
            )

            if template:
                print(f"✅ 模版已提取: {template}")
                print(f"   领域: {domain}")
                print(f"   标题: {title}")
                print(f"   原则: {'; '.join(principles)}")

            return {"id": template, "domain": domain, "title": title, "principles": principles}

        except subprocess.TimeoutExpired:
            print("❌ git 操作超时")
            return None
        except FileNotFoundError:
            print("❌ git 未安装或不在 PATH 中")
            return None
        except Exception as e:
            print(f"❌ 提取失败: {e}")
            return None

    def _extract_with_llm(
        self,
        commit: str,
        git_dir: str,
        msg: str,
        changed_files: list[str],
        model: str | None = None,
        base_url: str | None = None,
    ) -> dict | None:
        """使用 LLM 语义分析提取模版（降级到关键词规则）。"""
        import json
        import os
        import urllib.request
        import subprocess

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("⚠️  OPENAI_API_KEY 未设置，降级为关键词规则")
            return self._extract_fallback(msg, changed_files)

        api_base = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        llm_model = model or os.environ.get("MOAT_LLM_MODEL", "gpt-4o-mini")

        # 获取完整 diff
        try:
            diff_result = subprocess.run(
                ["git", "diff", f"{commit}~1", "--", *changed_files],
                capture_output=True, text=True, cwd=git_dir, timeout=15,
            )
            diff_content = diff_result.stdout[:8000]  # 截断，防止超长 diff
        except Exception:
            diff_content = ""

        prompt = f"""你是一个经验丰富的代码审查专家。请分析以下 git commit 的变更，提取出可复用的经验模版。

## Commit Message
{msg}

## 变更文件
{chr(10).join(changed_files)}

## Diff 内容
{diff_content or "(无详细 diff，仅文件列表)"}

请以 JSON 格式输出分析结果，包含以下字段：
- domain: 领域分类（api_design / testing / error_handling / security / data_model / data_access / configuration / infrastructure / observability / deployment / general）
- title: 模版标题（简洁，20 字以内）
- principles: 应遵守的原则列表（2-4 条，每条一句话）
- negative_examples: 反模式列表（至少 1 条，每条包含 scenario 和 better_approach）
- tags: 标签列表（3-5 个）

只输出 JSON，不要其他内容。"""

        print(f"🤖 调用 LLM ({llm_model}) 分析 diff...")
        try:
            req = urllib.request.Request(
                f"{api_base.rstrip('/')}/chat/completions",
                data=json.dumps({
                    "model": llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 1500,
                }).encode(),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())

            content = result["choices"][0]["message"]["content"]
            # 提取 JSON（兼容 markdown 代码块包裹的情况）
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            parsed = json.loads(content)

            domain = parsed.get("domain", "general")
            title = parsed.get("title", msg[:80])
            principles = parsed.get("principles", [])
            negative_examples = parsed.get("negative_examples", [])
            tags = parsed.get("tags", [domain, "llm_extracted"])

            template = self.add_template(
                domain=domain,
                title=title,
                elements={
                    "files_changed": changed_files[:10],
                    "commit_message": msg,
                    "total_files": len(changed_files),
                    "llm_analysis": True,
                },
                principles=principles,
                negative_examples=negative_examples,
                source="llm_extracted",
                importance=7,
                tags=tags,
            )

            if template:
                print(f"✅ 模版已提取（LLM）: {template}")
                print(f"   领域: {domain}")
                print(f"   标题: {title}")
                print(f"   原则: {'; '.join(principles)}")
                if negative_examples:
                    print(f"   反模式: {len(negative_examples)} 条")

            return {"id": template, "domain": domain, "title": title, "principles": principles}

        except Exception as e:
            print(f"⚠️  LLM 调用失败: {e}，降级为关键词规则")
            return self._extract_fallback(msg, changed_files)

    def _extract_fallback(self, msg: str, changed_files: list[str]) -> dict | None:
        """关键词规则降级。"""
        domain = self._infer_domain_from_files(changed_files)
        principles = self._infer_principles(msg, changed_files)
        title = msg.split("\n")[0][:80]

        template = self.add_template(
            domain=domain,
            title=title,
            elements={
                "files_changed": changed_files[:10],
                "commit_message": msg,
                "total_files": len(changed_files),
                "llm_fallback": True,
            },
            principles=principles,
            source="auto_extracted",
            importance=6,
            tags=[domain, "auto_extracted"],
        )

        if template:
            print(f"✅ 模版已提取（降级）: {template}")
            print(f"   领域: {domain}")
            print(f"   标题: {title}")
            print(f"   原则: {'; '.join(principles)}")

        return {"id": template, "domain": domain, "title": title, "principles": principles}

    @staticmethod
    def _infer_domain_from_files(files: list[str]) -> str:
        """从变更文件路径推断领域。"""
        domain_scores = {}
        for f in files:
            path_lower = f.lower()
            for keyword, domain in [
                ("api", "api_design"),
                ("route", "api_design"),
                ("endpoint", "api_design"),
                ("controller", "api_design"),
                ("model", "data_model"),
                ("schema", "data_model"),
                ("db/", "data_access"),
                ("database", "data_access"),
                ("sql", "data_access"),
                ("migration", "data_access"),
                ("test", "testing"),
                ("spec", "testing"),
                ("mock", "testing"),
                ("config", "configuration"),
                ("setting", "configuration"),
                ("security", "security"),
                ("auth", "security"),
                ("middleware", "infrastructure"),
                ("error", "error_handling"),
                ("exception", "error_handling"),
                ("memory", "architecture"),
                ("log", "observability"),
                ("metric", "observability"),
                ("monitor", "observability"),
                ("docker", "deployment"),
                ("ci/", "deployment"),
                ("deploy", "deployment"),
            ]:
                if keyword in path_lower:
                    domain_scores[domain] = domain_scores.get(domain, 0) + 1

        if not domain_scores:
            return "general"
        return max(domain_scores, key=domain_scores.get)

    @staticmethod
    def _infer_principles(commit_msg: str, files: list[str]) -> list[str]:
        """从 commit message 和文件列表推断应遵守的原则。"""
        principles = []
        msg_lower = commit_msg.lower()

        # 从 commit message 的关键词推断
        if any(w in msg_lower for w in ["fix", "bug", "修复", "错误", "issue", "hotfix"]):
            principles.append("修复 bug 后应添加对应的回归测试，防止同类问题再次出现")
        if any(w in msg_lower for w in ["refactor", "重构", "clean", "清理", "重写"]):
            principles.append("重构应保持行为不变，测试结果应前后一致")
        if any(w in msg_lower for w in ["add", "新增", "feature", "feat", "功能"]):
            principles.append("新增功能应同步补充文档和测试")
        if any(w in msg_lower for w in ["remove", "删除", "deprecate", "废弃"]):
            principles.append("删除代码前应确认无其他模块依赖该功能")
        if any(w in msg_lower for w in ["upgrade", "升级", "migrate", "迁移", "version"]):
            principles.append("版本升级应验证向后兼容性，并更新依赖声明")
        if any(w in msg_lower for w in ["perform", "性能", "optimize", "优化", "speed"]):
            principles.append("性能优化应附基准测试数据证明收益")
        if any(w in msg_lower for w in ["security", "安全", "vulnerability", "漏洞", "cve"]):
            principles.append("安全修复应优先合入，并在 changelog 中标注 CVE 编号")

        # 从文件类型推断
        py_files = [f for f in files if f.endswith(".py")]
        test_files = [f for f in files if "test" in f.lower()]
        if py_files and not test_files:
            principles.append("修改 Python 代码后应运行 `moat check` 确保不引入回归")

        if not principles:
            principles.append("代码变更应遵循项目现有架构风格，不做不必要的大幅重构")

        return principles

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

    def format_all_for_ai(self, redline_limit: int = 20, lesson_limit: int = 5, template_limit: int = 5) -> str:
        """将所有记忆格式化为 AI 可读的文本块。"""
        sections = []

        # 红线
        redlines = self.list_redlines()
        if redlines:
            rl_lines = ["📏 项目红线:"]
            for rl in redlines[:redline_limit]:
                icon = {"critical": "🔴", "warning": "🟡", "info": "ℹ️"}.get(rl.get("severity", "warning"), "⚠️")
                rl_lines.append(f"  {icon} {rl['title']}: {rl['description']}")
            sections.append("\n".join(rl_lines))

        # 踩坑
        lessons = self.list_lessons(limit=lesson_limit)
        if lessons:
            ls_lines = ["📝 项目踩坑记录（最近）:"]
            for lsn in lessons:
                tests = json.loads(lsn.get("failed_tests", "[]")) if isinstance(lsn.get("failed_tests"), str) else lsn.get("failed_tests", [])
                ls_lines.append(f"  • {lsn['title']}")
                if tests:
                    ls_lines.append(f"    失败: {'; '.join(t[:60] for t in tests[:3])}")
            sections.append("\n".join(ls_lines))

        # 模版
        templates = self.list_templates()
        if templates:
            tp_lines = ["📋 经验模版:"]
            for t in templates[:template_limit]:
                principles = t.get("principles", [])
                tp_lines.append(f"  • [{t.get('domain','?')}] {t.get('title','?')}")
                if principles:
                    for p in principles[:3]:
                        tp_lines.append(f"    - {p}")
            sections.append("\n".join(tp_lines))

        return "\n\n".join(sections)

    # ── 生命周期 ──────────────────────────────────────────

    def close(self):
        self.bridge.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
