"""v1.0.8 性能优化验证脚本

验证所有 Phase 3 的性能改进：
1. 缓存优化（LRU 缓存）
2. 增量扫描改进
3. 配置增强
"""
import time
from pathlib import Path
import tempfile


def test_cache_performance():
    """测试缓存性能提升"""
    print("=== 测试缓存性能 ===\n")

    from moat.cache_enhanced import EnhancedHashCacheManager

    with tempfile.TemporaryDirectory() as tmp:
        project_root = Path(tmp)

        # 创建 1000 个测试文件
        test_files = []
        for i in range(1000):
            file_path = project_root / f"file_{i}.py"
            file_path.write_text(f"# File {i}\ndef func_{i}():\n    pass\n")
            test_files.append(file_path)

        # 测试无缓存
        start = time.time()
        for f in test_files:
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                hash = content.__hash__()
            except:
                pass
        no_cache_time = time.time() - start

        # 测试 LRU 缓存
        cache_mgr = EnhancedHashCacheManager(project_root, max_cache_size=1000)
        start = time.time()
        for f in test_files:
            cache_mgr.get_file_hash(f)
        first_cache_time = time.time() - start

        # 第二次读取（命中缓存）
        start = time.time()
        for f in test_files:
            cache_mgr.get_file_hash(f)
        second_cache_time = time.time() - start

        print(f"无缓存: {no_cache_time:.3f}s")
        print(f"首次缓存: {first_cache_time:.3f}s")
        print(f"二次缓存: {second_cache_time:.3f}s")
        print(f"缓存命中速度提升: {first_cache_time / second_cache_time:.1f}x\n")

        # 缓存统计
        stats = cache_mgr.get_stats()
        print(f"缓存统计: {stats}\n")


def test_ast_diff_performance():
    """测试 AST diff 性能"""
    print("=== 测试 AST diff 性能 ===\n")

    from moat.ast.diff_enhanced import EnhancedASTDiffer

    with tempfile.TemporaryDirectory() as tmp:
        project_root = Path(tmp)
        test_file = project_root / "test.py"

        # 创建初始文件
        code1 = """
def func_a():
    return 1

def func_b():
    return 2
"""

        code2 = """
def func_a(x):
    return x + 1

def func_c():
    return 3
"""

        test_file.write_text(code1)

        differ = EnhancedASTDiffer(project_root)

        # 测试 diff 性能
        start = time.time()
        changes = differ.diff_file(test_file, old_content=code1, new_content=code2)
        diff_time = time.time() - start

        print(f"AST diff 时间: {diff_time:.4f}s")
        print(f"检测到 {len(changes)} 个变更:")
        for change in changes:
            print(f"  - {change.change_type}: {change.function} ({change.change_type_detail})")
        print()


def test_config_loading():
    """测试配置加载"""
    print("=== 测试配置加载 ===\n")

    from moat.config_enhanced import load_enhanced_config

    with tempfile.TemporaryDirectory() as tmp:
        project_root = Path(tmp)

        # 测试 1: 只有 moat.json
        moat_dir = project_root / ".moat"
        moat_dir.mkdir()
        (moat_dir / "moat.json").write_text('{"rules": ["sql_injection"]}')

        config = load_enhanced_config(project_root)
        print(f"moat.json: {config}")

        # 测试 2: 添加 pyproject.toml
        (project_root / "pyproject.toml").write_text("""
[tool.moat]
enabled_rules = ["secrets", "sql_injection"]
severity = "high"
""")

        config = load_enhanced_config(project_root)
        print(f"pyproject.toml + moat.json: {config}")

        # 测试 3: 添加 .moatignore
        (project_root / ".moatignore").write_text("test_*.py\ndemo/\n")

        config = load_enhanced_config(project_root)
        print(f".moatignore + pyproject.toml: {config}")
        print(f"忽略规则: {config.get('ignore', {}).get('patterns', [])}\n")


def test_full_pipeline():
    """测试完整流程性能"""
    print("=== 测试完整流程性能 ===\n")

    with tempfile.TemporaryDirectory() as tmp:
        project_root = Path(tmp)

        # 创建测试项目结构
        src_dir = project_root / "src"
        src_dir.mkdir()

        # 创建 100 个 Python 文件
        for i in range(100):
            file_path = src_dir / f"module_{i}.py"
            file_path.write_text(f"""
def func_{i}():
    return {i}

class Class_{i}:
    def __init__(self):
        self.value = {i}
""")

        from moat.checks.quick_check import QuickCheck

        check = QuickCheck(project_root, {})

        # 测试完整扫描
        start = time.time()
        results = check.run()
        elapsed = time.time() - start

        print(f"扫描 100 个文件: {elapsed:.3f}s")
        print(f"平均每个文件: {elapsed / 100 * 1000:.1f}ms")
        print(f"检测到 {len(results)} 个问题\n")


if __name__ == "__main__":
    print("=" * 80)
    print("  Moat v1.0.8 性能优化验证")
    print("=" * 80)
    print()

    # 测试 1: 缓存性能
    test_cache_performance()

    # 测试 2: AST diff 性能
    test_ast_diff_performance()

    # 测试 3: 配置加载
    test_config_loading()

    # 测试 4: 完整流程
    test_full_pipeline()

    print("✅ 所有性能测试完成！")
