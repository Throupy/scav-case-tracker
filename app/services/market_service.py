from typing import List, Optional, Dict, Any

from app.models import TarkovItem, User
from app.services import BaseService
from app.market.utils import get_market_information


class MarketService(BaseService):
    """Service for handling market-related business logic"""
    
    def search_items(self, query: str, limit: int = 10) -> List[TarkovItem]:
        """Search for items by name"""
        if not query.strip():
            return []
            
        return TarkovItem.query.filter(
            TarkovItem.name.ilike(f"%{query}%")
        ).limit(limit).all()
    
    def get_item_by_tarkov_id(self, tarkov_id: str) -> Optional[TarkovItem]:
        """Get item by Tarkov ID"""
        return TarkovItem.query.filter_by(tarkov_id=tarkov_id).first()
    
    def get_item_price_data(self, tarkov_item_id: str) -> Dict[str, Any]:
        """Get formatted price data for an item"""
        # TODO: Think about using the flask caching decoration here
        # TODO: https://flask.palletsprojects.com/en/stable/patterns/viewdecorators/#caching-decorator
        # TODO: Or Flask-Caching library, which would be heavier
        market_data = get_market_information(tarkov_item_id)
        # TODO: Seemingly the response to the above has changed... Investigate
        if not market_data or "data" not in market_data or not market_data["data"]["items"]:
            return {"error": "Price unavailable"}
        
        item = market_data["data"]["items"][0]
        
        # Extract values safely
        low_price = item.get("low24hPrice")
        high_price = item.get("high24hPrice")
        avg_price_24h = item.get("avg24hPrice")
        highest_vendor = "Flea Market"
        lowest_vendor = "Flea Market"
        
        # Fallback to highest trader price if market data is missing
        if not all((low_price, high_price, avg_price_24h)):
            highest_trader = max(
                item.get("sellFor", []), 
                key=lambda x: x["priceRUB"], 
                default=None
            )
            highest_vendor = highest_trader['vendor']['name']

            lowest_trader = min(
                item.get("sellFor", []),
                key=lambda x: x["priceRUB"],
                default=None
            )
            lowest_vendor = lowest_trader['vendor']['name']


            low_price = lowest_trader["price"] if lowest_trader else 0
            high_price = highest_trader["price"] if highest_trader else 0
            avg_price_24h = high_price
        
        return {
            "low_price": low_price,
            "high_price": high_price,
            "avg_price_24h": avg_price_24h,
            "highest_vendor": highest_vendor,
            "lowest_vendor": lowest_vendor
        }
    
    def track_item_for_user(self, user: User, tarkov_item_id: str) -> bool:
        """Add item to user's tracked items"""
        item = self.get_item_by_tarkov_id(tarkov_item_id)
        if not item:
            return False
            
        if item not in user.tracked_items:
            user.tracked_items.append(item)
            self.commit()
            return True
        
        return False  # Already tracking
    
    def untrack_item_for_user(self, user: User, tarkov_item_id: str) -> bool:
        """Remove item from user's tracked items"""
        item = self.get_item_by_tarkov_id(tarkov_item_id)
        if not item:
            return False
            
        if item in user.tracked_items:
            user.tracked_items.remove(item)
            self.commit()
            return True
            
        return False  # Wasn't tracking
    
    def get_user_tracked_items(self, user: User) -> List[TarkovItem]:
        """Get all items tracked by user"""
        return user.tracked_items