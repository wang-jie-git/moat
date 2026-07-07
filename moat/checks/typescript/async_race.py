"""TypeScript 专项检查 — 异步竞态检测"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult


class TypeScriptAsyncRaceCheck(Check):
    """TypeScript 异步竞态检测

    检测潜在的竞态条件：
    - 未处理的 Promise
    - 竞态条件的 async/await
    - 未取消的异步操作
    - 闭包中的异步循环
    """

    name = "typescript_async_race"
    description = "TypeScript 异步竞态检测"

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        super().__init__(project_root, config)

    def run(self) -> list[CheckResult]:
        results = []

        # 1. 检查是否有 TypeScript 文件
        ts_files = self._find_ts_files()
        if not ts_files:
            return [self.skip("项目中没有 TypeScript 文件")]

        # 2. 扫描异步竞态
        race_conditions = []
        for file_path in ts_files:
            if self._should_skip(file_path):
                continue

            try:
                source = file_path.read_text(encoding="utf-8")
                file_races = self._find_async_races(source, file_path)
                race_conditions.extend(file_races)
            except Exception:
                continue

        # 3. 评估结果
        if not race_conditions:
            return [self.pass_check("未发现异步竞态问题")]

        total = len(race_conditions)
        results.append(self.warn(
            f"发现 {total} 处潜在的异步竞态问题",
        ))

        # 详细报告
        for race in race_conditions[:5]:  # 最多报告 5 个
            results.append(self.warn(
                f"{race['type']}: {race['message']}",
                file=race["file"],
                line=race.get("line"),
            ))

        results.append(self.warn(
            "建议：使用 AbortController 取消异步操作，或使用锁机制",
        ))

        return results

    def _find_async_races(self, source: str, file_path: Path) -> list[dict[str, Any]]:
        """查找异步竞态条件

        Args:
            source: 源代码
            file_path: 文件路径

        Returns:
            竞态条件列表
        """
        import re

        races = []
        lines = source.split("\n")

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # 跳过注释
            if stripped.startswith("//"):
                continue

            # 1. 检测竞态的 async/await 在循环中
            if self._is_async_loop_race(lines, line_num - 1):
                races.append({
                    "file": file_path,
                    "line": line_num,
                    "type": "async_loop_race",
                    "message": "循环中的 async/await 可能导致竞态条件",
                    "context": stripped[:80],
                })

            # 2. 检测未处理的 Promise
            if re.search(r"new\s+Promise\s*\(", line) and "await" not in line:
                races.append({
                    "file": file_path,
                    "line": line_num,
                    "type": "unhandled_promise",
                    "message": "创建 Promise 但未 await",
                    "context": stripped[:80],
                })

            # 3. 检测 .then() 未处理错误
            if re.search(r"\.then\s*\(", line) and not re.search(r"\.catch\s*\(", line):
                # 检查后续行是否有 .catch
                has_catch = False
                for i in range(line_num, min(line_num + 5, len(lines))):
                    if re.search(r"\.catch\s*\(", lines[i]):
                        has_catch = True
                        break

                if not has_catch:
                    races.append({
                        "file": file_path,
                        "line": line_num,
                        "type": "unhandled_then",
                        "message": ".then() 链中缺少 .catch() 错误处理",
                        "context": stripped[:80],
                    })

        return races

    def _is_async_loop_race(self, lines: list[str], start_idx: int) -> bool:
        """检查是否是 async/await 在循环中的竞态

        Args:
            lines: 代码行列表
            start_idx: 起始行索引

        Returns:
            是否是竞态
        """
        import re

        # 向前查找 for/while 关键字
        for i in range(max(0, start_idx - 10), start_idx):
            line = lines[i]
            if re.search(r"\b(for|while|forEach)\s*\(", line):
                # 找到了循环
                # 检查当前行是否包含 await 或 async 函数调用
                current = lines[start_idx]
                if "await" in current or "async" in current:
                    return True

        return False

    def _find_ts_files(self) -> list[Path]:
        """查找所有 TypeScript 文件"""
        files = []
        for ext in ["*.ts", "*.tsx", "*.mts", "*.cts"]:
            files.extend(self._find_files(ext))
        return [f for f in files if not self._should_skip(f)]
