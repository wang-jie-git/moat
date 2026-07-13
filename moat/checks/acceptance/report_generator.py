"""验收报告生成器 — 将验收结果输出为结构化 Markdown/JSON 报告

报告格式严格遵循"Vibe Coding 验收 8 步法":
1. 架构规则审计        (Architecture Rules Audit)
2. 目录责任边界        (Directory Responsibility)
3. 最小模块演练        (Minimal Module Drill)
4. 接口统一返回规范    (API Response Consistency)
5. 框架复用与封装边界  (Framework Boundary)
6. 运行证据固定        (Runtime Evidence)
7. 收口验收结果        (Conclusion & Truth Document)
8. 固化版本基线        (Git Baseline)
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from .rule_registry import RuleRegistry
from .architect_runner import AcceptanceReport


class AcceptanceReportGenerator:
    """验收报告生成器"""

    def __init__(self, report: AcceptanceReport):
        self.report = report
        self.steps = report.steps_info or RuleRegistry.get_default_steps_info()

    # ── Markdown 报告 ──

    def to_markdown(self, include_evidence: bool = True) -> str:
        """生成结构化 Markdown 报告（8 步格式）"""
        lines = []

        # ── 封面 ──
        lines.extend(self._cover_section())

        # ── 摘要 ──
        lines.extend(self._summary_section())

        # ── 逐步骤报告（1-8） ──
        for step_num in range(1, 9):
            step_info = self.steps.get(step_num, {"title": f"步骤 {step_num}", "description": ""})
            step_rules = [r for r in self.report.rules if r.rule.step == step_num]

            lines.extend(self._step_section(step_num, step_info, step_rules, include_evidence))

        # ── 结论 ──
        lines.extend(self._conclusion_section())

        # ── 证据索引 ──
        if include_evidence and self.report.evidence_dir:
            lines.extend(self._evidence_index_section())

        return "\n".join(lines)

    def _cover_section(self) -> list[str]:
        """封面"""
        return [
            "# 🏗 架构验收报告",
            "",
            f"**项目**: `{self.report.project_path}`",
            f"**验收时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**验收版本**: v{self.report.version}",
            f"**工具**: Moat Accept (moat-ai)",
            "",
            "---",
            "",
        ]

    def _summary_section(self) -> list[str]:
        """摘要"""
        passed_icon = "✅" if self.report.passed else "❌"
        summary = self.report.summary()

        # 统计违规严重程度
        critical = sum(1 for r in self.report.rules for v in r.violations if v.get("severity") == "CRITICAL")
        high = sum(1 for r in self.report.rules for v in r.violations if v.get("severity") == "HIGH")
        warning = sum(1 for r in self.report.rules for v in r.violations if v.get("severity") == "RECOMMENDED")

        # 每个步骤的状态
        step_status = []
        for step_num in range(1, 9):
            step_rules = [r for r in self.report.rules if r.rule.step == step_num]
            if not step_rules:
                step_status.append(f"  {step_num}. ⚪ 无规则")
                continue
            all_ok = all(
                (r.passed or not r.rule.auto_checkable)
                for r in step_rules
            )
            icon = "✅" if all_ok else "❌"
            step_info = self.steps.get(step_num, {"title": f"步骤 {step_num}"})
            step_status.append(f"  {step_num}. {icon} {step_info['title']}")

        return [
            "## 📊 验收摘要",
            "",
            f"| 指标 | 结果 |",
            f"|------|------|",
            f"| 总体评分 | {summary['score']} |",
            f"| 验收结论 | {passed_icon} {'通过' if self.report.passed else '未通过'} |",
            f"| 自动检查 | {summary['auto']} |",
            f"| 人工核查 | {summary['manual']} 项 |",
            f"| 🔴 CRITICAL 违规 | {critical} |",
            f"| 🟡 HIGH 违规 | {high} |",
            f"| ⚠️ RECOMMENDED | {warning} |",
            f"| 耗时 | {summary['time']} |",
            "",
            "### 各步骤状态",
            "",
            *step_status,
            "",
            "---",
            "",
        ]

    def _step_section(self, step_num: int, step_info: dict, step_rules: list, include_evidence: bool) -> list[str]:
        """单步骤报告节"""
        if not step_rules:
            return [
                f"## 步骤 {step_num}: {step_info['title']}",
                "",
                f"_{step_info['description']}_",
                "",
                "⚪ 未配置规则",
                "",
                "---",
                "",
            ]

        lines = [
            f"## 步骤 {step_num}: {step_info['title']}",
            "",
            f"_{step_info['description']}_",
            "",
        ]

        for result in step_rules:
            rule = result.rule
            status_icon = "✅" if result.passed or not rule.auto_checkable else "❌"

            lines.append(f"### {status_icon} [{rule.id}] {rule.title}")
            lines.append("")
            lines.append(f"**严重级别**: {rule.severity}")
            lines.append(f"**验证方式**: {'自动' if result.auto_checked else '人工核查'}")
            lines.append("")

            # 规则描述
            if rule.description:
                lines.append(f"{rule.description}")
                lines.append("")

            # 违规
            if result.violations:
                lines.append(f"**违规 ({len(result.violations)})**:")
                for v in result.violations:
                    sev_icon = {"CRITICAL": "🔴", "HIGH": "🟡", "RECOMMENDED": "⚠️"}.get(
                        v.get("severity", ""), "📌"
                    )
                    file_info = ""
                    if v.get("file"):
                        file_info = f" — `{v['file']}`"
                        if v.get("line"):
                            file_info += f":{v['line']}"
                    lines.append(f"- {sev_icon} {v.get('message', '')}{file_info}")
                lines.append("")

            # 人工核查项
            if result.manual_check_items:
                lines.append(f"**人工核查项**:")
                for item in result.manual_check_items:
                    lines.append(f"- □ {item}")
                lines.append("")

            # 证据
            if include_evidence and result.evidence:
                lines.append(f"**证据 ({len(result.evidence)})**:")
                for e in result.evidence:
                    lines.append(f"- {e}")
                lines.append("")

            # 建议
            if result.suggestion:
                lines.append(f"**建议**: {result.suggestion}")
                lines.append("")

        lines.append("---")
        lines.append("")

        return lines

    def _conclusion_section(self) -> list[str]:
        """验收结论"""
        critical = sum(1 for r in self.report.rules for v in r.violations if v.get("severity") == "CRITICAL")
        high = sum(1 for r in self.report.rules for v in r.violations if v.get("severity") == "HIGH")
        manual_pending = self.report.total_manual

        if self.report.passed and critical == 0 and high == 0 and manual_pending == 0:
            conclusion = "✅ **架构验收通过**。所有规则验证完成，可以进入业务开发。"
            decision = "允许进入业务开发"
        elif critical > 0:
            conclusion = "❌ **架构验收不通过**。存在 CRITICAL 级别违规，必须修复后重新验收。"
            decision = "禁止进入业务开发（CRITICAL 违规未修复）"
        elif high > 0:
            conclusion = "⚠️ **架构验收有条件通过**。存在 HIGH 级别违规，建议修复后再进入业务开发。"
            decision = "有条件进入业务开发（需修复 HIGH 违规）"
        elif manual_pending > 0:
            conclusion = "📋 **架构验收待完成**。所有自动检查通过，但还有人工核查项未确认。"
            decision = "待人工核查完成后确认"
        else:
            conclusion = "⚠️ **架构验收未通过**。请修复违规后重新验收。"
            decision = "未通过"

        return [
            "## 📋 验收结论",
            "",
            f"### {conclusion}",
            "",
            "| 决策项 | 结果 |",
            "|--------|------|",
            f"| 进入业务开发 | {decision} |",
            f"| 🔴 CRITICAL 违规 | {critical} |",
            f"| 🟡 HIGH 违规 | {high} |",
            f"| 👤 人工核查待完成 | {manual_pending} |",
            f"| 📊 总体评分 | {self.report.overall_score:.0f}/100 |",
            "",
            "### 后续操作",
            "",
        ] + ([
            "- 修复 CRITICAL 违规后重新运行 `moat accept`",
        ] if critical > 0 else []) + ([
            "- 运行 `moat accept --generate-rules` 生成完整规则模板",
        ] if manual_pending > 0 else []) + [
            "- 手动确认人工核查项后更新验收报告",
            "- 验收通过后运行 `moat baseline save` 固化版本",
            "",
        ]

    def _evidence_index_section(self) -> list[str]:
        """证据索引"""
        evidence_dir = self.report.evidence_dir
        if not evidence_dir or not evidence_dir.exists():
            return []

        files = list(evidence_dir.iterdir())
        if not files:
            return []

        return [
            "## 📁 证据索引",
            "",
            f"证据目录: `{evidence_dir}`",
            "",
            "| 文件 | 大小 |",
            "|------|------|",
            *[f"| `{f.name}` | {f.stat().st_size} bytes |" for f in sorted(files)],
            "",
        ]

    # ── JSON 报告 ──

    def to_json(self, indent: int = 2) -> str:
        """生成 JSON 格式报告"""
        return json.dumps(self.report.to_dict(), indent=indent, ensure_ascii=False)

    # ── 保存报告 ──

    def save(self, path: str | Path, fmt: str = "md") -> Path:
        """保存报告到文件"""
        path = Path(path)

        # 自动生成文件名
        if path.is_dir() or path.suffix not in (".md", ".json"):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ACCEPTANCE_REPORT_{timestamp}.{fmt}"
            path = path / filename

        if fmt == "json":
            content = self.to_json()
        else:
            content = self.to_markdown()

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path
