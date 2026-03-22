import base64
from google.genai import types
from openai import OpenAI
from google.adk.tools.tool_context import ToolContext

client = OpenAI()


async def generate_images(tool_context: ToolContext):
    story_writer_output = tool_context.state.get("story_writer_output", {})
    page_drafts = story_writer_output.get("draft_pages", [])

    total = len(page_drafts)
    tool_context.state["total"] = total
    generated_images = []
    for page_id, draft_page in enumerate(page_drafts):
        tool_context.state["page_id"] = page_id
        visual_description = draft_page.get("visual_description", "")

        filename = f"image_{page_id}.jpeg"

        image = client.images.generate(
            model="gpt-image-1",
            prompt=visual_description,
            n=1,
            quality="low",
            moderation="low",
            output_format="jpeg",
            background="opaque",
            size="1024x1536",
        )

        image_bytes = base64.b64decode(image.data[0].b64_json)

        artifact = types.Part(
            inline_data=types.Blob(
                mime_type="image/jpeg",
                data=image_bytes,
            )
        )

        await tool_context.save_artifact(
            filename=filename,
            artifact=artifact,
        )

        generated_images.append(
            {
                "page_id": page_id,
                "visual_description": visual_description,
                "filename": filename,
            }
        )

    tool_context.state["generated_images"] = generated_images

    return {
        "total_images": len(generated_images),
        "generated_images": generated_images,
        "status": "complete",
    }


async def build_storybook(tool_context: ToolContext):
    story_writer_output = tool_context.state.get("story_writer_output", {})
    page_drafts = story_writer_output.get("draft_pages", [])
    generated_images = tool_context.state.get("generated_images", [])

    images_by_page_id = {
        image_info.get("page_id"): image_info for image_info in generated_images
    }

    pages = []
    for page_id, draft_page in enumerate(page_drafts):
        image_info = images_by_page_id.get(page_id, {})

        pages.append(
            {
                "page_id": page_id + 1,
                "text": draft_page.get("page_text", ""),
                "visual": draft_page.get("visual_description", ""),
                "image": {
                    "filename": image_info.get("filename"),
                    "saved_as_artifact": bool(image_info.get("filename")),
                },
            }
        )

    return {
        "total_pages": len(pages),
        "pages": pages,
        "status": "complete",
    }
