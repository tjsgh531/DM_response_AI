from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import json
import os

from app.webhook_handler import WebhookHandler
from app.response_generator import ResponseGenerator
from app.customer_service import CustomerService
from app.db import SessionLocal

# 🔑 .env 로드
load_dotenv()

app = FastAPI()

# ✅ 인증 토큰 환경변수에서 불러오기
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# ✅ DI처럼 핸들러 인스턴스 구성
def create_handler():
    db = SessionLocal()
    customer_service = CustomerService(db)
    response_generator = ResponseGenerator(os.getenv("OPENAI_API_KEY"))
    return WebhookHandler(customer_service, response_generator)

handler = create_handler()

# ✅ Webhook 인증용 GET (Meta에서 요청)
@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)
    return JSONResponse(content={"error": "Invalid token"}, status_code=403)

# ✅ DM 수신용 POST
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    # 💥 전체 Raw JSON 데이터 출력
    print("📨 Raw JSON 수신:\n", json.dumps(data, indent=2))

    try:
        change = data["entry"][0]["changes"][0]
        message_text = change["value"]["message"]["text"]
        sender_id = change["value"]["sender"]["id"]

        """
        reply = handler.handle(message_text, sender_id)
        print("🤖 생성된 응답:", reply)
        """

        return {"status": "done"}

    except Exception as e:
        print("❌ 처리 중 오류:", str(e))
        return JSONResponse(content={"error": "invalid message format"}, status_code=400)

print("🔐 VERIFY_TOKEN =", VERIFY_TOKEN)