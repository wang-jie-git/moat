"""
AI Test CLI — AI 测试生成命令

用法:
    moat test generate --file services/user.py    # 为指定文件生成测试
    moat test generate --scope missing            # 为所有缺失测试的文件生成
    moat test coverage                             # 检查测试覆盖率
"""

import argparse
from pathlib import Path


def cmd_test(args) -> int:
    """AI 测试命令入口"""
    if args.action == "generate":
        return _cmd_generate(args)
    elif args.action == "coverage":
        return _cmd_coverage(args)
    else:
        print(f"❌ 未知操作: {args.action}")
        return 1


def _cmd_generate(args) -> int:
    """生成测试"""
    from ..gatekeeper.ai_test.gateway import AITestGateway

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

        print(f"\n🤖 AI 生成测试: {file_path.name}")
        print(f"   类型: {args.type}")

        content = file_path.read_text(encoding="utf-8")
        test_code = gateway.generate_unit_test(str(file_path), content)

        if test_code:
            print(f"\n✅ 测试生成成功")
            return 0
        else:
            print(f"\n❌ 测试生成失败")
            return 1

    elif args.scope == "missing":
        # 为所有缺失测试的文件生成测试
        print("\n🔍 扫描缺失测试的文件...")
        print("   功能开发中，敬请期待")
        return 0

    else:
        print("❌ 请指定 --file 或 --scope")
        return 1


def _cmd_coverage(args) -> int:
    """检查测试覆盖率"""
    print("\n📊 测试覆盖率检查")
    print("   功能开发中，敬请期待")
    return 0


def add_test_parser(sub) -> None:
    """添加 test 命令到 argparse"""
    p_test = sub.add_parser("test", help="AI 测试生成")
    p_test.add_argument("action", choices=["generate", "coverage"],
                        help="操作")
    p_test.add_argument("--type", choices=["unit", "integration", "e2e", "bdd"],
                        default="unit", help="测试类型（默认: unit）")
    p_test.add_argument("--file", "-f", help="要生成测试的文件路径")
    p_test.add_argument("--scope", choices=["missing", "all"],
                        help="生成范围")
