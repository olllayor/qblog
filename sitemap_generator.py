from datetime import datetime

from flask import url_for


def generate_sitemap(app, articles=None, projects=None):
    """Generate sitemap XML content"""
    pages = [
        {
            "url": url_for("index", _external=True),
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "changefreq": "weekly",
            "priority": "1.0",
        },
        {
            "url": url_for("about", _external=True),
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "changefreq": "monthly",
            "priority": "0.9",
        },
        {
            "url": url_for("blog", _external=True),
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "changefreq": "daily",
            "priority": "0.9",
        },
        {
            "url": url_for("projects", _external=True),
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "changefreq": "weekly",
            "priority": "0.8",
        },
        {
            "url": url_for("talks", _external=True),
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
                        "url": url_for("article", slug=article.slug, _external=True),
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
    images = []

    static_images = [
        {
            "loc": url_for("static", filename="me.webp", _external=True),
            "title": "Ollayor Maxammadnabiyev - Software Engineer",
            "caption": "Portrait of Ollayor Maxammadnabiyev, Software Engineer",
        },
        {
            "loc": url_for(
                "static", filename="myself-social-optimized.jpg", _external=True
            ),
            "title": "Ollayor Maxammadnabiyev - Social Media Image",
            "caption": "Professional portrait for social media sharing",
        },
    ]

    images.extend(static_images)

    if articles:
        for article in articles:
            if article.is_published:
                first_image = article.get_first_image("")
                if first_image:
                    if not first_image.startswith("http"):
                        first_image = url_for(
                            "static", filename=first_image.lstrip("/"), _external=True
                        )

                    images.append(
                        {
                            "loc": first_image,
                            "title": article.title,
                            "caption": article.get_summary(160),
                            "page_url": url_for(
                                "article", slug=article.slug, _external=True
                            ),
                        }
                    )

    return images
