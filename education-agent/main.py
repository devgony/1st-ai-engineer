import dotenv

dotenv.load_dotenv()

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt
from langgraph.graph.message import add_messages

from typing import Annotated, Any, TypedDict
from langchain_core.tools import tool
from langchain_core.messages import (
    RemoveMessage,
    SystemMessage,
    HumanMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from openai import OpenAI


# ---------------------------------------------------------------------------
# Client / LLM setup
# ---------------------------------------------------------------------------
client = OpenAI()
LLM_MODEL = "gpt-4o-mini"


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
class State(TypedDict):
    subject: str
    level: str
    diagnosis: str
    study_plan: str
    quiz: str
    feedback: str
    messages: Annotated[list, add_messages]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
@tool
def web_search(query: str) -> str:
    """Search the web for up-to-date learning resources, tutorials, courses, and documentation."""
    response = client.responses.create(
        model=LLM_MODEL,
        tools=[{"type": "web_search_preview"}],
        input=query,
    )
    return response.output_text


tools = [web_search]
tool_node = ToolNode(tools)
llm_with_tools = ChatOpenAI(model=LLM_MODEL).bind_tools(tools)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
DIAGNOSIS_SYSTEM_PROMPT = (
    "You are an education expert. Diagnose the student's current level "
    "based on their subject and self-reported level. Respond in Korean, 2-3 sentences."
)

PLAN_SYSTEM_PROMPT = (
    "You are an education planner. Create a 1-week personalized study plan "
    "based on the diagnosis. Use the web_search tool to find real, up-to-date "
    "learning resources (online courses, tutorials, documentation) and include "
    "them in the plan. Respond in Korean with bullet points."
)

QUIZ_SYSTEM_PROMPT = (
    "You are a quiz maker. Generate 3 multiple-choice questions matching "
    "the study plan difficulty. Respond in Korean."
)


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------
def diagnose_level(state: State) -> dict:
    """Diagnose the student's current level."""
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": DIAGNOSIS_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"과목: {state['subject']}, 자기 평가 수준: {state['level']}",
            },
        ],
    )
    return {"diagnosis": response.choices[0].message.content}


def plan_agent(state: State) -> dict:
    """Generate a personalized study plan (with web search tool support)."""
    msgs = state.get("messages", [])

    if not msgs or not isinstance(msgs[-1], ToolMessage):
        remove = [RemoveMessage(id=m.id) for m in msgs if hasattr(m, "id")]
        init = [
            SystemMessage(content=PLAN_SYSTEM_PROMPT),
            HumanMessage(
                content=f"과목: {state['subject']}\n진단: {state['diagnosis']}"
            ),
        ]
        response = llm_with_tools.invoke(init)
        result: dict = {"messages": remove + init + [response]}
    else:
        response = llm_with_tools.invoke(msgs)
        result = {"messages": [response]}

    if not response.tool_calls:
        result["study_plan"] = response.content
    return result


def generate_quiz(state: State) -> dict:
    """Generate diagnostic quiz questions aligned with the study plan."""
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": QUIZ_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"과목: {state['subject']}\n학습 계획: {state['study_plan']}",
            },
        ],
    )
    return {"quiz": response.choices[0].message.content}


def human_feedback(state: State) -> dict:
    """Interrupt execution to collect user satisfaction feedback."""
    feedback = interrupt("결과물에 만족하시나요? (yes/no)")
    return {"feedback": feedback}


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------
def route_plan(state: State) -> str:
    """Route after plan_agent: execute tools or continue to quiz."""
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    return "continue"


def route_feedback(state: State) -> str:
    """Route after human_feedback: end or retry."""
    if state.get("feedback", "").lower() == "yes":
        return "end"
    return "retry"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------
def build_graph(checkpointer=None):
    """Build and compile the education planner graph."""
    if checkpointer is None:
        checkpointer = MemorySaver()

    graph_builder = StateGraph(State)

    # Nodes
    graph_builder.add_node("diagnose_level", diagnose_level)
    graph_builder.add_node("plan_agent", plan_agent)
    graph_builder.add_node("tools", tool_node)
    graph_builder.add_node("generate_quiz", generate_quiz)
    graph_builder.add_node("human_feedback", human_feedback)

    # Edges
    graph_builder.add_edge(START, "diagnose_level")
    graph_builder.add_edge("diagnose_level", "plan_agent")
    graph_builder.add_conditional_edges(
        "plan_agent",
        route_plan,
        {"tools": "tools", "continue": "generate_quiz"},
    )
    graph_builder.add_edge("tools", "plan_agent")
    graph_builder.add_edge("generate_quiz", "human_feedback")
    graph_builder.add_conditional_edges(
        "human_feedback",
        route_feedback,
        {"end": END, "retry": "plan_agent"},
    )

    return graph_builder.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    graph = build_graph()
    config = RunnableConfig(configurable={"thread_id": "student-1"})

    initial_input: Any = {
        "subject": "파이썬 프로그래밍",
        "level": "기초 문법은 알지만 클래스와 함수형 프로그래밍은 어려워요",
    }
    result = graph.invoke(initial_input, config=config)

    print("=== 수준 진단 ===")
    print(result["diagnosis"])
    print("\n=== 1주 학습 계획 ===")
    print(result["study_plan"])
    print("\n=== 진단 퀴즈 ===")
    print(result["quiz"])

    while True:
        snapshot = graph.get_state(config)
        if not snapshot.next:
            break

        user_input = input("\n결과물에 만족하시나요? (yes/no): ")
        result = graph.invoke(Command(resume=user_input), config=config)

        if user_input.lower() != "yes":
            print("\n=== 수정된 학습 계획 ===")
            print(result["study_plan"])
            print("\n=== 수정된 퀴즈 ===")
            print(result["quiz"])

    print("\n학습 계획이 확정되었습니다!")
