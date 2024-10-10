import os
import re
import secrets
from collections import defaultdict

import requests
import pytesseract

from PIL import Image, ImageFilter
from flask import current_app
from rapidfuzz import process, fuzz

from app.models import Insight, TarkovItem


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


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(
        current_app.root_path, "static/profile_pics", picture_fn
    )

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


def calculate_avg_items_per_case_type(entries):
    total_items_by_case_type = defaultdict(int)
    count_by_case_type = defaultdict(int)

    for entry in entries:
        total_items_by_case_type[entry.type] += len(entry.items)
        count_by_case_type[entry.type] += 1

    avg_items_per_case_type = {
        case_type: total_items_by_case_type[case_type] / count_by_case_type[case_type]
        for case_type in total_items_by_case_type
    }

    chart_data = {
        "x_value": list(avg_items_per_case_type.keys()),
        "y_value": list(avg_items_per_case_type.values()),
        "colors": ["rgba(231, 74, 59, 1)" for _ in avg_items_per_case_type.keys()],
        "border_colors": [
            "rgba(231, 74, 59, 1)" for _ in avg_items_per_case_type.keys()
        ],
    }

    chart_tooltip = {
        case_type: f"Average items: {round(avg_items_per_case_type[case_type], 2)}"
        for case_type in avg_items_per_case_type
    }

    return Insight(
        title="Average Items per Case Type",
        description="This chart shows the average number of items per scav case type.",
        chart_data=chart_data,
        chart_tooltip=chart_tooltip,
    )


def calculate_avg_return_by_case_type(entries):
    total_return_by_case_type = defaultdict(float)
    count_by_case_type = defaultdict(int)

    for entry in entries:
        if entry._return is not None:
            total_return_by_case_type[entry.type] += entry._return
            count_by_case_type[entry.type] += 1

    average_return_by_case_type = {
        case_type: total_return_by_case_type[case_type] / count_by_case_type[case_type]
        for case_type in total_return_by_case_type
    }

    chart_data = {
        "x_value": list(average_return_by_case_type.keys()),
        "y_value": list(average_return_by_case_type.values()),
        "colors": ["rgba(231, 74, 59, 1)" for _ in average_return_by_case_type.keys()],
        "border_colors": [
            "rgba(231, 74, 59, 1)" for _ in average_return_by_case_type.keys()
        ],
    }

    # Tooltip text for each case type
    chart_tooltip = {
        case_type: f"Average return: ₽{round(average_return_by_case_type[case_type]):,}"
        for case_type in average_return_by_case_type
    }

    return Insight(
        title="Average Return by Case Type",
        description="This chart shows the average return for each scav case type.",
        chart_data=chart_data,
        chart_tooltip=chart_tooltip,
    )


def calculate_and_prepare_most_profitable(entries) -> Insight:
    profit_by_case_type = defaultdict(float)
    count_by_case_type = defaultdict(int)

    for entry in entries:
        if entry._return is not None:
            profit = entry._return - entry.cost
            profit_by_case_type[entry.type] += profit
            count_by_case_type[entry.type] += 1

    if not profit_by_case_type:
        return Insight(
            title="Most Profitable Case Type",
            description="No data available.",
            chart_data={
                "case_types": [],
                "profits": [],
                "colors": [],
                "border_colors": [],
            },
            chart_tooltip={},
        )

    most_profitable_case_type = max(profit_by_case_type.items(), key=lambda x: x[1])
    case_type = most_profitable_case_type[0]
    total_profit = most_profitable_case_type[1]
    number_of_runs = count_by_case_type[case_type]

    chart_data = {
        "x_value": list(profit_by_case_type.keys()),
        "y_value": list(profit_by_case_type.values()),
        "colors": [
            "rgba(28, 200, 138, 1)" if k == case_type else "rgba(231, 74, 59, 1)"
            for k in profit_by_case_type.keys()
        ],
        "border_colors": [
            "rgba(28, 200, 138, 1)" if k == case_type else "rgba(231, 74, 59, 1)"
            for k in profit_by_case_type.keys()
        ],
    }

    # Tooltip text for each case type
    chart_tooltip = {
        case_type: f"Profit: ₽{round(profit_by_case_type[case_type]):,} from {count_by_case_type[case_type]} runs"
        for case_type in profit_by_case_type
    }

    return Insight(
        title="Most Profitable Case Type",
        description=f"""The <strong>most profitable</strong> case type is <strong>{case_type}</strong>, returning a total profit of <strong>₽{round(total_profit):,}</strong>
            from a total of <strong>{number_of_runs}</strong> uses.""",
        chart_data=chart_data,
        chart_tooltip=chart_tooltip,
    )

def validate_scav_case_image(image_path: str) -> bool:
    img = Image.open(image_path)
    img = img.convert("L")
    img = img.filter(ImageFilter.SHARPEN)
    text_data = pytesseract.image_to_string(img)
    confidence = fuzz.partial_ratio("scavs have brought you", text_data.lower())
    if confidence >= 75:
        return True
    return False

def fuzzy_match_ocr_to_database(ocr_text: str):
    all_items = TarkovItem.query.with_entities(TarkovItem.name).all()
    item_names = [item[0] for item in all_items]
    best_match = process.extractOne(ocr_text, item_names, scorer=fuzz.ratio)

    if best_match and best_match[1] > 20:
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
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]


def extract_items_from_ocr(text: str):
    item_pattern = r"([A-Za-z0-9\s\.\'\-\(\)x]+)\s+\(([\d\/]+)\)"
    matches = re.findall(item_pattern, text)

    items = []
    for match in matches:
        item_name = match[0].strip()
        quantity = match[1].strip()
        # You could add fuzzy matching here if necessary
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
