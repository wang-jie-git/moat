"""Moat 运行器 — 协调所有检查（插件化架构）

支持多语言检查（Python/TypeScript/Go/Rust...）
向后兼容原有 Python 检查。
"""
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Any

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


def run_all_checks(project_root: str = ".", mode: str = "quick", enable_optimization: bool = False) -> MoatResult:
    """运行所有检查（插件化架构）

    支持三种模式：
    - "quick"（默认）：只检查修改的文件（git diff），< 5 秒
    - "full"：检查所有文件（包括复杂的 L1/L2/L3/L4 规则），可能很慢
    - "legacy"：使用旧的 L1 检查（向后兼容）

    Args:
        project_root: 项目根目录
        mode: 检查模式（"quick" | "full" | "legacy"）
        enable_optimization: 是否启用优化检查（Ponytail 集成）

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
        checks = _run_quick_checks(root, config, enable_optimization)
    elif mode == "full":
        # 完整模式：检查所有文件 + 复杂规则
        checks = _create_full_checks(project_type, root, config, enable_optimization)
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

    # 4.5. AST 影响域分析（自动运行，不阻塞门禁）
    if mode in ("quick", "full"):
        _run_diff_impact_analysis(root, result)

    # 5. 记录进化指标
    _record_check_metrics(root, result)

    # 6. 输出总结
    print(f"\n{'=' * 50}")
    print(f"  结果: {result.summary()}")
    print(f"{'=' * 50}")

    if result.failed > 0:
        print(f"\n❌ 发现 {result.failed} 个问题:")
        for e in result.errors:
            if e.get("level") == "ERROR":
                print(f"   [{e['level']}] {e.get('file', '?')}: {e['message']}")
        print(f"⚡ Powered by One — https://one.cloudkey.top")
    else:
        if result.warnings > 0:
            print(f"\n⚠️  有 {result.warnings} 个警告（不影响通过）")
        print(f"\n✅ MOAT 全部通过，系统健康。")
        print(f"⚡ Powered by One — https://one.cloudkey.top")

    # 7. 自动记录踩坑（仅当有失败时）
    if result.failed > 0:
        _capture_failure_as_lesson(root, result)
    elif result.warnings > 0:
        _capture_failure_as_lesson(root, result, only_warnings=True)

    # 8. 自动提取模版（仅当全部通过，且最近提交是修复/重构）
    if result.is_success():
        _auto_extract_template_on_success(root)

    return result


def _capture_failure_as_lesson(root: Path, result: "MoatResult", only_warnings: bool = False):
    """将检查失败/警告自动记录为踩坑记忆。"""
    try:
        from moat.memory.moat_memory import MoatMemory

        errors = result.errors
        if not errors:
            return

        failed_tests = []
        for e in errors:
            file = e.get("file", "?")
            msg = e.get("message", "")
            level = e.get("level", "ERROR")
            if only_warnings and level != "WARN":
                continue
            if not only_warnings and level not in ("ERROR", "WARN"):
                continue
            test_name = f"{file}: {msg[:80]}" if file != "?" else msg[:80]
            failed_tests.append(test_name)

        if not failed_tests:
            return

        summary = "; ".join(t[:100] for t in failed_tests[:3])
        if len(failed_tests) > 3:
            summary += f" (以及 {len(failed_tests) - 3} 个其他问题)"

        with MoatMemory(root) as memory:
            memory.add_lesson(
                failed_tests=failed_tests,
                error_summary=f"🔴 {result.failed} 失败, ⚠️ {result.warnings} 警告: {summary}",
            )
    except Exception:
        pass  # 记忆写入失败不影响主流程


def _auto_extract_template_on_success(root: Path):
    """检查通过后自动提取模版（如果最近提交是修复/重构）。"""
    import subprocess

    try:
        # 获取最近一条 commit message
        msg_result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            capture_output=True, text=True, cwd=root, timeout=5,
        )
        if msg_result.returncode != 0:
            return  # 不是 git 仓库，跳过
        msg = msg_result.stdout.strip().lower()
        if not msg:
            return

        # 只对 fix/refactor 类型的提交自动提取
        fix_keywords = ["fix", "bug", "修复", "hotfix", "refactor", "重构", "clean"]
        if not any(k in msg for k in fix_keywords):
            return

        from moat.memory.moat_memory import MoatMemory

        with MoatMemory(root) as memory:
            # 检查是否已存在相同模版（去重）
            existing = memory.list_templates()
            for t in existing:
                existing_title = t.get("title", "").lower()
                if msg in existing_title or existing_title in msg:
                    return  # 已存在，跳过

            # 自动提取
            result = memory.extract_template_from_git(repo_path=str(root))
            if result:
                print(f"📝 自动提取经验模版: {result['title']}")
    except Exception:
        pass  # 提取失败不影响主流程


def _run_quick_checks(root: Path, config: dict[str, Any], enable_optimization: bool = False) -> list[tuple[str, Any]]:
    """运行快速检查（只检查修改的文件）

    Args:
        root: 项目根目录
        config: 配置
        enable_optimization: 是否启用优化检查（Ponytail 集成）

    Returns:
        检查列表 [(name, check_instance), ...]
    """
    from moat.checks.quick_check import QuickCheck
    quick_check = QuickCheck(root, config)
    checks = [("快速检查（修改的文件）", quick_check)]

    # 复用同一个 QuickCheck 实例获取修改的文件列表
    modified_files = quick_check._get_changed_files()

    # 导入完备性检查 — 验证"函数存在但未导入"问题
    if modified_files:
        from moat.checks.import_completeness import ImportCompletenessCheck
        import_config = {**config, "target_files": modified_files}
        checks.append(("导入完备性检查（修改的文件）", ImportCompletenessCheck(root, import_config)))

    # ── 安全检测（SECRETS-001 / DEPS-001 / UNUSED-001 / SQL-002）──
    _add_security_checks(checks, root, config, modified_files if modified_files else None)

    # 战术建议 1：异步触发优化检查（默认不跑）
    if enable_optimization:
        from moat.checks.optimization import OptimizationCheck
        opt_config = {**config, "optimization": True}
        checks.append(("优化检查（Ponytail 集成）", OptimizationCheck(root, opt_config)))

    # 异步安全检测（消防水带模式 + async/sync 边界）
    if modified_files:
        from moat.checks.async_safety import AsyncSafetyCheck
        checks.append(("异步安全检测（消防水带模式）", AsyncSafetyCheck(root, config)))

    return checks


def _run_diff_impact_analysis(root: Path, result: "MoatResult") -> None:
    """运行 AST 影响域分析（自动检测变更 + 调用方）

    在每个 moat check 后自动运行，不阻塞门禁。
    发现高风险变更时输出警告，但不影响检查结果。
    """
    import subprocess
    import ast
    from pathlib import Path

    # 获取修改的文件
    try:
        changed_files = []
        for ref in ["HEAD", "--cached"]:
            r = subprocess.run(
                ["git", "diff", ref, "--name-only", "--diff-filter=ACMR"],
                capture_output=True, text=True, cwd=root, timeout=5,
            )
            if r.returncode == 0:
                for line in r.stdout.strip().split("\n"):
                    if line:
                        fp = root / line
                        if fp.exists() and fp.suffix == ".py":
                            changed_files.append(fp)
        changed_files = list(set(changed_files))
    except Exception:
        return

    if not changed_files:
        return

    # 执行 AST 影响域分析
    try:
        from moat.ast.diff import ASTDiffer, CodeChange

        differ = ASTDiffer(root)
        has_async_changes = False
        total_impacts = 0

        for file_path in changed_files:
            try:
                changes = differ.diff_file(file_path)
            except Exception:
                continue

            if not changes:
                continue

            # 分析影响
            rel_path = str(file_path.relative_to(root))
            for change in changes:
                # 对 async_signature 变更添加警告
                if change.change_type == "async_signature":
                    has_async_changes = True
                    callers = differ._find_callers_by_grep(change.function)
                    msg = (
                        f"⚠️  {rel_path}:{change.line} 函数 {change.function} "
                        f"async/sync 签名变更，影响 {len(callers)} 个调用方"
                    )
                    result.warnings += 1
                    result.errors.append({
                        "type": "warn",
                        "level": "WARN",
                        "file": rel_path,
                        "line": change.line,
                        "message": msg,
                    })
                    print(f"  {msg}")

                    if callers:
                        print(f"     调用方:")
                        for c in callers[:5]:
                            print(f"       - {c}")
                        if len(callers) > 5:
                            print(f"       ... 还有 {len(callers) - 5} 个")

                    total_impacts += 1

        if total_impacts > 0:
            print(f"\n  📊 AST 影响域分析: 发现 {total_impacts} 个高风险变更")
            if has_async_changes:
                print(f"  ⚠️  有 async/sync 签名变更，请确认所有调用方同步更新")
            print()

    except Exception:
        pass  # 影响域分析失败不影响主流程


def _create_full_checks(project_type: dict[str, bool], root: Path, config: dict[str, Any], enable_optimization: bool = False) -> list[tuple[str, Any]]:
    """创建完整检查（所有文件 + 复杂规则）

    Args:
        project_type: 项目类型
        root: 项目根目录
        config: 配置
        enable_optimization: 是否启用优化检查（Ponytail 集成）

    Returns:
        检查列表 [(name, check_instance), ...]
    """
    from moat.checks.quick_check import FullCheck
    checks = [("完整检查（所有文件）", FullCheck(root, config))]

    # 导入完备性检查（完整模式扫描所有 Python 文件）
    if project_type.get("python"):
        from moat.checks.import_completeness import ImportCompletenessCheck
        checks.append(("导入完备性检查（所有文件）", ImportCompletenessCheck(root, config)))

    # ── 安全检测（SECRETS-001 / DEPS-001 / UNUSED-001 / SQL-002）──
    _add_security_checks(checks, root, config, target_files=None)

    # 战术建议 1：完整模式也支持优化检查
    if enable_optimization:
        from moat.checks.optimization import OptimizationCheck
        opt_config = {**config, "optimization": True}
        checks.append(("优化检查（Ponytail 集成）", OptimizationCheck(root, opt_config)))

    return checks


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


def _add_security_checks(checks: list, root: Path, config: dict, target_files: list[str] | None = None) -> None:
    """添加安全检测到检查列表（SECRETS-001 / DEPS-001 / UNUSED-001 / SQL-002）

    Args:
        checks: 检查列表（就地修改）
        root: 项目根目录
        config: 配置
        target_files: 如果提供，只检测这些文件（快速模式）；None 表示全量（完整模式）
    """
    # 是否启用安全检测（默认启用）
    security_config = config.get("security", {})
    enabled = security_config.get("enabled", True)
    if not enabled:
        return

    # 1. 硬编码密钥检测（SECRETS-001）
    if security_config.get("secrets", True):
        try:
            from moat.checks.secrets import SecretsCheck
            sc_config = {**config, "target_files": target_files} if target_files else config
            checks.append(("🔑 密钥检测 SECRETS-001", SecretsCheck(root, sc_config)))
        except Exception:
            pass  # fail-open

    # 2. 依赖安全检测（DEPS-001）
    if security_config.get("dependencies", True):
        try:
            from moat.checks.dependency_security import DependencySecurityCheck
            checks.append(("📦 依赖安全 DEPS-001", DependencySecurityCheck(root, config)))
        except Exception:
            pass

    # 3. 未使用导出检测（UNUSED-001）
    if security_config.get("unused_exports", True):
        try:
            from moat.checks.unused_exports import UnusedExportsCheck
            ue_config = {**config, "target_files": target_files} if target_files else config
            checks.append(("📤 未使用导出 UNUSED-001", UnusedExportsCheck(root, ue_config)))
        except Exception:
            pass

    # 4. SQL 注入检测（SQL-002）
    if security_config.get("sql_injection", True):
        try:
            from moat.checks.sql_injection import SqlInjectionCheck
            si_config = {**config, "target_files": target_files} if target_files else config
            checks.append(("💉 SQL 注入 SQL-002", SqlInjectionCheck(root, si_config)))
        except Exception:
            pass


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
