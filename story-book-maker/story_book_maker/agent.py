import asyncio
from google.genai import types
from google.adk.agents import Agent
from google.adk.agents.base_agent import BaseAgent
from google.adk.models.lite_llm import LiteLlm
from .tools import generate_single_image
from pydantic import BaseModel, Field
from typing import AsyncGenerator, Dict, List
from .prompt import (
    STORY_WRITER_AGENT_DESCRIPTION,
    STORY_WRITER_AGENT_INSTRUCTION,
)
from google.adk.agents import SequentialAgent, ParallelAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions

NUM_PAGES = 5


class ProgressSequentialAgent(SequentialAgent):
    progress_messages: Dict[str, str] = {}

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        for sub_agent in self.sub_agents:
            msg = self.progress_messages.get(sub_agent.name)
            if msg:
                yield Event(
                    invocation_id=ctx.invocation_id,
                    author=self.name,
                    content=types.Content(
                        parts=[types.Part(text=msg)],
                        role="model",
                    ),
                )
            async for event in sub_agent.run_async(ctx):
                yield event


class SingleImageAgent(BaseAgent):
    page_id: int = 0

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        story_writer_output = ctx.session.state.get("story_writer_output", {})
        page_drafts = story_writer_output.get("draft_pages", [])
        total = len(page_drafts)

        if self.page_id >= total:
            return

        draft_page = page_drafts[self.page_id]
        visual_description = draft_page.get("visual_description", "")
        filename = f"image_{self.page_id}.jpeg"

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=types.Content(
                parts=[
                    types.Part(text=f"🎨 이미지 {self.page_id + 1}/{total} 생성 중...")
                ],
                role="model",
            ),
        )

        image_b64 = await asyncio.to_thread(generate_single_image, visual_description)

        image_info = {
            "page_id": self.page_id,
            "visual_description": visual_description,
            "filename": filename,
            "b64": image_b64,
        }
        state_key = f"generated_image_{self.page_id}"
        ctx.session.state[state_key] = image_info
        actions = EventActions()
        actions.state_delta[state_key] = image_info

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=types.Content(
                parts=[types.Part(text=f"✅ 이미지 {self.page_id + 1}/{total} 완료")],
                role="model",
            ),
            actions=actions,
        )


class ImageCollectorAgent(BaseAgent):
    """ParallelAgent 완료 후 개별 이미지 state를 generated_images로 취합"""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        generated_images = []
        for i in range(NUM_PAGES):
            image_info = ctx.session.state.get(f"generated_image_{i}")
            if image_info:
                generated_images.append(image_info)

        ctx.session.state["generated_images"] = generated_images
        actions = EventActions()
        actions.state_delta["generated_images"] = generated_images

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=types.Content(
                parts=[
                    types.Part(text=f"✅ {len(generated_images)}개 이미지 생성 완료")
                ],
                role="model",
            ),
            actions=actions,
        )


MODEL = LiteLlm(model="openai/gpt-4o")


class DraftPage(BaseModel):
    page_text: str
    visual_description: str


class StoryWriterOutput(BaseModel):
    title: str = Field(description="The title of the storybook.")
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
    sub_agents=[
        SingleImageAgent(name=f"ImageGenerator_{i}", page_id=i)
        for i in range(NUM_PAGES)
    ],
)

image_collector_agent = ImageCollectorAgent(
    name="ImageCollector",
)

class StoryBookAssemblerAgent(BaseAgent):
    """스토리 텍스트 + 이미지를 하나의 메시지로 조립"""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        story_writer_output = ctx.session.state.get("story_writer_output", {})
        title = story_writer_output.get("title", "동화책")
        page_drafts = story_writer_output.get("draft_pages", [])
        generated_images = ctx.session.state.get("generated_images", [])
        images_by_page_id = {
            img.get("page_id"): img for img in generated_images
        }

        lines = [f"# {title}\n\n---"]

        for page_id, draft_page in enumerate(page_drafts):
            page_text = draft_page.get("page_text", "")
            lines.append(f"\n\n## 페이지 {page_id + 1}\n\n{page_text}")

            image_info = images_by_page_id.get(page_id)
            if image_info and image_info.get("b64"):
                lines.append(
                    f"\n\n![페이지 {page_id + 1} 삽화](data:image/jpeg;base64,{image_info['b64']})"
                )

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=types.Content(
                parts=[types.Part(text="".join(lines))],
                role="model",
            ),
        )


build_story_book_agent = StoryBookAssemblerAgent(
    name="BuildStoryBook",
)

story_book_maker = ProgressSequentialAgent(
    name="StoryBookMaker",
    sub_agents=[
        story_writer_agent,
        illustrator_agent,
        image_collector_agent,
        build_story_book_agent,
    ],
    progress_messages={
        "StoryWriterAgent": "📖 스토리 작성 중...",
        "IllustratorAgent": "🎨 이미지 생성 중...",
        "BuildStoryBook": "📚 스토리북 조립 중...",
    },
)

root_agent = story_book_maker
