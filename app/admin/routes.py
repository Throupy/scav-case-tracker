from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import current_user

from app.auth.decorators import superuser_required
from app.admin.forms import CreateUserForm
from app.models import User, UserAchievement
from app.extensions import db, bcrypt


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/users")
@superuser_required
def users():
    all_users = User.query.order_by(User.is_superuser.desc(), User.username.asc()).all()
    form = CreateUserForm()
    return render_template("admin/users.html", users=all_users, form=form)


@admin_bp.route("/users/create", methods=["POST"])
@superuser_required
def create_user():
    form = CreateUserForm()
    if form.validate_on_submit():
        hashed = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        user = User(username=form.username.data, password=hashed, force_password_change=True)
        db.session.add(user)
        db.session.commit()
        flash(f"User '{user.username}' created. They will be prompted to change their password on first login.", "success")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "danger")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@superuser_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin.users"))
    username = user.username
    UserAchievement.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    flash(f"User '{username}' and all their data have been permanently deleted.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/promote", methods=["POST"])
@superuser_required
def promote_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.is_superuser:
        flash(f"'{user.username}' is already a superuser.", "info")
    else:
        user.is_superuser = True
        db.session.commit()
        flash(f"'{user.username}' has been promoted to superuser.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/demote", methods=["POST"])
@superuser_required
def demote_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.id == current_user.id:
        flash("You cannot demote yourself.", "danger")
    elif not user.is_superuser:
        flash(f"'{user.username}' is not a superuser.", "info")
    else:
        user.is_superuser = False
        db.session.commit()
        flash(f"'{user.username}' has been demoted.", "success")
    return redirect(url_for("admin.users"))
