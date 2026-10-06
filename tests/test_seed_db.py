"""Unit tests for seed_db module."""

from unittest.mock import MagicMock

import seed_db


def test_seed_articles():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    seed_db.seed_articles(mock_conn)

    # Verify each mock article was inserted with its title and slug
    executed_queries = [call[0][0] for call in mock_cursor.execute.call_args_list]
    executed_params = [call[0][1] for call in mock_cursor.execute.call_args_list]

    assert len(executed_queries) == len(seed_db.MOCK_ARTICLES)
    assert all("INSERT INTO articles" in q for q in executed_queries)
    seeded_pairs = [(p[0], p[4]) for p in executed_params]
    for article in seed_db.MOCK_ARTICLES:
        assert (article["title"], article["slug"]) in seeded_pairs


def test_seed_projects_insert_and_update():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    # First project exists (id=1), subsequent do not
    mock_cursor.fetchone.side_effect = [(1,), None, None, None]
    mock_conn.cursor.return_value = mock_cursor
    seed_db.seed_projects(mock_conn)

    executed_queries = [call[0][0] for call in mock_cursor.execute.call_args_list]
    select_count = sum(
        1 for q in executed_queries if "SELECT id FROM projects WHERE title = %s" in q
    )
    update_count = sum(
        1 for q in executed_queries if "UPDATE projects" in q and "SET" in q
    )
    insert_count = sum(1 for q in executed_queries if "INSERT INTO projects" in q)

    assert select_count == len(seed_db.MOCK_PROJECTS)
    assert update_count == 1
    assert insert_count == len(seed_db.MOCK_PROJECTS) - 1


def test_seed_settings():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    seed_db.seed_settings(mock_conn)

    assert mock_cursor.execute.call_count == 1
    query, params = mock_cursor.execute.call_args[0]
    assert "INSERT INTO site_settings" in query
    assert params[0] == "homepage"


def test_seed_views():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    seed_db.seed_views(mock_conn)

    assert mock_cursor.execute.call_count == 10 * len(seed_db.MOCK_VIEWS)
    for call in mock_cursor.execute.call_args_list:
        query, params = call[0]
        assert "INSERT INTO article_views" in query
        slug, ip, ua, viewed_at, view_date, ref = params
        assert ip.startswith("192.168.1.")
        # Ensure timestamp date matches view_date
        assert viewed_at.date() == view_date
