import json
from datetime import datetime

import humanize
from flask import Blueprint, jsonify, request, abort

from app.models import ScavCase, ScavCaseItem
from app.extensions import db
from app.cases.utils import get_price
from app.http.responses import success_response, error_response
from app.http.errors import ValidationError, NotFoundError


api_bp = Blueprint("api", __name__)

# queried by case_distribution_chart template (within dashboard)
@api_bp.route("/api/scav-case-type-distribution")
def fetch_scav_case_type_distribution():
    rows = (
        db.session.query(ScavCase.type, db.func.count(ScavCase.id))
        .group_by(ScavCase.type)
        .all()
    )

    data = {case_type: count for case_type, count in rows}
    return success_response(data=data, message="Scav case type distribution fetched")

# queried by earnings_overview_chart template (within dashboard)
@api_bp.route("/api/get-chart-data")
def get_chart_data_route():
    case_type = request.args.get("type", "all")

    if case_type.lower() == "all":
        scav_cases = ScavCase.query.order_by(ScavCase.created_at.desc()).limit(15).all()
    else:
        scav_cases = (
            ScavCase.query.filter_by(type=case_type)
            .order_by(ScavCase.created_at.desc())
            .limit(15)
            .all()
        )

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