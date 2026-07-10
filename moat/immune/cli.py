"""
Moat Immune CLI — AI 工程化测试体系命令

用法:
    moat immune unit --file services/user.py         # 生成单元测试
    moat immune unit --scope missing                 # 生成所有缺失测试
    moat immune contract --api=openapi.json          # 生成契约测试
    moat immune bdd --requirement=prd.md             # 生成 BDD 测试
    moat immune run                                   # 运行完整测试流水线
    moat immune coverage                              # 检查测试覆盖率

兼容性:
    moat test generate --file services/user.py       # 已废弃，使用 moat immune unit
"""

import argparse
from pathlib import Path


def cmd_immune(args) -> int:
    """Moat Immune 命令入口"""
    if args.action == "unit":
        return _cmd_unit(args)
    elif args.action == "contract":
        return _cmd_contract(args)
    elif args.action == "bdd":
        return _cmd_bdd(args)
    elif args.action == "visual":
        return _cmd_visual(args)
    elif args.action == "run":
        return _cmd_run(args)
    elif args.action == "coverage":
        return _cmd_coverage(args)
    else:
        print(f"❌ 未知操作: {args.action}")
        return 1


def _cmd_unit(args) -> int:
    """生成单元测试"""
    from .unit.generator import AITestGateway

    gateway = AITestGateway()

    if not gateway.enabled:
        print("❌ AI Test Gateway 未启用")
        print("   请设置环境变量: export ANTHROPIC_API_KEY=your_key")
        return 1

    if args.file:
        # 为指定文件生成测试
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ 文件不存在: {file_path}")
            return 1

        print(f"\n🤖 AI 生成单元测试: {file_path.name}")

        content = file_path.read_text(encoding="utf-8")
        test_code = gateway.generate_unit_test(str(file_path), content)

        if test_code:
            print(f"\n✅ 单元测试生成成功")
            return 0
        else:
            print(f"\n❌ 单元测试生成失败")
            return 1

    elif args.scope == "missing":
        # 为所有缺失测试的文件生成测试
        print("\n🔍 扫描缺失测试的文件...")
        print("   功能开发中，敬请期待")
        return 0

    else:
        print("❌ 请指定 --file 或 --scope")
        return 1


def _cmd_contract(args) -> int:
    """生成契约测试"""
    print("\n📋 契约测试生成")
    print("   功能开发中，敬请期待")
    return 0


def _cmd_bdd(args) -> int:
    """生成 BDD 测试"""
    print("\n🎯 BDD 测试生成")
    print("   功能开发中，敬请期待")
    return 0


def _cmd_visual(args) -> int:
    """视觉测试"""
    print("\n👁️  AI 视觉测试")
    print("   功能开发中，敬请期待")
    return 0


def _cmd_run(args) -> int:
    """运行完整测试流水线"""
    print("\n🚀 运行 AI 测试流水线")
    print("   功能开发中，敬请期待")
    return 0


def _cmd_coverage(args) -> int:
    """检查测试覆盖率"""
    print("\n📊 测试覆盖率检查")
    print("   功能开发中，敬请期待")
    return 0


def add_immune_parser(sub) -> None:
    """添加 immune 命令到 argparse"""
    p_immune = sub.add_parser("immune", help="Moat Immune - AI 工程化测试体系")
    p_immune.add_argument("action", choices=[
        "unit", "contract", "bdd", "visual", "run", "coverage"
    ], help="操作")

    # 单元测试选项
    p_immune.add_argument("--file", "-f", help="要生成测试的文件路径（仅 unit）")
    p_immune.add_argument("--scope", choices=["missing", "all"],
                          help="生成范围（仅 unit）")

    # 契约测试选项
    p_immune.add_argument("--api", help="API 规范文件路径（仅 contract）")

    # BDD 测试选项
    p_immune.add_argument("--requirement", help="需求文档路径（仅 bdd）")

    # 视觉测试选项
    p_immune.add_argument("--page", help="要测试的页面路径（仅 visual）")
