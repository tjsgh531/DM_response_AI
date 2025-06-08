import os
import requests
from dotenv import load_dotenv

load_dotenv()
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
MY_INSTAGRAM_USER_ID = os.getenv("MY_INSTAGRAM_USER_ID")

class ReelsResponser:
    def handle(self, change):
        try:
            value = change.get("value", {})
            comment_id = value.get("id")
            text = value.get("text")
            sender = value.get("from", {})
            sender_id = sender.get("id")

            if sender_id == MY_INSTAGRAM_USER_ID:
                print("🔁 내가 단 댓글입니다. 무시합니다.")
                return

            if self.already_replied(comment_id):
                print("✅ 이미 답변한 댓글입니다. 무시합니다.")
                return

            print(f"💬 댓글 수신: {text} (ID: {comment_id})")
            if comment_id and text:
                reply = self.generate_reply(text)
                self.reply_to_comment(comment_id, reply)

        except Exception as e:
            print("❌ 댓글 처리 오류:", str(e))

    def already_replied(self, comment_id: str) -> bool:
        # ✅ 대댓글(replies) 기준으로 확인
        url = f"https://graph.facebook.com/v18.0/{comment_id}/replies?access_token={PAGE_ACCESS_TOKEN}"
        response = requests.get(url)
        if response.status_code != 200:
            print("❗ 댓글 응답 목록 조회 실패:", response.status_code, response.text)
            return False
        data = response.json().get("data", [])
        for item in data:
            if item.get("from", {}).get("id") == MY_INSTAGRAM_USER_ID:
                return True
        return False

    def generate_reply(self, comment_text: str) -> str:
        return f"댓글 남겨주셔서 감사합니다! 🙌 '{comment_text}'"

    def reply_to_comment(self, comment_id: str, text: str):
        url = f"https://graph.facebook.com/v18.0/{comment_id}/replies"
        headers = {"Authorization": f"Bearer {PAGE_ACCESS_TOKEN}"}
        payload = {"message": text}
        response = requests.post(url, json=payload, headers=headers)
        print("📤 댓글 응답 전송 결과:", response.status_code, response.text)
