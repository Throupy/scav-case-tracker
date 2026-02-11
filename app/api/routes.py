import json
from datetime import datetime

import humanize
from flask import Blueprint, jsonify, request, abort

from app.models import ScavCase, ScavCaseItem
from app.cases.utils import (
    get_price,
    get_image_link,
    save_uploaded_image,
    process_scav_case_image,
    create_scav_case_entry,
)
from app.extensions import db


api = Blueprint("api", __name__)


@api.route("/api/scav-case-type-distribution")
def fetch_scav_case_type_distribution():
    rows = (
        db.session.query(ScavCase.type, db.func.count(ScavCase.id))
        .group_by(ScavCase.type)
        .all()
    )
    
    return jsonify({case_type: count for case_type, count in rows})


@api.route("/api/discord-stats")
def discord_stats():
    """
    Stats results to be fetched by the discord bot
    """
    total_profit = ScavCase.query.with_entities(db.func.sum(ScavCase.profit)).scalar()
    total_cases = ScavCase.query.count()
    total_spend = ScavCase.query.with_entities(db.func.sum(ScavCase.cost)).scalar()
    return jsonify(
        {
            "total_profit": total_profit,
            "total_cases": total_cases,
            "total_spend": total_spend,
        }
    )


@api.route("/api/get-image-link")
def get_image_link_route():
    item_id = request.args.get("item_id")
    image_link = get_image_link(item_id)
    return jsonify({"url": image_link or None})


@api.route("/api/get-chart-data")
def get_chart_data_route():
    case_type = request.args.get("type") or "all"
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
            "created_at_humanized": humanize.naturaltime(
                datetime.utcnow() - scav_case.created_at
            ),
            "profit": scav_case.profit,
            "type": scav_case.type,
            "return": scav_case._return,
            "cost": scav_case.cost,
        }
        for scav_case in scav_cases
    ]

    return jsonify({"labels": labels, "scav_cases": scav_case_data})


@api.route("/api/get-item-price/<item_id>")
def get_item_price_route(item_id):
    price = get_price(item_id)
    return jsonify({"price": price})

@api.route("/api/get-latest-scav-case", methods=["GET"])
def latest_scav_case():
    latest_case = ScavCase.query.order_by(ScavCase.created_at.desc()).first()
    if not latest_case:
        return jsonify({"error": "No scav case found"}), 404

    return jsonify({
        "created_at": latest_case.created_at,
        "type": latest_case.type,
        "profit": latest_case.profit,
        "return": latest_case._return,
        "cost": latest_case.cost,
        "items": [
            {
                "name": item.name,
                "tarkov_id": item.tarkov_id,
                "price": item.price,
                "amount": item.amount,
            }
            for item in latest_case.items
        ],
    })