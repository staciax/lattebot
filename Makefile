default: help

.PHONY: help
help:
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

.PHONY: run
.SILENT: run
run: # Run the app 
	uv run launcher.py

.PHONY: dev
.SILENT: dev
dev: # Run the app with coverage
	uv run coverage run --source=lattebot launcher.py 

.PHONY: report
.SILENT: report
report: # See the coverage report
	uv run coverage report

.PHONY: lint
.SILENT: lint
lint: # Run the linter
	uv run mypy lattebot
	uv run ruff check lattebot
	uv run ruff format lattebot --check

.PHONY: format
.SILENT: format
format: # Format the code
	uv run ruff check lattebot --fix
	uv run ruff format lattebot

.PHONY: tests
.SILENT: tests
tests: # Run the tests
	uv run pytest
	# uv run coverage run --source=lattebot -m pytest
	# uv run coverage report --show-missing