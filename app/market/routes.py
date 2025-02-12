from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from app.models import TarkovItem
from app.extensions import db
from app.cases.utils import get_price

market = Blueprint("market", __name__, url_prefix="/market/")

# HMTX routes
@market.route("/search-items")
def search_items():
    query = request.args.get("q", "").strip()
    if not query:
        return ""

    results = TarkovItem.query.filter(
        TarkovItem.name.ilike(f"%{query}%")
    ).limit(10).all()

    if not results:
        return "<div class='list-group-item text-muted'>No items found.</div>"

    return "".join([
        f"""
        <button class="list-group-item list-group-item-action"
                hx-post="/market/track-item/{item.tarkov_id}"
                hx-trigger="click"
                hx-swap="outerHTML">
            {item.name}
        </button>
        """
        for item in results
    ])

@market.route("/get-price/<string:tarkov_item_id>", methods=["GET"])
def get_price_htmx(tarkov_item_id: str) -> str:
    price = get_price(tarkov_item_id)
    return f"<span>₽{price:,} </span>"

# Regular routes
@market.route("/track-item/<string:tarkov_item_id>", methods=["POST"])
@login_required
def track_item(tarkov_item_id: str):
    item = TarkovItem.query.filter_by(tarkov_id=tarkov_item_id).first()

    if item not in current_user.tracked_items:
        current_user.tracked_items.append(item)
        db.session.commit()

    # force a page reload by returnin JS
    return """
    <script>
        $('#trackItemModal').modal('hide');
        setTimeout(() => location.reload(), 500);
    </script>
    """

@market.route("/untrack-item/<string:tarkov_item_id>", methods=["DELETE"])
@login_required
def untrack_item(tarkov_item_id: str):
    item = TarkovItem.query.filter_by(tarkov_id=tarkov_item_id).first()

    if item in current_user.tracked_items:
        current_user.tracked_items.remove(item)
        db.session.commit()

    return """
    <script>
        $('#trackItemModal').modal('hide');
        setTimeout(() => location.reload(), 500);
    </script>
    """

@market.route("/")
@login_required
def index():
    return render_template("market.html")