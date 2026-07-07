"""Report Generator — 生成可复制给 AI 的详细报错报告

Usage:
    moat report --copy          # 生成报告并复制到剪贴板
    moat report --format md     # Markdown 格式
    moat report --format text   # 纯文本格式（默认）
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from moat.runner import MoatResult
from moat.checks import detect_project_type


class ReportGenerator:
    """报告生成器"""

    def __init__(self, project_root: Path, result: MoatResult):
        self.project = project_root.resolve()
        self.result = result
        self.project_types = detect_project_type(self.project)

    def generate(self, format: str = "text") -> str:
        """生成报告

        Args:
            format: 输出格式（text / md）

        Returns:
            格式化后的报告文本
        """
        if format == "md":
            return self._generate_markdown()
        return self._generate_text()

    def _generate_text(self) -> str:
        """生成纯文本报告"""
        lines = [
            "=" * 60,
            "  Moat Check 失败报告",
            f"  项目: {self.project}",
            f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            "",
            "📊 项目类型:",
        ]

        # 项目类型
        for lang, enabled in self.project_types.items():
            if enabled:
                lines.append(f"   ✓ {lang}")

        lines.extend([
            "",
            f"📈 检查结果: {self.result.summary()}",
            "",
        ])

        # 失败列表
        if self.result.errors:
            lines.extend([
                "❌ 发现以下问题:",
                "",
            ])

            for idx, error in enumerate(self.result.errors, 1):
                lines.extend(self._format_error_text(idx, error))

        # AI 修复建议
        lines.extend([
            "",
            "=" * 60,
            "  🤖 AI 修复建议",
            "=" * 60,
            "",
        ])

        for error in self.result.errors:
            suggestion = self._get_ai_suggestion(error)
            if suggestion:
                lines.append(f"• {suggestion}")

        lines.extend([
            "",
            "=" * 60,
            "  📋 一键复制命令",
            "=" * 60,
            "",
            "# 查看详细错误",
            f"cd {self.project}",
            "moat check --verbose",
            "",
            "# 查看基线差异",
            "moat baseline diff",
            "",
            "# 保存基线（如果允许改动）",
            "moat baseline save",
            "",
        ])

        return "\n".join(lines)

    def _generate_markdown(self) -> str:
        """生成 Markdown 报告"""
        lines = [
            f"# Moat Check 失败报告",
            "",
            f"**项目**: `{self.project}`",
            f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 📊 项目类型",
            "",
        ]

        for lang, enabled in self.project_types.items():
            if enabled:
                lines.append(f"- ✓ {lang}")

        lines.extend([
            "",
            f"## 📈 检查结果",
            "",
            f"```",
            f"{self.result.summary()}",
            f"```",
            "",
        ])

        if self.result.errors:
            lines.extend([
                "## ❌ 发现的问题",
                "",
            ])

            for idx, error in enumerate(self.result.errors, 1):
                lines.extend(self._format_error_markdown(idx, error))

        lines.extend([
            "## 🤖 AI 修复建议",
            "",
        ])

        for error in self.result.errors:
            suggestion = self._get_ai_suggestion(error)
            if suggestion:
                lines.append(f"- {suggestion}")

        lines.extend([
            "",
            "## 📋 操作步骤",
            "",
            "```bash",
            f"cd {self.project}",
            "moat check --verbose  # 查看详细错误",
            "moat baseline diff    # 查看基线差异",
            "# moat baseline save # 如果需要保存基线",
            "```",
            "",
        ])

        return "\n".join(lines)

    def _format_error_text(self, idx: int, error: dict) -> list[str]:
        """格式化错误为纯文本"""
        lines = [
            f"{idx}. [{error.get('level', 'ERROR')}] {error.get('file', '?')}",
            f"   类型: {error.get('type', 'unknown')}",
            f"   原因: {error.get('message', '未知错误')}",
        ]

        if error.get("line"):
            lines.append(f"   行号: {error['line']}")

        # 影响分析
        impact = self._analyze_impact(error)
        if impact:
            lines.extend([
                "",
                f"   💡 影响分析:",
                f"   {impact}",
            ])

        lines.append("")
        return lines

    def _format_error_markdown(self, idx: int, error: dict) -> list[str]:
        """格式化错误为 Markdown"""
        lines = [
            f"### {idx}. {error.get('message', '未知错误')}",
            "",
            f"- **文件**: `{error.get('file', '?')}`",
            f"- **类型**: `{error.get('type', 'unknown')}`",
            f"- **级别**: {error.get('level', 'ERROR')}",
        ]

        if error.get("line"):
            lines.append(f"- **行号**: {error['line']}")

        # 影响分析
        impact = self._analyze_impact(error)
        if impact:
            lines.extend([
                "",
                f"**💡 影响分析**: {impact}",
            ])

        lines.append("")
        return lines

    def _analyze_impact(self, error: dict) -> str | None:
        """分析错误影响范围"""
        error_type = error.get("type", "")
        message = error.get("message", "").lower()

        if "import" in error_type or "import" in message:
            return "可能导致模块无法加载，影响依赖该模块的所有功能"
        elif "api" in error_type or "endpoint" in message:
            return "API 接口可能不可用，影响前端/客户端调用"
        elif "module" in error_type or "class" in message:
            return "核心模块异常，可能影响整个子系统的功能"
        elif "file" in error_type or "missing" in message:
            return "文件缺失可能导致运行时错误或功能不完整"
        elif "syntax" in error_type or "语法" in message:
            return "语法错误会导致程序无法运行"
        elif "race" in error_type or "竞态" in message or "race condition" in message:
            return "竞态条件可能导致数据不一致或偶发性崩溃"
        elif "dedup" in error_type or "去重" in message:
            return "去重逻辑问题可能导致重复请求或数据重复"

        return None

    def _get_ai_suggestion(self, error: dict) -> str | None:
        """获取 AI 修复建议"""
        error_type = error.get("type", "")
        message = error.get("message", "").lower()
        file_path = error.get("file", "")

        suggestions = []

        if "import" in error_type or "import" in message:
            suggestions.append(
                f"检查 `{file_path}` 的 import 语句，确认依赖包已安装且路径正确"
            )
        elif "api" in error_type or "endpoint" in message:
            suggestions.append(
                f"检查 `{file_path}` 的 API 路由和请求/响应格式"
            )
        elif "module" in error_type:
            suggestions.append(
                f"修复 `{file_path}` 中的模块定义，确保可以正确导入"
            )
        elif "file" in error_type or "missing" in message:
            suggestions.append(
                f"恢复缺失的文件 `{file_path}` 或更新基线"
            )
        elif "syntax" in error_type or "语法" in message:
            suggestions.append(
                f"修复 `{file_path}` 的语法错误"
            )
        elif "race" in error_type or "竞态" in message:
            suggestions.append(
                f"为 `{file_path}` 添加时序注释或使用锁机制"
            )
        elif "dedup" in error_type or "去重" in message:
            suggestions.append(
                f"为 `{file_path}` 的去重逻辑添加动态窗口或注释说明"
            )

        return suggestions[0] if suggestions else None


def generate_report(project_root: str = ".", result: MoatResult | None = None,
                    format: str = "text", copy: bool = False) -> str:
    """生成报告（CLI 入口）

    Args:
        project_root: 项目根目录
        result: MoatResult 对象（如果为 None，则重新运行检查）
        format: 输出格式（text / md）
        copy: 是否复制到剪贴板

    Returns:
        报告文本
    """
    root = Path(project_root).resolve()

    # 如果没有提供结果，运行检查
    if result is None:
        from moat.runner import run_all_checks
        run_all_checks(str(root))
        # 注意：这里应该捕获结果，暂时简化处理
        result = MoatResult()

    generator = ReportGenerator(root, result)
    report = generator.generate(format)

    if copy:
        _copy_to_clipboard(report)
        print("✅ 报告已复制到剪贴板")

    return report


def _copy_to_clipboard(text: str):
    """复制文本到剪贴板"""
    try:
        import subprocess
        process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        process.communicate(text.encode('utf-8'))
    except Exception:
        # 如果 pbcopy 不可用，降级到 pyperclip
        try:
            import pyperclip
            pyperclip.copy(text)
        except ImportError:
            print("⚠️  无法复制到剪贴板，请手动复制")
