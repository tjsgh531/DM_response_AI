from app.db import SessionLocal
from app import crud
from datetime import date

# 🔌 DB 세션 연결
db = SessionLocal()

# 1️⃣ 고객 생성 테스트
customer = crud.create_customer(db, name="홍길동", notes="첫 방문 고객")
print("✅ 고객 생성:", customer.name, customer.id)

# 2️⃣ 방문 기록 추가 테스트
visit = crud.add_visit(
    db=db,
    customer_id=customer.id,
    visit_date=date.today(),
    treatment="손 젤네일"
)
print("✅ 방문 기록 추가:", visit.visit_date, visit.treatment)

# 3️⃣ 고객 정보 조회 테스트
fetched_customer = crud.get_customer_by_id(db, customer.id)
print("👤 고객 조회:", fetched_customer.name, fetched_customer.visit_count, fetched_customer.last_treatment)

# 4️⃣ 방문 이력 조회 테스트
visits = crud.get_visits_by_customer(db, customer.id)
print("📜 방문 이력:")
for v in visits:
    print("-", v.visit_date, v.treatment)

# 🔚 세션 종료
db.close()
