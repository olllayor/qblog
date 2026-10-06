"""Tests for SEO features, meta tags, structured data, sitemaps, and assets."""

from pathlib import Path

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
        assert 'rel="canonical"' in meta


def test_seo_article_structured_data(app):
    """Verify JSON-LD and breadcrumbs rendered for article pages."""
    with app.test_request_context("/article/test-post"):
        meta = render_template(
            "seo_meta.html",
            page_type="article",
            page_title="Test Post",
            page_description="A test post description",
            article_date="2026-10-06T12:00:00Z",
        )
        assert '"@context": "https://schema.org"' in meta
        assert '"@type": "BlogPosting"' in meta
        assert '"@type": "BreadcrumbList"' in meta
        assert '"position": 1' in meta
        assert '"position": 2' in meta
        assert '"position": 3' in meta


def test_person_schema_structured_data(app):
    """Verify JSON-LD Person and WebSite schema in person_schema.html."""
    with app.test_request_context("/"):
        schema = render_template("person_schema.html")
        assert '"@context": "https://schema.org"' in schema
        assert '"@type": "Person"' in schema
        assert '"@type": "WebSite"' in schema


def test_sitemap_generation(app):
    """Ensure standard sitemap generator returns valid page URLs."""
    with app.test_request_context("/"):
        pages = generate_sitemap(app, articles=[])
        assert isinstance(pages, list)
        assert len(pages) > 0
        assert any("index" in p["url"] or p["url"].endswith("/") for p in pages)


def test_image_sitemap_generation(app):
    """Ensure image sitemap generator produces static and article image mappings."""
    with app.test_request_context("/"):
        images = generate_image_sitemap(app, articles=[])
        assert isinstance(images, list)
        assert len(images) > 0
        assert any("loc" in img for img in images)


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
