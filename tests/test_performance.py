"""Unit tests for Frontend & Core Web Vitals optimizations."""

import re
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
    assert "prefers-reduced-motion" in content


def test_font_awesome_cdn_eliminated():
    """Verify font-awesome stylesheet CDN and icon elements are eliminated across all templates."""
    fa_icon_pattern = re.compile(
        r"<i\s+class=[\"\'](?:fa|fas|fab|far|fa-solid|fa-brands)\b"
    )
    for html_file in TEMPLATES_DIR.glob("**/*.html"):
        content = html_file.read_text(encoding="utf-8")
        assert "cdnjs.cloudflare.com/ajax/libs/font-awesome" not in content, (
            f"Found Font Awesome CDN link in {html_file.name}"
        )
        assert not fa_icon_pattern.search(content), (
            f"Found Font Awesome <i> tag in {html_file.name}"
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
    """Verify self-hosted JetBrains Mono woff2 fonts exist and no duplicate variants are present."""
    font_400 = STATIC_DIR / "fonts" / "jetbrains-mono-400.woff2"
    font_700 = STATIC_DIR / "fonts" / "jetbrains-mono-700.woff2"
    assert font_400.exists() and font_400.stat().st_size > 0
    assert font_700.exists() and font_700.stat().st_size > 0

    # Ensure duplicate unreferenced fonts were deleted
    assert not (STATIC_DIR / "fonts" / "jetbrains-mono-v24-latin-400.woff2").exists()
    assert not (STATIC_DIR / "fonts" / "jetbrains-mono-v24-latin-700.woff2").exists()


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
    """Verify lazy_content_images enforces aspect-ratio style and proper loading priority."""
    # First image is eager with high fetchpriority; second is lazy
    html_content = '<p><img src="/static/img1.png" alt="First"><img src="/static/img2.png" alt="Second"></p>'
    processed = lazy_content_images(html_content)

    img1_match = re.search(r'<img[^>]*alt="First"[^>]*>', processed)
    img2_match = re.search(r'<img[^>]*alt="Second"[^>]*>', processed)
    assert img1_match is not None
    assert img2_match is not None

    img1_tag = img1_match.group(0)
    img2_tag = img2_match.group(0)

    assert 'loading="eager"' in img1_tag
    assert 'fetchpriority="high"' in img1_tag
    assert 'decoding="async"' in img1_tag
    assert "aspect-ratio" in img1_tag

    assert 'loading="lazy"' in img2_tag
    assert "fetchpriority" not in img2_tag
    assert 'decoding="async"' in img2_tag
    assert "aspect-ratio" in img2_tag

    # Images with existing dimensions keep their dimensions
    html_with_dim = (
        '<p><img src="/static/img.png" width="800" height="450" alt="Test"></p>'
    )
    processed_with_dim = lazy_content_images(html_with_dim)
    assert 'width="800"' in processed_with_dim
    assert 'height="450"' in processed_with_dim

    # Single-quoted style attribute preserves single quotes
    html_single_quote = '<p><img src="/static/img3.png" style=\'border: 1px solid black;\' alt="Test"></p>'
    processed_single_quote = lazy_content_images(html_single_quote)
    assert (
        "style='border: 1px solid black; aspect-ratio: 16 / 9;'"
        in processed_single_quote
    )


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

    # Times and x aliases
    svg_times = render_icon("times", "w-4 h-4")
    svg_x = render_icon("x", "w-4 h-4")
    assert "<svg" in svg_times
    assert svg_times == svg_x

    # Unknown icon returns empty
    svg_none = render_icon("unknown-xyz")
    assert svg_none == ""
