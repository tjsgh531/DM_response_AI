from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# ✅ .env에서 환경변수 로드
load_dotenv()

# ✅ DATABASE_URL 환경변수에서 가져오기
DATABASE_URL = os.getenv("DATABASE_URL")

# ✅ SQLAlchemy 연결 설정
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ✅ Base 클래스는 모든 모델들이 상속받게 됨
Base = declarative_base()
