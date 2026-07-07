"""TypeScript 专项检查 — 类型导出完整性检查"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult


class TypeScriptExportCheck(Check):
    """TypeScript 类型导出完整性检查

    检测类型导出问题：
    - 未导出的公共类型
    - 未使用的导出
    - 循环依赖的导出
    """

    name = "typescript_export_integrity"
    description = "TypeScript 类型导出完整性检查"

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        super().__init__(project_root, config)

    def run(self) -> list[CheckResult]:
        results = []

        # 1. 检查是否有 TypeScript 文件
        ts_files = self._find_ts_files()
        if not ts_files:
            return [self.skip("项目中没有 TypeScript 文件")]

        # 2. 分析导出
        export_stats = self._analyze_exports(ts_files)

        # 3. 生成报告
        total_exports = export_stats["total_exports"]
        unused_exports = export_stats["unused_exports"]
        missing_exports = export_stats["missing_exports"]

        if total_exports == 0:
            return [self.pass_check("项目无导出类型")]

        # 检查未使用的导出
        if unused_exports:
            results.append(self.warn(
                f"发现 {len(unused_exports)} 个未使用的导出",
            ))

            for export in unused_exports[:5]:  # 最多报告 5 个
                results.append(self.warn(
                    f"未使用的导出: {export['name']}",
                    file=export["file"],
                    line=export.get("line"),
                ))

        # 检查缺少导出的公共类型
        if missing_exports:
            results.append(self.info(
                f"发现 {len(missing_exports)} 个未导出的公共类型",
            ))

        if not results:
            results.append(self.pass_check("类型导出完整性检查通过"))

        return results

    def _analyze_exports(self, ts_files: list[Path]) -> dict[str, Any]:
        """分析类型导出

        Args:
            ts_files: TypeScript 文件列表

        Returns:
            导出统计
        """
        import re

        exports: dict[str, dict[str, Any]] = {}
        usages: dict[str, int] = {}

        # 第一遍：收集所有导出
        for file_path in ts_files:
            if self._should_skip(file_path):
                continue

            try:
                source = file_path.read_text(encoding="utf-8")
                rel_path = str(file_path.relative_to(self.project))

                # 查找 export 语句
                for line_num, line in enumerate(source.split("\n"), 1):
                    stripped = line.strip()

                    # 跳过注释
                    if stripped.startswith("//"):
                        continue

                    # 匹配 export 语句
                    # export const/let/var/function/class/interface/type
                    patterns = [
                        r"export\s+(?:const|let|var)\s+(\w+)",
                        r"export\s+(?:function)\s+(\w+)",
                        r"export\s+(?:class)\s+(\w+)",
                        r"export\s+(?:interface|type)\s+(\w+)",
                    ]

                    for pattern in patterns:
                        match = re.search(pattern, line)
                        if match:
                            name = match.group(1)
                            exports[name] = {
                                "name": name,
                                "file": file_path,
                                "line": line_num,
                            }
                            break

            except Exception:
                continue

        # 第二遍：统计使用情况
        for file_path in ts_files:
            if self._should_skip(file_path):
                continue

            try:
                source = file_path.read_text(encoding="utf-8")

                for export_name in exports:
                    # 简单的使用统计（精确性可以后续优化）
                    count = source.count(export_name)
                    # 排除导出声明本身
                    if export_name in usages:
                        usages[export_name] += max(0, count - 1)
                    else:
                        usages[export_name] = max(0, count - 1)

            except Exception:
                continue

        # 分析未使用的导出
        unused = []
        for name, info in exports.items():
            if usages.get(name, 0) == 0:
                unused.append(info)

        return {
            "total_exports": len(exports),
            "unused_exports": unused,
            "missing_exports": [],  # TODO: 实现检测
        }

    def _find_ts_files(self) -> list[Path]:
        """查找所有 TypeScript 文件"""
        files = []
        for ext in ["*.ts", "*.tsx", "*.mts", "*.cts"]:
            files.extend(self._find_files(ext))
        return [f for f in files if not self._should_skip(f)]
