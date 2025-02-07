import json
from collections import defaultdict
import requests
from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.models import Entry, EntryItem
from app.extensions import db
from app.cases.forms import CreateEntryForm, UpdateEntryForm
from app.cases.utils import get_price, calculate_most_popular_categories, find_most_common_items, calculate_avg_items_per_case_type, calculate_avg_return_by_case_type, calculate_most_profitable, calculate_item_category_distribution

cases = Blueprint("cases", __name__)


@cases.route("/all-cases", methods=["GET"])
def all_cases():
    page = request.args.get("page", 1, type=int) 
    sort_by = request.args.get(
        "sort_by", "type"
    )
    sort_order = request.args.get("sort_order", "asc")  
    per_page = 10  
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

@cases.route("/insights-data")
def insights_data():
    case_type = request.args.get("case_type", "all")

    if case_type == "all":
        entries = Entry.query.all()
    else:
        entries = Entry.query.filter_by(type=case_type).all()

    if case_type == "all":
        # on "all", we want more aggregated / generic insights, so call some util functions for that
        entries = Entry.query.all()
        most_profitable_case = calculate_most_profitable(entries)
        avg_return_chart = calculate_avg_return_by_case_type(entries)
        avg_items_chart = calculate_avg_items_per_case_type(entries)
        category_distribution = calculate_item_category_distribution(entries)
        most_popular_categories = calculate_most_popular_categories(entries)
        most_popular_items = find_most_common_items(entries)
        # no individual chart data needed for this case type
        profit_over_time_chart = None
        items_over_time_chart = None
        return_over_time_chart = None
    else:
        entries = Entry.query.filter_by(type=case_type).all()
        most_popular_items = find_most_common_items(entries)
        most_popular_categories = calculate_most_popular_categories(entries)
        category_distribution = calculate_item_category_distribution(entries)

        profit_over_time_chart = {
            "labels": [str(entry.id) for entry in entries],
            "profits": [(entry._return - entry.cost) for entry in entries],
            "costs": [entry.cost for entry in entries]
        }

        items_over_time_chart = {
            "labels": [str(entry.id) for entry in entries],
            "items_count": [entry.number_of_items for entry in entries]
        }

        return_over_time_chart = {
            "labels": [str(entry.id) for entry in entries],
            "returns": [entry._return for entry in entries],
            "costs": [entry.cost for entry in entries]
        }

        # no bar chart nonsense when looking at a specific case type
        avg_items_chart = None
        most_profitable_case = None
        avg_return_chart = None


    return render_template(
        "partials/insights.html",
        case_type=case_type,
        most_popular_items=most_popular_items,
        most_popular_categories=most_popular_categories,
        avg_items_chart=avg_items_chart,
        most_profitable_case=most_profitable_case,
        avg_return_chart=avg_return_chart,
        return_over_time_chart=return_over_time_chart,
        category_labels=category_distribution["labels"],
        category_counts=category_distribution["values"],
        profit_over_time_chart=profit_over_time_chart,
        items_over_time_chart=items_over_time_chart
    )

@cases.route("/insights")
def insights():
    entries = Entry.query.all()

    most_profitable_case = calculate_most_profitable(entries)
    avg_return_chart = calculate_avg_return_by_case_type(entries)
    avg_items_chart = calculate_avg_items_per_case_type(entries)
    category_distribution = calculate_item_category_distribution(entries)
    most_popular_categories = calculate_most_popular_categories(entries)
    most_popular_items = find_most_common_items(entries)

    if not entries:
        flash("No Data to show", "warning")

    return render_template(
        "insights.html",
        case_type="all",
        most_profitable_case=most_profitable_case,
        avg_return_chart=avg_return_chart,
        avg_items_chart=avg_items_chart,
        category_labels=category_distribution["labels"],
        category_counts=category_distribution["values"],
        most_popular_categories=most_popular_categories,
        most_popular_items=most_popular_items,
    )


@cases.route("/create-entry", methods=["GET"])
@login_required
def create_entry():
    if not current_user.is_authenticated:
        flash("You must be logged in to do this", "danger")
        return redirect(url_for("users.login"))
    return render_template("create_entry.html")


@cases.route("/submit-scav-case", methods=["GET", "POST"])
@login_required
def submit_scav_case():
    form = CreateEntryForm()

    if form.validate_on_submit():
        scav_case_type = form.scav_case_type.data
        uploaded_image = form.scav_case_image.data
        items_data = form.items_data.data

        files = {"image": uploaded_image}
        data = {"scav_case_type": scav_case_type, "user_id": current_user.id, "items_data": items_data}

        response = requests.post(
            url_for("api.submit_scav_case_api", _external=True), data=data, files=files
        )
        if response.status_code == 200:
            flash("Scav Case and Items successfully added", "success")
            return redirect(url_for("main.dashboard"))
        else:
            flash(f"There was an error: {response.json().get('error')}", "danger")

    return render_template("create_entry.html", form=form)

@cases.route("/items")
def items():
    items = EntryItem.query.all()
    return render_template("items.html", items=items)

@cases.route("/entry/<int:entry_id>/detail")
def entry_detail(entry_id):
    entry = Entry.query.get_or_404(entry_id)
    return render_template("entry_detail.html", entry=entry)

@cases.route("/entry/<int:entry_id>/edit", methods=["GET", "POST"])
def update_entry(entry_id):
    entry = Entry.query.get_or_404(entry_id)
    form = UpdateEntryForm(obj=entry)

    if request.method == "GET":
        form.items_data.data = json.dumps([{
            "id": item.id,
            "name": item.name, 
            "quantity": item.amount
        } for item in entry.items])

    if form.validate_on_submit():
        items_data = json.loads(form.items_data.data)

        existing_items = {item.id: item for item in entry.items}
        received_item_ids = {item["id"] for item in items_data if "id" in item}

        items_to_delete = [item for item_id, item in existing_items.items() if item_id not in received_item_ids]
        for item in items_to_delete:
            db.session.delete(item)

        total_price = 0
        total_items = 0

        for item in items_data:
            if "id" in item and item["id"] in existing_items:
                # first update quantities
                existing_item = existing_items[item["id"]]
                existing_item.amount = item["quantity"]
            else:
                new_item = EntryItem(
                    entry=entry,
                    tarkov_id=item["id"],
                    price=get_price(item["id"]),
                    name=item["name"],
                    amount=item["quantity"],
                )
                total_price += new_item.price * new_item.amount
                db.session.add(new_item)
            
            item_price = getattr(existing_items.get(item.get("id")), "price", None) or 0
            total_price += item_price * item["quantity"]
            total_items += item["quantity"]

        entry._return = total_price
        entry.number_of_items = len(items_data)


        db.session.commit()
        flash("Scav Case entry updated successfully", "success")
        return redirect(url_for("cases.entry_detail", entry_id=entry.id))

    return render_template("edit_entry.html", form=form, entry=entry)

@cases.route("/delete-entry/<int:entry_id>", methods=["GET"])
def delete_entry(entry_id):
    entry = Entry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    flash("Your Entry was successfully deleted", "success")
    return redirect(url_for("main.dashboard"))
