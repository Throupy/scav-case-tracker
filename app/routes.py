import json
import os

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    Blueprint,
    flash,
    current_app,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Entry, EntryItem, TarkovItem
from app.utils import (
    get_price,
    calculate_and_prepare_most_profitable,
    calculate_avg_return_by_case_type,
    calculate_avg_items_per_case_type,
    process_image_for_items,
    extract_items_from_ocr,
    validate_scav_case_image,
    ItemNotFoundException,
)
from app.config import SCAV_CASE_TYPES

main = Blueprint("main", __name__)


@main.route("/not-implemented")
def not_implemented():
    flash("This feature hasn't been implemented yet", "warning")
    return redirect(request.referrer)


@main.route("/all-cases", methods=["GET"])
def all_cases():
    page = request.args.get("page", 1, type=int)  # Get current page number
    sort_by = request.args.get(
        "sort_by", "type"
    )  # Column to sort by, default to 'type'
    sort_order = request.args.get("sort_order", "asc")  # Sort order, default to 'asc'
    per_page = 10  # Number of entries per page
    entries = Entry.query.with_entities(Entry.id, Entry.type, Entry._return).all()

    if sort_order == "asc":
        entries_query = Entry.query.order_by(db.asc(getattr(Entry, sort_by)))
    else:
        entries_query = Entry.query.order_by(db.desc(getattr(Entry, sort_by)))

    pagination = entries_query.paginate(page=page, per_page=per_page)
    entries = pagination.items
    return render_template(
        "all_cases.html",
        entries=entries,
        pagination=pagination,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@main.route("/")
@main.route("/dashboard")
def dashboard():
    entries = Entry.query.all()
    return render_template(
        "dashboard.html", scav_case_types=SCAV_CASE_TYPES, entries=entries
    )


@main.route("/insights")
def insights():
    entries = Entry.query.all()

    most_profitable_insight = calculate_and_prepare_most_profitable(entries)
    average_return_insight = calculate_avg_return_by_case_type(entries)
    average_items_insight = calculate_avg_items_per_case_type(entries)

    insights = [most_profitable_insight, average_return_insight, average_items_insight]

    return render_template("insights.html", insights=insights)


@main.route("/create-entry", methods=["GET"])
@login_required
def create_entry():
    if not current_user.is_authenticated:
        flash("You must be logged in to do this", "danger")
        return redirect(url_for("users.login"))
    return render_template("create_entry.html")


@main.route("/submit-scav-case", methods=["POST"])
@login_required
def submit_scav_case():
    scav_case_type = request.form.get("scav_case_type")
    items_data = request.form.get("items_data")
    uploaded_image = request.files.get("scav_case_image")

    if not scav_case_type and not items_data and not uploaded_image:
        flash("Scav case type and items are required!", "danger")
        return redirect(url_for("main.dashboard"))

    if uploaded_image:
        filename = secure_filename(uploaded_image.filename)
        file_path = os.path.join(current_app.root_path, "static/uploads", filename)
        uploaded_image.save(file_path)

        if not validate_scav_case_image(file_path):
            flash("The uploaded image doesn't look like a scav case. See the instructions and try again", "danger")
            return redirect(url_for("main.create_entry"))

        ocr_text = process_image_for_items(file_path)
        try:
            items = extract_items_from_ocr(ocr_text)
        except ItemNotFoundException as e:
            flash(str(e), "danger")
            return redirect(url_for("main.dashboard"))

        items_data = json.dumps(items)

    try:
        entry = Entry(type=scav_case_type, user_id=current_user.id)
        # work out prices of each item upon entry
        if scav_case_type.lower() == "moonshine":
            entry.cost = get_price("5d1b376e86f774252519444e")
        elif scav_case_type.lower() == "intelligence":
            entry.cost = get_price("5c12613b86f7743bbe2c3f76")
        else:
            entry.cost = scav_case_type[1::]
        db.session.add(entry)
        db.session.commit()

        items = json.loads(items_data)
        for item in items:
            entry_item = EntryItem(
                entry_id=entry.id,
                tarkov_id=item["id"],
                price=get_price(item["id"]),
                name=item["name"],
                amount=item["quantity"],
            )
            db.session.add(entry_item)
            entry.number_of_items += 1
            entry._return += entry_item.price * item["quantity"]

        db.session.commit()
        flash("Scav case and items saved successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"There was an error adding your scav case: {e}", "danger")

    return redirect(url_for("main.dashboard"))


@main.route("/entry/<int:entry_id>/detail")
def entry_detail(entry_id):
    entry = Entry.query.get_or_404(entry_id)
    return render_template("entry_detail.html", entry=entry)


@main.route("/delete-entry/<int:entry_id>", methods=["GET"])
def delete_entry(entry_id):
    entry = Entry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    flash("Your Entry was successfully deleted", "success")
    return redirect(url_for("main.dashboard"))


@main.route("/search-items")
def search_items():
    query = request.args.get("q")
    if len(query) < 2:
        return render_template("partials/item_list.html", items=[])
    items = TarkovItem.query.filter(TarkovItem.name.ilike(f"%{query}%")).all()
    return render_template("partials/item_list.html", items=items)
