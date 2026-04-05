import pytest
from unittest.mock import MagicMock, patch

from langgraph.graph import END

from main import (
    State,
    transcribe,
    search_references,
    correct_syntax,
    recommend_ideal_answer,
    ask_regenerate,
    should_regenerate,
    graph,
)


@pytest.fixture
def base_state() -> State:
    return {
        "image_dir": "",
        "audio_bytes": b"fake-audio-data",
        "transcription": "",
        "search_results": "",
        "corrections": [],
        "recommendations": [],
        "regenerate": False,
    }


@pytest.fixture
def transcribed_state(base_state) -> State:
    return {
        **base_state,
        "transcription": "In this picture, I can see many peoples are sitting in a cafe.",
        "search_results": "TOEIC Speaking tips: use present continuous, describe locations clearly.",
    }


@pytest.fixture
def image_state(transcribed_state, tmp_path) -> State:
    img_path = tmp_path / "test_image.jpg"
    img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    return {
        **transcribed_state,
        "image_dir": str(img_path),
    }


class TestTranscribe:
    @patch("main.OpenAI")
    def test_returns_transcription(self, mock_openai_cls, base_state):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.audio.transcriptions.create.return_value = MagicMock(
            text="In this picture, I can see people sitting in a cafe."
        )

        result = transcribe(base_state)

        assert "transcription" in result
        assert "people sitting" in result["transcription"]

    @patch("main.OpenAI")
    def test_calls_whisper_model(self, mock_openai_cls, base_state):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.audio.transcriptions.create.return_value = MagicMock(text="test")

        transcribe(base_state)

        call_kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
        assert call_kwargs["model"] == "whisper-1"
        assert call_kwargs["language"] == "en"


class TestSearchReferences:
    @patch("main.tavily")
    def test_returns_search_results(self, mock_tavily, base_state):
        base_state["transcription"] = "People are eating at a restaurant."
        mock_tavily.invoke.return_value = [
            {"url": "https://example.com", "content": "TOEIC vocabulary tips"}
        ]

        result = search_references(base_state)

        assert "search_results" in result
        assert "TOEIC" in result["search_results"]

    @patch("main.tavily")
    def test_uses_transcription_in_query(self, mock_tavily, base_state):
        base_state["transcription"] = "Two men are shaking hands in an office."
        mock_tavily.invoke.return_value = []

        search_references(base_state)

        query = mock_tavily.invoke.call_args[0][0]["query"]
        assert "shaking hands" in query


class TestCorrectSyntax:
    @patch("main.llm")
    def test_returns_correction_list(self, mock_llm, transcribed_state):
        mock_llm.invoke.return_value = MagicMock(
            content="1. 'peoples' should be 'people'"
        )

        result = correct_syntax(transcribed_state)

        assert "corrections" in result
        assert isinstance(result["corrections"], list)
        assert len(result["corrections"]) == 1
        assert "people" in result["corrections"][0]

    @patch("main.llm")
    def test_includes_search_results_in_prompt(self, mock_llm, transcribed_state):
        mock_llm.invoke.return_value = MagicMock(content="correction")

        correct_syntax(transcribed_state)

        call_args = mock_llm.invoke.call_args[0][0]
        prompt_content = call_args[0].content
        assert "Reference materials" in prompt_content
        assert transcribed_state["search_results"] in prompt_content


class TestRecommendIdealAnswer:
    @patch("main.llm")
    def test_returns_recommendation_list(self, mock_llm, image_state):
        mock_llm.invoke.return_value = MagicMock(
            content="In this image, we can see a group of people..."
        )

        result = recommend_ideal_answer(image_state)

        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)
        assert len(result["recommendations"]) == 1

    @patch("main.llm")
    def test_sends_image_as_base64(self, mock_llm, image_state):
        mock_llm.invoke.return_value = MagicMock(content="description")

        recommend_ideal_answer(image_state)

        call_args = mock_llm.invoke.call_args[0][0]
        msg_content = call_args[0].content
        assert isinstance(msg_content, list)
        image_part = msg_content[1]
        assert image_part["type"] == "image_url"
        assert "base64" in image_part["image_url"]["url"]


class TestAskRegenerate:
    @patch("main.interrupt", return_value=True)
    def test_returns_regenerate_true(self, _mock, base_state):
        result = ask_regenerate(base_state)
        assert result == {"regenerate": True}

    @patch("main.interrupt", return_value=False)
    def test_returns_regenerate_false(self, _mock, base_state):
        result = ask_regenerate(base_state)
        assert result == {"regenerate": False}


class TestShouldRegenerate:
    def test_routes_to_correct_syntax_when_true(self):
        assert should_regenerate({"regenerate": True}) == "correct_syntax"

    def test_routes_to_end_when_false(self):
        assert should_regenerate({"regenerate": False}) == END

    def test_routes_to_end_when_missing(self):
        assert should_regenerate({}) == END


class TestGraphStructure:
    def test_graph_compiles(self):
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        node_names = set(graph.get_graph().nodes.keys())
        expected = {
            "generate_image",
            "record_voice",
            "transcribe",
            "search_references",
            "correct_syntax",
            "recommend_ideal_answer",
            "ask_regenerate",
        }
        assert expected.issubset(node_names)
