# Makefile for easy development workflows.
# See docs/development.md for docs.
# Note GitHub Actions call uv directly, not this Makefile.

.DEFAULT_GOAL := default

.PHONY: default install lint lint-check test audit upgrade build clean

default: install lint test

install:
	uv sync --all-extras

lint:
	uv run --frozen python devtools/lint.py

# Check-only lint, matching CI (does not modify files).
lint-check:
	uv run --frozen python devtools/lint.py --check

test:
	uv run --frozen pytest

# Audit locked runtime, extras, and groups. pip-audit is ephemeral (uvx), not
# a project dependency. See SUPPLY-CHAIN-SECURITY.md.
audit:
	@tmp="$$(mktemp)"; \
	uv export --frozen --all-extras --all-groups --no-emit-project -q -o "$$tmp"; \
	uvx pip-audit --disable-pip --no-deps -r "$$tmp"

upgrade:
	uv sync --upgrade --all-extras --dev

build:
	uv build

clean:
	-rm -rf dist/
	-rm -rf *.egg-info/
	-rm -rf .pytest_cache/
	-rm -rf .ruff_cache/
	-rm -rf .mypy_cache/
	-rm -rf .venv/
	-find . -type d -name "__pycache__" -exec rm -rf {} +
