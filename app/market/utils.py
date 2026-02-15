import json
from typing import Optional, Iterable

import requests
from flask import current_app

def generate_item_price_query(tarkov_item_id: int) -> str:
    """Generate a GraphQL query to retrieve item price information"""
    return (
        """{
            items(ids: "%s")
                { name low24hPrice high24hPrice avg24hPrice sellFor { price currency priceRUB vendor { name } } }
            }"""
        % tarkov_item_id
    )

def generate_prices_query(item_ids: list[str]) -> str:
    ids_literal = json.dumps(item_ids)
    return f"""
    {{
      items(ids: {ids_literal}) {{
        id
        sellFor {{
          price
          source
        }}
      }}
    }}
    """

def run_query(query):
    try:
        response = requests.post(
            "https://api.tarkov.dev/graphql", 
            headers={"Content-Type": "application/json"}, 
            json={"query": query},
            timeout=(3, 10), # connect, read
        )
        response.raise_for_status()
        return response.json()
    except requests.Timeout as e:
        current_app.logger.error("Tarkov API Timed out")
        raise e
    except requests.RequestException as e:
        current_app.logger.error(f"Tarkov API request failed: {e}")
        raise e

def _mask_tarkov_item_id(item_id: str) -> str:
    """Mask tarkov item ID, e.g. <LONG_ID> -> 4823f...j3f39"""
    return f"{item_id[:5]}...{item_id[-5:]}"

def get_prices(tarkov_item_ids: Iterable[str]) -> dict[str, Optional[int]]:
    """
    Bulk lookup of tarkov item prices, by ID
    - prefer flea market price if available
    - otherwise use the highest available trader price
    - if no sell price exists (unlikely), return None

    Return:
        dict { tarkov_id: price_or_None }
    """
    # receive, clean and normalise eft item IDs
    item_ids = [item_id.strip() for item_id in tarkov_item_ids if item_id and item_id.strip()]

    if not item_ids:
        return {}

    
    # e.g. <LONG_ID> -> ds45f...vjdk3 (used for logging only)
    masked_ids = [_mask_tarkov_item_id(item_id) for item_id in item_ids]

    current_app.logger.info(
        "Getting item price for %d item(s) with ID(s) %s",
        len(item_ids),
        masked_ids
    )

    # generate and execute the bulk query
    query = generate_prices_query(item_ids)
    response = run_query(query)

    # navigate response structure
    response_items = (response or {}).get("data", {}).get("items") or []

    # init output dict with None (default if no price found)
    prices_by_id: dict[str, Optional[int]] = {item_id: None for item_id in item_ids}

    for item_data in response_items:
        tarkov_id = item_data.get("id")
        sell_options = item_data.get("sellFor") or []

        # malformed for whatever reason, just skip it
        if not tarkov_id or tarkov_id not in prices_by_id or not sell_options:
            continue

        # try flea market first
        flea_entry = next(
            (entry for entry in sell_options if entry.get("source") == "fleaMarket"),
            None,
        )

        if flea_entry and flea_entry.get("price") is not None:
            prices_by_id[tarkov_id] = int(flea_entry["price"])
            continue

        # Ooherwise use highest available vendor price
        best_entry = max(
            (entry for entry in sell_options if entry.get("price") is not None),
            key=lambda entry: entry["price"],
            default=None,
        )

        prices_by_id[tarkov_id] = int(best_entry["price"]) if best_entry else None

    return prices_by_id

def get_price(tarkov_item_id: str) -> int:
    # TODO: Hell of a chunk of work, but this (and get_prices) should / could be moved to celery tasks?
    prices = get_prices([tarkov_item_id])
    return prices.get(tarkov_item_id)

def get_market_information(tarkov_item_id: int):
    query = generate_item_price_query(tarkov_item_id)

    response = requests.post(
        "https://api.tarkov.dev/graphql",
        headers={"Content-Type": "application/json"},
        json={"query": query},
    )

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(
            "Query failed to run by returning code of {}. {}".format(
                response.status_code, query
            )
        )
