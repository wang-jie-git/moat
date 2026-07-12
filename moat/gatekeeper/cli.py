"""
Gatekeeper CLI 命令
"""

import argparse
import sys
from pathlib import Path

from .checker import ArchitectureGatekeeper
from .types import GatekeeperConfig


def cmd_gatekeeper(args) -> int:
    """
    Gatekeeper 守门命令

    用法:
        moat gatekeeper start              # 启动守护进程
        moat gatekeeper stop               # 停止守护进程
        moat gatekeeper status             # 查看状态
        moat gatekeeper check --file <path> # 检查单个文件
        moat gatekeeper rules              # 列出所有规则
    """
    if args.action == "start":
        return _cmd_start(args)
    elif args.action == "stop":
        return _cmd_stop(args)
    elif args.action == "status":
        return _cmd_status(args)
    elif args.action == "check":
        return _cmd_check(args)
    elif args.action == "rules":
        return _cmd_rules(args)
    else:
        print(f"❌ 未知操作: {args.action}")
        return 1


def _cmd_start(args) -> int:
    """启动守护进程"""
    print("🚀 启动 Gatekeeper 守护进程...")
    print("   功能开发中，敬请期待")
    return 0


def _cmd_stop(args) -> int:
    """停止守护进程"""
    print("🛑 停止 Gatekeeper 守护进程...")
    print("   功能开发中，敬请期待")
    return 0


def _cmd_status(args) -> int:
    """查看状态"""
    print("📊 Gatekeeper 状态")
    print("   功能开发中，敬请期待")
    return 0


def _cmd_check(args) -> int:
    """检查单个文件"""
    # Bug 修复：检查必需的参数
    if not args.file:
        print("❌ 错误：必须指定 --file 参数")
        print("用法: moat gatekeeper check --file <文件路径>")
        return 1

    project_path = Path(args.project).resolve() if args.project else Path.cwd().resolve()
    file_path = Path(args.file).resolve()

    if not file_path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return 1

    # 检查文件是否在项目内
    try:
        file_path.relative_to(project_path)
    except ValueError:
        print(f"❌ 文件不在项目内: {file_path}")
        return 1

    # 读取文件内容
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return 1

    # 执行检查
    gatekeeper = ArchitectureGatekeeper(project_path)
    result = gatekeeper.check_file(str(file_path), content)

    # 显示结果
    print(f"\n🔍 检查文件: {file_path.relative_to(project_path)}")
    print(f"   状态: {'✅ 通过' if result.passed else '❌ 未通过'}")
    print(f"   执行时间: {result.execution_time:.1f}ms")

    if result.violations:
        print(f"\n违规 ({len(result.violations)}):")
        print(gatekeeper.format_violations(result))
    else:
        print(f"\n✅ 未发现违规")

    if result.ignored_violations:
        print(f"\n⚪ 已豁免: {len(result.ignored_violations)} 个")

    return 0 if result.passed else 1


def _cmd_rules(args) -> int:
    """列出所有规则"""
    from .rules import RuleEngine

    engine = RuleEngine()
    rules = engine.list_rules()

    print("\n📋 架构守门规则列表:\n")

    for i, rule in enumerate(rules, 1):
        print(f"{i}. [{rule['rule_id']}] {rule['name']}")
        print(f"   {rule['description']}")
        print(f"   严重程度: {rule['severity']}")
        print()

    return 0


def add_gatekeeper_parser(sub) -> None:
    """添加gatekeeper命令到argparse"""
    p_gatekeeper = sub.add_parser("gatekeeper", help="架构守门系统")
    p_gatekeeper.add_argument("action", choices=["start", "stop", "status", "check", "rules"],
                              help="操作")
    p_gatekeeper.add_argument("--file", "-f", help="要检查的文件路径（仅check）")
    p_gatekeeper.add_argument("--project", default=".", help="项目根目录")
