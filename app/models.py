from sqlalchemy import Column, Integer, String, DateTime
from app.db import Base
import datetime

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    ig_handle = Column(String, unique=True, index=True)  # Instagram sender_id
    name = Column(String)
    last_visit = Column(DateTime, default=datetime.datetime.utcnow)
    service_info = Column(String)  # 시술 내역 (예: "젤네일, 그라데이션, 파츠")
