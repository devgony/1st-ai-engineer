# Education Agent 2 — English Speaking Practice

OPIc / TOEIC Speaking 스타일 사진 묘사 연습 앱. LangGraph 파이프라인 + Streamlit UI.

## Pipeline

```
START
  │
  ▼
generate_image              ← GPT Image (gpt-image-1)
  │
  ▼
record_voice                ← interrupt() — 사용자 음성 입력 대기
  │
  ▼
transcribe                  ← OpenAI Whisper (whisper-1)
  │
  ▼
search_references           ← Tavily Web Search (Tool)
  │
  ▼
correct_syntax              ← GPT-4o-mini + 검색 참고자료
  │
  ▼
recommend_ideal_answer      ← GPT-4o-mini (vision) + 이미지
  │
  ▼
ask_regenerate              ← interrupt() — 재생성 여부 확인
  │
  ├─ yes ──▶ correct_syntax (루프백)
  └─ no ───▶ END
```

| Node | API | Description |
|---|---|---|
| `generate_image` | `gpt-image-1` | TOEIC/OPIc 스타일 일상 장면 이미지 생성 (3-6명, 구체적 장소) |
| `record_voice` | `interrupt()` | 그래프 일시정지 → Streamlit `st.audio_input`으로 녹음 |
| `transcribe` | `whisper-1` | 음성→텍스트 전사 (망설임/필러 포함) |
| `search_references` | `TavilySearch` | 전사 기반 TOEIC/OPIc 채점 기준, 어휘 팁 웹 검색 |
| `correct_syntax` | `gpt-4o-mini` | 문법 교정 + 어휘 제안 + 문장구조 개선 (검색 결과 참조) |
| `recommend_ideal_answer` | `gpt-4o-mini` (vision) | 이미지 기반 45-60초 모범답안 생성 |
| `ask_regenerate` | `interrupt()` | 재생성 여부 확인 → conditional edge로 루프 또는 종료 |

`corrections`/`recommendations`는 `Annotated[list, operator.add]`로 재생성 시 누적 → 버전별 비교 가능.

## Tech Stack

- **LangGraph** — 상태 관리 + human-in-the-loop (`interrupt` / `Command(resume=...)`)
- **LangChain** — LLM 추상화 (`init_chat_model`)
- **OpenAI API** — 이미지 생성, Whisper 전사, GPT-4o-mini
- **Streamlit** — 웹 UI (`st.audio_input`으로 브라우저 녹음)

## Run

```bash
uv sync
streamlit run app.py
```

## 추가 개선 사항

### 필수

- [x] LangGraph를 사용하세요.
- [x] 최소 2개의 작동하는 노드를 구현하세요.
- [ ] Jupyter Notebook에 설계 문서와 코드를 포함하세요.
- [x] 최소 3개의 노드를 구현하세요.
- [x] 최소 1개의 Conditional Edge를 구현하세요. (사용자 입력에 따라 다른 경로)

```text
1.generate_image
2.record_voice
3.transcribe
4.correct_syntax
- Grammar Corrections
- Vocabulary Suggestions for More Natural Expression
- Sentence Structure Improvements
5.recommend_ideal_answer (length: {short, medium, long})
  - compliment the user's answer & estimate the score
6. re-generate correction and ideal answer?
  yes -> 4, 5
  no -> finish, Show Try Again button

```

- [x] 최소 1개의 Tool을 연동하세요. (웹 검색, 파일 검색, 또는 커스텀)
- [ ] 최소 하나의 고급 패턴을 선택하세요

```text
Option A: 멀티 에이전트 아키텍처
전문 에이전트로 분리:
[Supervisor Agent]
       ↓
┌──────┼──────┐
↓      ↓      ↓
[Quiz] [Tutor] [Researcher]

Option B: 워크플로우 아키텍처
프롬프트 체이닝(Prompt Chaining)
병렬 처리(Parallelization)
Orchestrator-Workers

Option C: 테스트
- PyTest를 활용한 노드 테스트
- AI-as-judge 평가
```

- [x] Streamlit UI 완성
- [x] 모든 핵심 기능 작동
- [x] Streamlit Cloud에 배포
- [ ] 에러 발생 시 적절한 안내 표시

### 선택

- [ ] 병렬 실행 (Send API)
- [ ] 메모리 기능
- [ ] 여러 개의 Tool 연동
- [ ] 사용자 친화적인 UI
- [ ] 로딩 상태 표시
- [ ] 사용자를 위한 명확한 안내
- [ ] 프로젝트 설명이 포함된 README.md

