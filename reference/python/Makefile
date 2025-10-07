.PHONY: build-docs serve-clean-docs serve-docs
# .PHONY: build-docs serve-clean-docs serve-docs format-docs lint-docs tests

# ---------------------------------------
# Python reference documentation Makefile
# ---------------------------------------

all: help

# Build files for deployment
build:
	uv sync --link-mode=copy
	uv run python -m mkdocs build -c -f mkdocs.yml

# To preview what the docs will look like when built
serve-clean-docs:
	uv run python -m mkdocs serve -c -f mkdocs.yml --strict

# For local development; uses --dirty to avoid rebuilding unchanged files
serve-docs:
	uv run python -m mkdocs serve -f mkdocs.yml --dirty

# format-docs:
# 	uv run ruff format docs
# 	uv run ruff check --fix docs

# lint-docs:
# 	uv run ruff format --check docs
# 	uv run ruff check docs

# tests:
# 	uv run pytest tests/unit_tests

help:
	@echo "Available targets:"
	@echo "  build            - Build the documentation for deployment"
	@echo "  serve-clean-docs - Serve the documentation with a clean build (for previewing)"
	@echo "  serve-docs       - Serve the documentation for local development (faster)"
