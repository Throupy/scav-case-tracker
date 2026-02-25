from functools import wraps

from flask import abort, current_app, request
from flask_login import login_required, current_user


def superuser_required(f):
    """Requires login AND is_superuser=True. Use instead of @login_required for admin routes."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_superuser:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def api_key_required(f):
    """Require a valid API key in the Authorization: Bearer <key> header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = current_app.config.get("API_KEY")
        if not api_key:
            current_app.logger.error("API_KEY is not configured")
            abort(500)
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer ") or auth_header[7:] != api_key:
            abort(401)
        return f(*args, **kwargs)
    return decorated
