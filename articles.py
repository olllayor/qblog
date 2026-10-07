import logging
import re
from datetime import datetime

import psycopg2
from slugify import slugify

from database import commit_db, get_db, rollback_db

logger = logging.getLogger(__name__)

_RE_TAGS = re.compile(r"<[^>]+>")
_RE_IMG = re.compile(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)


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
        self._reading_time = None
        self._word_count = None
        self._summaries = {}

    def get_reading_time(self):
        """Calculate estimated reading time based on word count."""
        if self._reading_time is not None:
            return self._reading_time
        clean_text = _RE_TAGS.sub("", self.content or "")
        word_count = len(clean_text.split())
        self._reading_time = max(1, round(word_count / 225))
        return self._reading_time

    def get_word_count(self):
        """Get word count for the article."""
        if self._word_count is not None:
            return self._word_count
        clean_text = _RE_TAGS.sub("", self.content or "")
        self._word_count = len(clean_text.split())
        return self._word_count

    def get_summary(self, length=160):
        """Get a summary of the article for meta descriptions."""
        if length in self._summaries:
            return self._summaries[length]
        clean_text = _RE_TAGS.sub("", self.content or "")
        if len(clean_text) <= length:
            summary = clean_text
        else:
            summary = clean_text[:length].rsplit(" ", 1)[0] + "..."
        self._summaries[length] = summary
        return summary

    def get_first_image(self, base_url="https://ollayor.uz"):
        """Extract the first image from article content for social media sharing."""
        if not self.content:
            return None

        matches = _RE_IMG.findall(self.content)
        if matches:
            img_src = matches[0]
            if img_src.startswith(("data:", "blob:")):
                return None  # inline/blob URIs are not addressable by crawlers
            if img_src.startswith("/"):
                return f"{base_url}{img_src}"
            elif img_src.startswith("http"):
                return img_src
            else:
                return f"{base_url}/{img_src}"

        return None

    @staticmethod
    def track_view(slug, ip_address, user_agent=None, referrer_host=None):
        """Track a view for an article with duplicate prevention."""
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return False

        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO article_views
                    (article_slug, ip_address, user_agent, referrer_host, view_date)
                VALUES (%s, %s, %s, %s, CURRENT_DATE)
                ON CONFLICT (article_slug, ip_address, view_date) DO NOTHING
            """,
                (slug, ip_address, user_agent, referrer_host),
            )
            commit_db(conn)
            return True
        except psycopg2.Error as e:
            logger.error(f"Error tracking article view: {e}")
            rollback_db(conn)
            return False

    @staticmethod
    def get_view_count(slug):
        """Get the total view count for an article."""
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
            logger.error(f"Error getting view count for article {slug}: {e}")
            return 0

    @staticmethod
    def get_view_totals():
        """Get view totals: today, last 30 days, and all-time."""
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return {"daily": 0, "monthly": 0, "all_time": 0}

        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE view_date = CURRENT_DATE) as daily,
                    COUNT(*) FILTER (WHERE view_date >= CURRENT_DATE - INTERVAL '30 days') as monthly,
                    COUNT(*) as all_time
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

    @staticmethod
    def save_article(article):
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return False

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
            commit_db(conn)
            logger.info("Article saved successfully.")
            return True
        except psycopg2.Error as e:
            logger.error(f"Error saving article: {e}")
            rollback_db(conn)
            return False

    @staticmethod
    def update_article(article):
        conn = get_db()
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
            commit_db(conn)
            return True
        except psycopg2.Error as e:
            logger.error(f"Error updating article: {e}")
            rollback_db(conn)
            return False

    @staticmethod
    def get_all_articles():
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return []

        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT title, content, date_published, is_published, slug "
                "FROM articles ORDER BY date_published DESC"
            )
            articles_data = cur.fetchall()
        except psycopg2.Error as e:
            logger.error(f"Error fetching all articles: {e}")
            articles_data = []

        article_objects = [
            Article(row[0], row[1], row[2], row[3], row[4]) for row in articles_data
        ]
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
        """Count views by device class over the last `days`, using SQL aggregation."""
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return []

        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    CASE
                        WHEN user_agent ~* '(bot|crawler|spider|slurp|bingpreview)' THEN 'Bot'
                        WHEN user_agent ~* 'ipad' OR (user_agent ~* 'android' AND user_agent !~* 'mobile') OR user_agent ~* 'tablet' THEN 'Tablet'
                        WHEN user_agent ~* '(mobi|iphone|ipod|android|phone)' THEN 'Mobile'
                        ELSE 'Desktop'
                    END AS device_class,
                    COUNT(*) AS count
                FROM article_views
                WHERE viewed_at >= CURRENT_DATE - (%s - 1) * INTERVAL '1 day'
                GROUP BY 1
                """,
                (days,),
            )
            counts = {"Mobile": 0, "Tablet": 0, "Desktop": 0, "Bot": 0}
            for cls_name, cnt in cur.fetchall():
                if cls_name in counts:
                    counts[cls_name] = cnt
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
        """List articles for the admin panel with view counts."""
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
    def get_published_articles(limit=None):
        """Get only published articles, optionally limited."""
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return []

        try:
            cur = conn.cursor()
            query = (
                "SELECT title, content, date_published, is_published, slug "
                "FROM articles WHERE is_published = TRUE ORDER BY date_published DESC"
            )
            params = ()
            if limit is not None:
                query += " LIMIT %s"
                params = (limit,)
            cur.execute(query, params)
            articles_data = cur.fetchall()
        except psycopg2.Error as e:
            logger.error(f"Error fetching published articles: {e}")
            articles_data = []

        article_objects = [
            Article(row[0], row[1], row[2], row[3], row[4]) for row in articles_data
        ]
        return article_objects

    @staticmethod
    def get_published_articles_paginated(page=1, per_page=6):
        """Fetch published articles with pagination support in a single round trip."""
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
            cur.execute(
                """
                SELECT title, content, date_published, is_published, slug,
                       COUNT(*) OVER() AS total_count
                FROM articles
                WHERE is_published = TRUE
                ORDER BY date_published DESC
                LIMIT %s OFFSET %s
                """,
                (per_page, offset),
            )
            rows = cur.fetchall()
            if not rows:
                if offset > 0:
                    cur.execute(
                        "SELECT COUNT(*) FROM articles WHERE is_published = TRUE"
                    )
                    total_res = cur.fetchone()
                    total = total_res[0] if total_res else 0
                else:
                    total = 0
                return [], total

            total = rows[0][5]
            article_objects = [Article(r[0], r[1], r[2], r[3], r[4]) for r in rows]
            return article_objects, total
        except psycopg2.Error as e:
            logger.error(f"Error fetching paginated published articles: {e}")
            return [], 0

    @staticmethod
    def get_published_articles_by_slugs(slugs: list[str]) -> list:
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

        by_slug = {
            row[4]: Article(row[0], row[1], row[2], row[3], row[4]) for row in rows
        }
        ordered = [by_slug[slug] for slug in slugs if slug in by_slug]
        return ordered

    @staticmethod
    def delete_article_by_slug(slug):
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return False

        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM articles WHERE slug = %s", (slug,))
            commit_db(conn)
            return True
        except psycopg2.Error as e:
            logger.error(f"Error deleting article: {e}")
            rollback_db(conn)
            return False

    @classmethod
    def get_by_slug(cls, slug):
        conn = get_db()
        if conn is None:
            return None

        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT title, content, date_published, is_published, slug "
                "FROM articles WHERE slug = %s",
                (slug,),
            )
            row = cur.fetchone()
        except psycopg2.Error as e:
            logger.error(f"Error fetching article by slug: {e}")
            return None

        if row:
            return cls(
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
            )
        return None
