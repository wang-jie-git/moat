"""L2 架构健康报告生成器

专门用于生成架构健康分析的独立报告

Usage:
    moat architecture --format md     # Markdown 格式
    moat architecture --format json   # JSON 格式（用于 CI/CD）
    moat architecture --copy          # 复制到剪贴板
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from moat.runner import run_all_checks
from moat.baseline import BaselineManager
from moat.checks.l2_architecture import run_architecture_check


class ArchitectureReportGenerator:
    """架构健康报告生成器"""

    def __init__(self, project_root: Path):
        self.project = project_root.resolve()
        self.baseline_mgr = BaselineManager(self.project)
        self.baseline = self.baseline_mgr.load()

    def generate(self, format: str = "text") -> str:
        """生成架构健康报告

        Args:
            format: 输出格式（text / md / json）

        Returns:
            格式化后的报告文本
        """
        if format == "json":
            return self._generate_json()
        elif format == "md":
            return self._generate_markdown()
        return self._generate_text()

    def _generate_json(self) -> str:
        """生成 JSON 格式报告（用于 CI/CD）"""
        # 运行 L2 检查
        l2_errors = run_architecture_check(
            self.project,
            baseline=self.baseline,
            quick_mode=False,
        )

        # 分类统计
        entropy_errors = [e for e in l2_errors if "entropy" in e.get("type", "")]
        hub_errors = [e for e in l2_errors if "hub" in e.get("type", "")]
        change_errors = [e for e in l2_errors if "changed" in e.get("type", "")]

        # 计算健康评分
        health_score = self._calculate_health_score(l2_errors)

        report = {
            "timestamp": datetime.now().isoformat(),
            "project": str(self.project),
            "health_score": health_score,
            "summary": {
                "total_issues": len(l2_errors),
                "entropy_issues": len(entropy_errors),
                "hub_issues": len(hub_errors),
                "change_issues": len(change_errors),
            },
            "entropy": {
                "high": [e for e in entropy_errors if "high" in e.get("type", "")],
                "medium": [e for e in entropy_errors if "medium" in e.get("type", "")],
                "summary": [e for e in entropy_errors if "summary" in e.get("type", "")],
            },
            "dependency_hubs": [e for e in hub_errors if "hub" == e.get("type", "")],
            "file_changes": change_errors,
            "recommendations": self._generate_recommendations(l2_errors),
        }

        return json.dumps(report, indent=2, ensure_ascii=False)

    def _generate_markdown(self) -> str:
        """生成 Markdown 格式报告"""
        # 运行 L2 检查
        l2_errors = run_architecture_check(
            self.project,
            baseline=self.baseline,
            quick_mode=False,
        )

        if not l2_errors:
            return self._generate_no_issues_markdown()

        lines = [
            f"# 🏗️  架构健康报告",
            "",
            f"**项目**: `{self.project}`",
            f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        # 健康评分
        health_score = self._calculate_health_score(l2_errors)
        lines.extend([
            "## 📊 健康评分",
            "",
            f"**评分**: {health_score}/100",
            f"**状态**: {'🟢 健康' if health_score >= 80 else '🟡 警告' if health_score >= 60 else '🔴 需关注'}",
            "",
        ])

        # 问题汇总
        entropy_count = len([e for e in l2_errors if "entropy" in e.get("type", "")])
        hub_count = len([e for e in l2_errors if "hub" in e.get("type", "")])
        change_count = len([e for e in l2_errors if "changed" in e.get("type", "")])

        lines.extend([
            "## 📋 问题汇总",
            "",
            f"- 🔴 高熵增：{entropy_count} 个",
            f"- ⚠️  依赖枢纽：{hub_count} 个",
            f"- 📝 文件变更：{change_count} 个",
            "",
        ])

        # 详细问题
        if entropy_count > 0:
            lines.extend(self._format_entropy_markdown(l2_errors))

        if hub_count > 0:
            lines.extend(self._format_hubs_markdown(l2_errors))

        if change_count > 0:
            lines.extend(self._format_changes_markdown(l2_errors))

        # 改进建议
        recommendations = self._generate_recommendations(l2_errors)
        if recommendations:
            lines.extend([
                "## 💡 改进建议",
                "",
            ])
            for rec in recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        return "\n".join(lines)

    def _generate_text(self) -> str:
        """生成纯文本格式报告"""
        # 运行 L2 检查
        l2_errors = run_architecture_check(
            self.project,
            baseline=self.baseline,
            quick_mode=False,
        )

        if not l2_errors:
            return "✅ 架构健康，未检测到问题"

        lines = [
            "=" * 60,
            "  架构健康报告",
            f"  项目: {self.project}",
            f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            "",
        ]

        # 健康评分
        health_score = self._calculate_health_score(l2_errors)
        lines.append(f"📊 健康评分: {health_score}/100")
        lines.append(f"   状态: {'🟢 健康' if health_score >= 80 else '🟡 警告' if health_score >= 60 else '🔴 需关注'}")
        lines.append("")

        # 问题列表
        lines.append("⚠️  检测到以下问题:\n")

        for idx, error in enumerate(l2_errors, 1):
            lines.append(f"{idx}. {error.get('message', '')}")
            suggestion = error.get("suggestion", "")
            if suggestion:
                lines.append(f"   💡 {suggestion}")
            lines.append("")

        # 改进建议
        recommendations = self._generate_recommendations(l2_errors)
        if recommendations:
            lines.append("💡 改进建议:\n")
            for idx, rec in enumerate(recommendations, 1):
                lines.append(f"  {idx}. {rec}")
            lines.append("")

        return "\n".join(lines)

    def _generate_no_issues_markdown(self) -> str:
        """生成无问题的 Markdown 报告"""
        return "\n".join([
            f"# 🏗️  架构健康报告",
            "",
            f"**项目**: `{self.project}`",
            f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## ✅ 架构健康",
            "",
            "未检测到架构问题。继续保持！",
            "",
        ])

    def _format_entropy_markdown(self, errors: list[dict]) -> list[str]:
        """格式化熵增报告"""
        lines = ["## 📊 代码熵增", ""]

        high = [e for e in errors if e.get("type") == "high_entropy"]
        medium = [e for e in errors if e.get("type") == "medium_entropy"]

        if high:
            lines.append("### 🔴 高熵增（>100%）")
            lines.append("")
            for error in high:
                lines.append(f"- **{error.get('file', '?')}**: {error.get('message', '')}")
                suggestion = error.get("suggestion", "")
                if suggestion:
                    lines.append(f"  - {suggestion}")
            lines.append("")

        if medium:
            lines.append("### 🟡 中熵增（>50%）")
            lines.append("")
            for error in medium:
                lines.append(f"- **{error.get('file', '?')}**: {error.get('message', '')}")
                suggestion = error.get("suggestion", "")
                if suggestion:
                    lines.append(f"  - {suggestion}")
            lines.append("")

        return lines

    def _format_hubs_markdown(self, errors: list[dict]) -> list[str]:
        """格式化依赖枢纽报告"""
        lines = ["## 🔗 依赖枢纽", ""]

        hubs = [e for e in errors if e.get("type") == "dependency_hub"]
        for error in hubs[:10]:
            lines.append(f"- **{error.get('file', '?')}**: {error.get('message', '')}")
            suggestion = error.get("suggestion", "")
            if suggestion:
                lines.append(f"  - {suggestion}")

        lines.append("")
        return lines

    def _format_changes_markdown(self, errors: list[dict]) -> list[str]:
        """格式化文件变更报告"""
        lines = ["## 📝 文件内容变更", ""]

        for error in errors[:10]:
            lines.append(f"- **{error.get('file', '?')}**: {error.get('message', '')}")

        lines.append("")
        return lines

    def _calculate_health_score(self, errors: list[dict]) -> int:
        """计算架构健康评分（0-100）

        评分规则：
        - 基础分：100
        - 高熵增：-20/个
        - 中熵增：-10/个
        - 依赖枢纽：-5/个
        - 文件变更：-2/个
        - 最低 0 分
        """
        score = 100

        for error in errors:
            error_type = error.get("type", "")
            if "high_entropy" in error_type:
                score -= 20
            elif "medium_entropy" in error_type:
                score -= 10
            elif "hub" in error_type:
                score -= 5
            elif "changed" in error_type:
                score -= 2

        return max(0, score)

    def _generate_recommendations(self, errors: list[dict]) -> list[str]:
        """生成改进建议"""
        recommendations = []

        entropy_count = len([e for e in errors if "entropy" in e.get("type", "")])
        hub_count = len([e for e in errors if "hub" in e.get("type", "")])

        if entropy_count > 0:
            recommendations.append(
                f"检测到 {entropy_count} 个熵增问题，建议对增长过快的文件进行重构，拆分为多个职责清晰的模块"
            )

        if hub_count > 0:
            recommendations.append(
                f"检测到 {hub_count} 个依赖枢纽，建议为核心模块增加单元测试覆盖，并在修改时进行充分测试"
            )

        recommendations.append("定期运行 `moat check --full` 监控架构健康度")
        recommendations.append("使用 `moat baseline diff` 查看详细的基线对比")

        return recommendations


def generate_architecture_report(
    project_root: str = ".",
    format: str = "text",
    copy: bool = False,
) -> str:
    """生成架构健康报告（CLI 入口）

    Args:
        project_root: 项目根目录
        format: 输出格式（text / md / json）
        copy: 是否复制到剪贴板

    Returns:
        报告文本
    """
    root = Path(project_root).resolve()
    generator = ArchitectureReportGenerator(root)
    report = generator.generate(format=format)

    if copy:
        _copy_to_clipboard(report)
        print("✅ 架构报告已复制到剪贴板")

    return report


def _copy_to_clipboard(text: str):
    """复制文本到剪贴板"""
    try:
        import subprocess
        process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        process.communicate(text.encode('utf-8'))
    except Exception:
        try:
            import pyperclip
            pyperclip.copy(text)
        except ImportError:
            print("⚠️  无法复制到剪贴板，请手动复制")
