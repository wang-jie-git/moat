"""
Moat CLI — 护城河命令行工具

用法:
  moat check         改代码前/后检查（默认快速模式 < 5 秒）
  moat check --full  完整检查（所有文件，可能很慢）
  moat check --diff  增量检查（AST 对比 + 影响域分析 < 10 秒）
  moat watch         实时监控日志错误
  moat init          初始化到当前项目
  moat dashboard     启动 Web 错误看板
  moat adapter       安装 AI 工具适配器
  moat baseline      管理基线数据
  moat verify        架构验收
"""

import argparse
import sys
import os
from pathlib import Path


def cmd_check(args):
    """运行四层门禁检查

    支持三种模式：
    - moat check（默认）：快速检查（只检查修改的文件）< 5 秒
    - moat check --full：完整检查（所有文件 + 复杂规则）可能很慢
    - moat check --diff：增量检查（AST 对比 + 影响域分析）< 10 秒
    """
    from moat.runner import run_all_checks

    # 优先使用 --diff 模式（增量检查）
    if args.diff:
        # 增量检查模式（AST 对比 + 影响域分析）
        from moat.ast.diff import diff_project
        from moat.ast.builder import build_skeleton
        from moat.pain.scorer import calculate_total_pain

        root = Path(args.project)

        # 1. 构建骨架图
        print(f"\n🔨 构建项目骨架图...")
        skeleton = build_skeleton(str(root))
        print(f"   ✅ {skeleton.to_dict()['stats']['total_functions']} 个函数, "
              f"{skeleton.to_dict()['stats']['total_calls']} 个调用")

        # 2. 对比变更
        print(f"\n📊 分析代码变更...")
        changes = diff_project(str(root))

        if not changes:
            print(f"   ✅ 未检测到变更")
            return 0

        print(f"   ⚡ 检测到 {len(changes)} 个变更:\n")
        for change in changes:
            print(f"   {change['type']:10s} | {change['file']}:{change.get('line', '?')} "
                  f"::{change.get('function', '?')}")

        # 3. 影响域分析
        print(f"\n💡 影响域分析:")
        impacts = skeleton.analyze_impacts(changes, skeleton.to_dict())

        if impacts:
            for impact in impacts:
                change = impact.get("change", {})
                callers = impact.get("callers", [])
                risk_level = impact.get("risk_level", "unknown")
                print(f"\n   📍 {change.get('file', '?')}::{change.get('function', '?')}")
                print(f"      影响 {len(callers)} 个调用方:")
                for caller in callers[:5]:  # 最多显示 5 个
                    print(f"        - {caller}")
                if len(callers) > 5:
                    print(f"        ... 还有 {len(callers) - 5} 个")
                print(f"      风险等级: {risk_level}")
        else:
            print(f"   ✅ 未检测到直接影响")

        # 4. Pain Score 评估
        print(f"\n😣 痛觉评估:")
        errors_as_dict = [{"type": c["type"], "file": c["file"], "message": c.get("function", "")}
                          for c in changes]
        pain_result = calculate_total_pain(errors_as_dict)

        print(f"   总分: {pain_result['total_score']}/100 ({pain_result['overall_level']})")
        print(f"   建议: {pain_result['recommended_action']}")

        # 5. 返回建议
        if pain_result['overall_level'] in ('CRITICAL', 'HIGH'):
            print(f"\n⚠️  建议: 运行完整检查以确保没有引入问题")
            print(f"   moat check --full")
            return 1
        else:
            print(f"\n✅ 变更风险较低，但仍建议运行完整检查")
            return 0

    # 根据参数选择检查模式
    elif args.full:
        # 完整检查模式
        print(f"\n🔍 完整检查模式（所有文件 + 复杂规则）...")

        # 加载配置并添加 skip_architecture
        from moat.runner import _load_config
        config = _load_config(Path(args.project))
        if args.skip_architecture:
            config["skip_architecture"] = True

        # 这里需要临时修改 config，简化处理：通过环境变量传递
        import os
        if args.skip_architecture:
            os.environ["MOAT_SKIP_ARCHITECTURE"] = "true"

        # 战术建议 1：异步触发优化检查
        enable_optimization = getattr(args, 'optimize', False)
        result = run_all_checks(args.project, mode="full", enable_optimization=enable_optimization)

        if enable_optimization:
            print(f"\n⚡ 已启用代码优化检查（Ponytail 集成）")
        return 0 if result.is_success() else 1

    elif args.quick:
        # 快速检查模式（默认）
        print(f"\n⚡ 快速检查模式（只检查修改的文件）...")
        enable_optimization = getattr(args, 'optimize', False)
        result = run_all_checks(args.project, mode="quick", enable_optimization=enable_optimization)

        if enable_optimization:
            print(f"\n⚡ 已启用代码优化检查（Ponytail 集成）")
        return 0 if result.is_success() else 1

    else:
        # 默认：快速检查模式
        enable_optimization = getattr(args, 'optimize', False)
        result = run_all_checks(args.project, mode="quick", enable_optimization=enable_optimization)
        return 0 if result.is_success() else 1


def cmd_watch(args):
    """实时监控日志错误"""
    from moat.monitor import start_monitor
    log_path = args.log or _detect_log_path(args.project)
    if not log_path:
        print("❌ 找不到日志文件，请用 --log 指定路径")
        return 1
    start_monitor(Path(log_path), args.color, args.filter)


def cmd_init(args):
    """初始化 Moat 到当前项目"""
    from moat.discovery import init_project
    init_project(Path(args.project), interactive=not args.no_interactive)
    return 0


def cmd_baseline(args):
    """管理基线"""
    from moat.baseline import BaselineManager
    bm = BaselineManager(Path(args.project))
    if args.action == "save":
        bm.save()
        print(f"✅ 基线已保存 ({bm.baseline_path})")
    elif args.action == "show":
        bm.show()
    elif args.action == "diff":
        bm.diff()
    return 0


def cmd_dashboard(args):
    """启动 Web 看板"""
    from moat.dashboard.server import start_dashboard
    start_dashboard(
        project=Path(args.project),
        host=args.host,
        port=args.port,
        log_path=args.log or _detect_log_path(args.project),
    )
    return 0


def cmd_gatekeeper(args) -> int:
    """Gatekeeper守门"""
    from moat.gatekeeper.cli import cmd_gatekeeper
    return cmd_gatekeeper(args)


def cmd_verify(args) -> int:
    """架构验收"""
    from moat.verification.verify_cli import cmd_verify
    return cmd_verify(args)


def cmd_report(args):
    """生成检查报告"""
    from moat.report import generate_report
    from moat.runner import MoatResult

    root = Path(args.project)

    # 运行检查并获取结果
    from moat.runner import run_all_checks
    result = MoatResult()

    # 临时替换 runner 的打印函数来捕获结果
    import io
    from contextlib import redirect_stdout

    # 简单起见，直接运行检查并生成报告
    # 实际应该修改 runner 返回结果
    result = run_all_checks(str(root))

    # 生成报告
    report = generate_report(
        project_root=str(root),
        format=args.format,
        copy=args.copy,
    )

    if not result.is_success() and args.copy:
        return 0  # 复制成功就算成功
    return 0 if result.is_success() else 1


def cmd_architecture(args):
    """生成架构健康报告（L2）"""
    from moat.architecture_report import generate_architecture_report

    root = Path(args.project)

    # 生成报告
    report = generate_architecture_report(
        project_root=str(root),
        format=args.format,
        copy=args.copy,
    )

    print(report)
    return 0


def cmd_adapter(args):
    """安装 AI 适配器"""
    from moat.adapters import install_claude_adapter, install_precommit_hook

    if args.type == "claude" or args.type == "all":
        install_claude_adapter(Path(args.project))
    if args.type == "precommit" or args.type == "all":
        install_precommit_hook(Path(args.project))
    print("✅ 适配器安装完成")
    return 0


def cmd_fix(args):
    """AI 辅助修复"""
    from moat.fixer import generate_fix_report
    from moat.runner import run_all_checks

    root = Path(args.project)

    # 先运行检查获取错误列表
    print(f"\n🔍 运行检查以获取错误列表...")
    result = run_all_checks(str(root))

    if result.is_success():
        print("\n✅ 未发现错误，无需修复")
        return 0

    # 使用检查结果中的错误列表
    print(f"\n🔧 生成修复建议...")

    # 生成修复报告（传入错误列表）
    report = generate_fix_report(
        project_root=str(root),
        errors=result.errors,
        dry_run=not args.no_dry_run,
        format=args.format,
    )

    print(report)

    if args.copy:
        try:
            import pyperclip
            pyperclip.copy(report)
            print("\n✅ 报告已复制到剪贴板")
        except ImportError:
            print("\n⚠️  未安装 pyperclip，跳过复制")

    return 0


def cmd_sidecar(args):
    """Sidecar 守护进程管理"""
    from moat.sidecar.daemon import SidecarDaemon

    root = Path(args.project)
    daemon = SidecarDaemon(root)

    if args.action == "start":
        return daemon.start(foreground=args.foreground)
    elif args.action == "stop":
        return daemon.stop()
    elif args.action == "restart":
        return daemon.restart()
    elif args.action == "status":
        print(daemon.status())
        return 0
    return 1


def cmd_rules_explain(args):
    """解释规则详情

    让用户在 3 秒内理解：
    1. 为什么报错
    2. 如何修复
    3. 如何关闭此检查
    """
    rule_id = args.rule_id.upper()

    # 规则库（应该从配置文件读取，这里简化处理）
    rules_db = {
        # 安全规则
        "SQL-001": {
            "name": "SQL 注入检测",
            "description": "检测 SQL 字符串拼接导致的注入风险",
            "severity": "CRITICAL",
            "why": "SQL 注入是 OWASP Top 10 第一安全风险，可能导致数据泄露、数据篡改甚至服务器被控制",
            "fix": "使用参数化查询：cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
            "disable": '在 .moat/config.json 中设置 {"rules": {"sql_injection": false}}',
        },
        "API-001": {
            "name": "API 缺少鉴权",
            "description": "检测 API 路由缺少鉴权装饰器",
            "severity": "CRITICAL",
            "why": "未鉴权的 API 可能导致未授权访问，造成数据泄露",
            "fix": "添加鉴权装饰器：@login_required 或 @require_permission('admin')",
            "disable": '在 .moat/config.json 中设置 {"rules": {"api_auth": false}}',
        },
        # 复杂度规则
        "COMPLEX-001": {
            "name": "圈复杂度超标",
            "description": "函数圈复杂度超过阈值（默认 10）",
            "severity": "MEDIUM",
            "why": "高复杂度函数难以理解和维护，Bug 率随复杂度指数增长",
            "fix": "将复杂函数拆分为多个小函数（每个 < 10 复杂度）",
            "disable": '在 .moat/config.json 中设置 {"optimization": {"max_complexity": 15}}',
        },
        "COMPLEX-002": {
            "name": "函数过长",
            "description": "函数长度超过阈值（默认 50 行）",
            "severity": "LOW",
            "why": "长函数难以理解、测试和维护",
            "fix": "按逻辑块拆分函数，提取辅助函数",
            "disable": '在 .moat/config.json 中设置 {"optimization": {"max_function_length": 80}}',
        },
        "COMPLEX-003": {
            "name": "认知复杂度超标",
            "description": "函数认知复杂度超过阈值（默认 15）",
            "severity": "MEDIUM",
            "why": "高认知复杂度意味着代码难以被人理解，增加维护成本",
            "fix": "减少嵌套层级，使用卫语句（Guard Clauses），提取复杂逻辑到独立函数",
            "disable": '在 .moat/config.json 中设置 {"optimization": {"max_cognitive_complexity": 20}}',
        },
        # YAGNI 规则
        "YAGNI-001": {
            "name": "未使用的导入",
            "description": "检测未使用的 import 语句",
            "severity": "LOW",
            "why": "未使用的导入增加依赖负担，降低代码可读性",
            "fix": "删除未使用的导入，或使用工具（如 autoflake）自动清理",
            "disable": '在 .moat/config.json 中设置 {"optimization": {"check_yagni": false}}',
        },
        "YAGNI-002": {
            "name": "未处理的 TODO/FIXME",
            "description": "检测过多的 TODO/FIXME 注释",
            "severity": "LOW",
            "why": "过多的 TODO 表明代码未完成或技术债积累",
            "fix": "实现 TODO 对应的功能，或删除已过时的 TODO",
            "disable": '在 .moat/config.json 中设置 {"optimization": {"check_yagni": false}}',
        },
        "YAGNI-004": {
            "name": "死代码检测",
            "description": "检测无法访问的代码（return/raise 后）",
            "severity": "MEDIUM",
            "why": "死代码增加代码体积，误导读者",
            "fix": "删除 return/raise 后的代码，或将 cleanup 逻辑移到 finally",
            "disable": '在 .moat/config.json 中设置 {"optimization": {"check_dead_code": false}}',
        },
    }

    if rule_id not in rules_db:
        print(f"❌ 未知规则: {rule_id}")
        print(f"\n💡 可用规则:")
        for rid, rinfo in sorted(rules_db.items()):
            print(f"  {rid:12s} - {rinfo['name']}")
        print(f"\n更多帮助: moat rules list")
        return 1

    rule = rules_db[rule_id]

    # 输出格式化说明
    print(f"\n{'='*60}")
    print(f"  📖 规则详情: {rule_id}")
    print(f"{'='*60}\n")

    print(f"**名称**: {rule['name']}")
    print(f"**严重性**: {rule['severity']}")
    print(f"**描述**: {rule['description']}\n")

    print(f"**为什么报错**:")
    print(f"  {rule['why']}\n")

    print(f"**修复方法**:")
    print(f"  {rule['fix']}\n")

    print(f"**关闭此检查**:")
    print(f"  {rule['disable']}\n")

    print(f"{'='*60}")
    print(f"  💡 提示: 如果这是误报，请考虑关闭此规则")
    print(f"{'='*60}\n")

    return 0

def cmd_test(args) -> int:
    """AI 测试生成（已废弃，使用 moat immune）"""
    from moat.ai_test.cli import cmd_test
    return cmd_test(args)


def cmd_immune(args) -> int:
    """Moat Immune - AI 工程化测试体系"""
    from moat.immune.cli import cmd_immune
    return cmd_immune(args)


def cmd_evolution(args):
    """进化指标管理"""
    from moat.evolution_cli import cmd_evolution
    return cmd_evolution(args)


def _detect_log_path(project: str) -> str | None:
    """自动检测项目日志路径"""
    candidates = [
        "logs/backend.log",
        "log/backend.log",
        "logs/app.log",
        "log/app.log",
        "var/log/app.log",
    ]
    for c in candidates:
        p = Path(project) / c
        if p.exists():
            return str(p)
    return None


def _shared_args(parser: argparse.ArgumentParser):
    """添加共享参数到子命令"""
    parser.add_argument("--project", default=".",
                        help="项目根目录 (默认: 当前目录)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="详细输出")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="moat",
        description="Moat — AI 编码护城河。防止 AI 改代码时搞坏系统。",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # check
    p_check = sub.add_parser("check", help="运行四层门禁检查")
    _shared_args(p_check)
    p_check.add_argument("--diff", action="store_true",
                         help="增量检查模式（对比 Git 变更 + AST 影响域分析）")
    p_check.add_argument("--quick", action="store_true",
                         help="快速检查模式（只检查修改的文件，默认）")
    p_check.add_argument("--full", action="store_true",
                         help="完整检查模式（所有文件 + 复杂规则，可能很慢）")
    p_check.add_argument("--legacy", action="store_true",
                         help="使用旧版 L1 检查（向后兼容）")
    p_check.add_argument("--skip-architecture", action="store_true",
                         help="跳过 L2 架构检查（提升性能，完整模式有效）")
    p_check.add_argument("--optimize", action="store_true",
                         help="启用代码优化检查（Ponytail 集成：YAGNI、复杂度、标准库优先）")

    # watch
    p_watch = sub.add_parser("watch", help="实时监控日志错误")
    _shared_args(p_watch)
    p_watch.add_argument("--log", "-l", help="日志文件路径")
    p_watch.add_argument("--no-color", dest="color", action="store_false",
                         help="禁用颜色输出")
    p_watch.add_argument("--filter", "-f", default="ERROR|Traceback|Process exited|Bridge died",
                         help="过滤模式 (默认: 错误/异常)")

    # init
    p_init = sub.add_parser("init", help="初始化 Moat 到当前项目")
    _shared_args(p_init)
    p_init.add_argument("--no-interactive", action="store_true",
                        help="非交互模式（使用自动检测配置）")

    # report
    p_report = sub.add_parser("report", help="生成检查报告")
    _shared_args(p_report)
    p_report.add_argument("--format", choices=["text", "md", "json"], default="text",
                          help="输出格式（默认: text）")
    p_report.add_argument("--copy", action="store_true",
                          help="复制报告到剪贴板")

    # 🆕 rules - 规则管理
    p_rules = sub.add_parser("rules", help="规则管理")
    p_rules_sub = p_rules.add_subparsers(dest="rules_action", help="规则操作")

    # rules explain
    p_rules_explain = p_rules_sub.add_parser("explain", help="解释规则详情（为什么报错/如何修复/如何关闭）")
    p_rules_explain.add_argument("rule_id", help="规则 ID（如 SQL-001, COMPLEX-001）")

    # 🆕 architecture - 架构健康报告
    p_arch = sub.add_parser("architecture", help="生成架构健康报告（L2）")
    _shared_args(p_arch)
    p_arch.add_argument("--format", choices=["text", "md", "json"], default="text",
                        help="输出格式（默认: text）")
    p_arch.add_argument("--copy", action="store_true",
                        help="复制报告到剪贴板")

    # baseline
    p_baseline = sub.add_parser("baseline", help="管理基线")
    _shared_args(p_baseline)
    p_baseline.add_argument("action", choices=["save", "show", "diff"],
                            help="基线操作")

    # dashboard
    p_dash = sub.add_parser("dashboard", help="启动 Web 错误看板")
    _shared_args(p_dash)
    p_dash.add_argument("--host", default="127.0.0.1", help="监听地址")
    p_dash.add_argument("--port", "-p", type=int, default=9876, help="监听端口")
    p_dash.add_argument("--log", "-l", help="日志文件路径")

    # fix
    p_fix = sub.add_parser("fix", help="AI 辅助修复")
    _shared_args(p_fix)
    p_fix.add_argument("--no-dry-run", action="store_true",
                       help="实际修复（默认为演练模式）")
    p_fix.add_argument("--format", choices=["text", "md", "json"], default="text",
                       help="输出格式（默认: text）")
    p_fix.add_argument("--copy", action="store_true",
                       help="复制报告到剪贴板")

    # sidecar
    p_sidecar = sub.add_parser("sidecar", help="Sidecar 实时感知守护进程")
    _shared_args(p_sidecar)
    p_sidecar.add_argument("action", choices=["start", "stop", "restart", "status"],
                           help="操作")
    p_sidecar.add_argument("--foreground", action="store_true",
                           help="前台运行（仅 start）")

    # adapter
    p_adapter = sub.add_parser("adapter", help="安装 AI 适配器")
    _shared_args(p_adapter)
    p_adapter.add_argument("type", choices=["claude", "precommit", "all"],
                           default="all", nargs="?",
                           help="适配器类型")

    # evolution
    p_evolution = sub.add_parser("evolution", help="进化指标管理")
    _shared_args(p_evolution)
    p_evolution.add_argument("action", choices=["report", "adjust", "record"],
                            help="操作")
    p_evolution.add_argument("--window", type=int, default=24,
                            help="报告时间窗口（小时，默认: 24）")
    p_evolution.add_argument("--format", choices=["text", "json"], default="text",
                            help="输出格式（默认: text）")
    p_evolution.add_argument("--auto", action="store_true",
                            help="自动调整配置")
    p_evolution.add_argument("--pain-threshold", type=int,
                            help="调整 Pain Score 阈值")
    p_evolution.add_argument("--false-positive-tolerance", type=int,
                            help="调整误报容忍度")
    p_evolution.add_argument("--metric-type", choices=[
        "refactor_success", "performance_improvement", "bug_fix_time",
        "false_positive_rate", "dev_velocity"
    ], help="手动记录指标类型（仅 record）")
    p_evolution.add_argument("--value", type=float,
                            help="指标值（仅 record）")

    # verify
    p_verify = sub.add_parser("verify", help="架构验收")
    _shared_args(p_verify)
    p_verify.add_argument("--all", action="store_true", default=True,
                          help="执行完整验收（所有算子）")
    p_verify.add_argument("--operator", "-o",
                          help="执行单个算子（如: directory_responsibility）")
    p_verify.add_argument("--json", action="store_true",
                          help="JSON输出")
    p_verify.add_argument("--fail-on-score", type=int, metavar="SCORE",
                          help="架构评分低于此阈值则失败")

    # gatekeeper
    from moat.gatekeeper.cli import add_gatekeeper_parser
    add_gatekeeper_parser(sub)

    # immune (Moat Immune - AI 工程化测试体系)
    from moat.immune.cli import add_immune_parser
    add_immune_parser(sub)

    # test (已废弃，使用 moat immune unit)
    from moat.ai_test.cli import add_test_parser
    add_test_parser(sub)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    commands = {
        "check": cmd_check,
        "watch": cmd_watch,
        "init": cmd_init,
        "report": cmd_report,
        "rules": lambda args: cmd_rules_explain(args) if hasattr(args, 'rule_id') else cmd_rules_explain(args),
        "architecture": cmd_architecture,
        "fix": cmd_fix,
        "baseline": cmd_baseline,
        "dashboard": cmd_dashboard,
        "sidecar": cmd_sidecar,
        "evolution": cmd_evolution,
        "adapter": cmd_adapter,
        "verify": cmd_verify,
        "gatekeeper": cmd_gatekeeper,
        "immune": cmd_immune,
        "test": cmd_test,
    }

    sys.exit(commands[args.command](args))


if __name__ == "__main__":
    main()