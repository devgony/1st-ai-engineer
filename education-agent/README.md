# Education Agent: Start Your Demo Day Project

- 오늘의 강의: AI Agents Masterclass: From \#15.0 to r#15.5
- 이번 주부터 데모 데이를 위한 에이전트를 만듭니다

## 테마: 교육 & 학습

- 교육/학습 분야에서 본인의 창의력을 발휘하여 자유롭게 에이전트를 설계해 보세요!
- 아이디어 예시:
  - 언어 학습 파트너
  - 학습 도우미 / 시험 준비 코치
  - 플래시카드 생성기
  - 특정 스킬 학습을 돕는 튜터 (코딩, 요리, 음악 등)
  - 퀴즈 마스터
  - 에세이 코치
- 꼭 위의 예시가 아니어도 괜찮아요. 교육/학습 분야라면 어떤 아이디어든 좋습니다.

## Step 1: 에이전트 설계

- 이름: 에이전트의 이름은?
  - edu-planner-agent
- 목적: 어떤 문제를 해결하나요?
  - 학생들이 효과적으로 학습 계획을 세우고 목표를 달성하도록 돕습니다.
- 핵심 기능: 최소 3가지 주요 기능
  - 학습 목표 설정: 학생들이 달성하고자 하는 학습 목표를 정의하도록 돕습니다.
  - 맞춤형 학습 계획 생성: 학생의 목표, 시간 가용성
  - 선호하는 학습 스타일을 기반으로 개인화된 학습 계획을 만듭니다.
- 그래프 구조: 노드와 엣지 다이어그램 (손그림도 OK)

## Step 2: 기초 구축

- LangGraph로 기본 구조를 구현하세요:
  - State를 정의하세요 (MessagesState 또는 커스텀).
  - 최소 2개의 노드를 구현하세요.
  - 기본 그래프를 연결하세요.

## 요구사항

- LangGraph를 사용하세요.
- 최소 2개의 작동하는 노드를 구현하세요.
- Jupyter Notebook에 설계 문서와 코드를 포함하세요.

---

# Weekend Mission: Education Agent - Core Features

## Education Agent에 핵심 기능을 추가하세요

### 필수

- 최소 3개의 노드를 구현하세요.
- 최소 1개의 Conditional Edge를 구현하세요. (사용자 입력에 따라 다른 경로)
- 최소 1개의 Tool을 연동하세요. (웹 검색, 파일 검색, 또는 커스텀)

### 추가 기능 (선택사항)

- 병렬 실행 (Send API)
- 메모리 기능
- 여러 개의 Tool 연동

---

## Implementation

### Graph Architecture

```
START → diagnose_level → plan_agent ⟷ tools → generate_quiz → human_feedback → END
                              ↑                                      ↓
                              └──────────────── retry ───────────────┘
```

### Nodes

| Node             | Description                                                                                                                                                       |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `diagnose_level` | Diagnoses the student's current level based on subject and self-reported proficiency using `gpt-4o-mini`.                                                         |
| `plan_agent`     | Generates a personalized 1-week study plan. Uses `ChatOpenAI.bind_tools()` so the LLM autonomously decides when to call `web_search` for real learning resources. |
| `tools`          | A `ToolNode` that executes tool calls made by `plan_agent`. Routes back to `plan_agent` after execution.                                                          |
| `generate_quiz`  | Creates 3 multiple-choice diagnostic questions aligned with the study plan.                                                                                       |
| `human_feedback` | Pauses execution via `interrupt()` to collect user satisfaction feedback.                                                                                         |

### Conditional Edges

| From             | Router           | Routing Logic                                                                               |
| ---------------- | ---------------- | ------------------------------------------------------------------------------------------- |
| `plan_agent`     | `route_plan`     | If the LLM made `tool_calls` → `tools` node. Otherwise → `generate_quiz`.                   |
| `human_feedback` | `route_feedback` | If user responds `"yes"` → `END`. Otherwise → `plan_agent` (re-plan with fresh web search). |

### Tool Integration

**`web_search`** — registered as a LangGraph tool via `@tool` decorator + `ToolNode`.

- Internally calls OpenAI Responses API with `web_search_preview` to find up-to-date learning resources.
- The LLM decides whether to invoke it based on the planning context (not hardcoded).
- On retry (user unsatisfied), `RemoveMessage` clears previous conversation so `plan_agent` starts a fresh search.

### Human-in-the-Loop (Interrupt / Resume)

- `MemorySaver` checkpointer persists graph state across pauses.
- `interrupt()` inside `human_feedback` node halts execution and surfaces a prompt.
- `Command(resume=user_input)` resumes the graph with the user's response.
- A `while` loop in the notebook driver handles the interrupt-resume cycle via `graph.get_state()`.

### State

```python
class State(TypedDict):
    subject: str                              # Input: subject to study
    level: str                                # Input: self-reported level
    diagnosis: str                            # Output from diagnose_level
    study_plan: str                           # Output from plan_agent
    quiz: str                                 # Output from generate_quiz
    feedback: str                             # User feedback from interrupt
    messages: Annotated[list, add_messages]   # LLM ⟷ tool conversation history
```

# Education Agent: Advanced Features + Streamlit

- 오늘의 강의: AI Agents Masterclass: From #18.5 to #19.4
- 오늘의 과제: 아래 두 개의 과제를 각 지시사항에 따라 수행합니다.

## - 과제1

- Education Agent에 고급 패턴을 적용하고 Streamlit UI를 추가하세요!
- 최소 하나의 고급 패턴을 선택하세요

### Option A: 멀티 에이전트 아키텍처

- 전문 에이전트로 분리:

```
[Supervisor Agent]
       ↓
┌──────┼──────┐
↓      ↓      ↓
[Quiz] [Tutor] [Researcher]
```

### Option B: 워크플로우 아키텍처

- 프롬프트 체이닝(Prompt Chaining)
- 병렬 처리(Parallelization)
- Orchestrator-Workers

### Option C: 테스트

- PyTest를 활용한 노드 테스트
- AI-as-judge 평가

### 요구사항

- 최소 1개의 고급 패턴을 구현하세요.
- Streamlit UI를 추가하세요 (기본 채팅 인터페이스).
- 에이전트가 처음부터 끝까지 작동해야 합니다.
