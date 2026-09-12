from app.extensions import bcrypt, db
from app.models import User


def _create_user(username):
    user = User(
        username=username,
        password=bcrypt.generate_password_hash("Password123!").decode("utf-8"),
    )
    db.session.add(user)
    db.session.flush()
    return user.id


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def test_user_settings_defaults(session):
    user_id = _create_user("settings_defaults")
    user = db.session.get(User, user_id)
    assert user.theme_mode == "dark"
    assert user.accent_colour == "red"
    assert user.max_level_charisma is False


def test_settings_requires_login(client):
    with client.session_transaction() as session:
        session.pop("_user_id", None)
    response = client.get("/users/settings", follow_redirects=False)
    assert response.status_code == 302


def test_settings_persist_per_account(client, session):
    user_id = _create_user("settings_save")
    _login(client, user_id)

    response = client.post(
        "/users/settings",
        data={
            "theme_mode": "light",
            "accent_colour": "purple",
            "max_level_charisma": "y",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    user = db.session.get(User, user_id)
    assert user.theme_mode == "light"
    assert user.accent_colour == "purple"
    assert user.max_level_charisma is True
