# Repository Guidelines

## Project Structure & Module Organization
- `app.py` is the Flask entry point; it wires routes, templates, and app config.
- Core runtime modules live at the repo root: `articles.py`, `projects.py`,
  `database.py`, `icons.py`, and `sitemap_generator.py`.
- `scripts/` holds maintenance utilities (for example `scripts/optimize_images.py`).
- `templates/` contains Jinja templates; `static/` holds CSS, fonts, images, and other
  web assets (see `static/blog-styles.css` for MDX-style formatting).
- Automated test suites live in `tests/`.

## Build, Test, and Development Commands
- `uv run python app.py` runs the Flask app locally (defaults to port 4200).
- `uv run ruff check .` runs lint rules (pyflakes/bugbear/security/isort/etc.).
- `uv run ruff format .` formats code to the repo standard.
- `uv run pytest` executes the test suite (including `tests/test_app.py`, `tests/test_seo.py`, `tests/test_performance.py`, `tests/test_seed_db.py`).
- `uv build` builds the package as the CI does.
- `npm run build` (or `npm run build:css` / `make build-css`) rebuilds Tailwind CSS.
- `docker compose up -d --wait` (or `make up`) starts local PostgreSQL 16 and Redis.
- `uv run python seed_db.py` (or `make seed`) seeds local database with realistic test data.
- `uv run python scripts/optimize_images.py` runs image optimization tooling.

## Coding Style & Naming Conventions
- Python 3.12; 4-space indentation; 88-char line length (Ruff/Black style).
- Use double quotes and keep imports sorted (Ruff handles both).
- Modules are lowercase with underscores; functions and variables use snake_case.

## Testing Guidelines
- Tests are executed with pytest under `tests/` (e.g., `tests/test_app.py`, `tests/test_seo.py`, `tests/test_performance.py`, `tests/test_seed_db.py`).
- Name tests with `test_*.py` or `*_test.py` to align with Ruff test ignores.
- Every new feature or regression fix should include pytest tests.

## Commit & Pull Request Guidelines
- Recent history uses short, imperative summaries; occasional Conventional
  Commit prefixes appear (e.g., `fix:`). Follow the existing tone.
- PRs should include: a concise description, test commands run, and screenshots
  for UI or template changes.

## Configuration & Secrets
- Local config is loaded from environment variables via `.env`.
- Required/typical vars: `FLASK_SECRET_KEY`, `DATABASE_URL` (or `POSTGRES_*`),
  and optional `REDIS_URL` for caching. Use `FLASK_ENV`/`FLASK_DEBUG` for dev.
