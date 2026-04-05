.PHONY: help install dev-install run dev test clean migrate upgrade downgrade init-db reset-db lint format check-format deps-update venv activate mock-server mock-server-bg stop-mock-server both-servers

# Default target
help:
	@echo "==============================================="
	@echo "           Retinal Image System - Make Commands"
	@echo "==============================================="
	@echo ""
	@echo "🚀 QUICK START:"
	@echo "  setup-dev     - Complete development environment setup"
	@echo "  quick-start   - Install deps, migrate DB, and run Flask app"
	@echo "  both-servers  - Start both Flask app and mock inference server"
	@echo ""
	@echo "📦 ENVIRONMENT SETUP:"
	@echo "  venv          - Create virtual environment"
	@echo "  install       - Install production dependencies"
	@echo "  dev-install   - Install development dependencies"
	@echo "  setup-hooks   - Setup pre-commit hooks"
	@echo ""
	@echo "🏃 RUNNING APPLICATIONS:"
	@echo "  run           - Run Flask application (production mode)"
	@echo "  dev           - Run Flask application (development mode)"
	@echo "  mock-server   - Start mock inference server (foreground)"
	@echo "  mock-server-bg- Start mock inference server (background)"
	@echo "  stop-mock-server - Stop background mock inference server"
	@echo ""
	@echo "🗄️ DATABASE MANAGEMENT:"
	@echo "  init-db       - Initialize database from scratch"
	@echo "  migrate       - Create new migration (use: make migrate msg='description')"
	@echo "  upgrade       - Apply pending database migrations"
	@echo "  downgrade     - Revert last database migration"
	@echo "  reset-db      - Reset database (⚠️  destructive operation)"
	@echo "  backup-db     - Backup database"
	@echo ""
	@echo "🧪 TESTING & QUALITY:"
	@echo "  test          - Run tests with coverage"
	@echo "  lint          - Run code linting (flake8)"
	@echo "  format        - Format code (black + isort)"
	@echo "  check-format  - Check code formatting"
	@echo ""
	@echo "🛠️ MAINTENANCE:"
	@echo "  clean         - Clean temporary files and caches"
	@echo "  deps-update   - Update all dependencies"
	@echo "  health-check  - Check if Flask app is running"
	@echo ""
	@echo "🐳 DOCKER (if available):"
	@echo "  docker-build  - Build Docker image"
	@echo "  docker-run    - Run Docker container"
	@echo ""
	@echo "For more details, see README.md"
	@echo "==============================================="

# Python and pip commands
PYTHON := python
PIP := pip
FLASK := flask

# Virtual environment
VENV_DIR := venv
VENV_ACTIVATE := $(VENV_DIR)/Scripts/activate

# Mock server process ID file
MOCK_SERVER_PID := .mock_server.pid

# Get port values from environment or use defaults
FLASK_PORT := $(shell echo $${FLASK_PORT:-8080})
PROCESSING_SERVICE_PORT := $(shell echo $${PROCESSING_SERVICE_PORT:-5000})

# Create virtual environment
venv:
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "Virtual environment created. Activate it with: $(VENV_ACTIVATE)"

# Install production dependencies
install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

# Install development dependencies
dev-install: install
	$(PIP) install pytest pytest-cov flake8 black isort pre-commit

# Run Flask application in production mode
run:
	$(PYTHON) run.py

# Run Flask application in development mode
dev:
	set FLASK_ENV=development && set FLASK_DEBUG=1 && $(PYTHON) run.py

# Run tests
test:
	pytest tests/ -v --cov=server --cov-report=html --cov-report=term

# Clean up temporary files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -name ".coverage" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	del /f /q *.log 2>nul || true

# Database migrations
migrate:
	$(PYTHON) migrate.py db migrate -m "$(msg)"

# Apply database migrations
upgrade:
	$(PYTHON) migrate.py db upgrade

# Revert last migration
downgrade:
	$(PYTHON) migrate.py db downgrade

# Initialize database
init-db:
	$(PYTHON) migrate.py db init
	$(PYTHON) migrate.py db migrate -m "Initial migration"
	$(PYTHON) migrate.py db upgrade

# Reset database (careful!)
reset-db:
	@echo "Warning: This will delete all data in the database!"
	@echo "Press Ctrl+C to cancel, or press Enter to continue..."
	@pause
	$(PYTHON) migrate.py db downgrade base
	$(PYTHON) migrate.py db upgrade

# Linting
lint:
	flake8 server/ client/ --max-line-length=88 --extend-ignore=E203,W503

# Format code
format:
	black server/ client/ --line-length=88
	isort server/ client/ --profile black

# Check formatting
check-format:
	black server/ client/ --line-length=88 --check
	isort server/ client/ --profile black --check-only

# Update dependencies
deps-update:
	$(PIP) list --outdated --format=freeze | findstr /v "^\-e" | for /f "tokens=1 delims==" %%i in ('more') do $(PIP) install --upgrade %%i
	$(PIP) freeze > requirements.txt

# Setup pre-commit hooks
setup-hooks:
	pre-commit install

# Install everything for development
setup-dev: venv dev-install setup-hooks
	@echo "Development environment setup complete!"
	@echo "Activate virtual environment with: $(VENV_ACTIVATE)"

# Quick development start
quick-start: install upgrade dev

# Production deployment setup
prod-setup: install upgrade
	@echo "Production setup complete!"

# Check application health
health-check:
	curl -f http://localhost:$(FLASK_PORT)/health || echo "Flask application is not responding on port $(FLASK_PORT)"

# Check mock server health  
health-check-mock:
	curl -f http://localhost:$(PROCESSING_SERVICE_PORT)/health || echo "Mock API server is not responding on port $(PROCESSING_SERVICE_PORT)"

# Backup database (PostgreSQL)
backup-db:
	@echo "Enter database name:"
	@set /p DB_NAME=
	pg_dump $(DB_NAME) > backup_$(shell date +%Y%m%d_%H%M%S).sql

# Docker commands (if using Docker)
docker-build:
	docker build -t retinal-system .

docker-run:
	docker run -p 5000:5000 retinal-system

docker-compose-up:
	docker compose -f ../build/docker/docker-compose.yml up -d

docker-compose-down:
	docker compose -f ../build/docker/docker-compose.yml down

# Start mock inference server in foreground
mock-server:
	@echo "Starting mock inference server on http://localhost:$(PROCESSING_SERVICE_PORT)..."
	cd .. && $(PYTHON) mock_api.py

# Start mock inference server in background
mock-server-bg:
	@echo "Starting mock inference server in background on http://localhost:$(PROCESSING_SERVICE_PORT)..."
	cd .. && start /B $(PYTHON) mock_api.py
	@echo "Mock server started in background on port $(PROCESSING_SERVICE_PORT)"
	@echo "Use 'make stop-mock-server' to stop it"

# Stop background mock inference server
stop-mock-server:
	@echo "Stopping mock inference server..."
	@for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV ^| findstr "mock_api"') do taskkill /PID %%i /F 2>nul || true
	@echo "Mock server stopped"

# Start both Flask app and mock server
both-servers: mock-server-bg
	@echo "Starting Flask application on port $(FLASK_PORT)..."
	@timeout /t 2 /nobreak >nul
	$(PYTHON) run.py