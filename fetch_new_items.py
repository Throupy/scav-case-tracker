"""
Tarkov Item Updater Script

This script fetches new items from the Tarkov API and updates the local SQLite database.
It also downloads item images and uploads them to Cloudinary.

Features:
- Fetches new items from the Tarkov API
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


def generate_item_price_query() -> str:
    """Generate a GraphQL query to retrieve all items information"""
    return """{
        items { id name image512pxLink category { name } }
    }"""


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
        correct_category = CATEGORY_MAPPING.get(row["category"]["name"], "Unknown")

        try:
            cursor.execute("BEGIN TRANSACTION;")
            cursor.execute(
                "INSERT INTO tarkov_item (name, tarkov_id, category) VALUES (?, ?, ?)",
                (row["name"], row["id"], correct_category),
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
    image_link = row["image512pxLink"]
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


def fetch_tarkov_items():
    """Fetch new Tarkov items from the API."""
    query = generate_item_price_query()
    try:
        response = requests.post(
            "https://api.tarkov.dev/graphql",
            headers={"Content-Type": "application/json"},
            json={"query": query},
            timeout=10,
        )

        if response.status_code != 200:
            logging.error(f"API request failed: {response.status_code} - {response.text}")
            return []

        data = response.json()

        if "data" not in data or "items" not in data["data"]:
            logging.error("API response structure is invalid")
            return []

        return data["data"]["items"]

    except requests.RequestException as err:
        logging.error(f"API request error: {str(err)}")
        return []


def add_new_items(db_file: str, dry_run: bool = False):
    """Fetch new items and add them to the database."""
    local_item_ids = get_local_db_item_ids(db_file)
    rows = fetch_tarkov_items()
    new_items_count = 0

    for row in rows:
        if row["id"] not in local_item_ids:
            if not dry_run:
                add_item_to_database(row, db_file)
                image_filepath = download_item_image(row, "/tmp")
                upload_image_to_cloudinary(image_filepath)
                new_items_count += 1
            else:
                logging.info(f"[!] Would add item: '{row['name']}' (Dry-Run Mode)")

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
