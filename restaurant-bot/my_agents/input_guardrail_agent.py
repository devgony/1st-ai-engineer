from typing import Any

from agents import (
    Agent,
    RunContextWrapper,
    TResponseInputItem,
    input_guardrail,
    Runner,
    GuardrailFunctionOutput,
)
from models import InputGuardRailOutput, UserAccountContext

input_guardrail_agent = Agent(
    name="Input Guardrail Agent",
    instructions="""
    Determine whether the user's message is related to the restaurant context.

    ON-TOPIC (is_off_topic=false):
    - Menu inquiries (dishes, prices, ingredients, allergens, dietary options)
    - Food orders (placing, modifying, canceling orders)
    - Reservations (booking, changing, canceling tables)
    - Complaints and feedback (food quality, service, experience)
    - General restaurant questions (hours, location, parking, dress code)
    - Small talk or greetings at the start of a conversation

    OFF-TOPIC (is_off_topic=true):
    - Questions completely unrelated to restaurants or dining (e.g., math, politics, coding)
    - Inappropriate or abusive language directed at the system
    - Requests for non-restaurant services

    When in doubt, treat the message as on-topic. Complaints about food or service are ALWAYS on-topic.
""",
    output_type=InputGuardRailOutput,
)


@input_guardrail
async def off_topic_guardrail(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[Any],
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    result = await Runner.run(
        input_guardrail_agent,
        input,
        context=wrapper.context,
    )

    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.is_off_topic,
    )
