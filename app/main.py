from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from dotenv import load_dotenv
import json
import os
import time
import threading
import requests

from app.webhook_handler import WebhookHandler
from app.response_generator import ResponseGenerator

# 🔑 .env 로드
load_dotenv()

app = FastAPI()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")

# ✅ 응답 전송 함수
def send_dm(recipient_id: str, text: str):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "messaging_type": "RESPONSE",
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    response = requests.post(url, json=payload)
    print("📤 DM 전송 결과:", response.status_code, response.text)
    return response

# ✅ 응답 생성 핸들러 구성
def create_handler():
    response_generator = ResponseGenerator(os.getenv("OPENAI_API_KEY"))
    return WebhookHandler(response_generator)

handler = create_handler()

# ✅ Webhook 인증용 GET
@app.get("/webhook")
async def verify_webhook(request: Request):
    print("🛠 verify_webhook 작동")
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    return JSONResponse(content={"error": "Invalid token"}, status_code=403)

# ✅ DM 수신용 POST
@app.post("/webhook")
async def webhook(request: Request):
    print("🛠 webhook Post 작동")
    data = await request.json()
    print("📨 Raw JSON 수신:\n", json.dumps(data, indent=2))

    try:
        messaging_event = data["entry"][0]["messaging"][0]
        message_text = messaging_event["message"]["text"]
        sender_id = messaging_event["sender"]["id"]

        # 🤖 응답 생성
        reply = handler.handle(message_text)
        print("🤖 생성된 응답:", reply)

        # 📤 응답 전송
        send_dm(sender_id, reply)

        return {"status": "done"}

    except Exception as e:
        print("❌ 처리 중 오류:", str(e))
        return JSONResponse(content={"error": "invalid message format"}, status_code=400)

# ✅ 콘솔 확인용
print("🔐 VERIFY_TOKEN =", VERIFY_TOKEN)
print("🔐 PAGE_ACCESS_TOKEN =", PAGE_ACCESS_TOKEN)

# ✅ 서버 유지를 위한 더미 쓰레드
def keep_alive():
    while True:
        time.sleep(60)

threading.Thread(target=keep_alive).start()
