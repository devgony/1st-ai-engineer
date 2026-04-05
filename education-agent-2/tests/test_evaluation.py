import json
import pytest
from openai import OpenAI
from dotenv import load_dotenv

from main import correct_syntax, State

load_dotenv()

JUDGE_MODEL = "gpt-4o-mini"

pytestmark = pytest.mark.evaluation


def ask_judge(criteria: str, content: str) -> dict:
    client = OpenAI()
    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert evaluator for English speaking tests.\n"
                    "Score the given content on the criteria below.\n"
                    'Return JSON: {"score": <1-5>, "reasoning": "<1-2 sentences>"}\n'
                    "1 = very poor, 2 = poor, 3 = acceptable, 4 = good, 5 = excellent"
                ),
            },
            {
                "role": "user",
                "content": f"## Criteria\n{criteria}\n\n## Content to evaluate\n{content}",
            },
        ],
    )
    return json.loads(response.choices[0].message.content or "{}")


SAMPLE_TRANSCRIPTIONS = [
    {
        "id": "grammar_errors",
        "transcription": (
            "In this picture, I can see many peoples are sitting in a cafe. "
            "They is drinking coffee and talking each other. "
            "One man are reading a newspaper."
        ),
        "search_results": "TOEIC Speaking: use correct subject-verb agreement, plural forms.",
    },
    {
        "id": "good_but_simple",
        "transcription": (
            "I can see people in a park. Some people are running. "
            "There is a dog. The weather looks nice. There are trees."
        ),
        "search_results": "OPIc tips: use varied sentence structures, descriptive adjectives.",
    },
]


def _make_state(sample: dict) -> State:
    return {
        "image_dir": "",
        "audio_bytes": b"",
        "transcription": sample["transcription"],
        "search_results": sample["search_results"],
        "corrections": [],
        "recommendations": [],
        "regenerate": False,
    }


class TestCorrectionQuality:
    @pytest.mark.parametrize("sample", SAMPLE_TRANSCRIPTIONS, ids=lambda s: s["id"])
    def test_correction_is_relevant(self, sample):
        result = correct_syntax(_make_state(sample))
        correction = result["corrections"][0]

        verdict = ask_judge(
            criteria=(
                "Does the correction identify real grammar errors in the transcription? "
                "Are vocabulary suggestions natural and appropriate for TOEIC/OPIc? "
                "Are explanations clear and helpful for an English learner?"
            ),
            content=f"Original:\n{sample['transcription']}\n\nCorrection:\n{correction}",
        )

        assert verdict["score"] >= 3, (
            f"Correction quality too low ({verdict['score']}/5): {verdict['reasoning']}"
        )

    GRAMMAR_ERROR_SAMPLES = [s for s in SAMPLE_TRANSCRIPTIONS if s["id"] == "grammar_errors"]

    @pytest.mark.parametrize("sample", GRAMMAR_ERROR_SAMPLES, ids=lambda s: s["id"])
    def test_correction_addresses_grammar(self, sample):
        result = correct_syntax(_make_state(sample))
        correction = result["corrections"][0]

        verdict = ask_judge(
            criteria=(
                "Does the correction specifically address grammar mistakes "
                "(subject-verb agreement, plural forms, preposition usage)? "
                "Score based on how many actual errors are identified and corrected."
            ),
            content=f"Original:\n{sample['transcription']}\n\nCorrection:\n{correction}",
        )

        assert verdict["score"] >= 3, (
            f"Grammar coverage too low ({verdict['score']}/5): {verdict['reasoning']}"
        )

    @pytest.mark.parametrize("sample", SAMPLE_TRANSCRIPTIONS, ids=lambda s: s["id"])
    def test_correction_suggests_improvements(self, sample):
        result = correct_syntax(_make_state(sample))
        correction = result["corrections"][0]

        verdict = ask_judge(
            criteria=(
                "Does the correction provide useful suggestions to improve "
                "the speaker's English? This includes vocabulary enhancement, "
                "sentence variety, and natural expression tips."
            ),
            content=f"Original:\n{sample['transcription']}\n\nCorrection:\n{correction}",
        )

        assert verdict["score"] >= 3, (
            f"Improvement suggestions too low ({verdict['score']}/5): {verdict['reasoning']}"
        )
