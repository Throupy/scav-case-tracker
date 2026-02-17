import pytest
from werkzeug.exceptions import NotFound

from app.models import User, ScavCase
from app.extensions import db, bcrypt
from app.services.scav_case_service import ScavCaseService


@pytest.fixture
def service():
    return ScavCaseService()


def _make_user(app, username):
    """Create a user directly in the DB and return their ID."""
    with app.app_context():
        hashed = bcrypt.generate_password_hash("testpass123!").decode("utf-8")
        user = User(username=username, password=hashed)
        db.session.add(user)
        db.session.commit()
        return user.id


def _make_case(app, user_id, case_type="₽2500", cost=2500.0, return_val=5000.0):
    """Create a ScavCase in the DB and return its ID."""
    with app.app_context():
        sc = ScavCase(
            user_id=user_id,
            type=case_type,
            cost=cost,
            _return=return_val,
            number_of_items=0,
        )
        db.session.add(sc)
        db.session.commit()
        return sc.id


def test_get_case_by_id_or_404_found(app, service):
    """Returns the ScavCase when a valid ID is provided."""
    user_id = _make_user(app, "svc_found_user")
    case_id = _make_case(app, user_id)
    with app.app_context():
        result = service.get_case_by_id_or_404(case_id)
        assert result.id == case_id


def test_get_case_by_id_or_404_not_found(app, service):
    """Raises 404 when no case exists for the given ID."""
    with app.app_context():
        with pytest.raises(NotFound):
            service.get_case_by_id_or_404(999999)


def test_delete_scav_case(app, service):
    """Deleting a case removes it from the database."""
    user_id = _make_user(app, "svc_del_user")
    case_id = _make_case(app, user_id)
    with app.app_context():
        sc = service.get_case_by_id_or_404(case_id)
        result = service.delete_scav_case(sc)
        assert result is True
        assert service.get_case_by_id(case_id) is None


def test_generate_dashboard_data_returns_expected_keys(app, service):
    """Dashboard data dict always contains all required metric keys."""
    with app.app_context():
        data = service.generate_dashboard_data()
        for key in ("total_cases", "total_cost", "total_return", "total_profit"):
            assert key in data
            assert isinstance(data[key], (int, float))


def test_generate_dashboard_data_with_cases(app, service):
    """Dashboard totals correctly aggregate across all cases."""
    user_id = _make_user(app, "svc_dash_user")
    # profit: 5000 - 2500 = 2500, and 3000 - 2500 = 500 → total profit = 3000
    _make_case(app, user_id, cost=2500.0, return_val=5000.0)
    _make_case(app, user_id, cost=2500.0, return_val=3000.0)
    with app.app_context():
        data = service.generate_dashboard_data()
        assert data["total_cases"] >= 2
        assert data["total_cost"] >= 5000.0
        assert data["total_return"] >= 8000.0
        assert data["total_profit"] >= 3000.0


def test_get_cases_by_type_all(app, service):
    """get_cases_by_type('all') returns cases of every type."""
    user_id = _make_user(app, "svc_typeall_user")
    _make_case(app, user_id, case_type="₽2500")
    _make_case(app, user_id, case_type="Moonshine")
    with app.app_context():
        cases = service.get_cases_by_type("all")
        types = {c.type for c in cases}
        assert "₽2500" in types
        assert "Moonshine" in types


def test_get_cases_by_type_filtered(app, service):
    """get_cases_by_type with a specific type returns only that type."""
    user_id = _make_user(app, "svc_typeflt_user")
    _make_case(app, user_id, case_type="₽2500")
    _make_case(app, user_id, case_type="Moonshine")
    with app.app_context():
        cases = service.get_cases_by_type("₽2500")
        assert len(cases) >= 1
        assert all(c.type == "₽2500" for c in cases)


def test_get_cases_by_type_items_eager_loaded(app, service):
    """get_cases_by_type eagerly loads items, preventing N+1 queries."""
    user_id = _make_user(app, "svc_eager_user")
    _make_case(app, user_id)
    with app.app_context():
        cases = service.get_cases_by_type("all")
        assert len(cases) >= 1
        # Accessing .items should not trigger additional queries (already loaded)
        # sqlalchemy marks loaded collections with a 'loaded' flag - check it's not lazy
        from sqlalchemy import inspect as sa_inspect
        for sc in cases:
            state = sa_inspect(sc)
            assert "items" not in state.unloaded, "items relationship should be eagerly loaded"
