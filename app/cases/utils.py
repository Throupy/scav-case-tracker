import os
import re
import json
import secrets
from collections import defaultdict

import requests
import pytesseract
from PIL import Image, ImageFilter
from flask import current_app
from rapidfuzz import process, fuzz
from werkzeug.utils import secure_filename

from app.models import Insight, TarkovItem, Entry, EntryItem
from app.extensions import db


class ItemNotFoundException(Exception):
    pass


def generate_price_query(item_id):
    return (
        """
    {
        items(ids: "%s") {
            sellFor {
                price
                source
            }
        }
    }
    """
        % item_id
    )


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


def run_query(query):
    headers = {"Content-Type": "application/json"}
    response = requests.post(
        "https://api.tarkov.dev/graphql", headers=headers, json={"query": query}
    )
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(
            "Query failed to run by returning code of {}. {}".format(
                response.status_code, query
            )
        )


def get_image_link(item_id: str) -> str:
    query = generate_image_query(item_id)
    result = run_query(query)
    return result["data"]["items"][0]["iconLink"]


def get_price(item_id: str) -> int:
    query = generate_price_query(item_id)
    result = run_query(query)
    sell_for_list = result["data"]["items"][0]["sellFor"]
    # some stuff you just can't sell? e.g. GP Coin
    if len(sell_for_list) == 0:
        return None
    # try to get the flea market price
    flea_market_price = next(
        (item for item in sell_for_list if item["source"] == "fleaMarket"), None
    )
    if flea_market_price:
        print(f"Got price of {flea_market_price['price']} for item with ID: {item_id}")
        return flea_market_price["price"]
    # if no flea market possible (e.g. BTC)
    max_price_item = max(sell_for_list, key=lambda x: x["price"])
    print(
        "No flea market price available. Highest price from other sources is {} from {}.".format(
            max_price_item["price"], max_price_item["source"]
        )
    )
    return max_price_item["price"]


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


def fuzzy_match_ocr_to_database(ocr_text: str):
    """
    Perform a fuzzy match of OCR text to item names in the database.

    Args:
        ocr_text (str): The text extracted from OCR.

    Returns:
        TarkovItem or None: The best matching TarkovItem if found, None otherwise.
    """
    all_items = TarkovItem.query.with_entities(TarkovItem.name).all()
    item_names = [item[0] for item in all_items]
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
    print(f"[DEBUG] Extracting Items from OCR Text : {text}")
    item_pattern = r"([A-Za-z0-9\s\.\'\-\(\)x]+)\s+\(([\d\/]+)\)"
    matches = re.findall(item_pattern, text)
    print(f"[DEBUG] Found {len(matches)} items within the text")

    items = []
    for match in matches:
        item_name = match[0].strip()
        quantity = match[1].strip()
        matched_item = fuzzy_match_ocr_to_database(item_name)
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


def create_scav_case_entry(scav_case_type, items, user_id):
    """Creates a scav case entry and associated items in the database."""
    entry = Entry(type=scav_case_type, user_id=user_id)
    if scav_case_type.lower() == "moonshine":
        entry.cost = get_price("5d1b376e86f774252519444e")
    elif scav_case_type.lower() == "intelligence":
        entry.cost = get_price("5c12613b86f7743bbe2c3f76")
    else:
        entry.cost = int(scav_case_type.replace("₽", "").strip())

    db.session.add(entry)
    db.session.commit()

    for item in items:
        entry_item = EntryItem(
            entry_id=entry.id,
            tarkov_id=item["id"],
            price=get_price(item["id"]),
            name=item["name"],
            amount=item["quantity"],
        )
        db.session.add(entry_item)
        entry.number_of_items += 1
        entry._return += entry_item.price * item["quantity"]

    db.session.commit()
    return entry


def calculate_insights(entries):
    """Compute multiple insights dynamically"""
    insight_functions = {
        "Most Profitable Case": calculate_most_profitable,
        "Average Return by Case Type": calculate_avg_return_by_case_type,
        "Average Items per Case Type": calculate_avg_items_per_case_type,
    }

    insights = [func(entries) for func in insight_functions.values()]
    return [insight for insight in insights if insight is not None]

def find_most_common_items(entries, top_n = 3):
    """Find the top N most common items across all entries."""
    item_counts = defaultdict(int)
    tarkov_item_map = {}

    for entry in entries:
        for item in entry.items:
            item_counts[item.tarkov_id] += 1
            tarkov_item_map[item.tarkov_id] = item

    if not item_counts:
        return []

    sorted_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return [(tarkov_item_map[tarkov_id], count) for tarkov_id, count in sorted_items]

def calculate_item_category_distribution(entries):
    category_counts = defaultdict(int)

    for entry in entries:
        for item in entry.items:
            category_counts[item.tarkov_item.category] += 1

    if not category_counts:
        return {"labels": [], "values": []}

    return {
        "labels": list(category_counts.keys()),
        "values": list(category_counts.values()),
    }

def calculate_most_profitable(entries):
    """Find the scav case type with the highest average profit."""
    profit_by_case_type = defaultdict(float)
    count_by_case_type = defaultdict(int)

    for entry in entries:
        if entry._return is not None:
            profit = entry._return - entry.cost
            profit_by_case_type[entry.type] += profit
            count_by_case_type[entry.type] += 1

    if not profit_by_case_type:
        return None

    avg_profit_by_case_type = {
        case_type: profit_by_case_type[case_type] / count_by_case_type[case_type]
        for case_type in profit_by_case_type
    }

    most_profitable_case_type = max(avg_profit_by_case_type, key=avg_profit_by_case_type.get)
    avg_profit = avg_profit_by_case_type[most_profitable_case_type]

    return {
        "type": most_profitable_case_type, 
        "avg_profit": avg_profit,  
        "chart_data": { 
            "x_value": list(avg_profit_by_case_type.keys()),
            "y_value": list(avg_profit_by_case_type.values()),
        },
    }


def calculate_avg_items_per_case_type(entries):
    """Calculate the average number of items per scav case type."""
    total_items_by_case_type = defaultdict(int)
    count_by_case_type = defaultdict(int)

    for entry in entries:
        total_items_by_case_type[entry.type] += len(entry.items)
        count_by_case_type[entry.type] += 1

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

def calculate_most_popular_categories(entries, top_n = 3):
    """Find the top N most frequently appearing item categories across all scav cases."""
    category_counts = defaultdict(int)
    category_map = {}

    for entry in entries:
        for item in entry.items:
            category_counts[item.tarkov_item.category] += 1
            category_map[item.tarkov_item.category] = item.tarkov_item 

    if not category_counts:
        return []

    sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return [(category_map[category], count) for category, count in sorted_categories]


def calculate_avg_return_by_case_type(entries):
    """Calculate the average return for each scav case type."""
    total_return_by_case_type = defaultdict(float)
    count_by_case_type = defaultdict(int)

    for entry in entries:
        if entry._return is not None:
            total_return_by_case_type[entry.type] += entry._return
            count_by_case_type[entry.type] += 1

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
                round(total_return_by_case_type[case_type] / count_by_case_type[case_type])
                for case_type in total_return_by_case_type
            ],
        },
    }