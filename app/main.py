from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

import json
import os
import requests
import time
import threading
import psycopg2 # Changed from sqlite3
from datetime import datetime

from app.webhook_handler import WebhookHandler
from app.response_generator import ResponseGenerator
from app.mcp_handler import MCPHandler
from langchain.schema import HumanMessage, AIMessage


# 🔑 .env 로드
load_dotenv()

app = FastAPI()

# DATABASE_FILE global variable removed as it's no longer needed for PostgreSQL

# ✅ 인증 토큰 환경변수에서 불러오기
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# ✅ DI처럼 핸들러 인스턴스 구성
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MCP_API_KEY_VALUE = os.getenv("MCP_API_KEY")

response_generator_instance = ResponseGenerator(OPENAI_API_KEY)
webhook_handler_instance = WebhookHandler(response_generator_instance)
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
        
        generation_result = webhook_handler_instance.handle(message_text, sender_id)
        user_facing_reply = generation_result['reply']
        booking_details = generation_result['booking_details']

        print(f"🤖 생성된 초기 응답: {user_facing_reply}")
        if booking_details:
            print(f"ℹ️ 추출된 예약 정보: {booking_details}")
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
            "message": {"text": user_facing_reply},
            "messaging_type": "RESPONSE"
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            print("✅ 메시지 전송 성공")
        else:
            print(f"❌ 메시지 전송 실패: {response.status_code} {response.text}")

        # 대화 요약 및 저장 로직 추가
        try:
            if sender_id in response_generator_instance.memories:
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


# 대화 요약 및 DB 저장 함수 (PostgreSQL 버전)
def summarize_conversation_and_store(customer_id: str, conversation_history_str: str, response_generator_instance: ResponseGenerator):
    """
    Generates a summary of the conversation and stores it in the PostgreSQL database.
    """
    print(f"✍️ {customer_id} 대화 요약 시작 (PostgreSQL)...")
    
    # Load database connection parameters from environment variables
    db_host = os.getenv("DB_HOST")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")
    db_port = os.getenv("DB_PORT", "5432")

    if not all([db_host, db_user, db_password, db_name, db_port]):
        print("❌ Error: Missing PostgreSQL environment variables for summarization storage.")
        return

    conn = None
    try:
        # ResponseGenerator의 summarize 메소드 사용
        summary = response_generator_instance.summarize(conversation_history_str)
        print(f"📝 생성된 요약: {summary}")

        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )
        
        with conn.cursor() as cur:
            # conversation_time is set by DEFAULT CURRENT_TIMESTAMP in PostgreSQL schema
            # id is SERIAL PRIMARY KEY
            insert_query = """
                INSERT INTO conversations (customer_id, conversation_time, summary) 
                VALUES (%s, %s, %s)
            """
            # Note: conversation_time is now set by default in the DB, 
            # but we can still provide it if needed, or adjust the table schema.
            # For consistency with the schema in init_db.py (which has DEFAULT CURRENT_TIMESTAMP),
            # we provide current datetime.
            cur.execute(insert_query, (customer_id, datetime.now(), summary))
            conn.commit()
        
        print(f"💾 {customer_id} 대화 요약 저장 성공 (PostgreSQL)")

    except psycopg2.OperationalError as e:
        print(f"❌ PostgreSQL Operational Error (summarize_conversation_and_store): {e}")
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL DB 저장 오류 (summarize_conversation_and_store): {e}")
    except Exception as e:
        print(f"❌ 요약 생성 또는 DB 저장 중 예외 발생: {e}")
    finally:
        if conn:
            conn.close()
            print("🔌 PostgreSQL connection for summarization closed.")
