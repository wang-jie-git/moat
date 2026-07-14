# Moat 架构重构方案：从"护城河"到"智能生命"

**日期**: 2026-07-10
**版本**: v0.9.0-alpha
**状态**: 📋 提案

---

## 🎯 核心理念

**Moat = Core (护城河) + Immune (免疫系统)**

- **Moat Core**: 架构守护者（守城）
- **Moat Immune**: AI 工程化测试体系（出征）

两者共享：
- One Memory（记忆）
- Gatekeeper（守门机制）
- Pain Score（痛觉感知）

---

## 📊 当前状态 vs 目标状态

### 当前状态（v0.8.0-alpha）

```
moat/
├── gatekeeper/     # ✅ 护城河核心
│   ├── ai_test/    # 🎯 AI 测试生成（位置尴尬）
├── ai_test/        # 🎯 AI 测试 CLI（独立）
├── memory/         # ✅ One Memory 桥接
├── pain/           # ✅ 痛觉评分
├── ast/            # ✅ 感知层
└── checks/         # ✅ 检查规则
```

### 目标状态（v0.9.0-alpha）

```
moat/
├── core/                       # 🏛️ Moat Core（护城河核心）
│   ├── gatekeeper/             # 守门系统
│   ├── checks/                 # 架构检查
│   ├── pain/                   # 痛觉评分
│   ├── ast/                    # 感知层
│   └── rules/                  # Karpathy Principles
│
├── immune/                     # 🛡️ Moat Immune（免疫系统）
│   ├── unit/                   # 单元测试生成
│   │   ├── generator.py        # AI 测试生成器
│   │   └── gate.py             # 测试门票规则
│   ├── contract/               # 契约测试
│   │   ├── pact_generator.py   # Pact 生成器
│   │   └── self_healing.py     # AI 自愈
│   ├── bdd/                    # BDD 测试
│   │   ├── feature_parser.py   # 需求解析
│   │   └── step_generator.py   # 步骤生成
│   ├── visual/                 # 视觉测试
│   │   ├── playwright_adapter.py
│   │   ├── ai_vision.py        # GPT-4o 视觉断言
│   │   └── pixel_diff.py       # 像素差异检测
│   └── pipeline/               # 自动化流水线
│       ├── orchestrator.py     # 流程编排
│       └── reporter.py         # 测试报告
│
├── memory/                     # 🧠 One Memory 桥接（共享）
├── cli.py                      # 统一入口
├── moat.yml                    # 总配置
└── ai_test_config.yml          # Immune 配置
```

---

## 🗺️ 迁移策略

### Phase 0: 准备（当前已完成）

- [x] `ai_test_config.yml` - 配置清单
- [x] `AI_TEST_SYSTEM.md` - 使用文档
- [x] `moat/gatekeeper/rules/test_coverage_gate.py` - 测试门票规则
- [x] `moat/gatekeeper/ai_test/gateway.py` - AI 测试生成网关

### Phase 1: 重组（1-2 天）

**目标**: 创建 `moat/immune/` 目录，移动相关文件

**步骤**:
1. 创建 `moat/immune/` 目录结构
2. 移动 `moat/gatekeeper/ai_test/gateway.py` → `moat/immune/unit/generator.py`
3. 移动 `moat/ai_test/cli.py` → `moat/immune/cli.py`
4. 更新导入路径
5. 保留 `moat/gatekeeper/rules/test_coverage_gate.py` 在 Gatekeeper 中（因为它是守门规则）

### Phase 2: CLI 重构（1 天）

**目标**: 体现 Core vs Immune 的区分

**新命令结构**:
```bash
# Core 命令（原有）
moat check              # 架构检查
moat verify             # 架构验收
moat gatekeeper check   # 守门检查
moat baseline           # 基线管理

# Immune 命令（新增）
moat immune unit --file=services/user.py    # 生成单元测试
moat immune contract --api=openapi.json     # 生成契约测试
moat immune bdd --requirement=prd.md        # 生成 BDD 测试
moat immune visual --page=/dashboard        # 视觉测试
moat immune run                              # 运行完整测试流水线
```

### Phase 3: 统一配置（1 天）

**目标**: 创建 `moat.yml` 统一配置

**示例**:
```yaml
# moat.yml
version: "0.9.0"

# Moat Core 配置
core:
  enabled: true
  gatekeeper:
    block_on_critical: true
    block_on_error: true
  karpathy_principles:
    enabled: true

# Moat Immune 配置
immune:
  enabled: true
  config: "ai_test_config.yml"

  # 单元测试
  unit:
    enabled: true
    coverage_threshold: 80
    new_code_threshold: 85

  # 契约测试
  contract:
    enabled: false  # Phase 2 再启用

  # BDD 测试
  bdd:
    enabled: false  # Phase 2 再启用

  # 视觉测试
  visual:
    enabled: false  # Phase 3 再启用
    pixel_diff_threshold: 5.0
```

### Phase 4: README 更新（半天）

**目标**: 更新 README 体现新定位

**新定位声明**:
```markdown
# Moat: 自我进化的 AI 工程操作系统

Moat = Core (护城河) + Immune (免疫系统)

- **Moat Core**: 守护你的代码库不腐烂
- **Moat Immune**: 确保你的功能不崩坏

安装一个 Moat，获得双重保护。
```

---

## 🎯 CLI 命令设计

### Core 命令（保持稳定）

```bash
moat check              # 四层门禁检查
moat check --diff       # 增量检查
moat verify             # 架构验收
moat verify --all       # 完整验收
moat gatekeeper check   # 守门检查
moat gatekeeper rules   # 查看规则
moat baseline save      # 保存基线
moat watch --log=...    # 实时监控
```

### Immune 命令（新增）

```bash
# 测试生成
moat immune unit --file=services/user.py         # 生成单元测试
moat immune unit --scope=missing                 # 生成所有缺失测试
moat immune contract --api=openapi.json          # 生成契约测试
moat immune bdd --requirement=user_story.md      # 生成 BDD 测试

# 测试执行
moat immune run                                 # 运行完整测试流水线
moat immune run --type=unit                     # 只运行单元测试
moat immune run --type=visual                   # 只运行视觉测试

# 覆盖率检查
moat immune coverage                            # 检查覆盖率
moat immune coverage --threshold=85              # 自定义阈值

# AI 视觉测试
moat immune visual --page=/dashboard            # 测试单个页面
moat immune visual --all                        # 测试所有关键页面
```

---

## 📝 实施优先级

### 🔴 高优先级（立即做）

1. **创建 `moat/immune/` 目录结构**
   - 逻辑清晰
   - 为后续开发打好基础

2. **更新 CLI 命令**
   - `moat immune unit` 替代 `moat test generate`
   - 体现 Core vs Immune 区分

3. **更新 README**
   - 新定位声明
   - "为什么 Moat 不仅能守城，还能出征"

### 🟡 中优先级（本周内）

4. **创建 `moat.yml` 统一配置**
   - Core + Immune 配置分离
   - 向后兼容（支持 `.moat/config.json`）

5. **迁移测试代码**
   - `moat/gatekeeper/ai_test/gateway.py` → `moat/immune/unit/generator.py`
   - 更新所有导入

### 🟢 低优先级（可选）

6. **统一记忆层**
   - 将 `moat/memory/` 改为共享层
   - Core 和 Immune 都通过它通信

---

## 💭 关键决策

### Q: 为什么要保持在同一仓库？

**A**:
1. **统一品牌**: `pip install moat` 即可获得所有功能
2. **代码共享**: Core 和 Immune 共享 Gatekeeper、Memory、Pain Score
3. **降低维护成本**: 一个仓库，一个 CI/CD，一个版本号
4. **开源权重**: 500 Star > 2 × 100 Star

### Q: 什么时候才需要拆分？

**A**:
- Immune 的依赖变得极其臃肿（几百个测试框架）
- 安装包体积超过 500MB
- 有独立的维护团队
- 用户明确要求轻量安装

**当前判断**: 远未到拆分的时候

### Q: 向后兼容如何处理？

**A**:
1. `moat test generate` 保留为别名（deprecated warning）
2. 支持 `.moat/config.json` 和 `moat.yml` 两种配置
3. 提供迁移脚本 `moat migrate-config`

---

## 🚀 立即行动

我建议现在做这三件事：

### 1. 创建 `moat/immune/` 目录结构

```bash
mkdir -p moat/immune/{unit,contract,bdd,visual,pipeline}
```

### 2. 更新 README

添加新的定位声明和架构说明

### 3. 更新 CLI

```python
# moat/cli.py
def cmd_immune(args):
    """Moat Immune - AI 工程化测试体系"""
    from moat.immune.cli import cmd_immune
    return cmd_immune(args)
```

---

## 📚 参考资料

- **AI 测试体系配置**: `ai_test_config.yml`
- **使用文档**: `AI_TEST_SYSTEM.md`
- **Phase 1 完成报告**: `PHASE1_COMPLETE.md`

---

**你觉得这个方案如何？想现在就动手重构吗？** 🛠️
