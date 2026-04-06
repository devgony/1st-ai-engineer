---
title: English Speaking Practice
sub_title: OPIc / TOEIC Speaking style picture description app
author: henry
options:
  end_slide_shorthand: true
---

# Education Agent

sub_title: OPIc / TOEIC Speaking style picture description app

<!-- pause -->

- LangGraph 파이프라인 + Streamlit UI
- 음성 녹음 → 전사 → 교정 → 모범답안 생성

---

# Pipeline Overview

```text
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

---

# Node Details (1/2)

<!-- column_layout: [1, 1] -->

<!-- column: 0 -->

### generate_image

- **API**: `gpt-image-1`
- TOEIC/OPIc 스타일 일상 장면 이미지 생성
- 3-6명, 구체적 장소

<!-- pause -->

### record_voice

- **API**: `interrupt()`
- 그래프 일시정지
- Streamlit `st.audio_input`으로 녹음

<!-- column: 1 -->

### transcribe

- **API**: `whisper-1`
- 음성 → 텍스트 전사
- 망설임/필러 포함

<!-- pause -->

### search_references

- **API**: `TavilySearch`
- TOEIC/OPIc 채점 기준 웹 검색
- 어휘 팁 수집

<!-- reset_layout -->

---

# Node Details (2/2)

<!-- column_layout: [1, 1] -->

<!-- column: 0 -->

### correct_syntax

- **API**: `gpt-4o-mini`
- 문법 교정
- 어휘 제안
- 문장구조 개선
- 검색 결과 참조

<!-- column: 1 -->

### recommend_ideal_answer

- **API**: `gpt-4o-mini` (vision)
- 이미지 기반 모범답안 생성
- 45-60초 분량

<!-- pause -->

### ask_regenerate

- **API**: `interrupt()`
- 재생성 여부 확인
- conditional edge로 루프 또는 종료

<!-- reset_layout -->

---

# State Management

`corrections` / `recommendations`는 재생성 시 **누적**됩니다.

```python
corrections: Annotated[list, operator.add]
recommendations: Annotated[list, operator.add]
```

<!-- pause -->

버전별 비교가 가능하여 학습 진행 상황을 추적할 수 있습니다.

---

# Tech Stack

<!-- column_layout: [1, 1] -->

<!-- column: 0 -->

### Core

- **LangGraph**
  - 상태 관리
  - human-in-the-loop
  - `interrupt` / `Command(resume=...)`

<!-- pause -->

- **LangChain**
  - LLM 추상화
  - `init_chat_model`

<!-- column: 1 -->

### API & UI

- **OpenAI API**
  - 이미지 생성
  - Whisper 전사
  - GPT-4o-mini

<!-- pause -->

- **Streamlit**
  - 웹 UI
  - `st.audio_input`으로 브라우저 녹음

<!-- reset_layout -->

---

# How to Run

```bash
uv sync
streamlit run app.py
```

---

# Correct Syntax Node

교정 결과는 3가지 카테고리로 제공됩니다:

<!-- pause -->

**1. Grammar Corrections**

- 문법 오류 교정

<!-- pause -->

**2. Vocabulary Suggestions**

- 더 자연스러운 표현 제안

<!-- pause -->

**3. Sentence Structure Improvements**

- 문장 구조 개선

---

# Architecture Pattern

**Workflow Architecture** 채택

<!-- pause -->

```text
Option B: 워크플로우 아키텍처

- 프롬프트 체이닝 (Prompt Chaining)
- 병렬 처리 (Parallelization)
- Orchestrator-Workers
```

<!-- pause -->

Conditional Edge를 활용한 **루프백 패턴**으로
사용자가 만족할 때까지 재생성 가능

---

# Implementation Checklist

<!-- column_layout: [1, 1] -->

<!-- column: 0 -->

### Done

- [x] LangGraph 사용
- [x] 최소 3개 노드 구현
- [x] Conditional Edge 구현
- [x] Tool 연동 (Tavily)
- [x] 고급 패턴 적용
- [x] Streamlit UI 완성
- [x] 핵심 기능 작동
- [x] Streamlit Cloud 배포

<!-- column: 1 -->

### Future Work

- [ ] 에러 안내 표시
- [ ] 병렬 실행 (Send API)
- [ ] 메모리 기능
- [ ] 여러 Tool 연동
- [ ] 사용자 친화적 UI
- [ ] 로딩 상태 표시
- [ ] 사용자 안내 개선

<!-- reset_layout -->

---

<!-- jump_to_middle -->

# Thank You

**Education Agent 2** — English Speaking Practice

OPIc / TOEIC Speaking 실력을 키워보세요
