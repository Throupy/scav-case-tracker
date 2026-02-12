from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user, login_required

from app.models import UserAchievement, User
from app.constants import ACHIEVEMENT_METADATA


achievements_bp = Blueprint("achievements", __name__)


@achievements_bp.route("/users/<user_id>/achievements")
@login_required
def user_achievements(user_id):
    user = User.query.filter_by(id=user_id).first()
    user_achievements = UserAchievement.query.filter_by(user_id=user_id).all()
    unlocked = {a.achievement_name: a.achieved_at for a in user_achievements}
    # unlocked first, most recent first
    sorted_achievements = sorted(
        ACHIEVEMENT_METADATA.items(), 
        key=lambda a: (-unlocked[a[0]].timestamp() if a[0] in unlocked else float("inf"))
    )
    return render_template(
        "achievements.html", achievements=sorted_achievements, 
        unlocked=unlocked, user=user
    )

@achievements_bp.get("/me/achievements")
@login_required
def my_achievements():
    return redirect(url_for("achievements.user_achievements", user_id=current_user.id))