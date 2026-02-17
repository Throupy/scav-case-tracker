import os
from logging.config import dictConfig

from flask import Flask

from app.config import ConfigClass
from app.constants import SCAV_CASE_TYPES
from app.extensions import db, migrate, login_manager, bcrypt, csrf
from app.database.manager import db_manager
from app.discord_bot.manager import discord_manager
from app.models import User
from app.filters import timeago, get_item_cdn_image_url, get_category_cdn_image_url

from app.main.routes import main_bp
from app.api.routes import api_bp
from app.users.routes import users_bp
from app.market.routes import market_bp
from app.errors.routes import errors_bp
from app.quiz.routes import quiz_bp
from app.circles.routes import circles_bp
from app.cases.routes import cases_bp
from app.leaderboards.routes import leaderboards_bp
from app.achievements.routes import achievements_bp

def _is_flask_cli():
    return os.environ.get("FLASK_RUN_FROM_CLI") == "true"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def create_app(config_class=ConfigClass):
    """App factory for creating flask app instance"""
    # as per flask best-practice, set up logging before instantiating the app
    # https://flask.palletsprojects.com/en/stable/logging/
    _configure_logging()

    app = Flask(__name__)
    app.config.from_object(config_class)

    _init_extensions(app)
    _register_template_filters(app)
    _register_template_context(app)
    _register_blueprints(app)
    _init_database(app)
    _init_discord_bot(app)

    return app

def _configure_logging():
    # Create log dir if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)

    # this 1 call basically overwrwites the logging configuration with the JSON param
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,

        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "[%(asctime)s] %(levelname)s in %(name)s [%(pathname)s:%(lineno)d]: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },

        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
                "formatter": "default",
            },
            # traditional 'app.log' (or 'access.log'...)
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "detailed",
                "filename": os.path.join(log_dir, "app.log"),
                "maxBytes": 10485760,  # 10 MB
                # this is like NGINX capability, create access.log, access.log.1, access.log.2 (to 3)
                # of 'rotating' backups of the log file
                "backupCount": 3,
                "encoding": "utf8"
            },
            # separated error.log
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler", 
                "level": "ERROR",
                "formatter": "detailed",
                "filename": os.path.join(log_dir, "error.log"),
                "maxBytes": 10485760,  # 10 MB
                "backupCount": 3,
                "encoding": "utf8"
            }
        },

        "root": {
            "level": "INFO",
            "handlers": ["wsgi", "file", "error_file"],
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
    # flask-wtf csrfprotect
    csrf.init_app(app)

    # custom managers
    db_manager.init_app(app)
    discord_manager.init_app(app)

def _register_template_filters(app: Flask) -> None:
    """Register jinja2 template filters"""
    app.jinja_env.filters["timeago"] = timeago
    app.jinja_env.filters["get_item_cdn_image_url"] = get_item_cdn_image_url
    app.jinja_env.filters["get_category_cdn_image_url"] = get_category_cdn_image_url

def _register_template_context(app: Flask) -> None:
    # registers globals for templates. SCAV_CASE_TYPES is needed throughout a number of templates,
    # and it's safe to make global, so let's do it.
    @app.context_processor
    def inject_template_globals():
        return {"scav_case_types": SCAV_CASE_TYPES}

def _register_blueprints(app: Flask) -> None:
    """Register application blueprints (route mappings)"""
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(market_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(errors_bp)
    app.register_blueprint(cases_bp)
    app.register_blueprint(circles_bp)
    app.register_blueprint(leaderboards_bp)
    app.register_blueprint(achievements_bp)

def _init_database(app: Flask) -> None:
    """Initialise and optionally, seed, the database"""
    with app.app_context():
        app.logger.info("Initialising database...")
        if _is_flask_cli():
            app.logger.info("Skipping DB seeding for Flask CLI commands")
            return

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