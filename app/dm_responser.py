import os
import requests
from dotenv import load_dotenv

load_dotenv()
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")

class DMResponser:
    def handle(self, entry):
        try:
            event = entry["messaging"][0]
            sender_id = event["sender"]["id"]
            text = event["message"]["text"]

            print(f"📩 DM 수신: {text} (From: {sender_id})")
            reply = self.generate_reply(text)
            self.send_dm(sender_id, reply)

        except Exception as e:
            print("❌ DM 처리 오류:", str(e))

    # 메세지 응답 생성 함수
    def generate_reply(self, message: str) -> str:
        # 실제 GPT 호출 로직으로 대체 가능
        return f"안녕하세요! 보내주신 메시지 '{message}' 잘 받았습니다 😊"

    # 메세지 전송 함수
    def send_dm(self, recipient_id: str, text: str):
        url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
        payload = {
            "messaging_type": "RESPONSE",
            "recipient": {"id": recipient_id},
            "message": {"text": text}
        }
        response = requests.post(url, json=payload)
        print("📤 DM 응답 전송 결과:", response.status_code, response.text)
