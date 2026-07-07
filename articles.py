import logging
import re
from datetime import datetime

import psycopg2
from slugify import slugify

from database import get_db

logger = logging.getLogger(__name__)


def _classify_device(user_agent):
    """Rough device class from a User-Agent string (no external dependency)."""
    ua = (user_agent or "").lower()
    if not ua:
        return "Desktop"
    if any(b in ua for b in ("bot", "crawler", "spider", "slurp", "bingpreview")):
        return "Bot"
    if "ipad" in ua or ("android" in ua and "mobile" not in ua) or "tablet" in ua:
        return "Tablet"
    if any(m in ua for m in ("mobi", "iphone", "ipod", "android", "phone")):
        return "Mobile"
    return "Desktop"


class Article:
    def __init__(self, title, content, date_published, is_published=False, slug=None):
        self.title = title
        self.content = content
        if isinstance(date_published, str):
            self.date_published = datetime.fromisoformat(date_published)
        else:
            self.date_published = date_published
        self.is_published = is_published
        self.slug = slug or slugify(title)

    def get_reading_time(self):
        """Calculate estimated reading time based on word count"""
        # Remove HTML tags and count words
        clean_text = re.sub(r"<[^>]+>", "", self.content)
        word_count = len(clean_text.split())

        # Average reading speed is 200-250 words per minute
        # We'll use 225 as a middle ground
        reading_time = max(1, round(word_count / 225))
        return reading_time

    def get_word_count(self):
        """Get word count for the article"""
        clean_text = re.sub(r"<[^>]+>", "", self.content)
        return len(clean_text.split())

    def get_summary(self, length=160):
        """Get a summary of the article for meta descriptions"""
        clean_text = re.sub(r"<[^>]+>", "", self.content)
        if len(clean_text) <= length:
            return clean_text
        return clean_text[:length].rsplit(" ", 1)[0] + "..."

    def get_first_image(self, base_url="https://ollayor.uz"):
        """Extract the first image from article content for social media sharing"""
        if not self.content:
            return None

        # Look for img tags in the content
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
        matches = re.findall(img_pattern, self.content, re.IGNORECASE)

        if matches:
            img_src = matches[0]
            # Convert relative URLs to absolute URLs
            if img_src.startswith("/"):
                return f"{base_url}{img_src}"
            elif img_src.startswith("http"):
                return img_src
            else:
                # Relative path without leading slash
                return f"{base_url}/{img_src}"

        return None

    @staticmethod
    def track_view(slug, ip_address, user_agent=None, referrer_host=None):
        """Track a view for an article with duplicate prevention"""
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return False

        try:
            cur = conn.cursor()
            # Dedupe per visitor per day so daily/monthly aggregates stay meaningful
            # while page refreshes on the same day are not double-counted. Keep the
            # referrer from the first visit of the day (DO NOTHING on conflict).
            cur.execute(
                """
                INSERT INTO article_views
                    (article_slug, ip_address, user_agent, referrer_host, view_date)
                VALUES (%s, %s, %s, %s, CURRENT_DATE)
                ON CONFLICT (article_slug, ip_address, view_date) DO NOTHING
            """,
                (slug, ip_address, user_agent, referrer_host),
            )
            conn.commit()
            return True
        except psycopg2.Error as e:
            logger.error(f"Error tracking article view: {e}")
            return False

    @staticmethod
    def get_view_count(slug):
        """Get the total view count for an article"""
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return 0

        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM article_views WHERE article_slug = %s", (slug,)
            )
            result = cur.fetchone()
            return result[0] if result else 0
        except psycopg2.Error as e:
            logger.error(f"Error getting view count: {e}")
            return 0
        finally:
            pass

    @staticmethod
    def get_view_totals():
        """Return aggregate view counts for the current day, month, and all-time across all articles."""
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return {"daily": 0, "monthly": 0, "all_time": 0}

        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE viewed_at >= DATE_TRUNC('day', CURRENT_TIMESTAMP)) AS daily_views,
                    COUNT(*) FILTER (WHERE viewed_at >= DATE_TRUNC('month', CURRENT_TIMESTAMP)) AS monthly_views,
                    COUNT(*) AS total_views
                FROM article_views
                """
            )
            result = cur.fetchone()
            if not result:
                return {"daily": 0, "monthly": 0, "all_time": 0}
            daily, monthly, total = result
            return {
                "daily": daily or 0,
                "monthly": monthly or 0,
                "all_time": total or 0,
            }
        except psycopg2.Error as e:
            logger.error(f"Error getting view totals: {e}")
            return {"daily": 0, "monthly": 0, "all_time": 0}
        finally:
            pass

    @staticmethod
    def save_article(article):
        conn = get_db()  # Use get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return False  # Indicate failure

        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO articles (title, content, date_published, is_published, slug)
                VALUES (%s, %s, %s, %s, %s)""",
                (
                    article.title,
                    article.content,
                    article.date_published.isoformat(),
                    article.is_published,
                    article.slug,
                ),
            )
            conn.commit()
            logger.info("Article saved successfully.")
            return True  # Indicate success
        except psycopg2.Error as e:
            logger.error(f"Error saving article: {e}")
            return False  # Indicate failure
        finally:
            # Connection is now managed by app context, no close here
            pass

    @staticmethod
    def update_article(article):
        conn = get_db()  # Use get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                """UPDATE articles SET title = %s, content = %s, date_published = %s, is_published = %s
                    WHERE slug = %s""",
                (
                    article.title,
                    article.content,
                    article.date_published.isoformat(),
                    article.is_published,
                    article.slug,
                ),
            )
            conn.commit()
            return True
        except psycopg2.Error as e:
            logger.error(f"Error updating article: {e}")
            return False
        finally:
            # Connection is now managed by app context, no close here
            pass

    @staticmethod
    def get_all_articles():
        conn = get_db()  # Use get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return []

        try:
            cur = conn.cursor()
            # Sort by date_published in descending order directly in the query
            cur.execute("SELECT * FROM articles ORDER BY date_published DESC")
            articles_data = cur.fetchall()
        except psycopg2.Error as e:
            logger.error(f"Error fetching all articles: {e}")
            articles_data = []
        finally:
            # Connection is now managed by app context, no close here
            pass

        article_objects = [
            Article(row[1], row[2], row[3], row[4], row[5]) for row in articles_data
        ]
        # The sorting is now done by the database, so the Python sort is removed.
        return article_objects

    @staticmethod
    def get_views_by_day(days=30):
        """Daily unique-view counts for the last `days` days, zero-filled."""
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return []

        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT d.day::date, COALESCE(v.views, 0)
                FROM generate_series(
                    CURRENT_DATE - (%s - 1) * INTERVAL '1 day',
                    CURRENT_DATE,
                    INTERVAL '1 day'
                ) AS d(day)
                LEFT JOIN (
                    SELECT view_date, COUNT(*) AS views
                    FROM article_views
                    WHERE view_date >= CURRENT_DATE - (%s - 1) * INTERVAL '1 day'
                    GROUP BY view_date
                ) v ON v.view_date = d.day::date
                ORDER BY d.day
                """,
                (days, days),
            )
            return [{"date": row[0], "views": row[1]} for row in cur.fetchall()]
        except psycopg2.Error as e:
            logger.error(f"Error fetching views by day: {e}")
            return []

    @staticmethod
    def get_top_articles_by_views(limit=5):
        """Most-viewed articles: title, slug, total views, views this month."""
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return []

        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT a.title, a.slug, COUNT(v.id) AS total_views,
                       COUNT(v.id) FILTER (
                           WHERE v.viewed_at >= DATE_TRUNC('month', CURRENT_TIMESTAMP)
                       ) AS monthly_views
                FROM articles a
                JOIN article_views v ON v.article_slug = a.slug
                GROUP BY a.title, a.slug
                ORDER BY total_views DESC
                LIMIT %s
                """,
                (limit,),
            )
            return [
                {
                    "title": row[0],
                    "slug": row[1],
                    "total_views": row[2],
                    "monthly_views": row[3],
                }
                for row in cur.fetchall()
            ]
        except psycopg2.Error as e:
            logger.error(f"Error fetching top articles: {e}")
            return []

    @staticmethod
    def get_device_breakdown(days=30):
        """Count views by device class over the last `days`, using user_agent."""
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return []

        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT user_agent
                FROM article_views
                WHERE viewed_at >= CURRENT_DATE - (%s - 1) * INTERVAL '1 day'
                """,
                (days,),
            )
            counts = {"Mobile": 0, "Tablet": 0, "Desktop": 0, "Bot": 0}
            for (ua,) in cur.fetchall():
                counts[_classify_device(ua)] += 1
            return [
                {"label": k, "count": v} for k, v in counts.items() if v or k != "Bot"
            ]
        except psycopg2.Error as e:
            logger.error(f"Error fetching device breakdown: {e}")
            return []

    @staticmethod
    def get_top_referrers(days=30, limit=8):
        """Top referrer hosts over the last `days`; NULL rolls up to 'Direct'."""
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return []

        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT COALESCE(NULLIF(referrer_host, ''), 'Direct') AS host,
                       COUNT(*) AS views
                FROM article_views
                WHERE viewed_at >= CURRENT_DATE - (%s - 1) * INTERVAL '1 day'
                GROUP BY host
                ORDER BY views DESC
                LIMIT %s
                """,
                (days, limit),
            )
            return [{"host": row[0], "views": row[1]} for row in cur.fetchall()]
        except psycopg2.Error as e:
            logger.error(f"Error fetching top referrers: {e}")
            return []

    @staticmethod
    def get_articles_admin(status="all", query=None):
        """List articles for the admin panel with view counts.

        status: 'all' | 'published' | 'draft'. query: case-insensitive title match.
        Returns dicts (metadata only, no content).
        """
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return []

        where = []
        params = []
        if status == "published":
            where.append("a.is_published = TRUE")
        elif status == "draft":
            where.append("a.is_published = FALSE")
        if query:
            where.append("a.title ILIKE %s")
            params.append(f"%{query}%")
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        try:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT a.title, a.slug, a.is_published, a.date_published,
                       COUNT(v.id) AS views
                FROM articles a
                LEFT JOIN article_views v ON v.article_slug = a.slug
                {where_sql}
                GROUP BY a.id, a.title, a.slug, a.is_published, a.date_published
                ORDER BY a.date_published DESC
                """,  # noqa: S608 — where_sql built from a fixed whitelist, values bound
                params,
            )
            return [
                {
                    "title": row[0],
                    "slug": row[1],
                    "is_published": row[2],
                    "date_published": row[3],
                    "views": row[4],
                }
                for row in cur.fetchall()
            ]
        except psycopg2.Error as e:
            logger.error(f"Error fetching admin article list: {e}")
            return []

    @staticmethod
    def get_article_counts():
        """Return (total, published) article counts without loading content."""
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return 0, 0

        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*), COUNT(*) FILTER (WHERE is_published) FROM articles"
            )
            row = cur.fetchone()
            return (row[0], row[1]) if row else (0, 0)
        except psycopg2.Error as e:
            logger.error(f"Error counting articles: {e}")
            return 0, 0

    @staticmethod
    def get_recent_articles(limit=5):
        """Return the most recent articles with metadata only (no content)."""
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return []

        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT title, date_published, is_published, slug
                FROM articles
                ORDER BY date_published DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
            return [Article(r[0], "", r[1], r[2], r[3]) for r in rows]
        except psycopg2.Error as e:
            logger.error(f"Error fetching recent articles: {e}")
            return []

    @staticmethod
    def get_published_articles():
        """Get only published articles"""
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return []

        try:
            cur = conn.cursor()
            # Only fetch published articles, sorted by date_published in descending order
            cur.execute(
                "SELECT * FROM articles WHERE is_published = TRUE ORDER BY date_published DESC"
            )
            articles_data = cur.fetchall()
        except psycopg2.Error as e:
            logger.error(f"Error fetching published articles: {e}")
            articles_data = []
        finally:
            pass

        article_objects = [
            Article(row[1], row[2], row[3], row[4], row[5]) for row in articles_data
        ]
        return article_objects

    @staticmethod
    def get_published_articles_paginated(page=1, per_page=6):
        """Fetch published articles with pagination support."""
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 1

        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return [], 0

        offset = (page - 1) * per_page

        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM articles WHERE is_published = TRUE")
            total_result = cur.fetchone()
            total = total_result[0] if total_result else 0

            cur.execute(
                """
                SELECT *
                FROM articles
                WHERE is_published = TRUE
                ORDER BY date_published DESC
                LIMIT %s OFFSET %s
                """,
                (per_page, offset),
            )
            articles_data = cur.fetchall()
        except psycopg2.Error as e:
            logger.error(f"Error fetching paginated published articles: {e}")
            return [], 0
        finally:
            pass

        article_objects = [
            Article(row[1], row[2], row[3], row[4], row[5]) for row in articles_data
        ]
        return article_objects, total

    @staticmethod
    def get_published_articles_by_slugs(slugs):
        """Fetch published articles for a list of slugs preserving the input order."""
        if not slugs:
            return []

        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return []

        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT title, content, date_published, is_published, slug
                FROM articles
                WHERE is_published = TRUE AND slug = ANY(%s)
                """,
                (slugs,),
            )
            rows = cur.fetchall()
        except psycopg2.Error as e:
            logger.error(f"Error fetching published articles by slugs: {e}")
            return []
        finally:
            pass

        by_slug = {
            row[4]: Article(row[0], row[1], row[2], row[3], row[4]) for row in rows
        }
        ordered = [by_slug[slug] for slug in slugs if slug in by_slug]
        return ordered

    @staticmethod
    def delete_article_by_slug(slug):
        conn = get_db()  # Use get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return False

        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM articles WHERE slug = %s", (slug,))
            conn.commit()
            return True
        except psycopg2.Error as e:
            logger.error(f"Error deleting article: {e}")
            return False
        finally:
            # Connection is now managed by app context, no close here
            pass

    @classmethod
    def get_by_slug(cls, slug):
        conn = get_db()  # Use get_db()
        if conn is None:
            return None

        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM articles WHERE slug = %s", (slug,))
            article_data = cur.fetchone()
        except psycopg2.Error as e:
            logger.error(f"Error fetching article by slug: {e}")
            return None
        finally:
            # Connection is now managed by app context, no close here
            pass

        if article_data:
            return cls(
                article_data[1],
                article_data[2],
                article_data[3],
                article_data[4],
                article_data[5],
            )
        else:
            return None
