---
title: English speaking practice Agent
sub_title: OPIc / TOEIC Speaking picture description practice app
author: henry
options:
  end_slide_shorthand: true
---

# English speaking practice Agent

OPIc / TOEIC Speaking picture description practice app

- LangGraph pipeline + Streamlit UI
- Record voice → Transcribe → Correct → Recommend ideal answer

![image:width:100%](./assets/main.png)

---

# Graph Overview

<!-- column_layout: [1, 2] -->

<!-- column: 0 -->

```mermaid +render
graph TD;
    S([__start__]) --> A[generate_image]
    A --> B[record_voice]
    B --> C[transcribe]
    C --> D[search_references]
    D --> E[correct_syntax]
    E --> F[recommend_ideal_answer]
    F --> G[ask_regenerate]
    G -. yes .-> E
    G -. no .-> END([__end__])
```

<!-- column: 1 -->

**generate_image**: GPT Image generates a daily scene

**record_voice**: pauses graph, user records via Streamlit

**transcribe**: Whisper converts speech to text

- 2x speed-up by modifying WAV sample rate header

**search_references**: Tips and grading criteria by API(Tavily) tool

**correct_syntax**: grammar, vocabulary, structure fixes

**recommend_ideal_answer**: vision model writes ideal answer

**ask_regenerate**: user decides to loop or finish

<!-- reset_layout -->

---

# Key Patterns

- **Prompt Chaining** — sequential node execution
- **Human-in-the-loop** — `interrupt()` for voice input & regeneration
- **Conditional Loop** — `ask_regenerate` routes back to `correct_syntax`
- **Tool Integration** — Tavily web search for scoring rubrics

<!-- pause -->

**State accumulation** via `Annotated[list, operator.add]`

```python
corrections: Annotated[list[str], operator.add]
recommendations: Annotated[list[str], operator.add]
```

---

# Thank You
