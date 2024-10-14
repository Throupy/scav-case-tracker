import discord

valid_types = {
    "₽2500": ["2500", "2.5k", "2k"],
    "₽15000": ["15000", "15k"],
    "₽95000": ["95000", "95k"],
    "Moonshine": ["moonshine", "ms"],
    "Intelligence": ["intelligence", "intel"],
}


def normalise_input(user_input):
    user_input = user_input.lower().strip()

    if any(char.isdigit() for char in user_input):
        user_input = user_input.replace("k", "000")
        user_input = "".join(c for c in user_input if c.isdigit() or c == "₽")

    return user_input


def get_matching_type(user_input):
    normalised_input = normalise_input(user_input)

    for valid_type, variations in valid_types.items():
        if normalised_input in variations:
            return valid_type

    return None


def create_basic_embed(text: str) -> discord.Embed:
    embed = discord.Embed(description=text, color=discord.Color.red())
    embed.set_footer(text="Scav Case Tracker Bot")
    embed.set_thumbnail(
        url="https://github.com/Throupy/scav-case-tracker/blob/00d1ebe13240f56f200b52b80214ff8fab69233b/app/static/icon.png?raw=true"
    )
    return embed
