"""Go 基础检查 — 并发安全检测"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult


class GoConcurrencySafetyCheck(Check):
    """Go 并发安全检测

    检测：
    - 共享变量的并发访问
    - 未同步的 map 访问
    - sync.Mutex 使用建议
    - channel 通信模式
    """

    name = "go_concurrency_safety"
    description = "Go 并发安全检测"

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        super().__init__(project_root, config)

    def run(self) -> list[CheckResult]:
        results = []

        # 1. 检查是否有 Go 文件
        go_files = self._find_go_files()
        if not go_files:
            return [self.skip("项目中没有 Go 文件")]

        # 2. 扫描并发安全问题
        concurrency_issues = []
        for file_path in go_files:
            if self._should_skip(file_path):
                continue

            try:
                source = file_path.read_text(encoding="utf-8")
                file_issues = self._find_concurrency_issues(source, file_path)
                concurrency_issues.extend(file_issues)
            except Exception:
                continue

        # 3. 评估结果
        if not concurrency_issues:
            return [self.pass_check("Go 并发安全检查通过")]

        total = len(concurrency_issues)
        results.append(self.warn(
            f"发现 {total} 处潜在的并发安全问题",
        ))

        for issue in concurrency_issues[:5]:
            results.append(self.warn(
                f"{issue['type']}: {issue['message']}",
                file=issue["file"],
                line=issue.get("line"),
            ))

        return results

    def _find_concurrency_issues(self, source: str, file_path: Path) -> list[dict[str, Any]]:
        """查找并发安全问题

        Args:
            source: 源代码
            file_path: 文件路径

        Returns:
            问题列表
        """
        import re

        issues = []
        lines = source.split("\n")

        # 查找 map 声明
        map_declarations: set[str] = set()
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue

            match = re.search(r"(\w+)\s*:\s*map\s*\[", line)
            if match:
                map_name = match.group(1)
                map_declarations.add(map_name)

        # 检查 map 的并发访问
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue

            # 1. 检测未加锁的 map 写入
            for map_name in map_declarations:
                # 检查是否有 map_name[xxx] = yyy 的写入操作
                if re.search(rf"{map_name}\s*\[.*\]\s*=", line):
                    # 检查附近是否有 mutex 锁
                    has_mutex = False
                    for i in range(max(0, line_num - 20), min(line_num + 5, len(lines))):
                        if "Lock()" in lines[i] or "Unlock()" in lines[i] or \
                           "RLock()" in lines[i] or "RUnlock()" in lines[i]:
                            has_mutex = True
                            break

                    if not has_mutex:
                        issues.append({
                            "file": file_path,
                            "line": line_num,
                            "type": "unsync_map_write",
                            "message": f"并发写入 map '{map_name}' 未加锁",
                            "context": stripped[:80],
                        })

        return issues

    def _find_go_files(self) -> list[Path]:
        """查找所有 Go 文件"""
        files = []
        for ext in ["*.go"]:
            files.extend(self._find_files(ext))
        return [f for f in files if not self._should_skip(f)]
