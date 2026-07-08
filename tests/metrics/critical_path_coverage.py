#!/usr/bin/env python3
"""关键路径覆盖率报告生成器

生成 Moat 核心路径的专项覆盖率报告，区分"关键路径"与"整体覆盖率"。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


# ──────────────────────────────────────────────
# 关键路径定义
# ──────────────────────────────────────────────

CRITICAL_PATHS = {
    "L0 Python 语法检查": {
        "files": ["moat/checks/l1_import.py"],
        "weight": "critical",
        "description": "第一道防线，语法错误检测",
    },
    "L1 Import 检查": {
        "files": ["moat/checks/l1_import.py"],
        "weight": "critical",
        "description": "模块动态 import 验证",
    },
    "L1 文件完整性": {
        "files": ["moat/checks/l1_files.py"],
        "weight": "high",
        "description": "关键文件存在性检测",
    },
    "L1 核心模块": {
        "files": ["moat/checks/l1_modules.py"],
        "weight": "critical",
        "description": "核心模块实例化验证",
    },
    "L1 子系统": {
        "files": ["moat/checks/l1_subsystems.py"],
        "weight": "high",
        "description": "子系统存活检测",
    },
    "L3 关联检查": {
        "files": ["moat/checks/l3_correlation.py"],
        "weight": "high",
        "description": "循环依赖和核心-边缘违规检测",
    },
    "L4 基线对比": {
        "files": ["moat/checks/l4_baseline.py"],
        "weight": "medium",
        "description": "基线退化检测",
    },
    "TypeScript 语法检查": {
        "files": ["moat/checks/typescript/syntax.py"],
        "weight": "high",
        "description": "TS 语法门禁",
    },
    "痛觉评分": {
        "files": ["moat/pain/scorer.py", "moat/pain/feedback.py"],
        "weight": "critical",
        "description": "风险量化评分",
    },
    "记忆桥接器": {
        "files": ["moat/memory/bridge.py"],
        "weight": "high",
        "description": "One Memory SQLite 桥接",
    },
}


def run_coverage() -> dict[str, Any]:
    """运行 pytest --cov 并返回覆盖率数据。"""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--cov=moat", "--cov-report=json", "-q"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent),
    )

    # 解析 coverage.json
    cov_file = Path(__file__).parent.parent / "coverage.json"
    if not cov_file.exists():
        return {}

    with open(cov_file) as f:
        return json.load(f)


def calculate_critical_coverage(coverage_data: dict[str, Any]) -> dict[str, Any]:
    """计算关键路径覆盖率。"""
    files_data = coverage_data.get("files", {})

    # 构建归一化键映射（统一路径格式）
    normalized = {}
    for k, v in files_data.items():
        # 统一使用 posix 风格路径
        normalized_key = k.replace("\\", "/").lstrip("./")
        normalized[normalized_key] = v

    path_stats = {}
    total_critical_lines = 0
    total_critical_covered = 0

    for path_name, path_info in CRITICAL_PATHS.items():
        path_covered = 0
        path_total = 0

        for file_path in path_info["files"]:
            # 尝试多种路径格式
            candidates = [
                file_path,
                file_path.replace("moat/", ""),
                f"/Users/mac/Desktop/moat/{file_path}",
            ]
            found = False
            for candidate in candidates:
                if candidate in normalized:
                    stats = normalized[candidate]["summary"]
                    path_total += stats["num_statements"]
                    path_covered += stats["covered_lines"]
                    found = True
                    break

            if not found:
                # 尝试模糊匹配
                for key in normalized:
                    if key.endswith(file_path.split("/")[-1]):
                        stats = normalized[key]["summary"]
                        path_total += stats["num_statements"]
                        path_covered += stats["covered_lines"]
                        break

        if path_total > 0:
            coverage_pct = (path_covered / path_total) * 100
        else:
            coverage_pct = 0.0

        path_stats[path_name] = {
            "weight": path_info["weight"],
            "description": path_info["description"],
            "lines_covered": path_covered,
            "lines_total": path_total,
            "coverage_pct": round(coverage_pct, 1),
        }

        total_critical_lines += path_total
        total_critical_covered += path_covered

    overall_critical_pct = (total_critical_covered / total_critical_lines * 100) if total_critical_lines > 0 else 0

    return {
        "paths": path_stats,
        "total_lines": total_critical_lines,
        "covered_lines": total_critical_covered,
        "overall_coverage_pct": round(overall_critical_pct, 1),
    }


def print_report(report: dict[str, Any]) -> None:
    """打印格式化的报告。"""
    print("\n" + "=" * 80)
    print("🛡️  Moat 关键路径覆盖率报告")
    print("=" * 80)

    print(f"\n总关键路径行数: {report['total_lines']}")
    print(f"已覆盖行数:     {report['covered_lines']}")
    print(f"关键路径覆盖率: {report['overall_coverage_pct']}%\n")

    print("-" * 80)
    print(f"{'路径名称':<35} {'权重':<10} {'覆盖率':<10} {'行数'}")
    print("-" * 80)

    weight_emoji = {
        "critical": "🔴",
        "high": "🟡",
        "medium": "🟢",
    }

    for path_name, stats in report["paths"].items():
        emoji = weight_emoji.get(stats["weight"], "⚪")
        print(
            f"{emoji} {path_name:<33} "
            f"{stats['weight']:<10} "
            f"{stats['coverage_pct']:>6.1f}%  "
            f"{stats['lines_covered']}/{stats['lines_total']}  "
            f"# {stats['description']}"
        )

    print("-" * 80)

    # 评分
    critical_pct = report["overall_coverage_pct"]
    if critical_pct >= 80:
        grade = "A"
        emoji = "✅"
    elif critical_pct >= 60:
        grade = "B"
        emoji = "⚠️"
    elif critical_pct >= 40:
        grade = "C"
        emoji = "🔶"
    else:
        grade = "D"
        emoji = "❌"

    print(f"\n{emoji} 关键路径评分: {grade} ({critical_pct:.1f}%)")
    print("\n注：关键路径覆盖率 ≠ 整体覆盖率。")
    print("关键路径只包含核心业务逻辑（L0-L4 + TypeScript + 痛觉评分 + 记忆）。")
    print("\n" + "=" * 80 + "\n")


def main() -> None:
    """主入口：生成关键路径覆盖率报告。"""
    print("🔍 计算关键路径覆盖率...")

    # 1. 运行覆盖率
    print("📊 运行 pytest --cov...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--cov=moat", "--cov-report=json", "-q"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent),
    )

    if result.returncode != 0:
        print(f"⚠️  pytest 返回非零退出码 ({result.returncode})，但继续生成报告...")

    # 2. 读取覆盖率数据
    cov_file = Path(__file__).parent.parent / "coverage.json"
    if not cov_file.exists():
        print("❌ 未找到 coverage.json，请先运行 pytest --cov")
        sys.exit(1)

    with open(cov_file) as f:
        coverage_data = json.load(f)

    # 3. 计算关键路径
    report = calculate_critical_coverage(coverage_data)

    # 4. 打印报告
    print_report(report)

    # 5. 保存报告
    report_file = Path(__file__).parent.parent / "critical_path_coverage.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"💾 报告已保存: {report_file}\n")

    # 6. 返回退出码（用于 CI）
    if report["overall_coverage_pct"] < 60:
        print("⚠️  关键路径覆盖率低于 60% 阈值")
        sys.exit(1)


if __name__ == "__main__":
    main()
