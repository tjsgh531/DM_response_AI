from sqlalchemy.orm import Session
from app import models
from datetime import date

# ✅ 고객 관련 CRUD 
def get_customer_by_sns_id(db: Session, sns_id: str):
    return db.query(models.Customer).filter(models.Customer.sns_id == sns_id).first()

def create_customer(db: Session, sns_id: str, name: str = "무명고객", notes: str = ""):
    new_customer = models.Customer(sns_id=sns_id, name=name, notes=notes)
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer

def update_customer_visit_info(db: Session, customer: models.Customer, treatment: str, visit_date: date):
    customer.visit_count += 1
    customer.last_treatment = treatment
    customer.last_visit_date = visit_date
    db.commit()
    db.refresh(customer)


# ✅ 시술 이력 관련 CRUD
def add_visit(db: Session, customer: models.Customer, visit_date: date, treatment: str):
    visit = models.Visit(
        customer_id=customer.id,
        visit_date=visit_date,
        treatment=treatment
    )
    db.add(visit)
    update_customer_visit_info(db, customer, treatment, visit_date)
    db.commit()
    db.refresh(visit)
    return visit

def get_all_visits_by_customer(db: Session, customer: models.Customer):
    return db.query(models.Visit).filter(models.Visit.customer_id == customer.id).order_by(models.Visit.visit_date.desc()).all()

def get_latest_visit_by_customer(db: Session, customer: models.Customer):
    return db.query(models.Visit).filter(models.Visit.customer_id == customer.id).order_by(models.Visit.visit_date.desc()).first()
