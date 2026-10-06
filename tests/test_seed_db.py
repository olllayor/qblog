"""Unit tests for seed_db module."""

from unittest.mock import MagicMock, patch

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
    titles_seeded = [p[0] for p in executed_params]
    for article in seed_db.MOCK_ARTICLES:
        assert article["title"] in titles_seeded


def test_seed_projects_insert_and_update():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    # First project exists (id=1), subsequent do not
    mock_cursor.fetchone.side_effect = [(1,), None, None, None]
    mock_conn.cursor.return_value = mock_cursor
    seed_db.seed_projects(mock_conn)

    executed_queries = [call[0][0] for call in mock_cursor.execute.call_args_list]
    # Should perform SELECT queries to check existence
    assert any(
        "SELECT id FROM projects WHERE title = %s" in q for q in executed_queries
    )
    # Should perform UPDATE for existing project
    assert any("UPDATE projects" in q and "SET" in q for q in executed_queries)
    # Should perform INSERT for new projects
    assert any("INSERT INTO projects" in q for q in executed_queries)


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


def test_clean_database():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    seed_db.clean_database(mock_conn)

    assert mock_cursor.execute.call_count == 1
    query = mock_cursor.execute.call_args[0][0]
    assert "TRUNCATE TABLE" in query


def test_seed_database_failure_when_init_fails():
    with patch("seed_db.init_db", return_value=False):
        assert seed_db.seed_database() is False


def test_seed_database_success():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_conn.cursor.return_value = mock_cursor

    with (
        patch("seed_db.init_db", return_value=True),
        patch("seed_db.get_db", return_value=mock_conn),
        patch("seed_db.commit_db"),
    ):
        assert seed_db.seed_database() is True
