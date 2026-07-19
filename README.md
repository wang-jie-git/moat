# Moat — AI Moat: The Brake for AI Engineering 🛡️

> **Version**: v1.2.1 · **PyPI**: `pip install moat-ai` · **GitHub**: [wang-jie-git/moat](https://github.com/wang-jie-git/moat)
>
> [![PyPI version](https://img.shields.io/pypi/v/moat-ai.svg?style=flat-square&color=brightgreen)](https://pypi.org/project/moat-ai/)
> [![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg?style=flat-square)](LICENSE)
> [![Python](https://img.shields.io/badge/python-3.10+-blue.svg?style=flat-square)](pyproject.toml)
> [![Tests](https://img.shields.io/badge/tests-1020%20passed-brightgreen?style=flat-square)](tests/)
> [![CI](https://github.com/wang-jie-git/moat/actions/workflows/ci.yml/badge.svg)](https://github.com/wang-jie-git/moat/actions/workflows/ci.yml)

**🌐 [中文版本 🇨🇳](README.zh.md)**

> **"The Chief Architect for the AI Era"** — Not a linter, not a SAST tool. It's the collision avoidance system for your codebase.

AI writes code fast. AI breaks things fast too. Moat runs before and after every code change, telling you in seconds whether your system is still intact.

**v1.2.0 New: moat-memory** — Moat learns from every check failure and fix. The more you use it, the smarter it gets. No external services, no API calls. Zero dependencies.

---

## 🛡️ Security Manifesto: Your Code, Your Domain

In the wake of the **July 2026 Grok CLI incident** (auto-packaging codebases + reading `~/.claude/` API keys across directories), Moat upholds the **Local-First** principle — no compromise on security.

| Commitment | Description |
|------------|-------------|
| **Zero-Telemetry** | Moat never uploads code snapshots, configs, or API keys. All checks run locally. |
| **Transparent Audit** | Every file read is under your local audit. No silent side channels. |
| **Self-Sovereignty** | Your architecture rules, baselines, and memory indices stay under your control. |

### 📺 Demos

<p align="center">
  <img src="docs/demo-bug-intercept-compact.svg" alt="Moat: Bug Interception + AI Audit" width="700">
  <br>
  <em>Bug Interception → AI Tool Config Audit → Three Lines of Defense</em>
</p>

<p align="center">
  <img src="docs/demo-leak-detection.svg" alt="Moat: Leak Detection" width="700">
  <br>
  <em>Symlink leaks, sensitive file exposure, AI tool trace detection</em>
</p>

<p align="center">
  <img src="docs/demo-scan-ai.svg" alt="Moat: AI Tool System Audit" width="700">
  <br>
  <em>Scan Claude Code / Codex / Grok configs for sensitive info leaks</em>
</p>

### 🚨 Leak Detection

**`moat check --leak`** — Detect AI tool cross-directory reads and sensitive file exposure:

```bash
moat check --leak
```

Scans for:
- **AI tool traces**: `.grok/`, `.claude/`, `.codex/` configs referenced by the project
- **Sensitive file exposure**: `.env`, `credentials.json` not excluded by `.gitignore`
- **Symlink leaks**: Symlinks pointing outside the project (`.ssh/`, `.aws/`)
- **Hardcoded paths**: `~/` or `/home/` sensitive paths in code

```
🔒 Scanning for code leak risks...
   🔍 Scanning for leaks...
   🔴 [CRITICAL] AI tool traces found: .grok (Grok CLI session dir)
     📍 /project/.grok/
     💡 Check if .grok introduces sensitive configs. Remove from project if not needed.
   🟡 [WARNING] Symlink pointing outside project: secret.key → ~/.ssh/id_rsa
     📍 secret.key
     💡 Use relative paths or copy the file into the project.

✅ No code leak risks detected
```

### 👁️ AI Tool System Audit

**`moat check --scan-ai`** — Scan local AI tool configurations for security risks:

```bash
moat check --scan-ai
```

Detects:
- **Claude Code / Codex / Grok** config directories
- **Telemetry data** accumulation
- **Authorized sensitive commands** (sshpass, scp, tar+curl combinations)
- **Session history** containing sensitive conversation data

```
🕵️ AI tool system config security audit...
   📋 Found Claude Code config: /Users/mac/.claude
   🟡 [WARNING] Claude Code telemetry data: 24 files, 302.3 KB
     📍 /Users/mac/.claude/telemetry
   ℹ️ [INFO] Claude Code session history: 421.9 KB
     📍 /Users/mac/.claude/history.jsonl
   🟡 [WARNING] Claude Code has 19 sensitive commands authorized
     📍 /Users/mac/.claude/settings.local.json
```

### 🔐 Permission Audit

**`moat audit --permissions`** — Audit AI tool permissions and get a "slimming" recommendation:

```bash
moat audit --permissions
```

```
🔍 AI Tool Permission Audit...
   📋 Analyzing 156 authorized commands...
   🔴 [CRITICAL] 4 plaintext passwords found in command args
   🟡 [HIGH] 4 high-risk commands never used
   🟢 [INFO] 59 safe commands actively used
   📊 Idle rate: 62% (96 unused permissions)
   💡 Recommended: remove 4 plaintext passwords, remove 4 unused commands
```

---

## 🧠 moat-memory — Self-Learning Memory (v1.2.0)

Moat remembers every check failure and every fix. The more you use it, the smarter it gets.

```
check fails  → auto-record lesson in .moat/memory.db   ✅
fix passes   → auto-extract template from git diff     ✅
AI reads     → moat memory --ai outputs all memories   ✅
```

### Memory Types

| Type | Description | Auto-generated |
|------|-------------|:--------------:|
| **Redlines** | Architecture rules & coding boundaries | ✅ `moat init` presets 5 defaults |
| **Lessons** | Check failure records | ✅ On every `moat check` failure |
| **Templates** | Experience patterns from git diffs | ✅ On successful `moat check` if last commit is a fix |
| **Skills** | AI tool instructions | ✅ `moat adapter install` |

### CLI Commands

```bash
# Overview
moat memory                    # Memory stats (default)
moat memory --ai               # AI-readable format (all memories)

# Redlines (architecture rules)
moat redline list              # List all redlines
moat redline add "禁止跨层调用" --description "routes/ 不应直接调用 db/" --severity critical
moat redline remove <id>

# Templates (experience patterns)
moat template list             # List all templates
moat template extract          # Extract from latest git commit (keyword)
moat template extract --llm    # Extract with LLM semantic analysis (optional)

# Adapters (AI tool integration)
moat adapter claude            # Inject memory reading instructions into CLAUDE.md
```

### AI Tool Integration

After `moat adapter install`, AI tools automatically read moat-memory before modifying code:

- **Claude Code**: `.claude/skills/moat/SKILL.md` loaded at startup
- **Codex CLI**: `.codex/skills/moat/SKILL.md` loaded at startup
- **OpenCode**: `.opencode/skills/moat/SKILL.md` loaded at startup

### Zero External Dependencies

All memory is stored in `.moat/memory.db` (SQLite, WAL mode). No external services, no API calls, no data leaves your machine.

---

## ⚔️ Moat vs Traditional Tools

> Moat is not a linter replacement. It's a new category: **AI Engineering OS**
> Linters check syntax, SAST scans vulnerabilities, Moat governs architecture.

| Dimension | 🛡️ Moat | 🔧 Traditional Linter | 📊 SonarQube |
|-----------|----------|----------------------|--------------|
| **Core Positioning** | AI Engineering OS | Code style check | Code quality platform |
| **Architecture Governance** | ✅ 8-step acceptance loop | ❌ Syntax/style only | ⚠️ Code smells only |
| **Layer Enforcement** | ✅ Built-in 5 layers + custom | ❌ | ❌ |
| **Incremental Audit** | ✅ `--diff` 2s results | ⚠️ File-level only | ❌ Full scan |
| **Gate Mode** | ✅ `--fail-on-score` | ⚠️ Partial | ✅ |
| **Evidence Chain** | ✅ Reason → File → Line | ❌ Line only | ✅ |
| **Security Injection** | ✅ Zero false positives | ❌ High noise | ✅ |
| **AI Context Integration** | ✅ MCP / Claude Code Hook | ❌ | ❌ |
| **Performance** | **< 0.2s/run** | Medium | Slow (full scan) |
| **Test Coverage** | **99.8%+** (1020 tests) | ❌ | ❌ |
| **Configuration** | Zero config | Requires config | Requires config |

---

## ✨ Three Key Differentiators

### 🔍 Diff-Aware Audit (Incremental Acceptance)

Full scan of 4160 files? Too slow. **`moat accept --diff`** scans only the 5 files you changed, completing architecture-level audit in 2 seconds.

```bash
# Incremental acceptance after changing a few files
moat accept --diff --fail-on-score 60

# Full acceptance
moat accept --output ACCEPTANCE_REPORT.md
```

### 🧱 Layer-Enforcer

Built-in standard MVC/DDD layer rules, auto-detects cross-layer violations like `routes/` directly calling `db/`.

```bash
# Default 5-layer rule: routes → services → db / models / utils
moat accept --diff
```

Customize any layer rules via `architect.yml`.

### 📋 Evidence-Based

All blocks come with a complete evidence chain, not black-box errors:

```
❌ LAYER_VIOLATION: routes/ should not directly import db/
  → Reason: Layer violation (routes → services → db)
  → File: app/routes/user.py:15
  → Detail: Direct import db.session
```

---

## 🚀 Quick Start

```bash
# Install
pip install moat-ai

# Zero-config init
moat init

# Basic checks
moat check --quick        # Second-level check
moat check --full         # Full check (includes architecture audit)
moat check --leak         # 🔒 Leak detection (2s)
moat check --scan-ai      # 👁️ AI tool config audit

# Architecture acceptance (v1.1.4+)
moat accept               # 8-step architecture acceptance
moat accept --diff        # Incremental acceptance (2s)
moat accept --output report.md  # Generate report

# Gate mode
moat accept --diff --fail-on-score 60  # Block if score < 60

# Permission audit (v1.1.9+)
moat audit --permissions  # 🔐 AI tool permission audit + slimming

# CI/CD integration
moat ci                   # Auto-generate GitHub Actions workflow
moat notify --webhook <url>  # Send results to Slack/Feishu/Discord
```

---

## 📍 Installation

Moat is a standard Python package, runs on your local machine. Code never leaves your machine.

```bash
pip install moat-ai       # Project venv or global install
```

### Integration with Claude/Cursor

**Method 1: Direct CLI (Recommended)**

Claude executes Moat commands directly in the terminal, just like a human developer:

```bash
moat check --full              # Full check
moat accept                    # Architecture acceptance
moat gatekeeper check --file app.py  # Single file check
```

**Method 2: Sidecar Daemon**

```bash
moat sidecar start             # Start daemon
curl http://localhost:7777/api/health  # REST API
```

**Method 3: Static Rule Injection**

```bash
moat adapter claude            # Generate CLAUDE.md
moat adapter all               # Generate rules for all AI tools
```

---

## 📋 Full Command Reference

```bash
# Core checks
moat check [--quick|--full|--diff]  # 4 check modes
moat check --leak                   # 🔒 Leak detection
moat check --scan-ai                # 👁️ AI tool config audit
moat init                           # Zero-config init
moat watch                          # Real-time log monitoring
moat report [--format pdf|md|json]  # Generate report (PDF supported)
moat baseline [save|show|diff]      # Baseline management

# Architecture acceptance (v1.1.4+)
moat accept                         # 8-step architecture acceptance
moat accept --diff                  # Incremental acceptance
moat accept --output report.md      # Generate report
moat accept --fail-on-score 60      # Gate mode

# Permission audit (v1.1.9+)
moat audit --permissions            # 🔐 Permission audit + slimming

# CI/CD integration (v1.1.6+)
moat ci                             # ⚡ Generate GitHub Actions / GitLab CI
moat notify --webhook <url>         # 🔔 Send results to Slack / Feishu / Discord

# Optimization checks
moat check --quick --optimize       # Quick + optimization rules
moat check --full --optimize        # Full + optimization rules

# Evolution metrics
moat evolution report               # View evolution report
moat evolution adjust               # Auto-adjust configuration

# Sidecar daemon
moat sidecar start                  # Start daemon
moat sidecar status                 # View status
moat sidecar stop                   # Stop daemon

# AI adapters
moat adapter claude                 # Install Claude Code adapter
moat adapter all                    # Install all AI tool adapters
moat adapter precommit              # Install pre-commit hook

# moat-memory (v1.2.0+)
moat memory                         # 📊 Memory stats
moat memory --ai                    # 🤖 AI-readable format (all memories)
moat redline list                   # 📏 List redlines
moat template extract               # 📋 Extract template from git commit
moat template extract --llm         # 🤖 Extract with LLM semantic analysis
```

---

## 📚 Documentation

- [Quick Start](docs/QuickStart.md) — Get started in 5 minutes
- [Security Detection Guide](docs/security-detection-guide.en.md) — 🛡️ AI tool security audit
- [FAQ](docs/FAQ.md) — Frequently Asked Questions
- [Project Map](docs/ProjectMap.md) — Feature overview
- [CHANGELOG](CHANGELOG.md) — Version history
- [ROADMAP](ROADMAP.md) — Future roadmap
- [Contributing](CONTRIBUTING.md) — How to contribute

---

## 🔑 Core Philosophy

> **AI lies, cuts corners, and hallucinates.**
> 
> **Moat's real value: it's the brake for AI.**
>
> No matter how AI evolves, physics doesn't change — high speed needs brakes, complex systems need checkpoints, continuous output needs validation pauses.

**Why this positioning matters**:
- ❌ **Toy vs. Tool**: If defined as "AI Engineering OS", it's a toy. If defined as "the brake", it's a tool.
- ❌ **AI will get stronger, not more honest**: Future AI will be more capable, but still have "lazy tendencies" and "memory blind spots".
- ✅ **The eternal value of a "brake"**: High-speed motion needs brakes. Complex systems need checkpoints.

**You own the code, you own the guard.**

---

## 🏷️ Tags

`ai-agent` `architecture-guard` `security-tool` `code-review` `static-analysis`
`python` `gatekeeper` `devtools` `lint` `architecture` `mcp`

---

## License

Apache 2.0
