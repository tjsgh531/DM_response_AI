from langchain_community.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

class ResponseGenerator:
    def __init__(self, api_key: str):
        self.llm = ChatOpenAI(
            temperature=0.7,
            model="gpt-3.5-turbo",
            openai_api_key=api_key
        )

    def generate(self, message_text: str) -> str:
        prompt = f"""
        [시나리오]
        - 고객 메시지: "{message_text}"

        [목표]
        - 메시지 의도 파악 (가격문의, 보수요청, 예약)
        - 고객 상태 고려한 따뜻한 안내
        - 예약 시 예약 링크 포함

        [응답]
        """

        result = self.llm([HumanMessage(content=prompt)])
        return result.content
