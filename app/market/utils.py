import time
from typing import Optional, Iterable

import requests
from flask import current_app

# Defaults for the JSON API that replaced the deprecated GraphQL endpoint
# (api.tarkov.dev). Both are overridable via app config:
#   TARKOV_JSON_API_BASE_URL - e.g. "https://json.tarkov.dev"
#   TARKOV_GAME_MODE         - one of "regular", "pve", "pvp-season"
#   TARKOV_ITEMS_CACHE_TTL_SECONDS - how long to reuse the bulk /items fetch
#   TARKOV_TRADERS_CACHE_TTL_SECONDS - how long to reuse the /traders fetch
DEFAULT_TARKOV_JSON_API_BASE_URL = "https://json.tarkov.dev"
DEFAULT_TARKOV_GAME_MODE = "regular"
DEFAULT_TARKOV_ITEMS_CACHE_TTL_SECONDS = 300  # 5 min - the /items payload is huge
DEFAULT_TARKOV_TRADERS_CACHE_TTL_SECONDS = 3600  # trader roster barely ever changes

FLEA_MARKET_VENDOR_LABEL = "Flea Market"

# Only the fields we actually use out of the /items payload. Everything else
# (weapon slots, ballistics, armor zones, containsItems, ...) gets discarded
# right after fetching so we're not holding a multi-MB dict in memory per
# game mode for the lifetime of the cache.
_ITEM_FIELDS_TO_KEEP = (
    "lastLowPrice",
    "avg24hPrice",
    "low24hPrice",
    "high24hPrice",
    "sellToTrader",
)

# Process-local caches, keyed by (base_url, game_mode) so different configs
# (e.g. pve vs regular) don't clobber each other. Each entry is
# (fetched_at_monotonic, data).
_items_cache: dict[tuple[str, str], tuple[float, dict[str, dict]]] = {}
_traders_cache: dict[tuple[str, str], tuple[float, dict[str, str]]] = {}


def _get_base_url() -> str:
    try:
        return current_app.config.get(
            "TARKOV_JSON_API_BASE_URL", DEFAULT_TARKOV_JSON_API_BASE_URL
        )
    except RuntimeError:
        # no app context - fall back to default rather than blow up
        return DEFAULT_TARKOV_JSON_API_BASE_URL


def _get_game_mode() -> str:
    try:
        return current_app.config.get("TARKOV_GAME_MODE", DEFAULT_TARKOV_GAME_MODE)
    except RuntimeError:
        return DEFAULT_TARKOV_GAME_MODE


def _build_url(path_template: str, **path_vars) -> str:
    """
    Build a full URL from one of the {{gameMode}}/{{itemId}}-style path
    templates the JSON API documents, e.g. "/{{gameMode}}/items".
    """
    path = path_template.replace("{{gameMode}}", _get_game_mode())
    for key, value in path_vars.items():
        path = path.replace("{{%s}}" % key, str(value))
    return f"{_get_base_url()}{path}"


def _mask_tarkov_item_id(item_id: str) -> str:
    """Mask tarkov item ID, e.g. <LONG_ID> -> 4823f...j3f39"""
    return f"{item_id[:5]}...{item_id[-5:]}"


def _get_json(session: requests.Session, url: str) -> Optional[dict]:
    try:
        response = session.get(url, timeout=(3, 30))  # connect, read
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        current_app.logger.error("Tarkov JSON API timed out requesting %s", url)
        return None
    except requests.RequestException as e:
        current_app.logger.error("Tarkov JSON API request failed for %s: %s", url, e)
        return None
    except ValueError as e:
        current_app.logger.error("Tarkov JSON API returned malformed JSON for %s: %s", url, e)
        return None


def _get_items_cache_ttl() -> int:
    try:
        return current_app.config.get(
            "TARKOV_ITEMS_CACHE_TTL_SECONDS", DEFAULT_TARKOV_ITEMS_CACHE_TTL_SECONDS
        )
    except RuntimeError:
        return DEFAULT_TARKOV_ITEMS_CACHE_TTL_SECONDS


def _get_traders_cache_ttl() -> int:
    try:
        return current_app.config.get(
            "TARKOV_TRADERS_CACHE_TTL_SECONDS", DEFAULT_TARKOV_TRADERS_CACHE_TTL_SECONDS
        )
    except RuntimeError:
        return DEFAULT_TARKOV_TRADERS_CACHE_TTL_SECONDS


def _trim_item(item: dict) -> dict:
    """Keep only the fields get_prices() actually needs from an item dict."""
    return {field: item.get(field) for field in _ITEM_FIELDS_TO_KEEP}


def _fetch_items_by_id(session: requests.Session) -> dict[str, dict]:
    """
    Fetch the (trimmed) bulk items catalog (id -> item dict) for the
    configured game mode, using a short-lived process-local cache.

    The upstream /items response is huge (full weapon/armor/slot data for
    every item in the game), so we: (1) cache it briefly instead of
    re-fetching on every get_prices() call, and (2) immediately discard
    everything except the handful of price-relevant fields we care about,
    so the cached copy stays small.
    """
    cache_key = (_get_base_url(), _get_game_mode())
    ttl = _get_items_cache_ttl()

    cached = _items_cache.get(cache_key)
    if cached and (time.monotonic() - cached[0]) < ttl:
        return cached[1]

    url = _build_url("/{{gameMode}}/items")
    payload = _get_json(session, url)
    raw_items = ((payload or {}).get("data") or {}).get("items") or {}

    trimmed_items = {item_id: _trim_item(item) for item_id, item in raw_items.items()}

    if trimmed_items:
        _items_cache[cache_key] = (time.monotonic(), trimmed_items)

    return trimmed_items


def _fetch_trader_names(session: requests.Session) -> dict[str, str]:
    """
    Fetch trader id -> display name, for resolving the opaque trader IDs
    found in an item's sellToTrader entries. Falls back to an empty map
    (raw trader IDs will be used instead of names) if this fails or the
    response shape isn't what we expect - vendor naming is a nice-to-have,
    not worth failing the whole price lookup over.
    """
    cache_key = (_get_base_url(), _get_game_mode())
    ttl = _get_traders_cache_ttl()

    cached = _traders_cache.get(cache_key)
    if cached and (time.monotonic() - cached[0]) < ttl:
        return cached[1]

    url = _build_url("/{{gameMode}}/traders")
    payload = _get_json(session, url)
    traders = (payload or {}).get("data") or {}

    if not isinstance(traders, dict):
        current_app.logger.warning(
            "Unexpected traders response shape from Tarkov JSON API; "
            "vendor names will fall back to raw trader IDs."
        )
        return {}

    names: dict[str, str] = {}
    for trader_id, trader in traders.items():
        if not isinstance(trader, dict):
            continue
        # NOTE: trader["name"] is placeholder text (e.g. "<id> Nickname"),
        # not a real display name - normalizedName (e.g. "prapor") is the
        # actual usable field, so prettify that instead.
        normalized = trader.get("normalizedName")
        if normalized:
            names[trader_id] = normalized.replace("-", " ").replace("_", " ").title()

    if names:
        _traders_cache[cache_key] = (time.monotonic(), names)

    return names


def _best_trader_offer(sell_to_trader: list[dict]) -> Optional[dict]:
    """Pick the highest-priced sellToTrader entry, comparing in RUB."""
    priced_entries = [e for e in sell_to_trader if e.get("priceRUB") is not None]
    if not priced_entries:
        return None
    return max(priced_entries, key=lambda e: e["priceRUB"])


def _summarise_item(item: dict, trader_names: dict[str, str], include_vendor: bool) -> dict:
    """
    Reduce a single item dict from the bulk /items response down to the
    "current price + vendor" shape our callers expect, preferring flea
    market price and falling back to the best trader sell price.
    """
    flea_price = item.get("lastLowPrice")

    if flea_price is not None:
        return {
            "price": int(flea_price),
            "vendor": FLEA_MARKET_VENDOR_LABEL if include_vendor else None,
        }

    sell_to_trader = item.get("sellToTrader") or []
    best_offer = _best_trader_offer(sell_to_trader)

    if not best_offer:
        return {"price": None, "vendor": None}

    vendor_name = None
    if include_vendor:
        trader_id = best_offer.get("trader")
        vendor_name = trader_names.get(trader_id, trader_id)

    return {"price": int(best_offer["priceRUB"]), "vendor": vendor_name}


def get_prices(
    tarkov_item_ids: Iterable[str],
    include_historical: bool = False,
    include_vendor: bool = False,
) -> dict[str, Optional[int]]:
    """
    Bulk lookup of tarkov item prices, by ID, via the JSON API's bulk
    items endpoint (https://json.tarkov.dev/<gameMode>/items).
    - prefer flea market price if available (item.lastLowPrice)
    - otherwise use the highest available trader sell price (sellToTrader)
    - if no sell price exists (unlikely), return None

    Return:
        include_historical=False: dict { tarkov_id: price_or_None }
        include_historical=True:  dict { tarkov_id: {"price", "vendor", "avg", "low", "high"} }
    """
    item_ids = [item_id.strip() for item_id in tarkov_item_ids if item_id and item_id.strip()]

    if not item_ids:
        return {}

    masked_ids = [_mask_tarkov_item_id(item_id) for item_id in item_ids]

    current_app.logger.info(
        "Getting item price for %d item(s) with ID(s) %s",
        len(item_ids),
        masked_ids,
    )

    if not include_historical:
        prices_by_id: dict[str, Optional[int]] = {item_id: None for item_id in item_ids}
    else:
        prices_by_id: dict[str, dict] = {
            item_id: {"price": None, "vendor": None, "avg": None, "low": None, "high": None}
            for item_id in item_ids
        }

    with requests.Session() as session:
        items_by_id = _fetch_items_by_id(session)
        trader_names = _fetch_trader_names(session) if include_vendor else {}

        for item_id in item_ids:
            item = items_by_id.get(item_id)
            if not item:
                continue

            summary = _summarise_item(item, trader_names, include_vendor)

            if not include_historical:
                prices_by_id[item_id] = summary["price"]
                continue

            avg = item.get("avg24hPrice")
            low = item.get("low24hPrice")
            high = item.get("high24hPrice")

            # fallback logic - if the API didn't give us 24h stats but we do
            # have a current price, use that as a reasonable stand-in
            if summary["price"] is not None:
                if avg is None:
                    avg = summary["price"]
                if low is None:
                    low = summary["price"]
                if high is None:
                    high = summary["price"]

            prices_by_id[item_id] = {
                "price": summary["price"],
                "vendor": summary["vendor"],
                "avg": avg,
                "low": low,
                "high": high,
            }

    return prices_by_id


def get_price(tarkov_item_id: str) -> Optional[int]:
    # TODO: Hell of a chunk of work, but this (and get_prices) should / could be moved to celery tasks?
    prices = get_prices([tarkov_item_id])
    return prices.get(tarkov_item_id)


def get_market_information(tarkov_item_id: str) -> dict:
    """
    Fetch the raw flea market price-point history for a single item from
    https://json.tarkov.dev/<gameMode>/prices/<itemId> - useful for charting
    price over time, as opposed to get_price/get_prices which just want a
    current snapshot.
    """
    url = _build_url("/{{gameMode}}/prices/{{itemId}}", itemId=tarkov_item_id)

    with requests.Session() as session:
        payload = _get_json(session, url)

    data_points = (payload or {}).get("data") or []

    if not data_points:
        raise Exception(
            f"Query failed or returned no data for item {_mask_tarkov_item_id(tarkov_item_id)}"
        )

    return {"data": data_points}