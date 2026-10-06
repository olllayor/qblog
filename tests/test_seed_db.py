"""Unit tests for seed_db module."""

from unittest.mock import MagicMock, patch

import seed_db


def test_seed_articles():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    seed_db.seed_articles(mock_conn)
    assert mock_cursor.execute.call_count == len(seed_db.MOCK_ARTICLES)


def test_seed_projects_insert_and_update():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    # First project exists, second does not
    mock_cursor.fetchone.side_effect = [(1,), None, None, None]
    mock_conn.cursor.return_value = mock_cursor
    seed_db.seed_projects(mock_conn)
    # Check that execute was called for select and then insert/update
    assert mock_cursor.execute.call_count == len(seed_db.MOCK_PROJECTS) * 2


def test_seed_settings():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    seed_db.seed_settings(mock_conn)
    assert mock_cursor.execute.call_count == 1


def test_seed_views():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    seed_db.seed_views(mock_conn)
    assert mock_cursor.execute.call_count == 10 * len(seed_db.MOCK_VIEWS)


def test_clean_database():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    seed_db.clean_database(mock_conn)
    assert mock_cursor.execute.call_count == 1


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
    ):
        assert seed_db.seed_database(clean=True) is True
