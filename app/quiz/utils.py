import random

from app.models import WeaponAttachment


def generate_quiz_options(correct_value, modifier_type, num_options=3):
    """
    Generate random options for the quiz, including the correct answer.

    :param correct_value: The correct recoil or ergonomics modifier.
    :param modifier_type: Either 'recoil' or 'ergonomics' to specify which modifier type to pull from.
    :param num_options: Total number of options to generate (including the correct answer).
    :return: A shuffled list of options.
    """
    all_attachments = WeaponAttachment.query.all()
    incorrect_options = set()

    while len(incorrect_options) < num_options - 1:
        random_attachment = random.choice(all_attachments)

        if modifier_type == "recoil":
            value = random_attachment.recoil_modifier
        elif modifier_type == "ergonomics":
            value = random_attachment.ergonomics_modifier

        if value != correct_value:
            incorrect_options.add(value)

    options = list(incorrect_options) + [correct_value]
    random.shuffle(options)

    return options
