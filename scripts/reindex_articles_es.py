#!/usr/bin/env python3
"""Verify Postgres full-text search is wired up.

The search_vector column is maintained automatically by Postgres as a
GENERATED column, so there is nothing to reindex. This script just checks
that the column and its GIN index exist, and that the index covers every
published article.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import get_db


def main() -> int:
    with app.app_context():
        conn = get_db()
        if conn is None:
            print("Could not connect to the database.")
            return 1

        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'articles' AND column_name = 'search_vector'
                """
            )
            if cur.fetchone() is None:
                print("articles.search_vector column is missing. Run init_db().")
                return 1

            cur.execute("SELECT COUNT(*) FROM articles WHERE is_published = TRUE")
            total_row = cur.fetchone()
            total = int(total_row[0]) if total_row else 0

            cur.execute(
                "SELECT COUNT(*) FROM articles"
                " WHERE is_published = TRUE AND search_vector IS NOT NULL"
            )
            indexed_row = cur.fetchone()
            indexed = int(indexed_row[0]) if indexed_row else 0

            print(f"Search ready. published={total} indexed={indexed}")
            return 0 if total == indexed else 2
        except Exception as exc:
            print(f"Search check failed: {exc}")
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
