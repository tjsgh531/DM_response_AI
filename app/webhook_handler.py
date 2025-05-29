class WebhookHandler:
    def __init__(self, response_generator):
        self.response_generator = response_generator

    def handle(self, message_text: str):
        print("🤖 받은 메시지:", message_text)  # ← 이거 추가
        reply = self.response_generator.generate(message_text)
        print("🤖 생성된 응답:", reply)         # ← 이거도 추가
        return reply

