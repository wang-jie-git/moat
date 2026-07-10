"""Moat 运行器 — 协调所有检查（插件化架构）

支持多语言检查（Python/TypeScript/Go/Rust...）
向后兼容原有 Python 检查。
"""
import json
import time
from pathlib import Path
from datetime import datetime

from moat.checks.base import Check, CheckResult
from moat.checks import detect_project_type, create_check_instances


class MoatResult:
    """Moat 检查结果"""

    def __init__(self):
        self.passed: int = 0
        self.failed: int = 0
        self.skipped: int = 0
        self.warnings: int = 0
        self.start_time: float = time.time()
        self.end_time: float = 0
        self.errors: list[dict] = []

    def add_check_result(self, result: CheckResult):
        """添加检查结果"""
        if result.type == "pass":
            self.passed += 1
        elif result.type == "fail":
            self.failed += 1
            self.errors.append(result.to_dict())
        elif result.type == "warn":
            self.warnings += 1
            self.errors.append(result.to_dict())
        elif result.type == "skip":
            self.skipped += 1
    def add_legacy_errors(self, errors: list[dict]):
        """添加旧风格的错误（dict）"""
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

    @property
    def total_checks(self) -> int:
        return self.passed + self.failed + self.skipped + self.warnings

    def summary(self) -> str:
        return (
            f"通过: {self.passed}, 失败: {self.failed}, "
            f"警告: {self.warnings}, 跳过: {self.skipped}, "
            f"耗时: {self.duration:.2f}s"
        )

    def is_success(self) -> bool:
        """检查是否成功（允许警告，但不允许失败）"""
        return self.failed == 0


def run_all_checks(project_root: str = ".", mode: str = "quick") -> MoatResult:
    """运行所有检查（插件化架构）

    支持三种模式：
    - "quick"（默认）：只检查修改的文件（git diff），< 5 秒
    - "full"：检查所有文件（包括复杂的 L1/L2/L3/L4 规则），可能很慢
    - "legacy"：使用旧的 L1 检查（向后兼容）

    Args:
        project_root: 项目根目录
        mode: 检查模式（"quick" | "full" | "legacy"）

    Returns:
        MoatResult 包含完整的检查结果和错误列表
    """
    root = Path(project_root).resolve()
    result = MoatResult()

    print(f"\n{'=' * 50}")
    print(f"  Moat — AI 编码护城河")
    print(f"  {root}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 50}\n")

    # 1. 检测项目类型
    project_type = detect_project_type(root)
    print(f"📊 项目类型: {', '.join(k for k, v in project_type.items() if v) or '未知'}")
    print(f"🔧 检查模式: {mode}\n")

    # 2. 加载配置
    config = _load_config(root)

    # 3. 根据模式运行检查
    if mode == "quick":
        # 快速模式：只检查修改的文件
        checks = _run_quick_checks(root, config)
    elif mode == "full":
        # 完整模式：检查所有文件 + 复杂规则
        checks = _create_full_checks(project_type, root, config)
    elif mode == "legacy":
        # 旧模式：使用旧的 L1 检查
        checks = create_check_instances(project_type, root, config)
    else:
        raise ValueError(f"未知模式: {mode}")

    # 4. 运行检查
    for name, check_or_module in checks:
        print(f"▸ {name}...")

        # 检查是基于 Check 基类的实例还是旧风格模块
        if isinstance(check_or_module, Check):
            # 新风格：Check 基类实例
            check_results = check_or_module.run()
            for r in check_results:
                result.add_check_result(r)
                _print_result(r)
        else:
            # 旧风格：模块（向后兼容）
            # 根据名称推断运行哪个函数
            legacy_errors = _run_legacy_check(check_or_module, name, root)
            result.add_legacy_errors(legacy_errors)
            for e in legacy_errors:
                _print_error(e)

    result.end_time = time.time()

    # 5. 输出总结
    print(f"\n{'=' * 50}")
    print(f"  结果: {result.summary()}")
    print(f"{'=' * 50}")

    if result.failed > 0:
        print(f"\n❌ 发现 {result.failed} 个问题:")
        for e in result.errors:
            if e.get("level") == "ERROR":
                print(f"   [{e['level']}] {e.get('file', '?')}: {e['message']}")
    else:
        if result.warnings > 0:
            print(f"\n⚠️  有 {result.warnings} 个警告（不影响通过）")
        print(f"\n✅ MOAT 全部通过，系统健康。")

    return result


def _run_quick_checks(root: Path, config: dict[str, Any]) -> list[tuple[str, Any]]:
    """运行快速检查（只检查修改的文件）

    Args:
        root: 项目根目录
        config: 配置

    Returns:
        检查列表 [(name, check_instance), ...]
    """
    from moat.checks.quick_check import QuickCheck
    return [("快速检查（修改的文件）", QuickCheck(root, config))]


def _create_full_checks(project_type: dict[str, bool], root: Path, config: dict[str, Any]) -> list[tuple[str, Any]]:
    """创建完整检查（所有文件 + 复杂规则）

    Args:
        project_type: 项目类型
        root: 项目根目录
        config: 配置

    Returns:
        检查列表 [(name, check_instance), ...]
    """
    from moat.checks.quick_check import FullCheck
    return [("完整检查（所有文件）", FullCheck(root, config))]


def _run_legacy_check(module, name: str, root: Path) -> list[dict]:
    """运行旧风格的检查（向后兼容）"""
    try:
        if "语法" in name:
            return module.run_syntax_check(root)
        elif "import" in name:
            return module.run_import_check(root)
        elif "文件完整性" in name:
            return module.run_file_check(root)
        elif "核心模块" in name:
            return module.run_modules_check(root)
        elif "子系统" in name:
            return module.run_subsystems_check(root)
        elif "行为" in name:
            return module.run_behavior_check(root)
        else:
            return []
    except Exception as e:
        return [{"type": "error", "level": "ERROR", "file": name, "message": str(e)}]


def _load_config(root: Path) -> dict:
    """加载 Moat 配置（优先读取 moat.json，向后兼容 config.json）"""
    # 优先读取 moat.json（新格式）
    moat_json_path = root / ".moat" / "moat.json"
    if moat_json_path.exists():
        try:
            return json.loads(moat_json_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 向后兼容：读取 config.json（旧格式）
    config_path = root / ".moat" / "config.json"
    if config_path.exists():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _print_result(r: CheckResult):
    """打印检查结果"""
    if r.type == "pass":
        return  # 静默通过
    elif r.type == "warn":
        symbol = "⚠️ "
    elif r.type == "fail":
        symbol = "❌"
    else:
        symbol = "·"

    file_info = f"{r.file}" if r.file else ""
    if r.line:
        file_info += f":{r.line}"

    if file_info:
        print(f"  {symbol} [{r.level}] {file_info}: {r.message}")
    else:
        print(f"  {symbol} [{r.level}] {r.message}")


def _print_error(e: dict):
    """打印错误（兼容旧风格）"""
    typ = e.get("type", "")
    if typ.endswith("_ok"):
        return  # 静默通过
    if typ.endswith("_missing"):
        symbol = "⚠"
    elif typ.startswith("skip_"):
        symbol = "·"
    else:
        symbol = "❌"


def _record_check_metrics(root: Path, result: MoatResult):
    """自动记录进化指标（v0.5.0 新增）

    在每次 moat check 后自动记录关键指标。

    Args:
        root: 项目根目录
        result: 检查结果
    """
    try:
        from moat.evolution_metrics import EvolutionTracker

        moat_dir = root / ".moat"
        if not moat_dir.exists():
            return

        tracker = EvolutionTracker(moat_dir)

        # 记录检查通过/失败指标
        success_rate = result.passed / max(result.total_checks, 1)
        tracker.record_refactor_success(
            files_changed=0,  # moat check 不涉及文件变更
            tests_passed=result.is_success(),
            pain_score_before=0.0,
            pain_score_after=100.0 * (1 - success_rate),
            context={
                "source": "moat_check",
                "total_checks": result.total_checks,
                "passed": result.passed,
                "failed": result.failed,
            },
        )

        # 如果有失败，记录误报指标（如果可能）
        if result.failed > 0:
            for error in result.errors[:3]:  # 最多记录前 3 个错误
                if error.get("level") == "ERROR":
                    tracker.record_false_positive(
                        error_type=error.get("type", "unknown"),
                        file_path=error.get("file", "unknown"),
                        context={"source": "moat_check"},
                    )

    except ImportError:
        pass  # evolution_metrics 模块不可用
    except Exception as e:
        print(f"⚠️  记录进化指标失败: {e}")
