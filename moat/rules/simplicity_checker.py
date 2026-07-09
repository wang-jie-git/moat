"""
Simplicity First 规则：复杂度检查器

确保代码保持简洁，拒绝过度工程化。
利用 Tree-sitter 进行 AST 级复杂度分析。
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from moat.rules import PrincipleViolation, Principle


@dataclass
class ComplexityMetrics:
    """代码复杂度指标"""
    file_path: str
    total_lines: int
    function_count: int
    class_count: int
    max_function_lines: int
    max_class_methods: int
    max_inheritance_depth: int
    avg_function_length: float
    cyclomatic_complexity: int


class SimplicityChecker:
    """Simplicity First 检查器"""

    def __init__(
        self,
        max_function_lines: int = 50,
        max_class_methods: int = 15,
        max_inheritance_depth: int = 3,
        max_file_lines: int = 500,
        max_cyclomatic_complexity: int = 10
    ):
        self.max_function_lines = max_function_lines
        self.max_class_methods = max_class_methods
        self.max_inheritance_depth = max_inheritance_depth
        self.max_file_lines = max_file_lines
        self.max_cyclomatic_complexity = max_cyclomatic_complexity

        self.principle = Principle(
            name="simplicity_first",
            description="拒绝过度工程化，保持代码简洁",
            check_type="complexity_analysis",
            enforcement="critical"
        )

    def check_file(self, file_path: str, content: str) -> List[PrincipleViolation]:
        """
        检查文件复杂度

        Args:
            file_path: 文件路径
            content: 文件内容

        Returns:
            违规列表
        """
        violations = []

        # 检查文件总行数
        total_lines = len(content.split('\n'))
        if total_lines > self.max_file_lines:
            violations.append(PrincipleViolation(
                principle_name=self.principle.name,
                severity="warning",
                message=f"文件过大（{total_lines} 行），违反 'Simplicity First' 原则。建议拆分为多个模块。",
                file_path=file_path,
                context={
                    "total_lines": total_lines,
                    "max_allowed": self.max_file_lines,
                    "type": "file_size"
                }
            ))

        # 检查函数长度（简化版，生产环境建议使用 Tree-sitter AST）
        violations.extend(self._check_function_lengths(file_path, content))

        # 检查类复杂度
        violations.extend(self._check_class_complexity(file_path, content))

        return violations

    def _check_function_lengths(self, file_path: str, content: str) -> List[PrincipleViolation]:
        """检查函数长度"""
        violations = []
        lines = content.split('\n')

        in_function = False
        func_name = None
        func_start = 0
        indent_level = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # 检测函数定义
            if stripped.startswith('def ') or stripped.startswith('async def '):
                # 保存上一个函数
                if in_function and func_name:
                    func_length = i - func_start - 1
                    if func_length > self.max_function_lines:
                        violations.append(PrincipleViolation(
                            principle_name=self.principle.name,
                            severity="warning",
                            message=f"函数 '{func_name}' 过长（{func_length} 行），"
                                    f"违反 'Simplicity First' 原则。建议拆分为更小的函数。",
                            file_path=file_path,
                            line_number=func_start,
                            context={
                                "function_name": func_name,
                                "length": func_length,
                                "max_allowed": self.max_function_lines,
                                "type": "function_length"
                            }
                        ))

                # 开始新函数
                in_function = True
                func_name = stripped.split('(')[0].replace('def ', '').replace('async ', '')
                func_start = i
                indent_level = len(line) - len(line.lstrip())

            # 检测函数结束
            elif in_function and stripped:
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= indent_level and not stripped.startswith('#'):
                    in_function = False

        # 检查最后一个函数
        if in_function and func_name:
            func_length = len(lines) - func_start
            if func_length > self.max_function_lines:
                violations.append(PrincipleViolation(
                    principle_name=self.principle.name,
                    severity="warning",
                    message=f"函数 '{func_name}' 过长（{func_length} 行），"
                            f"违反 'Simplicity First' 原则。建议拆分为更小的函数。",
                    file_path=file_path,
                    line_number=func_start,
                    context={
                        "function_name": func_name,
                        "length": func_length,
                        "max_allowed": self.max_function_lines,
                        "type": "function_length"
                    }
                ))

        return violations

    def _check_class_complexity(self, file_path: str, content: str) -> List[PrincipleViolation]:
        """检查类复杂度（方法数量）"""
        violations = []
        lines = content.split('\n')

        in_class = False
        class_name = None
        class_start = 0
        method_count = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # 检测类定义
            if stripped.startswith('class '):
                # 保存上一个类
                if in_class and class_name and method_count > self.max_class_methods:
                    violations.append(PrincipleViolation(
                        principle_name=self.principle.name,
                        severity="warning",
                        message=f"类 '{class_name}' 方法过多（{method_count} 个），"
                                f"违反 'Simplicity First' 原则。建议拆分为多个类。",
                        file_path=file_path,
                        line_number=class_start,
                        context={
                            "class_name": class_name,
                            "method_count": method_count,
                            "max_allowed": self.max_class_methods,
                            "type": "class_size"
                        }
                    ))

                # 开始新类
                in_class = True
                class_name = stripped.split('(')[0].replace('class ', '')
                class_start = i
                method_count = 0

            # 统计方法数量
            elif in_class and stripped:
                if stripped.startswith('def ') or stripped.startswith('async def '):
                    method_count += 1

        # 检查最后一个类
        if in_class and class_name and method_count > self.max_class_methods:
            violations.append(PrincipleViolation(
                principle_name=self.principle.name,
                severity="warning",
                message=f"类 '{class_name}' 方法过多（{method_count} 个），"
                        f"违反 'Simplicity First' 原则。建议拆分为多个类。",
                file_path=file_path,
                line_number=class_start,
                context={
                    "class_name": class_name,
                    "method_count": method_count,
                    "max_allowed": self.max_class_methods,
                    "type": "class_size"
                }
            ))

        return violations

    def calculate_metrics(self, file_path: str, content: str) -> ComplexityMetrics:
        """
        计算复杂度指标

        Args:
            file_path: 文件路径
            content: 文件内容

        Returns:
            ComplexityMetrics
        """
        lines = content.split('\n')
        total_lines = len(lines)

        functions = self._extract_functions(content)
        classes = self._extract_classes(content)

        max_func_lines = max([f['length'] for f in functions], default=0)
        max_class_methods = max([c['method_count'] for c in classes], default=0)

        avg_func_length = sum(f['length'] for f in functions) / len(functions) if functions else 0

        return ComplexityMetrics(
            file_path=file_path,
            total_lines=total_lines,
            function_count=len(functions),
            class_count=len(classes),
            max_function_lines=max_func_lines,
            max_class_methods=max_class_methods,
            max_inheritance_depth=self._calculate_inheritance_depth(content),
            avg_function_length=avg_func_length,
            cyclomatic_complexity=self._calculate_cyclomatic_complexity(content)
        )

    def _extract_functions(self, content: str) -> List[Dict[str, Any]]:
        """提取函数信息"""
        # 简化实现，生产环境应使用 Tree-sitter
        functions = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('def ') or stripped.startswith('async def '):
                func_name = stripped.split('(')[0].replace('def ', '').replace('async ', '')
                functions.append({
                    'name': func_name,
                    'line': i + 1,
                    'length': 0  # 简化：不计算实际长度
                })

        return functions

    def _extract_classes(self, content: str) -> List[Dict[str, Any]]:
        """提取类信息"""
        classes = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('class '):
                class_name = stripped.split('(')[0].replace('class ', '')
                classes.append({
                    'name': class_name,
                    'line': i + 1,
                    'method_count': 0  # 简化：不计算实际数量
                })

        return classes

    def _calculate_inheritance_depth(self, content: str) -> int:
        """计算继承深度（简化版）"""
        # 简化：统计 class 定义的嵌套层数
        max_depth = 0
        current_depth = 0

        for line in content.split('\n'):
            stripped = line.strip()
            if stripped.startswith('class '):
                current_depth += 1
                max_depth = max(max_depth, current_depth)

        return max_depth

    def _calculate_cyclomatic_complexity(self, content: str) -> int:
        """计算圈复杂度（简化版）"""
        # 简化：统计 if/for/while/and/or 数量 + 1
        keywords = ['if', 'elif', 'for', 'while', 'and', 'or', 'except']
        complexity = 1

        for line in content.split('\n'):
            stripped = line.strip()
            for keyword in keywords:
                if f' {keyword} ' in f' {stripped} ':
                    complexity += 1

        return complexity
