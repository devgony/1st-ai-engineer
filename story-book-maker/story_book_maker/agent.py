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

illustrator_agent = Agent(
    name="IllustratorAgent",
    description=ILLUSTRATOR_AGENT_DESCRIPTION,
    instruction=ILLUSTRATOR_AGENT_INSTRUCTION,
    model=MODEL,
    output_key="illustrator_output",
    tools=[
        generate_images,
    ],
)

story_book_maker = Agent(
    name="StoryBookMaker",
    model=MODEL,
    description=STORY_BOOK_MAKER_DESCRIPTION,
    instruction=STORY_BOOK_MAKER_INSTRUCTION,
    tools=[
        AgentTool(agent=story_writer_agent),
        AgentTool(agent=illustrator_agent),
        build_storybook,
    ],
)

root_agent = story_book_maker
