from openai import OpenAI

client = OpenAI()


def generate_single_image(visual_description: str) -> str:
    """Returns base64-encoded JPEG string."""
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
    return image.data[0].b64_json
