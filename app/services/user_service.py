from app.services import BaseService
from app.models import User

class UserService(BaseService):
    """Service class for querying users and handling biz logic wrt users"""
    def get_user_by_id_or_404(self, user_id) -> User:
        return User.query.get_or_404(user_id)