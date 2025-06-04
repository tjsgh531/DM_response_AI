from langchain_community.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

class ResponseGenerator:
    def __init__(self, api_key, db_client):
        self.llm = ChatOpenAI(
            temperature=0.7,
            model="gpt-4",
            openai_api_key=api_key
        )

        self.db = db_client  # 고객 DB 인스턴스 (MongoDB, PostgreSQL 등)

        # 고정 응답
        self.trigger_responses = {
            "주차": "주차는 건물 지하 1층에 가능합니다.",
            "영업시간": "운영시간은 오전 10시 ~ 오후 8시입니다."
        }

        # 가격 응답
        self.price_info = {
            "손 젤네일": "손 젤네일은 30,000원입니다.",
            "발 젤네일": "발 젤네일은 40,000원입니다."
        }

        # 예약 응답
        self.reservation_guide = "예약은 아래 링크에서 가능합니다.\n👉 https://예약링크"


    def generate(self, customer_id: str, message_text: str, history: list[str]) -> str:
        # 1. DB에서 고객 정보 불러오기
        customer_info = self.db.get_customer_info(customer_id)

        # 2. 특정 키워드 응답
        for trigger, reply in self.trigger_responses.items():
            if trigger in message_text:
                return reply
            
        for keyword, price in self.price_info.items():
            if keyword in message_text:
                return price
            
        if "예약" in message_text:
            return self.reservation_guide

        # 3. LLM 기반 응답
        customer_context = f"""당신은 네일샵 전문가입니다.
- 이 고객은 {customer_info['visit_count']}번째 방문입니다.
- 최근 방문일: {customer_info['last_visit_date']}
- 최근 시술: {customer_info['last_treatment']}"""

        messages = [{"role": "system", "content": customer_context}]

        for i, msg in enumerate(history):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({"role": role, "content": msg})

        messages.append({"role": "user", "content": message_text})

        result = self.llm(messages)
        return result.content.strip()
