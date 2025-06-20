.PHONY: help install dev-install test lint format check-format publish clean init

# Colors
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
WHITE  := $(shell tput -Txterm setaf 7)
RESET  := $(shell tput -Txterm sgr0)

# Help target
help: ## Show this help
	@echo '\nUsage: make <target> [VARIABLE=value]'
	@echo '\nTargets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "${YELLOW}%-20s${GREEN}%s${RESET}\n", $$1, $$2}' $(MAKEFILE_LIST) | sort

# Project initialization
init: ## Initialize project structure
	@echo "${GREEN}Initializing project structure...${RESET}"
	@mkdir -p waproprint
	@touch waproprint/__init__.py
	@if [ ! -f waproprint/__init__.py ]; then \
		echo "${YELLOW}Creating waproprint package...${RESET}"; \
		echo "# waproprint package" > waproprint/__init__.py; \
	fi
	@echo "${GREEN}Project structure initialized.${RESET}"

# Poetry commands
install: ## Install the project and its dependencies
	@echo "${GREEN}Installing project...${RESET}"
	poetry install --no-root || (echo "${YELLOW}Installing dependencies first...${RESET}" && poetry install --only main)
	@if [ $$? -eq 0 ]; then \
		echo "${GREEN}Project installed successfully!${RESET}"; \
		echo "Run 'poetry shell' to activate the virtual environment."; \
	else \
		echo "${YELLOW}Installation completed with warnings.${RESET}"; \
	fi

update: ## Update project dependencies
	@echo "${GREEN}Updating dependencies...${RESET}"
	poetry update

dev-install: ## Install development dependencies
	@echo "${GREEN}Installing development dependencies...${RESET}
	poetry install --with dev

# Development
test: ## Run tests
	@echo "${GREEN}Running tests...${RESET}"
	poetry run pytest -v

lint: ## Run linter
	@echo "${GREEN}Running linter...${RESET}"
	poetry run pylint --recursive=y .

format: ## Format code
	@echo "${GREEN}Formatting code...${RESET}"
	poetry run autopep8 --in-place --recursive .

check-format: ## Check code formatting
	@echo "${GREEN}Checking code formatting...${RESET}"
	poetry run autopep8 --diff --recursive .

# Build and publish
build: ## Build the package
	@echo "${GREEN}Building package...${RESET}"
	poetry version patch
	poetry build

publish: ## Publish the package to PyPI
	@echo "${YELLOW}Are you sure you want to publish to PyPI? [y/N] ${RESET}"
	@read -p "" confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		echo "${GREEN}Publishing to PyPI...${RESET}"; \
		poetry publish --build; \
	else \
		echo "${YELLOW}Publishing cancelled${RESET}"; \
	fi

# Cleanup
clean: ## Clean up build artifacts
	@echo "${GREEN}Cleaning up...${RESET}"
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ .coverage htmlcov/
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.py[co]" -delete

# Configuration
config: ## Show current Poetry configuration
	@echo "${GREEN}Current Poetry configuration:${RESET}"
	poetry config --list

env: ## Show current Python environment info
	@echo "${GREEN}Python environment:${RESET}"
	poetry run python --version
	@echo "\n${GREEN}Poetry environment:${RESET}"
	poetry env info

# Docker (optional)
docker-build: ## Build Docker image
	docker build -t waproprint .

docker-run: ## Run Docker container
	docker run -it --rm waproprint

# Dependencies
deps: ## Show dependency tree
	poetry show --tree

deps-outdated: ## Check for outdated dependencies
	poetry show --outdated

# Documentation
docs: ## Generate documentation
	@echo "${GREEN}Generating documentation...${RESET}"
	# Add documentation generation command here
