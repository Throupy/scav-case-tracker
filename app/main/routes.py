from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from flask_login import current_user, login_required

from sqlalchemy.sql import func

from app.constants import SCAV_CASE_TYPES, ACHIEVEMENT_METADATA
from app.models import ScavCase, TarkovItem, ScavCaseItem, User, UserAchievement
from app.main.utils import get_dashboard_data

main_bp = Blueprint("main", __name__)


@main_bp.route("/not-implemented")
def not_implemented():
    flash("This feature hasn't been implemented yet", "warning")
    return redirect(url_for("cases.dashboard"))





@main_bp.route("/search-items")
def search_items():
    """HTMX search route"""
    query = request.args.get("q")
    if len(query) < 2:
        return render_template("partials/item_list.html", items=[])
    items = TarkovItem.query.filter(TarkovItem.name.ilike(f"%{query}%")).limit(15).all()
    return render_template("partials/item_list.html", items=items)

