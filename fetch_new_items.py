"""
Tarkov Item Updater Script

This script fetches new items from the Tarkov JSON API and updates the local
SQLite database. It also downloads item images and uploads them to Cloudinary.

Features:
- Fetches new items from the Tarkov JSON API (https://json.tarkov.dev)
- Adds missing items to the SQLite database
- Downloads item images
- Uploads images to Cloudinary
- Supports a "dry-run" mode for testing
- Can be run manually or scheduled as a cron job

Usage:
1. Run manually:
    python update_items.py --db-file /path/to/scav-case.db

2. Run in dry-run mode (no database modifications):
    python update_items.py --db-file /path/to/scav-case.db --dry-run

3. Schedule in cron (every 4 days at 3 AM):
    0 3 */4 * * /usr/bin/python3 /path/to/update_items.py --db-file /path/to/scav-case.db >> /var/log/scav_case_update.log 2>&1
    Note: This script has not been tested with a cron job - you may consider implementing a lockfile to ensure that the database doesn't corrupt!

Config (env vars, via .env):
    TARKOV_JSON_API_BASE_URL - default "https://json.tarkov.dev"
    TARKOV_GAME_MODE         - default "regular" (or "pve" / "pvp-season")
"""

import argparse
import logging
import os
import sqlite3

import requests
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

from app.constants import CATEGORY_MAPPING

load_dotenv()

logging.basicConfig(
    filename="/var/log/scav_case_update_items.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

DEFAULT_TARKOV_JSON_API_BASE_URL = "https://json.tarkov.dev"
DEFAULT_TARKOV_GAME_MODE = "regular"

UNKNOWN_CATEGORY_LABEL = "Unknown"


def _get_base_url() -> str:
    return os.getenv("TARKOV_JSON_API_BASE_URL", DEFAULT_TARKOV_JSON_API_BASE_URL)


def _get_game_mode() -> str:
    return os.getenv("TARKOV_GAME_MODE", DEFAULT_TARKOV_GAME_MODE)


def _build_url(path: str) -> str:
    return f"{_get_base_url()}/{_get_game_mode()}{path}"


def _prettify_slug(slug: str) -> str:
    """'colt-m4a1-556x45-assault-rifle' -> 'Colt M4A1 556x45 Assault Rifle'"""
    return slug.replace("-", " ").replace("_", " ").title()


def get_local_db_item_ids(db_file: str) -> list:
    """Retrieve existing item IDs from the database."""
    if not os.path.isfile(db_file):
        logging.error(f"[!] Database file '{db_file}' does not exist.")
        raise FileNotFoundError(f"Database file '{db_file}' not found.")

    with sqlite3.connect(db_file) as connection:
        cursor = connection.cursor()
        query_response = cursor.execute("SELECT tarkov_id FROM tarkov_item;")
        rows_ids = query_response.fetchall()
        return [row[0] for row in rows_ids]  # Convert from tuple (id,) to list of IDs


def add_item_to_database(row: dict, db_file: str) -> None:
    """Insert a new item into the database."""
    with sqlite3.connect(db_file) as connection:
        cursor = connection.cursor()
        cursor.execute("PRAGMA busy_timeout = 5000;")  # Wait up to 5s if DB is locked

        try:
            cursor.execute("BEGIN TRANSACTION;")
            cursor.execute(
                "INSERT INTO tarkov_item (name, tarkov_id, category) VALUES (?, ?, ?)",
                (row["name"], row["id"], row["category"]),
            )
            connection.commit()
            logging.info(
                f"[*] Added Tarkov item with name '{row['name']}' and ID '{row['id']}' to the database"
            )
        except sqlite3.Error as err:
            connection.rollback()
            logging.error(f"[!] Database Error: {err}")
            raise


def download_item_image(row: dict, output_directory: str) -> str:
    """Download the item image and save it to the specified directory."""
    image_link = row["image_link"]
    output_filename = image_link.split("/")[-1].replace("-512", "")
    output_filepath = os.path.join(output_directory, output_filename)

    response = requests.get(image_link, stream=True)
    if response.status_code == 200:
        with open(output_filepath, "wb") as output_file:
            for chunk in response.iter_content(1024):
                output_file.write(chunk)

        logging.info(f"[*] Wrote image from {image_link} to {output_filepath}")
    return output_filepath


def upload_image_to_cloudinary(filepath: str) -> None:
    """Upload the image to Cloudinary."""
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_SECRET"),
        secure=True,
    )

    if os.path.isfile(filepath):
        response = cloudinary.uploader.upload(
            filepath,
            use_filename=True,
            unique_filename=False,
            overwrite=True,
        )
        logging.info(f"[*] Uploaded file: {filepath} to Cloudinary CDN...")


def fetch_category_names(payload: dict) -> dict[str, str]:
    """
    Extract category id -> display name from the "itemCategories" dataset
    that's bundled alongside "items" under the /items endpoint's "data".

    Confirmed shape (2026-08-20):
        data.itemCategories = {
            category_id: {"id", "name" (placeholder junk, e.g. "<id> Name"),
                           "normalizedName" (real slug, e.g. "assault-rifle"),
                           "parent", "children"},
            ...
        }
    """
    categories = (payload.get("data") or {}).get("itemCategories")

    if not isinstance(categories, dict):
        logging.warning(
            "[!] Could not find an 'itemCategories' dict under data - the "
            "API shape may have changed again. All items will be "
            "categorised as 'Unknown' until this is fixed."
        )
        return {}

    names: dict[str, str] = {}
    for category_id, category in categories.items():
        if not isinstance(category, dict):
            continue
        normalized = category.get("normalizedName")
        if normalized:
            names[category_id] = _prettify_slug(normalized)

    return names


def fetch_tarkov_items() -> list[dict]:
    """
    Fetch all items (and their categories) from the JSON API in a single
    request, and normalise them into the shape the rest of this script
    expects: {id, name, category, image_link}.
    """
    try:
        response = requests.get(_build_url("/items"), timeout=(3, 30))
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as err:
        logging.error(f"[!] API request error: {err}")
        return []

    raw_items = (payload.get("data") or {}).get("items")
    if not isinstance(raw_items, dict):
        logging.error("[!] API response structure is invalid")
        return []

    category_names = fetch_category_names(payload)

    normalised_items = []
    for item_id, item in raw_items.items():
        # "name" is placeholder text on this API (e.g. "<id> Name"), not a
        # real display name - normalizedName is the real slug, so use that.
        normalized_name = item.get("normalizedName")
        display_name = _prettify_slug(normalized_name) if normalized_name else item.get("name")

        item_category_ids = item.get("categories") or []
        category_name = UNKNOWN_CATEGORY_LABEL
        for category_id in item_category_ids:
            if category_id in category_names:
                category_name = category_names[category_id]
                break
        # keep CATEGORY_MAPPING in the loop so existing DB category labels
        # stay consistent, falling back to whatever we resolved above
        category_name = CATEGORY_MAPPING.get(category_name, category_name)

        normalised_items.append(
            {
                "id": item_id,
                "name": display_name,
                "category": category_name,
                "image_link": item.get("image512pxLink"),
            }
        )

    return normalised_items


def add_new_items(db_file: str, dry_run: bool = False):
    """Fetch new items and add them to the database."""
    local_item_ids = get_local_db_item_ids(db_file)
    rows = fetch_tarkov_items()
    new_items_count = 0

    for row in rows:
        if row["id"] not in local_item_ids:
            if not dry_run:
                add_item_to_database(row, db_file)
                if row["image_link"]:
                    image_filepath = download_item_image(row, "/tmp")
                    upload_image_to_cloudinary(image_filepath)
                new_items_count += 1
            else:
                logging.info(
                    f"[DRY-RUN] Would add item: {row['id']} {row['name']!r} "
                    f"category={row['category']!r} image={row['image_link']!r}"
                )
                print(
                    f"[DRY-RUN] {row['id']} {row['name']} "
                    f"| category: {row['category']} | image: {row['image_link']}"
                )

    logging.info(
        f"Job Complete - {new_items_count} items were added to the database and their images uploaded to the CDN"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and update Tarkov items in the database.")
    parser.add_argument("--db-file", required=True, help="Path to the SQLite database file.")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry mode without modifying the database.")

    args = parser.parse_args()

    try:
        add_new_items(args.db_file, dry_run=args.dry_run)
    except Exception as e:
        logging.error(f"[!] Script execution failed: {e}")
