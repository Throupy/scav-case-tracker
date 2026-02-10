import json
from typing import List, Dict, Any, Optional

import requests
from flask import url_for, current_app

from app.models import ScavCase, ScavCaseItem, TarkovItem, User
from app.services import BaseService
from app.cases.utils import (
    get_price,
    calculate_most_popular_categories,
    find_most_common_items,
    calculate_avg_items_per_case_type,
    calculate_avg_return_by_case_type,
    calculate_most_profitable,
    calculate_item_category_distribution,
    check_achievements,
    save_uploaded_image,
    process_scav_case_image,
    create_scav_case_entry
)

class ScavCaseService(BaseService):
    """Service class for handling biz logic for ScavCase functionality"""
    def get_paginated_cases(
        self, page: int, per_page: int = 10,
        sort_by: str = "type", sort_order: str = "asc"
    ):
        """Get a paginated list of scav cases, with sorting"""
        # get the attribute 'sort_by' from ScavCase obj, fallback to ScavCase.id
        sort_attr = getattr(ScavCase, sort_by, ScavCase.id)

        if sort_order == "asc":
            query = ScavCase.query.order_by(self.db.asc(sort_attr))
        else:
            query = ScavCase.query.order_by(self.db.desc(sort_attr))

        return query.paginate(page=page, per_page=per_page)

    def get_case_by_id(self, case_id: int) -> Optional[ScavCase]:
        """Get scav case by ID or return None"""
        return ScavCase.query.get(case_id)

    def get_case_by_id_or_404(self, case_id: int) -> ScavCase:
        """Get scav case by ID, or raise a 404 error"""
        return ScavCase.query.get_or_404(case_id)

    def get_cases_by_type(self, case_type: str) -> List[ScavCase]:
        """Get all cases of specific type e.g. moonshine"""
        if case_type == "all":
            return ScavCase.query.all()
        return ScavCase.query.filter_by(type=case_type).all()

    def calculate_insights_data(self, case_type: str = "all") -> Dict[str, Any]:
        """Calculate values and form structure for insights page, for a given case type"""
        # TODO: Can this be refined, done better, shipped to API... 
        scav_cases = self.get_cases_by_type(case_type)
        # Common calculations
        most_popular_items = find_most_common_items(scav_cases)
        most_popular_categories = calculate_most_popular_categories(scav_cases)
        category_distribution = calculate_item_category_distribution(scav_cases)
        
        if case_type == "all":
            return {
                "most_popular_items": most_popular_items,
                "most_popular_categories": most_popular_categories,
                "category_distribution": category_distribution,
                "most_profitable_case": calculate_most_profitable(scav_cases),
                "avg_return_chart": calculate_avg_return_by_case_type(scav_cases),
                "avg_items_chart": calculate_avg_items_per_case_type(scav_cases),
                # Time-based charts not applicable for "all"
                "profit_over_time_chart": None,
                "items_over_time_chart": None,
                "return_over_time_chart": None,
            }
        else:
            return {
                "most_popular_items": most_popular_items,
                "most_popular_categories": most_popular_categories,
                "category_distribution": category_distribution,
                "profit_over_time_chart": self._build_profit_chart(scav_cases),
                "items_over_time_chart": self._build_items_chart(scav_cases),
                "return_over_time_chart": self._build_return_chart(scav_cases),
                # Aggregated charts not applicable for specific types
                "avg_items_chart": None,
                "most_profitable_case": None,
                "avg_return_chart": None,
            }
    
    def create_scav_case(self, scav_case_type: str, uploaded_image, items_data: str, user: User) -> Dict[str, Any]:
        """Create a new scav case entry - centralised function for web and integrations (e.g. discord bot)"""
        try:
            # uploaded_image is for integrations such as discord bot
            if uploaded_image:
                # save image, and process via OCR to get items
                file_path = save_uploaded_image(uploaded_image)
                items = process_scav_case_image(file_path)
            elif items_data:
                # process the items_data JSON passed in (i.e. via webapp)
                items = json.loads(items_data)
            else:
                raise ValueError("Either image or items_data must be provided")
            
            # TODO: Perhaps the functionality from the below method should be moved into here (service)
            scav_case = create_scav_case_entry(scav_case_type, items, user.id)

            check_achievements(user)

            current_app.logger.info(f"Scav case createds successfully for user: '{user.username}'")

            return {
                "success": True,
                "message": "Scav Case and Items successfully added",
                "scav_case_id": scav_case.id
            }
            
        except json.JSONDecodeError:
            return {"success": False, "message": "Invalid items data format"}
        except ValueError as e:
            return {"success": False, "message": str(e)}
        except Exception as e:
            current_app.logger.error(f"Error creating scav case: {e}")
            return {"success": False, "message": "An unexpected error occurred"}

                

    def create_scav_case_via_api(
        self, scav_case_type: str, uploaded_image, 
        items_data: str, user: User
    ) -> Dict[str, Any]:

        files = {"image": uploaded_image}
        data = {
            "scav_case_type": scav_case_type,
            "user_id": user.id,
            "items_data": items_data
        }

        try:
            response = requests.post(
                url_for("api.submit_scav_case_api", _external=True),
                data = data,
                files = files,
                timeout = 30
            )

            if response.status_code == 200:
                check_achievements(user)
                return {
                    "success": True,
                    "message": "Scav Case and Items successfully added"
                }
            else:
                error_msg = response.json().get("error", "Unknown error occurred")
                return {
                    "success": False,
                    "message": f"There was an error: {error_msg}"
                }
        
        except requests.RequestException as e:
            current_app.logger.error(f"API request failed: {e}")
            return {
                "success": False,
                "message": "Failed to communicate with API"
            }

    def update_scav_case_items(self, scav_case: ScavCase, items_data: List[Dict]) -> None:
        """Update items for an existing scav case"""
        existing_items = {item.id: item for item in scav_case.items}
        received_item_ids = {item["id"] for item in items_data if "id" in item}

        # First work out if any items were deleted
        # Check if any items are in the existing ScavCase DB row, that aren't passed to this function
        items_to_delete = [
            item for item_id, item in existing_items.items()
            if item_id not in received_item_ids
        ]
        for item in items_to_delete:
            # deleting ScavCaseItem will delete the reference in ScavCase
            self.db.session.delete(item)

        total_price = 0
        
        # Update or create items where required
        for item_data in items_data:
            if "id" in item_data and item_data["id"] in existing_items:
                # update existing item
                existing_item = existing_items[item_data["id"]]
                existing_item.amount = item_data["quantity"]
                item_price = existing_item.price
            else:
                # create a new item
                new_item = ScavCaseItem(
                    scav_case_id=scav_case.id,
                    tarkov_id=item_data["id"],
                    price=get_price(item_data["id"]),
                    name=item_data["name"],
                    amount=item_data["quantity"],
                )
                self.db.session.add(new_item)
                item_price = new_item.price
            
            total_price += item_price * item_data["quantity"]

        # update scav case totals
        scav_case._return = total_price
        scav_case.number_of_items = len(items_data)

        self.commit()

    def delete_scav_case(self, scav_case: ScavCase) -> bool:
        """Delete a scav case"""
        return self.delete(scav_case)

    def _build_profit_chart(self, scav_cases: List[ScavCase]) -> Dict[str, Any]:
        """Build profit over time chart data"""
        return {
            "labels": [str(case.id) for case in scav_cases],
            "profits": [(case._return - case.cost) for case in scav_cases],
            "costs": [case.cost for case in scav_cases],
        }

    def _build_items_chart(self, scav_cases: List[ScavCase]) -> Dict[str, Any]:
        """Build items count chart data"""
        return {
            "labels": [str(case.id) for case in scav_cases],
            "items_count": [case.number_of_items for case in scav_cases],
        }

    def _build_return_chart(self, scav_cases: List[ScavCase]) -> Dict[str, Any]:
        """Build return over time chart data"""
        return {
            "labels": [str(case.id) for case in scav_cases],
            "returns": [case._return for case in scav_cases],
            "costs": [case.cost for case in scav_cases],
        }