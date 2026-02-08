from logging.config import dictConfig

from flask import Flask

from app.config import ConfigClass
from app.extensions import db, migrate, login_manager, bcrypt
from app.database.manager import db_manager
from app.discord_bot.manager import discord_manager
from app.models import User


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_app(config_class=ConfigClass):
    """App factory for creating flask app instance"""
    # as per flask best-practice, set up logging before instantiating the app
    # https://flask.palletsprojects.com/en/stable/logging/
    _configure_logging()

    app = Flask(__name__)
    app.config.from_object(config_class)

    _init_extensions(app)
    _register_template_filters(app)
    _register_blueprints(app)
    _init_database(app)
    _init_discord_bot(app)

    return app

def _configure_logging():
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,

        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(name)s: %(message)s",
            }
        },

        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
                "formatter": "default",
            }
        },

        "root": {
            "level": "INFO",
            "handlers": ["wsgi"],
        },
    })

def _init_extensions(app: Flask) -> None:
    # flask-sqlalchemy
    db.init_app(app)
    # flask-migrate
    migrate.init_app(app, db)
    # flask-login
    login_manager.init_app(app)
    login_manager.login_view = "users.login"
    login_manager.login_message_category = "danger"
    # flask-bcrypt
    bcrypt.init_app(app)

    # custom managers
    db_manager.init_app(app)
    discord_manager.init_app(app)

def _register_template_filters(app: Flask) -> None:
    """Register jinja2 template filters"""
    from app.filters import timeago, get_item_cdn_image_url, get_category_cdn_image_url

    app.jinja_env.filters["timeago"] = timeago
    app.jinja_env.filters["get_item_cdn_image_url"] = get_item_cdn_image_url
    app.jinja_env.filters["get_category_cdn_image_url"] = get_category_cdn_image_url

def _register_blueprints(app: Flask) -> None:
    """Register application blueprints (route mappings)"""
    from app.main.routes import main
    from app.api.routes import api
    from app.users.routes import users
    from app.market.routes import market
    from app.errors.routes import errors
    from app.quiz.routes import _quiz as quiz
    from app.circles.routes import circles
    from app.cases.routes import cases
    from app.leaderboards.routes import leaderboards
    
    app.register_blueprint(main)
    app.register_blueprint(api)
    app.register_blueprint(users)
    app.register_blueprint(market)
    app.register_blueprint(quiz)
    app.register_blueprint(errors)
    app.register_blueprint(cases)
    app.register_blueprint(circles)
    app.register_blueprint(leaderboards)

def _init_database(app: Flask) -> None:
    """Initialise and optionally, seed, the database"""
    with app.app_context():
        app.logger.info("Initialising database...")
        db_manager.create_tables()

        db_manager.seed_discord_bot_user()
        db_manager.seed_tarkov_items(app.config.get("REFRESH_TARKOV_ITEMS", False))
        db_manager.seed_weapon_attachments(app.config.get("REFRESH_TARKOV_ITEMS", False))

        if app.config.get("SEED_ENTRIES"):
            count = app.config.get("SEED_ENTRIES_COUNT", 100)
            db_manager.seed_sample_entries(count)

        app.logger.info("Database initialisation complete")

def _init_discord_bot(app):
    """initialise the discord bot if configured to do so"""
    discord_manager.start_bot()