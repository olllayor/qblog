# qblog

A modern Flask blog with MDX-inspired styling and production-focused SEO.

## Project Layout

- `app.py`: Flask entry point and route wiring.
- `articles.py`, `projects.py`, `database.py`, `sitemap_generator.py`: core runtime modules.
- `scripts/`: maintenance utilities (for example image optimization).
- `templates/`: Jinja templates.
- `static/`: CSS, media, and web assets.

## Getting Started

```bash
# Install dependencies
uv sync --locked

# Run the application
uv run python app.py
```

## Useful Commands

```bash
# Lint and format
uv run ruff check .
uv run ruff format .

# Build package
uv build

# SEO smoke test
uv run python test_seo.py

# Optimize static images
uv run python scripts/optimize_images.py
```

## CI

The CI workflow (`.github/workflows/ci.yml`) runs:

- Ruff format check
- Ruff lint checks
- `uv build`
- fresh wheel install verification
