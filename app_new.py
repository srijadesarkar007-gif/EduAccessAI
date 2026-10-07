import html
import json
import re
import time

import streamlit as st
import streamlit.components.v1 as components

from google import genai
from google.genai import types

from modules.extractor import extract_pdf
from modules.transformer import transform_text
from modules.fidelity import check_fidelity


st.set_page_config(
    page_title="EduAccess AI",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------------------------------------------------------
# PREMIUM UI STYLES
# -----------------------------------------------------------------------------

st.markdown(
    """
    <style>
    :root {
        --ink: #1d2148;
        --muted: #707494;
        --lavender: #6f65f5;
        --lavender-soft: #efedff;
        --blue-soft: #eef4ff;
        --mint-soft: #eaf9f2;
        --peach-soft: #fff2e9;
        --line: #e7e7f2;
        --surface: #ffffff;
        --canvas: #f8f8ff;
    }

    .stApp {
        background: var(--canvas);
    }

    [data-testid="stHeader"] {
        background: rgba(248,248,255,0.88);
    }

    .block-container {
        max-width: 1400px;
        padding-top: 1.5rem;
        padding-bottom: 4rem;
    }

    section[data-testid="stSidebar"] {
        background: #f5f5ff;
        border-right: 1px solid var(--line);
    }

    section[data-testid="stSidebar"] > div {
        padding-top: 1.5rem;
    }

    .brand {
        display:flex;
        align-items:center;
        gap:10px;
        font-weight:800;
        font-size:1.12rem;
        color:var(--ink);
        letter-spacing:-0.02em;
    }

    .brand-mark {
        width:34px;
        height:34px;
        border-radius:11px;
        display:flex;
        align-items:center;
        justify-content:center;
        background:#e8e6ff;
        color:#5f55e8;
        font-size:1.15rem;
        box-shadow:0 8px 24px rgba(102,91,230,.12);
    }

    .sidebar-copy {
        color:var(--muted);
        line-height:1.6;
        font-size:.90rem;
    }

    .hero {
        background:linear-gradient(135deg, #ffffff 0%, #f1efff 58%, #eeeaff 100%);
        border:1px solid #e5e2fb;
        border-radius:30px;
        padding:48px 50px;
        position:relative;
        overflow:hidden;
        box-shadow:0 22px 60px rgba(51,45,128,.08);
    }

    .hero::after {
        content:"";
        position:absolute;
        width:280px;
        height:280px;
        right:-80px;
        top:-90px;
        border-radius:50%;
        background:#ded9ff;
        opacity:.65;
    }

    .eyebrow {
        color:#6c65d8;
        font-weight:800;
        font-size:.78rem;
        letter-spacing:.14em;
        text-transform:uppercase;
        margin-bottom:12px;
    }

    .hero-title {
        color:var(--ink);
        font-size:clamp(2.45rem,5vw,4.3rem);
        font-weight:800;
        letter-spacing:-0.055em;
        line-height:.98;
        margin:0;
        max-width:780px;
    }

    .hero-title span {
        color:#7268ed;
    }

    .hero-subtitle {
        color:#666a89;
        font-size:1.10rem;
        line-height:1.65;
        max-width:650px;
        margin:20px 0 0 0;
    }

    .feature-card {
        border:1px solid var(--line);
        border-radius:24px;
        padding:24px;
        min-height:180px;
        background:var(--surface);
        box-shadow:0 10px 32px rgba(35,34,83,.05);
    }

    .feature-icon {
        width:44px;
        height:44px;
        display:flex;
        align-items:center;
        justify-content:center;
        border-radius:14px;
        font-size:1.25rem;
        margin-bottom:18px;
    }

    .feature-title {
        font-size:1.08rem;
        font-weight:800;
        color:var(--ink);
        margin-bottom:8px;
    }

    .feature-copy {
        color:var(--muted);
        line-height:1.55;
        font-size:.91rem;
    }

    .section-label {
        font-size:1.05rem;
        font-weight:800;
        color:var(--ink);
        margin:26px 0 12px 0;
    }

    .metric-card {
        background:#fff;
        border:1px solid var(--line);
        border-radius:20px;
        padding:18px 20px;
        box-shadow:0 8px 26px rgba(40,40,87,.05);
    }

    .metric-kicker {
        color:var(--muted);
        font-size:.76rem;
        text-transform:uppercase;
        letter-spacing:.08em;
        font-weight:700;
    }

    .metric-value {
        color:var(--ink);
        font-size:1.45rem;
        font-weight:800;
        margin-top:4px;
    }

    .metric-note {
        color:#8b8da5;
        font-size:.78rem;
        margin-top:2px;
    }

    .doc-header {
        background:#fff;
        border:1px solid var(--line);
        border-radius:26px;
        padding:26px 28px;
        box-shadow:0 10px 34px rgba(39,38,87,.05);
    }

    .doc-icon {
        width:50px;
        height:50px;
        border-radius:16px;
        background:#eeeaff;
        color:#655ce9;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.35rem;
    }

    .doc-name {
        color:var(--ink);
        font-size:1.30rem;
        font-weight:800;
        margin-bottom:4px;
    }

    .doc-meta {
        color:var(--muted);
        font-size:.86rem;
    }

    .status-pill {
        display:inline-flex;
        align-items:center;
        gap:6px;
        border-radius:999px;
        padding:7px 11px;
        font-size:.77rem;
        font-weight:700;
        margin-top:10px;
    }

    .pill-purple { background:#efedff; color:#5c54d9; }
    .pill-green { background:#e8f8f0; color:#26775a; }
    .pill-amber { background:#fff2dc; color:#956b24; }

    .content-card {
        background:#fff;
        border:1px solid var(--line);
        border-radius:24px;
        padding:25px 28px;
        margin-bottom:18px;
        box-shadow:0 10px 30px rgba(39,38,87,.04);
    }

    .card-title {
        color:var(--ink);
        font-size:1.12rem;
        font-weight:800;
        margin-bottom:8px;
    }

    .card-copy {
        color:#555a78;
        line-height:1.75;
        font-size:.97rem;
    }

    .key-chip {
        display:inline-block;
        background:#f2f1fb;
        border:1px solid #e6e4f3;
        color:#50536f;
        border-radius:999px;
        padding:7px 11px;
        margin:0 6px 7px 0;
        font-size:.79rem;
        font-weight:650;
    }

    .eq-card {
        background:#fbfbff;
        border:1px solid #e5e5f2;
        border-radius:20px;
        padding:20px;
        margin-bottom:14px;
    }

    .eq-label {
        color:#6c6f8a;
        font-size:.78rem;
        font-weight:700;
        text-transform:uppercase;
        letter-spacing:.08em;
        margin-bottom:12px;
    }

    .eq-meaning {
        color:#5a5e7d;
        font-size:.90rem;
        line-height:1.55;
        margin-top:12px;
    }

    .small-muted {
        color:#8a8da6;
        font-size:.78rem;
    }

    .question-card {
        background:#fff;
        border:1px solid var(--line);
        border-radius:22px;
        padding:22px;
        box-shadow:0 8px 28px rgba(40,40,87,.05);
        margin-bottom:15px;
    }

    .question-number {
        color:#7268ed;
        font-size:.76rem;
        font-weight:800;
        text-transform:uppercase;
        letter-spacing:.08em;
        margin-bottom:8px;
    }

    .question-text {
        color:var(--ink);
        font-size:1.02rem;
        font-weight:750;
        line-height:1.5;
    }

    .option {
        border:1px solid #e5e5f0;
        border-radius:14px;
        padding:11px 13px;
        color:#555a78;
        margin-top:8px;
        background:#fcfcff;
        font-size:.91rem;
    }

    .practice-answer {
        margin-top:12px;
        background:#eaf8f1;
        color:#32735a;
        border-radius:14px;
        padding:12px 14px;
        font-size:.88rem;
        line-height:1.55;
    }

    div[data-testid="stButton"] > button,
    div[data-testid="stFormSubmitButton"] > button {
        border-radius:14px;
        border:1px solid #dedcf3;
        font-weight:750;
        min-height:42px;
    }

    div[data-testid="stButton"] > button[kind="primary"],
    div[data-testid="stFormSubmitButton"] > button[kind="primary"] {
        background:#252957;
        color:white;
        border-color:#252957;
    }

    div[data-testid="stFileUploaderDropzone"] {
        border:1.5px dashed #cbc8eb;
        border-radius:20px;
        background:#fbfaff;
    }

    .footer-note {
        color:#9395aa;
        text-align:center;
        font-size:.78rem;
        margin-top:30px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------


def get_model_candidates(preferred=None):
    candidates = []
    if preferred:
        candidates.append(preferred)
    for model in [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
    ]:
        if model not in candidates:
            candidates.append(model)
    return candidates


def gemini_text(prompt, preferred=None):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)
    last_error = None

    for model_name in get_model_candidates(preferred):
        for attempt in range(2):
            try:
                if model_name == "gemini-3.5-flash-lite":
                    config = types.GenerateContentConfig()
                else:
                    config = types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(
                            thinking_level="medium"
                        )
                    )

                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )

                if not response.text:
                    raise RuntimeError("Gemini returned an empty response.")

                return response.text, model_name

            except Exception as exc:
                last_error = exc
                error_text = str(exc)
                temporary = (
                    "503" in error_text
                    or "UNAVAILABLE" in error_text
                    or "429" in error_text
                    or "RESOURCE_EXHAUSTED" in error_text
                )
                if temporary and attempt == 0:
                    time.sleep(3)
                    continue
                if not temporary:
                    raise
                break

    raise last_error or RuntimeError("No Gemini model was available.")


def gemini_json(prompt, schema, preferred=None):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)
    last_error = None

    for model_name in get_model_candidates(preferred):
        for attempt in range(2):
            try:
                if model_name == "gemini-3.5-flash-lite":
                    config = types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                    )
                else:
                    config = types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                        thinking_config=types.ThinkingConfig(
                            thinking_level="medium"
                        ),
                    )

                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )

                if not response.text:
                    raise RuntimeError("Gemini returned an empty response.")

                return json.loads(response.text), model_name

            except Exception as exc:
                last_error = exc
                error_text = str(exc)
                temporary = (
                    "503" in error_text
                    or "UNAVAILABLE" in error_text
                    or "429" in error_text
                    or "RESOURCE_EXHAUSTED" in error_text
                )
                if temporary and attempt == 0:
                    time.sleep(3)
                    continue
                if not temporary:
                    raise
                break

    raise last_error or RuntimeError("No Gemini model was available.")


def math_clean(latex):
    if not isinstance(latex, str):
        return ""
    value = latex.strip()
    value = re.sub(r"^\\\[(.*)\\\]$", r"\1", value, flags=re.S)
    value = re.sub(r"^\$(.*)\$$", r"\1", value, flags=re.S)
    return value.strip()


def render_key_chips(items):
    clean = [str(x).strip() for x in items if str(x).strip()]
    if not clean:
        st.markdown('<div class="small-muted">No items extracted.</div>', unsafe_allow_html=True)
        return
    st.markdown(
        "".join(f'<span class="key-chip">{html.escape(x)}</span>' for x in clean),
        unsafe_allow_html=True,
    )


def render_svg_diagram(diagram):
    title = str(diagram.get("title", "Technical Diagram"))
    dtype = str(diagram.get("type", "concept_map")).lower()
    elements = [str(x) for x in diagram.get("elements", []) if str(x).strip()]
    relationships = [str(x) for x in diagram.get("relationships", []) if str(x).strip()]

    all_text = " ".join([title] + elements).lower()

    if "op-amp" in all_text or "operational amplifier" in all_text:
        svg = """
        <svg width="100%" height="300" viewBox="0 0 860 300" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
              <path d="M0,0 L0,6 L9,3 z" fill="#665ce8"/>
            </marker>
          </defs>
          <rect x="0" y="0" width="860" height="300" rx="24" fill="#fbfbff"/>
          <text x="34" y="38" font-size="18" font-weight="700" fill="#1d2148">Operational Amplifier — conceptual block diagram</text>
          <polygon points="350,82 350,226 610,154" fill="#efedff" stroke="#6f65f5" stroke-width="3"/>
          <text x="480" y="150" text-anchor="middle" font-size="18" font-weight="700" fill="#1d2148">OP-AMP</text>
          <text x="375" y="119" font-size="17" font-weight="700" fill="#1d2148">+</text>
          <text x="375" y="198" font-size="17" font-weight="700" fill="#1d2148">−</text>
          <line x1="95" y1="115" x2="350" y2="115" stroke="#5a5e7d" stroke-width="3" marker-end="url(#arrow)"/>
          <line x1="95" y1="195" x2="350" y2="195" stroke="#5a5e7d" stroke-width="3" marker-end="url(#arrow)"/>
          <line x1="610" y1="154" x2="765" y2="154" stroke="#5a5e7d" stroke-width="3" marker-end="url(#arrow)"/>
          <text x="66" y="109" font-size="15" font-weight="700" fill="#1d2148">V₁</text>
          <text x="66" y="190" font-size="15" font-weight="700" fill="#1d2148">V₂</text>
          <text x="774" y="149" font-size="15" font-weight="700" fill="#1d2148">Vₒ</text>
          <rect x="56" y="238" width="748" height="34" rx="12" fill="#f1f0fc"/>
          <text x="430" y="260" text-anchor="middle" font-size="13" fill="#5a5e7d">Interpretation: output depends on the differential input between the two terminals.</text>
        </svg>
        """
    elif "thermodynamic" in all_text or "system" in all_text and "heat" in all_text:
        svg = """
        <svg width="100%" height="300" viewBox="0 0 860 300" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <marker id="arrow2" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
              <path d="M0,0 L0,6 L9,3 z" fill="#665ce8"/>
            </marker>
          </defs>
          <rect x="0" y="0" width="860" height="300" rx="24" fill="#fbfbff"/>
          <text x="34" y="38" font-size="18" font-weight="700" fill="#1d2148">Thermodynamic energy exchange</text>
          <rect x="326" y="95" width="210" height="94" rx="18" fill="#efedff" stroke="#6f65f5" stroke-width="3"/>
          <text x="431" y="148" text-anchor="middle" font-size="20" font-weight="800" fill="#1d2148">SYSTEM</text>
          <text x="431" y="172" text-anchor="middle" font-size="13" fill="#686b87">boundary under study</text>
          <line x1="431" y1="68" x2="431" y2="95" stroke="#d16b57" stroke-width="3" marker-end="url(#arrow2)"/>
          <text x="445" y="65" font-size="14" font-weight="700" fill="#a75446">Q · heat</text>
          <line x1="536" y1="142" x2="705" y2="142" stroke="#4b9f7d" stroke-width="3" marker-end="url(#arrow2)"/>
          <text x="582" y="128" font-size="14" font-weight="700" fill="#31745a">W · work</text>
          <rect x="100" y="235" width="660" height="34" rx="12" fill="#f1f0fc"/>
          <text x="430" y="257" text-anchor="middle" font-size="13" fill="#5a5e7d">Heat and work are energy-transfer modes across a system boundary.</text>
        </svg>
        """
    else:
        width = 860
        box_w = 190
        box_h = 72
        gap = 28
        per_row = 3
        rows = max(1, (len(elements) + per_row - 1) // per_row)
        height = 100 + rows * (box_h + gap) + 70
        parts = [
            f'<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
            '<defs><marker id="arr" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#665ce8"/></marker></defs>',
            f'<rect x="0" y="0" width="{width}" height="{height}" rx="24" fill="#fbfbff"/>',
            f'<text x="34" y="38" font-size="18" font-weight="700" fill="#1d2148">{html.escape(title)}</text>'
        ]

        positions = []
        for idx, item in enumerate(elements[:9]):
            row = idx // per_row
            col = idx % per_row
            x = 58 + col * (box_w + gap)
            y = 72 + row * (box_h + gap)
            positions.append((x, y))
            parts.append(
                f'<rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" rx="16" fill="#efedff" stroke="#d8d4ff" stroke-width="2"/>'
            )
            label = html.escape(item[:42])
            parts.append(
                f'<text x="{x + box_w/2}" y="{y + 42}" text-anchor="middle" font-size="13" font-weight="700" fill="#2d3155">{label}</text>'
            )

        # Show a small relationship strip; this avoids pretending that
        # arbitrary natural-language relationships have exact geometry.
        rel_y = 82 + rows * (box_h + gap)
        if relationships:
            parts.append(
                f'<rect x="58" y="{rel_y}" width="744" height="54" rx="14" fill="#f1f0fc"/>'
            )
            rel = " · ".join(relationships[:2])
            parts.append(
                f'<text x="430" y="{rel_y + 32}" text-anchor="middle" font-size="12.5" fill="#5a5e7d">{html.escape(rel[:125])}</text>'
            )
        parts.append('</svg>')
        svg = "".join(parts)

    components.html(svg, height=max(310, int(svg.count("<rect") * 25) + 300), scrolling=False)


def model_badge(result):
    model = result.get("model_used", "Gemini")
    return html.escape(str(model))


def document_stats(text):
    words = len(text.split())
    equations = len(re.findall(r"=", text))
    return words, equations


def render_metric_cards(text, result, fidelity):
    words, equation_hits = document_stats(text)
    score = fidelity.get("score", 0)
    cols = st.columns(4)

    items = [
        ("SOURCE", f"{words:,}", "words extracted"),
        ("EQUATIONS", f"{equation_hits:,}", "source equation markers"),
        ("AI MODEL", model_badge(result), "transformation engine"),
        ("INTEGRITY", f"{score}%", "preliminary heuristic"),
    ]

    for col, (kicker, value, note) in zip(cols, items):
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-kicker">{html.escape(kicker)}</div>
                    <div class="metric-value">{html.escape(value)}</div>
                    <div class="metric-note">{html.escape(note)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def ask_doubt(question, source_text, result):
    preferred = result.get("model_used")
    prompt = f"""
You are EduAccess AI, an advanced STEM tutor.

Answer the student's question using the SOURCE MATERIAL as the primary
reference. Preserve technical meaning and equations. If the source does
not contain enough information, say so rather than inventing facts.
Explain the answer clearly, but keep university-level technical rigor.
Use LaTeX for equations when appropriate.

STUDENT QUESTION:
{question}

SOURCE MATERIAL:
{source_text[:24000]}
"""
    return gemini_text(prompt, preferred=preferred)


def generate_practice(source_text, result):
    preferred = result.get("model_used")
    schema = {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "options": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "answer": {"type": "string"},
                        "explanation": {"type": "string"},
                        "difficulty": {"type": "string"}
                    },
                    "required": [
                        "question",
                        "options",
                        "answer",
                        "explanation",
                        "difficulty"
                    ]
                }
            }
        },
        "required": ["questions"]
    }

    prompt = f"""
You are EduAccess AI's assessment engine.

Create 5 technically accurate MCQs from the supplied STEM material.
Questions must test understanding, not trivia.
Use only source-supported information.
Include a mixture of conceptual and application questions.
Each question must have exactly 4 options and one correct answer.
Do not fabricate facts or equations.

SOURCE MATERIAL:
{source_text[:24000]}
"""

    return gemini_json(prompt, schema, preferred=preferred)


# -----------------------------------------------------------------------------
# SESSION STATE
# -----------------------------------------------------------------------------

for key, default in {
    "processed": False,
    "original_text": "",
    "result": None,
    "fidelity": None,
    "doc_name": "",
    "history": [],
    "practice": None,
    "doubt_answer": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# -----------------------------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div class="brand">
            <div class="brand-mark">✦</div>
            <div>EduAccess <span style="color:#7469ed">AI</span></div>
        </div>
        <div style="height:14px"></div>
        <div class="sidebar-copy">
            AI-assisted STEM learning with technical-fidelity checking,
            OCR support and structured learning outputs.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-label">Your workspace</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="small-muted" style="line-height:1.8">
        01 · Extract & OCR<br>
        02 · Understand & explain<br>
        03 · Render equations<br>
        04 · Visualize concepts<br>
        05 · Verify technical information
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.history:
        st.markdown('<div class="section-label">Recent documents</div>', unsafe_allow_html=True)
        for item in st.session_state.history[-5:][::-1]:
            st.markdown(
                f'<div class="small-muted" style="padding:8px 0;border-bottom:1px solid #e7e7f2">{html.escape(item)}</div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="footer-note">Research prototype · technical fidelity is preliminary</div>', unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# HOME / UPLOAD
# -----------------------------------------------------------------------------

if not st.session_state.processed:

    st.markdown(
        """
        <div class="hero">
            <div class="eyebrow">AI-powered STEM study workspace</div>
            <div class="hero-title">Complex STEM.<br><span>Made Simple.</span></div>
            <div class="hero-subtitle">
                Upload your notes, PDFs or textbook content and turn dense
                STEM material into clear explanations, readable equations,
                visual concepts and practice-ready study material.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    features = [
        ("🧠", "Simplify Document", "Turn complex notes into clearer explanations.", "feature-icon"),
        ("💬", "Ask Doubts", "Ask questions directly against your material.", "feature-icon"),
        ("📝", "Practice Questions", "Generate source-grounded MCQs for revision.", "feature-icon"),
        ("◫", "Smart Visuals", "Build technical diagrams when they improve understanding.", "feature-icon"),
    ]
    colors = ["#eeeaff", "#f0ebff", "#eaf9f2", "#fff2e9"]
    for col, (icon, title, copy, cls), color in zip([c1,c2,c3,c4], features, colors):
        with col:
            st.markdown(
                f"""
                <div class="feature-card">
                    <div class="{cls}" style="background:{color}">{icon}</div>
                    <div class="feature-title">{html.escape(title)}</div>
                    <div class="feature-copy">{html.escape(copy)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown('<div class="section-label">Start studying</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload a PDF containing STEM educational material",
        type=["pdf"],
        label_visibility="visible",
    )

    if uploaded:
        st.markdown(
            f"<div class='small-muted' style='margin-top:4px'>Selected: <b>{html.escape(uploaded.name)}</b></div>",
            unsafe_allow_html=True,
        )

        if st.button("✦  Analyze document", type="primary", use_container_width=True):
            with st.spinner("Extracting text and reading scanned pages…"):
                text = extract_pdf(uploaded)

            if not text.strip():
                st.error("No readable text could be extracted from this document.")
                st.stop()

            st.session_state.original_text = text
            st.session_state.doc_name = uploaded.name

            with st.spinner("Building your advanced STEM learning representation…"):
                result = transform_text(text)

            if result.get("mode") == "error":
                st.error("The AI transformation could not be completed.")
                st.code(result.get("error", "Unknown Gemini error"))
                st.stop()

            with st.spinner("Checking technical information preservation…"):
                fidelity = check_fidelity(text, result)

            st.session_state.result = result
            st.session_state.fidelity = fidelity
            st.session_state.processed = True
            st.session_state.practice = None
            st.session_state.doubt_answer = None

            if uploaded.name not in st.session_state.history:
                st.session_state.history.append(uploaded.name)

            st.rerun()

    st.markdown('<div class="footer-note">EduAccess AI · accessible learning without removing technical meaning</div>', unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# STUDY SPACE
# -----------------------------------------------------------------------------

else:
    result = st.session_state.result
    fidelity = st.session_state.fidelity
    source_text = st.session_state.original_text

    # Header
    st.markdown(
        f"""
        <div class="doc-header">
            <div style="display:flex;align-items:center;gap:16px">
                <div class="doc-icon">▤</div>
                <div style="flex:1">
                    <div class="doc-name">{html.escape(st.session_state.doc_name or 'STEM document')}</div>
                    <div class="doc-meta">AI-analyzed learning workspace · OCR + structured transformation</div>
                    <span class="status-pill pill-purple">✦ {model_badge(result)}</span>
                    <span class="status-pill pill-amber" style="margin-left:6px">◈ preliminary technical review</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
    render_metric_cards(source_text, result, fidelity)
    st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)

    tabs = st.tabs([
        "Simple Explanation",
        "Deep Dive",
        "Equations",
        "Visuals",
        "Practice",
        "Ask Doubts",
    ])

    # -------------------------------------------------------------------------
    # SIMPLE EXPLANATION
    # -------------------------------------------------------------------------
    with tabs[0]:
        left, right = st.columns([1.7, 1], gap="large")

        with left:
            st.markdown(
                '<div class="content-card"><div class="card-title">What is this about?</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="card-copy">{html.escape(str(result.get("explanation", ""))).replace(chr(10), "<br>")}</div></div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                '<div class="content-card"><div class="card-title">Key concepts</div>',
                unsafe_allow_html=True,
            )
            render_key_chips(result.get("key_concepts", []))
            st.markdown('</div>', unsafe_allow_html=True)

        with right:
            st.markdown(
                '<div class="content-card"><div class="card-title">Definition</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="card-copy">{html.escape(str(result.get("definition", "")))}</div></div>',
                unsafe_allow_html=True,
            )

            prereq = result.get("prerequisites", [])
            st.markdown(
                '<div class="content-card"><div class="card-title">Before you learn this</div>',
                unsafe_allow_html=True,
            )
            if prereq:
                for item in prereq:
                    st.markdown(f"- {item}")
            else:
                st.markdown('<div class="small-muted">No specific prerequisites identified.</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # DEEP DIVE
    # -------------------------------------------------------------------------
    with tabs[1]:
        st.markdown(
            f"<div class='content-card'><div class='card-title'>Deep technical explanation</div><div class='card-copy'>{html.escape(str(result.get('deep_explanation', ''))).replace(chr(10), '<br>')}</div></div>",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="card-title">How it works</div>', unsafe_allow_html=True)
        steps = result.get("how_it_works", [])
        if steps:
            for idx, step in enumerate(steps, 1):
                st.markdown(
                    f"""
                    <div class="content-card" style="display:flex;gap:16px;align-items:flex-start">
                        <div style="width:34px;height:34px;min-width:34px;border-radius:12px;background:#efedff;color:#5d54dc;display:flex;align-items:center;justify-content:center;font-weight:800">{idx}</div>
                        <div class="card-copy">{html.escape(str(step))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("No ordered process was identified in the source.")

        mistakes = result.get("common_mistakes", [])
        if mistakes:
            st.markdown('<div class="card-title" style="margin-top:24px">Common mistakes</div>', unsafe_allow_html=True)
            for mistake in mistakes:
                st.markdown(
                    f'<div class="content-card" style="background:#fffaf6"><div class="card-copy">⚠️ {html.escape(str(mistake))}</div></div>',
                    unsafe_allow_html=True,
                )

    # -------------------------------------------------------------------------
    # EQUATIONS
    # -------------------------------------------------------------------------
    with tabs[2]:
        equations = result.get("equations", [])
        if not equations:
            st.info("No structured equations were extracted from this document.")
        else:
            st.markdown('<div class="card-title">Readable mathematics</div>', unsafe_allow_html=True)
            st.markdown('<div class="small-muted">Equations are rendered from AI-generated LaTeX rather than shown as raw text.</div>', unsafe_allow_html=True)

            for idx, eq in enumerate(equations, 1):
                latex = math_clean(eq.get("latex", "")) if isinstance(eq, dict) else str(eq)
                meaning = eq.get("meaning", "") if isinstance(eq, dict) else ""
                variables = eq.get("variables", []) if isinstance(eq, dict) else []

                with st.container(border=True):
                    st.markdown(f"**Equation {idx}**")
                    if latex:
                        st.latex(latex)
                    if meaning:
                        st.markdown(f"**Meaning:** {meaning}")
                    if variables:
                        st.markdown("**Variables**")
                        render_key_chips(variables)

    # -------------------------------------------------------------------------
    # VISUALS
    # -------------------------------------------------------------------------
    with tabs[3]:
        diagram = result.get("diagram", {}) or {}

        if diagram.get("needed"):
            st.markdown(
                f"<div class='content-card'><div class='card-title'>Smart visual: {html.escape(str(diagram.get('title', 'Technical diagram')))}</div><div class='small-muted'>Generated from the structured technical relationships identified in your material.</div></div>",
                unsafe_allow_html=True,
            )
            render_svg_diagram(diagram)

            rels = diagram.get("relationships", [])
            if rels:
                st.markdown('<div class="card-title" style="margin-top:20px">Technical relationships</div>', unsafe_allow_html=True)
                for rel in rels:
                    st.markdown(f"- {rel}")
        else:
            st.markdown(
                '<div class="content-card"><div class="card-title">No diagram required</div><div class="card-copy">The AI did not identify a diagram that would materially improve understanding of this material.</div></div>',
                unsafe_allow_html=True,
            )

    # -------------------------------------------------------------------------
    # PRACTICE
    # -------------------------------------------------------------------------
    with tabs[4]:
        st.markdown(
            '<div class="content-card"><div class="card-title">Practice questions</div><div class="card-copy">Generate source-grounded MCQs from the uploaded material for active recall.</div></div>',
            unsafe_allow_html=True,
        )

        if st.button("✦ Generate 5 practice questions", type="primary"):
            with st.spinner("Building a source-grounded practice set…"):
                try:
                    practice, practice_model = generate_practice(source_text, result)
                    practice["model_used"] = practice_model
                    st.session_state.practice = practice
                except Exception as exc:
                    st.error("The practice set could not be generated.")
                    st.code(str(exc))

        practice = st.session_state.practice
        if practice and practice.get("questions"):
            st.markdown(
                f'<div class="status-pill pill-green">✓ Generated with {html.escape(str(practice.get("model_used", "Gemini")))}</div>',
                unsafe_allow_html=True,
            )

            for idx, q in enumerate(practice["questions"], 1):
                st.markdown(
                    f"""
                    <div class="question-card">
                        <div class="question-number">Question {idx} · {html.escape(str(q.get('difficulty', 'mixed')).title())}</div>
                        <div class="question-text">{html.escape(str(q.get('question', '')))}</div>
                    """,
                    unsafe_allow_html=True,
                )
                for option in q.get("options", []):
                    st.markdown(
                        f'<div class="option">{html.escape(str(option))}</div>',
                        unsafe_allow_html=True,
                    )
                st.markdown(
                    f'<div class="practice-answer"><b>Answer:</b> {html.escape(str(q.get("answer", "")))}<br><br>{html.escape(str(q.get("explanation", "")))}</div></div>',
                    unsafe_allow_html=True,
                )

    # -------------------------------------------------------------------------
    # ASK DOUBTS
    # -------------------------------------------------------------------------
    with tabs[5]:
        st.markdown(
            '<div class="content-card"><div class="card-title">Ask about this document</div><div class="card-copy">Ask a question and EduAccess AI will answer using your uploaded material as the primary context.</div></div>',
            unsafe_allow_html=True,
        )

        question = st.text_area(
            "Your question",
            placeholder="Example: Why is the inverting amplifier gain negative?",
            height=100,
        )

        if st.button("Ask EduAccess AI", type="primary"):
            if not question.strip():
                st.warning("Enter a question first.")
            else:
                with st.spinner("Thinking through the source material…"):
                    try:
                        answer, answer_model = ask_doubt(
                            question,
                            source_text,
                            result,
                        )
                        st.session_state.doubt_answer = {
                            "answer": answer,
                            "model": answer_model,
                        }
                    except Exception as exc:
                        st.error("The question could not be answered right now.")
                        st.code(str(exc))

        answer = st.session_state.doubt_answer
        if answer:
            st.markdown(
                f'<div class="content-card"><div class="card-title">Answer</div><div class="card-copy">{html.escape(str(answer["answer"])).replace(chr(10), "<br>")}</div><div class="small-muted" style="margin-top:15px">Model: {html.escape(str(answer["model"]))}</div></div>',
                unsafe_allow_html=True,
            )

    # -------------------------------------------------------------------------
    # NOTES / TECHNICAL FACTS / SOURCE
    # -------------------------------------------------------------------------
    st.markdown('<div class="section-label">Technical review</div>', unsafe_allow_html=True)

    review_left, review_right = st.columns([1.15, 1], gap="large")

    with review_left:
        st.markdown(
            f"""
            <div class="content-card">
                <div class="card-title">Preliminary technical integrity</div>
                <div style="font-size:2.4rem;font-weight:850;color:#272b55">{fidelity.get('score', 0)}%</div>
                <div class="small-muted">Heuristic indicator only — it flags potential information loss; it is not a scientific correctness proof.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for item in fidelity.get("checks", []):
            icon = "✓" if item.get("status") == "pass" else "!"
            cls = "pill-green" if item.get("status") == "pass" else "pill-amber"
            st.markdown(
                f"""
                <div class="content-card">
                    <span class="status-pill {cls}">{icon} {html.escape(str(item.get('category', 'Review')))}</span>
                    <div class="card-copy" style="margin-top:10px">{html.escape(str(item.get('message', '')))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with review_right:
        facts = result.get("technical_facts", {}) or {}
        st.markdown('<div class="content-card"><div class="card-title">Technical terms</div>', unsafe_allow_html=True)
        render_key_chips(facts.get("terms", []))
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="content-card"><div class="card-title">Relationships</div>', unsafe_allow_html=True)
        for rel in facts.get("relationships", [])[:12]:
            st.markdown(f"- {rel}")
        if not facts.get("relationships"):
            st.markdown('<div class="small-muted">No relationships extracted.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="content-card"><div class="card-title">Worked examples</div>', unsafe_allow_html=True)
        for ex in result.get("worked_examples", [])[:8]:
            st.markdown(f"- {ex}")
        if not result.get("worked_examples"):
            st.markdown('<div class="small-muted">No worked examples were identified in the source.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("View original extracted material"):
        st.text(source_text)

    if st.button("← Process another document"):
        for key in [
            "processed",
            "original_text",
            "result",
            "fidelity",
            "doc_name",
            "practice",
            "doubt_answer",
        ]:
            st.session_state[key] = False if key == "processed" else None if key in {"result", "fidelity", "practice", "doubt_answer"} else ""
        st.rerun()
