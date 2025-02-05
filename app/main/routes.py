from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from sqlalchemy.sql import func

from app.config import SCAV_CASE_TYPES
from app.models import Entry, TarkovItem, EntryItem, User
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
        entries=Entry.query.all(),
        **dashboard_data 
    )

@main.route("/search-items")
def search_items():
    query = request.args.get("q")
    if len(query) < 2:
        return render_template("partials/item_list.html", items=[])
    items = TarkovItem.query.filter(TarkovItem.name.ilike(f"%{query}%")).all()
    return render_template("partials/item_list.html", items=items)
