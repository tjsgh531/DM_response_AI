class WebhookHandler:
    def __init__(self, customer_service, response_generator):
        self.customer_service = customer_service
        self.response_generator = response_generator

    def handle(self, message_text: str, sender_id: str):
        customer = self.customer_service.get_by_ig_handle(sender_id)
        reply = self.response_generator.generate(message_text, customer)
        return reply
