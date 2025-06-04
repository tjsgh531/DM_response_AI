from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()

class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sns_id = Column(String, unique=True, nullable=False) 
    name = Column(String, nullable=False)
    visit_count = Column(Integer, default=0)
    last_treatment = Column(String)
    last_visit_date = Column(Date)
    notes = Column(String)

    visits = relationship("Visit", back_populates="customer", cascade="all, delete-orphan")

class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)  # 수정된 부분 ✅
    visit_date = Column(Date, nullable=False)
    treatment = Column(String, nullable=False)

    customer = relationship("Customer", back_populates="visits")