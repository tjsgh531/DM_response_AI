# init_db.py
from app.db import engine
from app.models import Base
from dotenv import load_dotenv

# .env 로드
load_dotenv()

def init():
    print("📦 DB 테이블 생성 시작...")
    Base.metadata.create_all(bind=engine)
    print("✅ 모든 테이블이 생성되었습니다.")

if __name__ == "__main__":
    init()
