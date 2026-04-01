"""Unit tests for education-agent graph nodes and routing functions."""

from unittest.mock import MagicMock, patch

import pytest

from main import (
    State,
    diagnose_level,
    generate_quiz,
    human_feedback,
    plan_agent,
    route_feedback,
    route_plan,
    build_graph,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def base_state() -> State:
    """Minimal state with subject and level populated."""
    return State(
        subject="파이썬 프로그래밍",
        level="기초 문법은 알지만 클래스와 함수형 프로그래밍은 어려워요",
        diagnosis="",
        study_plan="",
        quiz="",
        feedback="",
        messages=[],
    )


@pytest.fixture
def diagnosed_state(base_state: State) -> State:
    """State after diagnosis is complete."""
    return {**base_state, "diagnosis": "학생은 파이썬 기초는 알고 있으나 클래스와 함수형 프로그래밍 심화가 필요합니다."}


@pytest.fixture
def planned_state(diagnosed_state: State) -> State:
    """State after study plan is generated."""
    return {
        **diagnosed_state,
        "study_plan": "1주 학습 계획:\n- 월: 클래스 기초\n- 화: 상속과 다형성\n- 수: 함수형 프로그래밍",
    }


# ---------------------------------------------------------------------------
# diagnose_level
# ---------------------------------------------------------------------------
class TestDiagnoseLevel:
    @patch("main.client")
    def test_returns_diagnosis_string(self, mock_client: MagicMock, base_state: State):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="학생은 중급 수준입니다."))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        result = diagnose_level(base_state)

        assert "diagnosis" in result
        assert result["diagnosis"] == "학생은 중급 수준입니다."

    @patch("main.client")
    def test_passes_subject_and_level_to_llm(self, mock_client: MagicMock, base_state: State):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="진단 결과"))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        diagnose_level(base_state)

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        user_msg = messages[1]["content"]
        assert "파이썬 프로그래밍" in user_msg
        assert "기초 문법" in user_msg

    @patch("main.client")
    def test_uses_system_prompt(self, mock_client: MagicMock, base_state: State):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="진단 결과"))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        diagnose_level(base_state)

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        system_msg = messages[0]["content"]
        assert "education expert" in system_msg.lower()


# ---------------------------------------------------------------------------
# plan_agent
# ---------------------------------------------------------------------------
class TestPlanAgent:
    @patch("main.llm_with_tools")
    def test_first_call_creates_system_and_human_messages(
        self, mock_llm: MagicMock, diagnosed_state: State
    ):
        mock_response = MagicMock()
        mock_response.tool_calls = []
        mock_response.content = "학습 계획입니다."
        mock_llm.invoke.return_value = mock_response

        result = plan_agent(diagnosed_state)

        assert "study_plan" in result
        assert result["study_plan"] == "학습 계획입니다."

    @patch("main.llm_with_tools")
    def test_routes_to_tools_when_tool_calls_present(
        self, mock_llm: MagicMock, diagnosed_state: State
    ):
        mock_response = MagicMock()
        mock_response.tool_calls = [{"name": "web_search", "args": {"query": "test"}}]
        mock_response.content = ""
        mock_llm.invoke.return_value = mock_response

        result = plan_agent(diagnosed_state)

        assert "study_plan" not in result
        assert "messages" in result


# ---------------------------------------------------------------------------
# generate_quiz
# ---------------------------------------------------------------------------
class TestGenerateQuiz:
    @patch("main.client")
    def test_returns_quiz_string(self, mock_client: MagicMock, planned_state: State):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="1. 파이썬에서 클래스란?\na) ...\nb) ..."))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        result = generate_quiz(planned_state)

        assert "quiz" in result
        assert "클래스" in result["quiz"]

    @patch("main.client")
    def test_includes_subject_and_plan_in_prompt(
        self, mock_client: MagicMock, planned_state: State
    ):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="퀴즈 내용"))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        generate_quiz(planned_state)

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        user_msg = messages[1]["content"]
        assert "파이썬 프로그래밍" in user_msg
        assert "학습 계획" in user_msg


# ---------------------------------------------------------------------------
# human_feedback
# ---------------------------------------------------------------------------
class TestHumanFeedback:
    @patch("main.interrupt", return_value="yes")
    def test_returns_feedback_from_interrupt(self, _mock_interrupt: MagicMock, planned_state: State):
        result = human_feedback(planned_state)
        assert result == {"feedback": "yes"}

    @patch("main.interrupt", return_value="no")
    def test_returns_no_feedback(self, _mock_interrupt: MagicMock, planned_state: State):
        result = human_feedback(planned_state)
        assert result == {"feedback": "no"}


# ---------------------------------------------------------------------------
# route_plan
# ---------------------------------------------------------------------------
class TestRoutePlan:
    def test_routes_to_tools_when_tool_calls(self):
        msg = MagicMock()
        msg.tool_calls = [{"name": "web_search"}]
        state: State = {
            "subject": "",
            "level": "",
            "diagnosis": "",
            "study_plan": "",
            "quiz": "",
            "feedback": "",
            "messages": [msg],
        }
        assert route_plan(state) == "tools"

    def test_routes_to_continue_when_no_tool_calls(self):
        msg = MagicMock()
        msg.tool_calls = []
        state: State = {
            "subject": "",
            "level": "",
            "diagnosis": "",
            "study_plan": "",
            "quiz": "",
            "feedback": "",
            "messages": [msg],
        }
        assert route_plan(state) == "continue"

    def test_routes_to_continue_when_no_tool_calls_attr(self):
        msg = MagicMock(spec=[])  # no attributes
        state: State = {
            "subject": "",
            "level": "",
            "diagnosis": "",
            "study_plan": "",
            "quiz": "",
            "feedback": "",
            "messages": [msg],
        }
        assert route_plan(state) == "continue"


# ---------------------------------------------------------------------------
# route_feedback
# ---------------------------------------------------------------------------
class TestRouteFeedback:
    def test_routes_to_end_on_yes(self):
        state: State = {
            "subject": "",
            "level": "",
            "diagnosis": "",
            "study_plan": "",
            "quiz": "",
            "feedback": "yes",
            "messages": [],
        }
        assert route_feedback(state) == "end"

    def test_routes_to_retry_on_no(self):
        state: State = {
            "subject": "",
            "level": "",
            "diagnosis": "",
            "study_plan": "",
            "quiz": "",
            "feedback": "no",
            "messages": [],
        }
        assert route_feedback(state) == "retry"

    def test_routes_to_retry_on_empty(self):
        state: State = {
            "subject": "",
            "level": "",
            "diagnosis": "",
            "study_plan": "",
            "quiz": "",
            "feedback": "",
            "messages": [],
        }
        assert route_feedback(state) == "retry"

    def test_case_insensitive_yes(self):
        state: State = {
            "subject": "",
            "level": "",
            "diagnosis": "",
            "study_plan": "",
            "quiz": "",
            "feedback": "YES",
            "messages": [],
        }
        assert route_feedback(state) == "end"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------
class TestBuildGraph:
    def test_graph_compiles_without_error(self):
        graph = build_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        graph = build_graph()
        node_names = set(graph.get_graph().nodes.keys())
        expected = {"diagnose_level", "plan_agent", "tools", "generate_quiz", "human_feedback"}
        assert expected.issubset(node_names)
