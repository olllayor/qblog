.PHONY: help build build-css dev lint format test up down seed seed-clean

help:
	@echo "qblog DevOps & Development commands:"
	@echo "  make build       - Build Tailwind CSS and Python wheel"
	@echo "  make build-css   - Compile Tailwind CSS"
	@echo "  make dev         - Run local development server"
	@echo "  make lint        - Run Ruff format and lint checks"
	@echo "  make format      - Auto-format code with Ruff"
	@echo "  make test        - Run test suite with pytest"
	@echo "  make up          - Start PostgreSQL & Redis via Docker Compose"
	@echo "  make down        - Stop Docker Compose services"
	@echo "  make seed        - Populate database with mock data"
	@echo "  make seed-clean  - Truncate and re-seed database"

node_modules: package.json package-lock.json
	npm ci
	touch node_modules

build: build-css
	uv build

build-css: node_modules
	npm run build:css

dev:
	uv run python app.py

lint:
	uv run ruff format --check .
	uv run ruff check .

format:
	uv run ruff format .
	uv run ruff check --fix .

test:
	uv run pytest

up:
	docker compose up -d --wait

down:
	docker compose down

seed:
	uv run python seed_db.py

seed-clean:
	uv run python seed_db.py --clean
