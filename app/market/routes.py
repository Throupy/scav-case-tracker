from flask import Blueprint, render_template

market = Blueprint("market", __name__, url_prefix="/market/")

@market.route("/")
def index():
    return render_template("market.html")