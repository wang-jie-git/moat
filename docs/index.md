---
title: Home
---

# Moat — AI Coding Gatekeeper

**Zero-config, real-time guardrails for AI-generated code.**

Moat is a local CLI + CI tool that catches architecture breaks, security leaks, and regression bugs **before** AI-generated code hits your repo.

<div class="grid cards" markdown>

-   :zap: **Lightning fast** — Each check completes in <0.2s
-   :shield: **4-layer defense** — Syntax → Survival → Structure → Correlation
-   :key: **Secret detection** — API keys, tokens, passwords (10+ patterns)
-   :chains: **Cross-file analysis** — "Did fixing A break B?"
-   :brain: **AI-context aware** — MCP adapter for Claude Code / Cursor
-   :house: **100% local** — Your code never leaves your machine

</div>

## Quick Start

```bash
pip install moat-ai
cd your-project
moat check
```

That's it. No config file, no server, no setup.

## Why Moat?

| Feature | Other Tools | Moat |
|---------|-------------|------|
| Architecture enforcement | ❌ | ✅ 4-layer gate |
| Cross-file impact analysis | ❌ | ✅ L3 Correlation |
| Self-evolution (pain score) | ❌ | ✅ Learns what breaks |
| AI-context integration | ❌ | ✅ MCP adapter |
| Local-only, zero data leaving | ❌ | ✅ |
| Setup time | Days | **Seconds** |

## License

Apache 2.0 &copy; 2026 One Team
