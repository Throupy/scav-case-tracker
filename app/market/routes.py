# app/market/routes.py (refactored)
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from app.services.market_service import MarketService

market = Blueprint("market", __name__, url_prefix="/market/")
market_service = MarketService()


# HTMX routes
@market.route("/search-items")
def search_items():
    query = request.args.get("q", "").strip()
    results = market_service.search_items(query)
    
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
    price_data = market_service.get_item_price_data(tarkov_item_id)
    
    if "error" in price_data:
        return f"<span class='text-danger'>{price_data['error']}</span>"

    return f"""
        <div class="col-2">
            <div class="card-body p-2"> 
                <h6 class="font-weight-bold card-title mb-0">₽{price_data['high_price']:,}</h6> 
            </div>
        </div>
        <div class="col-2">
            <div class="card-body p-2"> 
                <h6 class="font-weight-bold {price_data['change_48h_colour']} card-title mb-0">{price_data['change_48h_percent']:.2f}%</h6> 
            </div>
        </div>
        <div class="col-2">
            <div class="card-body p-2">
                <h6 class="card-title mb-0">    
                    <span><strong>₽{price_data['avg_price_24h']:,}</strong></span>
                </h6>
            </div>
        </div>
    """


# Regular routes
@market.route("/track-item/<string:tarkov_item_id>", methods=["POST"])
@login_required
def track_item(tarkov_item_id: str):
    success = market_service.track_item_for_user(current_user, tarkov_item_id)
    
    # Return JavaScript for HTMX to handle modal and reload
    return """
    <script>
        $('#trackItemModal').modal('hide');
        setTimeout(() => location.reload(), 500);
    </script>
    """


@market.route("/untrack-item/<string:tarkov_item_id>", methods=["DELETE"])
@login_required  
def untrack_item(tarkov_item_id: str):
    success = market_service.untrack_item_for_user(current_user, tarkov_item_id)
    
    # Return JavaScript for HTMX to handle modal and reload
    return """
    <script>
        $('#trackItemModal').modal('hide');
        setTimeout(() => location.reload(), 500);
    </script>
    """


@market.route("/")
@login_required
def index():
    tracked_items = market_service.get_user_tracked_items(current_user)

    # If it's an HTMX request, return partial template
    if request.headers.get("HX-Request"):
        return render_template("partials/market_tracked_items.html", tracked_items=tracked_items)

    return render_template("market.html", tracked_items=tracked_items)