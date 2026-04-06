---
title: English speaking practice Agent
sub_title: OPIc / TOEIC Speaking Picture Description App
author: henry
options:
  end_slide_shorthand: true
---

# English Speaking Practice

OPIc / TOEIC Speaking picture description practice app

- LangGraph pipeline + Streamlit UI
- Record voice → Transcribe → Correct → Recommend ideal answer

---

# Pipeline

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

---

# Nodes

<!-- column_layout: [1, 1] -->

<!-- column: 0 -->

| Node              | API            |
| ----------------- | -------------- |
| generate_image    | `gpt-image-1`  |
| record_voice      | `interrupt()`  |
| transcribe        | `whisper-1`    |
| search_references | `TavilySearch` |

<!-- column: 1 -->

| Node                   | API                    |
| ---------------------- | ---------------------- |
| correct_syntax         | `gpt-4o-mini`          |
| recommend_ideal_answer | `gpt-4o-mini` (vision) |
| ask_regenerate         | `interrupt()`          |

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
