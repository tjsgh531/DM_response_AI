import json
import re
from langchain_community.chat_models import ChatOpenAI
from langchain.schema import HumanMessage
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain

class ResponseGenerator:
    def __init__(self, api_key: str):
        self.llm = ChatOpenAI(
            temperature=0.0, # 예약과 같은 정보 추출 시에는 낮은 온도로 설정
            model="gpt-3.5-turbo",
            openai_api_key=api_key
        )
        self.memories = {}

    def generate(self, message_text: str, sender_id: str) -> dict:
        if sender_id not in self.memories:
            self.memories[sender_id] = ConversationBufferMemory()
        
        memory = self.memories[sender_id]

        conversation = ConversationChain(
            llm=self.llm,
            memory=memory,
            verbose=False
        )
        
        contextual_message = f"""
        당신은 고객 지원 및 예약 담당자입니다. 고객의 메시지를 분석하여 다음 작업을 수행해주세요:

        1. 고객의 주요 의도를 파악합니다 (예: 가격 문의, 수리 요청, 예약).
        2. 예약 의도가 감지되면, 관련된 주요 정보를 추출해주세요:
           - 원하는 날짜 (YYYY-MM-DD 형식)
           - 원하는 시간 (HH:MM 형식)
           - 인원수 (숫자)
           - 서비스 유형 (예: '타이어 교체', '엔진 오일 교환', '정기 점검')
           추출되지 않은 정보는 'None' 또는 'unknown'으로 표시합니다.
        3. 고객에게 친절하고 명확하게 응답합니다. 예약 관련 문의 시, 예약 가능 여부 확인 또는 예약 진행에 대한 안내를 포함할 수 있습니다.
        4. 만약 예약 의도가 높다고 판단되고, 관련 정보가 하나 이상 추출되었다면, 응답의 마지막 줄에 다음 형식으로 정보를 포함시켜주세요:
           BOOKING_INTENT_DETECTED: {{'date': 'YYYY-MM-DD or None', 'time': 'HH:MM or None', 'people': 'Number or None', 'service': 'Service Type or None'}}

        [고객 메시지]
        "{message_text}"

        [대화 기록]
        {memory.chat_memory.messages}

        [응답]
        """
        
        raw_llm_response = conversation.predict(input=contextual_message)
        
        booking_details = None
        user_reply = raw_llm_response

        booking_intent_marker = "BOOKING_INTENT_DETECTED: "
        if booking_intent_marker in raw_llm_response:
            parts = raw_llm_response.split(booking_intent_marker)
            user_reply = parts[0].strip() # 마커 이전 부분을 사용자 응답으로
            
            # 마커 이후의 문자열에서 JSON과 유사한 딕셔너리 부분 추출 시도
            booking_info_str = parts[1].strip()
            try:
                # LLM이 생성하는 문자열은 엄격한 JSON이 아닐 수 있으므로, 정규표현식 등으로 추가 처리 가능
                # 예: 작은따옴표를 큰따옴표로, None을 null로 등
                # 여기서는 LLM이 최대한 JSON에 가까운 형태로 출력한다고 가정
                # 'None'을 Python의 None으로 바꾸고 json.loads 대신 ast.literal_eval 사용 고려
                
                # 간단한 문자열 치환으로 JSON 호환성 높이기
                booking_info_str = booking_info_str.replace("'", '"')
                booking_info_str = booking_info_str.replace("None", 'null') # JSON에서 null 사용
                
                # 마지막에 불필요한 문자가 붙는 경우 제거 (예: LLM이 마침표를 찍는 경우)
                # 정규표현식으로 딕셔너리 형태만 정확히 추출하는 것이 더 안전함
                match = re.search(r"\{.*\}", booking_info_str)
                if match:
                    booking_info_str = match.group(0)
                    booking_details = json.loads(booking_info_str)
                    # null 값을 Python의 None으로 다시 변경
                    if isinstance(booking_details, dict):
                        for key, value in booking_details.items():
                            if value == 'null': # 문자열 'null'을 Python None으로
                                booking_details[key] = None
                else:
                    print(f"⚠️ 예약 정보 문자열에서 유효한 딕셔너리 패턴을 찾지 못했습니다: {parts[1].strip()}")

            except json.JSONDecodeError as e:
                print(f"❌ 예약 정보 JSON 파싱 오류: {e}. 문자열: {parts[1].strip()}")
            except Exception as e_gen:
                print(f"❌ 예약 정보 처리 중 일반 오류: {e_gen}. 문자열: {parts[1].strip()}")

        # ConversationChain 사용 시 메모리는 자동으로 업데이트 됨
        # memory.chat_memory.add_user_message(message_text) # 이미 contextual_message에 포함되어 전달됨
        # memory.chat_memory.add_ai_message(user_reply) # booking_details가 제외된 순수 응답을 저장해야 함

        return {"reply": user_reply, "booking_details": booking_details}

    def summarize(self, conversation_history_str: str) -> str:
        """
        Generates a summary of the given conversation history.
        """
        summary_prompt_text = f"""
        다음 대화 내용을 간결하게 요약해주세요:

        {conversation_history_str}

        요약:
        """
        # Using the llm instance from the class
        summary_result = self.llm([HumanMessage(content=summary_prompt_text)])
        return summary_result.content
