class WebhookHandler:
    def __init__(self, response_generator):
        self.response_generator = response_generator

    def handle(self, message_text: str):
        reply = self.response_generator.generate(message_text, customer)
        return reply
