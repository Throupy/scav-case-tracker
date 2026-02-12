from flask import Blueprint, render_template, request, jsonify, redirect, url_for

from app.models import WeaponAttachment
from app.extensions import db
from app.quiz.utils import generate_quiz_options

quiz_bp = Blueprint("quiz", __name__)


@quiz_bp.route("/quiz/<quiz_type>", methods=["GET", "POST"])
def quiz(quiz_type):
    if request.method == "POST":
        user_answer = float(request.form["selected_modifier"])
        attachment_id = int(request.form["attachment_id"])
        attachment = WeaponAttachment.query.get(attachment_id)

        if quiz_type == "recoil":
            correct_answer = attachment.recoil_modifier
        else:  # ergonomics
            correct_answer = attachment.ergonomics_modifier

        is_correct = user_answer == correct_answer

        return jsonify(
            {
                "is_correct": is_correct,
                "correct_answer": correct_answer,
                "attachment_name": attachment.tarkov_item.name,
            }
        )

    attachment = WeaponAttachment.query.order_by(db.func.random()).first()

    if quiz_type == "recoil":
        options = generate_quiz_options(attachment.recoil_modifier, "recoil")
        quiz_title = "Recoil Modifier Quiz"
        quiz_question = (
            f"What is the recoil modifier for {attachment.tarkov_item.name}?"
        )
    else:
        options = generate_quiz_options(attachment.ergonomics_modifier, "ergonomics")
        quiz_title = "Ergonomics Modifier Quiz"
        quiz_question = (
            f"What is the ergonomics modifier for {attachment.tarkov_item.name}?"
        )

    return render_template(
        "quiz.html",
        attachment=attachment,
        options=options,
        quiz_type=quiz_type,
        quiz_title=quiz_title,
        quiz_question=quiz_question,
    )
