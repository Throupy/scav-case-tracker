from flask import Blueprint, jsonify, request

from app.models import Entry
from app.utils import get_price, get_image_link


api = Blueprint("api", __name__)


@api.route("/api/scav-case-type-distribution")
def fetch_scav_case_type_distribution():
    entries = Entry.query.all()

    scav_case_types = {}
    for entry in entries:
        scav_case_types[entry.type] = scav_case_types.get(entry.type, 0) + 1

    return jsonify(scav_case_types)


@api.route("/api/get-image-link")
def get_image_link_route():
    item_id = request.args.get("item_id")
    image_link = get_image_link(item_id)
    return jsonify({"url": image_link or None})


@api.route("/api/get-chart-data")
def get_chart_data_route():
    case_type = request.args.get("type") or "all"
    if case_type.lower() == "all":
        entries = Entry.query.order_by(Entry.created_at.desc()).limit(30).all()
    else:
        entries = (
            Entry.query.filter_by(type=case_type)
            .order_by(Entry.created_at.desc())
            .limit(30)
            .all()
        )

    labels = list(range(1, len(entries) + 1))
    data = [entry._return for entry in entries]
    types = [entry.type for entry in entries]
    return jsonify({"labels": labels, "data": data, "types": types})


@api.route("/api/get-item-price/<item_id>")
def get_item_price_route(item_id):
    price = get_price(item_id)
    return jsonify({"price": price})
