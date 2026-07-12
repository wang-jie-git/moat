---
title: Usage
---

# Usage Guide

## Check modes

```bash
# Quick check (modified files only, < 5s)
moat check

# Full check (all files, may be slow)
moat check --full

# Incremental check (AST diff + impact analysis, < 10s)
moat check --diff

# Legacy mode (full output)
moat check --legacy
```

## Architecture verification

```bash
# Run full architecture verification
moat verify --all

# Check specific subsystem
moat verify --subsystem auth

# Generate architecture report
moat architecture --format json
```

## Real-time monitoring

```bash
# Watch logs for errors
moat watch --log logs/backend.log

# Custom filter
moat watch --log logs/app.log --filter "ERROR|Traceback|ImportError"

# Run in background
nohup moat watch --log logs/backend.log > logs/moat_watch.log 2>&1 &
```

## Gatekeeper rules

```bash
# Check a specific file
moat gatekeeper check --file app.py

# Check entire project
moat gatekeeper check --project .
```

## Baseline management

```bash
# Save current state as baseline
moat baseline save

# Compare against baseline
moat baseline diff

# List all baselines
moat baseline list
```

## AI Adapters

```bash
# Install Claude Code adapter (adds rules to CLAUDE.md)
moat adapter claude

# Install pre-commit hook
moat adapter precommit

# Install all adapters
moat adapter all
```
