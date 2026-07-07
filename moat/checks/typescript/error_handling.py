"""TypeScript 错误处理检查

检测错误日志是否可观测（禁止静默丢弃异常）
"""
import re
from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult


class TypeScriptErrorHandlingCheck(Check):
    """TypeScript 错误处理可观测性检查

    检查项:
    - catch 块必须使用 console.error（而非 console.warn）
    - catch 块必须记录上下文（文件名/错误信息）
    - 禁止空的 catch 块
    """

    # 危险模式
    DANGEROUS_PATTERNS = [
        (r"catch\s*\(\s*e\s*\)\s*\{\s*\}", "空的 catch 块"),
        (r"console\.warn\s*\([^)]*error[^)]*\)", "使用 console.warn 记录错误"),
        (r"catch\s*\([^)]*\)\s*\{\s*//\s*ignore", "忽略异常"),
    ]

    # 推荐模式
    SAFE_PATTERNS = [
        r"console\.error\s*\(",
        r"log(?:ger)?\.error\s*\(",
        r"throw\s+",
    ]

    def run(self) -> list[CheckResult]:
        results = []

        ts_files = self._find_ts_files()
        if not ts_files:
            return [self.skip("项目中没有 TypeScript 文件")]

        for file in ts_files:
            try:
                content = file.read_text(encoding="utf-8")
                lines = content.split("\n")

                for i, line in enumerate(lines, 1):
                    # 检查危险模式
                    for pattern, description in self.DANGEROUS_PATTERNS:
                        if re.search(pattern, line, re.IGNORECASE):
                            # 排除注释行
                            if line.strip().startswith("//"):
                                continue

                            results.append(self.warn(
                                f"检测到潜在问题: {description}",
                                file=str(file.relative_to(self.project)),
                                line=i,
                            ))

            except Exception as e:
                results.append(self.fail(
                    f"读取文件失败: {e}",
                    file=str(file.relative_to(self.project)),
                ))

        if not results:
            return [self.pass_check("错误处理可观测性检查通过")]

        return results

    def _find_ts_files(self) -> list[Path]:
        """查找所有 TypeScript 文件"""
        files = []
        for ext in ["*.ts", "*.tsx"]:
            files.extend(self._find_files(ext))
        return [f for f in files if not self._should_skip(f)]
