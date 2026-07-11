#!/usr/bin/env python3
"""
Moat 安装引导脚本

交互式引导新用户完成 Moat 的安装和配置。

用法:
    python3 setup.py
"""
from pathlib import Path
import subprocess
import sys


def print_header(title: str) -> None:
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_step(step: int, title: str) -> None:
    """打印步骤"""
    print(f"\n{'─' * 60}")
    print(f"  步骤 {step}: {title}")
    print(f"{'─' * 60}")


def run_command(cmd: str, description: str = "") -> bool:
    """运行命令并返回是否成功"""
    if description:
        print(f"\n▶️  {description}")
    print(f"   $ {cmd}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )

        if result.stdout:
            print(result.stdout)

        if result.returncode != 0:
            print(f"❌ 命令执行失败（退出码: {result.returncode}）")
            if result.stderr:
                print(f"   错误: {result.stderr[:200]}")
            return False

        print("✅ 成功")
        return True

    except Exception as e:
        print(f"❌ 异常: {e}")
        return False


def check_pipx() -> bool:
    """检查 pipx 是否已安装"""
    print_step(1, "检查 pipx 安装状态")

    result = subprocess.run(
        "which pipx",
        shell=True,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"✅ pipx 已安装: {result.stdout.strip()}")
        return True
    else:
        print("❌ pipx 未安装")
        print("\n推荐安装 pipx（自动管理虚拟环境）:")
        print("  brew install pipx    # macOS")
        print("  pip install pipx     # 通用")

        response = input("\n是否现在安装 pipx？(y/N): ").strip().lower()
        if response == 'y':
            return run_command("brew install pipx", "安装 pipx")
        else:
            print("⚠️  跳过 pipx，将使用 pip 安装")
            return False


def install_moat(use_pipx: bool) -> bool:
    """安装 Moat"""
    print_step(2, "安装 Moat")

    if use_pipx:
        return run_command("pipx install moat-ai", "使用 pipx 安装 Moat")
    else:
        return run_command("pip3 install --user moat-ai", "使用 pip 安装 Moat")


def verify_installation() -> bool:
    """验证安装"""
    print_step(3, "验证安装")

    return run_command("moat --version", "检查 Moat 版本")


def init_project() -> bool:
    """初始化项目"""
    print_step(4, "初始化项目")

    # 获取项目路径
    project_path = input("\n请输入你的项目路径（或直接回车使用当前目录）: ").strip()

    if project_path:
        project_path = Path(project_path).resolve()
    else:
        project_path = Path.cwd()

    print(f"\n项目路径: {project_path}")

    # 检查是否是 git 仓库
    if not (project_path / ".git").exists():
        print("⚠️  警告: 当前目录不是 git 仓库")
        response = input("是否继续？(y/N): ").strip().lower()
        if response != 'y':
            return False

    # 运行 moat init
    os_cmd = f"cd {project_path} && moat init"
    return run_command(os_cmd, f"初始化项目: {project_path}")


def create_baseline() -> bool:
    """创建基线"""
    print_step(5, "创建基线")

    print("\n基线 = 当前代码库的'快照'")
    print("Moat 会用基线对比后续代码变更")

    response = input("\n是否现在创建基线？(Y/n): ").strip().lower()

    if response == 'n':
        print("⚠️  跳过基线创建")
        print("   记住以后要运行: moat baseline save")
        return True

    return run_command("moat baseline save", "创建基线")


def show_next_steps() -> None:
    """显示下一步操作"""
    print_header("🎉 安装完成！")

    print("\n下一步操作:")
    print("\n1️⃣  日常开发:")
    print("   moat check                 # 改代码前后检查")
    print("   moat check --full          # 提交前完整检查")

    print("\n2️⃣  架构健康:")
    print("   moat architecture          # 查看架构健康报告")

    print("\n3️⃣  基线管理:")
    print("   moat baseline diff         # 对比基线差异")
    print("   moat baseline save         # 更新基线")

    print("\n4️⃣  AI 集成（可选）:")
    print("   moat adapter claude        # 集成 Claude Code")
    print("   moat adapter precommit     # 安装 git hook")

    print("\n5️⃣  查看帮助:")
    print("   moat --help                # 查看所有命令")
    print("   moat check --help          # 查看 check 命令")

    print("\n📚 文档:")
    print("   cat SETUP.md               # 查看详细指南")
    print("   cat README.md              # 查看完整文档")

    print("\n💡 核心工作流:")
    print("   改代码前 → moat check")
    print("   改代码后 → moat check")
    print("   两次都通过 → 提交代码")

    print("\n" + "=" * 60)
    print("  You own the code, you own the guard. 🛡️")
    print("=" * 60)


def main() -> None:
    """主函数"""
    print_header("🚀 Moat 安装引导")

    print("\n欢迎使用 Moat！")
    print("Moat 是 AI 编码守门员，防止 AI 改代码时搞坏系统。")
    print("\n这个脚本会引导你完成安装和配置。")

    # 步骤 1: 检查 pipx
    has_pipx = check_pipx()

    # 步骤 2: 安装 Moat
    if not install_moat(has_pipx):
        print("\n❌ Moat 安装失败")
        sys.exit(1)

    # 步骤 3: 验证安装
    if not verify_installation():
        print("\n❌ 安装验证失败")
        sys.exit(1)

    # 步骤 4: 初始化项目
    if not init_project():
        print("\n⚠️  项目初始化失败，但你仍然可以使用 Moat")
        print("   以后可以在项目目录运行: moat init")

    # 步骤 5: 创建基线
    create_baseline()

    # 显示下一步
    show_next_steps()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  安装被用户取消")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        sys.exit(1)
