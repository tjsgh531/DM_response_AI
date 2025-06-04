from db import engine
from models import Base
from dotenv import load_dotenv

load_dotenv()

def init():
    print("📦 DB 테이블 생성 시작...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("✅ 모든 테이블이 생성되었습니다.")

if __name__ == "__main__":
    init()
