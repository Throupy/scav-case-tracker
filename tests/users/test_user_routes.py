from flask import url_for
from app.models import User


def test_register_user(client):
    """Test user registration."""
    response = client.post(
        url_for("users.register"),
        data={
            "username": "testuser",
            "password": "password123",
            "confirm_password": "password123",
            "submit": True,
        },
        follow_redirects=True,
    )

    assert b"Your account has been created, you can now log in" in response.data

    user = User.query.filter_by(username="testuser").first()
    assert user is not None


def test_login_user(client):
    """Test user login."""
    response = client.post(
        url_for("users.login"),
        data={"username": "testuser", "password": "password123", "submit": True},
        follow_redirects=True,
    )

    assert b"You are now logged in" in response.data


def test_logout_user(client):
    """Test user logout."""
    response = client.get(url_for("users.logout"), follow_redirects=True)
    assert b"You are now logged out" in response.data
