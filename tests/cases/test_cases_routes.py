from app.models import User, ScavCase
from app.extensions import db, bcrypt


def _create_user(username, password="Password123!"):
    """Create a user in the current session (flush, no commit)."""
    hashed = bcrypt.generate_password_hash(password).decode("utf-8")
    user = User(username=username, password=hashed)
    db.session.add(user)
    db.session.flush()
    return user.id


def _create_case(user_id):
    """Create a ScavCase in the current session (flush, no commit)."""
    sc = ScavCase(
        user_id=user_id,
        type="₽2500",
        cost=2500.0,
        _return=5000.0,
        number_of_items=0,
    )
    db.session.add(sc)
    db.session.flush()
    return sc.id


def _login(client, user_id):
    """Simulate a login by writing directly to Flask-Login's session."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True


def _logout(client):
    """Clear the Flask-Login session cookie."""
    with client.session_transaction() as sess:
        sess.pop("_user_id", None)


def test_search_items_no_query_param(client):
    """GET /cases/search-items with no q param should return 200, not crash."""
    response = client.get("/cases/search-items")
    assert response.status_code == 200


def test_search_items_short_query(client):
    """GET /cases/search-items with a single character returns empty results."""
    response = client.get("/cases/search-items?q=x")
    assert response.status_code == 200


def test_all_cases_requires_login(client):
    """GET /cases/all redirects unauthenticated users to login."""
    _logout(client)
    response = client.get("/cases/all", follow_redirects=False)
    assert response.status_code == 302
    assert "login" in response.location


def test_case_detail_requires_login(client, session):
    """Unauthenticated GET /cases/<id> redirects to login."""
    user_id = _create_user("rt_det_owner")
    case_id = _create_case(user_id)
    _logout(client)
    response = client.get(f"/cases/{case_id}", follow_redirects=False)
    assert response.status_code == 302
    assert "login" in response.location


def test_case_detail_requires_ownership(client, session):
    """Authenticated user cannot view another user's case — expects 403."""
    owner_id = _create_user("rt_det_owner2")
    case_id = _create_case(owner_id)
    attacker_id = _create_user("rt_det_attacker")
    _login(client, attacker_id)
    response = client.get(f"/cases/{case_id}", follow_redirects=False)
    assert response.status_code == 403


def test_case_detail_owner_can_view(client, session):
    """Owner can view their own case detail page."""
    user_id = _create_user("rt_det_viewer")
    case_id = _create_case(user_id)
    _login(client, user_id)
    response = client.get(f"/cases/{case_id}")
    assert response.status_code == 200


def test_delete_case_requires_ownership(client, session):
    """Non-owner POST to delete another user's case returns 403."""
    owner_id = _create_user("rt_del_owner")
    case_id = _create_case(owner_id)
    attacker_id = _create_user("rt_del_attacker")
    _login(client, attacker_id)
    response = client.post(f"/cases/{case_id}/delete", follow_redirects=False)
    assert response.status_code == 403
