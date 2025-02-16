from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from flask_login import current_user

from sqlalchemy.sql import func

from app.constants import SCAV_CASE_TYPES, ACHIEVEMENT_METADATA
from app.models import ScavCase, TarkovItem, ScavCaseItem, User, UserAchievement
from app.main.utils import get_dashboard_data

main = Blueprint("main", __name__)


@main.route("/not-implemented")
def not_implemented():
    flash("This feature hasn't been implemented yet", "warning")
    return redirect(url_for("main.dashboard"))


@main.route("/")
@main.route("/dashboard")
def dashboard():
    dashboard_data = get_dashboard_data()

    return render_template(
        "dashboard.html",
        scav_case_types=SCAV_CASE_TYPES,
        scav_cases=ScavCase.query.all(),
        **dashboard_data,
    )


@main.route("/search-items")
def search_items():
    """HTMX search route"""
    query = request.args.get("q")
    if len(query) < 2:
        return render_template("partials/item_list.html", items=[])
    items = TarkovItem.query.filter(TarkovItem.name.ilike(f"%{query}%")).limit(15).all()
    return render_template("partials/item_list.html", items=items)

@main.route("/achievements")
def achievements():
    user_achievements = UserAchievement.query.filter_by(user_id=current_user.id).all()
    unlocked = {a.achievement_name: a.achieved_at for a in user_achievements}
    # unlocked first, most recent first
    sorted_achievements = sorted(
        ACHIEVEMENT_METADATA.items(), 
        key=lambda a: (-unlocked[a[0]].timestamp() if a[0] in unlocked else float("inf"))
    )
    return render_template("achievements.html", achievements=sorted_achievements, unlocked=unlocked)