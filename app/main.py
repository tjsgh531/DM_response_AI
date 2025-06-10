from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
import os
import json
import time
import threading
from dotenv import load_dotenv

from app.dm_responser import DMResponser
from app.reels_responser import ReelsResponser

# 환경 변수 로드
load_dotenv()
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# FastAPI 앱 생성
app = FastAPI()

# 응답 핸들러 인스턴스
dm_responser = DMResponser()
reels_responser = ReelsResponser()

# Webhook 인증용 GET
@app.get("/webhook")
async def verify_webhook(request: Request):
    print("🛠 Webhook 인증 Get 수신")

    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    return JSONResponse(content={"error": "Invalid token"}, status_code=403)

# Webhook POST 
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    print("📨 Webhook 수신:\n", json.dumps(data, indent=2))

    try:
        for entry in data.get("entry", []):
            # 🔹 릴스/게시글 댓글 이벤트 처리
            if "changes" in entry:
                for change in entry["changes"]:
                    field = change.get("field")
                    if field == "comments":
                        print("💬 릴스/게시글 댓글 수신!")
                        reels_responser.handle(change)

            # 🔹 DM 이벤트 처리
            elif "messaging" in entry:
                for message in entry.get("messaging", []):
                    dm_responser.handle(message)

        return {"status": "ok"}

    except Exception as e:
        print("❌ 오류:", str(e))
        return JSONResponse(content={"error": "Internal Server Error"}, status_code=500)

# 서버 유지를 위한 쓰레드
def keep_alive():
    while True:
        time.sleep(60)

threading.Thread(target=keep_alive, daemon=True).start()
