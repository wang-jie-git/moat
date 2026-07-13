# Moat 开发环境 — 一键测试 / 检查 / 清理
# 用法:
#   make test       # 跑全部测试（跳过 diff_bugfix）
#   make test-full  # 跑全部测试（含 diff_bugfix，可能较慢）
#   make check      # 等价于 moat check --full
#   make clean      # 清理缓存

PYTHON ?= python3
MOAT ?= moat

# 默认目标
.DEFAULT_GOAL := test

# 清除 PYTHONPATH 防止 SRE module mismatch
unexport PYTHONPATH

.PHONY: test test-full check check-quick clean venv

test:
	PYTHONPATH="" $(PYTHON) -m pytest tests/ -q --tb=short -k "not test_diff_bug_fix"

test-full:
	PYTHONPATH="" $(PYTHON) -m pytest tests/ -q --tb=short

check:
	PYTHONPATH="" $(MOAT) check --full

check-quick:
	PYTHONPATH="" $(MOAT) check --quick

venv:
	$(PYTHON) -m venv .venv
	.venv/bin/pip install -e ".[dev]"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .moat/evolution_metrics.json 2>/dev/null || true
	@echo "✅ 已清理"