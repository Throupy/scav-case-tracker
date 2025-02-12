from datetime import datetime

import humanize

from app.models import TarkovItem


def timeago(dt):
    """Convert datetime to a 'time ago' format"""
    if isinstance(dt, datetime):
        return humanize.naturaltime(datetime.utcnow() - dt)
    return dt


def get_item_image_filename(item):
    """
    Return the correct filename for an item's image
    This is needed because in the case of guns, the correct image actually has
    'default' appended to the end. E.g. the image for an M4A1 Assault Rifle
    ACTUALLY is attached to the item with name 'M4A1 Assault Rifle Default'. The normal
    M4A1 image is just the weapon's chassis.
    """
    if isinstance(item, TarkovItem):
        category = item.category
    else:
        category = item.tarkov_item.category
    if category == "Guns":
        print(f"Finding where name = '{item.name} Default'")
        real_image_item = TarkovItem.query.filter_by(
            name=f"{item.name} Default"
        ).first()
        if real_image_item:
            return f"{real_image_item.tarkov_id}.webp"
    return f"{item.tarkov_id}.webp"
