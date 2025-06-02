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
