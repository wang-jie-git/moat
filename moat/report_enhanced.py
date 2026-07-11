"""增强报告生成器

功能：
1. 错误分组（按严重性排序）
2. 文件维度统计
3. 可视化错误摘要
"""
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from moat.runner import MoatResult
from moat.checks import detect_project_type


class EnhancedReportGenerator:
    """增强报告生成器

    支持：
    - 按严重性分组错误（CRITICAL → INFO）
    - 文件维度统计
    - Markdown / JSON 格式输出
    """

    def __init__(self, project_root: Path, result: MoatResult):
        self.project = project_root.resolve()
        self.result = result
        self.project_types = detect_project_type(self.project)

    def generate(self, format: str = "text", enhanced: bool = True) -> str:
        """生成报告

        Args:
            format: 输出格式（text / md / json）
            enhanced: 是否使用增强格式

        Returns:
            格式化后的报告文本
        """
        if format == "md":
            return self._generate_enhanced_markdown() if enhanced else self._generate_markdown()
        elif format == "json":
            return self._generate_json()
        return self._generate_enhanced_text() if enhanced else self._generate_text()

    def _generate_enhanced_markdown(self) -> str:
        """生成增强的 Markdown 报告"""
        lines = []

        # 1. 标题
        lines.append("# Moat 检查报告")
        lines.append("")
        lines.append(f"**项目**: `{self.project}`")
        lines.append(f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**项目类型**: {', '.join(k for k, v in self.project_types.items() if v) or '未知'}")
        lines.append("")

        # 2. 错误摘要（按严重性）
        severity_summary = self._get_severity_summary()
        lines.append("## 📊 错误摘要（按严重性）")
        lines.append("")

        for level, count in severity_summary.items():
            if count > 0:
                symbol = self._get_level_symbol(level)
                lines.append(f"- {symbol} **{level}**: {count}")
        lines.append("")

        # 3. 文件维度统计
        file_stats = self._get_file_statistics()
        if file_stats:
            lines.append("## 📁 文件维度统计")
            lines.append("")
            lines.append("| 文件 | 错误数 | CRITICAL | HIGH | MEDIUM | LOW |")
            lines.append("|------|--------|----------|------|--------|-----|")

            for file_path, stats in sorted(file_stats.items(), key=lambda x: -x[1]["total"]):
                lines.append(
                    f"| `{file_path}` | {stats['total']} | {stats.get('CRITICAL', 0)} | "
                    f"{stats.get('HIGH', 0)} | {stats.get('MEDIUM', 0)} | {stats.get('LOW', 0)} |"
                )
            lines.append("")

        # 4. 详细错误列表（按严重性分组）
        severity_groups = self._group_by_severity()

        lines.append("## 🔍 详细错误列表")
        lines.append("")

        has_errors = False
        for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
            errors = severity_groups.get(level, [])
            if errors:
                has_errors = True
                symbol = self._get_level_symbol(level)
                lines.append(f"### {symbol} {level}")
                lines.append("")

                for error in errors:
                    file_info = f"`{error.get('file', '?')}`"
                    line_info = f":{error['line']}" if error.get("line") else ""
                    lines.append(f"- {file_info}{line_info}: {error.get('message', '无信息')}")
                lines.append("")

        if not has_errors:
            lines.append("✅ **没有发现任何问题**")
            lines.append("")

        # 5. 总结
        lines.append("## 📝 总结")
        lines.append("")
        lines.append(f"- **总检查数**: {self.result.total_checks}")
        lines.append(f"- **通过**: {self.result.passed} ✅")
        lines.append(f"- **失败**: {self.result.failed} ❌")
        lines.append(f"- **警告**: {self.result.warnings} ⚠️")
        lines.append(f"- **跳过**: {self.result.skipped} ·")
        lines.append(f"- **耗时**: {self.result.duration:.2f}s")
        lines.append("")

        return "\n".join(lines)

    def _generate_enhanced_text(self) -> str:
        """生成增强的纯文本报告"""
        lines = []

        # 1. 标题
        lines.append("=" * 80)
        lines.append("  Moat — AI 编码守门员")
        lines.append(f"  项目: {self.project}")
        lines.append(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)
        lines.append("")

        # 2. 错误摘要
        severity_summary = self._get_severity_summary()
        lines.append("📊 错误摘要（按严重性）：")

        for level, count in severity_summary.items():
            if count > 0:
                symbol = self._get_level_symbol(level)
                lines.append(f"  {symbol} {level}: {count}")
        lines.append("")

        # 3. 文件维度统计
        file_stats = self._get_file_statistics()
        if file_stats:
            lines.append("📁 文件维度统计（前 10 个）：")
            lines.append("")

            sorted_files = sorted(file_stats.items(), key=lambda x: -x[1]["total"])[:10]
            for file_path, stats in sorted_files:
                lines.append(f"  {file_path}")
                lines.append(f"    总计: {stats['total']} | CRITICAL: {stats.get('CRITICAL', 0)} | "
                           f"HIGH: {stats.get('HIGH', 0)} | MEDIUM: {stats.get('MEDIUM', 0)}")
            lines.append("")

        # 4. 详细错误
        severity_groups = self._group_by_severity()
        has_errors = False

        for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
            errors = severity_groups.get(level, [])
            if errors:
                has_errors = True
                symbol = self._get_level_symbol(level)
                lines.append(f"{symbol} {level} 错误：")
                lines.append("")

                for error in errors:
                    file_info = f"{error.get('file', '?')}"
                    line_info = f":{error['line']}" if error.get("line") else ""
                    lines.append(f"  [{file_info}{line_info}]")
                    lines.append(f"    {error.get('message', '无信息')}")
                lines.append("")

        if not has_errors:
            lines.append("✅ 没有发现任何问题")
            lines.append("")

        # 5. 总结
        lines.append("=" * 80)
        lines.append("  结果: 通过: {0}, 失败: {1}, 警告: {2}, 耗时: {3:.2f}s".format(
            self.result.passed,
            self.result.failed,
            self.result.warnings,
            self.result.duration,
        ))
        lines.append("=" * 80)

        return "\n".join(lines)

    def _get_severity_summary(self) -> dict[str, int]:
        """获取严重性摘要"""
        summary = defaultdict(int)

        for error in self.result.errors:
            level = error.get("level", "INFO")
            summary[level] += 1

        return dict(summary)

    def _get_file_statistics(self) -> dict[str, dict[str, int]]:
        """获取文件维度统计"""
        file_stats = defaultdict(lambda: defaultdict(int))

        for error in self.result.errors:
            file_path = error.get("file", "unknown")
            level = error.get("level", "INFO")

            file_stats[file_path]["total"] += 1
            file_stats[file_path][level] += 1

        return dict(file_stats)

    def _group_by_severity(self) -> dict[str, list[dict]]:
        """按严重性分组错误"""
        groups = defaultdict(list)

        for error in self.result.errors:
            level = error.get("level", "INFO")
            groups[level].append(error)

        return dict(groups)

    def _get_level_symbol(self, level: str) -> str:
        """获取严重性级别对应的符号"""
        symbols = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🔵",
            "INFO": "ℹ️",
            "ERROR": "❌",
            "WARN": "⚠️",
        }
        return symbols.get(level, "·")

    def _generate_text(self) -> str:
        """生成纯文本报告（兼容旧版）"""
        return self._generate_enhanced_text()

    def _generate_markdown(self) -> str:
        """生成 Markdown 报告（兼容旧版）"""
        return self._generate_enhanced_markdown()

    def _generate_json(self) -> str:
        """生成 JSON 报告"""
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "project": str(self.project),
            "project_types": {k: v for k, v in self.project_types.items() if v},
            "summary": {
                "total_checks": self.result.total_checks,
                "passed": self.result.passed,
                "failed": self.result.failed,
                "warnings": self.result.warnings,
                "skipped": self.result.skipped,
                "duration": round(self.result.duration, 2),
            },
            "severity_summary": self._get_severity_summary(),
            "file_statistics": self._get_file_statistics(),
            "errors": self.result.errors,
        }

        return json.dumps(report_data, indent=2, ensure_ascii=False)
