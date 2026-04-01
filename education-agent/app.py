"""Streamlit chat interface for the Education Planner Agent."""

import dotenv

dotenv.load_dotenv()

import streamlit as st
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from main import build_graph

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Education Planner", page_icon="📚")
st.title("📚 학습 계획 도우미")

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
if "graph" not in st.session_state:
    st.session_state.graph = build_graph(checkpointer=MemorySaver())

if "config" not in st.session_state:
    st.session_state.config = {"configurable": {"thread_id": "student-1"}}

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "안녕하세요! 학습 계획 도우미입니다.\n\n학습하고 싶은 **과목**을 알려주세요.",
        }
    ]

if "phase" not in st.session_state:
    st.session_state.phase = "awaiting_subject"

if "subject" not in st.session_state:
    st.session_state.subject = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def add_message(role: str, content: str):
    st.session_state.messages.append({"role": role, "content": content})


def run_graph(subject: str, level: str) -> dict:
    """Invoke the graph — blocks until the interrupt (human_feedback) or END."""
    graph = st.session_state.graph
    config = st.session_state.config
    result = graph.invoke({"subject": subject, "level": level}, config=config)
    return result


def resume_graph(feedback: str) -> dict | None:
    """Resume the graph after the human_feedback interrupt."""
    graph = st.session_state.graph
    config = st.session_state.config
    result = graph.invoke(Command(resume=feedback), config=config)
    return result


def format_result(result: dict) -> str:
    """Format diagnosis + study plan + quiz into a readable message."""
    parts = []
    if result.get("diagnosis"):
        parts.append(f"### 📋 수준 진단\n{result['diagnosis']}")
    if result.get("study_plan"):
        parts.append(f"### 📅 1주 학습 계획\n{result['study_plan']}")
    if result.get("quiz"):
        parts.append(f"### ✏️ 진단 퀴즈\n{result['quiz']}")
    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# Render chat history
# ---------------------------------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ---------------------------------------------------------------------------
# Chat input handler
# ---------------------------------------------------------------------------
if prompt := st.chat_input("메시지를 입력하세요"):
    add_message("user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    phase = st.session_state.phase

    # --- Phase 1: Collect subject ---
    if phase == "awaiting_subject":
        st.session_state.subject = prompt
        st.session_state.phase = "awaiting_level"
        response = f"**{prompt}** 과목이시군요!\n\n현재 본인의 **수준**을 자유롭게 설명해주세요.\n(예: 기초 문법은 알지만 클래스와 함수형 프로그래밍은 어려워요)"
        add_message("assistant", response)
        with st.chat_message("assistant"):
            st.markdown(response)

    # --- Phase 2: Collect level → run graph ---
    elif phase == "awaiting_level":
        with st.chat_message("assistant"):
            with st.spinner("학습 계획을 생성하고 있습니다..."):
                result = run_graph(st.session_state.subject, prompt)
                response = format_result(result)
                st.markdown(response)

                followup = "\n\n---\n\n결과물에 만족하시나요? **yes** 또는 **no**로 답해주세요."
                st.markdown(followup)

        add_message("assistant", response + followup)
        st.session_state.phase = "awaiting_feedback"

    # --- Phase 3: Feedback loop ---
    elif phase == "awaiting_feedback":
        if prompt.strip().lower() == "yes":
            response = "학습 계획이 확정되었습니다! 화이팅! 💪"
            # Resume graph so it terminates cleanly
            resume_graph(prompt.strip().lower())
            add_message("assistant", response)
            with st.chat_message("assistant"):
                st.markdown(response)
            st.session_state.phase = "done"
        else:
            with st.chat_message("assistant"):
                with st.spinner("학습 계획을 수정하고 있습니다..."):
                    result = resume_graph(prompt.strip().lower())
                    if result:
                        response = format_result(result)
                        st.markdown(response)
                        followup = "\n\n---\n\n결과물에 만족하시나요? **yes** 또는 **no**로 답해주세요."
                        st.markdown(followup)
                        add_message("assistant", response + followup)
                    else:
                        fallback = "수정된 결과를 가져오지 못했습니다. 다시 시도해주세요."
                        st.markdown(fallback)
                        add_message("assistant", fallback)

    # --- Phase 4: Done ---
    elif phase == "done":
        response = "이미 학습 계획이 확정되었습니다. 새로운 계획을 세우려면 사이드바에서 **초기화** 버튼을 눌러주세요."
        add_message("assistant", response)
        with st.chat_message("assistant"):
            st.markdown(response)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("설정")
    if st.button("🔄 초기화"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
