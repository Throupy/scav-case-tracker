import json
import os
import threading

from flask import Flask

from app.config import Config
from app.discord_bot.discord_bot import intents, ImageDownloaderClient
from app.main.routes import main
from app.api.routes import api
from app.users.routes import users
from app.quiz.routes import _quiz as quiz
from app.cases.routes import cases
from app.models import User, TarkovItem, WeaponAttachment, Entry
from app.filters import timeago
from app.cases.utils import get_price
from app.extensions import db, migrate, login_manager, bcrypt


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    app.jinja_env.filters['timeago'] = timeago

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "users.login"
    login_manager.login_message_category = "danger"

    bcrypt.init_app(app)

    with app.app_context():
        db.create_all()

        # Ensure the following runs only if the table is empty
        if User.query.count() == 0:
            print("[DEBUG] Adding Discord Bot Application user...")
            # add a user for the discord bot
            hashed_password = bcrypt.generate_password_hash(
                os.getenv("DISCORD_BOT_USER_PASSWORD")
            ).decode("utf-8")
            discord_bot_user = User(
                id=1,
                username="Discord Bot",
                password=hashed_password,
                image_file="discord-pfp.png",
            )
            db.session.add(discord_bot_user)

        if TarkovItem.query.count() == 0:
            print("[DEBUG] Adding Tarkov items...")
            with open("../output.json", "r") as f:
                item_data = json.load(f)
                for item_name, tarkov_id in item_data.items():
                    # Add items only if they don't already exist
                    if not TarkovItem.query.filter_by(tarkov_id=tarkov_id).first():
                        item = TarkovItem(name=item_name, tarkov_id=tarkov_id)
                        db.session.add(item)

        if WeaponAttachment.query.count() == 0:
            print("[DEBUG] Populating Tarkov weapon attachments...")
            with open("../attachments.json", "r") as f:
                attachment_data = json.load(f)
                c = 0
                for _attachment in attachment_data:
                    tarkov_item = TarkovItem.query.filter_by(
                        name=_attachment["name"]
                    ).first()

                    if tarkov_item:
                        attachment = WeaponAttachment(
                            id=tarkov_item.id,
                            recoil_modifier=_attachment.get("recoilModifier"),
                            ergonomics_modifier=_attachment.get("ergonomicsModifier"),
                        )
                        c += 1
                        db.session.add(attachment)

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
    app.register_blueprint(quiz)
    app.register_blueprint(cases)

    if app.config["START_DISCORD_BOT"] and (
        not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    ):
        with app.app_context():

            def run_discord_bot():
                discord_bot = ImageDownloaderClient(
                    download_dir=app.config["DISCORD_DOWNLOAD_DIR"],
                    channel_id=int(app.config["DISCORD_CHANNEL_ID"]),
                    intents=intents,
                )
                discord_bot.run(os.getenv("DISCORD_TOKEN"))

            discord_thread = threading.Thread(target=run_discord_bot)
            discord_thread.start()

    return app
