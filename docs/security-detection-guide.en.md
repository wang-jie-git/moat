# Moat Security Detection Guide

> **Version**: v1.1.10 · Last Updated: 2026-07-14

---

## Table of Contents

1. [What Moat Can Do](#1-what-moat-can-do)
2. [What Moat Cannot Do (Important)](#2-what-moat-cannot-do-important)
3. [Detection Capabilities Overview](#3-detection-capabilities-overview)
4. [Real-World Case: Local Machine Scan](#4-real-world-case-local-machine-scan)
5. [How to Read Results](#5-how-to-read-results)
6. [What to Do After Detection](#6-what-to-do-after-detection)
7. [FAQ](#7-faq)

---

## 1. What Moat Can Do

Moat is a **local static detection tool** that discovers security risks in AI development environments. It solves three core problems:

### 🔍 Code Leak Detection (`moat check --leak`)

Scans the project directory for:

| Detection Item | Severity | Description |
|---------------|----------|-------------|
| AI tool traces | 🟡 WARNING | `.grok/`, `.claude/`, `.codex/` configs referenced by the project |
| Sensitive file exposure | 🔴 CRITICAL | `.env`, `credentials.json` not in `.gitignore` |
| Symlink leaks | 🟡 WARNING | symlinks pointing outside the project (`.ssh/`, `.aws/`) |
| Hardcoded paths | 🟢 INFO | `~/` or `/home/` sensitive paths in code |

### 👁️ AI Tool System Audit (`moat check --scan-ai`)

Scans system-level AI tool config directories:

| Detection Item | Severity | Description |
|---------------|----------|-------------|
| Telemetry data accumulation | 🟡 WARNING | Claude Code / Codex / Grok telemetry log sizes |
| Session history exposure | 🟢 INFO | Chat history files containing sensitive info |
| Sensitive command authorization | 🟡 WARNING | Authorized `sshpass`, `scp`, `tar+curl` commands |
| Config directory exposure | 🟢 INFO | AI tool config dirs readable by other processes |

### 🔐 Permission Audit (`moat audit --permissions`)

Audits AI tool (Claude Code) authorized commands:

| Detection Item | Severity | Description |
|---------------|----------|-------------|
| Plaintext passwords | 🔴 CRITICAL | Passwords in command args (e.g., `sshpass -p 'xxx'`) |
| High-risk idle permissions | 🟡 HIGH | Never-used dangerous commands (`scp`, `tar czf`) |
| Permission usage rate | 🟢 INFO | Percentage of actually used authorized commands |
| Slimming recommendations | 📋 Suggestion | Redundant permissions to remove |

---

## 2. What Moat Cannot Do (Important)

> **Moat is a detection tool, not a real-time interceptor.**

| Capability | Moat | Description |
|------------|------|-------------|
| Static config scanning | ✅ | Scan filesystem, discover known risks |
| Real-time command interception | ❌ | Does not monitor shell commands |
| Process monitoring | ❌ | Does not monitor what AI tools are doing |
| Network traffic interception | ❌ | Does not block curl, scp, etc. |
| Auto-fix | ❌ | Does not auto-modify configs, only gives suggestions |
| File integrity monitoring | ❌ | Does not watch file changes |

**Why no interception?**

Real-time interception requires:
- OS-level hooks (zsh/bash preexec)
- Background daemon
- Process tree monitoring
- False positive handling

This is essentially an **EDR (Endpoint Detection & Response) product**, which is a completely different category from Moat's "lightweight CLI static analysis tool" positioning. Moat's value is in **discovering problems in seconds**, then letting you decide how to handle them.

---

## 3. Detection Capabilities Overview

### 3.1 Quick Start

```bash
# Detect project code leaks
moat check --leak

# Detect AI tool system configs
moat check --scan-ai

# Audit AI tool permissions
moat audit --permissions
```

### 3.2 Reading Results

Moat uses a unified color/symbol severity system:

```
🟢 [INFO]     Informational — no action needed
🟡 [WARNING]  Warning — review and fix recommended
🔴 [CRITICAL] Critical — fix immediately
```

Each result includes three elements:

```
🟡 [WARNING] Problem description
  📍 File path/location         ← Location
  💡 Fix suggestion             ← Action guide
```

### 3.3 Complete Example

```bash
$ moat check --leak

🔒 Scanning for code leak risks...
   🔍 Scanning for leaks...
   🔴 [CRITICAL] Sensitive file exposure: .env
     📍 .env
     💡 Add .env to .gitignore. Use .env.example as a template.
   🟡 [WARNING] AI tool traces found: .grok (Grok CLI session dir)
     📍 /project/.grok/
     💡 Check if .grok introduces sensitive configs.
   🟡 [WARNING] Symlink pointing outside project: secret.key → ~/.ssh/id_rsa
     📍 secret.key
     💡 Use relative paths or copy the file into the project.

✅ Scan complete
```

---

## 4. Real-World Case: Local Machine Scan

The following data comes from a real scan on macOS 15.7.7.

### 4.1 AI Tool System Audit

```bash
$ moat check --scan-ai

🕵️ AI tool system config security audit...
   📋 Scanning ~/.claude/ ~/.grok/ ~/.codex/ ...

   🟡 [WARNING] Claude Code telemetry data: 24 files, 302.3 KB
     📍 /Users/xxx/.claude/telemetry
     💡 Check telemetry directory contents.

   ℹ️ [INFO] Claude Code session history: 421.9 KB
     📍 /Users/xxx/.claude/history.jsonl
     💡 Session logs contain all chat history.

   🟡 [WARNING] Claude Code has 19 sensitive commands authorized
     📍 /Users/xxx/.claude/settings.local.json
     💡 Check for sensitive commands (sshpass, scp, tar czf).

   🟡 [WARNING] Codex CLI config: 1.35 GB data
     📍 /Users/xxx/.codex/
     💡 Codex CLI caches large amounts of data.

🛡️ Summary:
Found 2 WARNING risks, review recommended
```

### 4.2 Permission Audit

```bash
$ moat audit --permissions

🔍 AI tool permission audit...
   📋 Analyzing 156 authorized commands...

   🔴 [CRITICAL] 4 plaintext passwords in command args
     ⚠️  Bash(sshpass -p 'xxx' ssh ...)
     ⚠️  Bash(sshpass *)
     💡 Remove sshpass, switch to SSH key auth

   🟡 [HIGH] 4 high-risk commands never used
     ⚠️  scp: remote file transfer — 7 days unused
     ⚠️  tar czf: packaging — 7 days unused
     💡 Remove unused commands to reduce attack surface

   🟢 [INFO] 59 safe commands actively used
     ✅ git, npm, pip, python, node, curl, gh, docker ...

   📊 Idle rate: 62% (96 unused permissions)
   💡 Recommended: remove 4 plaintext passwords, remove 4 unused commands

✅ Audit complete, 8 risks found
```

### 4.3 Key Findings

| Finding | Severity | Impact |
|---------|----------|--------|
| 1.35 GB Codex cache | 🟡 High | Contains code snapshots, API response cache |
| 302 KB telemetry data | 🟡 Medium | Claude Code usage records |
| 421 KB session history | 🟢 Low | Contains conversations, may include sensitive info |
| 19 sensitive commands authorized | 🟡 High | sshpass plaintext passwords directly exploitable |
| 62% permission idle rate | 🟡 Medium | Unnecessarily expanded attack surface |

---

## 5. How to Read Results

### 5.1 Severity Decision Tree

```
Found 🔴 CRITICAL?
  ├─ Yes → Fix immediately, don't continue development
  │
  └─ No → Found 🟡 WARNING?
             ├─ Yes → Log to security checklist, fix this week
             │
             └─ No → Found 🟢 INFO?
                        ├─ Yes → Acknowledge, no urgent action
                        └─ No → Secure, continue working
```

### 5.2 Typical Attack Chain

Moat-detected risks can form a **data exfiltration pipeline**:

```
sshpass -p 'xxx'   →     tar czf     →     curl/scp
   Login remote         Package code        Upload to remote
```

If all three authorizations exist simultaneously, an AI Agent could:
1. Login to a remote server
2. Package the current project code
3. Upload to an external server

Moat detects this risk combination, marks each link, and recommends removing unnecessary authorizations.

---

## 6. What to Do After Detection

### 6.1 Sensitive File Exposure

```bash
# 1. Add sensitive files to .gitignore
echo ".env" >> .gitignore
echo "credentials.json" >> .gitignore

# 2. Create template file
cp .env .env.example
# Edit .env.example to remove real values, keep keys

# 3. Re-scan to confirm
moat check --leak
```

### 6.2 AI Tool Telemetry Data

```bash
# View telemetry contents
ls -la ~/.claude/telemetry/
cat ~/.claude/telemetry/latest.json | head -50

# Disable telemetry (if not needed)
# Edit ~/.claude/settings.json
# Set "telemetry_enabled": false

# Clean old data
rm -rf ~/.claude/telemetry/old/*
```

### 6.3 Plaintext Password → SSH Key

```bash
# 1. Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -C "your-email@example.com"

# 2. Copy to remote server
ssh-copy-id user@server

# 3. Configure SSH config
echo "Host myserver
    HostName server.example.com
    User user
    IdentityFile ~/.ssh/id_ed25519" >> ~/.ssh/config

# 4. Test connection (no password)
ssh myserver

# 5. Remove sshpass from Claude Code authorization
# Edit ~/.claude/settings.local.json, remove sshpass entries
```

### 6.4 Permission Slimming

```bash
# 1. View recommended permissions to remove
moat audit --permissions

# 2. Edit Claude Code config
vi ~/.claude/settings.local.json

# 3. Remove entries (example):
# "Bash(sshpass -p '*' ssh ...)" — switched to SSH key
# "Bash(scp *)"                  — never used
# "Bash(tar czf *)"              — never used

# 4. Re-scan to confirm
moat audit --permissions
```

---

## 7. FAQ

### Q: Can Moat prevent AI tools from stealing data?

**No.** Moat is a **detection tool**, not an **interception tool**. It finds security risks in AI tool configurations but cannot stop ongoing data exfiltration. Real-time interception requires EDR-level system integration, which is outside Moat's scope.

### Q: How often should I run detection?

Recommended frequency:
- `moat check --leak`: **Every development session start**
- `moat check --scan-ai`: **Weekly**
- `moat audit --permissions`: **After each AI tool install/update**

### Q: What is "telemetry data" in the results?

AI tools (Claude Code, Codex) record usage data including command history, conversations, and code snippets. This data is stored locally by default but can be read and exploited by AI Agents.

### Q: Why does Codex CLI have 1.35 GB of data?

Codex CLI caches large amounts of codebase indices, API responses, and session data. While stored locally, this accumulation may contain sensitive information. Regular cleanup is recommended.

### Q: Can I use Moat in CI/CD?

Yes. Moat is a pure CLI tool, works in CI/CD pipelines:
```bash
moat check --leak --fail-on-score 60
moat audit --permissions --fail-on-score 60
```

### Q: Does Moat upload my code?

**No.** All checks run locally, no data is sent to external servers. This is Moat's "Zero-Telemetry" commitment.

---

## Appendix: Quick Reference Card

```bash
# Detect code leaks
moat check --leak

# Detect AI tool configs
moat check --scan-ai

# Audit AI tool permissions
moat audit --permissions

# Gate mode (for CI/CD)
moat check --leak --fail-on-score 60
moat audit --permissions --fail-on-score 60

# Generate report
moat report --format pdf -o security-report.pdf
moat report --format md -o security-report.md
```

---

> **Moat's value isn't "interception", it's "discovery".**
> In an era where AI Agents have broad permissions, knowing "what's wrong" matters more than "can we block it".
> Because only when you know the problem, can you decide what to do about it.
