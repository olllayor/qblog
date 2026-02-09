# Repository Guidelines

## Project Structure & Module Organization
- `app.py` is the Flask entry point; it wires routes, templates, and app config.
- Core runtime modules live at the repo root: `articles.py`, `projects.py`,
  `database.py`, and `sitemap_generator.py`.
- `scripts/` holds maintenance utilities (for example `scripts/optimize_images.py`).
- `templates/` contains Jinja templates; `static/` holds CSS, images, and other
  web assets (see `static/blog-styles.css` for MDX-style formatting).
- SEO smoke checks live in `test_seo.py`.

## Build, Test, and Development Commands
- `uv run python app.py` runs the Flask app locally (defaults to port 4200).
- `uv run ruff check .` runs lint rules (pyflakes/bugbear/security/isort/etc.).
- `uv run ruff format .` formats code to the repo standard.
- `uv build` builds the package as the CI does.
- `uv run python test_seo.py` executes the SEO validation script.
- `uv run python scripts/optimize_images.py` runs image optimization tooling.

## Coding Style & Naming Conventions
- Python 3.12; 4-space indentation; 88-char line length (Ruff/Black style).
- Use double quotes and keep imports sorted (Ruff handles both).
- Modules are lowercase with underscores; functions and variables use snake_case.

## Testing Guidelines
- Current tests are focused scripts (e.g., `test_seo.py`); no coverage target
  is enforced yet.
- Name tests with `test_*.py` or `*_test.py` to align with Ruff test ignores.
- Prefer adding focused regression scripts when fixing a bug.

## Commit & Pull Request Guidelines
- Recent history uses short, imperative summaries; occasional Conventional
  Commit prefixes appear (e.g., `fix:`). Follow the existing tone.
- PRs should include: a concise description, test commands run, and screenshots
  for UI or template changes.

## Configuration & Secrets
- Local config is loaded from environment variables via `.env`.
- Required/typical vars: `FLASK_SECRET_KEY`, `DATABASE_URL` (or `POSTGRES_*`),
  and optional `REDIS_URL` for caching. Use `FLASK_ENV`/`FLASK_DEBUG` for dev.
