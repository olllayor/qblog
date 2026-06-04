# Search Mental Model for qblog

Search is backed by Postgres full-text search — no external service is required.

## 1) What lives where

- Postgres is the **source of truth** for articles and the **search engine**.
- Flask routes orchestrate reads via the `search.py` service.
- `articles.search_vector` is a `GENERATED ALWAYS AS ... STORED` column that
  Postgres maintains automatically on every `INSERT`/`UPDATE`.

Code map:

- `database.py`: schema + `init_db()` migration that creates the column and the
  GIN index (idempotent — safe to run on a populated DB).
- `search.py`: thin service that runs `websearch_to_tsquery` + `ts_rank` queries
  and returns ranked `slug`s.
- `app.py`: route-level read path (`get_blog_articles`) that preserves search
  rank order when stitching together `Article` objects.

## 2) Write path (consistency model)

When an article changes:

1. Commit to Postgres (`articles` table).
2. Postgres recomputes `search_vector` from `title` + `content` automatically.

No app-side indexing, no async jobs, no eventual-consistency window. The vector
is always in sync with the row.

## 3) Read path (query model)

For `/blog?q=...` and `/api/articles?...&q=...`:

1. `search.py` runs `ts_rank` + `websearch_to_tsquery` against `search_vector`,
   filtered to `is_published = true`, ordered by rank then `date_published desc`,
   with `LIMIT/OFFSET` for pagination.
2. `articles.py` fetches the matching slugs in one query, preserving rank order.
3. App renders normal `Article` objects.

For empty query (`q=`):

- Skip search entirely.
- Use normal DB pagination.

## 4) Relevance model

Configured in `database.py` (the generated column expression) and `search.py`:

- fields: `title` (weight `A`) and `content` (weight `B`) — title matches outrank
  content matches.
- HTML in `content` is stripped via `regexp_replace(content, '<[^>]+>', ' ', 'g')`
  before tokenizing, so tags don't pollute the index.
- stemmer: English (`to_tsvector('english', ...)`).
- query parser: `websearch_to_tsquery` — supports quotes, `OR`, and `-` naturally.
- published-only filter: `is_published = true`.
- sort: `ts_rank desc`, then `date_published desc`.

## 5) Resilience model

Search has no external dependency. If the DB itself is down, the request fails
the same way every other DB-backed request does — there is no degraded mode
specific to search.

`SearchResult.degraded` is kept in the API for forward compatibility but is
effectively always `false`.

## 6) Verification and recovery

```bash
uv run python scripts/reindex_articles_es.py
```

This confirms the `search_vector` column exists, the GIN index is present, and
every published article is indexed.

Because the column is generated, there is nothing to reindex manually. To force
a re-vectorization after a Postgres upgrade or schema change:

```sql
ALTER TABLE articles ADD COLUMN search_vector_new tsvector
  GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(regexp_replace(content, '<[^>]+>', ' ', 'g'), '')), 'B')
  ) STORED;
ALTER TABLE articles DROP COLUMN search_vector;
ALTER TABLE articles RENAME COLUMN search_vector_new TO search_vector;
CREATE INDEX idx_articles_search ON articles USING GIN (search_vector);
```

## 7) How to read your logs

- `Postgres search failed for query '...'` → DB query error; check Postgres
  connectivity and that `search_vector` exists.
- `articles.search_vector column missing` → `init_db()` has not been run since
  the migration was added.

## 8) Quick verification checklist

1. `GET /blog` works exactly like before.
2. `GET /blog?q=flask` returns ranked posts that contain "flask" in title or
   content.
3. `GET /blog?q=` behaves like a normal list.
4. `GET /api/articles?page=2&per_page=6&q=...` keeps infinite scroll for
   search.
5. Publish a new article containing a unique word; search for that word and
   confirm it appears immediately (no reindex step needed).

## 9) Common failure patterns

- No results but expected matches:
  - article isn't published (`is_published = false` is filtered out)
  - search term is too short or only stopwords; `websearch_to_tsquery` drops
    most stopwords on its own
- Slow queries:
  - GIN index missing — run `init_db()` or recreate with `CREATE INDEX`
- Postgres version < 11:
  - `websearch_to_tsquery` requires 11+. Fall back to `plainto_tsquery` in
    `search.py` if needed.
