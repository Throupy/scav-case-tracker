import pytest

from app import create_app
from app.extensions import db
from tests.config import TestConfig


@pytest.fixture(scope="module")
def app():
    """Create and configure a new app instance for each test."""
    app = create_app(config_class=TestConfig)
    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",  # Use in-memory database for tests
            "SECRET_KEY": "test_secret_key",  # Ensure a secret key is set for session management
        }
    )

    with app.app_context():
        db.create_all()  # Create tables
        yield app
        db.drop_all()  # Drop tables after tests


@pytest.fixture(scope="module")
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture(scope="function", autouse=True)
def session(app):
    """Ensure a clean database for each test."""
    with app.app_context():
        db.session.begin_nested()  # Start a nested transaction
        yield db.session
        db.session.rollback()  # Rollback the transaction after each test
