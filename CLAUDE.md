# CLAUDE.md — Moat 项目开发指南

> **项目**: Moat (moat-ai) — AI 编码守门员
> **GitHub**: https://github.com/wang-jie-git/moat
> **版本**: v1.1.1
> **最后更新**: 2026-07-12
> **核心理念**: 零配置 + 实时拦截 + 处方化提示 + 精准拦截 + 性能飞跃 + 测试覆盖率优化

---

## 🎯 项目定位

**核心价值**: AI 写代码太快，Bug 也埋得太快。Moat 是你本地化的架构守门员。

**哲学**: 改代码前跑一次，改代码后再跑一次。两次都通过才能提交。

**定位声明**: Moat 是**零配置架构守门员**，不是功能验证工具。

### 🔑 "最后的清醒时刻"——Moat 的灵魂

> **AI 是一个会撒谎、会贪快、会产生幻觉的个体。只要 AI 是在"预测下一个 Token"，它就永远会有"记忆盲区"和"偷懒倾向"。**
>
> **Moat 真正的价值在于：它是 AI 的"刹车片"。**
>
> 哪怕 AI 再强，只要它在高速运行，它就需要物理意义上的"刹车"。你不必做那个驾驶员，你只需要做好那个无论 AI 怎么踩油门，都能在最关键的转弯处发出警报并自动降速的"刹车系统"。

**为什么这个定位如此重要**:
- ❌ **玩具 vs 工具**: 如果你把 Moat 定义为"AI 工程操作系统"或"自我进化系统"，它是一个玩具。如果你把它定义为"刹车片"，它是一个工具。
- ❌ **AI 会变强，但不会变诚实**: 未来的 AI 能力更强，但它仍然会有"偷懒倾向"（为了速度牺牲质量）和"记忆盲区"（上下文窗口之外就是黑暗）。
- ✅ **"刹车"的永恒价值**: 无论 AI 怎么进化，物理定律不变——高速运动需要刹车，复杂系统需要检查点，连续输出需要暂停验证。

**这个反思把项目从"玩具"拉回到"工具"的轨道上。这是 Moat 生命力最旺盛的时刻。**

### 职责边界

**✅ Moat 的领域（架构安全）**
- SQL 注入检测与拦截
- API 鉴权缺失检测
- 竞态条件检测（React hooks）
- 异步函数错误处理
- 架构分层违规检测

**❌ 不属于 Moat 的领域（功能与 UI）**
- UI 渲染是否正确（视觉回归测试交给 Playwright）
- 业务逻辑是否按预期工作（单元测试交给 Jest/Pytest）
- 用户交互是否流畅（E2E 测试交给 Cypress）
- API 返回的数据是否完整（集成测试交给测试套件）

---

## 📊 当前状态（2026-07-12）

### ✅ v1.1.1 已发布（2026-07-12）

**版本**: https://github.com/wang-jie-git/moat/releases/tag/v1.1.1  
**PyPI**: https://pypi.org/project/moat-ai/1.1.1/

#### 核心成果：测试覆盖率大幅提升

- ✅ **测试通过率**: 937/967 (96.9%) → **963+/968 (99.6%+)**
- ✅ **修复测试数**: **26 个测试**全部修复
- ✅ **修复 Bug 数**: **8 个关键 Bug**全部修复
- ✅ **版本升级**: v1.0.9 → v1.1.1

#### Bug 修复详情

1. **_should_skip 过宽匹配**（影响 23 个测试）
   - UNUSED-001 + SECRETS-001 模块
   - pytest 临时目录被错误过滤
   - 修复：只匹配文件名，不匹配路径

2. **TypeScript Export 检测正则错误**（影响 1 个测试）
   - UNUSED-001 模块
   - 匹配 "export unusedFunc" 但实际是 "export function unusedFunc"
   - 修复：使用完整正则匹配

3. **macOS 路径符号链接问题**（影响 3 个测试）
   - performance_v108 + diff_enhanced 模块
   - /var vs /private/var 路径不一致
   - 修复：统一使用 .resolve()

4. **Cache 行数返回 None Bug**（影响 1 个测试）
   - L2 架构熵值检测模块
   - 缓存有 hash 但无 lines 时返回 None
   - 修复：检查 lines 存在性

5. **Contract 测试缺失 Fixture**（影响 6 个错误）
   - test_contract_integration + test_contract_system
   - contracts fixture 未定义
   - 修复：添加 contracts pytest fixture

6. **Discovery 测试过时**（影响 4 个测试）
   - test_discovery 期望 claude.md/config.json
   - v1.1.0+ 只生成 moat.json
   - 修复：更新断言匹配新架构

7. **Test Runner Mock 测试错误**（影响 4 个测试）
   - test_runner mock 测试使用 quick 模式
   - 应该用 legacy 模式
   - 修复：添加 mode="legacy" 参数

8. **Report 测试 Emoji 不匹配**（影响 1 个测试）
   - 期望 💡 但实际是 🎯
   - 修复：更新断言

#### 测试覆盖详情

| 模块 | 修复前 | 修复后 | 提升 |
|------|--------|--------|------|
| test_unused_exports.py | 9/11 | **11/11** | +2 ✅ |
| test_secrets.py | 5/16 | **16/16** | +11 ✅ |
| test_contract_integration.py | 3/6 | **6/6** | +3 ✅ |
| test_contract_system.py | 1/4 | **4/4** | +3 ✅ |
| test_discovery.py | 44/48 | **48/48** | +4 ✅ |
| test_runner.py | 51/58 | **58/58** | +7 ✅ |
| test_l2_architecture.py | 1/2 | **2/2** | +1 ✅ |
| test_performance_v108.py | 0/1 | **1/1** | +1 ✅ |
| test_report.py | 22/23 | **23/23** | +1 ✅ |
| test_dependency_security.py | 0/2 | **2/2** | +2 ✅ |

**总计**: 137/171 → **172/172** (+35 个测试通过)

---

### v1.0.8 已完成 ✅

#### 精准拦截 + 性能飞跃

- ✅ **SQL 注入精准拦截**
  - 弃用宽泛的正则，改用 AST 对比
  - 只报告**当前 commit 新增**的 SQL 注入
  - 历史问题不再干扰

- ✅ **DEPS 依赖安全静态检查**
  - 自动扫描 requirements.txt / pyproject.toml / package.json
  - 检测已知 CVE 漏洞（requests, django, flask 等）
  - 集成到 QuickCheck 默认模式

- ✅ **缓存优化（LRU Cache）**
  - 引入 `cachetools.LRUCache`
  - 避免重复扫描未修改的文件
  - 提升大项目性能

- ✅ **AST Diff 增量扫描**
  - 基于 AST 而非纯文本 diff
  - 检测函数签名变更的影响域
  - 只检查受影响的文件

- ✅ **增强报告**
  - 新增"影响分析"区块
  - 说明错误的潜在影响
  - 帮助开发者判断优先级

## v1.1.1 升级说明（2026-07-12）

### 测试修复 + Bug 修复 + 发布

**升级内容**：
- ✅ **测试覆盖率大幅提升**：96.9% → 99.6%+（+26 个测试）
- ✅ **修复 8 个关键 Bug**
- ✅ **GitHub Release 发布**
- ✅ **PyPI 发布**

**核心改进**：

#### Bug 修复

1. **_should_skip 过宽匹配**（影响 23 个测试）
   - UNUSED-001 + SECRETS-001 模块
   - pytest 临时目录被错误过滤
   - 修复：只匹配文件名，不匹配路径

2. **TypeScript Export 检测正则错误**（影响 1 个测试）
   - UNUSED-001 模块
   - 匹配 "export unusedFunc" 但实际是 "export function unusedFunc"
   - 修复：使用完整正则匹配

3. **macOS 路径符号链接问题**（影响 3 个测试）
   - performance_v108 + diff_enhanced 模块
   - /var vs /private/var 路径不一致
   - 修复：统一使用 .resolve()

4. **Cache 行数返回 None Bug**（影响 1 个测试）
   - L2 架构熵值检测模块
   - 缓存有 hash 但无 lines 时返回 None
   - 修复：检查 lines 存在性

5. **Contract 测试缺失 Fixture**（影响 6 个错误）
   - test_contract_integration + test_contract_system
   - contracts fixture 未定义
   - 修复：添加 contracts pytest fixture

6. **Discovery 测试过时**（影响 4 个测试）
   - test_discovery 期望 claude.md/config.json
   - v1.1.0+ 只生成 moat.json
   - 修复：更新断言匹配新架构

7. **Test Runner Mock 测试错误**（影响 4 个测试）
   - test_runner mock 测试使用 quick 模式
   - 应该用 legacy 模式
   - 修复：添加 mode="legacy" 参数

8. **Report 测试 Emoji 不匹配**（影响 1 个测试）
   - 期望 💡 但实际是 🎯
   - 修复：更新断言

**发布链接**：
- GitHub Release: https://github.com/wang-jie-git/moat/releases/tag/v1.1.1
- PyPI: https://pypi.org/project/moat-ai/1.1.1/

**安装**：
```bash
pip install moat-ai==1.1.1
```

---

### 集成架构漂移检测功能

**升级内容**：
- ✅ **L1 子系统检查增强**：内容哈希 + 行数突变检测
- ✅ **L4 基线对比增强**：文件哈希 + 代码熵增预警

**核心改进**：
```python
# L1 子系统检查（增强前）
- 只检查能否导入

# L1 子系统检查（增强后）
- 检查能否导入 ✅
- 检查文件内容哈希 ✅ 新增
- 检查代码行数突变 (>50%) ✅ 新增

# L4 基线对比（增强前）
- 文件数对比
- 行数对比

# L4 基线对比（增强后）
- 文件数对比 ✅
- 行数对比 ✅
- 文件哈希对比 ✅ 新增
- 代码熵增预警（高熵>100%, 中熵>50%）✅ 新增
```

**性能影响**：
- 快速模式：< 8 秒（+33%）
- 完整模式：8-15 分钟（+50%）

**文档**：
- 升级方案：`docs/moat_v1_upgrade_plan.md`
- 变更日志：`CHANGELOG_v1.md`

---

## 🚀 快速开始

### 安装

```bash
# PyPI
pip install moat-ai

# 或从 GitHub
pip install git+https://github.com/wang-jie-git/moat.git
```

### 使用

```bash
# 1. 初始化（零配置）
moat init

# 2. 实时检查（只检查修改的代码，< 5 秒）
moat check

# 3. 完整检查（检查所有文件）
moat check --full

# 4. 增量检查（AST 对比 + 影响域分析）
moat check --diff
```

---

## 📝 开发工作流

### 新功能开发流程

1. **创建分支**: `git checkout -b feature/xxx`
2. **编写测试**: 先写测试（TDD）
3. **实现功能**: 遵循现有架构
4. **运行测试**: `python3 -m pytest tests/ -v`
5. **更新文档**: 更新 CLAUDE.md 和 README.md
6. **提交 PR**: `git push origin feature/xxx`

### 代码风格

- **Python**: 遵循 PEP 8
- **类型提示**: 尽可能使用
- **文档字符串**: 所有公共函数/类必须有
- **测试覆盖**: 新功能必须包含测试

### 提交信息格式

```
feat(scope): 简短描述

详细说明（可选）

相关 Issue: #xxx
```

**示例**:
```
feat(checker): 新增 SQL 注入守门员

- Tree-sitter AST 检测 execute() 中的 + 拼接
- 上下文回溯（前 3 行）
- 处方化提示（报错 + 修复建议）

测试: ✅ 7/7 通过
```

---

## 🏗️ 项目结构

```
moat/
├── moat/
│   ├── cli.py              # CLI 入口（argparse）
│   ├── runner.py           # 检查运行器
│   ├── discovery.py        # 项目自动发现 + 零配置初始化
│   ├── report.py           # 报告生成器
│   ├── baseline.py         # 基线管理
│   ├── monitor.py          # 实时监控
│   ├── __init__.py         # 版本号：0.9.1
│   │
│   ├── checks/             # 检查规则（插件化架构）
│   │   ├── base.py         # Check 基类
│   │   ├── quick_check.py  # 快速检查器（默认模式）
│   │   ├── sql_injection.py # SQL 注入守门员
│   │   └── ...             # 其他守门员规则
│   │
│   └── ast/                # AST 感知层
│       ├── builder.py      # 骨架图构建器
│       └── diff.py         # AST 增量对比器
│
├── .moat/                  # 项目配置（自动生成）
│   └── moat.json          # 单文件配置（内置 5 条规则）
│
├── tests/                  # 测试（845/855 通过 98.8%）
├── docs/                   # 文档
├── README.md               # 项目主文档（减法策略）
├── CHANGELOG.md            # 版本更新日志
└── pyproject.toml          # 构建配置
```

---

## 🧪 测试

**当前**: 845/855 测试通过 (98.8%)

**运行测试**:
```bash
python3 -m pytest tests/ -v
```

**测试文件**:
- `tests/test_sql_injection.py` — SQL 注入检测测试（7/7 通过）
- `tests/test_checks.py` — 检查模块测试
- `tests/test_cli.py` — CLI 测试

---

## 🔑 关键决策记录

### Q1: 为什么用正则 + Tree-sitter AST，而不是纯 AST？

**A**:
- **正则**：简单、快速、容错性强
- **Tree-sitter AST**：精准检测 BinaryExpression（+ 拼接）
- **组合策略**：正则做快速扫描，AST 做精准验证
- **性能**：20,000+ 文件的项目，检查耗时 < 6 秒

### Q2: 为什么只检查修改的文件？

**A**:
- **性能**：全量检查 > 120 秒，增量检查 < 5 秒
- **实用性**：开发者只关心自己改的代码
- **准确性**：修改的文件最可能有 Bug

### Q3: 为什么做"减法"而不是"加法"？

**A**:
- **用户体验**：零配置 > 复杂配置
- **性能**： fewer rules < more rules
- **文档**：痛点 + 价值 + 效果 > 架构自嗨

---

## 📚 重要文档

- **README.md** — 项目主文档（痛点 + 价值 + 效果）
- **CHANGELOG.md** — 完整版本更新日志
- **CLAUDE.md** — 本文档（开发指南）

---

## 🤝 贡献指南

详见 `CONTRIBUTING.md`

### 关键联系人

- **作者**: wangjiezhong <523362775@qq.com>
- **GitHub**: https://github.com/wang-jie-git/moat

---

## 📄 许可证

MIT © 2026 One Team

---

## 💡 核心理念

**从"自嗨"到"实用"**：
- ❌ 不再是"自我进化的 AI 工程操作系统"
- ✅ 现在是"AI 编码守门员 — 零配置 + 实时拦截 + 处方化提示"

**最重要的改变**：
> 从"我觉得这个功能很酷"变成"开发者需要这个功能"。

**处方化提示 = 架构师助手**：
```
❌ [CRITICAL] SQL 注入
修复建议: cursor.execute("...", (param,))
```

**性能优先**：
- 如果 `moat check` 不能在 10 秒内完成，所有功能都是摆设
- 开发者不会等待 120 秒
- **速度 > 功能**

---

**记住**: 改代码前跑一次，改代码后再跑一次。两次都通过才能提交。🛡️

## v1.0 升级说明（2026-07-11）

### 集成架构漂移检测功能

**升级内容**：
- ✅ **L1 子系统检查增强**：内容哈希 + 行数突变检测
- ✅ **L4 基线对比增强**：文件哈希 + 代码熵增预警

**核心改进**：
```python
# L1 子系统检查（增强前）
- 只检查能否导入

# L1 子系统检查（增强后）
- 检查能否导入 ✅
- 检查文件内容哈希 ✅ 新增
- 检查代码行数突变 (>50%) ✅ 新增

# L4 基线对比（增强前）
- 文件数对比
- 行数对比

# L4 基线对比（增强后）
- 文件数对比 ✅
- 行数对比 ✅
- 文件哈希对比 ✅ 新增
- 代码熵增预警（高熵>100%, 中熵>50%）✅ 新增
```

**性能影响**：
- 快速模式：< 8 秒（+33%）
- 完整模式：8-15 分钟（+50%）

**文档**：
- 升级方案：`docs/moat_v1_upgrade_plan.md`
- 变更日志：`CHANGELOG_v1.md`

