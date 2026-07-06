# Moat — AI Coding Guardrails

[中文](README.md) | English

Run once **before** code changes, run again **after** code changes. Both must pass before commit.

Prevent AI tools from "fixing one bug and introducing three more."

## Why

AI writes code fast. AI breaks systems fast.

The root cause of "fix one, break three": **The code modifier (human or AI) doesn't know all subsystems**.

Moat's four-layer defense runs before and after code changes, telling you in 12 seconds if the system is broken.

## Installation

```bash
# From PyPI (recommended)
pip install moat-ai

# With Web Dashboard
pip install "moat-ai[dashboard]"

# Directly from GitHub
pip install git+https://github.com/wang-jie-git/moat.git
```

## Usage

### 1. Initialize

```bash
cd your-project
moat init
```

Auto-detects project structure, saves baseline data, generates AI adapter rules.

### 2. Check Before/After Code Changes

```bash
moat check
```

Completes four-layer defense in 12 seconds:

| Layer | Purpose |
|-------|---------|
| **L0 Syntax** | All Python files pass syntax check |
| **L1 Survival** | Imports work, APIs return 200, core modules instantiate, critical files exist |
| **L2 Structure** | API JSON fields match contract (prevents frontend/backend breaks) |
| **L3 Correlation** | Modified A doesn't break B (prevents "fix one, break three") |
| **L4 Baseline** | File count doesn't decrease, code quality doesn't regress (prevents silent deletions) |

### 3. Live Monitoring

```bash
moat watch --log logs/backend.log
```

Real-time log error monitoring with color-coded severity levels.

### 4. Web Dashboard

```bash
moat dashboard
```

Open `http://localhost:9876` in your browser to view the error dashboard:

- Real-time error list (auto-refresh)
- Run/save baseline
- Project status overview

### 5. AI Adapters

```bash
# Install all AI tool adapters
moat adapter all

# Install Claude Code adapter only
moat adapter claude

# Install pre-commit hook only
moat adapter precommit
```

AI tools (Claude Code, Cursor, Codex, Copilot) automatically follow Moat's rules when modifying code.

### 6. Baseline Management

```bash
# Save current state as baseline
moat baseline save

# View baseline
moat baseline show

# Compare current vs baseline
moat baseline diff
```

## Complete Example

```bash
# Initialize
cd /path/to/project
moat init

# Check before code changes
moat check

# Make changes...
# Check after code changes
moat check

# Commit if passed
git add .
git commit -m "fix: ..."

# Monitor server logs in real-time
moat watch --log logs/backend.log
```

## CI Integration

Add to GitHub Actions:

```yaml
- name: Moat Check
  run: |
    pip install moat
    moat check
```

## AI Tool Integration

### Claude Code

`moat adapter claude` auto-updates `CLAUDE.md` with Moat rules. Claude Code will then run `moat check` before and after code changes.

### Cursor

`moat adapter all` creates `.cursor/rules.mdc`, and Cursor will follow Moat rules when modifying code.

### Pre-commit

`moat adapter precommit` installs a git pre-commit hook that runs checks before every commit.

## FAQ

### Q: What if checks fail?

A: If `moat check` fails, it means something is broken in your system. Fix until it passes. Don't skip.

### Q: When should I update the baseline?

A: If you **intentionally** add files, remove files, or refactor modules — these are allowed changes. After completing:

```bash
moat baseline save
```

### Q: Do I need a running server?

A: L1 API checks require a running server. Other checks don't. You can also use `moat check` for static analysis only.

## Project Structure

```
moat/
├── moat/
│   ├── cli.py              # CLI Entry
│   ├── runner.py           # Check Runner
│   ├── monitor.py          # Live Monitoring
│   ├── baseline.py         # Baseline Management
│   ├── discovery.py        # Project Auto-Discovery
│   ├── contract.py         # CONTRACT Generation
│   ├── checks/             # Four-layer Defense
│   │   ├── l1_import.py    # L1: Import Chain
│   │   ├── l1_api.py       # L1: API Endpoints
│   │   ├── l1_modules.py   # L1: Core Modules
│   │   ├── l1_files.py     # L1: File Integrity
│   │   ├── l1_subsystems.py # L1: Subsystems
│   │   ├── l1_behavior.py  # L1: Behavior Validation
│   │   ├── l2_schema.py    # L2: Structure Check
│   │   ├── l3_correlation.py # L3: Correlation Check
│   │   � └── l4_baseline.py  # L4: Baseline Comparison
│   ├── dashboard/
│   │   ├── server.py       # FastAPI Web Dashboard
│   │   └── static/         # Frontend
│   └── adapters/
│       └── __init__.py     # AI Adapters
├── pyproject.toml           # Build Config
├── README.md
└── LICENSE
```

## License

MIT © 2026 One Team
