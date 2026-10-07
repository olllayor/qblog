"""Tests for SEO features, meta tags, structured data, sitemaps, and assets."""

import json
import re
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from flask import render_template

from articles import Article
from sitemap_generator import generate_image_sitemap, generate_sitemap

LD_JSON_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)

ADVERSARIAL_TEXTS = [
    pytest.param("line one\nline two", id="newline"),
    pytest.param('He said "hello" and it\'s fine', id="quotes"),
    pytest.param("x</script><script>alert(1)", id="script-breakout"),
    pytest.param("Uzbekiston \u2014 \u00absalom\u00bb \u2026", id="unicode"),
]

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
        assert f'<link rel="canonical" href="{custom_context["page_url"]}" />' in meta
        assert '"@type": "BlogPosting"' in meta
        assert '"@type": "BreadcrumbList"' in meta
        assert '"position": 1' in meta
        assert '"position": 2' in meta


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
    mock_article.slug = "test-article"
    mock_article.get_summary.return_value = "Test article summary"
    mock_article.get_first_image.return_value = "img/test.webp"

    with app.test_request_context("/"):
        images = generate_image_sitemap(app, articles=[mock_article])
        assert isinstance(images, list)
        assert len(images) >= 3  # 2 static images + 1 article image
        assert any("loc" in img for img in images)
        assert any("img/test.webp" in img["loc"] for img in images)
        assert any(
            img.get("title") == "Test Article"
            and img.get("caption") == "Test article summary"
            and "test-article" in img.get("page_url", "")
            for img in images
        )


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


@pytest.mark.parametrize("text", ADVERSARIAL_TEXTS)
def test_article_json_ld_parses_with_adversarial_text(app, text):
    """Every ld+json block on an article must stay valid JSON.

    Summaries come from stripped article HTML, so they carry newlines;
    titles carry quotes. Interpolating either into a JSON string literal
    used to emit `Invalid control character` (BlogPosting) or mangled
    HTML entities. The template now serializes a dict with tojson.
    """
    ctx = {
        "page_title": f"Title {text}",
        "page_description": f"Desc {text}",
        "page_image": "https://example.com/og.jpg",
        "page_url": "https://example.com/blog/x",
        "page_type": "article",
        "article_date": "2026-01-01",
        "article_modified": "",
    }
    with app.test_request_context("/blog/x"):
        meta = render_template("seo_meta.html", **ctx)
    blocks = LD_JSON_RE.findall(meta)
    assert len(blocks) == 2  # BlogPosting + BreadcrumbList
    for raw in blocks:
        json.loads(raw)  # must not raise
    posting = json.loads(blocks[0])
    assert posting["@type"] == "BlogPosting"
    assert posting["headline"] == ctx["page_title"]
    assert posting["description"] == ctx["page_description"]
    crumb = json.loads(blocks[1])
    assert crumb["itemListElement"][2]["name"] == ctx["page_title"]


def test_person_schema_itemlist_parses_with_adversarial_project(app):
    """Project fields are user input; the ItemList block must survive them."""
    project = MagicMock()
    project.title = 'P "quoted"\nnewline'
    project.description = 'D1\nD2 "q" </script>'
    project.github_link = "https://github.com/x/y"
    project.live_demo_link = ""
    project.technologies = ["Python", 'A"B']
    with app.test_request_context("/"):
        html = render_template("person_schema.html", projects=[project])
    blocks = LD_JSON_RE.findall(html)
    assert blocks, "expected at least the ItemList block"
    for raw in blocks:
        json.loads(raw)  # must not raise


def test_get_first_image_rejects_inline_uris():
    """data: and blob: sources are not crawler-addressable; fall back."""
    assert (
        Article("t", '<img src="data:image/png;base64,AAA">', None).get_first_image()
        is None
    )
    assert (
        Article("t", '<img src="blob:https://x/uuid">', None).get_first_image() is None
    )
    assert (
        Article("t", '<img src="/media/img/abc">', None).get_first_image()
        == "https://ollayor.uz/media/img/abc"
    )
    assert (
        Article("t", '<img src="https://cdn/x.png">', None).get_first_image()
        == "https://cdn/x.png"
    )


def test_public_responses_are_edge_cacheable(client):
    """No session touch on public routes: Vary must be absent, CC public."""
    for path in ["/", "/about", "/blog"]:
        resp = client.get(path)
        assert resp.status_code == 200, path
        assert resp.headers.get("Vary") is None, path
        assert "s-maxage" in (resp.headers.get("Cache-Control") or ""), path


def test_login_keeps_session_vary(client):
    """The session-dependent route must keep varying on Cookie."""
    resp = client.get("/login")
    assert resp.status_code == 200
    assert resp.headers.get("Vary") == "Cookie"


def test_article_page_json_ld_and_fallback_image(app, client, monkeypatch):
    """Full article page: ld+json parses, data: image falls back, no Vary."""
    nasty = Article(
        'A "quoted"\ntitle',
        "<p>first\nsecond</p>" + '<img src="data:image/png;base64,AAAA">',
        datetime(2026, 1, 2),
        True,
        "nasty",
    )
    monkeypatch.setattr(Article, "get_by_slug", lambda slug: nasty)
    monkeypatch.setattr(Article, "get_view_count", lambda slug: 0)
    resp = client.get("/blog/nasty")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    blocks = LD_JSON_RE.findall(html)
    assert blocks, "expected BlogPosting + BreadcrumbList blocks"
    for raw in blocks:
        json.loads(raw)  # must not raise
    assert "myself-social-optimized.jpg" in html
    assert resp.headers.get("Vary") is None


def test_authenticated_header_still_resolves_user(auth_client):
    """The lazy current_user proxy must resolve for logged-in admins."""
    resp = auth_client.get("/for-llms")
    assert resp.status_code == 200
    assert b"Admin" in resp.data
