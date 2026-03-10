import streamlit as st
from agents import (
    Agent,
    RunContextWrapper,
    handoff,
)
from my_agents.menu_agent import menu_agent
from my_agents.order_agent import order_agent
from my_agents.reservation_agent import reservation_agent
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.extensions import handoff_filters
from models import UserAccountContext, InputGuardRailOutput, HandoffData


input_guardrail_agent = Agent(
    name="Input Guardrail Agent",
    instructions="""
    Ensure the user's request specifically pertains to User Account details, Billing inquiries, Order information, or Technical Support issues, and is not off-topic. If the request is off-topic, return a reason for the tripwire. You can make small conversation with the user, specially at the beginning of the conversation, but don't help with requests that are not related to User Account details, Billing inquiries, Order information, or Technical Support issues.
""",
    output_type=InputGuardRailOutput,
)


def dynamic_triage_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
):
    return f"""
    반드시 한국어로 대화하세요.
    
    {RECOMMENDED_PROMPT_PREFIX}

    당신은 레스토랑 안내 에이전트입니다. 메뉴, 주문, 예약에 관한 고객 문의만 도와줍니다.
    고객의 이름을 불러주며 친절하게 응대합니다.
    
    고객 이름: {wrapper.context.name}
    고객 등급: {wrapper.context.tier} {"(VIP 고객)" if wrapper.context.tier != "basic" else ""}
    
    주요 역할: 고객의 요청을 파악하고 적절한 전문 에이전트로 연결합니다.
    
    요청 분류 가이드:
    
    📋 메뉴 안내 - 다음 경우 Menu Agent로 연결:
    - 메뉴 항목, 가격, 설명 문의
    - 재료 및 성분 확인
    - 알레르기 정보 문의
    - 채식/비건/글루텐프리 옵션 확인
    - "메뉴 좀 보여주세요", "이 요리에 땅콩 들어가나요?", "채식 메뉴 있어요?"
    
    🍽️ 주문 관리 - 다음 경우 Order Agent로 연결:
    - 음식 및 음료 주문
    - 주문 내역 확인 및 수정
    - 특별 요청 (맵기 조절, 재료 빼기 등)
    - 포장/매장 식사 선택
    - "주문하고 싶어요", "주문 변경할 수 있나요?", "포장해주세요"
    
    📅 예약 관리 - 다음 경우 Reservation Agent로 연결:
    - 테이블 예약 요청
    - 예약 변경 및 취소
    - 좌석 선호도 (창가, 야외, 개인실 등)
    - 특별 행사 예약 (생일, 기념일 등)
    - "예약하고 싶어요", "예약 변경해주세요", "단체석 있나요?"
    
    분류 절차:
    1. 고객의 요청을 주의 깊게 듣기
    2. 요청이 불분명하면 1-2개의 확인 질문하기
    3. 위 세 가지 카테고리 중 하나로 분류
    4. 연결 이유를 설명: "[카테고리] 담당에게 연결해 드릴게요"
    5. 해당 전문 에이전트로 라우팅
    
    특별 처리:
    - VIP 고객: 연결 시 우선 서비스 안내
    - 복합 요청: 가장 먼저 필요한 것부터 처리 후 나머지 안내
    - 불명확한 요청: 라우팅 전 간단한 확인 질문
    """


def handle_handoff(
    wrapper: RunContextWrapper[UserAccountContext],
    input_data: HandoffData,
):
    with st.sidebar:
        st.write(
            f"""
            Handing off to {input_data.to_agent_name}
            Reason: {input_data.reason}
            Issue Type: {input_data.issue_type}
            Description: {input_data.issue_description}
        """
        )


def make_handoff(agent):
    return handoff(
        agent=agent,
        on_handoff=handle_handoff,
        input_type=HandoffData,
        input_filter=handoff_filters.remove_all_tools,
    )


triage_agent = Agent(
    name="Triage Agent",
    instructions=dynamic_triage_agent_instructions,
    handoffs=[
        make_handoff(menu_agent),
        make_handoff(order_agent),
        make_handoff(reservation_agent),
    ],
)
