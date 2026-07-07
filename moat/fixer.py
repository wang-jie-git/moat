"""Fix Engine — AI 辅助修复引擎

提供基于策略和 AI 的代码修复能力。
支持 dry-run 模式和自动修复简单问题。
"""
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from moat.fix_strategies import get_strategy, get_all_strategies


class FixEngine:
    """修复引擎"""

    def __init__(self, project_root: Path, dry_run: bool = True):
        """初始化修复引擎

        Args:
            project_root: 项目根目录
            dry_run: 是否为演练模式（不实际修改文件）
        """
        self.project = project_root.resolve()
        self.dry_run = dry_run
        self.fixes_applied: list[dict[str, Any]] = []
        self.fixes_skipped: list[dict[str, Any]] = []

    def fix_error(self, error: dict[str, Any]) -> dict[str, Any] | None:
        """修复单个错误

        Args:
            error: 错误字典，包含 type, file, message 等字段

        Returns:
            修复结果字典，如果无法修复则返回 None
        """
        error_type = error.get("type", "unknown")
        message = error.get("message", "")
        file_path = error.get("file", "")

        # 1. 查找修复策略
        strategy = get_strategy(error_type, message)
        if not strategy:
            return None

        # 2. 构建修复结果
        result = {
            "error": error,
            "strategy": {
                "type": strategy.error_type,
                "suggestion": strategy.suggestion,
                "example": strategy.example,
                "confidence": strategy.confidence,
            },
            "auto_fixable": strategy.auto_fixable,
            "status": "pending",
        }

        # 3. 如果支持自动修复且不是演练模式
        if strategy.auto_fixable and not self.dry_run:
            try:
                success = self._apply_auto_fix(error, strategy)
                result["status"] = "fixed" if success else "failed"
                if success:
                    self.fixes_applied.append(result)
                else:
                    self.fixes_skipped.append(result)
            except Exception as e:
                result["status"] = "error"
                result["error_message"] = str(e)
                self.fixes_skipped.append(result)
        else:
            # 仅生成建议
            result["status"] = "suggested"
            self.fixes_skipped.append(result)

        return result

    def _apply_auto_fix(self, error: dict[str, Any], strategy: Any) -> bool:
        """应用自动修复

        Args:
            error: 错误信息
            strategy: 修复策略

        Returns:
            是否修复成功
        """
        file_path = self.project / error.get("file", "")
        if not file_path.exists():
            return False

        # 这里可以根据不同的错误类型实现具体的修复逻辑
        # 目前返回 False，表示需要手动修复
        return False

    def fix_errors(self, errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """批量修复错误

        Args:
            errors: 错误列表

        Returns:
            修复结果列表
        """
        results = []
        for error in errors:
            result = self.fix_error(error)
            if result:
                results.append(result)
        return results

    def generate_ai_suggestions(self, errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """为每个错误生成 AI 修复建议

        基于策略库和错误上下文生成详细的修复建议。
        未来可以接入 LLM 生成更智能的建议。

        Args:
            errors: 错误列表

        Returns:
            AI 建议列表
        """
        suggestions = []

        for error in errors:
            strategy = get_strategy(error.get("type", ""), error.get("message", ""))

            if not strategy:
                continue

            suggestion = {
                "error": error,
                "strategy_type": strategy.error_type,
                "suggestion": strategy.suggestion,
                "example": strategy.example,
                "confidence": strategy.confidence,
                "auto_fixable": strategy.auto_fixable,
                "file": error.get("file", ""),
                "line": error.get("line"),
                "message": error.get("message", ""),
            }

            # 添加 Pain Score 上下文
            if "pain_score" in error:
                suggestion["pain_score"] = error["pain_score"]
                suggestion["pain_level"] = error["pain_level"]

            suggestions.append(suggestion)

        return suggestions

    def generate_fix_pr_description(self, results: list[dict[str, Any]]) -> str:
        """生成修复 PR 描述

        Args:
            results: 修复结果列表

        Returns:
            PR 描述文本
        """
        if not results:
            return "## 修复说明\n\n未发现需要修复的问题。"

        lines = [
            "## 修复说明",
            "",
            f"本次修复共处理 {len(results)} 个问题：",
            "",
        ]

        for i, result in enumerate(results, 1):
            error = result.get("error", {})
            strategy = result.get("strategy", {})
            status = result.get("status", "unknown")

            lines.extend([
                f"### {i}. [{status.upper()}] {error.get('type', 'unknown')}",
                "",
                f"- **文件**: `{error.get('file', 'unknown')}`",
                f"- **问题**: {error.get('message', 'unknown')}",
                f"- **策略**: {strategy.get('type', 'unknown')}",
                f"- **建议**: {strategy.get('suggestion', 'unknown')}",
                "",
            ])

            if result.get("auto_fixable"):
                lines.append("✅ **已自动修复**")
            else:
                lines.append("⚠️ **需要手动修复**")

            lines.append("")

        # 添加下一步建议
        lines.extend([
            "## 下一步",
            "",
            "1. 运行 `moat check` 验证修复",
            "2. 运行 `moat report` 生成完整报告",
            "3. 提交代码",
            "",
        ])

        return "\n".join(lines)

    def get_statistics(self) -> dict[str, Any]:
        """获取修复统计

        Returns:
            统计信息
        """
        return {
            "dry_run": self.dry_run,
            "total_processed": len(self.fixes_applied) + len(self.fixes_skipped),
            "auto_fixed": len(self.fixes_applied),
            "suggested": len(self.fixes_skipped),
            "fixes_applied": self.fixes_applied,
            "fixes_skipped": self.fixes_skipped,
        }


def generate_fix_report(
    project_root: str,
    errors: list[dict[str, Any]] | None = None,
    dry_run: bool = True,
    format: str = "text",
) -> str:
    """生成修复报告（便捷函数）

    Args:
        project_root: 项目根目录
        errors: 错误列表（如果为 None 则从 runner 获取）
        dry_run: 是否为演练模式
        format: 输出格式（text / md / json）

    Returns:
        格式化后的报告
    """

    root = Path(project_root)

    # 如果没有提供错误列表，则运行检查并获取结果
    if errors is None:
        from moat.runner import run_all_checks, MoatResult

        print("\n🔍 运行检查以获取错误列表...")
        # 运行检查并获取完整结果
        result = run_all_checks(project_root)

        # 使用检查结果中的错误列表
        if isinstance(result, MoatResult):
            errors = result.errors
        else:
            # 如果返回的是布尔值（旧版本兼容），返回提示
            return "错误：无法获取错误列表，请使用 `moat report --format json > errors.json` 然后 `moat fix --errors errors.json`"

        if not errors:
            return "✅ 未发现错误，无需修复"

    # 创建修复引擎
    engine = FixEngine(root, dry_run=dry_run)

    # 生成 AI 建议
    suggestions = engine.generate_ai_suggestions(errors)

    # 生成报告
    if format == "json":
        return json.dumps(
            {
                "project": str(root),
                "dry_run": dry_run,
                "total_errors": len(errors),
                "fixable_errors": len(suggestions),
                "suggestions": suggestions,
                "statistics": engine.get_statistics(),
            },
            indent=2,
            ensure_ascii=False,
        )
    elif format == "md":
        return _generate_markdown_report(engine, suggestions)
    else:
        return _generate_text_report(engine, suggestions)


def _generate_text_report(engine: FixEngine, suggestions: list[dict[str, Any]]) -> str:
    """生成纯文本修复报告"""
    lines = [
        "=" * 60,
        "  Moat AI 修复建议",
        f"  项目: {engine.project}",
        f"  模式: {'演练' if engine.dry_run else '实际修复'}",
        "=" * 60,
        "",
        f"📊 扫描到 {len(suggestions)} 个可修复的问题",
        "",
    ]

    if engine.dry_run:
        lines.append("⚠️  演练模式：不会实际修改文件，仅生成建议")
        lines.append("")

    for i, suggestion in enumerate(suggestions, 1):
        error = suggestion.get("error", {})
        strategy = suggestion.get("strategy_type", "unknown")
        confidence = suggestion.get("confidence", 0)

        lines.extend([
            f"[{i}] {error.get('type', 'unknown')}",
            f"    文件: {error.get('file', 'unknown')}:{error.get('line', '?')}",
            f"    问题: {error.get('message', 'unknown')}",
            f"    策略: {strategy}",
            f"    置信度: {confidence * 100:.0f}%",
            f"    建议: {suggestion.get('suggestion', 'unknown')}",
            "",
        ])

        if suggestion.get("auto_fixable") and not engine.dry_run:
            lines.append("    ✅ 已自动修复")
        elif suggestion.get("auto_fixable"):
            lines.append("    ⚙️  支持自动修复（使用 --no-dry-run 启用）")
        else:
            lines.append("    ⚠️  需要手动修复")

        lines.append("")

    lines.extend([
        "=" * 60,
        "💡 使用建议:",
        "   1. 查看每个建议的示例代码",
        "   2. 应用建议修改",
        "   3. 运行 `moat check` 验证",
        "   4. 运行 `moat report` 生成报告",
        "=" * 60,
    ])

    return "\n".join(lines)


def _generate_markdown_report(engine: FixEngine, suggestions: list[dict[str, Any]]) -> str:
    """生成 Markdown 修复报告"""
    lines = [
        "# Moat AI 修复建议",
        "",
        f"**项目**: `{engine.project}`",
        f"**模式**: {'演练（Dry Run）' if engine.dry_run else '实际修复'}",
        "",
        f"## 概览",
        "",
        f"扫描到 **{len(suggestions)}** 个可修复的问题",
        "",
    ]

    if engine.dry_run:
        lines.extend([
            "⚠️ **演练模式**：不会实际修改文件，仅生成建议",
            "",
        ])

    for i, suggestion in enumerate(suggestions, 1):
        error = suggestion.get("error", {})
        strategy = suggestion.get("strategy_type", "unknown")
        confidence = suggestion.get("confidence", 0)

        lines.extend([
            f"## {i}. {error.get('type', 'unknown')}",
            "",
            f"- **文件**: `{error.get('file', 'unknown')}`:{error.get('line', '?')}",
            f"- **问题**: {error.get('message', 'unknown')}",
            f"- **策略**: {strategy}",
            f"- **置信度**: {confidence * 100:.0f}%",
            "",
            f"### 💡 建议",
            "",
            suggestion.get("suggestion", "unknown"),
            "",
        ])

        if suggestion.get("example"):
            lines.extend([
                "### 📝 示例",
                "",
                "```",
                suggestion["example"],
                "```",
                "",
            ])

        if suggestion.get("auto_fixable") and not engine.dry_run:
            lines.append("✅ **已自动修复**")
        elif suggestion.get("auto_fixable"):
            lines.append("⚙️ **支持自动修复**（使用 `--no-dry-run` 启用）")
        else:
            lines.append("⚠️ **需要手动修复**")

        lines.append("")

    lines.extend([
        "---",
        "",
        "## 下一步",
        "",
        "1. 查看每个建议的示例代码",
        "2. 应用建议修改",
        "3. 运行 `moat check` 验证",
        "4. 运行 `moat report` 生成报告",
        "",
    ])

    return "\n".join(lines)
