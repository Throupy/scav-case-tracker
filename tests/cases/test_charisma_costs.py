import json
from unittest.mock import patch

from app.extensions import bcrypt, db
from app.models import ScavCase, TarkovItem, User
from app.services.scav_case_service import ScavCaseService


def test_charisma_changes_only_future_static_case_costs(app):
    with app.test_request_context("/"):
        user = User(
            username="charisma_costs",
            password=bcrypt.generate_password_hash("Password123!").decode("utf-8"),
            max_level_charisma=True,
        )
        loot = TarkovItem(
            name="Charisma Test Loot",
            tarkov_id="charisma-test-loot",
            category="Barter Items",
        )
        db.session.add_all([user, loot])
        db.session.flush()

        service = ScavCaseService()
        items = json.dumps([
            {"id": loot.tarkov_id, "name": loot.name, "quantity": 1}
        ])

        with patch(
            "app.services.scav_case_service.get_prices",
            return_value={loot.tarkov_id: 1000},
        ):
            result = service.create_scav_case("\u20bd95000", None, items, user)

        discounted = db.session.get(ScavCase, result["scav_case_id"])
        assert discounted.type == "\u20bd95000"
        assert discounted.cost == 85500

        user.max_level_charisma = False
        db.session.commit()
        assert db.session.get(ScavCase, discounted.id).cost == 85500

        with patch(
            "app.services.scav_case_service.get_prices",
            return_value={loot.tarkov_id: 1000},
        ):
            result = service.create_scav_case("\u20bd95000", None, items, user)

        standard = db.session.get(ScavCase, result["scav_case_id"])
        assert standard.type == "\u20bd95000"
        assert standard.cost == 95000


def test_charisma_does_not_discount_dynamic_case_costs(app):
    with app.test_request_context("/"):
        user = User(
            username="charisma_dynamic",
            password=bcrypt.generate_password_hash("Password123!").decode("utf-8"),
            max_level_charisma=True,
        )
        loot = TarkovItem(
            name="Dynamic Test Loot",
            tarkov_id="dynamic-test-loot",
            category="Barter Items",
        )
        db.session.add_all([user, loot])
        db.session.flush()

        service = ScavCaseService()
        items = json.dumps([
            {"id": loot.tarkov_id, "name": loot.name, "quantity": 1}
        ])
        prices = {
            loot.tarkov_id: 1000,
            "5d1b376e86f774252519444e": 321000,
        }
        with patch("app.services.scav_case_service.get_prices", return_value=prices):
            result = service.create_scav_case("Moonshine", None, items, user)

        scav_case = db.session.get(ScavCase, result["scav_case_id"])
        assert scav_case.cost == 321000
