import logging
import os
from urllib.parse import urlparse

import psycopg2
from flask import g  # Added import
from psycopg2.pool import SimpleConnectionPool

logger = logging.getLogger(__name__)


def _normalize_url(url: str | None) -> str | None:
    if not url:
        return url
    # psycopg2 accepts both, but normalize for consistency
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def get_database_url() -> tuple[str | None, str | None]:
    """Resolve a usable Postgres URL and indicate its source key.

    Priority:
    - DATABASE_URL
    - DATABASE_URL_UNPOOLED
    - POSTGRES_URL
    - POSTGRES_URL_NON_POOLING
    - Compose from PG*/POSTGRES* parts
    """
    candidates = [
        ("DATABASE_URL", os.getenv("DATABASE_URL")),
        ("DATABASE_URL_UNPOOLED", os.getenv("DATABASE_URL_UNPOOLED")),
        ("POSTGRES_URL", os.getenv("POSTGRES_URL")),
        ("POSTGRES_URL_NON_POOLING", os.getenv("POSTGRES_URL_NON_POOLING")),
    ]
    for source, url in candidates:
        if url:
            return _normalize_url(url), source

    # Compose from parts
    pg_host = os.getenv("PGHOST") or os.getenv("POSTGRES_HOST")
    pg_user = os.getenv("PGUSER") or os.getenv("POSTGRES_USER")
    pg_pass = os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD")
    pg_db = os.getenv("PGDATABASE") or os.getenv("POSTGRES_DATABASE")
    if pg_host and pg_user and pg_pass and pg_db:
        url = f"postgresql://{pg_user}:{pg_pass}@{pg_host}/{pg_db}?sslmode=require"
        return url, "PG_*_COMPOSED"

    return None, None


def _safe_dsn_summary(url: str | None, source: str | None) -> str:
    if not url:
        return "No database URL configured"
    parsed = urlparse(url)
    dbname = (parsed.path or "").lstrip("/")
    return (
        f"host={parsed.hostname} db={dbname} user={parsed.username} "
        f"scheme={parsed.scheme} source={source}"
    )


def connect_db():
    """Create or reuse a global connection pool and fetch a connection."""
    url, source = get_database_url()
    if not url:
        logger.error("Database URL not found in environment.")
        return None
    try:
        # Initialize pool lazily and store on module-level
        global _POOL
        if "_POOL" not in globals() or _POOL is None:
            _POOL = SimpleConnectionPool(minconn=1, maxconn=10, dsn=url)
            logger.info("Initialized DB pool (%s)", _safe_dsn_summary(url, source))
        conn = _POOL.getconn()
        # Optionally set autocommit for simple queries
        conn.autocommit = True
        return conn
    except psycopg2.Error as e:
        logger.error(
            "Error obtaining DB connection (%s): %s", _safe_dsn_summary(url, source), e
        )
        return None


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if "db" not in g:
        g.db = connect_db()
        g._db_from_pool = True if g.db is not None else False
    return g.db


def close_db(e=None):
    """Closes the database connection."""
    db = g.pop("db", None)
    from_pool = g.pop("_db_from_pool", False)

    if db is not None:
        global _POOL
        if from_pool and "_POOL" in globals() and _POOL is not None:
            try:
                _POOL.putconn(db)
            except Exception as exc:
                # Fallback to close if cannot return to pool
                logger.debug("Failed to return connection to pool: %s", exc)
                try:
                    db.close()
                except Exception as exc2:
                    logger.debug("Failed to close connection: %s", exc2)
        else:
            try:
                db.close()
            except Exception as exc:
                logger.debug("Failed to close connection: %s", exc)
        logger.info("Database connection released.")


def init_db():
    conn = get_db()  # Use get_db instead of connect_db
    if conn is None:
        logger.error("Failed to connect to the database.")
        return False

    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                date_published TIMESTAMP NOT NULL,
                is_published BOOLEAN NOT NULL DEFAULT FALSE,
                slug TEXT UNIQUE NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                image_url TEXT,
                technologies TEXT, -- Comma-separated or JSON
                github_link TEXT,
                live_demo_link TEXT,
                date_added TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS article_views (
                id SERIAL PRIMARY KEY,
                article_slug TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                user_agent TEXT,
                viewed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(article_slug, ip_address)
            )
        """)
        # Helpful index for blog listing performance
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_published_date ON articles (is_published, date_published DESC)"
        )
        # Using autocommit, but safe to call commit in case autocommit was disabled
        try:
            conn.commit()
        except Exception as exc:
            logger.debug("Commit failed (likely autocommit on): %s", exc)
        logger.info("Database initialized or already exists.")
        return True
    except psycopg2.Error as e:
        logger.error(f"Error initializing database: {e}")
        return False
    finally:
        # Connection is now managed by app context, no close here
        pass
