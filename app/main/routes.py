from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
)

from app.config import SCAV_CASE_TYPES
from app.models import Entry, TarkovItem

main = Blueprint("main", __name__)


@main.route("/not-implemented")
def not_implemented():
    flash("This feature hasn't been implemented yet", "warning")
    return redirect(request.referrer)


@main.route("/")
@main.route("/dashboard")
def dashboard():
    entries = Entry.query.all()
    return render_template(
        "dashboard.html", scav_case_types=SCAV_CASE_TYPES, entries=entries
    )


@main.route("/search-items")
def search_items():
    query = request.args.get("q")
    if len(query) < 2:
        return render_template("partials/item_list.html", items=[])
    items = TarkovItem.query.filter(TarkovItem.name.ilike(f"%{query}%")).all()
    return render_template("partials/item_list.html", items=items)
