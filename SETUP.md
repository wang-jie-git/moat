# 🚀 Moat 安装与快速开始指南

**目标**: 5 分钟内完成安装并开始使用 Moat

---

## 📋 目录

1. [安装](#1-安装)
2. [初始化项目](#2-初始化项目)
3. [创建基线](#3-创建基线)
4. [日常使用](#4-日常使用)
5. [AI 工具集成](#5-ai-工具集成)
6. [常见问题](#6-常见问题)

---

## 1. 安装

### 方式 1: 使用 pipx（推荐）⭐

**pipx 会自动管理虚拟环境，避免污染系统 Python**

```bash
# 1. 安装 pipx（如果还没有）
brew install pipx  # macOS
# 或
pip install pipx  # 通用

# 2. 安装 Moat
pipx install moat-ai

# 3. 验证安装
moat --version
# 输出: Moat v1.0.4
```

**优点**:
- ✅ 自动隔离依赖
- ✅ 不会污染系统 Python
- ✅ 自动管理 PATH

---

### 方式 2: 使用 pip（全局安装）

```bash
# 1. 安装
pip3 install --user moat-ai

# 2. 确保 PATH 包含 pip bin 目录
export PATH="$HOME/Library/Python/3.x/bin:$PATH"

# 3. 验证安装
moat --version
```

**适合**: 只有 Moat 一个 Python 工具的简单场景

---

### 方式 3: 使用虚拟环境（项目级）

```bash
# 1. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate     # Windows

# 2. 安装 Moat
pip install moat-ai

# 3. 验证安装
moat --version
```

**适合**: 需要隔离项目依赖的场景

---

## 2. 初始化项目

### 自动初始化（推荐）

```bash
# 在你的项目根目录运行
cd /path/to/your/project
moat init
```

**moat init 会做什么？**
1. 自动检测项目类型（Python/TypeScript/Go/多语言）
2. 创建 `.moat/moat.json` 配置文件
3. 设置默认检查规则
4. 生成 `.moatignore`（排除不需要检查的文件）

**示例输出**:
```
✅ Moat 初始化完成

📊 检测到项目类型: python, typescript
📝 配置文件: .moat/moat.json
⚙️  默认规则: 5 条守门员规则

下一步:
  1. 运行 moat check 开始检查
  2. 运行 moat baseline save 创建基线
  3. 运行 moat architecture 查看架构健康
```

---

### 手动初始化

如果 `moat init` 失败，可以手动创建：

```bash
# 1. 创建 .moat 目录
mkdir -p .moat

# 2. 创建配置文件
cat > .moat/moat.json << 'JSON'
{
  "skip_patterns": [".venv", "node_modules", "__pycache__"],
  "rules": {
    "sql_injection": true,
    "api_auth": true,
    "race_condition": true,
    "error_handling": true,
    "layer_violation": true
  }
}
JSON
```

---

## 3. 创建基线

### 为什么要创建基线？

**基线 = 当前代码库的"快照"**

Moat 会把基线保存下来，以后每次检查时对比：
- 哪些文件被修改了
- 哪些文件内容变了
- 代码行数有没有突增

**类比**: 就像游戏的存档点，你想知道"从上次存档到现在，我改了什么"。

---

### 创建基线

```bash
# 在项目根目录运行
moat baseline save
```

**示例输出**:
```
✅ 基线已保存

📊 基线统计:
  文件数: 1234
  代码行数: 56789
  基线大小: 156 KB

⏱️  耗时: 2.34s
```

---

### 什么时候创建基线？

**首次使用时**（必须）:
```bash
# 1. 初始化
moat init

# 2. 创建基线（第一次）
moat baseline save

# 3. 开始使用
moat check
```

**重大变更后**（可选）:
```bash
# 完成一个大功能后，更新基线
moat baseline save
```

**定期维护**（建议每周一次）:
```bash
# 每周一更新基线，记录本周变更
moat baseline save
```

---

## 4. 日常使用

### 🎯 核心工作流

```
改代码前 → moat check
改代码后 → moat check
两次都通过 → 提交代码
```

---

### 命令速查表

#### 快速检查（默认）

```bash
# 检查修改的文件（快速，< 5 秒）
moat check
```

**适用场景**:
- ✅ 开发过程中实时检查
- ✅ 改代码前后检查
- ✅ 提交前检查

---

#### 完整检查

```bash
# 检查所有文件 + 复杂规则（较慢，1-3 分钟）
moat check --full
```

**适用场景**:
- ✅ 提交前完整检查
- ✅ 每周定期检查
- ✅ CI/CD 流水线

---

#### 增量检查

```bash
# 对比 Git 变更 + AST 影响域分析
moat check --diff
```

**适用场景**:
- ✅ Review PR 前
- ✅ 检查本次变更的影响范围

---

#### 架构健康报告

```bash
# 生成架构健康报告
moat architecture

# Markdown 格式
moat architecture --format md

# JSON 格式（用于 CI/CD）
moat architecture --format json

# 复制到剪贴板
moat architecture --copy
```

**适用场景**:
- ✅ 每周架构评审
- ✅ 技术债务追踪
- ✅ CI/CD 报告

---

#### 基线管理

```bash
# 查看当前基线
moat baseline show

# 对比基线差异
moat baseline diff

# 保存新基线
moat baseline save

# 列出所有基线
moat baseline list
```

---

### 示例工作流

#### 场景 1: 日常开发

```bash
# 早上开始工作
moat check                    # 检查修改的文件

# 改代码...
vim app.py

# 改完再检查
moat check                    # 确认没问题

# 提交前完整检查
moat check --full             # 确保所有检查通过
git commit -m "feat: add new feature"
```

---

#### 场景 2: 每周架构评审

```bash
# 1. 生成架构报告
moat architecture --format md > architecture_report.md

# 2. 查看问题
cat architecture_report.md

# 3. 如果有问题，查看详情
moat check --full

# 4. 更新基线（记录本周变更）
moat baseline save
```

---

#### 场景 3: 集成到 CI/CD

```yaml
# .github/workflows/moat.yml
name: Moat Check

on: [push, pull_request]

jobs:
  moat:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Moat
        run: pip install moat-ai

      - name: Run Moat Check
        run: moat check --full
```

---

## 5. AI 工具集成

### Claude Code 集成

```bash
# 1. 安装 Claude 适配器
moat adapter claude

# 2. Claude 会自动读取 CLAUDE.md 中的 Moat 规则
# 现在 Claude 知道要遵守 Moat 的检查规则
```

**效果**:
- Claude 改代码前会自动运行 `moat check`
- Claude 会根据 Moat 的警告修正代码

---

### Cursor 集成

```bash
# 1. 安装 Cursor 适配器
moat adapter all

# 2. Cursor 会自动读取 .cursor/rules.mdc
```

---

### Git Pre-commit Hook

```bash
# 1. 安装 pre-commit hook
moat adapter precommit

# 2. 每次提交前自动运行 moat check
# 如果检查失败，阻止提交
```

**示例**:
```bash
git commit -m "fix: bug fix"
# 🔍 [Moat] 提交前检查...
# ❌ [Moat] 检查失败。修到通过再提交。
#    moat check
# 提交被阻止
```

---

## 6. 常见问题

### Q1: moat check 失败，怎么修复？

**A**: 查看具体错误信息：

```bash
# 1. 查看详细输出
moat check --verbose

# 2. 根据错误类型查找解决方案
# - [SQL 注入] → 使用参数化查询
# - [鉴权] → 添加鉴权装饰器
# - [竞态] → 添加依赖数组
```

**常见修复**:
```python
# ❌ 错误: SQL 注入
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# ✅ 正确: 参数化查询
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

---

### Q2: moat check 太慢怎么办？

**A**: 使用快速模式或跳过架构检查

```bash
# 快速模式（只检查修改的文件，< 5 秒）
moat check --quick

# 完整模式但跳过架构检查（性能提升 4.3x）
moat check --full --skip-architecture

# 环境变量（永久配置）
export MOAT_SKIP_ARCHITECTURE=true
moat check --full
```

---

### Q3: 如何忽略某些警告？

**A**: 使用 `.moatignore` 文件

```bash
# 创建 .moatignore
cat > .moatignore << 'EOF'
# 跳过测试文件
tests/*.py
**/*_test.py

# 跳过生成的代码
**/generated/*.py

# 跳过特定文件
legacy_code.py
EOF
```

**或者在代码中添加忽略注释**:
```python
# moat: ignore=sql_injection
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")  # intentionally unsafe for demo
```

---

### Q4: 基线太大怎么办？

**A**: 清理不需要的文件

```bash
# 1. 查看基线大小
du -h .moat/baseline.json

# 2. 如果太大（>10 MB），考虑排除某些目录
# 编辑 .moat/moat.json
{
  "skip_patterns": [
    ".venv",
    "node_modules",
    "__pycache__",
    "dist",        # 添加这行
    "build"       # 添加这行
  ]
}

# 3. 重新创建基线
moat baseline save
```

---

### Q5: 如何更新 Moat？

**A**: 根据安装方式选择

```bash
# pipx 安装
pipx upgrade moat-ai

# pip 安装
pip3 install --upgrade moat-ai

# 虚拟环境
source .venv/bin/activate
pip install --upgrade moat-ai
```

---

### Q6: moat check 通过了，但 architecture 显示问题？

**A**: 这是正常的

- `moat check`: 检查代码质量（SQL 注入、鉴权等）
- `moat architecture`: 检查架构健康（依赖枢纽、熵增等）

**两者互补**，不是重复。

```bash
# 建议工作流
moat check            # 每日开发
moat architecture     # 每周评审
```

---

### Q7: 如何删除基线重新开始？

**A**: 删除基线文件并重新创建

```bash
# 1. 删除基线
rm .moat/baseline.json

# 2. 重新创建
moat baseline save
```

---

### Q8: Windows 支持吗？

**A**: 部分支持

**支持**:
- ✅ CLI 命令
- ✅ Python/TypeScript/Go 检查
- ✅ 基线对比

**不支持**:
- ❌ 实时监控（`moat watch`）
- ❌ Sidecar 守护进程（`moat sidecar`）

---

## 🎯 5 分钟快速开始

```bash
# 1. 安装（1 分钟）
pipx install moat-ai

# 2. 进入你的项目
cd /path/to/your/project

# 3. 初始化（30 秒）
moat init

# 4. 创建基线（1 分钟）
moat baseline save

# 5. 开始使用（随时）
moat check
```

---

## 📚 下一步

- [完整命令参考](README.md)
- [守门员规则详解](RULES.md)
- [贡献指南](CONTRIBUTING.md)
- [常见问题](FAQ.md)

---

## 💬 获取帮助

- 📖 [文档](https://github.com/wang-jie-git/moat)
- 🐛 [报告 Bug](https://github.com/wang-jie-git/moat/issues)
- 💡 [功能建议](https://github.com/wang-jie-git/moat/discussions)

---

**You own the code, you own the guard.** 🛡️
