import logging
import re
from datetime import datetime

import psycopg2
from slugify import slugify

from database import get_db

logger = logging.getLogger(__name__)


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
    def track_view(slug, ip_address, user_agent=None):
        """Track a view for an article with duplicate prevention"""
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return False

        try:
            cur = conn.cursor()
            # Use INSERT ... ON CONFLICT DO NOTHING for PostgreSQL
            cur.execute(
                """
                INSERT INTO article_views (article_slug, ip_address, user_agent)
                VALUES (%s, %s, %s)
                ON CONFLICT (article_slug, ip_address) DO NOTHING
            """,
                (slug, ip_address, user_agent),
            )
            conn.commit()
            return True
        except psycopg2.Error as e:
            logger.error(f"Error tracking article view: {e}")
            return False
        finally:
            pass

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
        """Return aggregate view counts for the current day and month across all articles."""
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return {"daily": 0, "monthly": 0}

        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE viewed_at >= DATE_TRUNC('day', CURRENT_TIMESTAMP)) AS daily_views,
                    COUNT(*) FILTER (WHERE viewed_at >= DATE_TRUNC('month', CURRENT_TIMESTAMP)) AS monthly_views
                FROM article_views
                """
            )
            result = cur.fetchone()
            if not result:
                return {"daily": 0, "monthly": 0}
            daily, monthly = result
            return {"daily": daily or 0, "monthly": monthly or 0}
        except psycopg2.Error as e:
            logger.error(f"Error getting view totals: {e}")
            return {"daily": 0, "monthly": 0}
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
