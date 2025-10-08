"""
SEO Helper Utilities
Provides helper functions for SEO optimization including image alt text validation
"""

import re


def validate_alt_text(alt_text: str) -> tuple[bool, list[str]]:
    """
    Validate image alt text for SEO best practices

    Returns:
        Tuple of (is_valid, list of issues)
    """
    issues = []

    if not alt_text or alt_text.strip() == "":
        issues.append("Alt text is empty - all images should have descriptive alt text")
        return False, issues

    alt_text = alt_text.strip()

    if len(alt_text) < 5:
        issues.append("Alt text is too short - should be at least 5 characters")

    if len(alt_text) > 125:
        issues.append("Alt text is too long - recommended maximum is 125 characters")

    if alt_text.lower() in ["image", "photo", "picture", "img", "graphic"]:
        issues.append(
            "Alt text is generic - should describe the specific image content"
        )

    if alt_text.lower().startswith(("image of", "picture of", "photo of")):
        issues.append("Avoid starting with 'image of' or 'picture of' - be direct")

    if not re.search(r"[a-zA-Z]", alt_text):
        issues.append("Alt text should contain descriptive words, not just symbols")

    return len(issues) == 0, issues


def suggest_alt_text(context: str, image_type: str = "general") -> str:
    """
    Suggest alt text based on context

    Args:
        context: The context where image appears (e.g., article title, section)
        image_type: Type of image (profile, screenshot, diagram, chart, etc.)

    Returns:
        Suggested alt text
    """
    templates = {
        "profile": "Portrait of {context}",
        "screenshot": "Screenshot showing {context}",
        "diagram": "Diagram illustrating {context}",
        "chart": "Chart displaying {context}",
        "code": "Code example for {context}",
        "logo": "{context} logo",
        "icon": "{context} icon",
        "general": "{context}",
    }

    template = templates.get(image_type, templates["general"])
    return template.format(context=context)


def extract_images_from_html(html_content: str) -> list[dict]:
    """
    Extract all images from HTML content with their attributes

    Returns:
        List of dicts with image info (src, alt, width, height, etc.)
    """
    img_pattern = r"<img[^>]*>"
    images = []

    for match in re.finditer(img_pattern, html_content, re.IGNORECASE):
        img_tag = match.group(0)

        src_match = re.search(r'src=["\']([^"\']+)["\']', img_tag, re.IGNORECASE)
        alt_match = re.search(r'alt=["\']([^"\']*)["\']', img_tag, re.IGNORECASE)
        width_match = re.search(r'width=["\']?(\d+)["\']?', img_tag, re.IGNORECASE)
        height_match = re.search(r'height=["\']?(\d+)["\']?', img_tag, re.IGNORECASE)
        loading_match = re.search(
            r'loading=["\']([^"\']+)["\']', img_tag, re.IGNORECASE
        )

        image_info = {
            "src": src_match.group(1) if src_match else None,
            "alt": alt_match.group(1) if alt_match else "",
            "width": width_match.group(1) if width_match else None,
            "height": height_match.group(1) if height_match else None,
            "loading": loading_match.group(1) if loading_match else None,
            "has_alt": bool(alt_match),
            "has_dimensions": bool(width_match and height_match),
            "has_lazy_loading": bool(loading_match),
        }

        images.append(image_info)

    return images


def get_seo_score(images: list[dict]) -> dict:
    """
    Calculate SEO score for images

    Returns:
        Dict with score and recommendations
    """
    if not images:
        return {"score": 100, "total_images": 0, "issues": [], "recommendations": []}

    total_images = len(images)
    issues = []
    recommendations = []

    images_with_alt = sum(1 for img in images if img["has_alt"] and img["alt"])
    images_with_dimensions = sum(1 for img in images if img["has_dimensions"])
    images_with_lazy = sum(1 for img in images if img["has_lazy_loading"])

    if images_with_alt < total_images:
        missing = total_images - images_with_alt
        issues.append(f"{missing} image(s) missing alt text")
        recommendations.append("Add descriptive alt text to all images")

    if images_with_dimensions < total_images:
        missing = total_images - images_with_dimensions
        issues.append(f"{missing} image(s) missing width/height attributes")
        recommendations.append(
            "Add width and height attributes to prevent layout shift"
        )

    if images_with_lazy < total_images - 1:
        recommendations.append(
            "Consider adding loading='lazy' to below-the-fold images"
        )

    alt_score = (images_with_alt / total_images) * 100
    dimension_score = (images_with_dimensions / total_images) * 100
    lazy_score = min(100, (images_with_lazy / max(1, total_images - 1)) * 100)

    overall_score = alt_score * 0.5 + dimension_score * 0.3 + lazy_score * 0.2

    return {
        "score": round(overall_score, 1),
        "total_images": total_images,
        "images_with_alt": images_with_alt,
        "images_with_dimensions": images_with_dimensions,
        "images_with_lazy_loading": images_with_lazy,
        "issues": issues,
        "recommendations": recommendations,
    }


def generate_og_image_meta(
    image_url: str,
    title: str,
    description: str = "",
    width: int = 1200,
    height: int = 630,
) -> dict:
    """
    Generate Open Graph meta tags for an image

    Returns:
        Dict with OG meta tag properties
    """
    return {
        "og:image": image_url,
        "og:image:width": str(width),
        "og:image:height": str(height),
        "og:image:alt": title,
        "og:image:type": "image/jpeg",
        "twitter:card": "summary_large_image",
        "twitter:image": image_url,
        "twitter:image:alt": title,
    }
