venv=.venv
python=$(venv)/bin/python

default: help

.PHONY: help
help:
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

.PHONY: run
.SILENT: run
run: # Run the app 
	$(python) launcher.py

.PHONY: dev
.SILENT: dev
dev: # Run the app with coverage
	$(python) -m coverage run --source=lattebot launcher.py 

.PHONY: report
.SILENT: report
report: # See the coverage report
	$(python) -m coverage report

.PHONY: lint
.SILENT: lint
lint: # Run the linter
	mypy lattebot
	ruff check lattebot
	ruff format lattebot --check

.PHONY: format
.SILENT: format
format: # Format the code
	ruff check lattebot --fix
	ruff format lattebot
