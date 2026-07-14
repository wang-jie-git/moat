# Security Policy 🛡️

> **版本**: 1.1.x · **更新**: 2026-07-14

---

## Security Manifesto: Your Code, Your Domain

Moat 是 **Local-First** 安全工具。我们坚持三条不可谈判的原则：

### Zero-Telemetry

Moat **不会主动上传**任何代码快照、配置文件或 API 密钥到远端服务器。所有检查在本地完成，代码绝不离开你的机器。

- ✅ 所有 `moat check` / `moat accept` 操作完全离线
- ✅ 基线数据、记忆索引全部存储在你的 `.moat/` 目录中
- ✅ 不存在"静默旁路通道"——每一行代码读取都能审计

### Transparent Audit

Moat 的每一次文件读取都在你的本地审计之下。

- ✅ `moat check --leak` 可检测是否有外部 AI 工具在扫描你的项目
- ✅ 所有 Operator 的执行日志在终端实时输出
- ✅ Evidence Chain 可追溯每个违规的 "Reason → File → Line"

### Self-Sovereignty

你的架构规则、基线数据、Truth Document 全在你的控制下。

- ✅ `architect.yml` 自定义规则，不依赖任何第三方服务器
- ✅ `.moat/baseline.json` 版本化存储，团队成员共享
- ✅ 无远程配置拉取，无云端依赖

---

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.1.x   | ✅ Active support  |
| 1.0.x   | ⚠️  Patch only     |

## 🔒 代码泄露检测

Moat 提供 `moat check --leak` 命令，主动检测项目中是否存在代码泄露风险：

| 检测项 | 描述 | 严重级别 |
|--------|------|----------|
| AI 工具痕迹 | `.grok/`、`.claude/`、`.codex/` 等配置是否被项目引用 | CRITICAL |
| 敏感文件暴露 | `.env`、`credentials.json` 是否未被 `.gitignore` 排除 | CRITICAL |
| 符号链接泄露 | symlink 是否指向项目外敏感目录（`.ssh/`、`.aws/`） | WARNING |
| 硬编码路径 | 代码中是否写死了 `~/` 或 `/home/` 敏感路径 | WARNING |
| Git 覆盖检查 | `.gitignore` 是否遗漏了敏感目录或文件 | WARNING |

## Reporting a Vulnerability

如果你发现 Moat 存在安全问题，请通过以下方式报告：

### Private Report (推荐)

发送邮件到: **opensource@one-pi.com**

或在 GitHub 创建 [Security Advisory](https://github.com/wang-jie-git/moat/security/advisories)

### 响应时间

- 24 小时内确认收到报告
- 7 天内提供修复时间表
- 修复后发布安全公告

## Security Best Practices

### 使用 Moat

- ✅ 定期更新到最新版本 (`pip install --upgrade moat-ai`)
- ✅ 在 CI/CD 中集成 Moat 检查 (`moat check --leak` + `moat accept --diff`)
- ✅ 定期运行泄露检测 (`moat check --leak`)
- ✅ 基线数据应纳入版本控制 (`.moat/baseline.json`)
- ⚠️ 不要将敏感信息写入基线文件

### 贡献代码

- ✅ 所有用户输入都应进行验证
- ✅ 避免硬编码凭证
- ✅ 遵循最小权限原则
- ✅ 更新 SECURITY.md (如果影响安全性)

## Known Issues

目前无已知安全问题。

## Past Security Issues

无历史安全问题。