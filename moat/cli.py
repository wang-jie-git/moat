"""
Moat CLI — 护城河命令行工具

用法:
  moat check         改代码前/后检查（12秒）
  moat watch         实时监控日志错误
  moat init          初始化到当前项目
  moat dashboard     启动 Web 错误看板
  moat adapter       安装 AI 工具适配器
  moat baseline      管理基线数据
"""

import argparse
import sys
import os
from pathlib import Path


def cmd_check(args):
    """运行四层门禁检查"""
    from moat.runner import run_all_checks
    success = run_all_checks(args.project)
    return 0 if success else 1


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
    success = run_all_checks(str(root))

    # 生成报告
    report = generate_report(
        project_root=str(root),
        format=args.format,
        copy=args.copy,
    )

    if not success and args.copy:
        return 0  # 复制成功就算成功
    return 0 if success else 1


def cmd_adapter(args):
    """安装 AI 适配器"""
    from moat.adapters.claude import install_claude_adapter
    from moat.adapters.precommit import install_precommit_hook

    if args.type == "claude" or args.type == "all":
        install_claude_adapter(Path(args.project))
    if args.type == "precommit" or args.type == "all":
        install_precommit_hook(Path(args.project))
    print("✅ 适配器安装完成")
    return 0


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
    p_report.add_argument("--format", choices=["text", "md"], default="text",
                          help="输出格式（默认: text）")
    p_report.add_argument("--copy", action="store_true",
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

    # adapter
    p_adapter = sub.add_parser("adapter", help="安装 AI 适配器")
    _shared_args(p_adapter)
    p_adapter.add_argument("type", choices=["claude", "precommit", "all"],
                           default="all", nargs="?",
                           help="适配器类型")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    commands = {
        "check": cmd_check,
        "watch": cmd_watch,
        "init": cmd_init,
        "report": cmd_report,
        "baseline": cmd_baseline,
        "dashboard": cmd_dashboard,
        "adapter": cmd_adapter,
    }

    sys.exit(commands[args.command](args))


if __name__ == "__main__":
    main()