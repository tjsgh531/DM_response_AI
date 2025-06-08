import os
import requests
from dotenv import load_dotenv

load_dotenv()
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")

class ReelsResponser:
    def handle(self, change):
        try:
            value = change.get("value", {})
            comment_id = value.get("id")
            text = value.get("text")
            sender = value.get("from", {})
            sender_id = sender.get("id")

            # 내 페이지 또는 Instagram 계정 ID라면 무시
            MY_INSTAGRAM_USER_ID = os.getenv("MY_INSTAGRAM_USER_ID")
            if sender_id == MY_INSTAGRAM_USER_ID:
                print("🔁 내가 단 댓글입니다. 무시합니다.")
                return

            print(f"💬 댓글 수신: {text} (ID: {comment_id})")
            if comment_id and text:
                reply = self.generate_reply(text)
                self.reply_to_comment(comment_id, reply)

        except Exception as e:
            print("❌ 댓글 처리 오류:", str(e))

    # 릴스 답변 생성 함수
    def generate_reply(self, comment_text: str) -> str:
        # 실제 GPT 호출 로직으로 대체 가능
        return f"댓글 남겨주셔서 감사합니다! 🙌 '{comment_text}'"

    # 릴스 답변 전송 함수
    def reply_to_comment(self, comment_id: str, text: str):
        url = f"https://graph.facebook.com/v18.0/{comment_id}/replies"
        headers = {"Authorization": f"Bearer {PAGE_ACCESS_TOKEN}"}
        payload = {"message": text}
        response = requests.post(url, json=payload, headers=headers)
        print("📤 댓글 응답 전송 결과:", response.status_code, response.text)
