import logging
from dataclasses import dataclass

from database import get_db

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    slugs: list[str]
    total: int
    degraded: bool = False


class PostgresSearchService:
    def __init__(self):
        self._column_checked = False

    def is_enabled(self) -> bool:
        return True

    def ensure_index(self) -> bool:
        if self._column_checked:
            return True
        conn = get_db()
        if conn is None:
            logger.warning("Search unavailable: database connection is None.")
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'articles' AND column_name = 'search_vector'
                """
            )
            if cur.fetchone() is None:
                logger.warning(
                    "articles.search_vector column missing. "
                    "Run init_db() to create it before searching."
                )
                return False
            self._column_checked = True
            return True
        except Exception as exc:
            logger.warning("Failed verifying search_vector column: %s", exc)
            return False

    def index_article(self, article) -> bool:
        return self.ensure_index()

    def delete_article(self, slug: str) -> bool:
        return True

    def search_published_slugs(
        self, query: str, page: int, per_page: int
    ) -> SearchResult:
        clean_query = (query or "").strip()
        if not clean_query:
            return SearchResult(slugs=[], total=0, degraded=False)

        if not self.ensure_index():
            return SearchResult(slugs=[], total=0, degraded=True)

        page = max(1, page)
        per_page = max(1, per_page)
        from_ = (page - 1) * per_page

        conn = get_db()
        if conn is None:
            return SearchResult(slugs=[], total=0, degraded=True)

        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT slug,
                       ts_rank(search_vector, tsq) AS rank
                FROM articles, websearch_to_tsquery('english', %s) AS tsq
                WHERE search_vector @@ tsq
                  AND is_published = TRUE
                ORDER BY rank DESC, date_published DESC
                LIMIT %s OFFSET %s
                """,
                (clean_query, per_page, from_),
            )
            slugs = [row[0] for row in cur.fetchall() if row[0]]

            cur.execute(
                """
                SELECT COUNT(*)
                FROM articles, websearch_to_tsquery('english', %s) AS tsq
                WHERE search_vector @@ tsq
                  AND is_published = TRUE
                """,
                (clean_query,),
            )
            total_row = cur.fetchone()
            total = int(total_row[0]) if total_row else 0

            return SearchResult(slugs=slugs, total=total, degraded=False)
        except Exception as exc:
            logger.warning(
                "Postgres search failed for query '%s': %s", clean_query, exc
            )
            return SearchResult(slugs=[], total=0, degraded=True)


_SEARCH_SERVICE = None


def get_search_service() -> PostgresSearchService:
    global _SEARCH_SERVICE
    if _SEARCH_SERVICE is None:
        _SEARCH_SERVICE = PostgresSearchService()
    return _SEARCH_SERVICE
