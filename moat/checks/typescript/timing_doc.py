"""TypeScript 时序文档检查

检查关键函数是否有时序注释或时序图文档。
"""
import re
from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult


class TypeScriptTimingDocCheck(Check):
    """TypeScript 时序文档检查

    检查项:
    - handleStop / line_complete / assistant_complete 必须有时序注释
    - 时序图文档必须存在（可选）
    """

    # 关键函数
    CRITICAL_FUNCTIONS = [
        "handleStop",
        "handleSubmit",
        "handleLineComplete",
        "handleAssistantComplete",
    ]

    # 时序注释关键词
    TIMING_KEYWORDS = [
        "时序", "timing", "流程", "flow", "顺序", "sequence",
        "触发", "trigger", "中断", "interrupt", "完成", "complete",
        "竞态", "race", "防抖", "throttle", "debouce",
    ]

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        super().__init__(project_root, config)
        self.require_timing_doc = self.config.get("require_timing_doc", False)

    def run(self) -> list[CheckResult]:
        results = []

        ts_files = self._find_ts_files()
        if not ts_files:
            return [self.skip("项目中没有 TypeScript 文件")]

        for file in ts_files:
            try:
                content = file.read_text(encoding="utf-8")
                lines = content.split("\n")

                for func_name in self.CRITICAL_FUNCTIONS:
                    # 查找函数定义
                    pattern = rf"(const|function)\s+{func_name}\s*[=\(]"
                    matches = list(re.finditer(pattern, content))

                    if not matches:
                        continue

                    for match in matches:
                        line_num = content[: match.start()].count("\n") + 1

                        # 检查前 20 行是否有时序注释
                        context_start = max(0, line_num - 21)
                        context = "\n".join(lines[context_start:line_num])

                        has_timing_comment = any(
                            kw.lower() in context.lower() for kw in self.TIMING_KEYWORDS
                        )

                        if not has_timing_comment:
                            results.append(self.warn(
                                f"{func_name} 缺少时序注释\n"
                                f"建议添加注释说明:\n"
                                f"  - 触发时机\n"
                                f"  - 状态转换\n"
                                f"  - 关键时序依赖",
                                file=str(file.relative_to(self.project)),
                                line=line_num,
                            ))

            except Exception as e:
                results.append(self.fail(
                    f"读取文件失败: {e}",
                    file=str(file.relative_to(self.project)),
                ))

        # 可选：检查时序图文档
        if self.require_timing_doc:
            timing_doc = self.project / "docs" / "guides" / "CONVERSATION_TIMING.md"
            if not timing_doc.exists():
                results.append(self.warn(
                    "时序图文档不存在（docs/guides/CONVERSATION_TIMING.md）\n"
                    "建议添加时序图文档，说明关键函数的执行流程",
                ))

        if not results:
            return [self.pass_check("时序文档检查通过")]

        return results

    def _find_ts_files(self) -> list[Path]:
        """查找所有 TypeScript 文件"""
        files = []
        for ext in ["*.ts", "*.tsx"]:
            files.extend(self._find_files(ext))
        return [f for f in files if not self._should_skip(f)]
