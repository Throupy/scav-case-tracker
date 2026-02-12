import pytest
from flask import url_for, get_flashed_messages


def test_dashboard_route(client):
    """Test the dashboard route."""
    response = client.get(url_for("cases.dashboard"))
    assert response.status_code == 200
    assert b"Dashboard" in response.data


def test_not_implemented_route(client):
    """Test the not implemented route."""
    with client:
        response = client.get(url_for("main.not_implemented"), follow_redirects=True)
        assert response.status_code == 200
        flashed_messages = get_flashed_messages(with_categories=True)
        assert (
            "warning",
            "This feature hasn't been implemented yet",
        ) in flashed_messages


def test_search_items_route(client):
    """Test the search items route with a valid query."""
    response = client.get(url_for("main.search_items", q="object #"))
    assert response.status_code == 200
    # Assuming the response contains a list of items
    assert b"Object #11SR keycard" in response.data
    assert b"Object #21WS keycard" in response.data
