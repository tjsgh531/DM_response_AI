from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

import json
import os
import requests
import time
import threading
import sqlite3
from datetime import datetime

from app.webhook_handler import WebhookHandler
from app.response_generator import ResponseGenerator
from app.mcp_handler import MCPHandler
from langchain.schema import HumanMessage, AIMessage


# 🔑 .env 로드
load_dotenv()

app = FastAPI()

# Database file path (consistent with init_db.py)
# Assuming init_db.py is in the parent directory of 'app'
DATABASE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'chat_history.db')


# ✅ 인증 토큰 환경변수에서 불러오기
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# ✅ DI처럼 핸들러 인스턴스 구성
# (MCPHandler와 WebhookHandler를 별도로 인스턴스화하거나, WebhookHandler가 MCPHandler를 포함하도록 구조 변경 가능)
# 여기서는 main.py에서 두 핸들러를 모두 관리하는 것으로 가정합니다.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MCP_API_KEY_VALUE = os.getenv("MCP_API_KEY") # 명확한 이름 사용

response_generator_instance = ResponseGenerator(OPENAI_API_KEY)
webhook_handler_instance = WebhookHandler(response_generator_instance) # WebhookHandler가 ResponseGenerator를 사용
mcp_handler_instance = MCPHandler(api_key=MCP_API_KEY_VALUE)


# ✅ 환경변수 추가
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")

# ✅ Webhook 인증용 GET (Meta에서 요청)
@app.get("/webhook")
async def verify_webhook(request: Request):
    print("🛠 verify_webhook 작동")
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)
    
    return JSONResponse(content={"error": "Invalid token"}, status_code=403)

# ✅ DM 수신용 POST
@app.post("/webhook")
async def webhook(request: Request):
    print("🛠 webhook Post 작동")
    data = await request.json()

    # 💥 전체 Raw JSON 데이터 출력
    print("📨 Raw JSON 수신:\n", json.dumps(data, indent=2))

    try:
        change = data["entry"][0]["changes"][0]
        message_text = change["value"]["message"]["text"]
        sender_id = change["value"]["sender"]["id"]
        
        # ResponseGenerator의 generate 메소드는 이제 dict를 반환합니다.
        # {'reply': user_facing_reply, 'booking_details': parsed_details_dict_or_none}
        generation_result = webhook_handler_instance.handle(message_text, sender_id)
        user_facing_reply = generation_result['reply']
        booking_details = generation_result['booking_details']

        print(f"🤖 생성된 초기 응답: {user_facing_reply}")
        if booking_details:
            print(f"ℹ️ 추출된 예약 정보: {booking_details}")
            # 예약 시도
            # TODO: 고객 이름과 같은 추가 정보가 필요하다면 booking_details에 포함시키거나,
            #       별도의 대화 흐름으로 수집해야 합니다. 여기서는 booking_details만 사용합니다.
            #       또한, 실제로는 날짜/시간 포맷 검증, 필수 필드 확인 등이 필요합니다.
            
            # 필수 정보 (예: 날짜, 시간, 서비스)가 있는지 확인 후 예약 시도
            # 여기서는 mcp_handler.make_reservation이 내부적으로 처리한다고 가정하거나,
            # 또는 여기서 간단한 검증을 추가할 수 있습니다.
            # 예: if booking_details.get("date") and booking_details.get("time") and booking_details.get("service"):
            
            reservation_result = mcp_handler_instance.make_reservation(booking_details)
            print(f"🎟️ MCP 예약 시도 결과: {reservation_result}")

            if reservation_result.get("success"):
                user_facing_reply += f"\n\n🎉 예약 성공! {reservation_result.get('message', '')} (ID: {reservation_result.get('booking_id', 'N/A')})"
            else:
                user_facing_reply += f"\n\n⚠️ 예약 실패: {reservation_result.get('message', '죄송합니다, 예약 처리 중 문제가 발생했습니다.')}"
        
        print(f"💬 최종 사용자 응답: {user_facing_reply}")

        # Meta Graph API를 통해 메시지 전송
        url = f"https://graph.facebook.com/v18.0/me/messages"
        headers = {
            "Authorization": f"Bearer {FACEBOOK_PAGE_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "recipient": {"id": sender_id},
            "message": {"text": user_facing_reply}, # 최종 응답 사용
            "messaging_type": "RESPONSE"
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            print("✅ 메시지 전송 성공")
        else:
            print(f"❌ 메시지 전송 실패: {response.status_code} {response.text}")

        # 대화 요약 및 저장 로직 추가
        # 요약은 원래 대화 내용을 기반으로 해야 하므로, response_generator_instance를 전달합니다.
        try:
            if sender_id in response_generator_instance.memories: # response_generator_instance에서 메모리 접근
                memory = response_generator_instance.memories[sender_id]
                history_messages = memory.chat_memory.messages
                conversation_history_str = "\n".join(
                    [f"{'Human' if isinstance(msg, HumanMessage) else 'AI'}: {msg.content}" for msg in history_messages]
                )
                
                if conversation_history_str:
                    summarize_conversation_and_store(sender_id, conversation_history_str, response_generator_instance)
            else:
                print(f"🤷 사용자 ID {sender_id}에 대한 메모리를 찾을 수 없습니다. (요약 스킵)")

        except Exception as e_summary:
            print(f"❌ 대화 요약 및 저장 중 오류: {e_summary}")

        return {"status": "done"}

    except Exception as e:
        print("❌ 처리 중 오류:", str(e))
        return JSONResponse(content={"error": "invalid message format"}, status_code=400)

# ✅ 콘솔 확인용 토큰 출력
print("🔐 VERIFY_TOKEN =", VERIFY_TOKEN)

# ✅ Render에서 꺼지지 않도록 서버 유지용 쓰레드 추가
def keep_alive():
    while True:
        time.sleep(60)

threading.Thread(target=keep_alive).start()


# 대화 요약 및 DB 저장 함수
def summarize_conversation_and_store(customer_id: str, conversation_history_str: str, response_generator_instance: ResponseGenerator):
    """
    Generates a summary of the conversation and stores it in the SQLite database.
    """
    print(f"✍️ {customer_id} 대화 요약 시작...")
    try:
        # ResponseGenerator의 summarize 메소드 사용
        summary = response_generator_instance.summarize(conversation_history_str)
        print(f"📝 생성된 요약: {summary}")

        conn = None
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO conversations (customer_id, conversation_time, summary)
                VALUES (?, ?, ?)
            ''', (customer_id, datetime.now(), summary))
            conn.commit()
            print(f"💾 {customer_id} 대화 요약 저장 성공")
        except sqlite3.Error as e:
            print(f"❌ DB 저장 오류: {e}")
        finally:
            if conn:
                conn.close()

    except Exception as e:
        print(f"❌ 요약 생성 중 오류: {e}")
