import json

from flask import Flask

from app.config import Config
from app.routes import main
from app.api.routes import api
from app.users.routes import users
from app.models import User, TarkovItem, Entry
from app.utils import get_price
from app.extensions import db, migrate, login_manager, bcrypt


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "users.login"
    login_manager.login_message_category = "danger"

    bcrypt.init_app(app)

    with app.app_context():
        db.create_all()

        if TarkovItem.query.count() == 0:  # Ensure this runs only if the table is empty
            with open("../output.json", "r") as f:
                item_data = json.load(f)
                for item_name, tarkov_id in item_data.items():
                    # Add items only if they don't already exist
                    if not TarkovItem.query.filter_by(tarkov_id=tarkov_id).first():
                        item = TarkovItem(name=item_name, tarkov_id=tarkov_id)
                        db.session.add(item)

        if app.config["SEED_ENTRIES"]:
            print(
                f"[*] app.config['SEED_ENTRIES'] is true, adding {app.config['SEED_ENTRIES_COUNT']} entrie(s)."
            )
            import random

            costs = {
                2500: "₽2500",
                15000: "₽15000",
                95000: "₽95000",
                get_price("5d1b376e86f774252519444e"): "Moonshine",
                get_price("5c12613b86f7743bbe2c3f76"): "Intelligence",
            }

            for x in range(app.config["SEED_ENTRIES_COUNT"]):
                cost = random.choice(list(costs.keys()))
                _return = random.uniform(cost * 0.5, cost * 1.5)
                if random.choice(range(5)) == 3:
                    _return = random.uniform(cost * 0.9, cost * 5.5)
                _type = costs[cost]
                entry = Entry(cost=cost, _return=_return, type=_type, user_id=1)
                db.session.add(entry)

        db.session.commit()

    app.register_blueprint(main)
    app.register_blueprint(api)
    app.register_blueprint(users)

    return app
