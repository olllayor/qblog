"""Admin-editable site settings stored as JSONB rows in site_settings."""

import json
import logging

import psycopg2

from database import get_db

logger = logging.getLogger(__name__)

# Defaults mirror the previously hardcoded homepage copy, so an empty
# site_settings table renders the site exactly as before.
HOMEPAGE_DEFAULTS = {
    "hero_emoji": "👋",
    "hero_greeting": "hey! i'm ollayor",
    "hero_line1": "i'm a software developer & full-time breaker.",
    "hero_line2": "I break things, fix them, then break them better.",
    "show_readers_badge": True,
    "show_projects": True,
    "blog_cta_text": "Read my thoughts",
}


def get_homepage_settings():
    """Homepage settings merged over defaults. Never raises."""
    merged = dict(HOMEPAGE_DEFAULTS)
    conn = get_db()
    if conn is None:
        return merged
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM site_settings WHERE key = %s", ("homepage",))
        row = cur.fetchone()
        if row and isinstance(row[0], dict):
            stored = {k: v for k, v in row[0].items() if k in HOMEPAGE_DEFAULTS}
            merged.update(stored)
    except psycopg2.Error as e:
        logger.warning("Failed to load homepage settings: %s", e)
    return merged


def save_homepage_settings(values):
    """Upsert homepage settings; unknown keys are dropped."""
    clean = {k: v for k, v in values.items() if k in HOMEPAGE_DEFAULTS}
    conn = get_db()
    if conn is None:
        logger.error("Failed to connect to the database.")
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO site_settings (key, value, updated_at)
               VALUES (%s, %s, CURRENT_TIMESTAMP)
               ON CONFLICT (key) DO UPDATE
               SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP""",
            ("homepage", json.dumps(clean)),
        )
        conn.commit()
        return True
    except psycopg2.Error as e:
        logger.error("Failed to save homepage settings: %s", e)
        conn.rollback()
        return False
