# Moat 优化规则文档（Ponytail 集成）

> **版本**: v1.0.6
> **创建时间**: 2026-07-11
> **参考项目**: [Ponytail](https://github.com/DietrichGebert/ponytail)

---

## 📖 目录

1. [概述](#概述)
2. [规则清单](#规则清单)
   - [复杂度规则（3 条）](#复杂度规则)
   - [YAGNI 规则（6 条）](#yagni规则)
   - [TypeScript 专项检查（2 条）](#typescript-专项检查)
   - [标准库优先检查（1 条）](#标准库优先检查)
3. [技术债务分类](#技术债务分类)
4. [配置选项](#配置选项)
5. [使用方法](#使用方法)
6. [最佳实践](#最佳实践)

---

## 概述

Moat 的优化检查器（OptimizationCheck）基于 Ponytail 的三大核心原则：

1. **YAGNI (You Ain't Gonna Need It)**：检测过度工程化
2. **复杂度控制**：圈复杂度、认知复杂度、函数长度
3. **标准库优先**：优先使用标准库而非第三方依赖

### 设计哲学

- **异步触发**：默认关闭优化检查，需要时通过 `--optimize` 启用
- **数据驱动**：每条规则有唯一的 `rule_id`，便于报告统计和配置
- **技术债务分类**：结果按类别分组（code_simplification / complexity / standard_library）

---

## 规则清单

### 复杂度规则

#### COMPLEX-001：圈复杂度超标

**严重性**: medium
**类别**: complexity
**默认阈值**: 10

**描述**: 函数圈复杂度超过阈值，建议拆分。

**圈复杂度计算规则（McCabe）**:
- 基础值：1
- 每个分支结构（if、for、while、except、with）：+1
- 布尔运算符（and、or）：每个额外值 +1
- 三元运算符：+1

**示例**:

```python
# ❌ 圈复杂度 5 > 10
def complex_function(x, y):
    if x > 0:           # +1
        for i in range(10):  # +1
            if y > 0:    # +1
                print(i)
    elif x < 0:         # +1
        print("negative")
    else:               # +1
        print("zero")

# ✅ 拆分为多个小函数
def process_positive(x, y):
    for i in range(10):
        if y > 0:
            print(i)

def handle_negative():
    print("negative")

def handle_zero():
    print("zero")

def complex_function(x, y):
    if x > 0:
        return process_positive(x, y)
    elif x < 0:
        return handle_negative()
    else:
        return handle_zero()
```

**修复建议**:
- 将复杂函数拆分为多个小函数（每个 < 10 复杂度）
- 使用策略模式或状态机替代复杂的条件判断
- 提取公共逻辑到独立函数

---

#### COMPLEX-002：函数过长

**严重性**: low
**类别**: complexity
**默认阈值**: 50 行

**描述**: 函数长度超过阈值，建议拆分。

**示例**:

```python
# ❌ 函数 80 行 > 50 行
def long_function():
    # ... 80 行代码 ...
    pass

# ✅ 拆分为多个小函数
def part1():
    # ... 30 行 ...

def part2():
    # ... 30 行 ...

def part3():
    # ... 20 行 ...

def long_function():
    part1()
    part2()
    part3()
```

**修复建议**:
- 按逻辑块拆分函数
- 提取辅助函数
- 使用类封装相关函数

---

#### COMPLEX-003：认知复杂度超标

**严重性**: medium
**类别**: complexity
**默认阈值**: 15

**描述**: 函数认知复杂度超过阈值，建议简化逻辑。

**认知复杂度计算规则（SonarSource）**:
- 顺序执行结构（if、for、while、with、try）：+1
- if-else：else 分支额外 +1
- 循环（for、while）：+2
- 嵌套结构：每增加一层嵌套 +1
- 递归：+3

**示例**:

```python
# ❌ 认知复杂度 6 > 15
def nested_logic(x, y):
    if x > 0:          # +1
        for i in range(10):  # +2
            if y > 0:   # +1 (嵌套 +1)
                while True:  # +2 (嵌套 +1)
                    try:
                        if i % 2 == 0:  # +1 (嵌套 +2)
                            print(i)
                    except:  # +1
                        break

# ✅ 简化逻辑
def handle_even(i):
    if i % 2 == 0:
        print(i)

def process_item(i):
    try:
        handle_even(i)
    except:
        pass

def nested_logic(x, y):
    if x > 0:
        for i in range(10):
            if y > 0:
                while True:
                    process_item(i)
                    break
```

**修复建议**:
- 减少嵌套层级
- 使用卫语句（Guard Clauses）
- 提取嵌套逻辑到独立函数
- 使用多态替代复杂的条件判断

**参考**:
- [SonarSource Cognitive Complexity](https://www.sonarsource.com/resources/why-cognitive-complexity/)

---

### YAGNI 规则

#### YAGNI-001：未使用的导入

**严重性**: low
**类别**: code_simplification

**描述**: 检测未使用的 import，避免冗余依赖。

**Python 检查规则**:
- import 语句 > 5 个时触发警告

**TypeScript 检查规则**:
- import 语句 > 10 个时触发警告

**示例**:

```python
# ❌ 过多的导入
import os
import sys
import json
import re
import ast
import typing
import collections
import itertools
import functools

# ✅ 只导入需要的
import json
import re
```

**修复建议**:
- 删除未使用的 import
- 使用工具自动清理（如 `autoflake`）

---

#### YAGNI-002：未处理的 TODO/FIXME

**严重性**: low
**类别**: code_simplification

**描述**: 检测过多的 TODO/FIXME 注释，建议及时处理。

**触发条件**:
- Python：`# TODO` / `# FIXME` / `# XXX` > 3 个
- TypeScript：`// TODO` / `// FIXME` / `// XXX` > 3 个

**示例**:

```python
# ❌ 过多的 TODO
def foo():
    # TODO: 实现这个函数
    pass

def bar():
    # FIXME: 修复这个bug
    pass

def baz():
    # TODO: 添加验证
    pass

def qux():
    # TODO: 优化性能
    pass

# ✅ 及时处理或删除 TODO
def foo():
    # 已实现
    return True
```

**修复建议**:
- 实现 TODO 对应的功能
- 删除已过时的 TODO
- 将重要的 TODO 转换为 Issue 并添加链接

---

#### YAGNI-003：过度抽象

**严重性**: medium
**类别**: code_simplification

**描述**: 检测过多的函数/类/接口定义，可能存在过度设计。

**触发条件**:
- Python：函数 + 类 > 20 个
- TypeScript：interface + type > 10 个

**示例**:

```typescript
// ❌ 过多的接口定义
interface IUser {}
interface IPost {}
interface IComment {}
interface IAuth {}
interface IRole {}
interface IPermission {}
interface ILogger {}
interface IConfig {}
interface IValidator {}
interface ISerializer {}
interface IDeserializer {}

// ✅ 合并相关接口
interface IUser {
  post: IPost[];
  comments: IComment[];
}
```

**修复建议**:
- 合并相关接口/类型
- 删除未使用的定义
- 遵循 YAGNI 原则：只在需要时抽象

---

#### YAGNI-004：死代码检测

**严重性**: medium
**类别**: code_simplification

**描述**: 检测无法访问的代码（return/raise/break 后的代码）。

**检测场景**:
1. return 语句后的代码
2. raise 语句后的代码
3. break/continue 后的代码（在循环中）

**示例**:

```python
# ❌ 死代码
def foo():
    return 1
    print("这行代码永远不会执行")  # 死代码

def bar():
    raise Exception("error")
    cleanup()  # 死代码

# ✅ 删除死代码
def foo():
    return 1

def bar():
    raise Exception("error")
```

**修复建议**:
- 删除 return/raise 后的代码
- 将 cleanup 逻辑移到 raise 前（使用 finally）

---

#### YAGNI-005：过度注释

**严重性**: low
**类别**: code_simplification

**描述**: 注释行数超过代码行数的 30%，建议精简。

**触发条件**:
- 注释行数 / 代码行数 > 30%
- 连续注释 > 10 行

**示例**:

```python
# ❌ 过度注释
# 这个函数用于计算用户的年龄
# 参数：
#   - birth_date: 出生日期
#   - today: 今天日期
# 返回：
#   - 年龄（整数）
# 异常：
#   - ValueError: 如果日期无效
def calculate_age(birth_date, today):
    # 计算年龄
    # 首先计算年份差
    age = today.year - birth_date.year
    # 然后检查是否过了生日
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        # 如果还没过生日，年龄减 1
        age -= 1
    # 返回年龄
    return age

# ✅ 精简注释
def calculate_age(birth_date, today):
    """计算年龄（满周岁）"""
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age
```

**修复建议**:
- 删除显而易见的注释
- 使用文档字符串（docstring）替代行内注释
- 只在复杂逻辑处添加注释

---

#### YAGNI-006：重复代码

**严重性**: medium
**类别**: code_simplification
**默认状态**: 关闭（性能原因，通过 `check_duplicate_code=True` 启用）

**描述**: 检测相似代码块（≥5 行），建议提取函数。

**检测算法**:
- 滑动窗口：检查 ≥5 行的代码块
- 字符串匹配：简化版（非精确 AST）
- 性能优化：默认关闭

**示例**:

```python
# ❌ 重复代码
def calculate_user_age(birth_date):
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age

def calculate_pet_age(birth_date):
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age

# ✅ 提取公共函数
def calculate_age(birth_date):
    """计算年龄（通用）"""
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age

def calculate_user_age(birth_date):
    return calculate_age(birth_date)

def calculate_pet_age(birth_date):
    return calculate_age(birth_date)
```

**修复建议**:
- 提取公共逻辑到独立函数
- 使用参数化函数
- 考虑使用装饰器或混入（Mixin）

---

### TypeScript 专项检查

#### TS-001：any 类型滥用

**严重性**: medium
**类别**: type_safety

**描述**: 使用 any 类型会失去 TypeScript 的类型安全优势。

**触发条件**:
- `any` 类型出现 > 3 次：警告
- `any` 类型出现 1-3 次：提示

**示例**:

```typescript
// ❌ any 类型滥用
function process(data: any): any {
    return data;
}

// ✅ 使用具体类型
interface User {
    name: string;
    age: number;
}

function process(data: User): User {
    return data;
}

// ✅ 必要时使用 unknown
function process(data: unknown): unknown {
    if (typeof data === 'object' && data !== null) {
        return data;
    }
    throw new Error('Invalid data');
}
```

**修复建议**:
- 使用具体类型替代 `any`
- 必要时使用 `unknown`（更安全）
- 使用类型守卫（Type Guards）

---

#### TS-002：过度嵌套的三元运算符

**严重性**: medium
**类别**: readability

**描述**: 嵌套三元运算符难以阅读，建议改用 if-else。

**触发条件**:
- 嵌套层级 > 2

**示例**:

```typescript
// ❌ 过度嵌套
const status = condition1
    ? condition2
        ? condition3
            ? 'active'
            : 'inactive'
        : 'pending'
    : 'disabled';

// ✅ 改用 if-else
let status: string;
if (condition1) {
    if (condition2) {
        if (condition3) {
            status = 'active';
        } else {
            status = 'inactive';
        }
    } else {
        status = 'pending';
    }
} else {
    status = 'disabled';
}

// ✅ 或使用对象映射
const statusMap = {
    true: {
        true: {
            true: 'active',
            false: 'inactive',
        },
        false: 'pending',
    },
    false: 'disabled',
};
const status = statusMap[condition1][condition2][condition3];
```

**修复建议**:
- 改用 if-else 语句
- 使用对象映射（Object Mapping）
- 提取为独立函数

---

### 标准库优先检查

#### STDLIB-001：使用标准库替代 requests

**严重性**: info
**类别**: standard_library

**描述**: 轻度使用可考虑 urllib.request（标准库），减少第三方依赖。

**检查的包**:

| 第三方包 | 标准库替代方案 | 适用场景 |
|---------|--------------|---------|
| `requests` | `urllib.request` | HTTP 请求 |
| `numpy` | `array` module | 轻度数组操作 |
| `pandas` | `csv` module | 轻度 CSV 处理 |
| `tqdm` | 手动进度条（10 行内） | 轻度进度条 |

**示例**:

```python
# ❌ 轻度使用 requests
import requests

response = requests.get('https://api.example.com/data')
data = response.json()

# ✅ 使用标准库
from urllib.request import urlopen
import json

with urlopen('https://api.example.com/data') as response:
    data = json.loads(response.read())
```

**修复建议**:
- 评估第三方依赖的使用频率
- 轻度使用优先考虑标准库
- 重度使用（如数据分析）继续使用第三方库

---

## 技术债务分类

Moat 将优化检查结果分为三类技术债务：

### 1. code_simplification（代码精简空间）

**包含规则**:
- YAGNI-001：未使用的导入
- YAGNI-002：未处理的 TODO/FIXME
- YAGNI-003：过度抽象
- YAGNI-004：死代码检测
- YAGNI-005：过度注释
- YAGNI-006：重复代码

**处理优先级**: 高
**原因**: 直接影响代码可读性和维护成本

---

### 2. complexity（复杂度债务）

**包含规则**:
- COMPLEX-001：圈复杂度超标
- COMPLEX-002：函数过长
- COMPLEX-003：认知复杂度超标

**处理优先级**: 中
**原因**: 增加理解和修改代码的难度

---

### 3. standard_library（标准库优化）

**包含规则**:
- STDLIB-001：使用标准库替代第三方包
- TS-001 ~ TS-002：TypeScript 优化

**处理优先级**: 低
**原因**: 不影响功能，但可以优化依赖

---

## 配置选项

### 全局配置（`.moat/config.json`）

```json
{
  "optimization": {
    "enabled": false,
    "max_complexity": 10,
    "max_function_length": 50,
    "max_cognitive_complexity": 15,
    "check_yagni": true,
    "check_dead_code": true,
    "check_duplicate_code": false,
    "check_stdlib": true
  }
}
```

### CLI 参数

```bash
# 启用优化检查
moat check --quick --optimize
moat check --full --optimize
```

---

## 使用方法

### 基础用法

```bash
# 1. 快速检查 + 优化（只检查修改的文件）
moat check --quick --optimize

# 2. 完整检查 + 优化（检查所有文件）
moat check --full --optimize

# 3. 生成技术债务报告
moat report
```

### 查看优化规则

```bash
# 列出所有优化规则
python3 -c "
from moat.checks.optimization import OPTIMIZATION_RULES
for rule in OPTIMIZATION_RULES.values():
    print(f\"{rule['id']}: {rule['name']} ({rule['severity']})\")
"
```

### 自定义配置

```json
{
  "optimization": {
    "max_complexity": 15,
    "max_function_length": 80,
    "max_cognitive_complexity": 20,
    "check_duplicate_code": true
  }
}
```

---

## 最佳实践

### 1. 日常工作流

```bash
# 开发时：快速检查 + 优化
moat check --quick --optimize

# 提交前：完整检查 + 优化 + 报告
moat check --full --optimize && moat report
```

### 2. 技术债务管理

- **高优先级**：立即修复 code_simplification 类别的警告
- **中优先级**：定期重构 complexity 类别的警告
- **低优先级**：有空时处理 standard_library 类别的警告

### 3. CI/CD 集成

```yaml
# GitHub Actions 示例
- name: Run Moat with Optimization
  run: |
    pip install moat-ai
    moat init
    moat check --full --optimize
```

### 4. 规则自定义

根据项目需求调整阈值：

```json
{
  "optimization": {
    "max_complexity": 15,
    "max_function_length": 100,
    "max_cognitive_complexity": 20
  }
}
```

---

## 性能影响

| 模式 | 耗时 | 优化检查耗时 | 总耗时 |
|------|------|------------|--------|
| 快速模式（无优化） | 0.2s | - | 0.2s |
| 快速模式 + 优化 | 0.2s | +0.1s | 0.3s |
| 完整模式（无优化） | 5s | - | 5s |
| 完整模式 + 优化 | 5s | +2s | 7s |

**结论**: 优化检查增加约 40% 的检查时间，但带来的代码质量提升值得。

---

## 参考资源

- **原 Ponytail 项目**: https://github.com/DietrichGebert/ponytail
- **认知复杂度规范**: https://www.sonarsource.com/resources/why-cognitive-complexity/
- **Moat 文档**: [README.md](../README.md)
- **更新日志**: [CHANGELOG.md](../CHANGELOG.md)

---

**最后更新**: 2026-07-11
**版本**: v1.0.6
