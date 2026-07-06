"""行为验证检查 — L1: 核心行为"""
from pathlib import Path


def run_behavior_check(project_root: Path) -> list[dict]:
    """验证项目的基本行为（构建、测试、lint）"""
    errors = []

    # 检查是否有测试
    test_dirs = ["tests", "test"]
    has_tests = any((project_root / d).exists() for d in test_dirs)
    if not has_tests:
        errors.append({
            "file": "tests/",
            "level": "L1",
            "type": "behavior_no_tests",
            "message": "项目没有测试目录",
        })

    # 检查是否有 CI 配置文件
    ci_files = [
        ".github/workflows",
        ".gitlab-ci.yml",
        "Jenkinsfile",
        ".circleci/config.yml",
    ]
    has_ci = any((project_root / f).exists() for f in ci_files)
    if not has_ci:
        errors.append({
            "file": ".github/",
            "level": "L1",
            "type": "behavior_no_ci",
            "message": "项目没有 CI 配置",
        })

    return errors