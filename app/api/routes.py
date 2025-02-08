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
    scav_cases = ScavCase.query.all()

    scav_case_types = {}
    for scav_case in scav_cases:
        scav_case_types[scav_case.type] = scav_case_types.get(scav_case.type, 0) + 1

    return jsonify(scav_case_types)

@api.route("/api/discord-stats")
def discord_stats():
    """
    Stats results to be fetched by the discord bot
    """
    total_profit = ScavCase.query.with_entities(db.func.sum(ScavCase.profit)).scalar()
    total_cases = len(ScavCase.query.all())
    total_spend = ScavCase.query.with_entities(db.func.sum(ScavCase.cost)).scalar()
    return jsonify({"total_profit": total_profit, "total_cases": total_cases, "total_spend": total_spend})

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
            "created_at_humanized": humanize.naturaltime(datetime.utcnow() - scav_case.created_at),  
            "profit": scav_case.profit,                   
            "type": scav_case.type,
            "return": scav_case._return,
            "cost": scav_case.cost
        }
        for scav_case in scav_cases
    ]

    return jsonify({"labels": labels, "scav_cases": scav_case_data})

@api.route("/api/get-item-price/<item_id>")
def get_item_price_route(item_id):
    price = get_price(item_id)
    return jsonify({"price": price})


@api.route("/api/submit-scav-case", methods=["POST"])
def submit_scav_case_api():
    scav_case_type = request.form.get("scav_case_type")
    items_data = request.form.get("items_data")
    uploaded_image = request.files.get("image")
    user_id = request.form.get("user_id", None)

    if not scav_case_type and not (uploaded_image or items_data) :
        return jsonify({"error": "Scav case type and image are required"}), 400

    try:
        if uploaded_image:
            file_path = save_uploaded_image(uploaded_image)
            items = process_scav_case_image(file_path)
        else:
            items = json.loads(items_data)

        scav_case = create_scav_case_entry(scav_case_type, items, user_id)

        return jsonify(
            {
                "message": "Scav case successfully added",
                "scav_case_id": scav_case.id,
                "items": items,
            }
        ), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred: " + str(e)}), 500
