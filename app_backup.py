import streamlit as st
from modules.extractor import extract_pdf
from modules.transformer import transform_text
from modules.fidelity import check_fidelity

st.set_page_config(page_title="EduAccess AI", page_icon="♿", layout="wide")

st.title("♿ EduAccess AI")
st.caption("AI-assisted transformation of STEM educational content with technical-fidelity checking.")

uploaded = st.file_uploader("Upload a STEM PDF", type=["pdf"])

if uploaded:
    if st.button("Process document", type="primary"):
        with st.spinner("Extracting educational content..."):
            text = extract_pdf(uploaded)

        if not text.strip():
            st.error("No readable text was found. Try a text-based PDF for this prototype.")
            st.stop()

        st.session_state["original_text"] = text

        with st.spinner("Creating an accessible representation..."):
            result = transform_text(text)

        st.session_state["result"] = result

        with st.spinner("Checking technical information preservation..."):
            fidelity = check_fidelity(text, result)
        st.session_state["fidelity"] = fidelity

if "result" in st.session_state:
    result = st.session_state["result"]
    fidelity = st.session_state["fidelity"]

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📖 Accessible explanation")
        st.write(result["explanation"])

        st.subheader("📌 Key concepts")
        for item in result["key_concepts"]:
            st.markdown(f"- {item}")

    with col2:
        st.subheader("🧩 Structured learning")
        st.markdown("**Definition**")
        st.write(result["definition"])
        st.markdown("**How it works**")
        st.write(result["how_it_works"])

        st.subheader("🔍 Technical-fidelity report")
        st.metric("Preservation score", f'{fidelity["score"]}%')

        for item in fidelity["checks"]:
            icon = "✅" if item["status"] == "pass" else "⚠️"
            st.write(f'{icon} **{item["category"]}:** {item["message"]}')

    st.divider()
    st.subheader("Original extracted text")
    with st.expander("Show source text"):
        st.text(st.session_state["original_text"])
