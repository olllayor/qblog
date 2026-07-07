import logging
import os
from urllib.parse import urlparse

import psycopg2
from flask import g
from psycopg2.pool import SimpleConnectionPool

logger = logging.getLogger(__name__)

_POOL = None
_MAX_RETRIES = 3


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


def _is_connection_alive(conn) -> bool:
    """Check if a database connection is still usable."""
    if conn is None:
        return False
    try:
        if conn.closed:
            return False
        # Rollback any pending transaction before testing
        conn.rollback()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        return True
    except Exception:
        return False


def _reset_pool():
    """Reset the connection pool when connections become stale."""
    global _POOL
    if _POOL is not None:
        try:
            _POOL.closeall()
        except Exception as e:
            logger.debug("Error closing pool: %s", e)
        _POOL = None


def connect_db():
    """Create or reuse a global connection pool and fetch a connection with retry logic."""
    global _POOL
    url, source = get_database_url()
    if not url:
        logger.error("Database URL not found in environment.")
        return None

    for attempt in range(_MAX_RETRIES):
        try:
            if _POOL is None:
                # Serverless functions handle one request at a time, and each
                # instance gets its own pool; keep it small to avoid Postgres
                # connection exhaustion across many concurrent instances.
                max_conn = int(os.getenv("DB_POOL_MAX", "2"))
                _POOL = SimpleConnectionPool(minconn=1, maxconn=max_conn, dsn=url)
                logger.info("Initialized DB pool (%s)", _safe_dsn_summary(url, source))

            conn = _POOL.getconn()

            if not _is_connection_alive(conn):
                logger.warning(
                    "Got stale connection from pool, resetting pool (attempt %d)",
                    attempt + 1,
                )
                try:
                    _POOL.putconn(conn, close=True)
                except Exception as e:
                    logger.debug("Failed to close stale connection: %s", e)
                _reset_pool()
                continue

            # Rollback any pending transaction before setting autocommit
            try:
                conn.rollback()
            except Exception as e:
                logger.debug("Failed to rollback transaction: %s", e)
            conn.autocommit = True
            return conn

        except psycopg2.OperationalError as e:
            logger.warning(
                "DB connection error (attempt %d/%d): %s", attempt + 1, _MAX_RETRIES, e
            )
            _reset_pool()
            if attempt == _MAX_RETRIES - 1:
                logger.error("Failed to connect after %d attempts", _MAX_RETRIES)
                return None
        except psycopg2.Error as e:
            logger.error(
                "Error obtaining DB connection (%s): %s",
                _safe_dsn_summary(url, source),
                e,
            )
            return None

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
    global _POOL
    db = g.pop("db", None)
    from_pool = g.pop("_db_from_pool", False)

    if db is not None:
        if from_pool and _POOL is not None:
            try:
                if db.closed:
                    logger.debug("Connection already closed, not returning to pool")
                else:
                    _POOL.putconn(db)
            except Exception as exc:
                logger.debug("Failed to return connection to pool: %s", exc)
                try:
                    if not db.closed:
                        db.close()
                except Exception as exc2:
                    logger.debug("Failed to close connection: %s", exc2)
        else:
            try:
                if not db.closed:
                    db.close()
            except Exception as exc:
                logger.debug("Failed to close connection: %s", exc)
        logger.debug("Database connection released.")


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
                slug TEXT UNIQUE NOT NULL,
                search_vector tsvector
                    GENERATED ALWAYS AS (
                        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
                        setweight(
                            to_tsvector(
                                'english',
                                coalesce(regexp_replace(content, '<[^>]+>', ' ', 'g'), '')
                            ),
                            'B'
                        )
                    ) STORED
            )
        """)
        cur.execute(
            "ALTER TABLE articles ADD COLUMN IF NOT EXISTS search_vector tsvector"
            " GENERATED ALWAYS AS ("
            "   setweight(to_tsvector('english', coalesce(title, '')), 'A') ||"
            "   setweight(to_tsvector('english', coalesce(regexp_replace(content, '<[^>]+>', ' ', 'g'), '')), 'B')"
            " ) STORED"
        )
        cur.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                image_url TEXT,
                technologies TEXT, -- Comma-separated or JSON
                github_link TEXT,
                live_demo_link TEXT,
                date_added TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_visible BOOLEAN NOT NULL DEFAULT TRUE,
                is_featured BOOLEAN NOT NULL DEFAULT FALSE,
                sort_order INTEGER NOT NULL DEFAULT 0
            )
        """)
        # Migrate pre-existing projects tables to the curation columns
        cur.execute(
            "ALTER TABLE projects ADD COLUMN IF NOT EXISTS is_visible BOOLEAN NOT NULL DEFAULT TRUE"
        )
        cur.execute(
            "ALTER TABLE projects ADD COLUMN IF NOT EXISTS is_featured BOOLEAN NOT NULL DEFAULT FALSE"
        )
        cur.execute(
            "ALTER TABLE projects ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0"
        )
        # Key/value store for admin-editable site settings (homepage copy, toggles)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS site_settings (
                key TEXT PRIMARY KEY,
                value JSONB NOT NULL,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS article_views (
                id SERIAL PRIMARY KEY,
                article_slug TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                user_agent TEXT,
                viewed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                view_date DATE NOT NULL DEFAULT CURRENT_DATE,
                UNIQUE(article_slug, ip_address, view_date)
            )
        """)
        # Migrate legacy schema (unique per slug+ip forever) to per-day dedup so
        # daily/monthly aggregates actually reflect returning visitors.
        cur.execute(
            "ALTER TABLE article_views ADD COLUMN IF NOT EXISTS view_date DATE NOT NULL DEFAULT CURRENT_DATE"
        )
        # When the column is first added to a legacy table, every existing row
        # gets today's date from the DEFAULT, collapsing all historical views
        # onto the migration day. Backfill from the real viewed_at timestamp.
        # Idempotent: matches nothing once view_date already tracks viewed_at.
        cur.execute(
            "UPDATE article_views SET view_date = viewed_at::date "
            "WHERE view_date <> viewed_at::date"
        )
        # Referrer host for audience stats (nullable; direct visits stay NULL)
        cur.execute(
            "ALTER TABLE article_views ADD COLUMN IF NOT EXISTS referrer_host TEXT"
        )
        cur.execute(
            "ALTER TABLE article_views "
            "DROP CONSTRAINT IF EXISTS article_views_article_slug_ip_address_key"
        )
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'article_views_slug_ip_date_key'
                ) THEN
                    ALTER TABLE article_views
                        ADD CONSTRAINT article_views_slug_ip_date_key
                        UNIQUE (article_slug, ip_address, view_date);
                END IF;
            END$$;
        """)
        # Helpful index for blog listing performance
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_published_date ON articles (is_published, date_published DESC)"
        )
        # Index for daily/monthly view aggregation
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_article_views_viewed_at ON article_views (viewed_at)"
        )
        # Index for per-article view counts
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_article_views_slug ON article_views (article_slug)"
        )
        # GIN index for Postgres full-text search
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_search ON articles USING GIN (search_vector)"
        )
        # Uploaded images, stored as bytes so they survive Vercel's read-only FS.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id TEXT PRIMARY KEY,
                filename TEXT,
                content_type TEXT NOT NULL,
                data BYTEA NOT NULL,
                byte_size INTEGER NOT NULL,
                uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
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
