import os
import requests
from dotenv import load_dotenv

load_dotenv()
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")

class DMResponser:
    def handle(self, message, ig_business_id: str):
        print("📌 DM Responser가 전달 받은 데이터")
        
        try:
            sender_id = message["sender"]["id"]
            text = message["message"]["text"]

            print(f"📩 DM 수신: {text} (From: {sender_id})")
            reply = self.generate_reply(text)
            self.send_dm(sender_id, reply, ig_business_id)

        except Exception as e:
            print("❌ DM 처리 오류:", str(e))

    # 메세지 응답 생성 함수
    def generate_reply(self, message: str) -> str:
        return f"안녕하세요! 보내주신 메시지 '{message}' 잘 받았습니다 😊"

    # Instagram 메시지 전송 함수
    def send_dm(self, recipient_id: str, text: str, ig_business_id: str):
        url = f"https://graph.facebook.com/v18.0/{ig_business_id}/messages"
        headers = {
            "Authorization": f"Bearer {PAGE_ACCESS_TOKEN}"
        }
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": text}
        }

        print("📤 메시지 전송 URL:", url)
        print("📤 Payload:", payload)
        response = requests.post(url, headers=headers, json=payload)
        print("📤 DM 응답 전송 결과:", response.status_code, response.text)
