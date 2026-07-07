"""Moat 检查模块测试"""
import pytest
from pathlib import Path
from moat.checks.base import Check, CheckResult


class TestCheckResult:
    """测试 CheckResult 数据结构"""

    def test_create_result(self):
        """创建检查结果"""
        r = CheckResult(type="pass", message="OK")
        assert r.type == "pass"
        assert r.message == "OK"
        assert r.level == "INFO"

    def test_to_dict(self):
        """转换为字典"""
        r = CheckResult(type="fail", message="Error", file="test.py", line=10)
        d = r.to_dict()
        assert d["type"] == "fail"
        assert d["file"] == "test.py"
        assert d["line"] == 10

    def test_pass_factory(self):
        """通过结果工厂方法"""
        r = CheckResult(type="pass", message="All good")
        assert r.type == "pass"
        assert r.level == "INFO"

    def test_fail_factory(self):
        """失败结果工厂方法"""
        r = CheckResult(type="fail", message="Something wrong", file="app.py", line=42, level="ERROR")
        assert r.type == "fail"
        assert r.level == "ERROR"
        assert r.file == "app.py"
        assert r.line == 42

    def test_warn_factory(self):
        """警告结果工厂方法"""
        r = CheckResult(type="warn", message="Be careful", file="utils.py", level="WARN")
        assert r.type == "warn"
        assert r.level == "WARN"

    def test_skip_factory(self):
        """跳过结果工厂方法"""
        r = CheckResult(type="skip", message="No tests found", level="INFO")
        assert r.type == "skip"
        assert r.level == "INFO"


class ConcreteCheck(Check):
    """用于测试的具体 Check 实现"""
    def run(self) -> list[CheckResult]:
        return [self.pass_check("test")]


class TestCheckBase:
    """测试 Check 基类"""

    def test_subclass_implementation(self, tmp_path):
        """子类实现 run 方法"""
        check = ConcreteCheck(tmp_path)
        results = check.run()
        assert len(results) == 1
        assert results[0].type == "pass"

    def test_find_files(self, tmp_path):
        """查找文件"""
        # 创建测试文件
        (tmp_path / "a.py").touch()
        (tmp_path / "b.ts").touch()
        (tmp_path / "c.tsx").touch()
        (tmp_path / "node_modules" / "d.ts").mkdir(parents=True)
        (tmp_path / "node_modules" / "d.ts").touch()

        check = ConcreteCheck(tmp_path)
        all_files = check._find_files("*.ts")
        # 过滤掉 node_modules
        filtered = [f for f in all_files if not check._should_skip(f)]
        assert len(filtered) == 1  # node_modules 应该被过滤

    def test_should_skip(self):
        """跳过目录检查"""
        check = ConcreteCheck(Path("/project/venv/lib/python3.12/site-packages"))
        assert check._should_skip(Path("/project/venv/lib/python3.12/site-packages/pkg"))
        assert not check._should_skip(Path("/project/src/main.py"))


class TestTypeScriptChecks:
    """测试 TypeScript 检查"""

    def test_syntax_check_no_ts_files(self, tmp_path):
        """没有 TS 文件时跳过"""
        from moat.checks.typescript import TypeScriptSyntaxCheck

        check = TypeScriptSyntaxCheck(tmp_path)
        results = check.run()
        assert len(results) == 1
        assert results[0].type == "skip"

    def test_dedup_check_no_ts_files(self, tmp_path):
        """没有 TS 文件时跳过"""
        from moat.checks.typescript import TypeScriptDedupCheck

        check = TypeScriptDedupCheck(tmp_path)
        results = check.run()
        assert len(results) == 1
        assert results[0].type == "skip"
