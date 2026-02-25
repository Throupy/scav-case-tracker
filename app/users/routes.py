from flask import Blueprint, redirect, url_for, flash, request, render_template
from flask_login import login_user, logout_user, login_required, current_user

from app.users.utils import save_profile_picture
from app.models import User
from app.extensions import db, bcrypt
from app.users.forms import LoginForm, UpdateAccountForm, ChangePasswordForm, AccountChangePasswordForm
from app.services.scav_case_service import ScavCaseService
from app.services.user_service import UserService

users_bp = Blueprint("users", __name__)

scav_case_service = ScavCaseService()
user_service = UserService()

@users_bp.route("/users/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("cases.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            if user.force_password_change:
                flash("Please set a new password before continuing.", "warning")
                return redirect(url_for("users.change_password"))
            flash("You are now logged in", "success")
            return redirect(url_for("cases.dashboard"))
        else:
            flash("Login Unsuccessful. Please check username and password", "danger")
    return render_template("login.html", form=form)


@users_bp.route("/users/register", methods=["GET", "POST"])
def register():
    flash("Registration is currently closed. Contact an administrator.", "warning")
    return redirect(url_for("users.login"))


@users_bp.route("/users/logout", methods=["POST"])
def logout():
    logout_user()
    flash("You are now logged out", "success")
    return redirect(url_for("users.login"))


@users_bp.route("/users/account", methods=["GET", "POST"])
@login_required
def account():
    form = UpdateAccountForm()
    pw_form = AccountChangePasswordForm(prefix="pw")
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_profile_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        db.session.commit()
        flash("Your account has been updated!", "success")
        return redirect(url_for("users.account"))
    elif request.method == "GET":
        form.username.data = current_user.username
    return render_template("account.html", form=form, pw_form=pw_form)


@users_bp.route("/users/account/change-password", methods=["POST"])
@login_required
def account_change_password():
    pw_form = AccountChangePasswordForm(prefix="pw")
    if pw_form.validate_on_submit():
        if not bcrypt.check_password_hash(current_user.password, pw_form.current_password.data):
            flash("Current password is incorrect.", "danger")
        else:
            current_user.password = bcrypt.generate_password_hash(pw_form.new_password.data).decode("utf-8")
            db.session.commit()
            flash("Password changed successfully.", "success")
    else:
        for errors in pw_form.errors.values():
            for error in errors:
                flash(error, "danger")
    return redirect(url_for("users.account"))

@users_bp.route("/users/<int:user_id>/cases", methods=["GET"])
def cases(user_id: int):
    user = user_service.get_user_by_id_or_404(user_id)

    page = request.args.get("page", 1, type=int)
    sort_by = request.args.get("sort_by", "created_at")
    sort_order = request.args.get("sort_order", "desc")
    case_type = request.args.get("case_type", "all")

    pagination = scav_case_service.get_all_cases_by_user_paginated(
        user=user,
        page=page,
        sort_by=sort_by,
        sort_order=sort_order,
        case_type=case_type,
    )

    return render_template(
        "user_cases.html",
        user=user,
        scav_cases=pagination.items,
        pagination=pagination,
        sort_by=sort_by,
        sort_order=sort_order,
        case_type=case_type,
    )

@users_bp.route("/users/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        current_user.password = bcrypt.generate_password_hash(form.new_password.data).decode("utf-8")
        current_user.force_password_change = False
        db.session.commit()
        flash("Password updated successfully.", "success")
        return redirect(url_for("cases.dashboard"))
    return render_template("change_password.html", form=form)


@users_bp.route("/users/<int:user_id>/cases-showcase")
def cases_showcase(user_id: int):
    user = user_service.get_user_by_id_or_404(user_id)
    users_cases_showcase_data = scav_case_service.generate_users_cases_showcase_data(user_id)
    return render_template("user_cases_showcase.html", user=user, **users_cases_showcase_data)
