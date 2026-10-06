import logging
import os
from urllib.parse import urlparse

import psycopg2
import psycopg2.extensions
from flask import g, has_app_context
from psycopg2.pool import ThreadedConnectionPool

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
    """Check if a database connection is still usable.

    Used only when recovering from errors or explicitly probing.
    """
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


def commit_db(conn):
    """Safely commit transaction if autocommit is disabled."""
    if conn is not None and not getattr(conn, "autocommit", False):
        try:
            conn.commit()
        except psycopg2.ProgrammingError as e:
            logger.debug("commit_db skipped (autocommit on): %s", e)


def rollback_db(conn):
    """Safely rollback transaction if autocommit is disabled."""
    if conn is not None and not getattr(conn, "autocommit", False):
        try:
            conn.rollback()
        except Exception as e:
            logger.debug("rollback_db failed: %s", e)


def connect_db():
    """Create or reuse a thread-safe connection pool and fetch a connection."""
    global _POOL
    url, source = get_database_url()
    if not url:
        logger.error("Database URL not found in environment.")
        return None

    for attempt in range(_MAX_RETRIES):
        try:
            if _POOL is None:
                max_conn = int(os.getenv("DB_POOL_MAX", "5"))
                _POOL = ThreadedConnectionPool(minconn=1, maxconn=max_conn, dsn=url)
                logger.info("Initialized DB pool (%s)", _safe_dsn_summary(url, source))

            conn = _POOL.getconn()

            # Fast in-memory check without network roundtrip
            if conn.closed:
                logger.warning(
                    "Got closed connection from pool, resetting pool (attempt %d)",
                    attempt + 1,
                )
                try:
                    _POOL.putconn(conn, close=True)
                except Exception as e:
                    logger.debug("Failed to close stale connection: %s", e)
                _reset_pool()
                continue

            # Rollback any pending transaction before handing out
            if (
                hasattr(conn, "status")
                and conn.status == psycopg2.extensions.STATUS_IN_TRANSACTION
            ):
                try:
                    conn.rollback()
                except Exception as e:
                    logger.debug("Failed to rollback pending transaction: %s", e)

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
    if not has_app_context():
        return connect_db()
    if "db" not in g:
        g.db = connect_db()
        g._db_from_pool = True if g.db is not None else False
    return g.db


def close_db(e=None):
    """Closes or returns the database connection to the pool."""
    global _POOL
    if not has_app_context():
        return
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


# Tables plus the newest migrated columns. When adding a future migration,
# extend this probe so cold starts keep skipping the full DDL walk.
_SCHEMA_PROBE_TABLES = (
    "articles",
    "projects",
    "site_settings",
    "article_views",
    "images",
)
_SCHEMA_PROBE_COLUMNS = (
    ("article_views", "view_date"),
    ("article_views", "referrer_host"),
    ("projects", "is_visible"),
    ("projects", "is_featured"),
    ("projects", "sort_order"),
)


def _schema_is_ready(conn) -> bool:
    """Fast check that the schema already exists.

    Uses PostgreSQL system catalog tables directly rather than heavy
    information_schema views for sub-millisecond execution on cold starts.
    """
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM pg_tables "
            "WHERE schemaname = 'public' "
            "AND tablename = ANY(%s)",
            (list(_SCHEMA_PROBE_TABLES),),
        )
        row = cur.fetchone()
        if not row or row[0] < len(_SCHEMA_PROBE_TABLES):
            return False

        cur.execute(
            """
            SELECT COUNT(*) FROM pg_attribute a
            JOIN pg_class c ON a.attrelid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE n.nspname = 'public'
              AND (c.relname || '.' || a.attname) = ANY(%s)
              AND a.attnum > 0 AND NOT a.attisdropped
            """,
            ([f"{pair[0]}.{pair[1]}" for pair in _SCHEMA_PROBE_COLUMNS],),
        )
        row = cur.fetchone()
        return bool(row and row[0] >= len(_SCHEMA_PROBE_COLUMNS))
    except Exception as e:
        logger.debug(
            "Fast catalog schema probe failed, falling back to full init: %s", e
        )
        return False


def init_db():
    conn = get_db()
    if conn is None:
        logger.error("Failed to connect to the database.")
        return False

    try:
        if _schema_is_ready(conn):
            logger.debug("Schema already present, skipping DDL.")
            return True
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS articles (\n                id SERIAL PRIMARY KEY,\n                title TEXT NOT NULL,\n                content TEXT NOT NULL,\n                date_published TIMESTAMP NOT NULL,\n                is_published BOOLEAN NOT NULL DEFAULT FALSE,\n                slug TEXT UNIQUE NOT NULL,\n                search_vector tsvector\n                    GENERATED ALWAYS AS (\n                        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||\n                        setweight(\n                            to_tsvector(\n                                'english',\n                                coalesce(regexp_replace(content, '<[^>]+>', ' ', 'g'), '')\n                            ),\n                            'B'\n                        )\n                    ) STORED\n            )\n        """)
        cur.execute(
            "ALTER TABLE articles ADD COLUMN IF NOT EXISTS search_vector tsvector"
            " GENERATED ALWAYS AS ("
            "   setweight(to_tsvector('english', coalesce(title, '')), 'A') ||"
            "   setweight(to_tsvector('english', coalesce(regexp_replace(content, '<[^>]+>', ' ', 'g'), '')), 'B')"
            " ) STORED"
        )
        cur.execute("""
            CREATE TABLE IF NOT EXISTS projects (\n                id SERIAL PRIMARY KEY,\n                title TEXT NOT NULL,\n                description TEXT NOT NULL,\n                image_url TEXT,\n                technologies TEXT, -- Comma-separated or JSON\n                github_link TEXT,\n                live_demo_link TEXT,\n                date_added TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n                is_visible BOOLEAN NOT NULL DEFAULT TRUE,\n                is_featured BOOLEAN NOT NULL DEFAULT FALSE,\n                sort_order INTEGER NOT NULL DEFAULT 0\n            )\n        """)
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
            CREATE TABLE IF NOT EXISTS site_settings (\n                key TEXT PRIMARY KEY,\n                value JSONB NOT NULL,\n                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP\n            )\n        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS article_views (\n                id SERIAL PRIMARY KEY,\n                article_slug TEXT NOT NULL,\n                ip_address TEXT NOT NULL,\n                user_agent TEXT,\n                viewed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n                view_date DATE NOT NULL DEFAULT CURRENT_DATE,\n                UNIQUE(article_slug, ip_address, view_date)\n            )\n        """)
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
        # Index on view_date for daily view queries
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_article_views_view_date ON article_views (view_date)"
        )
        # Composite index for project curation and visibility sorting
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_projects_visible_order ON projects (is_visible, sort_order ASC, date_added DESC)"
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
            CREATE TABLE IF NOT EXISTS images (\n                id TEXT PRIMARY KEY,\n                filename TEXT,\n                content_type TEXT NOT NULL,\n                data BYTEA NOT NULL,\n                byte_size INTEGER NOT NULL,\n                uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP\n            )\n        """)
        commit_db(conn)
        logger.info("Database initialized or already exists.")
        return True
    except psycopg2.Error as e:
        logger.error(f"Error initializing database: {e}")
        rollback_db(conn)
        return False
    finally:
        pass
