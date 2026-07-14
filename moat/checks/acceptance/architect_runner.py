"""验收引擎 — 编排规则注册表 + verification operator + 检查管道

执行流程:
1. 加载 architect.yml 规则注册表
2. 自动检查 → 调用 verification operator / 现有检查管道
3. 人工核查 → 生成证据包 + 核查清单
4. 聚合结果 → 输出验收报告
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .rule_registry import RuleRegistry, RuleDefinition, RuleResult


@dataclass
class AcceptanceReport:
    """完整验收报告"""

    project_path: Path
    """项目路径"""

    rules: list[RuleResult] = field(default_factory=list)
    """所有规则验收结果"""

    overall_score: float = 0.0
    """总体评分 (0-100)"""

    passed: bool = False
    """是否全部通过"""

    total_auto: int = 0
    """自动检查数"""

    total_manual: int = 0
    """人工核查数"""

    passed_auto: int = 0
    """自动检查通过数"""

    execution_time: float = 0.0
    """执行耗时"""

    evidence_dir: Path | None = None
    """证据目录"""

    truth_doc_path: Path | None = None
    """真元文档路径"""

    version: str = "1.0"
    """验收版本"""

    steps_info: dict[int, dict[str, str]] = field(default_factory=dict)
    """步骤元信息"""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_path": str(self.project_path),
            "overall_score": round(self.overall_score, 1),
            "passed": self.passed,
            "total_auto": self.total_auto,
            "total_manual": self.total_manual,
            "passed_auto": self.passed_auto,
            "execution_time": round(self.execution_time, 2),
            "version": self.version,
            "rules": [r.to_dict() for r in self.rules],
        }

    def summary(self) -> dict[str, Any]:
        """简短摘要"""
        return {
            "score": f"{self.overall_score:.0f}/100",
            "status": "✅ 通过" if self.passed else "❌ 未通过",
            "auto": f"{self.passed_auto}/{self.total_auto}",
            "manual": self.total_manual,
            "time": f"{self.execution_time:.1f}s",
        }


class ArchitectRunner:
    """验收引擎 — 是 `moat accept` 的后端核心"""

    def __init__(self, project_root: Path, rules_path: str | Path | None = None):
        self.project_root = project_root.resolve()
        self.rules_path = Path(rules_path) if rules_path else None
        self.registry = RuleRegistry(self.project_root)
        self.target_files: list[str] | None = None  # 增量模式的限定文件列表

    def _get_changed_files(self) -> list[str]:
        """获取 git 修改的文件列表（增量模式）"""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                capture_output=True, text=True, cwd=self.project_root,
                timeout=10,
            )
            if result.returncode == 0:
                files = [f.strip() for f in result.stdout.split("\n") if f.strip()]
                return files
        except Exception:
            pass
        return []

    def run(self, diff_mode: bool = False) -> AcceptanceReport:
        """执行完整架构验收

        流程:
        1. 加载规则 → 2. 自动检查 → 3. 人工核查 → 4. 聚合报告

        Args:
            diff_mode: 增量模式，只检查 git 修改的文件
        """
        start_time = time.time()

        print(f"\n{'=' * 55}")
        title = "  🏗  Moat 架构验收（增量模式）" if diff_mode else "  🏗  Moat 架构验收"
        print(f"  {title}")
        print(f"  {self.project_root}")
        print(f"{'=' * 55}\n")

        # 1. 加载规则
        rules = self.registry.load(self.rules_path)
        summary = self.registry.summary()

        # 增量模式：获取修改的文件列表
        if diff_mode:
            self.target_files = self._get_changed_files()
            print(f"📋 增量模式：检测到 {len(self.target_files)} 个修改的文件")
            if not self.target_files:
                print(f"   无未提交的变更，跳过验收")
                return AcceptanceReport(
                    project_path=self.project_root,
                    overall_score=100.0,
                    passed=True,
                    execution_time=time.time() - start_time,
                )
        else:
            self.target_files = None

        # 检查是否使用了自定义规则文件
        rules_file = self.project_root / "architect.yml"
        if rules_file.exists():
            print(f"📋 加载自定义规则: {rules_file.name}")
        else:
            print(f"📋 使用内置默认规则（运行 moat accept --generate-rules 生成自定义规则）")

        print(f"📋 加载 {summary['total']} 条架构规则")
        print(f"   🔧 可自动检查: {summary['auto_checkable']}")
        print(f"   👤 需要人工核查: {summary['manual']}\n")

        # 2. 逐规则执行
        results: list[RuleResult] = []
        auto_rules = self.registry.get_auto_checkable()
        manual_rules = self.registry.get_manual()

        passed_auto = 0
        total_auto = len(auto_rules)

        # 2a. 自动检查
        if auto_rules:
            print("-" * 40)
            print("   🔧 自动检查阶段")
            print("-" * 40)
            for rule in auto_rules:
                result = self._run_auto_check(rule)
                results.append(result)
                if result.passed:
                    passed_auto += 1
                if result.auto_checked:
                    print(f"   {'✅' if result.passed else '❌'} [{rule.id}] {rule.title}")
                else:
                    print(f"   📋 [{rule.id}] {rule.title} (降级为人工核查)")
                if result.violations:
                    for v in result.violations:
                        print(f"      违规: {v.get('message', '')}")
                if not result.passed and result.suggestion:
                    print(f"      建议: {result.suggestion}")
                if result.manual_check_items:
                    for item in result.manual_check_items:
                        print(f"      □ {item}")
                print()

        # 2b. 人工核查
        if manual_rules:
            print("-" * 40)
            print("   👤 人工核查阶段（以下项需要人工确认）")
            print("-" * 40)
            for rule in manual_rules:
                result = self._run_manual_check(rule)
                results.append(result)
                print(f"   📋 [{rule.id}] {rule.title}")
                for item in result.manual_check_items:
                    print(f"      □ {item}")
                if result.suggestion:
                    print(f"      建议: {result.suggestion}")
                print()

        # 3. 计算评分
        overall_score = self._calculate_score(results)
        all_passed = all(
            (r.passed or not r.rule.auto_checkable)
            for r in results
        )

        elapsed = time.time() - start_time

        report = AcceptanceReport(
            project_path=self.project_root,
            rules=results,
            overall_score=overall_score,
            passed=all_passed,
            total_auto=total_auto,
            total_manual=len(manual_rules),
            passed_auto=passed_auto,
            execution_time=elapsed,
            evidence_dir=self.project_root / ".moat" / "acceptance_evidence",
            steps_info=RuleRegistry.get_default_steps_info(),
        )

        # 打印摘要
        self._print_summary(report)

        return report

    def _run_auto_check(self, rule: RuleDefinition) -> RuleResult:
        """执行单条规则的自动检查"""
        start = time.time()
        result = RuleResult(rule=rule)
        result.auto_checked = True

        try:
            if rule.operator and rule.operator in OPERATOR_MAP:
                operator_fn = OPERATOR_MAP[rule.operator]
                # 调用 verification operator
                op_result = operator_fn(
                    self.project_root,
                    target_files=self.target_files,
                )
                result.passed = op_result.get("passed", False)
                result.violations = op_result.get("violations", [])
                result.evidence = op_result.get("evidence", [])
                result.suggestion = op_result.get("suggestion")
            else:
                # 没有对应 operator，标记为人工核查
                result.passed = False
                result.auto_checked = False  # 降级为人工核查
                result.manual_check_items.append(
                    f"无对应自动算子，请人工检查: {rule.title}"
                )
        except Exception as e:
            result.passed = False
            result.violations.append({
                "message": f"自动检查失败: {e}",
                "severity": rule.severity,
            })

        result.execution_time = time.time() - start
        return result

    def _run_manual_check(self, rule: RuleDefinition) -> RuleResult:
        """生成人工核查清单"""
        result = RuleResult(rule=rule)
        result.auto_checked = False

        # 从规则配置中提取核查项
        items = rule.config.get("items", [f"请人工核查: {rule.title}"])
        result.manual_check_items = items

        # 尝试生成自动证据
        try:
            if rule.id == "GIT_BASELINE":
                evidence = self._collect_git_evidence()
                result.evidence = evidence
        except Exception:
            pass

        return result

    def _collect_git_evidence(self) -> list[str]:
        """收集 Git 基线证据"""
        evidence = []
        git_dir = self.project_root / ".git"

        if not git_dir.exists():
            evidence.append("❌ 未发现 Git 仓库")
            return evidence

        evidence.append("✅ Git 仓库已存在")

        # 尝试获取 git 状态
        try:
            import subprocess

            # 最近一次提交
            result = subprocess.run(
                ["git", "log", "-1", "--format=%h %ai %s"],
                capture_output=True, text=True, cwd=self.project_root,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                evidence.append(f"最新提交: {result.stdout.strip()}")

            # 是否有未提交变更
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, cwd=self.project_root,
                timeout=5,
            )
            changes = [l for l in result.stdout.split("\n") if l.strip()]
            if changes:
                evidence.append(f"未提交变更: {len(changes)} 个文件")
            else:
                evidence.append("✅ 工作区干净")

            # 检查 tag
            result = subprocess.run(
                ["git", "tag", "--list", "v*"],
                capture_output=True, text=True, cwd=self.project_root,
                timeout=5,
            )
            tags = [t for t in result.stdout.split("\n") if t.strip()]
            if tags:
                evidence.append(f"基线标签: {', '.join(tags[:5])}")
            else:
                evidence.append("⚠️  未创建基线标签 (建议: git tag v1.0)")

        except Exception as e:
            evidence.append(f"⚠️  Git 信息获取失败: {e}")

        return evidence

    def _calculate_score(self, results: list[RuleResult]) -> float:
        """计算总体评分

        策略:
        - 自动检查通过的规则得到满分权重
        - 未通过的自动检查按 severity 扣分
        - 人工核查项算 50% 权重（待确认）
        """
        if not results:
            return 0.0

        score = 100.0
        penalties = {"CRITICAL": 20.0, "HIGH": 10.0, "RECOMMENDED": 5.0}

        for result in results:
            if result.auto_checked and not result.passed:
                penalty = penalties.get(result.rule.severity, 10.0)
                score -= penalty * min(len(result.violations) + 1, 3)

        return max(0.0, min(100.0, score))

    def _print_summary(self, report: AcceptanceReport) -> None:
        """打印验收摘要"""
        summary = report.summary()
        print("=" * 55)
        print(f"  📊 验收完成")
        print(f"     评分: {summary['score']}")
        print(f"     状态: {summary['status']}")
        print(f"     自动检查: {summary['auto']}")
        print(f"     人工核查: {summary['manual']} 项")
        print(f"     耗时: {summary['time']}")
        print("=" * 55)

        if report.overall_score < 60:
            print(f"\n❌ 架构评分过低，建议修复后再继续")
        elif report.overall_score < 80:
            print(f"\n⚠️  架构有待改进，建议修复违规项")
        else:
            print(f"\n✅ 架构验收通过")

        if report.total_manual > 0:
            print(f"\n📋 还有 {report.total_manual} 项需要人工核查")
            print(f"   运行: moat accept --output report.md")
            print(f"   查看完整报告，手工确认后标记通过")


# ──────────────────────────────────────────────
# Operator 映射表 — 对接 verification 模块
# ──────────────────────────────────────────────

def _run_directory_operator(project_root: Path, target_files: list[str] | None = None) -> dict:
    """运行目录责任算子"""
    try:
        from moat.verification.operators import DirectoryResponsibilityOperator
        from moat.verification.types import VerificationContext

        op = DirectoryResponsibilityOperator()
        ctx = VerificationContext(project_path=project_root)
        result = op.verify(ctx)

        return {
            "passed": result.passed,
            "violations": [
                {"message": v.message, "severity": v.severity.value, "file": v.file_path, "line": v.line}
                for v in result.violations
            ],
            "evidence": [f"{k}: {v}" for k, v in result.evidence.items()],
            "suggestion": result.suggestions[0] if result.suggestions else None,
        }
    except Exception as e:
        return {"passed": False, "violations": [{"message": f"算子执行异常: {e}"}], "evidence": [], "suggestion": None}


def _run_module_drill_operator(project_root: Path, target_files: list[str] | None = None) -> dict:
    """运行最小模块演练算子"""
    try:
        from moat.verification.operators import MinimalModuleDrillOperator
        from moat.verification.types import VerificationContext

        op = MinimalModuleDrillOperator()
        ctx = VerificationContext(project_path=project_root)
        result = op.verify(ctx)

        return {
            "passed": result.passed,
            "violations": [
                {"message": v.message, "severity": v.severity.value, "file": v.file_path, "line": v.line}
                for v in result.violations
            ],
            "evidence": [f"{k}: {v}" for k, v in result.evidence.items()],
            "suggestion": result.suggestions[0] if result.suggestions else None,
        }
    except Exception as e:
        return {"passed": False, "violations": [{"message": f"算子执行异常: {e}"}], "evidence": [], "suggestion": None}


def _run_api_spec_operator(project_root: Path, target_files: list[str] | None = None) -> dict:
    """运行接口规范算子"""
    try:
        from moat.verification.operators import APIResponseSpecOperator
        from moat.verification.types import VerificationContext

        op = APIResponseSpecOperator()
        ctx = VerificationContext(project_path=project_root)
        result = op.verify(ctx)

        return {
            "passed": result.passed,
            "violations": [
                {"message": v.message, "severity": v.severity.value, "file": v.file_path, "line": v.line}
                for v in result.violations
            ],
            "evidence": [f"{k}: {v}" for k, v in result.evidence.items()],
            "suggestion": result.suggestions[0] if result.suggestions else None,
        }
    except Exception as e:
        return {"passed": False, "violations": [{"message": f"算子执行异常: {e}"}], "evidence": [], "suggestion": None}


def _run_framework_operator(project_root: Path, target_files: list[str] | None = None) -> dict:
    """运行框架边界算子"""
    try:
        from moat.verification.operators import FrameworkUsageOperator
        from moat.verification.types import VerificationContext

        op = FrameworkUsageOperator()
        ctx = VerificationContext(project_path=project_root)
        result = op.verify(ctx)

        return {
            "passed": result.passed,
            "violations": [
                {"message": v.message, "severity": v.severity.value, "file": v.file_path, "line": v.line}
                for v in result.violations
            ],
            "evidence": [f"{k}: {v}" for k, v in result.evidence.items()],
            "suggestion": result.suggestions[0] if result.suggestions else None,
        }
    except Exception as e:
        return {"passed": False, "violations": [{"message": f"算子执行异常: {e}"}], "evidence": [], "suggestion": None}


def _run_runtime_operator(project_root: Path, target_files: list[str] | None = None) -> dict:
    """运行运行时证据算子"""
    try:
        from moat.verification.operators import RuntimeEvidenceOperator
        from moat.verification.types import VerificationContext

        op = RuntimeEvidenceOperator()
        ctx = VerificationContext(project_path=project_root)
        result = op.verify(ctx)

        return {
            "passed": result.passed,
            "violations": [
                {"message": v.message, "severity": v.severity.value, "file": v.file_path, "line": v.line}
                for v in result.violations
            ],
            "evidence": [f"{k}: {v}" for k, v in result.evidence.items()],
            "suggestion": result.suggestions[0] if result.suggestions else None,
        }
    except Exception as e:
        return {"passed": False, "violations": [{"message": f"算子执行异常: {e}"}], "evidence": [], "suggestion": None}


def _run_truth_document_operator(project_root: Path, target_files: list[str] | None = None) -> dict:
    """运行真元文档生成算子"""
    try:
        from moat.verification.operators import TruthDocumentGeneratorOperator
        from moat.verification.types import VerificationContext

        op = TruthDocumentGeneratorOperator()
        ctx = VerificationContext(project_path=project_root)
        result = op.verify(ctx)

        return {
            "passed": result.passed,
            "violations": [
                {"message": v.message, "severity": v.severity.value, "file": v.file_path, "line": v.line}
                for v in result.violations
            ],
            "evidence": [f"{k}: {v}" for k, v in result.evidence.items()],
            "suggestion": result.suggestions[0] if result.suggestions else None,
        }
    except Exception as e:
        return {"passed": False, "violations": [{"message": f"算子执行异常: {e}"}], "evidence": [], "suggestion": None}


def _run_git_baseline_operator(project_root: Path, target_files: list[str] | None = None) -> dict:
    """运行 Git 基线检查"""
    evidence = []
    git_dir = project_root / ".git"

    if not git_dir.exists():
        return {
            "passed": False,
            "violations": [{"message": "未发现 Git 仓库", "severity": "CRITICAL"}],
            "evidence": ["❌ 未发现 Git 仓库"],
            "suggestion": "使用 git init 初始化仓库",
        }

    evidence.append("✅ Git 仓库已存在")

    try:
        import subprocess

        # 最近一次提交
        result = subprocess.run(
            ["git", "log", "-1", "--format=%h %ai %s"],
            capture_output=True, text=True, cwd=project_root,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            evidence.append(f"最新提交: {result.stdout.strip()}")
        else:
            evidence.append("⚠️  无提交记录")

        # 是否有未提交变更
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=project_root,
            timeout=5,
        )
        changes = [l for l in result.stdout.split("\n") if l.strip()]
        if changes:
            evidence.append(f"未提交变更: {len(changes)} 个文件")
        else:
            evidence.append("✅ 工作区干净")

        # 检查 tag
        result = subprocess.run(
            ["git", "tag", "--list", "v*"],
            capture_output=True, text=True, cwd=project_root,
            timeout=5,
        )
        tags = [t for t in result.stdout.split("\n") if t.strip()]
        if tags:
            evidence.append(f"基线标签: {', '.join(tags[:5])}")
        else:
            evidence.append("⚠️  未创建基线标签 (建议: git tag v1.0)")

    except Exception as e:
        evidence.append(f"⚠️  Git 信息获取失败: {e}")

    violations = []
    warnings = [e for e in evidence if "⚠️" in e or "❌" in e]
    for w in warnings:
        violations.append({"message": w, "severity": "HIGH"})

    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "evidence": evidence,
        "suggestion": "运行 git tag v1.0 创建基线标签" if any("基线标签" in e for e in evidence if "⚠️" in e) else None,
    }


def _run_layer_violation_operator(project_root: Path, target_files: list[str] | None = None) -> dict:
    """运行调用链分层校验"""
    try:
        from moat.verification.operators import LayerViolationOperator
        from moat.verification.types import VerificationContext

        op = LayerViolationOperator()
        ctx = VerificationContext(project_path=project_root)

        # 增量模式：只检查修改文件的调用链
        if target_files is not None:
            ctx.config["target_files"] = target_files

        result = op.verify(ctx)

        return {
            "passed": result.passed,
            "violations": [
                {"message": v.message, "severity": v.severity.value, "file": v.file_path, "line": v.line}
                for v in result.violations
            ],
            "evidence": [f"{k}: {v}" for k, v in result.evidence.items()],
            "suggestion": result.suggestions[0] if result.suggestions else None,
        }
    except Exception as e:
        return {"passed": False, "violations": [{"message": f"算子执行异常: {e}"}], "evidence": [], "suggestion": None}


def _run_leakage_detection_operator(project_root: Path, target_files: list[str] | None = None) -> dict:
    """运行泄露检测算子"""
    try:
        from moat.verification.operators import LeakageDetectionOperator
        from moat.verification.types import VerificationContext

        op = LeakageDetectionOperator()
        ctx = VerificationContext(project_path=project_root)

        # 增量模式：只检查修改的文件
        if target_files is not None:
            ctx.config["target_files"] = target_files

        result = op.verify(ctx)

        return {
            "passed": result.passed,
            "violations": [
                {"message": v.message, "severity": v.severity.value, "file": v.file_path, "line": v.line}
                for v in result.violations
            ],
            "evidence": [f"{k}: {v}" for k, v in result.evidence.items()],
            "suggestion": result.suggestions[0] if result.suggestions else None,
        }
    except Exception as e:
        return {"passed": False, "violations": [{"message": f"算子执行异常: {e}"}], "evidence": [], "suggestion": None}


# operator 名称 → 执行函数映射
OPERATOR_MAP = {
    "directory_responsibility": _run_directory_operator,
    "minimal_module_drill": _run_module_drill_operator,
    "api_response_spec": _run_api_spec_operator,
    "framework_usage": _run_framework_operator,
    "runtime_evidence": _run_runtime_operator,
    "truth_document": _run_truth_document_operator,
    "git_baseline": _run_git_baseline_operator,
    "layer_violation": _run_layer_violation_operator,
    "leakage_detection": _run_leakage_detection_operator,
}
