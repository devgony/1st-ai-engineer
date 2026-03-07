import dotenv

dotenv.load_dotenv()
from openai import OpenAI
import asyncio
import streamlit as st
import base64
from typing import Any, cast

from agents import (
    Agent,
    Runner,
    SQLiteSession,
    WebSearchTool,
    FileSearchTool,
    ImageGenerationTool,
)
from agents.items import TResponseInputItem

# Workaround for openai-agents SDK bug: to_input_item() leaks extra fields from
# Pydantic models with extra='allow', causing 400 errors on session replay.
_VALID_INPUT_FIELDS: dict[str, set[str]] = {
    "image_generation_call": {"id", "result", "status", "type"},
    "web_search_call": {"id", "action", "status", "type"},
    "file_search_call": {"id", "queries", "status", "type", "results"},
}


class CleanSQLiteSession(SQLiteSession):
    async def get_items(self, limit: int | None = None) -> list[TResponseInputItem]:
        items = await super().get_items(limit)
        return [self._strip_output_fields(item) for item in items]

    @staticmethod
    def _strip_output_fields(item: Any) -> TResponseInputItem:
        if not isinstance(item, dict):
            return cast(TResponseInputItem, item)
        item_type = item.get("type")
        allowed = _VALID_INPUT_FIELDS.get(item_type)
        if allowed is None:
            return cast(TResponseInputItem, item)
        return cast(TResponseInputItem, {k: v for k, v in item.items() if k in allowed})


client = OpenAI()
VECTOR_STORE_ID = dotenv.dotenv_values().get(
    "VECTOR_STORE_ID", "life-coach-vector-store"
)

if "agent" not in st.session_state:
    st.session_state["agent"] = Agent(
        name="Life Coach",
        instructions="""
        You are a helpful assistant to encourage users like life coach.

        You have access to the followign tools:
            - Image Generation Tool:
                - If user made goals related to fitness, health, or self-development, use the image generation tool to create motivational images for the user.
                - If user wants to visualize their goals, use the image generation tool to create vision board style images.
            - File Search Tool: 
                - If you use this tool, say: 목표를 확인했어요: {확인된 내용}
                - Use this tool when the user asks a question about facts related to themselves. Or when they ask questions about specific files.
                - Always search any tips according to the user's data in the file search tool, and use the information you find to give personalized advice.
            - Web Search Tool: 
                - Use this when the user asks a questions that isn't in your training data.
                - Use this tool when the users asks about current or future events, when you think you don't know the answer, try searching for it in the web first.
                - Especially when the user asks about motivation, self-development tips, habit formation advice.
                - If User has some concerns, search the trending solution.
        Right after File Search Tool, Show the result and Use Web Search Tool to search for the latest tips and advice on the web, and combine the information from both tools to give the best possible answer to the user.
        """,
        tools=[
            WebSearchTool(),
            FileSearchTool(vector_store_ids=[VECTOR_STORE_ID], max_num_results=3),
            ImageGenerationTool(
                tool_config={
                    "type": "image_generation",
                    "quality": "low",
                    "output_format": "jpeg",
                    "partial_images": 1,
                }
            ),
        ],
    )
agent = st.session_state["agent"]

if "session" not in st.session_state:
    st.session_state["session"] = CleanSQLiteSession(
        "chat-history",
        "life-coach.db",
    )
session = st.session_state["session"]


async def paint_history():
    messages = await session.get_items()

    for message in messages:
        if "role" in message:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.write(message["content"])
                else:
                    if message["type"] == "message":
                        st.write(message["content"][0]["text"].replace("$", "\\$"))
        if "type" in message:
            message_type = message["type"]
            if message_type == "web_search_call":
                with st.chat_message("ai"):
                    st.write("🔍 Searched the web...")
            elif message_type == "file_search_call":
                with st.chat_message("ai"):
                    st.write("🗂️ Searched your files...")
            elif message_type == "image_generation_call":
                image = base64.b64decode(message["result"])
                with st.chat_message("ai"):
                    st.image(image)


asyncio.run(paint_history())


def update_status(status_container, event):

    status_messages = {
        "response.web_search_call.completed": ("✅ Web search completed.", "complete"),
        "response.web_search_call.in_progress": (
            "🔍 Starting web search...",
            "running",
        ),
        "response.web_search_call.searching": (
            "🔍 Web search in progress...",
            "running",
        ),
        "response.file_search_call.completed": (
            "✅ File search completed.",
            "complete",
        ),
        "response.file_search_call.in_progress": (
            "🗂️ Starting file search...",
            "running",
        ),
        "response.file_search_call.searching": (
            "🗂️ File search in progress...",
            "running",
        ),
        "response.image_generation_call.generating": (
            "🎨 Drawing image...",
            "running",
        ),
        "response.image_generation_call.in_progress": (
            "🎨 Drawing image...",
            "running",
        ),
        "response.completed": (" ", "complete"),
    }

    if event in status_messages:
        label, state = status_messages[event]
        status_container.update(label=label, state=state)


async def run_agent(message):
    with st.chat_message("ai"):
        status_container = st.status("⏳", expanded=False)
        text_placeholder = st.empty()
        image_placeholder = st.empty()
        response = ""

        stream = Runner.run_streamed(
            agent,
            message,
            session=session,
        )

        async for event in stream.stream_events():
            if event.type == "raw_response_event":
                update_status(status_container, event.data.type)

                if event.data.type == "response.output_text.delta":
                    response += event.data.delta
                    text_placeholder.write(response.replace("$", "\\$"))
                elif event.data.type == "response.image_generation_call.partial_image":
                    image = base64.b64decode(event.data.partial_image_b64)
                    image_placeholder.image(image)
                elif event.data.type == "response.completed":
                    pass


prompt = st.chat_input(
    "Write a message for your assistant",
    accept_file=True,
    file_type=["txt"],
)

if prompt:
    for file in prompt.files:
        if file.type.startswith("text/"):
            with st.chat_message("ai"):
                with st.status("⏳ Uploading file...") as status:
                    uploaded_file = client.files.create(
                        file=(file.name, file.getvalue()),
                        purpose="user_data",
                    )
                    status.update(label="⏳ Attaching file...")
                    client.vector_stores.files.create(
                        vector_store_id=VECTOR_STORE_ID,
                        file_id=uploaded_file.id,
                    )
                    status.update(label="✅ File uploaded", state="complete")

    if prompt.text:
        with st.chat_message("human"):
            st.write(prompt.text)
        asyncio.run(run_agent(prompt.text))

with st.sidebar:
    reset = st.button("Reset memory")
    if reset:
        asyncio.run(session.clear_session())
    st.write(asyncio.run(session.get_items()))
