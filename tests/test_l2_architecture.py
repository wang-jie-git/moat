"""L2 架构规则检查测试"""
from pathlib import Path
import tempfile
import os

def test_entropy_detection():
    """测试代码熵增检测"""
    from moat.checks.l2_architecture import _detect_code_entropy

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # 创建基线（100行代码）
        base_file = project_root / "core.py"
        base_content = "# " + "\n# ".join([f"Line {i}" for i in range(100)])
        base_file.write_text(base_content)

        # 创建基线数据
        baseline = {
            "file_count": 1,
            "total_lines": 100,
            "file_hashes": {
                "core.py": "abc123"
            },
            "line_counts": {
                "core.py": 100
            }
        }

        # 增大文件到 300 行（增长 200%）
        large_content = base_content + "\n" + "\n".join([f"# Line {i}" for i in range(200)])
        base_file.write_text(large_content)

        # 运行检测
        errors = _detect_code_entropy(project_root, baseline)

        # 应该检测到高熵增
        assert len(errors) > 0
        high_entropy = [e for e in errors if e.get("type") == "high_entropy"]
        assert len(high_entropy) > 0
        assert "200.0%" in high_entropy[0]["message"]
        print("✅ 熵增检测测试通过")


def test_dependency_hubs():
    """测试依赖枢纽识别"""
    from moat.checks.l2_architecture import _identify_dependency_hubs

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # 创建核心模块
        core = project_root / "core" / "config.py"
        core.parent.mkdir()
        core.write_text("class Config: pass")

        # 创建多个模块导入 core.config
        for i in range(7):
            mod = project_root / f"module_{i}.py"
            mod.write_text(f"from core.config import Config\nclass Module{i}: pass")

        # 运行检测
        errors = _identify_dependency_hubs(project_root)

        # 应该检测到依赖枢纽
        assert len(errors) > 0
        hubs = [e for e in errors if e.get("type") == "dependency_hub"]
        assert len(hubs) > 0
        print("✅ 依赖枢纽检测测试通过")


if __name__ == "__main__":
    test_entropy_detection()
    test_dependency_hubs()
    print("\n✅ 所有 L2 测试通过")
