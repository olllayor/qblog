"""Unit tests for Frontend & Core Web Vitals optimizations."""

from pathlib import Path

from app import app, get_static_version, lazy_content_images, versioned_static
from icons import render_icon

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def test_theme_universal_transition():
    """Verify universal transition has been scoped to body to avoid INP latency."""
    theme_file = TEMPLATES_DIR / "_theme.html"
    content = theme_file.read_text(encoding="utf-8")
    assert "body, body *" not in content
    assert "transition: background-color 0.2s ease, color 0.2s ease;" in content


def test_font_awesome_cdn_eliminated():
    """Verify font-awesome stylesheet CDN has been eliminated from all templates."""
    for html_file in TEMPLATES_DIR.glob("**/*.html"):
        content = html_file.read_text(encoding="utf-8")
        assert "cdnjs.cloudflare.com/ajax/libs/font-awesome" not in content, (
            f"Found Font Awesome CDN link in {html_file.name}"
        )
        assert '<i class="fas ' not in content, (
            f'Found <i class="fas in {html_file.name}'
        )
        assert '<i class="fab ' not in content, (
            f'Found <i class="fab in {html_file.name}'
        )


def test_external_google_fonts_eliminated():
    """Verify Google Fonts external links are eliminated across all templates."""
    for html_file in TEMPLATES_DIR.glob("**/*.html"):
        content = html_file.read_text(encoding="utf-8")
        assert "fonts.googleapis.com" not in content, (
            f"Found fonts.googleapis.com in {html_file.name}"
        )
        assert "fonts.gstatic.com" not in content, (
            f"Found fonts.gstatic.com in {html_file.name}"
        )


def test_self_hosted_fonts_exist():
    """Verify self-hosted JetBrains Mono woff2 fonts exist."""
    font_400 = STATIC_DIR / "fonts" / "jetbrains-mono-400.woff2"
    font_700 = STATIC_DIR / "fonts" / "jetbrains-mono-700.woff2"
    assert font_400.exists() and font_400.stat().st_size > 0
    assert font_700.exists() and font_700.stat().st_size > 0


def test_font_face_font_display_swap():
    """Verify @font-face includes font-display: swap."""
    css_file = STATIC_DIR / "tailwind.css"
    content = css_file.read_text(encoding="utf-8")
    assert "font-display:swap" in content or "font-display: swap" in content
    assert "JetBrains Mono" in content


def test_static_cache_busting():
    """Verify versioned_static appends MD5 hash query parameter."""
    with app.test_request_context():
        # Valid file
        v_url = versioned_static("favicon.ico")
        assert "?v=" in v_url
        assert len(v_url.split("?v=")[1]) == 8
        version_hash = get_static_version("favicon.ico")
        assert version_hash != ""
        assert len(version_hash) == 8

        # Non-existent file gracefully returns static path without hash
        v_url_missing = versioned_static("nonexistent_file.png")
        assert "/static/nonexistent_file.png" in v_url_missing
        assert "?v=" not in v_url_missing


def test_lazy_content_images_cls_fix():
    """Verify lazy_content_images enforces aspect-ratio style on content images without dimensions."""
    # First image is eager for LCP optimization, subsequent images are lazy
    html_content = '<p><img src="/static/img1.png" alt="First"><img src="/static/img2.png" alt="Second"></p>'
    processed = lazy_content_images(html_content)
    assert 'loading="eager"' in processed
    assert 'loading="lazy"' in processed
    assert 'decoding="async"' in processed
    assert "aspect-ratio" in processed

    # Images with existing dimensions keep their dimensions
    html_with_dim = (
        '<p><img src="/static/img.png" width="800" height="450" alt="Test"></p>'
    )
    processed_with_dim = lazy_content_images(html_with_dim)
    assert 'width="800"' in processed_with_dim
    assert 'height="450"' in processed_with_dim


def test_render_icon_helper():
    """Verify render_icon generates valid SVG markup and handles aliases."""
    svg_gh = render_icon("github", "w-5 h-5")
    assert "<svg" in svg_gh
    assert 'class="w-5 h-5"' in svg_gh
    assert 'aria-hidden="true"' in svg_gh

    # Font Awesome alias lookup
    svg_alias = render_icon("fab fa-twitter", "w-4 h-4")
    assert "<svg" in svg_alias
    assert 'class="w-4 h-4"' in svg_alias

    # Unknown icon returns empty
    svg_none = render_icon("unknown-xyz")
    assert svg_none == ""
