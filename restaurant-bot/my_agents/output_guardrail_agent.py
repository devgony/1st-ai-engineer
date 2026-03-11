from agents import (
    Agent,
    output_guardrail,
    Runner,
    RunContextWrapper,
    GuardrailFunctionOutput,
)
from models import RestaurantOutputGuardRailOutput, UserAccountContext


restaurant_output_guardrail_agent = Agent(
    name="Restaurant Output Guardrail",
    instructions="""
    Analyze the restaurant bot's response and check for the following issues:

    1. UNPROFESSIONAL OR IMPOLITE TONE:
       - Rude, dismissive, or sarcastic language
       - Informal slang inappropriate for customer service
       - Blaming the customer or being argumentative
       - Lack of empathy when addressing complaints

    2. INTERNAL INFORMATION EXPOSURE:
       - Food cost, profit margins, or supplier pricing
       - Employee names, schedules, or internal communications
       - Internal policies not meant for customers (e.g., staff disciplinary actions)
       - System details, database info, or technical infrastructure
       - Supplier or vendor names and contract details
       - Internal operational procedures or kitchen workflows

    Set is_unprofessional=true if the response lacks professionalism or politeness.
    Set exposes_internal_info=true if the response reveals any internal business information.
    Provide a brief reason explaining the issue.
    """,
    output_type=RestaurantOutputGuardRailOutput,
)


@output_guardrail
async def restaurant_output_guardrail(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent,
    output: str,
):
    result = await Runner.run(
        restaurant_output_guardrail_agent,
        output,
        context=wrapper.context,
    )

    validation = result.final_output

    triggered = validation.is_unprofessional or validation.exposes_internal_info

    return GuardrailFunctionOutput(
        output_info=validation,
        tripwire_triggered=triggered,
    )
