import json
from typing import List, Dict, Any, Optional

import requests
from flask import url_for, current_app, jsonify
from sqlalchemy.sql import func, case
from sqlalchemy.orm import joinedload, selectinload

from app.constants import DISCORD_BOT_USER_USERNAME
from app.models import ScavCase, ScavCaseItem, TarkovItem, User
from app.services import BaseService
from app.services.user_service import UserService
from app.cases.utils import (
    calculate_most_popular_categories,
    find_most_common_items,
    calculate_avg_items_per_case_type,
    calculate_avg_return_by_case_type,
    calculate_most_profitable,
    calculate_item_category_distribution,
    check_achievements,
    save_uploaded_image,
    process_scav_case_image,
)
from app.market.utils import (
    get_price,
    get_prices,
)

user_service = UserService()

class ScavCaseService(BaseService):
    """Service class for handling biz logic for ScavCase functionality"""
    def get_all_cases(self) -> list[ScavCase] | None:
        return ScavCase.query.all()
        
    def get_all_cases_paginated(
        self, page: int, per_page: int = 10,
        sort_by: str = "created_at", sort_order: str = "asc",
        case_type: Optional[str] = None,
    ):
        """Return all ScavCases (paginated) with safe sorting, including profit sorting."""
        query = (
            self.db.session.query(ScavCase)
            .options(joinedload(ScavCase.author))  # template uses scav_case.author.*
        )

        if case_type and case_type != "all":
            query = query.filter(ScavCase.type == case_type)

        if sort_by == "profit":
            sort_expr = ScavCase._return - ScavCase.cost
        else:
            allowed_sort_columns = {
                "id": ScavCase.id,
                "created_at": ScavCase.created_at,
                "type": ScavCase.type,
                "cost": ScavCase.cost,
                "_return": ScavCase._return,
                "number_of_items": ScavCase.number_of_items,
            }
            sort_expr = allowed_sort_columns.get(sort_by, ScavCase.type)

        if sort_order == "asc":
            query = query.order_by(self.db.asc(sort_expr), self.db.asc(ScavCase.id))
        else:
            query = query.order_by(self.db.desc(sort_expr), self.db.desc(ScavCase.id))

        return query.paginate(page=page, per_page=per_page, error_out=False)

    def get_all_cases_by_user(self, user: User) -> list[ScavCase] | None:
        return ScavCase.query.filter_by(user_id=user.id).all()

    def get_all_cases_by_user_paginated(
        self, user: User, page: int, per_page: int = 10,
        sort_by: str = "created_at", sort_order: str = "asc",
        case_type: Optional[str] = None,
    ):
        """Return a user's ScavCases (paginated) with optional filtering and sorting."""
        query = (
            self.db.session.query(ScavCase)
            .options(joinedload(ScavCase.author))
            .filter(ScavCase.user_id == user.id)
        )

        if case_type and case_type != "all":
            query = query.filter(ScavCase.type == case_type)

        if sort_by == "profit":
            sort_expr = ScavCase._return - ScavCase.cost
        else:
            allowed_sort_columns = {
                "id": ScavCase.id,
                "created_at": ScavCase.created_at,
                "type": ScavCase.type,
                "cost": ScavCase.cost,
                "_return": ScavCase._return,
                "number_of_items": ScavCase.number_of_items,
            }
            sort_expr = allowed_sort_columns.get(sort_by, ScavCase.created_at)

        if sort_order == "asc":
            query = query.order_by(self.db.asc(sort_expr), self.db.asc(ScavCase.id))
        else:
            query = query.order_by(self.db.desc(sort_expr), self.db.desc(ScavCase.id))

        return query.paginate(page=page, per_page=per_page, error_out=False)

    def get_case_by_id(self, case_id: int) -> Optional[ScavCase]:
        """Get scav case by ID or return None"""
        return ScavCase.query.get(case_id)

    def get_case_by_id_or_404(self, case_id: int) -> ScavCase:
        """Get scav case by ID, or raise a 404 error"""
        return ScavCase.query.get_or_404(case_id)

    def get_cases_by_type(self, case_type: str) -> List[ScavCase]:
        """Get all cases of specific type e.g. moonshine"""
        q = self.db.session.query(ScavCase).options(selectinload(ScavCase.items))
        if case_type == "all":
            return q.all()
        return q.filter(ScavCase.type == case_type).all()

    def calculate_insights_data(self, case_type: str = "all") -> Dict[str, Any]:
        """Calculate values and form structure for insights page, for a given case type"""

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
            
            scav_case = self._create_scav_case_entry(scav_case_type, items, user.id)

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

    def handle_discord_bot_submission(self, request):
        """
        Handle Discord bot scav case submission
        Returns: (response_dict, status_code)
        """
        try:
            # Get the Discord bot user
            discord_bot_user = User.query.filter_by(username='Discord Bot').first()
            if not discord_bot_user:
                current_app.logger.error("Discord bot user not found in database")
                return jsonify({"error": "Discord bot user not found"}), 500
            
            current_app.logger.info(f"Found Discord bot user: {discord_bot_user.username}")
            
            # Extract form data
            scav_case_type = request.form.get("scav_case_type")
            uploaded_image = request.files.get("image")
            items_data = request.form.get("items_data", "")
            
            current_app.logger.info(f"Form data - Type: {scav_case_type}, Has Image: {bool(uploaded_image)}")
            
            if not scav_case_type:
                return jsonify({"error": "scav_case_type is required"}), 400
            
            # Create the scav case
            result = self.create_scav_case(
                scav_case_type=scav_case_type,
                uploaded_image=uploaded_image,
                items_data=items_data,
                user=discord_bot_user
            )
            
            current_app.logger.info(f"Service result: {result}")
            
            if result["success"]:
                return jsonify({"message": result["message"]}), 200
            else:
                return jsonify({"error": result["message"]}), 400
                
        except Exception as e:
            current_app.logger.error(f"Discord bot submission error: {e}")
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500

    # TODO: Maybe split this into a DashboardService
    def generate_dashboard_data(self, since_date=None, case_type: str = None):
        """Compute all dashboard metrics dynamically."""
        return {
            **self._get_totals(since_date=since_date, case_type=case_type), # total spent, total return, number of cases, and profit
            "most_popular_category": self._get_most_popular_category_name(since_date=since_date, case_type=case_type),
            "top_contributor": self._get_top_contributor(since_date=since_date, case_type=case_type),
            "most_profitable_case_type": self._get_most_profitable_case_type_name(since_date=since_date, case_type=case_type),
            "most_valuable_item": self._get_most_valuable_item(since_date=since_date, case_type=case_type),
        }

    def save_user_global_dashboard_layout(self, user_id, layout):
        if not isinstance(layout, list):
            return jsonify({"error": "layout must be a list"}), 400

        user = user_service.get_user_by_id_or_404(user_id)
        user.scav_case_global_dashboard_layout = layout
        self.db.session.commit()
        return jsonify({"ok": True})

    def generate_users_cases_showcase_data(self, user_id: int) -> dict:
        """Generate data for the /users/XXXX/cases page"""
        return {
            **self._get_totals(user_id=user_id),
            "good_cases": self._get_best_cases(user_id=user_id),
            "avg_profit": self._get_avg_profit_per_case(user_id=user_id),
            "most_profitable_case": self._get_most_profitable_case(user_id=user_id),
            "profitable_cases_pcnt": self._get_profitable_cases_percentage(user_id=user_id)
        }

    def _get_profitable_cases_percentage(self, user_id: int = None) -> float:
        """
        Return the percentage of profitable cases (return > cost).
        Optionally restrict to a specific user.
        Rounded to 1d.p
        """

        q = self.db.session.query(
            func.count(ScavCase.id).label("total_cases"),
            func.sum(
                case(
                    (ScavCase._return > ScavCase.cost, 1),
                    else_=0
                )
            ).label("profitable_cases")
        )

        if user_id is not None:
            q = q.filter(ScavCase.user_id == user_id)

        total_cases, profitable_cases = q.one()

        if not total_cases:
            return 0.0

        percentage = (profitable_cases / total_cases) * 100

        return round(percentage, 1)

    def _get_most_profitable_case(self, user_id: int = None) -> float:
        """
        Return the `_return` value of the most profitable case.
        Optionally restrict to a specific user.
        """
        q = self.db.session.query(ScavCase)

        if user_id is not None:
            q = q.filter(ScavCase.user_id == user_id)

        case_obj = (
            q.order_by(
                (ScavCase._return - ScavCase.cost).desc(),
                ScavCase.created_at.desc()
            )
            .first()
        )

        if not case_obj:
            return 0.0

        return case_obj

    def _get_avg_profit_per_case(self, case_type: str = None, user_id: int = None) -> float:
        """
        Return the average profit per case.
        Optionally filter by case_type and/or user_id.
        """
        q = self.db.session.query(
            func.coalesce(
                func.avg(ScavCase._return - ScavCase.cost),
                0.0
            )
        )

        if case_type is not None:
            q = q.filter(ScavCase.type == case_type)

        if user_id is not None:
            q = q.filter(ScavCase.user_id == user_id)

        avg_profit = q.scalar()

        return float(avg_profit)

    def _get_best_cases(self, n: int = 6, user_id: int = None) -> list[ScavCase]:
        """
        Return the top N most profitable scav cases (desc).
        If user_id is provided, restrict to that user's cases.
        """
        q = self.db.session.query(ScavCase)

        if user_id is not None:
            q = q.filter(ScavCase.user_id == user_id)

        return (
            q.order_by(
                (ScavCase._return - ScavCase.cost).desc(),
                ScavCase.created_at.desc(),  # deterministic tie-breaker
            )
            .limit(n)
            .all()
        )

    def _get_totals(self, user_id: int = None, since_date=None, case_type: str = None) -> dict:
        q = self.db.session.query(
            func.count(ScavCase.id),
            func.coalesce(func.sum(ScavCase.cost), 0),
            func.coalesce(func.sum(ScavCase._return), 0),
            func.coalesce(func.sum(ScavCase._return - ScavCase.cost), 0),
        )

        if user_id is not None:
            q = q.filter(ScavCase.user_id == user_id)
        if since_date is not None:
            q = q.filter(ScavCase.created_at >= since_date)
        if case_type and case_type.lower() != 'all':
            q = q.filter(ScavCase.type == case_type)

        total_cases, total_cost, total_return, total_profit = q.one()

        return {
            "total_cases": int(total_cases),
            "total_cost": float(total_cost),
            "total_return": float(total_return),
            "total_profit": float(total_profit),
        }

    def _get_most_popular_category_name(self, user_id: int = None, since_date=None, case_type: str = None) -> str | None:
        """Most popular item category by count of items (not quantity), optionally per-user."""
        q = (
            self.db.session.query(TarkovItem.category)
            .join(ScavCaseItem, ScavCaseItem.tarkov_id == TarkovItem.tarkov_id)
            .filter(TarkovItem.category.isnot(None))
        )

        needs_case_join = user_id is not None or since_date is not None or (case_type and case_type.lower() != 'all')
        if needs_case_join:
            q = q.join(ScavCase, ScavCaseItem.scav_case_id == ScavCase.id)
            if user_id is not None:
                q = q.filter(ScavCase.user_id == user_id)
            if since_date is not None:
                q = q.filter(ScavCase.created_at >= since_date)
            if case_type and case_type.lower() != 'all':
                q = q.filter(ScavCase.type == case_type)

        return (
            q.group_by(TarkovItem.category)
            .order_by(func.count(ScavCaseItem.id).desc(), TarkovItem.category.asc())
            .limit(1)
            .scalar()
        )

    def _get_most_profitable_case_type_name(self, user_id: int = None, since_date=None, case_type: str = None) -> str | None:
        """Most profitable case type by average profit per run (optionally per-user)."""
        q = self.db.session.query(ScavCase.type)

        if user_id is not None:
            q = q.filter(ScavCase.user_id == user_id)
        if since_date is not None:
            q = q.filter(ScavCase.created_at >= since_date)
        if case_type and case_type.lower() != 'all':
            q = q.filter(ScavCase.type == case_type)

        return (
            q.group_by(ScavCase.type)
            .order_by(
                func.avg(ScavCase._return - ScavCase.cost).desc(),
                ScavCase.type.asc(),
            )
            .limit(1)
            .scalar()
        )


    def _get_most_valuable_item(self, user_id: int = None, since_date=None, case_type: str = None) -> ScavCaseItem | None:
        """Most valuable single item (optionally per-user)."""
        q = (
            self.db.session.query(ScavCaseItem)
            .options(joinedload(ScavCaseItem.scav_case))
        )

        needs_case_join = user_id is not None or since_date is not None or (case_type and case_type.lower() != 'all')
        if needs_case_join:
            q = q.join(ScavCase, ScavCaseItem.scav_case_id == ScavCase.id)
            if user_id is not None:
                q = q.filter(ScavCase.user_id == user_id)
            if since_date is not None:
                q = q.filter(ScavCase.created_at >= since_date)
            if case_type and case_type.lower() != 'all':
                q = q.filter(ScavCase.type == case_type)

        return q.order_by(ScavCaseItem.price.desc(), ScavCaseItem.id.desc()).first()

    def _get_top_contributor(self, since_date=None, case_type: str = None) -> User | None:
        """Find the user who submitted the most scav cases globally."""
        q = self.db.session.query(ScavCase.user_id).group_by(ScavCase.user_id)
        if since_date is not None:
            q = q.filter(ScavCase.created_at >= since_date)
        if case_type and case_type.lower() != 'all':
            q = q.filter(ScavCase.type == case_type)
        top_user_id = (
            q.order_by(func.count(ScavCase.id).desc(), ScavCase.user_id.asc())
            .limit(1)
            .scalar()
        )
        if not top_user_id:
            return None

        return self.db.session.get(User, top_user_id)

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

    def _create_scav_case_entry(
        self, scav_case_type: str, items: list[dict[str, Any]], user_id: int,
    ) -> ScavCase:
        """Create ScavCase + ScavCaseItems."""

        def _parse_case_cost(case_type: str) -> float:
            """resolve cost of the case
            - Moonshine / Intel -> dynamic price lookup
            - static costs -> parsed integers
            """
            ct = (case_type or "").strip()
            ctl = ct.lower()

            if ctl == "moonshine":
                p = get_price("5d1b376e86f774252519444e")
                return float(p or 0.0)
            if ctl == "intelligence":
                p = get_price("5c12613b86f7743bbe2c3f76")
                return float(p or 0.0)

            # parse the static cost
            try:
                return float(int(ct.replace("₽", "").replace(",", "").strip()))
            except Exception as e:
                raise ValueError(f"Invalid scav_case_type cost: {case_type!r}") from e

        # validate and normalise items
        normalized: list[dict[str, Any]] = []
        for i, item in enumerate(items or []):
            # confirm the tarkov id, name, and quantity vars exist
            try:
                tid = str(item["id"]).strip()
                name = str(item.get("name", "")).strip()
                qty = int(item.get("quantity", 0))
            except Exception as e:
                raise ValueError(f"Invalid item payload at index {i}: {item!r}") from e

            if not tid:
                raise ValueError(f"Missing item id at index {i}")
            if qty <= 0:
                raise ValueError(f"Invalid quantity for item {tid}: {qty}")

            normalized.append({"id": tid, "name": name, "quantity": qty})

        # compute case cost after validation
        cost = _parse_case_cost(scav_case_type)

        # prepare IDs for bulk price lookup
        unique_ids = list({x["id"] for x in normalized})
        prices_by_id: dict[str, Optional[int]]
        try:
            # bulk call to graphql endpoint
            prices_by_id = get_prices(unique_ids)
        except Exception:
            current_app.logger.exception("Price lookup failed (bulk). Falling back to None prices.")
            prices_by_id = {tid: None for tid in unique_ids}

        # use real session obj, not scoped proxy
        session = self.db.session()

        try:
            # if we are already in a trransaction, use a savepoint, otherwise new trans.
            tx_ctx = session.begin_nested() if session.in_transaction() else session.begin()

            with tx_ctx:
                scav_case = ScavCase(
                    type=scav_case_type,
                    user_id=user_id,
                    cost=cost,
                    number_of_items=len(normalized),
                    _return=0.0,
                )
                session.add(scav_case)
                # flush so scav_case.id is rdy for FK refs
                session.flush() 

                total_return = 0.0
                case_items: list[ScavCaseItem] = []

                for item in normalized:
                    tid = item["id"]
                    qty = item["quantity"]

                    # 'freeze' price at creation time
                    price_i = prices_by_id.get(tid)
                    price_f = float(price_i) if price_i is not None else 0.0

                    case_items.append(
                        ScavCaseItem(
                            scav_case_id=scav_case.id,
                            tarkov_id=tid,
                            price=price_f,
                            name=item["name"],
                            amount=qty,
                        )
                    )
                    total_return += price_f * qty

                session.add_all(case_items)
                # compute return val
                scav_case._return = total_return

            # if the outer transaction was started then commit it. if the caller started then they can commit
            if not session.in_transaction():
                session.commit()

            return scav_case

        except Exception:
            session.rollback()
            current_app.logger.exception("Error inserting scav case into the database")
            raise
