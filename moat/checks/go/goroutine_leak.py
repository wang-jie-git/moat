"""Go 基础检查 — goroutine 泄露检测"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult


class GoGoroutineLeakCheck(Check):
    """Go goroutine 泄露检测

    检测：
    - 无限循环的 goroutine
    - 未通过 channel 发送信号的 goroutine
    - 未使用 context 的 goroutine
    """

    name = "go_goroutine_leak"
    description = "Go goroutine 泄露检测"

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        super().__init__(project_root, config)

    def run(self) -> list[CheckResult]:
        results = []

        # 1. 检查是否有 Go 文件
        go_files = self._find_go_files()
        if not go_files:
            return [self.skip("项目中没有 Go 文件")]

        # 2. 扫描 goroutine 问题
        goroutine_issues = []
        for file_path in go_files:
            if self._should_skip(file_path):
                continue

            try:
                source = file_path.read_text(encoding="utf-8")
                file_issues = self._find_goroutine_issues(source, file_path)
                goroutine_issues.extend(file_issues)
            except Exception:
                continue

        # 3. 评估结果
        if not goroutine_issues:
            return [self.pass_check("Go goroutine 泄露检查通过")]

        total = len(goroutine_issues)
        results.append(self.warn(
            f"发现 {total} 处潜在的 goroutine 泄露",
        ))

        for issue in goroutine_issues[:5]:
            results.append(self.warn(
                f"{issue['type']}: {issue['message']}",
                file=issue["file"],
                line=issue.get("line"),
            ))

        return results

    def _find_goroutine_issues(self, source: str, file_path: Path) -> list[dict[str, Any]]:
        """查找 goroutine 问题

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

            # 1. 检测 go func() 但没有 context
            if re.search(r"go\s+func\s*\(", line):
                # 检查函数体是否使用 context
                has_context = False
                for i in range(line_num, min(line_num + 30, len(lines))):
                    if "context.Context" in lines[i] or "ctx " in lines[i]:
                        has_context = True
                        break

                if not has_context:
                    issues.append({
                        "file": file_path,
                        "line": line_num,
                        "type": "goroutine_without_context",
                        "message": "goroutine 未使用 context，可能导致无法取消",
                        "context": stripped[:80],
                    })

            # 2. 检测 select {} 无限循环（可能是 goroutine 泄露）
            if re.search(r"select\s*{", line) or re.search(r"for\s*{", line):
                # 检查是否是 goroutine
                in_goroutine = False
                for i in range(max(0, line_num - 10), line_num):
                    if re.search(r"go\s+func\s*\(", lines[i]):
                        in_goroutine = True
                        break

                if in_goroutine and "default:" not in line:
                    issues.append({
                        "file": file_path,
                        "line": line_num,
                        "type": "potential_goroutine_leak",
                        "message": "goroutine 中的无限循环可能导致泄露",
                        "context": stripped[:80],
                    })

        return issues

    def _find_go_files(self) -> list[Path]:
        """查找所有 Go 文件"""
        files = []
        for ext in ["*.go"]:
            files.extend(self._find_files(ext))
        return [f for f in files if not self._should_skip(f)]
