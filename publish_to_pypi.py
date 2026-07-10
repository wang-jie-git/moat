#!/usr/bin/env python3
"""
Moat v0.9.0 PyPI 发布脚本

手动构建分发包并上传到 PyPI
"""

import subprocess
import sys
import tarfile
from pathlib import Path

def create_sdist():
    """创建源码分发包"""
    print("📦 创建源码分发包...")

    project_dir = Path.cwd()
    version = "0.9.0"

    # 创建 dist 目录
    dist_dir = project_dir / "dist"
    dist_dir.mkdir(exist_ok=True)

    # 创建临时目录
    temp_dir = project_dir / f"temp-{version}"
    if temp_dir.exists():
        import shutil
        shutil.rmtree(temp_dir)
    temp_dir.mkdir()

    # 复制 moat 目录
    import shutil
    shutil.copytree(project_dir / "moat", temp_dir / "moat")

    # 复制其他必要文件
    for file in ["pyproject.toml", "README.md", "LICENSE"]:
        src = project_dir / file
        if src.exists():
            shutil.copy2(src, temp_dir / file)

    # 创建 tarball
    tarball_name = f"moat_ai-{version}.tar.gz"
    tarball_path = dist_dir / tarball_name

    with tarfile.open(tarball_path, "w:gz") as tar:
        tar.add(temp_dir, arcname=f"moat-ai-{version}")

    # 清理临时目录
    import shutil
    shutil.rmtree(temp_dir)

    print(f"   ✅ 源码包: {tarball_path}")
    print(f"   📊 大小: {tarball_path.stat().st_size / 1024:.1f} KB")
    return tarball_path


def create_wheel():
    """创建 Wheel 分发包"""
    print("\n📦 创建 Wheel 分发包...")

    # 使用 pip wheel 创建 wheel
    result = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", ".", "-w", "dist/"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("   ✅ Wheel 创建成功")
        # 查找创建的 wheel 文件
        dist_dir = Path("dist")
        wheels = list(dist_dir.glob("moat_ai-*.whl"))
        if wheels:
            wheel_path = wheels[0]
            print(f"   📄 {wheel_path.name}")
            print(f"   📊 大小: {wheel_path.stat().st_size / 1024:.1f} KB")
            return wheel_path
    else:
        print(f"   ❌ Wheel 创建失败:")
        print(result.stderr)
        return None


def upload_to_pypi():
    """上传到 PyPI"""
    print("\n🚀 上传到 PyPI...")

    # 检查 dist 目录
    dist_dir = Path("dist")
    if not dist_dir.exists() or not list(dist_dir.glob("*")):
        print("   ❌ dist 目录为空，请先构建分发包")
        return False

    # 使用 twine 上传
    result = subprocess.run(
        ["twine", "upload", "dist/*"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("   ✅ 上传成功！")
        print("   🔗 PyPI: https://pypi.org/project/moat-ai/0.9.0/")
        return True
    else:
        print(f"   ❌ 上传失败:")
        print(result.stderr)
        return False


def main():
    print("=" * 60)
    print("Moat v0.9.0 PyPI 发布脚本")
    print("=" * 60)

    # 1. 创建源码包
    sdist = create_sdist()

    # 2. 创建 Wheel（如果失败，只上传源码包）
    wheel = create_wheel()

    # 3. 上传
    if sdist:
        success = upload_to_pypi()
        if success:
            print("\n" + "=" * 60)
            print("✅ Moat v0.9.0 发布成功！")
            print("=" * 60)
            return 0

    print("\n❌ 发布失败")
    return 1


if __name__ == "__main__":
    sys.exit(main())
