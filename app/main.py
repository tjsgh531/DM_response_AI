from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os
import json

from app.db import SessionLocal
from app import crud
from app.response_generator import ResponseGenerator
from app.webhook_handler import send_dm

# 🔐 환경변수 로드 및 응답 생성기 초기화
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
response_generator = ResponseGenerator(api_key)

# 🚀 FastAPI 앱 시작
app = FastAPI()

# ✅ DM 수신용 Webhook 엔드포인트
@app.post("/webhook")
async def webhook(request: Request):
    print("📥 DM 수신됨")

    try:
        data = await request.json()
        print("📨 Raw JSON 수신:\n", json.dumps(data, indent=2))

        messaging_event = data["entry"][0]["messaging"][0]
        message_text = messaging_event["message"]["text"]
        sender_id = messaging_event["sender"]["id"]

        # ✅ DB 세션 시작
        db = SessionLocal()

        # ✅ 고객 조회 또는 생성
        customer = crud.get_customer_by_sns_id(db, sender_id)
        if not customer:
            customer = crud.create_customer(db, sns_id=sender_id, name="무명고객")
            print("🆕 새로운 고객 생성:", sender_id)

        # ✅ 고객 정보 요약 문자열 생성
        info_text = f"""
        고객 정보:
        - 방문 횟수: {customer.visit_count}
        - 최근 시술: {customer.last_treatment or "없음"}
        - 최근 방문일: {customer.last_visit_date or "없음"}
        """

        # ✅ GPT 응답 생성
        prompt = f"""{info_text.strip()}\n\n고객 메시지: {message_text}"""
        reply = response_generator.generate(prompt)
        print("🤖 생성된 응답:", reply)

        # ✅ 응답 전송
        send_dm(sender_id, reply)

        return {"status": "done"}

    except Exception as e:
        print("❌ 오류 발생:", str(e))
        return JSONResponse(content={"error": "invalid message format"}, status_code=400)
