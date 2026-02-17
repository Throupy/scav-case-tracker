from datetime import datetime
from dataclasses import dataclass

from sqlalchemy import event, insert
from sqlalchemy.orm import Session
from sqlalchemy.ext.hybrid import hybrid_property
from flask_login import UserMixin

from app.extensions import db
from app.constants import DEFAULT_TRACKED_ITEMS


@dataclass
class Insight:
    title: str
    description: str
    chart_data: dict
    chart_tooltip: str


class ScavCase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cost = db.Column(db.Float, nullable=False, default=0)
    # can't call it 'return', bloody python
    _return = db.Column(db.Float, nullable=False, default=0)
    type = db.Column(db.String(50), nullable=False)
    number_of_items = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    items = db.relationship("ScavCaseItem", backref="scav_case", cascade="all, delete")

    @hybrid_property
    def profit(self):
        if self._return:
            return self._return - self.cost
        return 0  # If _return is None, profit is 0


class ScavCaseItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tarkov_id = db.Column(
        db.String(50),
        db.ForeignKey("tarkov_item.tarkov_id", name="fk_scav_case_item_tarkov"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(100), nullable=False)  # item name
    amount = db.Column(db.Integer, nullable=False)  # number of that item
    price = db.Column(db.Float, nullable=False)  # price of the item
    scav_case_id = db.Column(
        db.Integer,
        db.ForeignKey("scav_case.id", name="fk_scav_case_item_scavcase"),
        nullable=False,
        index=True,
    )  # reference to case

    tarkov_item = db.relationship(
        "TarkovItem",
        backref="scav_case_items",
        primaryjoin="ScavCaseItem.tarkov_id == TarkovItem.tarkov_id",
    )


class TarkovItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # item name
    tarkov_id = db.Column(db.String(50), nullable=False, unique=True, index=True)
    category = db.Column(db.String(64), nullable=True)


class WeaponAttachment(db.Model):
    id = db.Column(db.Integer, db.ForeignKey("tarkov_item.id"), primary_key=True)
    tarkov_item = db.relationship("TarkovItem", backref="attachment")
    recoil_modifier = db.Column(db.Float)
    ergonomics_modifier = db.Column(db.Float)


# many to many association table
user_tracked_items = db.Table(
    "user_tracked_items",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("item_id", db.Integer, db.ForeignKey("tarkov_item.id"), primary_key=True),
)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default="default.jpg")
    password = db.Column(db.String(60), nullable=False)
    scav_case_global_dashboard_layout = db.Column(db.JSON, nullable=True)
    scav_cases = db.relationship("ScavCase", backref="author", lazy=True, cascade="all, delete-orphan")
    # many-to-many with TarkovItem (for market section tracking)
    tracked_items = db.relationship(
        "TarkovItem",
        secondary=user_tracked_items,
        backref="tracking_users",
        lazy="joined",
    )
    achievements = db.relationship("UserAchievement", backref='user', lazy='dynamic')


# upon user registration, add three default items to be tracked in the
# users personalised 'market' section.
@event.listens_for(User, "after_insert")
def add_default_items(mapper, connection, target):
    """Assign default tracked items after user creation using direct SQL insertion."""
    session = Session.object_session(target)
    if session is None:
        return

    tarkov_items = (
        session.query(TarkovItem.id)
        .filter(TarkovItem.name.in_(DEFAULT_TRACKED_ITEMS))
        .all()
    )

    if tarkov_items:
        item_ids = [item[0] for item in tarkov_items]
        connection.execute(
            insert(user_tracked_items),
            [{"user_id": target.id, "item_id": item_id} for item_id in item_ids],
        )


class UserAchievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    achievement_name = db.Column(db.String(100), nullable=False)
    achieved_at = db.Column(db.DateTime, default=datetime.utcnow)

    # make sure user cannot get same achievement twice
    __table_args__ = (db.UniqueConstraint("user_id", "achievement_name"), )