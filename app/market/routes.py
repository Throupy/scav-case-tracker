from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from app.models import TarkovItem
from app.extensions import db
from app.cases.utils import get_price
from app.market.utils import get_market_information

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
    market_data = get_market_information(tarkov_item_id)
    print(market_data)
    if not market_data or "data" not in market_data or not market_data["data"]["items"]:
        return "<span class='text-danger'>Price unavailable</span>"

    item = market_data["data"]["items"][0]
    high_price = item.get("high24hPrice", "N/A")
    avg_price_24h = item.get("avg24hPrice", "N/A")
    change_48h_percent = float(item.get("changeLast48hPercent", "0"))

    change_48h_colour = "text-success" if change_48h_percent > 0 else "text-danger"

    return f"""
        <div class="col-2">
            <div class="card-body p-2"> 
                <h6 class="font-weight-bold card-title mb-0">₽{high_price:,}</h6> 
            </div>
        </div>
        <div class="col-2">
            <div class="card-body p-2"> 
                <h6 class="font-weight-bold {change_48h_colour} card-title mb-0">{change_48h_percent:.2f}%</h6> 
            </div>
        </div>
        <div class="col-2">
            <div class="card-body p-2">
                <h6 class="card-title mb-0">    
                    <span><strong>₽{avg_price_24h:,}</strong> 
                </h6>
            </div>
        </div>
    """

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