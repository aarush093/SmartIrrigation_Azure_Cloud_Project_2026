# Cloud-Based Smart Irrigation Recommendation using Weather Intelligence
# BITE412L Cloud Computing, VIT. Phase-II build targets.
#
# Works on Linux, macOS and Windows (Git Bash or WSL). On Windows the
# virtualenv puts executables in Scripts/ rather than bin/, which is detected
# below rather than assumed.

SHELL := /bin/bash
.DEFAULT_GOAL := help

VENV := .venv
ifeq ($(OS),Windows_NT)
	BIN := $(VENV)/Scripts
	PY  := python
else
	BIN := $(VENV)/bin
	PY  := python3
endif

PYTHON := $(BIN)/python
PIP    := $(BIN)/pip

# Teammate code is written into handoff/ and committed by its owners from their
# own accounts. These targets copy it into place for local end-to-end runs only;
# handoff/ is gitignored and src/frontend and src/ai_model stay untouched in git.
HANDOFF_FRONTEND := handoff/student1_frontend
HANDOFF_AI       := handoff/student3_ai_model

.PHONY: help setup test lint format demo demo-offline script-samples script-html sim validate validate-hourly validate-inputs sensitivity func-start bicep-build deploy-plan deploy sync-handoff clean

help:  ## Show the available targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup:  ## Create the virtualenv and install the engine with dev dependencies
	$(PY) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@echo
	@echo "Environment ready. Run 'make test' and 'make lint'."

test:  ## Run the unit test suite (no network; integration tests are skipped)
	$(BIN)/pytest

test-integration:  ## Run the tests that hit Open-Meteo, SoilGrids and NASA POWER
	$(BIN)/pytest -m integration

validate:  ## Objective 2 ET0 cross-check against Open-Meteo. Hits the live API.
	$(BIN)/pytest tests/validation/et0_crosscheck.py -m integration -s

validate-hourly:  ## Settle the hourly-vs-daily ET0 hypothesis. Hits the live API.
	$(BIN)/pytest tests/validation/et0_hourly_hypothesis.py -m integration -s

validate-inputs:  ## Settle input-dataset vs methodology for ET0. Hits Open-Meteo and NASA POWER.
	$(BIN)/pytest tests/validation/et0_input_dataset.py -m integration -s

sensitivity:  ## Report the ET0 uncertainty budget in pump minutes. No network.
	$(BIN)/pytest tests/validation/et0_sensitivity.py -m integration -s

test-cov:  ## Run the unit suite with a coverage report
	$(BIN)/pytest --cov --cov-report=term-missing

lint:  ## Run ruff and mypy --strict
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .
	$(BIN)/mypy

format:  ## Apply ruff's formatter and autofixes
	$(BIN)/ruff check --fix .
	$(BIN)/ruff format .

sync-handoff:  ## Copy teammate handoff code into src/ for a local end-to-end run
	@echo "These files belong to Nayan and Krishna. This copies them so the"
	@echo "system runs end to end locally; they are NEVER committed from here."
	@if [ -d "$(HANDOFF_FRONTEND)" ]; then \
		mkdir -p src/frontend && cp -r $(HANDOFF_FRONTEND)/. src/frontend/ && \
		echo "copied $(HANDOFF_FRONTEND) -> src/frontend"; \
	else echo "note: $(HANDOFF_FRONTEND) not present, skipping"; fi
	@if [ -d "$(HANDOFF_AI)" ]; then \
		mkdir -p src/ai_model && cp -r $(HANDOFF_AI)/. src/ai_model/ && \
		echo "copied $(HANDOFF_AI) -> src/ai_model"; \
	else echo "note: $(HANDOFF_AI) not present, skipping"; fi
	@echo "Reminder: these files are committed by their owners, never from this branch."

demo:  ## Seed three farmers, pull live weather and soil, plan and render the calls
	$(PYTHON) -m irrigation_engine.devtools.demo --out results

demo-offline:  ## Same as demo but with no network, for a room with bad wifi
	$(PYTHON) -m irrigation_engine.devtools.demo --offline --out results

script-samples:  ## Write every rendered script to results/ for native-speaker review
	$(PYTHON) -m irrigation_engine.devtools.script_samples

script-html:  ## Render those scripts as a phone-readable page for a native speaker
	@# A terminal cannot be trusted with Devanagari or Tamil. This is the file to
	@# actually hand to a reviewer.
	$(PYTHON) -m irrigation_engine.devtools.script_page

sim:  ## Run the five-policy simulation study into results/
	@# Prefers the teammate's committed copy under src/ai_model, falling back
	@# to the handoff package so the simulation runs before he uploads it.
	@if [ -f src/ai_model/simulate_policies.py ]; then SIM=src/ai_model/simulate_policies.py; else SIM=$(HANDOFF_AI)/simulate_policies.py; echo "note: src/ai_model not committed yet; running the handoff copy"; fi; $(PYTHON) $$SIM --out results/

func-start:  ## Run the Azure Functions host locally
	cd src/azure/functions && func start

bicep-build:  ## Compile the Bicep to ARM, to check it parses. No Azure needed.
	bicep build src/azure/infra/main.bicep --stdout > /dev/null && echo 'Bicep compiles'

deploy-plan:  ## Preview the deployment. Changes nothing, spends nothing.
	az deployment group what-if \n		--resource-group $${AZURE_RESOURCE_GROUP:?set AZURE_RESOURCE_GROUP} \n		--template-file src/azure/infra/main.bicep \n		--parameters src/azure/infra/main.parameters.dev.json

deploy:  ## Deploy for real. THE OWNER RUNS THIS, never the build.
	@echo 'This creates billable Azure resources. Ctrl-C now if that is not intended.'
	@echo 'Every resource is on a free or consumption tier; see src/azure/infra/README.md.'
	az deployment group create \n		--resource-group $${AZURE_RESOURCE_GROUP:?set AZURE_RESOURCE_GROUP} \n		--template-file src/azure/infra/main.bicep \n		--parameters src/azure/infra/main.parameters.dev.json

clean:  ## Remove caches and build artefacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage
	find . -type d -name __pycache__ -not -path "./$(VENV)/*" -prune -exec rm -rf {} +
	find . -type d -name "*.egg-info" -not -path "./$(VENV)/*" -prune -exec rm -rf {} +
