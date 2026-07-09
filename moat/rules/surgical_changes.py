"""
Surgical Changes 规则：手术刀式修改检查

确保代码修改保持原子性和精准性，禁止大规模重写。
"""

import subprocess
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from moat.rules import PrincipleViolation, Principle


@dataclass
class DiffStats:
    """Git diff 统计信息"""
    file_path: str
    added_lines: int
    removed_lines: int
    total_changes: int
    change_type: str  # "added", "modified", "deleted"


class SurgicalChangesChecker:
    """Surgical Changes 检查器"""

    def __init__(self, max_diff_lines: int = 100, max_files_changed: int = 3):
        self.max_diff_lines = max_diff_lines
        self.max_files_changed = max_files_changed
        self.principle = Principle(
            name="surgical_changes",
            description="修改必须精准，禁止重写整个文件",
            check_type="diff_size_limit",
            enforcement="warning"
        )

    def check_diff(self, repo_path: Path = None) -> List[PrincipleViolation]:
        """
        检查 Git diff 是否符合手术刀式修改原则

        Args:
            repo_path: Git 仓库路径，默认为当前目录

        Returns:
            违规列表
        """
        if repo_path is None:
            repo_path = Path.cwd()

        violations = []

        # 获取 git diff 统计
        diff_stats = self._get_diff_stats(repo_path)

        # 检查文件数量
        if len(diff_stats) > self.max_files_changed:
            violations.append(PrincipleViolation(
                principle_name=self.principle.name,
                severity=self.principle.enforcement,
                message=f"修改文件过多（{len(diff_stats)} 个），违反 'Surgical Changes' 原则。"
                        f"建议限制在 {self.max_files_changed} 个文件以内。",
                context={
                    "files_changed": len(diff_stats),
                    "max_allowed": self.max_files_changed,
                    "files": [d.file_path for d in diff_stats]
                }
            ))

        # 检查每个文件的修改行数
        for diff_stat in diff_stats:
            if diff_stat.total_changes > self.max_diff_lines:
                violations.append(PrincipleViolation(
                    principle_name=self.principle.name,
                    severity=self.principle.enforcement,
                    message=f"文件 '{diff_stat.file_path}' 修改过大（+{diff_stat.added_lines}/-{diff_stat.removed_lines}），"
                            f"违反 'Surgical Changes' 原则。建议拆分为多个小的原子修改。",
                    file_path=diff_stat.file_path,
                    context={
                        "added_lines": diff_stat.added_lines,
                        "removed_lines": diff_stat.removed_lines,
                        "total_changes": diff_stat.total_changes,
                        "max_allowed": self.max_diff_lines
                    }
                ))

        return violations

    def _get_diff_stats(self, repo_path: Path) -> List[DiffStats]:
        """
        获取 Git diff 统计信息

        Returns:
            DiffStats 列表
        """
        stats = []

        try:
            # 获取 staged changes 的 diff
            result = subprocess.run(
                ["git", "diff", "--numstat", "--cached"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False
            )

            # 解析 numstat 输出
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue

                parts = line.split('\t')
                if len(parts) != 3:
                    continue

                added = int(parts[0]) if parts[0] != '-' else 0
                removed = int(parts[1]) if parts[1] != '-' else 0
                file_path = parts[2]

                # 跳过二进制文件
                if added == 0 and removed == 0:
                    continue

                # 确定变更类型
                if added > 0 and removed == 0:
                    change_type = "added"
                elif added == 0 and removed > 0:
                    change_type = "deleted"
                else:
                    change_type = "modified"

                stats.append(DiffStats(
                    file_path=file_path,
                    added_lines=added,
                    removed_lines=removed,
                    total_changes=added + removed,
                    change_type=change_type
                ))

        except Exception as e:
            # 如果不是 git 仓库或 git 命令失败，返回空列表
            pass

        return stats

    def check_unstaged_diff(self, repo_path: Path = None) -> List[PrincipleViolation]:
        """
        检查未暂存的修改（用于 pre-commit hook）

        Args:
            repo_path: Git 仓库路径

        Returns:
            违规列表
        """
        if repo_path is None:
            repo_path = Path.cwd()

        violations = []

        try:
            # 获取 unstaged changes
            result = subprocess.run(
                ["git", "diff", "--numstat"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False
            )

            # 解析并检查
            diff_stats = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue

                parts = line.split('\t')
                if len(parts) != 3:
                    continue

                added = int(parts[0]) if parts[0] != '-' else 0
                removed = int(parts[1]) if parts[1] != '-' else 0
                file_path = parts[2]

                if added == 0 and removed == 0:
                    continue

                diff_stats.append(DiffStats(
                    file_path=file_path,
                    added_lines=added,
                    removed_lines=removed,
                    total_changes=added + removed,
                    change_type="modified"
                ))

            # 检查规则
            if len(diff_stats) > self.max_files_changed:
                violations.append(PrincipleViolation(
                    principle_name=self.principle.name,
                    severity="warning",
                    message=f"未暂存修改涉及 {len(diff_stats)} 个文件，建议分批提交。",
                    context={"files": [d.file_path for d in diff_stats]}
                ))

        except Exception:
            pass

        return violations

    def get_recommendation(self, violation: PrincipleViolation) -> str:
        """获取修复建议"""
        if "files_changed" in violation.context:
            files = violation.context["files"]
            return f"建议拆分为以下独立的提交:\n" + "\n".join(
                f"  - commit {i+1}: {f}" for i, f in enumerate(files[:self.max_files_changed])
            )
        elif violation.file_path and "total_changes" in violation.context:
            return f"建议将 '{violation.file_path}' 的修改拆分为多个小步骤。"
        return "请遵循手术刀式修改原则，保持修改原子性。"
