import random

from flask import Blueprint, render_template, request, current_app
from werkzeug.exceptions import HTTPException

from app.constants import MESSAGES_403, MESSAGES_404, MESSAGES_500
from app.http.errors import AppError
from app.http.responses import error_response

errors_bp = Blueprint("errors", __name__)


def get_random_message(error_list):
    return random.choice(error_list)

def wants_json_response() -> bool:
    """Use JSON for API routes and JSON-preferring clients, otherwise HTML"""
    if request.path.startswith("/api/"):
        return True

    best = request.accept_mimetypes.best
    if best is None:
        return False

    return (
        best == "application/json"
        and request.accept_mimetypes["application/json"]
        >= request.accept_mimetypes["text/html"]
    )

@errors_bp.app_errorhandler(AppError)
def handle_app_error(error: AppError):
    if wants_json_response():
        return error_response(
            message = error.message,
            error_code = error.error_code,
            status_code = error.status_code,
            details = error.details,
        )
    
    template = "errors/500.html"
    if error.status_code == 403:
        template = "errors/403.html"
    elif error.status_code == 404:
        template = "errors/404.html"
    return render_template(template, message=error.message), error.status_code

@errors_bp.app_errorhandler(HTTPException)
def handle_http_exception(error: HTTPException):
    if wants_json_response():
        return error_response(
            message = error.description,
            error_code = f"HTTP_{error.code}",
            status_code = error.code,
        )

    if error.code == 403:
        return render_template(
            "errors/403.html", message=get_random_message(MESSAGES_403)
        ), 403
    if error.code == 404:
        return render_template(
            "errors/404.html", message=get_random_message(MESSAGES_404)
        ), 404

    return render_template(
        "errors/500.html", message=get_random_message(MESSAGES_500)
    ), error.code

@errors_bp.app_errorhandler(Exception)
def handle_unexpected_exception(error: Exception):
    current_app.logger.exception("Unhandled exception: %s", error)

    if wants_json_response():
        return error_response(
            message="An unexpected error occurred",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500,
        )

    return render_template(
        "errors/500.html", message=get_random_message(MESSAGES_500)
    ), 500