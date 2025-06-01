from datetime import datetime

from flask import url_for


def generate_sitemap(app, articles=None, projects=None):
    """Generate sitemap XML content"""

    with app.app_context():
        # Static pages
        pages = [
            {
                "url": url_for("index", _external=True),
                "lastmod": datetime.now().strftime("%Y-%m-%d"),
                "changefreq": "weekly",
                "priority": "1.0",
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

        # Add articles to sitemap
        if articles:
            for article in articles:
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
