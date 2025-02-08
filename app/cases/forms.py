from flask_wtf import FlaskForm
from wtforms import SelectField, FileField, HiddenField, SubmitField
from wtforms.validators import DataRequired, ValidationError


class CreateScavCaseForm(FlaskForm):
    scav_case_type = SelectField(
        "Scav Case Type",
        choices=[
            ("₽2500", "₽2500"),
            ("₽15000", "₽15000"),
            ("₽95000", "₽95000"),
            ("Moonshine", "Moonshine"),
            ("Intelligence", "Intelligence"),
        ],
        validators=[DataRequired()],
    )

    items_data = HiddenField("Items Data")
    scav_case_image = FileField("Upload an Image")
    submit = SubmitField("Submit Scav Case")

    def validate_items_data(form, field):
        if not form.scav_case_image.data:
            if not field.data or field.data == "[]":
                raise ValidationError(
                    "You must select at least one item for a scav case"
                )

class UpdateScavCaseForm(FlaskForm):
    items_data = HiddenField("Items Data")
    submit = SubmitField("Submit Scav Case")