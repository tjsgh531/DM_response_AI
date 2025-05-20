from sqlalchemy.orm import Session
from app.models import Customer

class CustomerService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_ig_handle(self, handle: str) -> Customer | None:
        return self.db.query(Customer).filter(Customer.ig_handle == handle).first()
