.PHONY: help install format lint test clean run dry-run setup

help: ## Show this help message
	@echo "Dental AI Grant Finder - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

format: ## Format code with black and ruff
	black src/ tests/
	ruff check --fix src/ tests/

lint: ## Run linting checks
	ruff check src/ tests/
	black --check src/ tests/

test: ## Run tests
	pytest tests/ -v

test-coverage: ## Run tests with coverage
	pytest tests/ --cov=src --cov-report=html --cov-report=term

clean: ## Clean up generated files
	rm -rf __pycache__/
	rm -rf src/__pycache__/
	rm -rf src/*/__pycache__/
	rm -rf tests/__pycache__/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -f .coverage
	rm -f opportunities.db
	rm -f grant_finder.log

run: ## Run the pipeline
	python -m src.pipeline

dry-run: ## Run the pipeline in dry-run mode
	python -m src.pipeline --dry-run

setup: ## Initial setup (install dependencies and validate config)
	@echo "Setting up Dental AI Grant Finder..."
	pip install -r requirements.txt
	@echo "Validating configuration..."
	python -c "from src.config import config; config.validate(); print('Configuration is valid!')"

check-config: ## Check configuration without running pipeline
	python -c "from src.config import config; config.validate(); print('Configuration is valid!')"

logs: ## Show recent logs
	tail -f grant_finder.log

create-env: ## Create .env file from template
	cp env.example .env
	@echo "Created .env file from template. Please edit with your settings."

test-connections: ## Test all external connections
	@echo "Testing Google Sheets connection..."
	python -c "from src.storage.sheet import GoogleSheetsManager; gs = GoogleSheetsManager(); print('Google Sheets: OK' if gs.test_connection() else 'Google Sheets: FAILED')"
	@echo "Testing Slack connection..."
	python -c "from src.notify.slack import SlackNotifier; slack = SlackNotifier(); print('Slack: OK' if slack.test_connection() else 'Slack: DISABLED')"
	@echo "Testing email connection..."
	python -c "from src.notify.emailer import EmailNotifier; email = EmailNotifier(); print('Email: OK' if email.test_connection() else 'Email: DISABLED')"

dev-setup: ## Complete development setup
	@echo "Setting up development environment..."
	make install
	make create-env
	@echo "Development setup complete!"
	@echo "Next steps:"
	@echo "1. Edit .env with your configuration"
	@echo "2. Add Google service account JSON to creds/service_account.json"
	@echo "3. Run 'make check-config' to validate"
	@echo "4. Run 'make dry-run' to test the pipeline" 