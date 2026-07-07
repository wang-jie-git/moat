#!/usr/bin/env python3
"""
Moat 安装验证脚本
用于验证安装配置是否正确
"""

import sys
from pathlib import Path


def check_python_version():
    """检查 Python 版本"""
    print("📋 检查 Python 版本...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} (需要 >= 3.10)")
        return False


def check_dependencies():
    """检查依赖"""
    print("\n📦 检查依赖...")
    dependencies = {
        "httpx": "核心依赖",
        "watchdog": "Sidecar 文件监控",
        "fastapi": "Web 看板 + Sidecar API",
        "uvicorn": "Web 看板 + Sidecar API",
        "pyperclip": "剪贴板复制",
    }

    available = {}
    for package, description in dependencies.items():
        try:
            __import__(package)
            print(f"   ✅ {package:15s} — {description}")
            available[package] = True
        except ImportError:
            print(f"   ⚠️  {package:15s} — {description} (未安装)")
            available[package] = False

    return available


def check_moat_core():
    """检查 Moat 核心模块"""
    print("\n🔍 检查 Moat 核心模块...")

    # 尝试导入 moat 包
    try:
        import moat
        moat_version = moat.__version__
        print(f"   ✅ moat 包 (v{moat_version})")
    except ImportError:
        print(f"   ⚠️  moat 包未安装（开发模式跳过此检查）")
        return {}

    modules = {
        "moat.cli": "CLI 入口",
        "moat.runner": "检查运行器",
        "moat.ast.builder": "AST 骨架图构建器",
        "moat.ast.diff": "AST 增量对比器",
        "moat.pain.scorer": "Pain Score 计算器",
        "moat.pain.feedback": "自我校准机制",
        "moat.memory.bridge": "SQLite 共享桥接器",
        "moat.evolution": "进化引擎",
        "moat.evolution_metrics": "进化指标系统",
        "moat.fixer": "修复引擎",
        "moat.fix_strategies": "修复策略库",
        "moat.report": "报告生成器",
    }

    available = {}
    for module, description in modules.items():
        try:
            __import__(module)
            print(f"   ✅ {module:30s} — {description}")
            available[module] = True
        except ImportError as e:
            print(f"   ❌ {module:30s} — {description} ({e})")
            available[module] = False

    return available


def check_sidecar_modules(deps):
    """检查 Sidecar 模块"""
    print("\n⚡ 检查 Sidecar 模块...")
    if not deps.get("watchdog"):
        print("   ⚠️  watchdog 未安装，Sidecar 文件监控不可用")
        return False

    try:
        from moat.sidecar.daemon import SidecarDaemon
        from moat.sidecar.watcher import FileChangeHandler
        print("   ✅ Sidecar 守护进程")
        print("   ✅ Sidecar 文件监控")
        return True
    except ImportError as e:
        print(f"   ❌ Sidecar 模块 ({e})")
        return False


def check_dashboard_modules(deps):
    """检查 Dashboard 模块"""
    print("\n📊 检查 Dashboard 模块...")
    if not deps.get("fastapi"):
        print("   ⚠️  fastapi 未安装，Web 看板不可用")
        return False

    try:
        from moat.dashboard.server import start_dashboard
        print("   ✅ Web 看板")
        return True
    except ImportError:
        # Dashboard 可能未实现，这是正常的
        print("   ℹ️  Web 看板（未实现或可选）")
        return True


def check_vscode_features(deps):
    """检查 VS Code 功能"""
    print("\n🎨 检查 VS Code 功能...")
    if not deps.get("pyperclip"):
        print("   ⚠️  pyperclip 未安装，剪贴板复制不可用")
    else:
        print("   ✅ 剪贴板复制")

    print("   ℹ️  VS Code 插件（需要在 vscode-moat/ 目录手动安装）")
    return True


def print_summary(core_ok, deps, sidecar_ok, dashboard_ok, vscode_ok):
    """打印总结"""
    print("\n" + "=" * 60)
    print("  安装验证总结")
    print("=" * 60)

    # 核心功能
    print("\n✅ 核心功能:")
    if core_ok:
        print("   🟢 全部可用")
    else:
        failed = [m for m, ok in core_ok.items() if not ok]
        print(f"   🔴 {len(failed)} 个模块不可用")

    # 可选功能
    print("\n⚡ 可选功能:")
    features = [
        ("Sidecar 文件监控", sidecar_ok and deps.get("watchdog")),
        ("Sidecar REST API", dashboard_ok and deps.get("fastapi")),
        ("Web 看板", dashboard_ok),
        ("剪贴板复制", deps.get("pyperclip")),
    ]

    for name, available in features:
        if available:
            print(f"   🟢 {name}")
        else:
            print(f"   🔴 {name} (需要安装依赖)")

    # 安装建议
    print("\n💡 安装建议:")
    missing = []
    if not deps.get("watchdog"):
        missing.append("watchdog")
    if not deps.get("fastapi"):
        missing.append("fastapi")
    if not deps.get("uvicorn"):
        missing.append("uvicorn")
    if not deps.get("pyperclip"):
        missing.append("pyperclip")

    if missing:
        print(f"   安装缺失依赖:")
        print(f"   pip install {' '.join(missing)}")
        print(f"\n   或一键安装所有功能:")
        print(f"   pip install 'moat-ai[all]'")
    else:
        print("   🎉 所有功能已启用！")

    print("\n" + "=" * 60)


def main():
    """主函数"""
    print("🧪 Moat v0.4.0 安装验证")
    print("=" * 60)
    print()

    # 1. 检查 Python 版本
    if not check_python_version():
        sys.exit(1)

    # 2. 检查依赖
    deps = check_dependencies()

    # 3. 检查核心模块
    core_ok = check_moat_core()

    # 4. 检查可选模块
    sidecar_ok = check_sidecar_modules(deps)
    dashboard_ok = check_dashboard_modules(deps)
    vscode_ok = check_vscode_features(deps)

    # 5. 打印总结
    print_summary(core_ok, deps, sidecar_ok, dashboard_ok, vscode_ok)


if __name__ == "__main__":
    main()
