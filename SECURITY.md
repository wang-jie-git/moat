# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | ✅ Fully supported |

## Reporting a Vulnerability

如果你发现 Moat 存在安全问题,请通过以下方式报告:

### 私人报告 (推荐)

发送邮件到: **security@example.com** (需要设置实际邮箱)

或在 GitHub 创建 [Security Advisory](https://github.com/wang-jie-git/moat/security/advisories)

### 包含信息

请包含:
- 问题描述
- 复现步骤
- 预期行为 vs 实际行为
- 你的环境 (Python 版本,操作系统等)
- 如果可能,提供 PoC (概念验证)

### 响应时间

- 24-48 小时内确认收到报告
- 7 天内提供修复时间表
- 修复后发布安全公告

## Security Best Practices

### 使用 Moat 时

- ✅ 定期更新到最新版本
- ✅ 在 CI/CD 中集成 Moat 检查
- ✅ 不要在生产环境禁用 L0/L1 检查
- ⚠️ 基线数据应纳入版本控制 (`.moat/baseline.json`)
- ⚠️ 不要将敏感信息写入基线文件

### 贡献代码时

- ✅ 所有用户输入都应进行验证
- ✅ 避免硬编码凭证
- ✅ 遵循最小权限原则
- ✅ 更新 SECURITY.md (如果影响安全性)

## Known Issues

目前无已知安全问题。

## Past Security Issues

无历史安全问题。
