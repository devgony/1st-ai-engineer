import streamlit as st
from main import graph
from langgraph.types import Command
import uuid

st.set_page_config(
    page_title="English Speaking Practice", page_icon="🎤", layout="wide"
)
st.title("🎤 English Speaking Practice")
st.caption("OPIc / TOEIC Speaking style picture description practice")

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
        st.image(
            image_dir,
            caption="Describe this image in English",
            use_container_width=True,
        )

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

    st.subheader("📝 Your Answer")
    st.write(values.get("transcription", ""))

    st.divider()

    corrections = values.get("corrections", [])
    recommendations = values.get("recommendations", [])

    for i in range(len(corrections) - 1, -1, -1):
        version = i + 1
        is_latest = i == len(corrections) - 1
        label = f"Version {version} (Latest)" if is_latest else f"Version {version}"

        with st.expander(label, expanded=is_latest):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**✅ Corrections**")
                st.write(corrections[i])
            with col2:
                st.markdown("**🌟 Ideal Answer**")
                if i < len(recommendations):
                    st.write(recommendations[i])

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔄 New Correction & Ideal Answer", type="secondary"):
            with st.spinner("Generating new correction and ideal answer..."):
                graph.invoke(Command(resume=True), config)
            st.rerun()
    with col_b:
        if st.button("✅ Try Again", type="primary"):
            graph.invoke(Command(resume=False), config)
            reset()
            st.rerun()
