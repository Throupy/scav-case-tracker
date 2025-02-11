import random

from flask import Blueprint, render_template

from app.constants import MESSAGES_403, MESSAGES_404, MESSAGES_500

errors = Blueprint("errors", __name__)


def get_random_message(error_list):
    return random.choice(error_list)

@errors.app_errorhandler(403)
def forbidden_error(error):
    return render_template(
        "errors/403.html",
        message=get_random_message(MESSAGES_403)
    ), 403

@errors.app_errorhandler(404)
def not_found_error(error):
    return render_template(
        "errors/404.html",
        message=get_random_message(MESSAGES_404)
    ), 403

@errors.app_errorhandler(500)
def internal_server_error(error):
    return render_template(
        "errors/500.html",
        message=get_random_message(MESSAGES_500)
    ), 403
