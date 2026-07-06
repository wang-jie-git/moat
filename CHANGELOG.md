# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project setup
- Four-layer defense system (L0-L4)
- AI adapters (Claude Code, Cursor, Pre-commit)
- Web dashboard
- Live monitoring
- Baseline management

## [0.1.0] - 2025-07-07

### Added
- Initial public release
- L0: Syntax checking
- L1: Import/API/Modules/Files/Subsystems/Behavior checks
- L2: Schema validation
- L3: Correlation checks
- L4: Baseline comparison
- CLI: `moat check`, `moat init`, `moat baseline`, `moat watch`, `moat dashboard`
- Pre-commit hook integration
- GitHub Actions integration
- Claude Code adapter
- Cursor adapter

### Documentation
- README (Chinese + English)
- CONTRIBUTING.md
- CODE_OF_CONDUCT.md
- SECURITY.md

[Unreleased]: https://github.com/wang-jie-git/moat/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/wang-jie-git/moat/releases/tag/v0.1.0
