import os
import json
import requests
from collections import defaultdict

from flask import Blueprint, request, render_template, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user

from app.models import ScavCase, ScavCaseItem
from app.cases.forms import CreateScavCaseForm, UpdateScavCaseForm
from app.cases.utils import is_discord_bot_request
from app.services.scav_case_service import ScavCaseService


cases = Blueprint("cases", __name__)
scav_case_service = ScavCaseService()


@cases.route("/all-scav-cases", methods=["GET"])
def all_scav_cases():
    page = request.args.get("page", 1, type=int)
    sort_by = request.args.get("sort_by", "type")
    sort_order = request.args.get("sort_order", "asc")
    
    pagination = scav_case_service.get_paginated_cases(
        page=page, sort_by=sort_by, sort_order=sort_order
    )
    
    return render_template(
        "all_scav_cases.html",
        scav_cases=pagination.items,
        pagination=pagination,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@cases.route("/insights-data")
def insights_data():
    case_type = request.args.get("case_type", "all")
    insights = scav_case_service.calculate_insights_data(case_type)
    
    return render_template(
        "partials/insights.html",
        case_type=case_type,
        **insights
    )


@cases.route("/insights")
def insights():
    insights = scav_case_service.calculate_insights_data("all")

    if not scav_case_service.get_cases_by_type("all"):
        flash("No Data to show", "warning")
    
    return render_template("insights.html", case_type="all", **insights)


@cases.route("/create-scav-case", methods=["GET"])
@login_required
def create_scav_case():
    if not current_user.is_authenticated:
        flash("You must be logged in to do this", "danger")
        return redirect(url_for("users.login"))
    return render_template("create_scav_case.html")

@cases.route("/submit-scav-case", methods=["GET", "POST"])
# no login_required - integrations will hit this (with key-based auth), check for integration first, then check login if webapp
def submit_scav_case():
    # special handling for the discord bot integration
    if request.method == "POST" and is_discord_bot_request(request):
        return scav_case_service.handle_discord_bot_submission(request)

    # this will be a webapp user, check they are authenticated
    if not current_user.is_authenticated:
        return redirect(url_for("users.login", next=request.url))

    # Create the form instance to display to web user
    form = CreateScavCaseForm()

    if form.validate_on_submit():
        result = scav_case_service.create_scav_case(
            scav_case_type=form.scav_case_type.data,
            uploaded_image=form.scav_case_image.data,
            items_data=form.items_data.data,
            user=current_user
        )

        if result["success"]:
            flash(result["message"], "success")
            return redirect(url_for("main.dashboard"))
        else:
            flash(result["message"], "danger")
    
    # render HTML with CreateScavCase form
    return render_template("create_scav_case.html", form=form)

@cases.route("/items")
def items():
    items = ScavCaseItem.query.all()
    return render_template("items.html", items=items)


@cases.route("/case/<int:scav_case_id>/detail")
def scav_case_detail(scav_case_id):
    scav_case = scav_case_service.get_case_by_id_or_404(scav_case_id)
    return render_template("scav_case_detail.html", scav_case=scav_case)


@cases.route("/case/<int:scav_case_id>/edit", methods=["GET", "POST"])
def update_scav_case(scav_case_id):
    scav_case = scav_case_service.get_case_by_id_or_404(scav_case_id)
    form = UpdateScavCaseForm(obj=scav_case)
    
    if request.method == "GET":
        form.items_data.data = json.dumps([
            {"id": item.id, "name": item.name, "quantity": item.amount}
            for item in scav_case.items
        ])
    
    if form.validate_on_submit():
        try:
            items_data = json.loads(form.items_data.data)
            scav_case_service.update_scav_case_items(scav_case, items_data)
            
            flash("Scav Case updated successfully", "success")
            return redirect(url_for("cases.scav_case_detail", scav_case_id=scav_case.id))
            
        except (json.JSONDecodeError, Exception) as e:
            flash(f"Error updating scav case: {str(e)}", "danger")
    
    return render_template("edit_scav_case.html", form=form, scav_case=scav_case)


@cases.route("/case/<int:scav_case_id>/delete", methods=["GET"])
def delete_scav_case(scav_case_id):
    # TODO: Delete shouldn't use GET
    scav_case = scav_case_service.get_case_by_id_or_404(scav_case_id)
    
    if scav_case_service.delete_scav_case(scav_case):
        flash("Your ScavCase was successfully deleted", "success")
    else:
        flash("Error deleting ScavCase", "danger")
        
    return redirect(url_for("cases.all_scav_cases"))