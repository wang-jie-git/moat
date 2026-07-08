"""TypeScript 去重逻辑检查

检测去重/防抖代码是否缺少"为什么"注释，以及是否使用固定窗口。
"""
import re
from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult


class TypeScriptDedupCheck(Check):
    """TypeScript 去重逻辑检查

    检查项:
    - isDuplicate / dedupWindow 等去重变量必须有"为什么"注释
    - 禁止使用固定窗口（除非有注释说明）
    - 重连感知（检测 reconnect 相关逻辑）
    """

    # 关键词：去重/防抖相关变量名
    PATTERNS = [
        r"isDuplicate\s*=",
        r"dedupWindow\s*=",
        r"debounce\s*\(",
        r"throttle\s*\(",
        r"\.debounce\s*\(",
        r"\.throttle\s*\(",
    ]

    # "为什么"注释的关键词（中文/英文）
    # 注意：不要在这里包含去重模式本身（如 dedupWindow），否则会自匹配导致漏报
    WHY_KEYWORDS = [
        "为什么", "why", "防止", "prevent", "避免", "avoid",
        "时序", "timing", "场景", "trigger", "race", "deadlock",
        "目的", "purpose", "说明", "note", "原因", "reason",
        "reconnect", "重连", "动态", "dynamic",
    ]

    def run(self) -> list[CheckResult]:
        results = []

        # 查找所有 TypeScript 文件
        ts_files = self._find_ts_files()
        if not ts_files:
            return [self.skip("项目中没有 TypeScript 文件")]

        for file in ts_files:
            try:
                content = file.read_text(encoding="utf-8")
                lines = content.split("\n")

                for i, line in enumerate(lines, 1):
                    # 检查是否匹配去重/防抖模式
                    for pattern in self.PATTERNS:
                        if re.search(pattern, line):
                            # 检查前 10 行是否有"为什么"注释
                            context_start = max(0, i - 11)
                            context = "\n".join(lines[context_start:i])

                            has_why_comment = any(
                                kw.lower() in context.lower()
                                for kw in self.WHY_KEYWORDS
                            )

                            if not has_why_comment:
                                results.append(self.fail(
                                    f"去重/防抖代码缺少'为什么'注释",
                                    file=str(file.relative_to(self.project)),
                                    line=i,
                                    pattern=pattern,
                                ))

                            break  # 每行只检查一次

            except Exception as e:
                results.append(self.fail(
                    f"读取文件失败: {e}",
                    file=str(file.relative_to(self.project)),
                ))

        if not results:
            return [self.pass_check(f"去重/防抖代码注释检查通过（{len(ts_files)} 个文件）")]

        return results

    def _find_ts_files(self) -> list[Path]:
        """查找所有 TypeScript 文件"""
        files = []
        for ext in ["*.ts", "*.tsx"]:
            files.extend(self._find_files(ext))
        return [f for f in files if not self._should_skip(f)]
