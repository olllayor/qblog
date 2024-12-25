import os
from slugify import slugify
from datetime import datetime
import psycopg2
from database import connect_db
import logging

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

    @staticmethod
    def save_article(article):
        conn = connect_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return

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
        except psycopg2.Error as e:
            logger.error(f"Error saving article: {e}")
        finally:
            if conn:
                conn.close()

    @staticmethod
    def update_article(article):
        conn = connect_db()
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
            if conn:
                conn.close()

    @staticmethod
    def get_all_articles():
        conn = connect_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return []

        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM articles")
            articles = cur.fetchall()
        except psycopg2.Error as e:
            logger.error(f"Error fetching all articles: {e}")
            articles = []
        finally:
            if conn:
                conn.close()

        article_objects = [
            Article(row[1], row[2], row[3], row[4], row[5]) for row in articles
        ]
        sorted_articles = sorted(
            article_objects, key=lambda a: a.date_published, reverse=True
        )
        return sorted_articles

    @staticmethod
    def delete_article_by_slug(slug):
        conn = connect_db()
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
            if conn:
                conn.close()

    @classmethod
    def get_by_slug(cls, slug):
        conn = connect_db()
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
            if conn:
                conn.close()

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
