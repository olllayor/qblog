"""Tests for SEO features, meta tags, structured data, sitemaps, and assets."""

from pathlib import Path
from unittest.mock import MagicMock

from flask import render_template

from sitemap_generator import generate_image_sitemap, generate_sitemap

OPTIMIZED_IMAGES = [
    "me.webp",
    "myself.webp",
    "photo.webp",
    "favicon-32x32.png",
    "favicon-optimized.ico",
    "myself-social-optimized.jpg",
]


def test_seo_meta_tags_homepage(app):
    """Verify default SEO and social graph tags rendered in seo_meta.html."""
    with app.test_request_context("/"):
        meta = render_template("seo_meta.html")
        assert 'property="og:title"' in meta
        assert 'property="og:type"' in meta
        assert 'property="og:image"' in meta
        assert 'property="og:url"' in meta
        assert 'name="twitter:card"' in meta
        assert 'name="twitter:title"' in meta
        assert 'name="twitter:image"' in meta
        assert 'name="robots"' in meta


def test_seo_meta_tags_custom_article(app):
    """Verify custom article metadata overrides defaults in seo_meta.html."""
    custom_context = {
        "page_title": "Deep Dive into Python Web Performance",
        "page_description": "Comprehensive guide on optimizing Flask and Postgres.",
        "page_image": "https://example.com/custom-og.jpg",
        "page_url": "https://example.com/blog/deep-dive-python-perf",
        "page_type": "article",
    }
    with app.test_request_context("/blog/deep-dive-python-perf"):
        meta = render_template("seo_meta.html", **custom_context)
        assert "Deep Dive into Python Web Performance" in meta
        assert "Comprehensive guide on optimizing Flask and Postgres." in meta
        assert "https://example.com/custom-og.jpg" in meta
        assert 'name="twitter:card" content="summary_large_image"' in meta
        assert 'property="og:type" content="article"' in meta


def test_structured_data_rendering(app):
    """Verify JSON-LD structured data template outputs valid schema types."""
    with app.test_request_context("/"):
        sd = render_template("person_schema.html")
        assert '"@type": "Person"' in sd
        assert "Ollayor Maxammadnabiyev" in sd
        assert "Software Engineer" in sd


def test_sitemap_generation(app):
    """Ensure standard sitemap generator returns valid page URLs."""
    with app.test_request_context("/"):
        pages = generate_sitemap(app, articles=[])
        assert isinstance(pages, list)
        assert len(pages) > 0
        assert any("index" in p["url"] or p["url"].endswith("/") for p in pages)


def test_image_sitemap_generation(app):
    """Ensure image sitemap generator produces static and article image mappings."""
    mock_article = MagicMock()
    mock_article.is_published = True
    mock_article.title = "Test Article"
    mock_article.get_first_image.return_value = "img/test.webp"

    with app.test_request_context("/"):
        images = generate_image_sitemap(app, articles=[mock_article])
        assert isinstance(images, list)
        assert len(images) >= 3  # 2 static images + 1 article image
        assert any("loc" in img for img in images)
        assert any("img/test.webp" in img["loc"] for img in images)
        assert any(img.get("title") == "Test Article" for img in images)


def test_optimized_images_exist(app):
    """Verify that all core optimized static assets exist and are non-empty."""
    static_dir = Path(app.root_path) / "static"
    for img_name in OPTIMIZED_IMAGES:
        img_path = static_dir / img_name
        assert img_path.is_file(), (
            f"Expected optimized image {img_name} to exist at {img_path}"
        )
        assert img_path.stat().st_size > 0, (
            f"Expected {img_name} to have non-zero file size"
        )
