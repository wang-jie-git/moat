# Moat 安全检测指南

> **版本**: v1.1.10 · 最后更新: 2026-07-14

---

## 目录

1. [Moat 能做什么](#1-moat-能做什么)
2. [Moat 不能做什么（重要）](#2-moat-不能做什么重要)
3. [检测能力一览](#3-检测能力一览)
4. [真实案例：本机检测报告](#4-真实案例本机检测报告)
5. [如何解读检测结果](#5-如何解读检测结果)
6. [检测到问题后怎么办](#6-检测到问题后怎么办)
7. [常见问题](#7-常见问题)

---

## 1. Moat 能做什么

Moat 是一个**本地静态检测工具**，用于发现 AI 开发环境中的安全风险。它解决的三个核心问题是：

### 🔍 代码泄露风险检测 (`moat check --leak`)

扫描项目目录，检测是否存在以下风险：

| 检测项 | 风险等级 | 说明 |
|--------|---------|------|
| AI 工具痕迹 | 🟡 WARNING | `.grok/`、`.claude/`、`.codex/` 等配置目录被项目引用 |
| 敏感文件暴露 | 🔴 CRITICAL | `.env`、`credentials.json` 等未加入 `.gitignore` |
| 符号链接泄露 | 🟡 WARNING | symlink 指向项目外敏感目录（`.ssh/`、`.aws/`） |
| 硬编码路径 | 🟢 INFO | 代码中写死了 `~/` 或 `/home/` 敏感路径 |

### 👁️ AI 工具系统审计 (`moat check --scan-ai`)

扫描系统级 AI 工具配置目录，发现以下风险：

| 检测项 | 风险等级 | 说明 |
|--------|---------|------|
| 遥测数据累积 | 🟡 WARNING | Claude Code / Codex / Grok 遥测日志大小 |
| 会话历史泄露 | 🟢 INFO | 对话历史文件包含敏感信息 |
| 敏感命令授权 | 🟡 WARNING | 已授权的 `sshpass`、`scp`、`tar+curl` 等命令 |
| 配置目录暴露 | 🟢 INFO | AI 工具配置目录是否被其他进程可读 |

### 🔐 权限审计 (`moat audit --permissions`)

审计 AI 工具（Claude Code）的已授权命令：

| 检测项 | 风险等级 | 说明 |
|--------|---------|------|
| 明文密码 | 🔴 CRITICAL | 命令参数中包含明文密码（如 `sshpass -p 'xxx'`） |
| 高危闲置权限 | 🟡 HIGH | 从未使用的高危命令（如 `scp`、`tar czf`） |
| 权限使用率 | 🟢 INFO | 已授权命令中实际使用的比例 |
| 瘦身建议 | 📋 建议 | 建议移除的冗余权限列表 |

---

## 2. Moat 不能做什么（重要）

> **Moat 是检测工具，不是实时拦截器。**

| 能力 | Moat | 说明 |
|------|------|------|
| 静态扫描配置 | ✅ | 扫描文件系统，发现已知风险 |
| 实时命令拦截 | ❌ | 不监听 shell 命令，不拦截正在执行的命令 |
| 进程监控 | ❌ | 不监控 AI 工具正在做什么 |
| 网络流量拦截 | ❌ | 不拦截 curl、scp 等网络请求 |
| 自动修复 | ❌ | 不自动修改配置，只给建议 |
| 文件完整性监控 | ❌ | 不监控文件变化 |

**为什么不做拦截？**

实时拦截需要：
- 操作系统级 hook（zsh/bash preexec）
- 常驻后台 daemon
- 进程树监控
- 误报处理机制

这本质上是一个 **EDR（端点检测与响应）产品**，与 Moat 的"轻量级 CLI 静态分析工具"定位完全不同。Moat 的价值在于**几秒内发现问题**，然后由你决定怎么处理。

---

## 3. 检测能力一览

### 3.1 快速入门

```bash
# 检测项目代码泄露风险
moat check --leak

# 检测 AI 工具系统配置
moat check --scan-ai

# 审计 AI 工具权限
moat audit --permissions
```

### 3.2 检测结果解读

Moat 的检测结果使用统一的颜色/符号分级：

```
🟢 [INFO]     信息提示 — 无需处理，仅供参考
🟡 [WARNING]  警告 — 建议审查和修复
🔴 [CRITICAL] 严重 — 必须立即修复
```

每条检测结果都包含三个要素：

```
🟡 [WARNING] 问题描述
  📍 文件路径/位置         ← 定位
  💡 修复建议              ← 行动指南
```

### 3.3 完整检测示例

```bash
$ moat check --leak

🔒 代码泄露风险检测...
   🔍 扫描泄露风险...
   🔴 [CRITICAL] 发现敏感文件暴露: .env
     📍 .env
     💡 将 .env 加入 .gitignore。使用 .env.example 作为模板提交。
   🟡 [WARNING] 发现 AI 工具痕迹: .grok (Grok CLI 会话目录)
     📍 /project/.grok/
     💡 检查 .grok 是否引入了敏感配置。如不需要，请从项目中移除。
   🟡 [WARNING] 符号链接指向项目外: secret.key → ~/.ssh/id_rsa
     📍 secret.key
     💡 使用相对路径或复制文件到项目内。

✅ 检测完成
```

---

## 4. 真实案例：本机检测报告

以下数据来自 macOS 15.7.7 的真实检测结果。

### 4.1 AI 工具系统审计

```bash
$ moat check --scan-ai

🕵️ AI 工具系统配置安全审计...
   📋 扫描 ~/.claude/ ~/.grok/ ~/.codex/ ...

   🟡 [WARNING] Claude Code 遥测数据: 24 个文件, 302.3 KB
     📍 /Users/xxx/.claude/telemetry
     💡 检查 telemetry 目录内容。如需关闭遥测，
         检查 settings.json 中的 telemetry_enabled 配置。

   ℹ️ [INFO] Claude Code 会话历史: 421.9 KB
     📍 /Users/xxx/.claude/history.jsonl
     💡 会话日志包含所有对话历史。如涉及敏感信息，
         建议定期清理。

   🟡 [WARNING] Claude Code 已授权 19 个敏感命令
     📍 /Users/xxx/.claude/settings.local.json
     💡 检查授权列表中的敏感命令（sshpass, scp,
         tar czf 等）。如需撤销，编辑
         settings.local.json 移除对应条目。

   🟡 [WARNING] 发现 Codex CLI 配置: 1.35 GB 数据
     📍 /Users/xxx/.codex/
     💡 Codex CLI 缓存了大量数据，建议检查
         .codex 目录内容并清理不需要的缓存。

🛡️ 总结:
发现 2 个 WARNING 风险，建议审查
```

### 4.2 权限审计

```bash
$ moat audit --permissions

🔍 AI 工具权限审计...
   📋 分析 156 个已授权命令...

   🔴 [CRITICAL] 4 个明文密码命令参数
     ⚠️  Bash(sshpass -p 'xxx' ssh ...)
     ⚠️  Bash(sshpass *)
     📍 /Users/xxx/.claude/settings.local.json
     💡 移除 sshpass 命令，改用 SSH 密钥认证

   🟡 [HIGH] 4 个高危命令从未使用
     ⚠️  scp: 远程文件传输 — 7 天无使用记录
     ⚠️  tar czf: 打包操作 — 7 天无使用记录
     📍 /Users/xxx/.claude/settings.local.json
     💡 建议移除未使用的命令，减少攻击面

   🟢 [INFO] 59 个安全命令正在使用
     ✅ git, npm, pip, python, node, curl, gh, docker ...

   📊 闲置率: 62% (96 个未使用的权限)
   💡 建议: 移除 4 个明文密码, 移除 4 个未使用命令

✅ 审计完成，共发现 8 个风险项
```

### 4.3 关键发现

| 发现 | 严重程度 | 实际影响 |
|------|---------|---------|
| 1.35 GB Codex 缓存 | 🟡 高 | 包含代码快照、API 响应缓存 |
| 302 KB 遥测数据 | 🟡 中 | Claude Code 使用情况记录 |
| 421 KB 会话历史 | 🟢 低 | 包含对话内容，可能含敏感信息 |
| 19 个敏感命令授权 | 🟡 高 | sshpass 明文密码可直接利用 |
| 62% 权限闲置率 | 🟡 中 | 攻击面不必要地扩大 |

---

## 5. 如何解读检测结果

### 5.1 风险等级决策树

```
发现 🔴 CRITICAL？
  ├─ 是 → 立即修复，不修复不继续开发
  │
  └─ 否 → 发现 🟡 WARNING？
             ├─ 是 → 记录到安全检查清单，本周内修复
             │
             └─ 否 → 发现 🟢 INFO？
                        ├─ 是 → 了解即可，无需立即处理
                        └─ 否 → 安全，继续工作
```

### 5.2 典型攻击路径

Moat 检测到的风险组合可以直接构成一条**数据窃取流水线**：

```
sshpass -p 'xxx'   →     tar czf     →     curl/scp
   登录远程服务器       打包代码库         上传到远程
```

如果这三个授权同时存在，AI Agent 可以在不被用户察觉的情况下：
1. 登录远程服务器
2. 打包当前项目代码
3. 上传到外部服务器

Moat 检测到这种风险组合后，会分别标记每个环节，并建议移除不必要的授权。

---

## 6. 检测到问题后怎么办

### 6.1 敏感文件暴露

```bash
# 1. 将敏感文件加入 .gitignore
echo ".env" >> .gitignore
echo "credentials.json" >> .gitignore

# 2. 创建模板文件
cp .env .env.example
# 编辑 .env.example 移除真实值，保留键名

# 3. 重新检测确认
moat check --leak
```

### 6.2 AI 工具遥测数据

```bash
# 查看遥测数据内容
ls -la ~/.claude/telemetry/
cat ~/.claude/telemetry/latest.json | head -50

# 关闭遥测（如果不需要）
# 编辑 ~/.claude/settings.json
# 设置 "telemetry_enabled": false

# 清理旧数据
rm -rf ~/.claude/telemetry/old/*
```

### 6.3 明文密码 → SSH 密钥

```bash
# 1. 生成 SSH 密钥（如果还没有）
ssh-keygen -t ed25519 -C "your-email@example.com"

# 2. 复制到远程服务器
ssh-copy-id user@server

# 3. 配置 SSH config
echo "Host myserver
    HostName server.example.com
    User user
    IdentityFile ~/.ssh/id_ed25519" >> ~/.ssh/config

# 4. 测试连接（无需密码）
ssh myserver

# 5. 从 Claude Code 授权中移除 sshpass
# 编辑 ~/.claude/settings.local.json，删除 sshpass 相关条目
```

### 6.4 权限瘦身

```bash
# 1. 查看建议移除的权限列表
moat audit --permissions

# 2. 编辑 Claude Code 配置文件
vi ~/.claude/settings.local.json

# 3. 移除以下条目（示例）：
# "Bash(sshpass -p '*' ssh ...)" — 已改用 SSH 密钥
# "Bash(scp *)"                  — 从未使用
# "Bash(tar czf *)"              — 从未使用

# 4. 重新检测确认
moat audit --permissions
```

---

## 7. 常见问题

### Q: Moat 能防止 AI 工具偷数据吗？

**不能。** Moat 是**检测工具**，不是**拦截工具**。它能发现 AI 工具配置中的安全风险，但不能阻止正在发生的窃取行为。实时拦截需要 EDR 级别的系统集成，不在 Moat 的定位范围内。

### Q: 我应该多久运行一次检测？

建议频率：
- `moat check --leak`：**每次开发会话开始时**
- `moat check --scan-ai`：**每周一次**
- `moat audit --permissions`：**每次安装/更新 AI 工具后**

### Q: 检测结果中提到"遥测数据"，这是什么？

AI 工具（如 Claude Code、Codex）会记录你的使用数据，包括命令执行历史、对话内容、代码片段等。这些数据默认存储在本地，但可能被 AI Agent 读取和利用。

### Q: 为什么 Codex CLI 有 1.35 GB 数据？

Codex CLI 缓存了大量的代码库索引、API 响应和会话数据。这些数据虽然存储在本地，但大量累积可能包含敏感信息，建议定期检查并清理不需要的缓存。

### Q: 我可以用 Moat 扫描 CI/CD 环境吗？

可以。Moat 是纯命令行工具，可以在 CI/CD 流水线中运行：
```bash
moat check --leak --fail-on-score 60
moat audit --permissions --fail-on-score 60
```

### Q: Moat 会上传我的代码吗？

**不会。** 所有检查在本地完成，不发送任何数据到外部服务器。这是 Moat 的"Zero-Telemetry"承诺。

---

## 附录：快速参考卡

```bash
# 检测代码泄露
moat check --leak

# 检测 AI 工具配置
moat check --scan-ai

# 审计 AI 工具权限
moat audit --permissions

# 门禁模式（CI/CD 中使用）
moat check --leak --fail-on-score 60
moat audit --permissions --fail-on-score 60

# 生成报告
moat report --format pdf -o security-report.pdf
moat report --format md -o security-report.md
```

---

> **Moat 的价值不在于"拦截"，而在于"发现"。**
> 在一个 AI Agent 普遍拥有高级权限的时代，知道"哪里有问题"比"能不能拦截"更重要。
> 因为只有知道了问题，你才能决定怎么处理。
