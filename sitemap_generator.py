from datetime import datetime

from flask import request

BASE_URL = "https://ollayor.uz"


def generate_sitemap(app, articles=None, projects=None):
    """Generate sitemap XML content"""
    try:
        base = request.host_url.rstrip("/")
    except RuntimeError:
        base = BASE_URL

    pages = [
        {
            "url": f"{base}/",
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "changefreq": "weekly",
            "priority": "1.0",
        },
        {
            "url": f"{base}/about",
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "changefreq": "monthly",
            "priority": "0.9",
        },
        {
            "url": f"{base}/blog",
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "changefreq": "daily",
            "priority": "0.9",
        },
        {
            "url": f"{base}/projects",
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "changefreq": "weekly",
            "priority": "0.8",
        },
        {
            "url": f"{base}/talks",
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "changefreq": "monthly",
            "priority": "0.6",
        },
    ]

    if articles:
        for article in articles:
            if article.is_published:
                pages.append(
                    {
                        "url": f"{base}/blog/{article.slug}",
                        "lastmod": article.date_updated.strftime("%Y-%m-%d")
                        if article.date_updated
                        else article.date_published.strftime("%Y-%m-%d"),
                        "changefreq": "monthly",
                        "priority": "0.7",
                    }
                )

    return pages


def generate_image_sitemap(app, articles=None):
    """Generate image sitemap for better image SEO"""
    try:
        base = request.host_url.rstrip("/")
    except RuntimeError:
        base = BASE_URL

    images = [
        {
            "loc": f"{base}/static/me.webp",
            "title": "Ollayor Maxammadnabiyev - Software Engineer",
            "caption": "Portrait of Ollayor Maxammadnabiyev, Software Engineer",
        },
        {
            "loc": f"{base}/static/myself-social-optimized.jpg",
            "title": "Ollayor Maxammadnabiyev - Social Media Image",
            "caption": "Professional portrait for social media sharing",
        },
    ]

    if articles:
        for article in articles:
            if article.is_published:
                first_image = article.get_first_image("")
                if first_image:
                    if not first_image.startswith("http"):
                        first_image = f"{base}/static/{first_image.lstrip('/')}"

                    images.append(
                        {
                            "loc": first_image,
                            "title": article.title,
                            "caption": article.get_summary(160),
                            "page_url": f"{base}/blog/{article.slug}",
                        }
                    )

    return images
