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

    def _generate_json(self) -> str:
        """生成 JSON 报告"""
        from datetime import datetime

        # 计算 Pain Score
        from moat.pain.scorer import calculate_total_pain

        core_areas_config = self._get_core_areas_config()
        pain_result = calculate_total_pain(self.result.errors, core_areas_config)

        # 加载架构意图
        architecture_intent = self._load_architecture_intent()

        # 生成结构化报告
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "project": str(self.project),
            "project_types": {k: v for k, v in self.project_types.items() if v},
            "architecture_intent": architecture_intent,
            "summary": {
                "total_checks": self.result.total_checks,
                "passed": self.result.passed,
                "failed": self.result.failed,
                "warnings": self.result.warnings,
                "skipped": self.result.skipped,
                "duration": round(self.result.duration, 2),
            },
            "pain_score": {
                "total": pain_result["total_score"],
                "level": pain_result["overall_level"],
                "error_count": pain_result["error_count"],
                "recommended_action": pain_result["recommended_action"],
            },
            "errors": [
                {
                    "type": error.get("type", "unknown"),
                    "file": error.get("file", ""),
                    "line": error.get("line"),
                    "message": error.get("message", ""),
                    "level": error.get("level", "ERROR"),
                    "pain_score": score["score"],
                    "pain_level": score["level"],
                    "impact": self._analyze_impact(error),
                    "ai_suggestion": self._get_ai_suggestion(error),
                }
                for error, score in zip(self.result.errors, pain_result["scores"])
            ],
            "actions": {
                "view_details": f"moat check --project {self.project} --verbose",
                "baseline_diff": f"moat baseline diff --project {self.project}",
                "save_baseline": f"moat baseline save --project {self.project}",
                "generate_report": f"moat report --copy --project {self.project}",
            },
        }

        return json.dumps(report_data, indent=2, ensure_ascii=False)

    def _get_core_areas_config(self) -> list[dict] | None:
        """获取核心业务区域配置"""
        config_path = self.project / ".moat" / "config.json"
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                return config.get("core_areas")
            except Exception:
                pass
        return None

    def _load_architecture_intent(self) -> dict[str, Any]:
        """加载架构意图"""
        intent_file = self.project / ".moat" / "architecture_intent.md"
        if intent_file.exists():
            try:
                content = intent_file.read_text(encoding="utf-8")
                return {
                    "present": True,
                    "path": str(intent_file.relative_to(self.project)),
                    "content": content[:2000] + "..." if len(content) > 2000 else content,
                }
            except Exception:
                pass
        return {"present": False}

    def _generate_text(self) -> str:
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

        # 🆕 新增：技术债务报告
        tech_debt_section = self._generate_tech_debt_section()
        if tech_debt_section:
            lines.append(tech_debt_section)

        # 🆕 新增：L2 架构健康报告
        arch_section = self._generate_architecture_section()
        if arch_section:
            lines.append(arch_section)

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

        # 🆕 新增：技术债务报告
        tech_debt_section = self._generate_tech_debt_section_md()
        if tech_debt_section:
            lines.append(tech_debt_section)

        # 🆕 新增：L2 架构健康报告
        arch_section = self._generate_architecture_section()
        if arch_section:
            lines.append(arch_section)

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

        # 显示 L2 修复建议
        suggestion = error.get("suggestion", "")
        if suggestion:
            lines.extend([
                "",
                f"**💡 修复建议**: {suggestion}",
            ])

        # 影响分析
        impact = self._analyze_impact(error)
        if impact:
            lines.extend([
                "",
                f"**🎯 影响分析**: {impact}",
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

    def _generate_architecture_section(self) -> str | None:
        """生成 L2 架构健康报告章节

        从检查结果中提取 L2 架构相关问题并格式化输出

        Returns:
            格式化后的架构健康章节文本，如果没有 L2 问题则返回 None
        """
        # 筛选 L2 架构相关问题
        arch_errors = [
            e for e in self.result.errors
            if e.get("level") == "L2"
        ]

        if not arch_errors:
            return None

        lines = [
            "",
            "=" * 60,
            "  🏗️  L2 架构健康报告",
            "=" * 60,
            "",
        ]

        # 直接输出所有 L2 错误（简化版本）
        lines.append("⚠️  检测到以下架构问题：\n")

        for error in arch_errors:
            lines.append(f"  {error.get('message', '')}")
            suggestion = error.get("suggestion", "")
            if suggestion:
                lines.append(f"    💡 {suggestion}")

        lines.append("")

        # 架构建议
        lines.extend([
            "💡 架构维护建议：",
            "  • 定期运行 `moat check --full` 监控架构健康度",
            "  • 使用 `moat baseline diff` 查看详细的基线对比",
            "  • 对于熵增过快的文件，考虑拆分为多个职责清晰的模块",
            "  • 依赖枢纽模块修改前，确保有充分的单元测试覆盖",
            "",
        ])

        return "\n".join(lines)

    def _categorize_optimization_error(self, message: str) -> str:
        """将优化检查错误分类为技术债务类型"""
        if "[YAGNI-" in message:
            return "code_simplification"
        elif "[COMPLEX-" in message:
            return "complexity"
        elif "[STDLIB-" in message or "[TS-" in message:
            return "standard_library"
        else:
            return "other"

    def _generate_tech_debt_section(self) -> str | None:
        """生成技术债务报告（纯文本格式）

        从错误列表中提取优化检查结果，按技术债务分类展示
        """
        # 筛选优化检查错误
        opt_errors = [
            e for e in self.result.errors
            if any(keyword in e.get("message", "")
                   for keyword in ["[YAGNI-", "[COMPLEX-", "[STDLIB-", "[TS-"])
        ]

        if not opt_errors:
            return None

        # 按类别分组
        categories = {
            "code_simplification": [],
            "complexity": [],
            "standard_library": [],
            "other": [],
        }

        for error in opt_errors:
            category = self._categorize_optimization_error(error.get("message", ""))
            categories[category].append(error)

        # 生成报告
        lines = [
            "",
            "=" * 60,
            "  📦 技术债务报告",
            "=" * 60,
            "",
        ]

        category_names = {
            "code_simplification": "代码精简空间 (YAGNI)",
            "complexity": "复杂度债务",
            "standard_library": "标准库优化",
            "other": "其他优化建议",
        }

        for category, errors in categories.items():
            if errors:
                lines.append(f"{category_names[category]} - {len(errors)} 个")
                for error in errors:
                    file_info = error.get('file', '?')
                    line_info = f":{error['line']}" if error.get('line') else ""
                    message = error.get('message', '')
                    lines.append(f"  • {file_info}{line_info} - {message}")
                lines.append("")

        # 添加优化建议
        lines.extend([
            "💡 优化建议:",
            "  • 优先处理复杂度债务（COMPLEX-*），提高代码可维护性",
            "  • 定期清理 YAGNI 问题（YAGNI-*），保持代码精简",
            "  • 考虑标准库替代方案（STDLIB-*），减少依赖",
            "  • 运行 moat check --full --optimize 查看完整优化检查",
            "",
        ])

        return "\n".join(lines)

    def _generate_tech_debt_section_md(self) -> str | None:
        """生成技术债务报告（Markdown 格式）"""
        # 筛选优化检查错误
        opt_errors = [
            e for e in self.result.errors
            if any(keyword in e.get("message", "")
                   for keyword in ["[YAGNI-", "[COMPLEX-", "[STDLIB-", "[TS-"])
        ]

        if not opt_errors:
            return None

        # 按类别分组
        categories = {
            "code_simplification": [],
            "complexity": [],
            "standard_library": [],
            "other": [],
        }

        for error in opt_errors:
            category = self._categorize_optimization_error(error.get("message", ""))
            categories[category].append(error)

        # 生成报告
        lines = [
            "## 📦 技术债务报告",
            "",
        ]

        category_icons = {
            "code_simplification": "📦",
            "complexity": "🔢",
            "standard_library": "📚",
            "other": "💡",
        }

        category_names = {
            "code_simplification": "代码精简空间 (YAGNI)",
            "complexity": "复杂度债务",
            "standard_library": "标准库优化",
            "other": "其他优化建议",
        }

        for category, errors in categories.items():
            if errors:
                lines.append(f"### {category_icons[category]} {category_names[category]} ({len(errors)} 个)")
                lines.append("")
                for error in errors:
                    file_info = error.get('file', '?')
                    line_info = f":{error['line']}" if error.get('line') else ""
                    message = error.get('message', '')
                    lines.append(f"- {file_info}{line_info} - {message}")
                lines.append("")

        # 添加优化建议
        lines.extend([
            "💡 **优化建议**:",
            "",
            "- 优先处理复杂度债务（COMPLEX-*），提高代码可维护性",
            "- 定期清理 YAGNI 问题（YAGNI-*），保持代码精简",
            "- 考虑标准库替代方案（STDLIB-*），减少依赖",
            "- 运行 `moat check --full --optimize` 查看完整优化检查",
            "",
        ])

        return "\n".join(lines)


def generate_report(project_root: str = ".", result: MoatResult | None = None,
                    format: str = "text", copy: bool = False) -> str:
    """生成报告（CLI 入口）

    Args:
        project_root: 项目根目录
        result: MoatResult 对象（如果为 None，则重新运行检查）
        format: 输出格式（text / md / json）
        copy: 是否复制到剪贴板

    Returns:
        报告文本
    """
    root = Path(project_root).resolve()

    # 如果没有提供结果，运行检查
    if result is None:
        from moat.runner import run_all_checks
        success = run_all_checks(str(root))
        # 注意：这里应该捕获结果，暂时简化处理
        result = MoatResult()

    generator = ReportGenerator(root, result)

    if format == "json":
        report = generator._generate_json()
    elif format == "md":
        report = generator.generate(format="md")
    else:
        report = generator.generate(format="text")

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
