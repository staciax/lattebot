default: help

.PHONY: help
help:
	@echo "Puyu Makefile"
	@echo ""
	@echo "\033[1;32mUsage:\033[0m \033[1;36mmake <target>\033[0m"
	@echo ""
	@echo "\033[1;32mAvailable targets:\033[0m"
	@grep -E '^[a-zA-Z0-9 _-]+:.*#' Makefile | \
		while read -r line; do \
		name=$$(echo $$line | cut -d':' -f1); \
		desc=$$(echo $$line | cut -d'#' -f2-); \
		printf "  \033[1;36m%-8s\033[0m %s\n" "$${name}" "$$desc"; \
	done

.PHONY: sync
.SILENT: sync
sync: # Install dependencies
	uv sync

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
	uv run mypy lattebot tests
	uv run ruff check lattebot tests
	uv run ruff format lattebot tests --check

.PHONY: mypy
.SILENT: mypy
mypy: # Run type checks with mypy
	uv run mypy lattebot tests

.PHONY: format
.SILENT: format
format: # Format the code
	uv run ruff check lattebot tests --fix
	uv run ruff format lattebot tests

.PHONY: format-check
.SILENT: format-check
format-check: # Check code formatting
	uv run ruff format lattebot tests --check

.PHONY: tests
.SILENT: tests
tests: # Run the tests
	uv run pytest
	# uv run coverage run --source=lattebot -m pytest
	# uv run coverage report --show-missing

.PHONY: check
.SILENT: check
check: format-check lint mypy tests # Run all checks