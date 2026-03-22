from google.genai import types
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from .tools import build_storybook, generate_images
from google.adk.tools.agent_tool import AgentTool
from pydantic import BaseModel, Field
from typing import List
from .prompt import (
    ILLUSTRATOR_AGENT_DESCRIPTION,
    ILLUSTRATOR_AGENT_INSTRUCTION,
    STORY_BOOK_MAKER_DESCRIPTION,
    STORY_BOOK_MAKER_INSTRUCTION,
    STORY_WRITER_AGENT_DESCRIPTION,
    STORY_WRITER_AGENT_INSTRUCTION,
)
from google.adk.agents import SequentialAgent, ParallelAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse


MODEL = LiteLlm(model="openai/gpt-4o")


class DraftPage(BaseModel):
    page_text: str
    visual_description: str


class StoryWriterOutput(BaseModel):
    draft_pages: List[DraftPage] = Field(
        description="A list of drafts for each page of the storybook, where each draft includes the text for the page and a visual description to guide the illustration process."
    )


story_writer_agent = Agent(
    name="StoryWriterAgent",
    description=STORY_WRITER_AGENT_DESCRIPTION,
    instruction=STORY_WRITER_AGENT_INSTRUCTION,
    model=MODEL,
    output_schema=StoryWriterOutput,
    output_key="story_writer_output",
)

illustrator_agent = ParallelAgent(
    name="IllustratorAgent",
    description=ILLUSTRATOR_AGENT_DESCRIPTION,
    instruction=ILLUSTRATOR_AGENT_INSTRUCTION,
    model=MODEL,
    output_key="illustrator_output",
    tools=[
        generate_images,
    ],
)


def before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
):
    state = callback_context.state
    message = "에러가 발생 했습니다."
    if "generated_images" in state:
        message = "📚 스토리북 조립 중..."
    elif "story_writer_output" in state:
        # message = "🎨 이미지 생성 중..."
        state = callback_context.state
        total = state.get("total")
        page_id = state.get("page_id")
        message = f"🎨 이미지 {page_id + 1}/{total} 생성 중..."
    else:
        message = "📖 스토리 작성 중..."

    return LlmResponse(
        content=types.Content(
            parts=[
                types.Part(text=message),
            ],
            role="model",
        )
    )


story_book_maker = SequentialAgent(
    name="StoryBookMaker",
    model=MODEL,
    description=STORY_BOOK_MAKER_DESCRIPTION,
    instruction=STORY_BOOK_MAKER_INSTRUCTION,
    tools=[
        AgentTool(agent=story_writer_agent),
        AgentTool(agent=illustrator_agent),
        build_storybook,
    ],
    before_model_callback=before_model_callback,
)

root_agent = story_book_maker
