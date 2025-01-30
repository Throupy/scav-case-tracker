from datetime import datetime

import humanize

def timeago(dt):
    """Convert datetime to a 'time ago' format"""
    if isinstance(dt, datetime):
        return humanize.naturaltime(datetime.utcnow() - dt)
    return dt