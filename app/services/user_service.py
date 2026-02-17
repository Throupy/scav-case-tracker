from flask import jsonify

from app.extensions import db
from app.services import BaseService
from app.models import User

class UserService(BaseService):
    """Service class for querying users and handling biz logic wrt users"""
    def get_user_by_id_or_404(self, user_id) -> User:
        return User.query.get_or_404(user_id)

    def save_user_global_dashboard_layout(self, user_id, layout):
        """Save the user's global dashboard layout, hit by cases/ route"""
        if not isinstance(layout, list):
            return jsonify({"error": "layout must be a list"}), 400

        user = self.get_user_by_id_or_404(user_id)
        user.scav_case_global_dashboard_layout = layout
        db.session.commit()
        return jsonify({"ok": True})