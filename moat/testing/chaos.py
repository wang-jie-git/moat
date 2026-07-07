"""混沌测试集（Chaos Suite）

随机修改项目代码，验证 Moat 的检测能力。
如果 Moat 漏报了，说明需要修复 Moat 的 Bug；
如果 Moat 报了但用户认为不重要，说明需要调整权重。
"""
import ast
import random
import subprocess
from pathlib import Path
from typing import Any


class ChaosMonkey:
    """混沌猴子 — 随机修改代码"""

    def __init__(self, project_root: Path):
        self.project = project_root.resolve()
        self.py_files = [
            f for f in self.project.rglob("*.py")
            if not any(p in f.parts for p in (
                ".venv", "venv", "__pycache__", ".git", "node_modules",
                "build", "dist", "tests"
            ))
        ]

    def pick_random_file(self) -> Path | None:
        """随机选择一个 Python 文件"""
        if not self.py_files:
            return None
        return random.choice(self.py_files)

    def pick_random_function(self, file_path: Path) -> dict[str, Any] | None:
        """随机选择一个函数进行修改"""
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source)

            functions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "end_line": node.end_lineno,
                    })

            if not functions:
                return None

            return random.choice(functions)
        except Exception:
            return None

    def inject_race_condition(self, file_path: Path, function_name: str) -> str:
        """注入竞态条件"""
        try:
            source = file_path.read_text(encoding="utf-8")
            lines = source.split("\n")

            # 在函数末尾添加一条注释（模拟竞态条件）
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    end_line = node.end_lineno or node.lineno
                    indent = "    "

                    # 插入竞态条件注释
                    new_line = f"{indent}# @chaos: pendingMessageRef 缺少时序注释"
                    lines.insert(end_line, new_line)

                    return "\n".join(lines)
        except Exception:
            pass

        return file_path.read_text(encoding="utf-8")

    def inject_syntax_error(self, file_path: Path, function_name: str) -> str:
        """注入语法错误"""
        try:
            source = file_path.read_text(encoding="utf-8")
            lines = source.split("\n")

            # 添加无效语法（注释 + 孤立冒号）
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    end_line = node.end_lineno or node.lineno
                    indent = "    "

                    # 插入语法错误
                    new_line = f"{indent}def :  # @chaos: syntax error"
                    lines.insert(end_line, new_line)

                    return "\n".join(lines)
        except Exception:
            pass

        return file_path.read_text(encoding="utf-8")

    def inject_missing_doc(self, file_path: Path, function_name: str) -> str:
        """模拟缺少文档的检查项"""
        # 这里不需要修改代码，只需要创建一个检查任务
        return file_path.read_text(encoding="utf-8")

    def create_chaos_task(self, chaos_type: str = "random") -> dict[str, Any]:
        """创建一个混沌任务

        Args:
            chaos_type: "race_condition" | "syntax_error" | "missing_doc" | "random"

        Returns:
            任务描述
        """
        file_path = self.pick_random_file()
        if not file_path:
            return {"error": "No Python files found"}

        func_info = self.pick_random_function(file_path)
        if not func_info:
            return {"error": f"No functions found in {file_path}"}

        if chaos_type == "random":
            chaos_type = random.choice([
                "race_condition", "syntax_error", "missing_doc"
            ])

        # 备份原文件
        backup_path = file_path.with_suffix(".py.bak")
        file_path.rename(backup_path)

        # 注入混沌
        if chaos_type == "race_condition":
            new_content = self.inject_race_condition(backup_path, func_info["name"])
        elif chaos_type == "syntax_error":
            new_content = self.inject_syntax_error(backup_path, func_info["name"])
        else:
            new_content = backup_path.read_text(encoding="utf-8")

        # 写入修改后的文件
        file_path.write_text(new_content, encoding="utf-8")

        task = {
            "chaos_type": chaos_type,
            "file": str(file_path.relative_to(self.project)),
            "function": func_info["name"],
            "line": func_info["line"],
            "backup": str(backup_path.relative_to(self.project)),
            "should_detect": True,
        }

        return task

    def restore(self, task: dict[str, Any]):
        """恢复原文件"""
        file_path = self.project / task["file"]
        backup_path = self.project / task["backup"]

        if backup_path.exists():
            file_path.unlink(missing_ok=True)
            backup_path.rename(file_path)


class ChaosRunner:
    """混沌测试运行器"""

    def __init__(self, project_root: str = "."):
        self.project = Path(project_root).resolve()
        self.monkey = ChaosMonkey(self.project)
        self.results: list[dict[str, Any]] = []

    def run(self, num_tasks: int = 5) -> dict[str, Any]:
        """运行混沌测试

        Args:
            num_tasks: 测试任务数

        Returns:
            测试结果统计
        """
        print(f"\n{'=' * 60}")
        print(f"  🐒 Chaos Suite — 混沌测试")
        print(f"  项目: {self.project}")
        print(f"  任务数: {num_tasks}")
        print(f"{'=' * 60}\n")

        detected = 0
        missed = 0

        for i in range(num_tasks):
            print(f"[{i + 1}/{num_tasks}] 创建混沌任务...")

            # 1. 创建混沌任务
            task = self.monkey.create_chaos_task()
            if "error" in task:
                print(f"   ⚠️  {task['error']}")
                continue

            print(f"   ⚡ 类型: {task['chaos_type']}")
            print(f"   📄 文件: {task['file']}::{task['function']}")

            # 2. 运行 moat check
            print(f"   🔍 运行 Moat 检查...")
            result = self._run_moat_check()

            # 3. 评估结果
            should_detect = task["should_detect"]
            was_detected = result["failed"] > 0

            if should_detect and was_detected:
                print(f"   ✅ Moat 正确检测到问题")
                detected += 1
            elif should_detect and not was_detected:
                print(f"   ❌ Moat 漏报了！需要修复")
                missed += 1
            else:
                print(f"   ℹ️  任务完成（无需检测）")

            # 4. 恢复原文件
            self.monkey.restore(task)
            print()

        # 统计结果
        total = detected + missed
        detection_rate = (detected / total * 100) if total > 0 else 0.0

        summary = {
            "total_tasks": num_tasks,
            "detected": detected,
            "missed": missed,
            "detection_rate": round(detection_rate, 1),
            "passed": missed == 0,
        }

        print(f"{'=' * 60}")
        print(f"  测试结果:")
        print(f"  检测到: {detected}/{total} ({detection_rate:.1f}%)")
        print(f"  漏报: {missed}/{total}")
        print(f"{'=' * 60}\n")

        if summary["passed"]:
            print("✅ 混沌测试通过！Moat 检测能力正常。")
        else:
            print(f"❌ 混沌测试失败！Moat 漏报了 {missed} 个问题，需要修复。")

        return summary

    def _run_moat_check(self) -> dict[str, Any]:
        """运行 moat check 并返回结果"""
        try:
            result = subprocess.run(
                ["python3", "-m", "moat", "check", "--project", str(self.project)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            return {
                "returncode": result.returncode,
                "failed": result.stdout.count("❌") + result.stderr.count("❌"),
                "passed": result.stdout.count("✅"),
            }
        except subprocess.TimeoutExpired:
            return {"returncode": -1, "failed": 0, "passed": 0, "error": "timeout"}
        except Exception as e:
            return {"returncode": -1, "failed": 0, "passed": 0, "error": str(e)}


def run_chaos_suite(project_root: str = ".", num_tasks: int = 5) -> dict[str, Any]:
    """运行混沌测试（便捷函数）

    Args:
        project_root: 项目根目录
        num_tasks: 测试任务数

    Returns:
        测试结果统计
    """
    runner = ChaosRunner(project_root)
    return runner.run(num_tasks)
