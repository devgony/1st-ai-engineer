"""AI-as-judge evaluation for the education-agent outputs.

These tests call the real OpenAI API to evaluate the quality of node outputs.
They are slow and require OPENAI_API_KEY. Run with:

    pytest tests/test_evaluation.py -v -s

Skip in CI with:  pytest -m "not evaluation"
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import dotenv
import pytest

dotenv.load_dotenv()

from openai import OpenAI

from main import State, diagnose_level, generate_quiz

client = OpenAI()

# Mark all tests in this module as evaluation (slow, needs API key)
pytestmark = pytest.mark.evaluation


# ---------------------------------------------------------------------------
# Judge helper
# ---------------------------------------------------------------------------
JUDGE_MODEL = "gpt-4o-mini"


def ask_judge(criteria: str, content: str) -> dict:
    """Ask an LLM judge to evaluate content against criteria.

    Returns: {"score": int (1-5), "reasoning": str}
    """
    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert evaluator. Score the given content on the criteria below.\n"
                    "Return JSON: {\"score\": <1-5>, \"reasoning\": \"<1-2 sentences>\"}\n"
                    "1 = very poor, 2 = poor, 3 = acceptable, 4 = good, 5 = excellent"
                ),
            },
            {
                "role": "user",
                "content": f"## Criteria\n{criteria}\n\n## Content to evaluate\n{content}",
            },
        ],
    )
    content_str = response.choices[0].message.content or "{}"
    return json.loads(content_str)


# ---------------------------------------------------------------------------
# Test inputs
# ---------------------------------------------------------------------------
SAMPLE_INPUTS = [
    {
        "subject": "파이썬 프로그래밍",
        "level": "기초 문법은 알지만 클래스와 함수형 프로그래밍은 어려워요",
    },
    {
        "subject": "영어 회화",
        "level": "간단한 인사와 자기소개는 가능하지만 일상 대화가 어려워요",
    },
    {
        "subject": "데이터 분석",
        "level": "엑셀은 사용할 수 있지만 판다스와 시각화 라이브러리는 처음이에요",
    },
]


# ---------------------------------------------------------------------------
# Diagnosis evaluation
# ---------------------------------------------------------------------------
class TestDiagnosisQuality:
    """Evaluate the quality of diagnose_level outputs using AI-as-judge."""

    @pytest.mark.parametrize("sample", SAMPLE_INPUTS, ids=lambda s: s["subject"])
    def test_diagnosis_relevance(self, sample: dict):
        """Diagnosis should be relevant to the subject and level."""
        state: State = {
            "subject": sample["subject"],
            "level": sample["level"],
            "diagnosis": "",
            "study_plan": "",
            "quiz": "",
            "feedback": "",
            "messages": [],
        }
        result = diagnose_level(state)
        diagnosis = result["diagnosis"]

        verdict = ask_judge(
            criteria=(
                "Is the diagnosis relevant to the student's subject and self-reported level? "
                "Does it accurately assess the student's position and suggest what they need to focus on? "
                "Is it written in Korean?"
            ),
            content=f"Subject: {sample['subject']}\nLevel: {sample['level']}\n\nDiagnosis:\n{diagnosis}",
        )

        print(f"\n[Diagnosis - {sample['subject']}] Score: {verdict['score']}/5")
        print(f"  Reasoning: {verdict['reasoning']}")
        print(f"  Output: {diagnosis[:200]}...")

        assert verdict["score"] >= 3, (
            f"Diagnosis quality too low ({verdict['score']}/5): {verdict['reasoning']}"
        )

    @pytest.mark.parametrize("sample", SAMPLE_INPUTS, ids=lambda s: s["subject"])
    def test_diagnosis_conciseness(self, sample: dict):
        """Diagnosis should be concise (2-3 sentences as instructed)."""
        state: State = {
            "subject": sample["subject"],
            "level": sample["level"],
            "diagnosis": "",
            "study_plan": "",
            "quiz": "",
            "feedback": "",
            "messages": [],
        }
        result = diagnose_level(state)
        diagnosis = result["diagnosis"]

        verdict = ask_judge(
            criteria=(
                "Is the response concise, approximately 2-3 sentences? "
                "It should not be overly verbose or too brief."
            ),
            content=diagnosis,
        )

        print(f"\n[Conciseness - {sample['subject']}] Score: {verdict['score']}/5")
        print(f"  Reasoning: {verdict['reasoning']}")

        assert verdict["score"] >= 3, (
            f"Conciseness too low ({verdict['score']}/5): {verdict['reasoning']}"
        )


# ---------------------------------------------------------------------------
# Quiz evaluation
# ---------------------------------------------------------------------------
class TestQuizQuality:
    """Evaluate the quality of generate_quiz outputs using AI-as-judge."""

    @pytest.mark.parametrize(
        "subject,plan",
        [
            (
                "파이썬 프로그래밍",
                "1주 학습 계획:\n- 월: 클래스 기초 (객체, 속성, 메서드)\n- 화: 상속과 다형성\n- 수: 함수형 프로그래밍 (lambda, map, filter)",
            ),
            (
                "영어 회화",
                "1주 학습 계획:\n- 월: 기본 패턴 50개 암기\n- 화: 레스토랑 상황 대화 연습\n- 수: 쇼핑 상황 대화 연습",
            ),
        ],
        ids=["python", "english"],
    )
    def test_quiz_alignment(self, subject: str, plan: str):
        """Quiz questions should be aligned with the study plan content."""
        state: State = {
            "subject": subject,
            "level": "",
            "diagnosis": "",
            "study_plan": plan,
            "quiz": "",
            "feedback": "",
            "messages": [],
        }
        result = generate_quiz(state)
        quiz = result["quiz"]

        verdict = ask_judge(
            criteria=(
                "Do the quiz questions align with the study plan topics? "
                "Are they multiple-choice with clear options? "
                "Are they at an appropriate difficulty level? "
                "Are they written in Korean?"
            ),
            content=f"Study Plan:\n{plan}\n\nGenerated Quiz:\n{quiz}",
        )

        print(f"\n[Quiz Alignment - {subject}] Score: {verdict['score']}/5")
        print(f"  Reasoning: {verdict['reasoning']}")
        print(f"  Output: {quiz[:300]}...")

        assert verdict["score"] >= 3, (
            f"Quiz alignment too low ({verdict['score']}/5): {verdict['reasoning']}"
        )

    @pytest.mark.parametrize(
        "subject,plan",
        [
            (
                "파이썬 프로그래밍",
                "1주 학습 계획:\n- 월: 클래스 기초\n- 화: 상속과 다형성\n- 수: 함수형 프로그래밍",
            ),
        ],
        ids=["python"],
    )
    def test_quiz_has_three_questions(self, subject: str, plan: str):
        """Quiz should contain exactly 3 questions as instructed."""
        state: State = {
            "subject": subject,
            "level": "",
            "diagnosis": "",
            "study_plan": plan,
            "quiz": "",
            "feedback": "",
            "messages": [],
        }
        result = generate_quiz(state)
        quiz = result["quiz"]

        verdict = ask_judge(
            criteria=(
                "Does the quiz contain exactly 3 questions? "
                "Count the number of distinct questions."
            ),
            content=quiz,
        )

        print(f"\n[Quiz Count - {subject}] Score: {verdict['score']}/5")
        print(f"  Reasoning: {verdict['reasoning']}")

        assert verdict["score"] >= 3, (
            f"Quiz count check failed ({verdict['score']}/5): {verdict['reasoning']}"
        )
