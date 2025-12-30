# --- VARIABLES ---
DATE ?= $(shell date +%d%m%Y)

# --- PHONY TARGETS ---
.PHONY: up down build build-nc clean logs train ingest test-backend test-frontend test-all type-check clean-pycache

# --- CONTROL COMMANDS ---
up:
	docker-compose up -d

down:
	docker-compose down

# Standard build
build:
	docker-compose build

# No-cache build (The "Force Refresh" you used to fix the path issues)
build-nc:
	docker-compose build --no-cache

# The "Nuke": Stops containers, removes volumes, and wipes local Python caches
clean: down
	docker-compose down -v --remove-orphans
	@$(MAKE) clean-pycache
	@echo "💥 System wiped clean. Database is empty and caches removed."

# Helper to remove local __pycache__ and .pytest_cache that cause permission errors
clean-pycache:
	@echo "🧹 Cleaning Python cache folders with sudo..."
	# We use sudo here because these files were created by root inside Docker
	sudo find . -type d -name "__pycache__" -exec rm -rf {} +
	sudo find . -type d -name ".pytest_cache" -exec rm -rf {} +

logs:
	docker-compose logs -f

# --- WORKFLOW COMMANDS ---

train:
	@echo "🧠 Training ML Model..."
	docker-compose run --rm backend python -m src.ml.trainer

ingest:
	@echo "🚀 Ingesting data for date: $(DATE)"
	docker-compose run --rm backend python -m src.cli.etl --date $(DATE) --type all

# --- TESTING & QUALITY ---

test-backend:
	@echo "🧪 Running Backend Tests..."
	docker-compose run --rm backend pytest tests/ -v

test-frontend:
	@echo "🧪 Running Frontend Tests..."
	# Added PYTHONPATH to ensure 'ui', 'api', and 'state' modules are found inside /app
	docker-compose run --rm -e PYTHONPATH=/app frontend pytest tests/ -v

test-all: test-backend test-frontend

type-check:
	@echo "🔍 Checking Types..."
	docker-compose run --rm backend mypy src/