from abc import ABC

from app.extensions import db

class BaseService(ABC):
    """Base service layer class with common DB operations"""
    def __init__(self) -> None:
        self.db = db

    # generic CRUD ops, will be abstract here and defined in children
    def save(self, obj: db.Model) -> db.Model:
        """Save an object to the database"""
        try:
            self.db.session.add(obj)
            self.sb.session.commit()
            return obj
        # Don't like being this generic.. but it's an abstract class
        # will implement lower-level catching in the children
        except Exception as e:
            self.db.session.rollback()
            raise e

    def delete(self, obj):
        """Delete object from database"""
        try:
            self.db.session.delete(obj)
            self.db.session.commit()
            return True
        except Exception as e:
            self.db.session.rollback()
            raise e
            
    def commit(self):
        """Commit current transaction"""
        try:
            self.db.session.commit()
        except Exception as e:
            self.db.session.rollback()
            raise e

