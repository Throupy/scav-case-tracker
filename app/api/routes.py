import json
from datetime import datetime, timedelta

import humanize
from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user

from app.auth.decorators import api_key_required
from app.models import ScavCase, ScavCaseItem, User
from app.extensions import db
from app.filters import get_item_cdn_image_url
from app.market.utils import get_price
from app.http.responses import success_response, error_response
from app.http.errors import ValidationError, NotFoundError
from app.constants import SCAV_CASE_TYPES
from app.services.scav_case_service import ScavCaseService


api_bp = Blueprint("api", __name__)
_scav_case_service = ScavCaseService()


def _since_date(days: int):
    """Return a UTC cutoff datetime for `days` ago, or None if days <= 0 (all-time)."""
    return datetime.utcnow() - timedelta(days=days) if days > 0 else None


# queried by case_distribution_chart template (within dashboard)
@api_bp.route("/api/scav-case-type-distribution")
@login_required
def fetch_scav_case_type_distribution():
    days = request.args.get("days", 0, type=int)
    scope = request.args.get("scope", "global")
    q = db.session.query(ScavCase.type, db.func.count(ScavCase.id)).group_by(ScavCase.type)
    since = _since_date(days)
    if since:
        q = q.filter(ScavCase.created_at >= since)
    if scope == "personal":
        q = q.filter(ScavCase.user_id == current_user.id)
    rows = q.all()

    data = {case_type: count for case_type, count in rows}
    return success_response(data=data, message="Scav case type distribution fetched")

# queried by earnings_overview_chart template (within dashboard)
@api_bp.route("/api/get-chart-data")
@login_required
def get_chart_data_route():
    case_type = request.args.get("type", "all")
    days = request.args.get("days", 0, type=int)
    scope = request.args.get("scope", "global")

    if case_type.lower() != "all" and case_type not in SCAV_CASE_TYPES:
        return error_response(message="Invalid case type", error_code="VALIDATION_ERROR", status_code=422)

    q = ScavCase.query
    if case_type.lower() != "all":
        q = q.filter_by(type=case_type)
    since = _since_date(days)
    if since:
        q = q.filter(ScavCase.created_at >= since)
    if scope == "personal":
        q = q.filter(ScavCase.user_id == current_user.id)
    scav_cases = q.order_by(ScavCase.created_at.desc()).limit(15).all()

    labels = list(range(1, len(scav_cases) + 1))
    scav_case_data = [
        {
            "id": scav_case.id,
            "created_at_humanized": humanize.naturaltime(datetime.utcnow() - scav_case.created_at),
            "profit": scav_case.profit,
            "type": scav_case.type,
            "return": scav_case._return,
            "cost": scav_case.cost,
        }
        for scav_case in scav_cases
    ]

    return success_response(
        data={"labels": labels, "scav_cases": scav_case_data},
        message="Chart data fetched",
    )

# queried by dashboard KPI cards when the time-range slider or case-type dropdown changes
@api_bp.route("/api/dashboard-kpis")
@login_required
def dashboard_kpis():
    days = request.args.get("days", 0, type=int)
    case_type = request.args.get("case_type", "all")
    scope = request.args.get("scope", "global")
    since = _since_date(days)

    if case_type.lower() != "all" and case_type not in SCAV_CASE_TYPES:
        return error_response(message="Invalid case type", error_code="VALIDATION_ERROR", status_code=422)

    user_id = current_user.id if scope == "personal" else None
    data = _scav_case_service.generate_dashboard_data(since_date=since, case_type=case_type, user_id=user_id)

    tc = data["top_contributor"]
    mvi = data["most_valuable_item"]
    bl = data["biggest_loss"]

    return success_response(
        data={
            "total_cases": data["total_cases"],
            "total_cost": data["total_cost"],
            "total_return": data["total_return"],
            "total_profit": data["total_profit"],
            "most_popular_category": data["most_popular_category"],
            "most_profitable_case_type": data["most_profitable_case_type"],
            "top_contributor": {
                "id": tc.id,
                "username": tc.username,
                "image_file": tc.image_file,
            } if tc else None,
            "most_valuable_item": {
                "name": mvi.name,
                "scav_case_id": mvi.scav_case_id,
                "image_url": get_item_cdn_image_url(mvi),
            } if mvi else None,
            "biggest_loss": {
                "id": bl.id,
                "cost": bl.cost,
                "_return": bl._return,
            } if bl else None,
            "win_rate": data["win_rate"],
            "average_roi": data["average_roi"],
        },
        message="Dashboard KPIs fetched",
    )


def _parse_insight_filters():
    """Parse the days/case_type/scope query params shared by all insight widgets.

    Returns (case_type, since_date, user_id, error_response). error_response is
    not None when case_type failed validation, in which case the other values
    should be ignored and error_response returned directly by the caller.
    """
    case_type = request.args.get("case_type", "all")
    days = request.args.get("days", 0, type=int)
    scope = request.args.get("scope", "global")

    if case_type.lower() != "all" and case_type not in SCAV_CASE_TYPES:
        return None, None, None, error_response(message="Invalid case type", error_code="VALIDATION_ERROR", status_code=422)

    since = _since_date(days)
    user_id = current_user.id if scope == "personal" else None
    return case_type, since, user_id, None


# queried by the "Most Common Items" dashboard widget
@api_bp.route("/api/insights/most-common-items")
@login_required
def insights_most_common_items():
    case_type, since, user_id, err = _parse_insight_filters()
    if err:
        return err

    items = _scav_case_service.get_most_common_items_insight(case_type=case_type, since_date=since, user_id=user_id)
    data = [
        {
            "tarkov_id": item.tarkov_id,
            "name": item.name,
            "count": count,
            "image_url": get_item_cdn_image_url(item),
        }
        for item, count in items
    ]
    return success_response(data=data, message="Most common items fetched")


# queried by the "Item Category Distribution" dashboard widget
@api_bp.route("/api/insights/category-distribution")
@login_required
def insights_category_distribution():
    case_type, since, user_id, err = _parse_insight_filters()
    if err:
        return err

    data = _scav_case_service.get_category_distribution_insight(case_type=case_type, since_date=since, user_id=user_id)
    return success_response(data=data, message="Category distribution fetched")


# queried by the "Return" dashboard widget
@api_bp.route("/api/insights/return-chart")
@login_required
def insights_return_chart():
    case_type, since, user_id, err = _parse_insight_filters()
    if err:
        return err

    data = _scav_case_service.get_return_insight(case_type=case_type, since_date=since, user_id=user_id)
    return success_response(data=data, message="Return insight fetched")


# queried by the "Items" dashboard widget
@api_bp.route("/api/insights/items-chart")
@login_required
def insights_items_chart():
    case_type, since, user_id, err = _parse_insight_filters()
    if err:
        return err

    data = _scav_case_service.get_items_insight(case_type=case_type, since_date=since, user_id=user_id)
    return success_response(data=data, message="Items insight fetched")


# queried by the "Profit" dashboard widget
@api_bp.route("/api/insights/profit-chart")
@login_required
def insights_profit_chart():
    case_type, since, user_id, err = _parse_insight_filters()
    if err:
        return err

    data = _scav_case_service.get_profit_insight(case_type=case_type, since_date=since, user_id=user_id)
    return success_response(data=data, message="Profit insight fetched")


def _serialize_case(case):
    roi = ((case._return - case.cost) / case.cost * 100) if case.cost else 0
    return {
        "id": case.id,
        "type": case.type,
        "cost": case.cost,
        "total_return": case._return,
        "profit": case.profit,
        "roi_pct": round(roi, 1),
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "submitted_by": case.author.username,
        "via_discord": case.via_discord,
        "items": [
            {
                "name": item.name,
                "amount": item.amount,
                "price": item.price,
                "total": (item.price or 0) * item.amount,
            }
            for item in case.items
        ],
    }


# queried by discord bot !case command
@api_bp.route("/api/case/<int:case_id>")
@api_key_required
def get_case(case_id):
    case = _scav_case_service.get_case_by_id(case_id)
    if not case:
        return error_response(message=f"Case {case_id} not found", error_code="NOT_FOUND", status_code=404)
    return success_response(data=_serialize_case(case), message="Case fetched")


@api_bp.route("/api/case/best")
@api_key_required
def get_best_case():
    case = _scav_case_service._get_most_profitable_case()
    if not case:
        return error_response(message="No cases found", error_code="NOT_FOUND", status_code=404)
    return success_response(data=_serialize_case(case), message="Best case fetched")


@api_bp.route("/api/case/worst")
@api_key_required
def get_worst_case():
    case = _scav_case_service._get_worst_case()
    if not case:
        return error_response(message="No cases found", error_code="NOT_FOUND", status_code=404)
    return success_response(data=_serialize_case(case), message="Worst case fetched")


# queried by discord bot
@api_bp.route("/api/discord-stats")
@api_key_required
def discord_stats():
    data = _scav_case_service.generate_dashboard_data()
    tc = data["top_contributor"]
    mvi = data["most_valuable_item"]
    return success_response(
        data={
            "total_profit": data["total_profit"],
            "total_cases": data["total_cases"],
            "total_spend": data["total_cost"],
            "total_return": data["total_return"],
            "avg_profit": _scav_case_service._get_avg_profit_per_case(),
            "most_profitable_case_type": data["most_profitable_case_type"],
            "most_popular_category": data["most_popular_category"],
            "top_contributor": tc.username if tc else None,
            "most_valuable_item": mvi.name if mvi else None,
        },
        message="Discord stats fetched",
    )