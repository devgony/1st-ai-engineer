# Education Agent 2 — English Speaking Practice

TOEIC Speaking / OPIc 스타일 사진 묘사 연습 앱. LangGraph 파이프라인 + Streamlit UI.

## Pipeline

```
generate_image → record_voice → transcribe → correct_syntax → recommend_ideal_answer
```

| Node | Description |
|---|---|
| `generate_image` | GPT Image (`gpt-image-1`)로 일상 장면 이미지 생성 |
| `record_voice` | LangGraph `interrupt`로 일시정지 — 사용자 음성 입력 대기 |
| `transcribe` | OpenAI Whisper (`whisper-1`)로 음성→텍스트 전사 |
| `correct_syntax` | GPT-4o-mini로 문법/어휘/문장구조 교정 |
| `recommend_ideal_answer` | GPT-4o-mini (vision)로 이미지 기반 모범답안 생성 |

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