import os
import requests
from dotenv import load_dotenv

# Langchain
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

load_dotenv()
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")


class DMResponser:
    def __init__(self):
        self.replied_messages = set()
        self.llm = ChatOpenAI(
            temperature=0.7,
            model="gpt-4",  # 또는 gpt-3.5-turbo 등
        )

    def handle(self, message):
        try:
            if "read" in message:
                print("👁️ 읽음 이벤트입니다. 응답하지 않습니다.")
                return

            if message.get("message", {}).get("is_echo"):
                print("🔁 Echo 메시지입니다. 응답하지 않습니다.")
                return

            if "message" in message and "text" in message["message"]:
                sender_id = message["sender"]["id"]
                text = message["message"]["text"]
                message_id = message["message"].get("mid")

                print(f"🔎 처리 중인 메시지 ID: {message_id}")

                if message_id in self.replied_messages:
                    print("✅ 이미 응답한 메시지입니다. 무시합니다.")
                    return
                self.replied_messages.add(message_id)

                if len(self.replied_messages) > 10000:
                    print("🧹 캐시 초기화")
                    self.replied_messages.clear()

                print(f"📩 DM 수신: {text} (From: {sender_id})")
                reply = self.generate_reply(text)
                self.send_dm(sender_id, reply)
                return

            print("⚠️ 처리 대상이 아닌 메시지입니다.")

        except Exception as e:
            print("❌ DM 처리 오류:", str(e))

    def generate_reply(self, message: str) -> str:
        try:
            response = self.llm([HumanMessage(content=message)])
            return response.content
        except Exception as e:
            print("❗Langchain 응답 실패:", e)
            return "죄송해요! 잠시 오류가 발생했어요. 다시 말씀해 주실 수 있나요?"

    def send_dm(self, recipient_id: str, text: str):
        url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
        payload = {
            "messaging_type": "RESPONSE",
            "recipient": {"id": recipient_id},
            "message": {"text": text}
        }
        response = requests.post(url, json=payload)
        print("📤 DM 응답 전송 결과:", response.status_code, response.text)
