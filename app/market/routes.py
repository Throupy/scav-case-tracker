# app/market/routes.py (refactored)
from flask import Blueprint, render_template, request, flash
from flask_login import login_required, current_user

from app.services.market_service import MarketService

market_bp = Blueprint("market", __name__)
market_service = MarketService()


# HTMX routes
@market_bp.route("/market/search-items")
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


@market_bp.route("/market/get-price/<string:tarkov_item_id>", methods=["GET"])
def get_price_htmx(tarkov_item_id: str) -> str:
    price_data = market_service.get_item_price_data(tarkov_item_id)
    if "error" in price_data:
        return f"<span class='text-danger'>{price_data['error']}</span>"

    return f"""
    <div class="col-7">
        <div class="row align-items-center">

            <div class="col-4">
                <h6 class="font-weight-bold mb-0">
                    ₽{price_data['avg_price_24h']:,}
                    <span class="badge badge-pill badge-primary ml-2">
                        {price_data['highest_vendor']}
                    </span>
                </h6>
            </div>

            <div class="col-4">
                <h6 class="font-weight-bold mb-0">
                    ₽{price_data['low_price']:,}
                    <span class="badge badge-pill badge-danger ml-2">
                        {price_data['lowest_vendor']}
                    </span>
                </h6>
            </div>

            <div class="col-4">
                <h6 class="font-weight-bold mb-0">
                    ₽{price_data['high_price']:,}
                    <span class="badge badge-pill badge-success ml-2">
                        {price_data['highest_vendor']}
                    </span>
                </h6>
            </div>

        </div>
    </div>
    """


# Regular routes
@market_bp.route("/market/track-item/<string:tarkov_item_id>", methods=["POST"])
@login_required
def track_item(tarkov_item_id: str):
    success = market_service.track_item_for_user(current_user, tarkov_item_id)
    flash("Item tracked", "success")
    # Return JavaScript for HTMX to handle modal and reload
    return """
    <script>
        $('#trackItemModal').modal('hide');
        setTimeout(() => location.reload(), 500);
    </script>
    """


@market_bp.route("/market/untrack-item/<string:tarkov_item_id>", methods=["DELETE"])
@login_required  
def untrack_item(tarkov_item_id: str):
    success = market_service.untrack_item_for_user(current_user, tarkov_item_id)
    flash("Item untracked", "success")
    # Return JavaScript for HTMX to handle modal and reload
    return """
    <script>
        $('#trackItemModal').modal('hide');
        setTimeout(() => location.reload(), 500);
    </script>
    """


@market_bp.route("/market/")
@login_required
def index():
    tracked_items = market_service.get_user_tracked_items(current_user)

    # If it's an HTMX request, return partial template
    if request.headers.get("HX-Request"):
        return render_template("partials/_market_tracked_items.html", tracked_items=tracked_items)

    return render_template("market.html", tracked_items=tracked_items)