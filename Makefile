# Makefile for Horse Racing Prediction Project

# --- VARIABLES ---
# Default to today's date (DDMMYYYY) if not specified
DATE ?= $(shell date +%d%m%Y)

.PHONY: up down build clean logs train ingest test-backend test-frontend test-all type-check

# --- CONTROL COMMANDS ---
up:
	docker-compose up -d

down:
	docker-compose down

# The "Nuke": Stops containers and removes volumes (database data)
clean:
	docker-compose down -v --remove-orphans
	@echo "💥 System wiped clean. Database is empty."

build:
	docker-compose build

logs:
	docker-compose logs -f

# --- WORKFLOW COMMANDS ---

# Run the training script inside the backend container
train:
	@echo "🧠 Training ML Model..."
	docker-compose run --rm backend python -m src.ml.trainer

# Run the ETL Orchestrator. 
# Usage: make ingest (defaults to today) OR make ingest DATE=01012025
ingest:
	@echo "🚀 Ingesting data for date: $(DATE)"
	docker-compose run --rm backend python -m src.cli.etl --date $(DATE) --type all

# --- TESTING & QUALITY ---

test-backend:
	@echo "🧪 Running Backend Tests..."
	docker-compose run --rm backend pytest tests/ -v

test-frontend:
	@echo "🧪 Running Frontend Tests..."
	# FIXED: Changed from 'npm test' to 'pytest' because Streamlit is Python
	docker-compose run --rm frontend pytest frontend/tests/ -v

# Run ALL tests (Backend + Frontend)
test-all: test-backend test-frontend

type-check:
	@echo "🔍 Checking Types..."
	docker-compose run --rm backend mypy src/