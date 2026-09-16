"""Review and import new Tarkov items from json.tarkov.dev."""

from __future__ import annotations

import os
from dataclasses import dataclass

import cloudinary
import cloudinary.uploader
import requests

from app.constants import CATEGORY_MAPPING
from app.extensions import db
from app.models import TarkovItem


DEFAULT_API_BASE_URL = "https://json.tarkov.dev"
DEFAULT_GAME_MODE = "regular"
GENERATED_PRESET_ID_PREFIX = "707265736574"


class ItemCatalogError(RuntimeError):
    """Raised when the upstream item catalogue cannot be read safely."""


@dataclass(frozen=True)
class ImportResult:
    imported: tuple[str, ...]
    skipped: tuple[str, ...]


def _prettify_slug(value: str) -> str:
    return value.replace("-", " ").replace("_", " ").title()


def _mapped_category(category_name: str) -> str | None:
    normalized = category_name.replace("-", " ").replace("_", " ").strip()
    mapping = {key.casefold(): value for key, value in CATEGORY_MAPPING.items()}
    return mapping.get(normalized.casefold())


def _is_generated_preset_id(item_id: str | None) -> bool:
    return bool(item_id and item_id.startswith(GENERATED_PRESET_ID_PREFIX))


def _eligibility(raw_items: dict[str, dict]) -> dict[str, tuple[bool, str]]:
    result = {item_id: (True, "Available for scav-case selection") for item_id in raw_items}

    for item_id, item in raw_items.items():
        item_types = item.get("types") or []
        properties = item.get("properties") or {}

        if _is_generated_preset_id(item_id):
            result[item_id] = (False, "Generated preset ID; not safe to store")
            continue

        if "preset" in item_types and properties.get("default") is not True:
            result[item_id] = (False, "Custom preset; cannot be received from a scav case")

        if "gun" not in item_types:
            continue

        default_id = properties.get("defaultPreset")
        default_item = raw_items.get(default_id) if default_id else None
        default_properties = (default_item or {}).get("properties") or {}
        has_stable_default = bool(
            default_id
            and not _is_generated_preset_id(default_id)
            and "preset" in ((default_item or {}).get("types") or [])
            and default_properties.get("default") is True
        )
        if has_stable_default:
            result[item_id] = (False, "Base weapon; its assembled default version is used instead")
            result[default_id] = (True, "Assembled default weapon")

    return result


def classify_scav_case_eligibility(raw_items: dict[str, dict]) -> dict[str, bool]:
    """Return the public item-ID eligibility map used by regression tests."""
    return {
        item_id: eligible
        for item_id, (eligible, _reason) in _eligibility(raw_items).items()
    }


class TarkovItemImportService:
    def __init__(self, http=requests):
        self.http = http

    @property
    def source_url(self) -> str:
        base = os.getenv("TARKOV_JSON_API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")
        mode = os.getenv("TARKOV_GAME_MODE", DEFAULT_GAME_MODE).strip("/")
        return f"{base}/{mode}/items"

    def fetch_catalog(self) -> list[dict]:
        try:
            response = self.http.get(self.source_url, timeout=(3, 30))
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as error:
            raise ItemCatalogError(f"Could not fetch the Tarkov item catalogue: {error}") from error

        data = payload.get("data") or {}
        raw_items = data.get("items")
        categories = data.get("itemCategories")
        if not isinstance(raw_items, dict) or not isinstance(categories, dict):
            raise ItemCatalogError("The Tarkov item API returned an unexpected response format.")

        category_names = {
            category_id: _prettify_slug(category["normalizedName"])
            for category_id, category in categories.items()
            if isinstance(category, dict) and category.get("normalizedName")
        }
        eligibility = _eligibility(raw_items)
        rows = []
        for item_id, item in raw_items.items():
            normalized_name = item.get("normalizedName")
            name = _prettify_slug(normalized_name) if normalized_name else item.get("name")
            if not name:
                name = item_id

            category = "Unknown"
            source_categories = []
            for category_id in item.get("categories") or []:
                source_name = category_names.get(category_id)
                if not source_name:
                    continue
                source_categories.append(source_name)
                mapped = _mapped_category(source_name)
                if mapped and category == "Unknown":
                    category = mapped

            eligible, reason = eligibility[item_id]
            rows.append({
                "id": item_id,
                "name": name,
                "category": category,
                "source_categories": source_categories,
                "types": item.get("types") or [],
                "image_link": item.get("image512pxLink"),
                "base_price": item.get("basePrice"),
                "scav_case_eligible": eligible,
                "eligibility_reason": reason,
            })
        return rows

    def find_new_items(self) -> list[dict]:
        existing_ids = {row[0] for row in db.session.query(TarkovItem.tarkov_id).all()}
        rows = [row for row in self.fetch_catalog() if row["id"] not in existing_ids]
        return sorted(rows, key=lambda row: (not row["scav_case_eligible"], row["name"].casefold()))

    def import_selected(self, selected_ids: set[str]) -> ImportResult:
        """Refetch and validate selected IDs; never trust preview form fields."""
        if not selected_ids:
            return ImportResult((), ())

        current_rows = {row["id"]: row for row in self.fetch_catalog()}
        existing_ids = {
            row[0]
            for row in db.session.query(TarkovItem.tarkov_id)
            .filter(TarkovItem.tarkov_id.in_(selected_ids)).all()
        }
        imported = []
        skipped = []

        try:
            for item_id in sorted(selected_ids):
                row = current_rows.get(item_id)
                if not row or item_id in existing_ids or not row["scav_case_eligible"]:
                    skipped.append(item_id)
                    continue

                if row["image_link"]:
                    self._upload_image(row["image_link"], item_id)

                db.session.add(TarkovItem(
                    tarkov_id=item_id,
                    name=row["name"],
                    category=row["category"],
                    scav_case_eligible=True,
                ))
                imported.append(row["name"])
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return ImportResult(tuple(imported), tuple(skipped))

    @staticmethod
    def _upload_image(image_url: str, item_id: str) -> None:
        required = {
            "cloud_name": os.getenv("CLOUDINARY_CLOUD_NAME"),
            "api_key": os.getenv("CLOUDINARY_API_KEY"),
            "api_secret": os.getenv("CLOUDINARY_SECRET"),
        }
        if not all(required.values()):
            raise ItemCatalogError("Cloudinary credentials are not configured; no items were imported.")

        cloudinary.config(**required, secure=True)
        cloudinary.uploader.upload(
            image_url,
            public_id=item_id,
            unique_filename=False,
            overwrite=True,
        )
