"""未使用的导出检测测试（UNUSED-001）

测试所有常见的未使用导出模式
"""
import pytest
from pathlib import Path
from moat.checks.unused_exports import UnusedExportsCheck
from moat.checks.base import CheckResult


@pytest.fixture
def check(tmp_path):
    """创建 UnusedExportsCheck 实例"""
    return UnusedExportsCheck(tmp_path, {})


def test_python_unused_export_in_all(check):
    """测试 Python __all__ 中未使用的导出"""
    test_file = Path(check.project) / "mymodule.py"
    test_file.write_text("""
__all__ = ["func_a", "func_b", "unused_func"]

def func_a():
    pass

def func_b():
    pass

def unused_func():
    pass

# func_a 被使用
func_a()
""")

    results = check._check_file(test_file)
    # 应该检测到 unused_func 未被使用
    assert len(results) >= 1
    assert any("unused_func" in r.message for r in results)
    print(f"✅ Python __all__ 检测: 找到 {len(results)} 个未使用导出")


def test_python_all_exports_used(check):
    """测试所有 __all__ 中的导出都被使用"""
    test_file = Path(check.project) / "mymodule.py"
    test_file.write_text("""
__all__ = ["func_a", "func_b"]

def func_a():
    pass

def func_b():
    pass

func_a()
func_b()
""")

    results = check._check_file(test_file)
    # 不应该有未使用导出
    assert len(results) == 0
    print(f"✅ 所有导出都被使用: 无问题")


def test_python_no_all(check):
    """测试没有 __all__ 的文件"""
    test_file = Path(check.project) / "mymodule.py"
    test_file.write_text("""
def func_a():
    pass

def func_b():
    pass
""")

    results = check._check_file(test_file)
    # 没有 __all__，不应该有结果
    assert len(results) == 0
    print(f"✅ 无 __all__: 无问题")


def test_python_class_in_all(check):
    """测试 __all__ 中的类"""
    test_file = Path(check.project) / "mymodule.py"
    test_file.write_text("""
__all__ = ["MyClass", "unused_class"]

class MyClass:
    pass

class unused_class:
    pass

obj = MyClass()
""")

    results = check._check_file(test_file)
    # 应该检测到 unused_class
    assert len(results) >= 1
    print(f"✅ 类导出检测: 找到 {len(results)} 个未使用")


def test_typescript_unused_export(check):
    """测试 TypeScript 未使用的 export"""
    test_file = Path(check.project) / "utils.ts"
    test_file.write_text("""
export function usedFunc() {
    return "hello";
}

export function unusedFunc() {
    return "world";
}

usedFunc();
""")

    results = check._check_file(test_file)
    # 应该检测到 unusedFunc
    assert len(results) >= 1
    assert any("unusedFunc" in r.message for r in results)
    print(f"✅ TypeScript 检测: 找到 {len(results)} 个未使用导出")


def test_typescript_default_export(check):
    """测试 TypeScript default export"""
    test_file = Path(check.project) / "index.ts"
    test_file.write_text("""
export default function myFunc() {
    return "hello";
}
""")

    results = check._check_file(test_file)
    # default export 应该被跳过
    print(f"✅ default export: 找到 {len(results)} 个问题")


def test_go_unused_export(check):
    """测试 Go 未使用的导出函数"""
    test_file = Path(check.project) / "main.go"
    test_file.write_text("""
package main

import "fmt"

func UsedFunc() {
    fmt.Println("used")
}

func UnusedFunc() {
    fmt.Println("unused")
}

func main() {
    UsedFunc()
}
""")

    results = check._check_file(test_file)
    # 应该检测到 UnusedFunc
    assert len(results) >= 1
    assert any("UnusedFunc" in r.message for r in results)
    print(f"✅ Go 检测: 找到 {len(results)} 个未使用导出")


def test_go_exported_type(check):
    """测试 Go 导出的类型"""
    test_file = Path(check.project) / "types.go"
    test_file.write_text("""
package mypackage

type UsedType struct {
    Name string
}

type UnusedType struct {
    Value int
}

var _ = UsedType{}
""")

    results = check._check_file(test_file)
    # 应该检测到 UnusedType
    assert len(results) >= 1
    assert any("UnusedType" in r.message for r in results)
    print(f"✅ Go 类型检测: 找到 {len(results)} 个未使用导出")


def test_run_multiple_files(check):
    """测试多个文件的检测"""
    file1 = Path(check.project) / "module1.py"
    file1.write_text("""
__all__ = ["func_a", "unused1"]

def func_a():
    pass

def unused1():
    pass

func_a()
""")

    file2 = Path(check.project) / "module2.py"
    file2.write_text("""
__all__ = ["func_b", "unused2"]

def func_b():
    pass

def unused2():
    pass

func_b()
""")

    results = check.run()
    # 应该检测到两个未使用导出
    assert len(results) >= 2
    print(f"✅ 多文件检测: 找到 {len(results)} 个问题")


def test_empty_all(check):
    """测试空的 __all__"""
    test_file = Path(check.project) / "mymodule.py"
    test_file.write_text("""
__all__ = []

def func_a():
    pass
""")

    results = check._check_file(test_file)
    # 空的 __all__，不应该有结果
    assert len(results) == 0
    print(f"✅ 空 __all__: 无问题")


def test_no_definitions_in_all(check):
    """测试 __all__ 中的名称不在定义中"""
    test_file = Path(check.project) / "mymodule.py"
    test_file.write_text("""
__all__ = ["func_a", "nonexistent"]

def func_a():
    pass

func_a()
""")

    results = check._check_file(test_file)
    # nonexistent 不在定义中，应该被跳过
    unused_results = [r for r in results if "nonexistent" in r.message]
    assert len(unused_results) == 0
    print(f"✅ 不存在的导出: 正确处理")


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        check = UnusedExportsCheck(tmp_path, {})

        print("=== 未使用导出检测测试 ===\n")

        # 测试 1: Python __all__ 未使用
        test_python_unused_export_in_all(check)

        # 测试 2: 所有导出都被使用
        test_python_all_exports_used(check)

        # 测试 3: 没有 __all__
        test_python_no_all(check)

        # 测试 4: __all__ 中的类
        test_python_class_in_all(check)

        # 测试 5: TypeScript
        test_typescript_unused_export(check)

        # 测试 6: TypeScript default export
        test_typescript_default_export(check)

        # 测试 7: Go
        test_go_unused_export(check)

        # 测试 8: Go 类型
        test_go_exported_type(check)

        # 测试 9: 多文件
        test_run_multiple_files(check)

        # 测试 10: 空 __all__
        test_empty_all(check)

        print("\n✅ 所有测试通过！")
