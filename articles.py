import os
from slugify import slugify
from datetime import datetime
import psycopg2
from database import connect_db
import logging

logger = logging.getLogger(__name__)

class Article:
    def __init__(self, title, content, date_published, is_published=False):
        self.title = title
        self.content = content
        self.date_published = date_published
        self.is_published = is_published

    @staticmethod
    def save_article(article):
        conn = connect_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO articles (title, content, date_published, is_published, slug)
                    VALUES (%s, %s, %s, %s, %s)""",
                    (
                        article.title,
                        article.content,
                        article.date_published,
                        article.is_published,
                        slugify(article.title),
                    ),
                )
            conn.commit()
        except psycopg2.Error as e:
            logger.error(f"Error saving article: {e}")
        finally:
            conn.close()

    @staticmethod
    def get_all_articles():
        conn = connect_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return []

        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM articles")
                articles = cur.fetchall()
        except psycopg2.Error as e:
            logger.error(f"Error fetching all articles: {e}")
            articles = []
        finally:
            conn.close()

        article_objects = [
            Article(
                row[1], 
                row[2], 
                row[3], 
                row[4]
            ) for row in articles
        ]
        sorted_articles = sorted(article_objects, key=lambda a: a.date_published, reverse=True)
        return sorted_articles
    @staticmethod
    def delete_article_by_slug(slug):
        conn = connect_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return False

        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM articles WHERE slug = %s", (slug,))
            conn.commit()
            return True
        except psycopg2.Error as e:
            logger.error(f"Error deleting article: {e}")
            return False
        finally:
            conn.close()

    @property
    def slug(self):
        return slugify(self.title)

    def load_content(self):
        file_path = f"articles/{self.title}"
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                self.date_published = datetime.strptime(lines[1].strip(), '%d %B, %Y')
                self.content = ''.join(lines[2:])
        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")

    @classmethod
    def all(cls):
        titles = os.listdir('articles')
        slug_articles = {}
        for title in titles:
            slug = slugify(title)
            article = Article(title, "", "")
            article.load_content()
            slug_articles[slug] = article
        return slug_articles

    @classmethod
    def get_by_slug(cls, slug):
        conn = connect_db()
        if conn is None:
            return None

        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM articles WHERE slug = %s", (slug,))
                article_data = cur.fetchone()
        except psycopg2.Error as e:
            logger.error(f"Error fetching article by slug: {e}")
            return None
        finally:
            conn.close()

        if article_data:
            return cls(article_data[1], article_data[2], article_data[3], article_data[4])
        else:
            return None