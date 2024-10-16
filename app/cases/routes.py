import requests
from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.models import Entry
from app.extensions import db
from app.cases.forms import ScavCaseForm
from app.cases.utils import (
    calculate_and_prepare_most_profitable,
    calculate_avg_items_per_case_type,
    calculate_avg_return_by_case_type,
)

cases = Blueprint("cases", __name__)


@cases.route("/all-cases", methods=["GET"])
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


@cases.route("/insights")
def insights():
    entries = Entry.query.all()

    most_profitable_insight = calculate_and_prepare_most_profitable(entries)
    average_return_insight = calculate_avg_return_by_case_type(entries)
    average_items_insight = calculate_avg_items_per_case_type(entries)

    insights = [most_profitable_insight, average_return_insight, average_items_insight]
    insights = [insight for insight in insights if insight is not None]
    if not insights:
        flash("No Data to show", "warning")
    return render_template("insights.html", insights=insights)


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
    form = ScavCaseForm()

    if form.validate_on_submit():
        scav_case_type = form.scav_case_type.data
        uploaded_image = form.scav_case_image.data

        # Send the form data and image to the API
        files = {"image": uploaded_image}
        data = {"scav_case_type": scav_case_type, "user_id": current_user.id}

        response = requests.post(
            url_for("api.submit_scav_case_api", _external=True), data=data, files=files
        )
        if response.status_code == 200:
            flash("Scav Case and Items successfully added", "success")
            return redirect(url_for("main.dashboard"))
        else:
            flash(f"There was an error: {response.json().get('error')}", "danger")

    return render_template("create_entry.html", form=form)


@cases.route("/entry/<int:entry_id>/detail")
def entry_detail(entry_id):
    entry = Entry.query.get_or_404(entry_id)
    return render_template("entry_detail.html", entry=entry)


@cases.route("/delete-entry/<int:entry_id>", methods=["GET"])
def delete_entry(entry_id):
    entry = Entry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    flash("Your Entry was successfully deleted", "success")
    return redirect(url_for("main.dashboard"))
