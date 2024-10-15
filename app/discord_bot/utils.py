import discord

valid_types = {
    "₽2500": ["2500", "2.5k", "2k"],
    "₽15000": ["15000", "15k"],
    "₽95000": ["95000", "95k"],
    "Moonshine": ["moonshine", "ms"],
    "Intelligence": ["intelligence", "intel"],
}


def normalise_input(user_input):
    """
    Normalizes the user input by converting it to lowercase, stripping whitespace,
    and transforming shorthand notations. Specifically, it replaces 'k' with '000'
    for numeric values and retains only digits and the '₽' symbol.

    Args:
        user_input (str): The input string provided by the user.

    Returns:
        str: The normalized input string.
    """
    user_input = user_input.lower().strip()

    if any(char.isdigit() for char in user_input):
        user_input = user_input.replace("k", "000")
        user_input = "".join(c for c in user_input if c.isdigit() or c == "₽")

    return user_input


def get_matching_type(user_input):
    """
    Determines the valid scav case type based on user input.

    This function takes a user input string, normalizes it using the
    `normalise_input` function, and checks it against a predefined
    dictionary of valid scav case types and their variations. If a match
    is found, it returns the corresponding valid scav case type. If no
    match is found, it returns None.

    Args:
        user_input (str): The input string provided by the user.

    Returns:
        str or None: The valid scav case type if a match is found,
        otherwise None.
    """
    normalised_input = normalise_input(user_input)

    for valid_type, variations in valid_types.items():
        if normalised_input in variations:
            return valid_type

    return None


def create_basic_embed(text: str) -> discord.Embed:
    """
    Generate a simple embed with a description, a red color
    theme, a footer, and a thumbnail image.

    Args:
        text (str): The description text to be included in the embed.

    Returns:
        discord.Embed: The formatted embed object ready to be sent
    """
    embed = discord.Embed(description=text, color=discord.Color.red())
    embed.set_footer(text="Scav Case Tracker Bot")
    embed.set_thumbnail(
        url="https://github.com/Throupy/scav-case-tracker/blob/00d1ebe13240f56f200b52b80214ff8fab69233b/app/static/icon.png?raw=true"
    )
    return embed
