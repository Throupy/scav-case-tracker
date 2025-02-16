import json
from collections import defaultdict
import requests
from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.models import ScavCase, ScavCaseItem
from app.extensions import db
from app.cases.forms import CreateScavCaseForm, UpdateScavCaseForm
from app.cases.utils import (
    get_price,
    calculate_most_popular_categories,
    find_most_common_items,
    calculate_avg_items_per_case_type,
    calculate_avg_return_by_case_type,
    calculate_most_profitable,
    calculate_item_category_distribution,
    check_achievements
)

cases = Blueprint("cases", __name__)


@cases.route("/all-scav-cases", methods=["GET"])
def all_scav_cases():
    page = request.args.get("page", 1, type=int)
    sort_by = request.args.get("sort_by", "type")
    sort_order = request.args.get("sort_order", "asc")
    per_page = 10
    scav_cases = ScavCase.query.with_entities(
        ScavCase.id, ScavCase.type, ScavCase._return
    ).all()

    if sort_order == "asc":
        scav_cases_query = ScavCase.query.order_by(db.asc(getattr(ScavCase, sort_by)))
    else:
        scav_cases_query = ScavCase.query.order_by(db.desc(getattr(ScavCase, sort_by)))

    pagination = scav_cases_query.paginate(page=page, per_page=per_page)
    scav_cases = pagination.items
    return render_template(
        "all_scav_cases.html",
        scav_cases=scav_cases,
        pagination=pagination,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@cases.route("/insights-data")
def insights_data():
    case_type = request.args.get("case_type", "all")

    if case_type == "all":
        scav_cases = ScavCase.query.all()
    else:
        scav_cases = ScavCase.query.filter_by(type=case_type).all()

    if case_type == "all":
        # on "all", we want more aggregated / generic insights, so call some util functions for that
        scav_cases = ScavCase.query.all()
        most_profitable_case = calculate_most_profitable(scav_cases)
        avg_return_chart = calculate_avg_return_by_case_type(scav_cases)
        avg_items_chart = calculate_avg_items_per_case_type(scav_cases)
        category_distribution = calculate_item_category_distribution(scav_cases)
        most_popular_categories = calculate_most_popular_categories(scav_cases)
        most_popular_items = find_most_common_items(scav_cases)
        # no individual chart data needed for this case type
        profit_over_time_chart = None
        items_over_time_chart = None
        return_over_time_chart = None
    else:
        scav_cases = ScavCase.query.filter_by(type=case_type).all()
        most_popular_items = find_most_common_items(scav_cases)
        most_popular_categories = calculate_most_popular_categories(scav_cases)
        category_distribution = calculate_item_category_distribution(scav_cases)

        profit_over_time_chart = {
            "labels": [str(scav_case.id) for scav_case in scav_cases],
            "profits": [
                (scav_case._return - scav_case.cost) for scav_case in scav_cases
            ],
            "costs": [scav_case.cost for scav_case in scav_cases],
        }

        items_over_time_chart = {
            "labels": [str(scav_case.id) for scav_case in scav_cases],
            "items_count": [scav_case.number_of_items for scav_case in scav_cases],
        }

        return_over_time_chart = {
            "labels": [str(scav_case.id) for scav_case in scav_cases],
            "returns": [scav_case._return for scav_case in scav_cases],
            "costs": [scav_case.cost for scav_case in scav_cases],
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
        items_over_time_chart=items_over_time_chart,
    )


@cases.route("/insights")
def insights():
    scav_cases = ScavCase.query.all()

    most_profitable_case = calculate_most_profitable(scav_cases)
    avg_return_chart = calculate_avg_return_by_case_type(scav_cases)
    avg_items_chart = calculate_avg_items_per_case_type(scav_cases)
    category_distribution = calculate_item_category_distribution(scav_cases)
    most_popular_categories = calculate_most_popular_categories(scav_cases)
    most_popular_items = find_most_common_items(scav_cases)

    if not scav_cases:
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


@cases.route("/create-scav-case", methods=["GET"])
@login_required
def create_scav_case():
    if not current_user.is_authenticated:
        flash("You must be logged in to do this", "danger")
        return redirect(url_for("users.login"))
    return render_template("create_scav_case.html")


@cases.route("/submit-scav-case", methods=["GET", "POST"])
@login_required
def submit_scav_case():
    form = CreateScavCaseForm()

    if form.validate_on_submit():
        scav_case_type = form.scav_case_type.data
        uploaded_image = form.scav_case_image.data
        items_data = form.items_data.data

        files = {"image": uploaded_image}
        data = {
            "scav_case_type": scav_case_type,
            "user_id": current_user.id,
            "items_data": items_data,
        }

        response = requests.post(
            url_for("api.submit_scav_case_api", _external=True), data=data, files=files
        )
        if response.status_code == 200:
            check_achievements(current_user)
            flash("Scav Case and Items successfully added", "success")
            return redirect(url_for("main.dashboard"))
        else:
            flash(f"There was an error: {response.json().get('error')}", "danger")

    return render_template("create_scav_case.html", form=form)


@cases.route("/items")
def items():
    items = ScavCaseItem.query.all()
    return render_template("items.html", items=items)


@cases.route("/case/<int:scav_case_id>/detail")
def scav_case_detail(scav_case_id):
    scav_case = ScavCase.query.get_or_404(scav_case_id)
    return render_template("scav_case_detail.html", scav_case=scav_case)


@cases.route("/case/<int:scav_case_id>/edit", methods=["GET", "POST"])
def update_scav_case(scav_case_id):
    scav_case = ScavCase.query.get_or_404(scav_case_id)
    form = UpdateScavCaseForm(obj=scav_case)

    if request.method == "GET":
        form.items_data.data = json.dumps(
            [
                {"id": item.id, "name": item.name, "quantity": item.amount}
                for item in scav_case.items
            ]
        )

    if form.validate_on_submit():
        items_data = json.loads(form.items_data.data)

        existing_items = {item.id: item for item in scav_case.items}
        received_item_ids = {item["id"] for item in items_data if "id" in item}

        items_to_delete = [
            item
            for item_id, item in existing_items.items()
            if item_id not in received_item_ids
        ]
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
                new_item = ScavCaseItem(
                    scav_case_id=scav_case.id,
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

        scav_case._return = total_price
        scav_case.number_of_items = len(items_data)

        db.session.commit()
        flash("Scav Case updated successfully", "success")
        return redirect(url_for("cases.scav_case_detail", scav_case_id=scav_case.id))

    return render_template("edit_scav_case.html", form=form, scav_case=scav_case)


@cases.route("/case/<int:scav_case_id>/delete", methods=["GET"])
def delete_scav_case(scav_case_id):
    scav_case = ScavCase.query.get_or_404(scav_case_id)
    db.session.delete(scav_case)
    db.session.commit()
    flash("Your ScavCase was successfully deleted", "success")
    return redirect(url_for("main.dashboard"))
