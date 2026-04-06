from openai import OpenAI
from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langchain_tavily import TavilySearch
from langgraph.types import interrupt
from langgraph.checkpoint.memory import InMemorySaver
from typing import Annotated, TypedDict
from dotenv import load_dotenv
import operator
import struct
import base64
import io
import os
from datetime import datetime

load_dotenv()

llm = init_chat_model("openai:gpt-4o-mini")
tavily = TavilySearch(max_results=3)


class State(TypedDict):
    image_dir: str
    audio_bytes: bytes
    transcription: str
    search_results: str
    corrections: Annotated[list[str], operator.add]
    recommendations: Annotated[list[str], operator.add]
    regenerate: bool


def generate_image(state: State):
    client = OpenAI()
    prompt = (
        "Create a realistic, everyday scene image for an English speaking test "
        "(TOEIC Speaking/OPIc-style picture description). The image should include "
        "3-6 people, clear actions, visible objects, and a specific location "
        "(e.g., cafe, office, park, airport, store). Add enough detail for a "
        "45-60 second spoken description: people's positions, clothing, expressions, "
        "interactions, background elements, and at least one notable event or contrast. "
        "Keep it natural, modern, and free of text/watermarks."
    )
    result = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        quality="low",
        moderation="low",
        size="auto",
    )
    image_bytes = base64.b64decode(result.data[0].b64_json)
    current_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    os.makedirs("images", exist_ok=True)
    image_dir = f"images/question_{current_timestamp}.jpg"

    with open(image_dir, "wb") as file:
        file.write(image_bytes)

    return {"image_dir": image_dir}


def record_voice(state: State):
    audio_bytes = interrupt("Please record your voice describing the image.")
    return {"audio_bytes": audio_bytes}


def speed_up_wav(wav_bytes: bytes, factor: int = 2) -> bytes:
    data = bytearray(wav_bytes)
    sample_rate = struct.unpack_from("<I", data, 24)[0]
    byte_rate = struct.unpack_from("<I", data, 28)[0]
    struct.pack_into("<I", data, 24, sample_rate * factor)
    struct.pack_into("<I", data, 28, byte_rate * factor)
    return bytes(data)


def transcribe(state: State):
    client = OpenAI()
    fast_audio = speed_up_wav(state["audio_bytes"])
    audio_bio = io.BytesIO(fast_audio)
    audio_bio.name = "audio.wav"
    transcription = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_bio,
        language="en",
        prompt=(
            "Transcribe the audio for an English speaking test "
            "(TOEIC Speaking/OPIc-style picture description). "
            "Capture all spoken words including hesitations and fillers."
        ),
    )
    return {"transcription": transcription.text}


def search_references(state: State):
    query = (
        "TOEIC Speaking OPIc picture description "
        "scoring rubric vocabulary and expression tips "
        f"for: {state['transcription'][:200]}"
    )
    results = tavily.invoke({"query": query})
    return {"search_results": str(results)}


def correct_syntax(state: State):
    references = state.get("search_results", "")
    response = llm.invoke(
        [
            HumanMessage(
                content=(
                    "You are an English speaking test evaluator.\n"
                    "Analyze the following transcription from a picture description task.\n\n"
                    "Provide:\n"
                    "1. Grammar corrections with explanations\n"
                    "2. Vocabulary suggestions for more natural expression\n"
                    "3. Sentence structure improvements\n\n"
                    f"Transcription:\n{state['transcription']}\n\n"
                    f"Reference materials from web search:\n{references}\n\n"
                    "Use the reference materials to provide more accurate and "
                    "up-to-date suggestions. "
                    "Provide corrections in a clear, structured format."
                )
            )
        ]
    )
    return {"corrections": [response.content]}


def recommend_ideal_answer(state: State):
    with open(state["image_dir"], "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    response = llm.invoke(
        [
            HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": (
                            "You are an English speaking test expert. "
                            "Generate an ideal 45-60 second picture description answer "
                            "for this image. Use natural, fluent English appropriate for "
                            "a TOEIC Speaking or OPIc test. Include descriptions of people, "
                            "actions, setting, and notable details."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        },
                    },
                ]
            )
        ]
    )
    return {"recommendations": [response.content]}


def ask_regenerate(state: State):
    answer = interrupt("Would you like to re-generate the correction and ideal answer?")
    return {"regenerate": answer}


def should_regenerate(state: State):
    if state.get("regenerate"):
        return "yes"
    return "no"


memory = InMemorySaver()

graph_builder = StateGraph(State)

graph_builder.add_node("generate_image", generate_image)
graph_builder.add_node("record_voice", record_voice)
graph_builder.add_node("transcribe", transcribe)
graph_builder.add_node("search_references", search_references)
graph_builder.add_node("correct_syntax", correct_syntax)
graph_builder.add_node("recommend_ideal_answer", recommend_ideal_answer)
graph_builder.add_node("ask_regenerate", ask_regenerate)

graph_builder.add_edge(START, "generate_image")
graph_builder.add_edge("generate_image", "record_voice")
graph_builder.add_edge("record_voice", "transcribe")
graph_builder.add_edge("transcribe", "search_references")
graph_builder.add_edge("search_references", "correct_syntax")
graph_builder.add_edge("correct_syntax", "recommend_ideal_answer")
graph_builder.add_edge("recommend_ideal_answer", "ask_regenerate")
graph_builder.add_conditional_edges(
    "ask_regenerate",
    should_regenerate,
    {"yes": "correct_syntax", "no": END},
)

graph = graph_builder.compile(checkpointer=memory, name="english-education-agent")
