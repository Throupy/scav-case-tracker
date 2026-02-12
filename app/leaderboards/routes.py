from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy import func

from app.models import User, ScavCase, ScavCaseItem
from app.constants import LEADERBOARD_METRICS
from app.extensions import db
from app.leaderboards.utils import leaderboard_base_query


leaderboards_bp = Blueprint("leaderboards", __name__)

@leaderboards_bp.route("/leaderboards")
def index():
    metric = request.args.get("metric", "total_profit")
    if metric not in LEADERBOARD_METRICS:
        metric = "total_profit"

    rows = []
    for r in leaderboard_base_query().all():
        avg_profit = (r.total_profit / r.case_count) if r.case_count else 0

        rows.append({
            "username": r.username,
            "image_file": r.image_file,
            "total_profit": float(r.total_profit),
            "case_count": int(r.case_count),
            "avg_profit": float(avg_profit),
            "most_expensive_item": float(r.most_expensive_item),
            "no_of_cases": int(r.case_count),
        })

    rows.sort(
        key=lambda x: x.get(metric, 0),
        reverse=True
    )

    m = LEADERBOARD_METRICS[metric]

    return render_template(
        "leaderboards.html",
        data=rows,
        metric=metric,
        metric_title=m["title"],
        metric_desc=m["desc"],
        metrics=[(k, v["title"], v["desc"]) for k, v in LEADERBOARD_METRICS.items()],
    )
