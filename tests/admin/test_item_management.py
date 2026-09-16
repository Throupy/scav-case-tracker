import pytest

from app.extensions import db
from app.models import TarkovItem, User
from app.services.tarkov_item_import_service import TarkovItemImportService


def _login_superuser(client, username="item_admin"):
    user = User(username=username, password="unused", is_superuser=True)
    db.session.add(user)
    db.session.commit()
    with client.session_transaction() as flask_session:
        flask_session["_user_id"] = str(user.id)
        flask_session["_fresh"] = True
    return user


def _login_regular_user(client, username="regular_user"):
    user = User(username=username, password="unused", is_superuser=False)
    db.session.add(user)
    db.session.commit()
    with client.session_transaction() as flask_session:
        flask_session["_user_id"] = str(user.id)
        flask_session["_fresh"] = True
    return user


def test_item_management_requires_login(client):
    response = client.get("/admin/items")
    assert response.status_code == 302


@pytest.mark.parametrize(
    "path, method",
    [
        ("/admin", "get"),
        ("/admin/", "get"),
        ("/admin/items", "get"),
        ("/admin/items/check", "post"),
        ("/admin/items/import", "post"),
        ("/admin/users", "get"),
    ],
)
def test_regular_users_receive_403_for_admin_endpoints(client, path, method):
    _login_regular_user(client, f"regular_{method}_{path.replace('/', '_')}")
    response = getattr(client, method)(path)
    assert response.status_code == 403


def test_admin_landing_redirects_superusers(client):
    _login_superuser(client, "landing_admin")
    response = client.get("/admin")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/items")


def test_check_items_previews_without_writing(client, monkeypatch):
    _login_superuser(client, "preview_admin")
    preview = {
        "id": "new-preview-id",
        "name": "Preview Item",
        "category": "Barter Items",
        "source_categories": ["Other"],
        "types": ["item"],
        "image_link": None,
        "base_price": 1234,
        "scav_case_eligible": True,
        "eligibility_reason": "Available for scav-case selection",
    }
    monkeypatch.setattr(TarkovItemImportService, "find_new_items", lambda self: [preview])

    before = TarkovItem.query.count()
    response = client.post("/admin/items/check")

    assert response.status_code == 200
    assert b"Preview Item" in response.data
    assert b"1,234" in response.data
    assert TarkovItem.query.count() == before


def test_import_refetches_and_rejects_ineligible_items(client, monkeypatch):
    _login_superuser(client, "import_admin")
    rows = [
        {
            "id": "allowed-id",
            "name": "Allowed Item",
            "category": "Guns",
            "image_link": None,
            "scav_case_eligible": True,
        },
        {
            "id": "preset-id",
            "name": "Custom Preset",
            "category": "Guns",
            "image_link": None,
            "scav_case_eligible": False,
        },
    ]
    monkeypatch.setattr(TarkovItemImportService, "fetch_catalog", lambda self: rows)

    response = client.post(
        "/admin/items/import",
        data={"item_ids": ["allowed-id", "preset-id", "invented-id"]},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert TarkovItem.query.filter_by(tarkov_id="allowed-id").one().name == "Allowed Item"
    assert TarkovItem.query.filter_by(tarkov_id="preset-id").first() is None
    assert TarkovItem.query.filter_by(tarkov_id="invented-id").first() is None
    assert b"Imported 1 item" in response.data
    assert b"Skipped 2 item" in response.data
