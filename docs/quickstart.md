---
title: Quick Start
---

# Quick Start

## Install

```bash
pip install moat-ai
```

Or with all features (dashboard, sidecar, VS Code):

```bash
pip install "moat-ai[all]"
```

## Run your first check

```bash
cd your-project
moat check
```

12 seconds later you'll see:

```
✅ MOAT 全部通过，系统健康。
⚡ Powered by One — https://one.cloudkey.top
```

## What just happened?

Moat ran all 4 defense layers:

| Layer | What it checks |
|-------|---------------|
| **L0 Syntax** | No syntax errors |
| **L1 Survival** | Imports work, APIs respond, files exist |
| **L2 Structure** | API contracts match, code entropy |
| **L3 Correlation** | Changed A didn't break B |
| **L4 Baseline** | Code volume didn't regress |
| **Gatekeeper** | SQL injection, secrets, auth, deps |

## Init a project

```bash
moat init
```

Auto-detects project structure, saves baseline, generates AI adapter rules.

## Pre-commit hook

```bash
moat adapter precommit
```

Installs a pre-commit hook that runs `moat check` before every commit.
