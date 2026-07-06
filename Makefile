# ─────────────────────────────────────────────────────────────────────────────
# Scalable URL Shortener — Makefile
#
# Prerequisites: make, Python 3.11+, Docker (optional)
# ─────────────────────────────────────────────────────────────────────────────

PYTHON   := venv/Scripts/python.exe   # Windows venv
PIP      := venv/Scripts/pip.exe
PYTEST   := venv/Scripts/pytest.exe
UVICORN  := venv/Scripts/uvicorn.exe

# Detect OS — override PYTHON/PIP/PYTEST for Linux/macOS
ifeq ($(OS),Windows_NT)
    PYTHON  := venv/Scripts/python.exe
    PIP     := venv/Scripts/pip.exe
    PYTEST  := venv/Scripts/pytest.exe
    UVICORN := venv/Scripts/uvicorn.exe
else
    PYTHON  := venv/bin/python
    PIP     := venv/bin/pip
    PYTEST  := venv/bin/pytest
    UVICORN := venv/bin/uvicorn
endif

.PHONY: help install venv run migrate migrate-down test test-unit test-integration \
        coverage lint format docker-up docker-down docker-build clean

# ── Default target ────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  Scalable URL Shortener — Available make commands"
	@echo "  ──────────────────────────────────────────────────"
	@echo "  make install          Create venv + install dependencies"
	@echo "  make run              Start dev server (uvicorn --reload)"
	@echo "  make migrate          Apply Alembic migrations (upgrade head)"
	@echo "  make migrate-down     Rollback last Alembic migration"
	@echo "  make test             Run full test suite"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make coverage         Run tests with HTML coverage report"
	@echo "  make lint             Run ruff linter"
	@echo "  make format           Auto-format with ruff"
	@echo "  make docker-up        Start Postgres + Redis via Docker Compose"
	@echo "  make docker-down      Stop and remove Docker containers"
	@echo "  make docker-build     Build the API Docker image"
	@echo "  make clean            Remove venv + __pycache__ directories"
	@echo ""

# ── Setup ─────────────────────────────────────────────────────────────────────
venv:
	python -m venv venv
	@echo "✔ Virtual environment created."

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "✔ Dependencies installed."

# ── Development server ────────────────────────────────────────────────────────
run:
	$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

# ── Database migrations ───────────────────────────────────────────────────────
migrate:
	$(PYTHON) -m alembic upgrade head

migrate-down:
	$(PYTHON) -m alembic downgrade -1

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
	$(PYTEST) tests/ -v --tb=short

test-unit:
	$(PYTEST) tests/unit/ -v --tb=short

test-integration:
	$(PYTEST) tests/integration/ -v --tb=short

coverage:
	$(PYTEST) tests/ -v --cov=app --cov-report=term-missing --cov-report=html
	@echo "✔ HTML coverage report written to htmlcov/index.html"

# ── Code quality ──────────────────────────────────────────────────────────────
lint:
	$(PYTHON) -m ruff check app/ tests/

format:
	$(PYTHON) -m ruff format app/ tests/

# ── Docker ────────────────────────────────────────────────────────────────────
docker-up:
	docker compose up -d postgres redis
	@echo "✔ PostgreSQL and Redis are running."
	@echo "   Postgres: localhost:5432  Redis: localhost:6379"

docker-down:
	docker compose down -v
	@echo "✔ Containers stopped and volumes removed."

docker-build:
	docker build -t url-shortener:latest .
	@echo "✔ Docker image built: url-shortener:latest"

docker-all:
	docker compose up -d
	@echo "✔ Full stack (Postgres, Redis, API) is running."
	@echo "   API:      http://localhost:8000"
	@echo "   Swagger:  http://localhost:8000/docs"

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean:
	rm -rf venv htmlcov .coverage .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "✔ Cleaned up."
