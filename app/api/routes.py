from flask import Blueprint, jsonify, request

from app.models import Entry
from app.cases.utils import (
    get_price,
    get_image_link,
    save_uploaded_image,
    process_scav_case_image,
    create_scav_case_entry,
)


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


@api.route("/api/submit-scav-case", methods=["POST"])
def submit_scav_case_api():
    scav_case_type = request.form.get("scav_case_type")
    uploaded_image = request.files.get("image")
    user_id = request.form.get("user_id", None)

    if not scav_case_type or not uploaded_image:
        return jsonify({"error": "Scav case type and image are required"}), 400

    try:
        file_path = save_uploaded_image(uploaded_image)
        items = process_scav_case_image(file_path)
        entry = create_scav_case_entry(scav_case_type, items, user_id)

        return jsonify(
            {
                "message": "Scav case successfully added",
                "entry_id": entry.id,
                "items": items,
            }
        ), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred: " + str(e)}), 500
