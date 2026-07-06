"""Moat 运行器 — 协调所有检查"""
import json
import time
from pathlib import Path
from datetime import datetime


class CheckResult:
    """单次检查结果"""

    def __init__(self):
        self.errors: list[dict] = []
        self.passed: int = 0
        self.failed: int = 0
        self.skipped: int = 0
        self.start_time: float = time.time()
        self.end_time: float = 0

    def add_errors(self, errors: list[dict]):
        for e in errors:
            if e.get("type", "").endswith("_ok"):
                self.passed += 1
            elif e.get("type", "").startswith("skip_"):
                self.skipped += 1
            else:
                self.failed += 1
                self.errors.append(e)

    @property
    def duration(self) -> float:
        return (self.end_time or time.time()) - self.start_time

    def summary(self) -> str:
        return f"通过: {self.passed}, 失败: {self.failed}, 跳过: {self.skipped}, 耗时: {self.duration:.2f}s"


def run_all_checks(project_root: str = ".") -> bool:
    """运行所有检查"""
    root = Path(project_root).resolve()
    print(f"\n{'=' * 50}")
    print(f"  Moat — AI 编码护城河")
    print(f"  {root}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 50}\n")

    from moat.checks import l1_import, l1_api, l1_modules, l1_files, l1_subsystems, l1_behavior
    from moat.checks import l2_schema, l3_correlation, l4_baseline
    from moat.baseline import BaselineManager

    result = CheckResult()

    # L0: 语法检查
    print("▸ L0 语法检查...")
    errors = l1_import.run_syntax_check(root)
    result.add_errors(errors)
    for e in errors:
        _print_error(e)

    # L1: import 检查
    print("▸ L1 import 链检查...")
    errors = l1_import.run_import_check(root)
    result.add_errors(errors)
    for e in errors:
        _print_error(e)

    # L1: 文件完整性
    print("▸ L1 文件完整性检查...")
    errors = l1_files.run_file_check(root)
    result.add_errors(errors)
    for e in errors:
        _print_error(e)

    # L1: 核心模块
    print("▸ L1 核心模块检查...")
    errors = l1_modules.run_modules_check(root)
    result.add_errors(errors)
    for e in errors:
        _print_error(e)

    # L1: 子系统
    print("▸ L1 子系统检查...")
    errors = l1_subsystems.run_subsystems_check(root)
    result.add_errors(errors)
    for e in errors:
        _print_error(e)

    # L1: 行为
    print("▸ L1 行为检查...")
    errors = l1_behavior.run_behavior_check(root)
    result.add_errors(errors)
    for e in errors:
        _print_error(e)

    # L3: 关联检查
    print("▸ L3 跨系统关联检查...")
    errors = l3_correlation.run_correlation_check(root)
    result.add_errors(errors)
    for e in errors:
        _print_error(e)

    # L4: 基线对比
    bm = BaselineManager(root)
    baseline = bm.load()
    print("▸ L4 基线对比...")
    errors = l4_baseline.run_baseline_check(root, baseline)
    result.add_errors(errors)
    for e in errors:
        _print_error(e)

    result.end_time = time.time()

    # 输出总结
    print(f"\n{'=' * 50}")
    print(f"  结果: {result.summary()}")
    print(f"{'=' * 50}")

    if result.failed > 0:
        print(f"\n❌ 发现 {result.failed} 个问题:")
        for e in result.errors:
            print(f"   [{e['level']}] {e['file']}: {e['message']}")
        return False
    else:
        print(f"\n✅ MOAT 全部通过，系统健康。")
        return True


def _print_error(e: dict):
    """打印错误（带颜色）"""
    typ = e.get("type", "")
    if typ.endswith("_ok"):
        return  # 静默通过
    if typ.endswith("_missing"):
        symbol = "⚠"
    elif typ.startswith("skip_"):
        symbol = "·"
    else:
        symbol = "❌"
    print(f"  {symbol} [{e['level']}] {e['file']}: {e['message']}")