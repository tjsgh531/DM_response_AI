from langchain_community.chat_models import ChatOpenAI
from langchain.schema import HumanMessage
from app.models import Customer

class ResponseGenerator:
    def __init__(self, api_key: str):
        self.llm = ChatOpenAI(
            temperature=0.7,
            model="gpt-3.5-turbo",
            openai_api_key=api_key
        )

    def generate(self, message_text: str, customer: Customer = None) -> str:
        if customer:
            context = f"""
            고객은 단골입니다.
            이름: {customer.name}
            마지막 시술일: {customer.last_visit}
            시술 정보: {customer.service_info}
            """
        else:
            context = "고객은 신규입니다."

        prompt = f"""
        [시나리오]
        - 고객 메시지: "{message_text}"
        - {context}

        [목표]
        - 메시지 의도 파악 (가격문의, 보수요청, 예약)
        - 고객 상태 고려한 따뜻한 안내
        - 예약 시 예약 링크 포함

        [응답]
        """

        result = self.llm([HumanMessage(content=prompt)])
        return result.content
