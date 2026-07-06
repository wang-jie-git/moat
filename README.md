# Moat — AI 编码护城河

改代码**前**跑一次，改代码**后**再跑一次。两次都通过才能提交。

防止 AI 工具修一个 bug 出三个 bug。

## 为什么

AI 改代码很快。AI 搞坏系统也很快。

修一个 bug 出三个 bug 的根本原因：**改代码的人不熟悉系统的所有子系统**。Moat 的四层防线在改代码前/后各跑一次，12 秒内告诉你系统有没有被搞坏。

## 安装

```bash
pip install moat

# 或带 Web 看板
pip install "moat[dashboard]"
```

## 使用

### 1. 初始化

```bash
cd your-project
moat init
```

自动检测项目结构，保存基线数据，生成 AI 适配规则。

### 2. 改代码前/后检查

```bash
moat check
```

12 秒跑完四层防线：

| 层级 | 作用 |
|------|------|
| **L0 语法** | 所有 Python 文件无语法错误 |
| **L1 存活** | import 正常、API 能返回 200、核心模块能实例化、关键文件存在 |
| **L2 结构** | API 返回的 JSON 字段符合契约（防前后端断裂） |
| **L3 关联** | 改了 A，B 还能用（防修一个出三个） |
| **L4 基线** | 文件数不减少、代码量不退化（防隐性删除） |

### 3. 实时监控

```bash
moat watch --log logs/backend.log
```

服务器运行中实时监控日志错误，分级着色显示。

### 4. Web 看板

```bash
moat dashboard
```

浏览器打开 `http://localhost:9876` 查看错误看板：

- 实时错误列表（自动刷新）
- 运行/保存基线
- 项目状态总览

### 5. AI 适配器

```bash
# 安装所有 AI 工具适配器
moat adapter all

# 只安装 CLAUDE.md
moat adapter claude

# 只安装 pre-commit hook
moat adapter precommit
```

各 AI 工具（Claude Code、Cursor、Codex、Copilot）在改代码时自动遵从 Moat 铁律。

### 6. 基线管理

```bash
# 保存当前状态为基线
moat baseline save

# 查看基线
moat baseline show

# 对比当前与基线
moat baseline diff
```

## 完整示例

```bash
# 初始化
cd /path/to/project
moat init

# 改代码前
moat check

# 改代码...
# 改代码后
moat check

# 通过后提交
git add .
git commit -m "fix: ..."

# 服务器运行时实时监控
moat watch --log logs/backend.log
```

## 与 CI 集成

在 GitHub Actions 中添加：

```yaml
- name: Moat Check
  run: |
    pip install moat
    moat check
```

## 与 AI 工具集成

### Claude Code

`moat adapter claude` 自动更新 `CLAUDE.md`，写入铁律。之后 Claude Code 改代码前/后自动跑 `moat check`。

### Cursor

`moat adapter all` 创建 `.cursor/rules.mdc`，Cursor 在改代码时自动遵守。

### Pre-commit

`moat adapter precommit` 安装 git pre-commit hook，每次 `git commit` 前自动检查。

## 常见问题

### Q: 报错了怎么办？

A: `moat check` 报错说明系统有地方坏了。修到通过为止，不要跳过。

### Q: 什么情况下需要更新基线？

A: 如果你**有意地**增加了文件、减少了文件、重构了模块——这些是允许的改动。改完后：

```bash
moat baseline save
```

### Q: 需要服务器运行吗？

A: L1 API 检查需要服务器运行。其他检查不需要。也可以只用 `moat check` 做静态检查。

## 项目结构

```
moat/
├── moat/
│   ├── cli.py              # CLI 入口
│   ├── runner.py           # 检查运行器
│   ├── monitor.py          # 实时监控
│   ├── baseline.py         # 基线管理
│   ├── discovery.py        # 项目自动发现
│   ├── contract.py         # CONTRACT 生成
│   ├── checks/             # 四层检查实现
│   │   ├── l1_import.py    # L1: import 链
│   │   ├── l1_api.py       # L1: API 端点
│   │   ├── l1_modules.py   # L1: 核心模块
│   │   ├── l1_files.py     # L1: 文件完整性
│   │   ├── l1_subsystems.py # L1: 子系统
│   │   ├── l1_behavior.py  # L1: 行为验证
│   │   ├── l2_schema.py    # L2: 结构检查
│   │   ├── l3_correlation.py # L3: 关联检查
│   │   └── l4_baseline.py  # L4: 基线对比
│   ├── dashboard/
│   │   ├── server.py       # FastAPI Web 看板
│   │   └── static/         # 前端文件
│   └── adapters/
│       └── __init__.py     # AI 适配器
├── pyproject.toml           # 构建配置
├── README.md
└── LICENSE
```