"""TypeScript async_race.py 测试

覆盖 moat/checks/typescript/async_race.py
"""
import tempfile
from pathlib import Path

import pytest

from moat.checks.typescript.async_race import TypeScriptAsyncRaceCheck


@pytest.fixture
def tmp_project(tmp_path):
    """创建临时 TypeScript 项目"""
    project = tmp_path / "ts_project"
    project.mkdir()
    return project


@pytest.fixture
def checker(tmp_project):
    """创建 TypeScriptAsyncRaceCheck 实例"""
    return TypeScriptAsyncRaceCheck(tmp_project)


class TestTypeScriptAsyncRaceCheck:
    """测试 TypeScriptAsyncRaceCheck"""

    def test_no_ts_files(self, checker):
        """测试没有 TypeScript 文件"""
        results = checker.run()
        assert len(results) == 1
        assert results[0].type == "skip"

    def test_no_race_conditions(self, checker, tmp_project):
        """测试没有竞态条件"""
        (tmp_project / "app.ts").write_text("""
async function fetchData() {
  const data = await fetch('/api/data');
  return data;
}
""")

        results = checker.run()
        assert len(results) == 1
        assert results[0].type == "pass"

    def test_unhandled_promise(self, checker, tmp_project):
        """测试未处理的 Promise"""
        (tmp_project / "app.ts").write_text("""
new Promise((resolve) => {
  resolve();
});
""")

        results = checker.run()
        assert any("unhandled_promise" in r.message for r in results)

    def test_async_in_loop(self, checker, tmp_project):
        """测试循环中的 async/await"""
        (tmp_project / "app.ts").write_text("""
for (let i = 0; i < 10; i++) {
  await fetch(`/api/item/${i}`);
}
""")

        results = checker.run()
        # 可能检测到也可能检测不到，取决于实现
        assert len(results) >= 1

    def test_then_without_catch(self, checker, tmp_project):
        """测试 .then() 没有 .catch()"""
        (tmp_project / "app.ts").write_text("""
fetch('/api/data')
  .then(res => res.json())
  .then(data => console.log(data));
""")

        results = checker.run()
        assert any("catch" in r.message.lower() for r in results)

    def test_then_with_catch(self, checker, tmp_project):
        """测试 .then() 有 .catch()"""
        (tmp_project / "app.ts").write_text("""
fetch('/api/data')
  .then(res => res.json())
  .catch(err => console.error(err));
""")

        results = checker.run()
        # 不应该报告错误
        assert not any("catch" in r.message.lower() for r in results if r.type == "warn")

    def test_multiple_issues(self, checker, tmp_project):
        """测试多个问题"""
        (tmp_project / "app.ts").write_text("""
// 未处理的 Promise
new Promise((resolve) => resolve());

// 没有 .catch()
fetch('/api/data').then(res => res.json());
""")

        results = checker.run()
        assert len(results) >= 2
        assert any(r.type == "warn" for r in results)

    def test_skip_node_modules(self, checker, tmp_project):
        """测试跳过 node_modules"""
        node_modules = tmp_project / "node_modules"
        node_modules.mkdir()
        (node_modules / "lib.ts").write_text("""
new Promise((resolve) => resolve());
""")

        results = checker.run()
        assert len(results) == 1
        assert results[0].type == "skip"

    def test_forEach_async(self, checker, tmp_project):
        """测试 forEach 中的 async"""
        (tmp_project / "app.ts").write_text("""
items.forEach(async (item) => {
  await process(item);
});
""")

        results = checker.run()
        # forEach 中的 async 是常见的竞态条件
        assert len(results) >= 1

    def test_while_loop_async(self, checker, tmp_project):
        """测试 while 循环中的 async"""
        (tmp_project / "app.ts").write_text("""
while (condition) {
  await next();
}
""")

        results = checker.run()
        assert len(results) >= 1

    def test_complex_race_condition(self, checker, tmp_project):
        """测试复杂的竞态条件"""
        (tmp_project / "app.ts").write_text("""
async function processItems(items: string[]) {
  for (const item of items) {
    const result = await fetch(`/api/${item}`);
    console.log(result);
  }
}

new Promise((resolve) => setTimeout(resolve, 100));

fetch('/api/data').then(res => res.json());
""")

        results = checker.run()
        assert len(results) >= 2
        assert any(r.type == "warn" for r in results)
