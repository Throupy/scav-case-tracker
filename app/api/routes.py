import json
from datetime import datetime, timedelta

import humanize
from flask import Blueprint, jsonify, request, abort

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
def fetch_scav_case_type_distribution():
    days = request.args.get("days", 0, type=int)
    q = db.session.query(ScavCase.type, db.func.count(ScavCase.id)).group_by(ScavCase.type)
    since = _since_date(days)
    if since:
        q = q.filter(ScavCase.created_at >= since)
    rows = q.all()

    data = {case_type: count for case_type, count in rows}
    return success_response(data=data, message="Scav case type distribution fetched")

# queried by earnings_overview_chart template (within dashboard)
@api_bp.route("/api/get-chart-data")
def get_chart_data_route():
    case_type = request.args.get("type", "all")
    days = request.args.get("days", 0, type=int)

    if case_type.lower() != "all" and case_type not in SCAV_CASE_TYPES:
        return error_response(message="Invalid case type", error_code="VALIDATION_ERROR", status_code=422)

    q = ScavCase.query
    if case_type.lower() != "all":
        q = q.filter_by(type=case_type)
    since = _since_date(days)
    if since:
        q = q.filter(ScavCase.created_at >= since)
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
def dashboard_kpis():
    days = request.args.get("days", 0, type=int)
    case_type = request.args.get("case_type", "all")
    since = _since_date(days)

    if case_type.lower() != "all" and case_type not in SCAV_CASE_TYPES:
        return error_response(message="Invalid case type", error_code="VALIDATION_ERROR", status_code=422)

    data = _scav_case_service.generate_dashboard_data(since_date=since, case_type=case_type)

    tc = data["top_contributor"]
    mvi = data["most_valuable_item"]

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
        },
        message="Dashboard KPIs fetched",
    )


# queried by discord bot
@api_bp.route("/api/discord-stats")
def discord_stats():
    """Stats results to be fetched by the discord bot"""
    total_profit = ScavCase.query.with_entities(db.func.sum(ScavCase.profit)).scalar() or 0
    total_cases = ScavCase.query.count()
    total_spend = ScavCase.query.with_entities(db.func.sum(ScavCase.cost)).scalar() or 0

    return success_response(
        data = {
            "total_profit": total_profit,
            "total_cases": total_cases,
            "total_spend": total_spend
        },
        message = "Discord stats fetched"
    )