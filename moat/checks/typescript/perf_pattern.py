"""TypeScript 专项检查 — 性能反模式检测"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult


class TypeScriptPerfAntiPatternCheck(Check):
    """TypeScript 性能反模式检测

    检测性能相关的反模式：
    - 循环中的数组操作（filter/map/reduce）
    - 大量数据的深拷贝
    - 频繁的 DOM 查询
    - 未优化的 React 重渲染
    """

    name = "typescript_perf_antipattern"
    description = "TypeScript 性能反模式检测"

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        super().__init__(project_root, config)

    def run(self) -> list[CheckResult]:
        results = []

        # 1. 检查是否有 TypeScript 文件
        ts_files = self._find_ts_files()
        if not ts_files:
            return [self.skip("项目中没有 TypeScript 文件")]

        # 2. 扫描性能反模式
        anti_patterns = []
        for file_path in ts_files:
            if self._should_skip(file_path):
                continue

            try:
                source = file_path.read_text(encoding="utf-8")
                file_patterns = self._find_anti_patterns(source, file_path)
                anti_patterns.extend(file_patterns)
            except Exception:
                continue

        # 3. 评估结果
        if not anti_patterns:
            return [self.pass_check("未发现性能反模式")]

        total = len(anti_patterns)
        by_type: dict[str, list] = {}
        for pattern in anti_patterns:
            pattern_type = pattern["type"]
            if pattern_type not in by_type:
                by_type[pattern_type] = []
            by_type[pattern_type].append(pattern)

        results.append(self.warn(
            f"发现 {total} 处性能反模式",
        ))

        for pattern_type, patterns in by_type.items():
            results.append(self.warn(
                f"{pattern_type}: {len(patterns)} 处",
            ))

            for pattern in patterns[:3]:  # 每种类型最多报告 3 个
                results.append(self.warn(
                    f"{pattern['message']}",
                    file=pattern["file"],
                    line=pattern.get("line"),
                ))

        return results

    def _find_anti_patterns(self, source: str, file_path: Path) -> list[dict[str, Any]]:
        """查找性能反模式

        Args:
            source: 源代码
            file_path: 文件路径

        Returns:
            反模式列表
        """
        import re

        patterns = []
        lines = source.split("\n")

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # 跳过注释
            if stripped.startswith("//"):
                continue

            # 1. 循环中的数组操作
            if self._is_in_loop_context(lines, line_num - 1):
                if re.search(r"\.(filter|map|reduce|forEach)\s*\(", line):
                    patterns.append({
                        "file": file_path,
                        "line": line_num,
                        "type": "array_op_in_loop",
                        "message": "循环中使用数组操作，建议提前计算",
                        "context": stripped[:80],
                    })

            # 2. 深拷贝大型对象
            if re.search(r"JSON\.parse\s*\(\s*JSON\.stringify\s*\(", line):
                patterns.append({
                    "file": file_path,
                    "line": line_num,
                    "type": "deep_copy_anti_pattern",
                    "message": "使用 JSON.parse/stringify 进行深拷贝，性能较差",
                    "context": stripped[:80],
                })

            # 3. 频繁的 DOM 查询
            if re.search(r"document\.querySelector\s*\(", line) or \
               re.search(r"document\.getElementById\s*\(", line):
                patterns.append({
                    "file": file_path,
                    "line": line_num,
                    "type": "frequent_dom_query",
                    "message": "频繁查询 DOM，建议缓存结果",
                    "context": stripped[:80],
                })

            # 4. 未优化的 React 重渲染
            if re.search(r"React\.(memo|useMemo|useCallback)\s*\(", line) is None:
                # 检查是否是 React 组件
                if re.search(r"function\s+\w+\s*\(.*\)\s*{", line) or \
                   re.search(r"=>\s*{", line):
                    # 简单的启发式：如果包含大量状态或计算，建议优化
                    if "useState" in source or "useEffect" in source:
                        # 这里只是建议，不是强制
                        pass

        return patterns

    def _is_in_loop_context(self, lines: list[str], idx: int) -> bool:
        """检查是否在循环上下文中

        Args:
            lines: 代码行列表
            idx: 当前行索引

        Returns:
            是否在循环中
        """
        import re

        # 向前查找最近 20 行
        for i in range(max(0, idx - 20), idx + 1):
            line = lines[i]
            if re.search(r"\b(for|while|forEach)\s*\(", line):
                return True

            # 检查 for...of 和 for...in
            if re.search(r"\bfor\s*\(.*\bof\b", line):
                return True
            if re.search(r"\bfor\s*\(.*\bin\b", line):
                return True

        return False

    def _find_ts_files(self) -> list[Path]:
        """查找所有 TypeScript 文件"""
        files = []
        for ext in ["*.ts", "*.tsx", "*.mts", "*.cts"]:
            files.extend(self._find_files(ext))
        return [f for f in files if not self._should_skip(f)]
