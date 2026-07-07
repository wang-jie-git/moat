"""TypeScript 竞态条件检查

检测竞态条件相关代码（handleStop/pendingMessageRef/lineCompletePendingRef 等）
是否缺少时序注释或注释。
"""
import re
from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult


class TypeScriptRaceConditionCheck(Check):
    """TypeScript 竞态条件检查

    检查项:
    - handleStop 函数必须有时序注释
    - pendingMessageRef 必须注释说明竞态保护
    - lineCompletePendingRef 必须注释说明用途
    """

    # 关键变量/函数
    CRITICAL_PATTERNS = {
        "handleStop": {
            "description": "用户中断 → WebSocket interrupt → 等待 line_complete",
            "required_keywords": ["时序", "timing", "中断", "interrupt", "pending"],
        },
        "pendingMessageRef": {
            "description": "缓存用户消息，防止 WebSocket 未就绪时丢失",
            "required_keywords": ["pending", "缓存", "缓存", "消息", "中断", "竞态"],
        },
        "lineCompletePendingRef": {
            "description": "标记是否正在处理 line_complete 事件",
            "required_keywords": ["lineComplete", "标记", "防止", "重复"],
        },
        "busyClearTimeoutRef": {
            "description": "延迟清 busy 的定时器",
            "required_keywords": ["busy", "timeout", "延迟", "800ms"],
        },
    }

    def run(self) -> list[CheckResult]:
        results = []

        ts_files = self._find_ts_files()
        if not ts_files:
            return [self.skip("项目中没有 TypeScript 文件")]

        for file in ts_files:
            try:
                content = file.read_text(encoding="utf-8")
                lines = content.split("\n")

                for pattern, config in self.CRITICAL_PATTERNS.items():
                    # 查找关键变量/函数
                    matches = list(re.finditer(pattern, content))
                    if not matches:
                        continue

                    for match in matches:
                        line_num = content[:match.start()].count("\n") + 1

                        # 检查前 15 行是否有必要注释
                        context_start = max(0, line_num - 16)
                        context = "\n".join(lines[context_start:line_num])

                        has_comment = any(
                            kw.lower() in context.lower()
                            for kw in config["required_keywords"]
                        )

                        if not has_comment:
                            results.append(self.warn(
                                f"{pattern} 缺少时序注释\n"
                                f"建议添加注释说明: {config['description']}",
                                file=str(file.relative_to(self.project)),
                                line=line_num,
                            ))

            except Exception as e:
                results.append(self.fail(
                    f"读取文件失败: {e}",
                    file=str(file.relative_to(self.project)),
                ))

        if not results:
            return [self.pass_check("竞态条件注释检查通过")]

        return results

    def _find_ts_files(self) -> list[Path]:
        """查找所有 TypeScript 文件"""
        files = []
        for ext in ["*.ts", "*.tsx"]:
            files.extend(self._find_files(ext))
        return [f for f in files if not self._should_skip(f)]
