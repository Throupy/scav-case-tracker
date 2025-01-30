from datetime import datetime
from dataclasses import dataclass

from sqlalchemy.ext.hybrid import hybrid_property
from flask_login import UserMixin

from app.extensions import db


@dataclass
class Insight:
    title: str
    description: str
    chart_data: dict
    chart_tooltip: str


class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cost = db.Column(db.Float, nullable=False, default=0)
    # can't call it 'return', bloody python
    _return = db.Column(db.Float, nullable=False, default=0)
    type = db.Column(db.String(50), nullable=False)
    number_of_items = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    items = db.relationship("EntryItem", backref="entry", cascade="all, delete")

    @hybrid_property
    def profit(self):
        if self._return:
            return self._return - self.cost
        return 0  # If _return is None, profit is 0


class EntryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tarkov_id = db.Column(db.String(50), db.ForeignKey("tarkov_item.tarkov_id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # item name
    amount = db.Column(db.Integer, nullable=False)  # number of that item
    price = db.Column(db.Float, nullable=False)  # price of the item
    entry_id = db.Column(
        db.Integer, db.ForeignKey("entry.id"), nullable=False
    )  # reference to Entry

    tarkov_item = db.relationship("TarkovItem", backref="entry_items", primaryjoin="EntryItem.tarkov_id == TarkovItem.tarkov_id")


class TarkovItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # item name
    tarkov_id = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(64), nullable=True)


class WeaponAttachment(db.Model):
    id = db.Column(db.Integer, db.ForeignKey("tarkov_item.id"), primary_key=True)
    tarkov_item = db.relationship("TarkovItem", backref="attachment")
    recoil_modifier = db.Column(db.Float)
    ergonomics_modifier = db.Column(db.Float)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default="default.jpg")
    password = db.Column(db.String(60), nullable=False)
    entries = db.relationship("Entry", backref="author", lazy=True)
