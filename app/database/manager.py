"""Contains database intiialisation class and methods. The methods herein are primarily used for ad-hoc database
operations and primarily used for testing... Many of the functions are legacy and generally unused"""
import random
import json
import os

from app.extensions import db, bcrypt
from app.models import User, TarkovItem, WeaponAttachment, ScavCase
from app.constants import CATEGORY_MAPPING, DISCORD_BOT_USER_USERNAME
from app.cases.utils import get_price

class DatabaseManager:
    """Handles database initialisation and seeding operations, if enabled"""
    def __init__(self, app=None) -> None:
        self.app = app

    def init_app(self, app) -> None:
        """Initialise with flask app instance"""
        self.app = app
    
    def create_tables(self) -> None:
        """Create all database tables"""
        with self.app.app_context():
            db.create_all()

    def seed_discord_bot_user(self):
        """Create the user for the discord bot, if it doesn't exist"""
        # check if the user already exists
        if User.query.filter_by(username=DISCORD_BOT_USER_USERNAME).first() is not None:
            return
        self.app.logger.info("Creating Discord Bot user...")

        # retrive the bot password secret
        password = os.getenv("DISCORD_BOT_USER_PASSWORD")
        if not password:
            self.app.logger.error("DISCORD_BOT_USER_PASSWORD environment variable not set, cannot create user")
            return

        hashed_password = bcrypt.generate_password_hash(
            password
        ).decode("utf-8")
        
        discord_bot_user = User(
            username="Discord Bot",
            password=hashed_password,
            image_file="discord-pfp.png",
        )
        db.session.add(discord_bot_user)
        db.session.commit()
        self.app.logger.info("Discord Bot user created successfully")

    def seed_tarkov_items(self, force_refresh=False):
        """Load tarkov items from JSON file - legacy function"""
        # if there are already some items in the DB, and we aren't forcing the refresh
        if TarkovItem.query.count() > 0 and not force_refresh:
            return

        items_file = self._get_data_file_path("all_items.json")
        self.app.logger.info(f"Loading Tarkov items from {items_file}...")

        try:
            with open(items_file, "r") as f:
                item_data = json.load(f)

            for item in item_data["items"]:
                self._process_tarkov_item(item)

            db.session.commit()
            self.app.logger.info(f"Successfully loaded {len(item_data["items"])} Tarkov Items")

        except FileNotFoundError:
            self.app.logger.warning(f"Items file not found: {items_file}")
        except Exception as e:
            self.app.logger.error(f"Failed to load tarkov items: {e}")
            db.session.rollback()

    def seed_weapon_attachments(self, force_refresh=False):
        """Load weapon attachments from JSON file - legacy function"""
        # only run if empty
        if WeaponAttachment.query.count() > 0 and not force_refresh:
            return

        attachments_file = self._get_data_file_path("attachments.json")
        self.app.logger.info(f"Loading weapon attachments from {attachments_file}...")

        try:
            with open(attachments_file, "r") as f:
                attachment_data = json.load(f)

            count = 0
            for _attachment in attachment_data:
                if self._process_weapon_attachment(_attachment):
                    count += 1
            
            db.session.commit()
            self.app.logger.info(f"Successfully loaded {count} weapon attachments")
        except FileNotFoundError:
            self.app.logger.warning(f"Attachments file not found: {attachments_file}")
        except Exception as e:
            self.app.logger.error(f"Failed to load weapon attachments: {e}")
            db.session.rollback()

    def seed_sample_entries(self, count: int) -> None:
        """Generate sample scav case entries for testing"""
        self.app.logger.info(f"Generating {count} sample scav case entries...")

        costs = {
            2500: "₽2500",
            15000: "₽15000", 
            95000: "₽95000",
            get_price("5d1b376e86f774252519444e"): "Moonshine",
            get_price("5c12613b86f7743bbe2c3f76"): "Intelligence",
        }

        for _ in range(count):
            # generate a random 'type' of case e.g. moonshine
            cost = random.choice(list(costs.keys()))
            # generate a random return value, somwhere between 50% and 150% of the cost
            base_return = random.uniform(cost * 0.5, cost * 1.5)
            # 20% chance for an extra high return - between 90% and 550%
            if random.choice(range(5)) == 3:
                base_return = random.uniform(cost * 0.9, cost * 5.5)
            
            scav_case = ScavCase(
                cost = cost,
                _return = base_return,
                type = costs[cost],
                user_id = 1
            )
            db.session.add(scav_case)
        
        db.session.commit()
        self.app.logger.info(f"Successfully generated {count} sample entries")

    def _get_data_file_path(self, filename: str) -> str:
        """Get the full path for a data file"""
        # look for data files relative to the app root
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        return os.path.join(base_dir, filename)

    def _process_tarkov_item(self, item_json: str) -> None:
        """Process a single tarkov item, passed in as JSON"""
        tarkov_id, item_name, subcategory = item_json.values()
        # actual item categories are stupid, map them to something sensible
        broad_category = CATEGORY_MAPPING.get(subcategory, "Unknown")

        # we will still add it to the DB, but generate some warning
        if broad_category == "Unknown":
            self.app.logger.warning(f"Unknown category for {item_name}: {subcategory}")

        # does this item already exist in the database? 
        existing_item = TarkovItem.query.filter_by(tarkov_id=tarkov_id).first()
    
        # if the item exists, check that the category uses the new 'broad' mappings
        if existing_item:
            if existing_item.category != broad_category:
                existing_item.category = broad_category
                self.app.logger.info(f"{item_name} ({tarkov_id}): Category changed to {broad_category}")
        else:
            # otherwise, create the item
            new_item = TarkovItem(
                name=item_name,
                tarkov_id=tarkov_id, 
                category=broad_category
            )
            db.session.add(new_item)

    def _process_weapon_attachment(self, attachment_json: str) -> bool:
        """Process a single weapon attachment"""
        tarkov_item = TarkovItem.query.filter_by(
            name=attachment_json["name"]
        ).first()
        
        if not tarkov_item:
            return False
            
        attachment = WeaponAttachment(
            id=tarkov_item.id,
            recoil_modifier=attachment_json.get("recoilModifier"),
            ergonomics_modifier=attachment_json.get("ergonomicsModifier"),
        )
        db.session.add(attachment)
        return True

# singleton instance
db_manager = DatabaseManager()