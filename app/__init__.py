import json
import os
import threading

from flask import Flask

from app.config import ConfigClass
from app.constants import CATEGORY_MAPPING
from app.discord_bot.discord_bot import intents, ImageDownloaderClient
from app.main.routes import main
from app.api.routes import api
from app.users.routes import users
from app.market.routes import market
from app.errors.routes import errors
from app.quiz.routes import _quiz as quiz
from app.circles.routes import circles
from app.cases.routes import cases
from app.models import User, TarkovItem, WeaponAttachment, ScavCase
from app.filters import timeago, get_item_cdn_image_url, get_category_cdn_image_url
from app.cases.utils import get_price
from app.extensions import db, migrate, login_manager, bcrypt


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_app(config_class=ConfigClass):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.jinja_env.filters["timeago"] = timeago
    app.jinja_env.filters["get_category_cdn_image_url"] = get_category_cdn_image_url
    app.jinja_env.filters["get_item_cdn_image_url"] = get_item_cdn_image_url

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

        # This is very much for ad-hoc database operations... no real logic here, I just change
        # it to do whatever I need doing at the time.
        if TarkovItem.query.count() == 0 or app.config["REFRESH_TARKOV_ITEMS"]:
            print("[DEBUG] Adding Tarkov items...")
            with open("../all_items.json", "r") as f:
                item_data = json.load(f)
                for item in item_data["items"]:
                    tarkov_id, item_name, subcategory = item.values()
                    # put items in a broader category - the tarkov ones are so bad!!!
                    broad_category = CATEGORY_MAPPING.get(subcategory, "Unknown")
                    if broad_category == "Unknown":
                        print(
                            f"[!] Not sure about {item_name}. Subcategory is {subcategory}"
                        )
                    existing_item = TarkovItem.query.filter_by(
                        tarkov_id=tarkov_id
                    ).first()
                    # Add items only if they don't already exist
                    if existing_item:
                        if existing_item.category != broad_category:
                            existing_item.category = broad_category
                            print(
                                f"[UPDATE] {tarkov_id}: Changing category from {existing_item.category} to {broad_category}"
                            )
                    else:
                        item = TarkovItem(
                            name=item_name, tarkov_id=tarkov_id, category=broad_category
                        )
                        db.session.add(item)
                        print(f"[*] Added Item with name: {item_name}")

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
                scav_case = ScavCase(cost=cost, _return=_return, type=_type, user_id=1)
                db.session.add(scav_case)

        db.session.commit()

    app.register_blueprint(main)
    app.register_blueprint(api)
    app.register_blueprint(users)
    app.register_blueprint(market)
    app.register_blueprint(quiz)
    app.register_blueprint(errors)
    app.register_blueprint(cases)
    app.register_blueprint(circles)

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
