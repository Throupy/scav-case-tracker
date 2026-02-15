# app/market/routes.py (refactored)
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from flask_wtf.csrf import generate_csrf

from app.services.market_service import MarketService
from app.main.utils import get_tarkov_item_name_by_id

market_bp = Blueprint("market", __name__)
market_service = MarketService()


# HTMX routes
@market_bp.route("/market/search-items")
@login_required
def search_items():
    query = request.args.get("q", "").strip()
    results = market_service.search_items(query)
    
    if not results:
        return "<div class='list-group-item text-muted'>No items found.</div>"

    token = generate_csrf()

    return "".join([
        f"""
        <form method="POST" action="/market/track-item/{item.tarkov_id}">
            <input type="hidden" name="csrf_token" value="{token}">
            <button type="submit" class="list-group-item list-group-item-action">
                {item.name}
            </button>
        </form>
        """
        for item in results
    ])

@market_bp.route("/market/")
@login_required
def index():
    tracked_items = market_service.get_user_tracked_items(current_user)

    # If it's an HTMX request, return partial template
    if request.headers.get("HX-Request"):
        return render_template("partials/_market_tracked_items.html", tracked_items=tracked_items)

    return render_template("market.html", tracked_items=tracked_items)

@market_bp.route("/market/get-tracked-item-prices", methods=["GET"])
@login_required
def get_prices_htmx():
    tracked_items = market_service.get_user_tracked_items(current_user)

    ids = [i.tarkov_id for i in tracked_items]
    prices_by_id = market_service.get_tarkov_item_prices_by_ids(
        ids, include_historical=True, include_vendor=True
    )

    # render rows with prices filled
    return render_template(
        "partials/_market_tracked_items.html",
        tracked_items=tracked_items,
        prices_by_id=prices_by_id,
    )


# Regular routes
@market_bp.route("/market/track-item/<string:tarkov_item_id>", methods=["POST"])
@login_required
def track_item(tarkov_item_id: str):
    success = market_service.track_item_for_user(current_user, tarkov_item_id)
    tarkov_item_name = get_tarkov_item_name_by_id(tarkov_item_id)

    if success:
        flash(f"Item: '{tarkov_item_name}' tracked for {current_user.username}", "success")
    else:
        flash("Something went wrong while performing that action", "danger")
    return redirect(url_for("market.index"))

@market_bp.route("/market/untrack-item/<string:tarkov_item_id>", methods=["POST"])
@login_required  
def untrack_item(tarkov_item_id: str):
    success = market_service.untrack_item_for_user(current_user, tarkov_item_id)
    tarkov_item_name = get_tarkov_item_name_by_id(tarkov_item_id)

    if success:
        flash(f"Item: '{tarkov_item_name}' untracked for {current_user.username}", "success")
    else:
        flash("Something went wrong while performing that action", "danger")
    return redirect(url_for("market.index"))