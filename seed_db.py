#!/usr/bin/env python3
"""Seed the local database with realistic mock articles, projects, and settings.

Usage:
    uv run python seed_db.py [--clean]
"""

import argparse
import json
import logging
import os
import sys
from datetime import UTC, datetime, timedelta

from dotenv import load_dotenv

# Ensure root modules can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables (.env) if present
load_dotenv()

# Default to local Docker Compose database credentials if not configured
os.environ.setdefault("DATABASE_URL", "postgresql://qblog:qblog@localhost:5432/qblog")

from database import commit_db, get_db, init_db  # noqa: E402
from settings import HOMEPAGE_DEFAULTS  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

MOCK_ARTICLES = [
    {
        "title": "Building High-Throughput Telegram Bots with Python and Asyncio",
        "slug": "building-high-throughput-telegram-bots-with-python-and-asyncio",
        "content": """
<h2>Introduction</h2>
<p>As telegram bots scale to thousands of active concurrent users, naive synchronous architectures quickly buckle under I/O bottlenecks. In this guide, we dive deep into building production-ready Telegram bots using Python 3.12, <code>asyncio</code>, and pooled persistent webhooks.</p>

<h2>Architecture Overview</h2>
<p>A resilient bot architecture separates edge webhook ingestion from worker execution via message brokers or in-memory asyncio worker queues:</p>
<ul>
    <li><strong>Edge Gateway:</strong> Validates webhook requests and publishes events.</li>
    <li><strong>Worker Pool:</strong> Consumes Telegram updates and processes business logic.</li>
    <li><strong>State Store:</strong> Redis for conversation sessions and rate-limiting counters.</li>
</ul>

<h2>Handling Concurrency with Asyncio</h2>
<p>Utilizing Python's <code>asyncio.gather</code> and bounded task semaphores ensures that slow network calls to third-party APIs never block handling new user interactions.</p>
""",
        "date_published": datetime.now(UTC) - timedelta(days=12),
        "is_published": True,
    },
    {
        "title": "Modern Database Indexing Patterns in PostgreSQL: Beyond B-Trees",
        "slug": "modern-database-indexing-patterns-in-postgresql-beyond-b-trees",
        "content": """
<h2>Why B-Trees Are Not Always the Answer</h2>
<p>PostgreSQL offers versatile index types tailored to diverse access patterns. While the default B-Tree index excels at scalar equality and range queries, modern applications often handle semi-structured data, full-text search, and time-series metrics.</p>

<h2>GIN Indexes for Full-Text Search</h2>
<p>Generalized Inverted Indexes (GIN) are optimized for items containing multiple elements—such as arrays, JSONB keys, and <code>tsvector</code> text search vectors. In qblog, a stored generated tsvector column combined with a GIN index allows instant sub-millisecond full-text queries across thousands of technical posts.</p>

<h2>BRIN Indexes for Append-Only Time Series</h2>
<p>Block Range Indexes (BRIN) summarize values within contiguous physical page ranges. For append-only log tables and view tracking, BRIN indexes occupy a fraction of the disk footprint compared to B-Trees while maintaining rapid scan capabilities.</p>
""",
        "date_published": datetime.now(UTC) - timedelta(days=7),
        "is_published": True,
    },
    {
        "title": "Designing Resilient Caching Architectures with Redis and Flask",
        "slug": "designing-resilient-caching-architectures-with-redis-and-flask",
        "content": """
<h2>The Fallacy of Cache-As-Database</h2>
<p>Caching is one of the highest-leverage performance optimizations available for web applications, but naive caching introduces subtle bugs: stale reads, cache stampedes, and memory fragmentation.</p>

<h2>Cache Stampede Prevention</h2>
<p>When high-traffic keys expire simultaneously, hundreds of parallel requests can overwhelm the primary database. Implementing probabilistic early expiration (XFetch algorithm) or distributed lock renewal ensures smooth background refreshes without user disruption.</p>
""",
        "date_published": datetime.now(UTC) - timedelta(days=3),
        "is_published": True,
    },
    {
        "title": "Draft: Future of Edge Computing and Serverless Deployments",
        "slug": "future-of-edge-computing-and-serverless-deployments",
        "content": """
<h2>Exploring Next-Gen Edge Runtimes</h2>
<p>This draft explores running lightweight Python and WebAssembly runtimes at edge points of presence, dramatically lowering latency for international audiences.</p>
""",
        "date_published": datetime.now(UTC) - timedelta(days=1),
        "is_published": False,
    },
]

MOCK_PROJECTS = [
    {
        "title": "qblog - Modern Developer Portfolio & Publishing Platform",
        "description": "Ultra-fast, markdown-centric developer publishing engine and portfolio with PostgreSQL full-text search, Redis caching, and automated Tailwind CSS compilation.",
        "image_url": "/static/myself-social-optimized.jpg",
        "technologies": "Python,Flask,PostgreSQL,Redis,Tailwind CSS",
        "github_link": "https://github.com/olllayor/qblog",
        "live_demo_link": "https://ollayor.uz",
        "is_visible": True,
        "is_featured": True,
        "sort_order": 1,
    },
    {
        "title": "AsyncBot Engine - Scalable Telegram Framework",
        "description": "High-throughput asynchronous Telegram bot platform featuring distributed rate limiting, state machine workflows, and edge webhook scaling.",
        "image_url": None,
        "technologies": "Python,Asyncio,Redis,Docker",
        "github_link": "https://github.com/olllayor/asyncbot-engine",
        "live_demo_link": "https://t.me/examplebot",
        "is_visible": True,
        "is_featured": True,
        "sort_order": 2,
    },
    {
        "title": "DevMetrics - Edge Telemetry Collector",
        "description": "Lightweight telemetry aggregator and dashboard delivering real-time performance insights, error tracking, and request distribution analytics.",
        "image_url": None,
        "technologies": "TypeScript,Next.js,FastAPI,PostgreSQL",
        "github_link": "https://github.com/olllayor/devmetrics",
        "live_demo_link": "https://metrics.example.com",
        "is_visible": True,
        "is_featured": False,
        "sort_order": 3,
    },
    {
        "title": "CacheFlow - Resilient Caching Library",
        "description": "Zero-overhead distributed cache abstraction with tiered failover, jittered expiration, and stampede suppression.",
        "image_url": None,
        "technologies": "Python,Redis,Memcached",
        "github_link": "https://github.com/olllayor/cacheflow",
        "live_demo_link": None,
        "is_visible": True,
        "is_featured": False,
        "sort_order": 4,
    },
]

MOCK_VIEWS = [
    (
        "building-high-throughput-telegram-bots-with-python-and-asyncio",
        "192.168.1.101",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "news.ycombinator.com",
    ),
    (
        "building-high-throughput-telegram-bots-with-python-and-asyncio",
        "192.168.1.102",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
        "twitter.com",
    ),
    (
        "modern-database-indexing-patterns-in-postgresql-beyond-b-trees",
        "192.168.1.103",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "github.com",
    ),
    (
        "modern-database-indexing-patterns-in-postgresql-beyond-b-trees",
        "192.168.1.104",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "google.com",
    ),
    (
        "designing-resilient-caching-architectures-with-redis-and-flask",
        "192.168.1.105",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        None,
    ),
]


def clean_database(conn):
    """Truncate tables before reseeding."""
    logger.info("Cleaning existing mock data...")
    cur = conn.cursor()
    cur.execute(
        "TRUNCATE TABLE article_views, articles, projects, site_settings RESTART IDENTITY CASCADE"
    )
    commit_db(conn)
    logger.info("Database cleaned successfully.")


def seed_articles(conn):
    """Seed mock articles."""
    logger.info("Seeding articles...")
    cur = conn.cursor()
    for article in MOCK_ARTICLES:
        cur.execute(
            """
            INSERT INTO articles (title, content, date_published, is_published, slug)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE
            SET title = EXCLUDED.title,
                content = EXCLUDED.content,
                date_published = EXCLUDED.date_published,
                is_published = EXCLUDED.is_published
            """,
            (
                article["title"],
                article["content"].strip(),
                article["date_published"],
                article["is_published"],
                article["slug"],
            ),
        )
    commit_db(conn)
    logger.info("Seeded %d articles.", len(MOCK_ARTICLES))


def seed_projects(conn):
    """Seed mock projects."""
    logger.info("Seeding projects...")
    cur = conn.cursor()
    for proj in MOCK_PROJECTS:
        # Check if project with title already exists
        cur.execute("SELECT id FROM projects WHERE title = %s", (proj["title"],))
        existing = cur.fetchone()
        if existing:
            cur.execute(
                """
                UPDATE projects
                SET description = %s, image_url = %s, technologies = %s,
                    github_link = %s, live_demo_link = %s, is_visible = %s,
                    is_featured = %s, sort_order = %s
                WHERE id = %s
                """,
                (
                    proj["description"],
                    proj["image_url"],
                    proj["technologies"],
                    proj["github_link"],
                    proj["live_demo_link"],
                    proj["is_visible"],
                    proj["is_featured"],
                    proj["sort_order"],
                    existing[0],
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO projects
                    (title, description, image_url, technologies, github_link,
                     live_demo_link, is_visible, is_featured, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    proj["title"],
                    proj["description"],
                    proj["image_url"],
                    proj["technologies"],
                    proj["github_link"],
                    proj["live_demo_link"],
                    proj["is_visible"],
                    proj["is_featured"],
                    proj["sort_order"],
                ),
            )
    commit_db(conn)
    logger.info("Seeded %d projects.", len(MOCK_PROJECTS))


def seed_settings(conn):
    """Seed site settings."""
    logger.info("Seeding site settings...")
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO site_settings (key, value, updated_at)
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (key) DO UPDATE
        SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
        """,
        ("homepage", json.dumps(HOMEPAGE_DEFAULTS)),
    )
    commit_db(conn)
    logger.info("Seeded homepage site settings.")


def seed_views(conn):
    """Seed realistic article views."""
    logger.info("Seeding article views...")
    cur = conn.cursor()
    today = datetime.now(UTC).date()
    count = 0
    for day_offset in range(10):
        view_date = today - timedelta(days=day_offset)
        for slug, ip, ua, ref in MOCK_VIEWS:
            ip_variant = f"{ip[:-1]}{day_offset % 9 + 1}"
            viewed_at = datetime.now(UTC) - timedelta(
                days=day_offset, hours=day_offset % 12
            )
            cur.execute(
                """
                INSERT INTO article_views (article_slug, ip_address, user_agent, viewed_at, view_date, referrer_host)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (article_slug, ip_address, view_date) DO NOTHING
                """,
                (slug, ip_variant, ua, viewed_at, view_date, ref),
            )
            count += 1
    commit_db(conn)
    logger.info("Seeded article views across 10 days.")


def seed_database(clean=False):
    """Initialize schema and seed database."""
    logger.info("Connecting to database and initializing schema...")
    if not init_db():
        logger.error(
            "Failed to initialize database schema. Ensure PostgreSQL is running."
        )
        return False

    conn = get_db()
    if conn is None:
        logger.error("Could not obtain database connection.")
        return False

    try:
        if clean:
            clean_database(conn)
        seed_articles(conn)
        seed_projects(conn)
        seed_settings(conn)
        seed_views(conn)
        logger.info("Database seeding complete!")
        return True
    except Exception as e:
        logger.exception("Error seeding database: %s", e)
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed local PostgreSQL database.")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean (truncate) existing tables before seeding",
    )
    args = parser.parse_args()

    success = seed_database(clean=args.clean)
    sys.exit(0 if success else 1)
