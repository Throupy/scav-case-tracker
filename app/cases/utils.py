import os
import re
import json
import secrets
from collections import defaultdict
from typing import Iterable, Optional

import requests
import pytesseract
from PIL import Image, ImageFilter
from flask import flash, current_app
from rapidfuzz import process, fuzz
from sqlalchemy.orm import selectinload
from werkzeug.utils import secure_filename

from app.constants import ACHIEVEMENT_CHECKS, ACHIEVEMENT_METADATA
from app.models import Insight, TarkovItem, ScavCase, ScavCaseItem, UserAchievement, User
from app.extensions import db


class ItemNotFoundException(Exception):
    pass


def generate_image_query(item_id):
    return (
        """
    {
        items(ids: "%s") {
            id
            name
            iconLink
        }
    }
    """
        % item_id
    )


def validate_scav_case_image(image_path: str) -> bool:
    """
    Validate whether an image is a scav case image by checking for specific text.

    This function performs the following steps:
    1. Opens and processes the image (converts to grayscale and sharpens).
    2. Extracts text from the image using OCR.
    3. Checks for the presence of the phrase "scavs have brought you" in the extracted text.

    Args:
        image_path (str): The file path of the image to be validated.

    Returns:
        bool: True if the image is likely a scav case image (confidence >= 75%),
              False otherwise.

    Note:
        The function uses fuzzy matching to allow for slight variations or OCR errors
        in the target phrase "scavs have brought you".
    """
    img = Image.open(image_path)
    img = img.convert("L")
    img = img.filter(ImageFilter.SHARPEN)
    text_data = pytesseract.image_to_string(img)
    confidence = fuzz.partial_ratio("scavs have brought you", text_data.lower())
    if confidence >= 75:
        return True
    return False


def fuzzy_match_ocr_to_database(ocr_text: str, item_names: list[str]) -> str | None:
    """
    Perform a fuzzy match of OCR text to item names in the database.

    Args:
        ocr_text (str): The text extracted from OCR.
        item_names (list[str]): the item names to search through

    Returns:
        TarkovItem or None: The best matching TarkovItem if found, None otherwise.
    """
    best_match = process.extractOne(ocr_text, item_names, scorer=fuzz.ratio)

    if best_match and best_match[1] > 50:
        matched_item = TarkovItem.query.filter_by(name=best_match[0]).first()
        return matched_item
    else:
        return None


def process_image_for_items(image_path: str) -> str:
    img = Image.open(image_path)
    img = img.convert("L")
    img = img.filter(ImageFilter.SHARPEN)
    text = pytesseract.image_to_string(img)
    return text


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in current_app.config["ALLOWED_EXTENSIONS"]
    )


def extract_items_from_ocr(text: str):
    """
    Extract item information from OCR text.

    Args:
        text (str): The OCR text to process.

    Returns:
        list: A list of dictionaries containing item information.

    Raises:
        ItemNotFoundException: If an item is not recognized in the database.
    """
    current_app.logger.info(f"[DEBUG] Extracting Items from OCR Text : {text}")
    item_pattern = r"([A-Za-z0-9\s\.\'\-\(\)x]+)\s+\(([\d\/]+)\)"
    matches = re.findall(item_pattern, text)
    current_app.logger.info(f"[DEBUG] Found {len(matches)} items within the text")
    
    all_items = TarkovItem.query.with_entities(TarkovItem.tarkov_id, TarkovItem.name).all()
    item_names = [name for _, name in all_items]
    name_to_item = {name: tid for tid, name in all_items}

    items = []
    for match in matches:
        item_name = match[0].strip()
        quantity = match[1].strip()
        matched_item = fuzzy_match_ocr_to_database(item_name, item_names)
        if matched_item:
            items.append(
                {
                    "id": matched_item.tarkov_id,
                    "name": matched_item.name,
                    "quantity": int(quantity),
                }
            )
        else:
            raise ItemNotFoundException(
                "One of the items wasn't recognised. Please add the case manually."
            )
    return items


def save_uploaded_image(uploaded_image):
    """Saves the uploaded image to the server and returns the file path."""
    filename = secure_filename(uploaded_image.filename)
    file_path = os.path.join(current_app.root_path, "static/uploads", filename)
    uploaded_image.save(file_path)
    return file_path


def process_scav_case_image(file_path):
    """
    Validate and process an image of a scav case to extract item data using OCR.

    This function performs the following steps:
    1. Validates that the image is indeed a scav case image.
    2. Processes the image to extract text using OCR.
    3. Extracts item information from the OCR text.

    Args:
        file_path (str): The path to the image file to be processed.

    Returns:
        list: A list of dictionaries containing extracted item information.
              Each dictionary contains 'id', 'name', and 'quantity' of an item.

    Raises:
        ValueError: If the image is not recognized as a valid scav case image.
        ItemNotFoundException: If any extracted item is not recognized in the database.

    Note:
        The image should clearly show the text "Scavs have brought you" at the top
        for it to be considered a valid scav case image.
    """
    if not validate_scav_case_image(file_path):
        raise ValueError(
            "The uploaded image doesn't look like a scav case. Make sure the text that reads 'Scavs have brought you' at the top is visible within the image."
        )

    ocr_text = process_image_for_items(file_path)
    return extract_items_from_ocr(ocr_text)


def calculate_insights(scav_cases):
    """Compute multiple insights dynamically"""
    insight_functions = {
        "Most Profitable Case": calculate_most_profitable,
        "Average Return by Case Type": calculate_avg_return_by_case_type,
        "Average Items per Case Type": calculate_avg_items_per_case_type,
    }

    insights = [func(scav_cases) for func in insight_functions.values()]
    return [insight for insight in insights if insight is not None]


def find_most_common_items(scav_cases, top_n=3):
    """Find the top N most common items across all scav cases."""
    item_counts = defaultdict(int)
    tarkov_item_map = {}

    for scav_case in scav_cases:
        for item in scav_case.items:
            item_counts[item.tarkov_id] += 1
            tarkov_item_map[item.tarkov_id] = item

    if not item_counts:
        return []

    sorted_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return [(tarkov_item_map[tarkov_id], count) for tarkov_id, count in sorted_items]


def calculate_item_category_distribution(scav_cases):
    category_counts = defaultdict(int)

    for scav_case in scav_cases:
        for item in scav_case.items:
            category_counts[item.tarkov_item.category] += 1

    if not category_counts:
        return {"labels": [], "values": []}

    return {
        "labels": list(category_counts.keys()),
        "values": list(category_counts.values()),
    }


def calculate_most_profitable(scav_cases):
    """Find the scav case type with the highest average profit."""
    profit_by_case_type = defaultdict(float)
    count_by_case_type = defaultdict(int)

    for scav_case in scav_cases:
        if scav_case._return is not None:
            profit = scav_case._return - scav_case.cost
            profit_by_case_type[scav_case.type] += profit
            count_by_case_type[scav_case.type] += 1

    if not profit_by_case_type:
        return None

    avg_profit_by_case_type = {
        case_type: profit_by_case_type[case_type] / count_by_case_type[case_type]
        for case_type in profit_by_case_type
    }

    most_profitable_case_type = max(
        avg_profit_by_case_type, key=avg_profit_by_case_type.get
    )
    avg_profit = avg_profit_by_case_type[most_profitable_case_type]

    return {
        "type": most_profitable_case_type,
        "avg_profit": avg_profit,
        "chart_data": {
            "x_value": list(avg_profit_by_case_type.keys()),
            "y_value": list(avg_profit_by_case_type.values()),
        },
    }


def calculate_avg_items_per_case_type(scav_cases):
    """Calculate the average number of items per scav case type."""
    total_items_by_case_type = defaultdict(int)
    count_by_case_type = defaultdict(int)

    for scav_case in scav_cases:
        total_items_by_case_type[scav_case.type] += len(scav_case.items)
        count_by_case_type[scav_case.type] += 1

    if not total_items_by_case_type:
        return None

    return {
        "chart_data": {
            "x_value": list(total_items_by_case_type.keys()),
            "y_value": [
                total_items_by_case_type[case_type] / count_by_case_type[case_type]
                for case_type in total_items_by_case_type
            ],
        },
    }


def calculate_most_popular_categories(scav_cases, top_n=3):
    """Find the top N most frequently appearing item categories across all scav cases."""
    category_counts = defaultdict(int)
    category_map = {}

    for scav_case in scav_cases:
        for item in scav_case.items:
            category_counts[item.tarkov_item.category] += 1
            category_map[item.tarkov_item.category] = item.tarkov_item

    if not category_counts:
        return []

    sorted_categories = sorted(
        category_counts.items(), key=lambda x: x[1], reverse=True
    )[:top_n]
    return [(category_map[category], count) for category, count in sorted_categories]


def calculate_avg_return_by_case_type(scav_cases):
    """Calculate the average return for each scav case type."""
    total_return_by_case_type = defaultdict(float)
    count_by_case_type = defaultdict(int)

    for scav_case in scav_cases:
        if scav_case._return is not None:
            total_return_by_case_type[scav_case.type] += scav_case._return
            count_by_case_type[scav_case.type] += 1

    if not total_return_by_case_type:
        return None

    avg_return_by_case_type = {
        case_type: total_return_by_case_type[case_type] / count_by_case_type[case_type]
        for case_type in total_return_by_case_type
    }

    return {
        "chart_data": {
            "x_value": list(avg_return_by_case_type.keys()),
            "y_value": [
                round(
                    total_return_by_case_type[case_type] / count_by_case_type[case_type]
                )
                for case_type in total_return_by_case_type
            ],
        },
    }

def check_achievements(user):
    """Check which achievements a user qualifies for and unlock them"""
    # Eagerly load scav_cases + items in 2 queries to avoid N+1 inside the lambda checks
    user_loaded = (
        db.session.query(User)
        .options(selectinload(User.scav_cases).selectinload(ScavCase.items))
        .filter(User.id == user.id)
        .one()
    )
    unlocked_achievements = {a.achievement_name for a in user_loaded.achievements}
    # TODO: What if a scav case is deleted, or the items changed. Achievements should be removed
    # TODO: Create new lock_achievement (or similar) function
    # TODO: Will need to add checks in the scav_case_service.py
    for achievement_name, check_func in ACHIEVEMENT_CHECKS.items():
        if achievement_name not in unlocked_achievements and check_func(user_loaded):
            unlock_achievement(user_loaded, achievement_name)

def unlock_achievement(user, achievement_name):
    """Unlock an achievement and store it in the database."""
    new_achievement = UserAchievement(user_id=user.id, achievement_name=achievement_name)
    db.session.add(new_achievement)
    db.session.commit()

    flash(f"🎉 Achievement Unlocked: {achievement_name}!", "success")

def is_discord_bot_request(request):
    """Check if a request is from discord bot with valid credentials"""
    bot_header = request.headers.get("X-BOT-REQUEST")
    bot_key = request.headers.get("X-BOT-KEY")
    expected_key = os.getenv("DISCORD_BOT_API_KEY")

    if not bot_key:
        return False

    if not expected_key:
        # TODO: This function should probably return ok, reason, status (bool, str|None, int).
        # In general, the consistency of responses from the service/view layer are just pretty inconsistent
        # and it needs to be sorted out. Currently, this will just crap out if this condition hits, and the user
        # won't get anything meaningful. Bit task of work, but needs done.
        error_text = "Retrieved a suspected discord bot request. Cannot proceed because DISCORD_BOT_API_KEY is not set"
        current_app.logger.error(error_text)
        return False

    return bot_header == "true" and bot_key == expected_key