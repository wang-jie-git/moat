# Moat 优化方案 v1.0

> 基于 2026-07-13 工程复盘：Moat 未能检测 `_build_system_prompt` 导入缺失 Bug 的根因分析与改进方案

---

## 一、核心发现：静态分析的物理边界

### 事件回顾

`ws_full_handler.py` 中调用了 `_build_system_prompt()`，但该函数未在文件顶部导入。运行时才报错。

### Moat 当时检查了什么

| 检查层级 | Moat 覆盖 | 实际结果 |
|----------|-----------|---------|
| 模块能否导入 | ✅ `from one_backend.ws_full_handler import ...` | 成功 |
| 函数是否存在 | ✅ `_build_system_prompt` 在 `ws_handler_helpers.py` 中 | 存在 |
| 函数是否被调用方正确导入 | ❌ **未覆盖** | 缺失导入，运行时崩溃 |
| 调用链是否完整 | ❌ **未覆盖** | WebSocket 连接时才报错 |

### 结论

这不是 Moat 的 Bug，是**检查覆盖范围的局限**。任何静态分析工具都有此物理边界。

---

## 二、解决方案

### 方案 A：新增 `ImportCompletenessChecker`（推荐，P0）

用 Python 的 `ast` 模块（无需额外依赖）扫描每个 Python 文件：
1. 收集文件内所有**函数调用**
2. 收集文件顶部所有**导入语句**
3. 对每个函数调用，检查它是否在导入列表、同文件定义、或内置函数中
4. 如果都不在，判定为**未绑定引用**，报错

#### 设计

```
moat/checks/import_completeness.py
├── class ImportCompletenessCheck(Check)
│   ├── run() → list[CheckResult]
│   ├── _check_file(file) → list[CheckResult]
│   ├── _collect_imports(tree) → set[str]      # 当前文件导入的符号
│   ├── _collect_definitions(tree) → set[str]  # 当前文件定义的符号
│   ├── _collect_calls(tree) → list[CallInfo]  # 当前文件调用的符号
│   └── _is_builtin(name) → bool              # 内置函数豁免
```

#### 误报抑制

- ✅ 内置函数（`print`, `len`, `str`, `dict` 等）自动豁免
- ✅ 同文件定义的函数自动豁免
- ✅ `self.xxx` / `cls.xxx` 方法调用自动豁免
- ✅ `from x import y` 中 `y` 已导入的豁免
- ✅ `import x` 后 `x.func()` 的 `x.` 前缀豁免
- ✅ 变量名调用（非函数名）自动豁免
- ✅ 测试文件可选跳过

#### 集成点

| 模式 | 集成位置 | 说明 |
|------|---------|------|
| `--full` | `runner.py:_create_full_checks()` | 扫描所有 Python 文件 |
| `--quick` | `runner.py:_run_quick_checks()` → `QuickCheck` | 只检查 git diff 修改的文件 |

---

### 方案 B：调用链运行时测试（辅助，P1）

针对关键路径（WebSocket 初始化、API 路由注册）编写集成测试，确保真实调用链完整。

```
tests/test_call_chain.py
├── test_ws_initialization_chain()
│   ├── mock 所有 ws 依赖
│   ├── 调用 ws_full_handler 的核心函数
│   └── 断言无 ImportError / AttributeError
├── test_api_route_registration()
│   ├── 遍历所有注册的路由
│   ├── 调用每个路由的处理函数
│   └── 断言无缺失导入
```

---

### 方案 C：Moat 自身测试基础设施（P1）

| 问题 | 修复 |
|------|------|
| `moat/.venv` 没有 pytest | 在 venv 中安装 `pytest` + `pytest-cov` |
| 系统 PYTHONPATH 污染导致 SRE mismatch | 在项目根目录加 `.envrc` 或 Makefile 自动清空 |
| 测试运行耗时 2 分半 | 拆分 `fast` / `full` 测试模式 |

---

## 三、实施优先级

| 优先级 | 方案 | 文件 | 工作量 | 收益 |
|--------|------|------|--------|------|
| 🔴 P0 | ImportCompletenessChecker | `moat/checks/import_completeness.py` + `runner.py` 集成 | ~150 行 | 消灭"函数存在但未导入"类 Bug |
| 🟡 P1 | 调用链集成测试 | `tests/test_call_chain.py` | ~80 行 | 运行时验证关键路径 |
| 🟡 P1 | dev 基础设施 | `.venv` + pytest 安装 | 5 行 | 开发者可本地跑测试 |
| 🟢 P2 | 测试模式拆分 | `pyproject.toml` 或 Makefile | 10 行 | 提速 CI |

---

## 四、ImportCompletenessChecker 详细设计

### 算法

```
对于每个 .py 文件:
  1. 解析 AST
  2. 收集 imports = {从 import/from 语句中提取的所有符号名}
  3. 收集 definitions = {当前文件中 def/class/async def 定义的符号名}
  4. 收集 calls = {所有函数调用表达式中的函数名}
  5. 对于每个 call in calls:
     a. 如果 call 在 imports 中 → 跳过
     b. 如果 call 在 definitions 中 → 跳过
     c. 如果 call 是内置函数 → 跳过
     d. 如果 call 是 self.xxx / cls.xxx → 跳过
     e. 如果 call 是模块.xxx（有点号）→ 检查模块是否在 imports 中
     f. 否则 → 报错: "未绑定引用: {call}"
```

### 内置函数豁免列表

```python
BUILTINS = {
    "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes",
    "callable", "chr", "classmethod", "compile", "complex", "delattr",
    "dict", "dir", "divmod", "enumerate", "eval", "exec", "filter",
    "float", "format", "frozenset", "getattr", "globals", "hasattr",
    "hash", "hex", "id", "input", "int", "isinstance", "issubclass",
    "iter", "len", "list", "locals", "map", "max", "memoryview", "min",
    "next", "object", "oct", "open", "ord", "pow", "print", "property",
    "range", "repr", "reversed", "round", "set", "setattr", "slice",
    "sorted", "staticmethod", "str", "sum", "super", "tuple", "type",
    "vars", "zip", "__import__",
    # 常见异常/类型
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
    "AttributeError", "ImportError", "RuntimeError", "StopIteration",
    "NotImplementedError", "OSError", "IOError", "FileNotFoundError",
    "True", "False", "None",
}
```

### 排除规则

| 模式 | 示例 | 处理方式 |
|------|------|---------|
| 内置函数 | `print()`, `len()` | 自动豁免 |
| 同文件定义 | `def foo(): ...` 后调用 `foo()` | 自动豁免 |
| 方法调用 | `self.foo()`, `cls.foo()` | 自动豁免（`ast.Attribute` 且 `value` 是 `Name(id='self')`） |
| 已导入符号 | `from os import path` 后调用 `path.join()` | 检查 `path` 是否在 imports 中 |
| 模块前缀 | `os.path.join()` | 检查 `os` 是否在 imports 中 |
| 变量名 | `x = lambda: ...; x()` | 自动豁免（无 `def` 定义但有赋值） |
| 装饰器 | `@app.route(...)` | 检查 `app` 是否在 imports 中 |
| 测试文件 | `test_*.py` | 默认跳过，可通过配置关闭 |

---

## 五、预期效果

### 能检测到的 Bug

| Bug 类型 | 示例 | 检测结果 |
|----------|------|---------|
| 缺失函数导入 | 调用 `_build_system_prompt()` 但未 import | ✅ `未绑定引用: _build_system_prompt` |
| 拼写错误 | 调用 `get_usr_session()` 但实际是 `get_user_session()` | ✅ 取决于是否在定义中 |
| 删除后未清理 | 删除了 `helpers.py` 中的函数但调用方还在用 | ✅ 取决于是否有其他定义来源 |

### 不能检测到的 Bug

| Bug 类型 | 原因 |
|----------|------|
| 动态导入 | `__import__()` / `importlib.import_module()` 运行时决定 |
| 字符串调用 | `getattr(obj, 'func_name')()` 无法静态分析 |
| 条件导入 | `if platform == 'win32': from ... import ...` 不在当前路径的导入 |
| 跨文件循环 | A 导入 B，B 导入 A，但初始化顺序错了 |

---

## 六、实施步骤

1. **创建 `moat/checks/import_completeness.py`** — 核心检查逻辑
2. **集成到 `runner.py`** — 在 `_create_full_checks` 和 `_run_quick_checks` 中注册
3. **编写测试** — `tests/test_import_completeness.py`
4. **运行 Moat 自检** — `moat check --full` 验证 Moat 自己通过
5. **在 One 项目上验证** — 运行 `moat check --full` 确认能发现真实问题