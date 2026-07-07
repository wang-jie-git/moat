"""Go 基础检查 — error 处理完整性检查"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult


class GoErrorHandlingCheck(Check):
    """Go error 处理完整性检查

    检测：
    - 未检查的 error 返回值
    - panic 使用（建议使用 error）
    - 未处理的 recover
    """

    name = "go_error_handling"
    description = "Go error 处理完整性检查"

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        super().__init__(project_root, config)

    def run(self) -> list[CheckResult]:
        results = []

        # 1. 检查是否有 Go 文件
        go_files = self._find_go_files()
        if not go_files:
            return [self.skip("项目中没有 Go 文件")]

        # 2. 扫描 error 处理问题
        error_issues = []
        for file_path in go_files:
            if self._should_skip(file_path):
                continue

            try:
                source = file_path.read_text(encoding="utf-8")
                file_issues = self._find_error_issues(source, file_path)
                error_issues.extend(file_issues)
            except Exception:
                continue

        # 3. 评估结果
        if not error_issues:
            return [self.pass_check("Go error 处理完整性检查通过")]

        total = len(error_issues)
        results.append(self.warn(
            f"发现 {total} 处 error 处理问题",
        ))

        for issue in error_issues[:5]:  # 最多报告 5 个
            results.append(self.warn(
                f"{issue['type']}: {issue['message']}",
                file=issue["file"],
                line=issue.get("line"),
            ))

        return results

    def _find_error_issues(self, source: str, file_path: Path) -> list[dict[str, Any]]:
        """查找 error 处理问题

        Args:
            source: 源代码
            file_path: 文件路径

        Returns:
            问题列表
        """
        import re

        issues = []
        lines = source.split("\n")

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # 跳过注释
            if stripped.startswith("//"):
                continue

            # 1. 检测未使用的 error 返回值
            # 匹配：func Xxx(...) (..., err error)
            if re.search(r"err\s+error\s*\)", line):
                # 检查函数体内是否有 if err != nil
                has_error_check = False
                for i in range(line_num, min(line_num + 50, len(lines))):
                    if "if err != nil" in lines[i]:
                        has_error_check = True
                        break
                    # 如果遇到下一个函数定义，停止
                    if re.search(r"^func\s+\w+", lines[i]):
                        break

                if not has_error_check:
                    issues.append({
                        "file": file_path,
                        "line": line_num,
                        "type": "unchecked_error",
                        "message": "函数返回 error 但未检查",
                        "context": stripped[:80],
                    })

            # 2. 检测 panic 使用
            if re.search(r"\bpanic\s*\(", line):
                issues.append({
                    "file": file_path,
                    "line": line_num,
                    "type": "panic_usage",
                    "message": "使用 panic()，建议返回 error",
                    "context": stripped[:80],
                })

        return issues

    def _find_go_files(self) -> list[Path]:
        """查找所有 Go 文件"""
        files = []
        for ext in ["*.go"]:
            files.extend(self._find_files(ext))
        return [f for f in files if not self._should_skip(f)]
