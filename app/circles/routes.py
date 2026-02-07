from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user

circles = Blueprint("circles", __name__)

@circles.route("/circles/create", methods=["GET"])
def create_circle():
    return redirect(url_for("main.not_implemented"))

