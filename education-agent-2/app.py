import streamlit as st
from main import graph
from langgraph.types import Command
import uuid

st.set_page_config(page_title="English Speaking Practice", page_icon="🎤", layout="wide")
st.title("🎤 English Speaking Practice")
st.caption("TOEIC Speaking / OPIc style picture description practice")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.step = "start"

config = {"configurable": {"thread_id": st.session_state.thread_id}}


def reset():
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.step = "start"


if st.session_state.step == "start":
    st.markdown("Press the button to generate a practice image.")
    if st.button("🖼️ Generate Image", type="primary"):
        with st.spinner("Generating image..."):
            graph.invoke({}, config)
        st.session_state.step = "record"
        st.rerun()

elif st.session_state.step == "record":
    state = graph.get_state(config)
    image_dir = state.values.get("image_dir")

    if image_dir:
        st.image(image_dir, caption="Describe this image in English", use_container_width=True)

    st.divider()
    st.markdown("**Record your description** (up to 60 seconds)")
    audio = st.audio_input("🎙️ Record your answer", sample_rate=16000)

    if audio:
        st.audio(audio)
        audio_bytes = audio.read()

        with st.spinner("Transcribing and analyzing your answer..."):
            graph.invoke(Command(resume=audio_bytes), config)

        st.session_state.step = "result"
        st.rerun()

elif st.session_state.step == "result":
    state = graph.get_state(config)
    values = state.values

    if values.get("image_dir"):
        st.image(values["image_dir"], use_container_width=True)

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📝 Your Answer")
        st.write(values.get("transcription", ""))

    with col2:
        st.subheader("✅ Corrections")
        st.write(values.get("correction", ""))

    st.divider()

    st.subheader("🌟 Ideal Answer")
    st.write(values.get("recommendation", ""))

    st.divider()
    if st.button("🔄 Try Again", type="primary"):
        reset()
        st.rerun()
