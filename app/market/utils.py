import json

import requests


def generate_item_price_query(tarkov_item_id: int) -> str:
    """Generate a GraphQL query to retrieve item price information"""
    return (
        """{
            items(ids: "%s")
                { name low24hPrice high24hPrice avg24hPrice sellFor { price currency priceRUB vendor { name } } }
            }"""
        % tarkov_item_id
    )


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
