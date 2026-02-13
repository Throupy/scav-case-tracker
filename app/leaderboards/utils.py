from sqlalchemy import func

from app.extensions import db
from app.models import ScavCase, ScavCaseItem, User

def leaderboard_base_query():
    profit_sq = (
        db.session.query(
            ScavCase.user_id.label("user_id"),
            func.sum(
                func.coalesce(ScavCase._return, 0) -
                func.coalesce(ScavCase.cost, 0)
            ).label("total_profit"),
            func.count(ScavCase.id).label("case_count"),
        )
        .group_by(ScavCase.user_id)
        .subquery()
    )

    item_sq = (
        db.session.query(
            ScavCase.user_id.label("user_id"),
            func.max(func.coalesce(ScavCaseItem.price, 0)).label("most_expensive_item"),
        )
        .join(ScavCase, ScavCase.id == ScavCaseItem.scav_case_id)
        .group_by(ScavCase.user_id)
        .subquery()
    )

    return (
        db.session.query(
            User.id.label("user_id"),
            User.username.label("username"),
            User.image_file.label("image_file"),
            func.coalesce(profit_sq.c.total_profit, 0).label("total_profit"),
            func.coalesce(profit_sq.c.case_count, 0).label("case_count"),
            func.coalesce(item_sq.c.most_expensive_item, 0).label("most_expensive_item"),
        )
        .outerjoin(profit_sq, profit_sq.c.user_id == User.id)
        .outerjoin(item_sq, item_sq.c.user_id == User.id)
    )
