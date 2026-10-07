from __future__ import annotations

import html
import re
import streamlit as st

from modules.gemini_native import (
    analyze_pdf,
    answer_question,
    generate_descriptive,
    generate_mcqs,
    generate_numericals,
    generate_practice,
    prepare_pdf,
)
from modules.pdf_assets import pdf_stats, render_page
from modules.fidelity import preliminary_review

st.set_page_config(page_title="EduAccess AI", page_icon="✦", layout="wide", initial_sidebar_state="expanded")

st.markdown(r"""
<style>
:root{--ink:#202451;--muted:#70769b;--lav:#7567f4;--lav2:#eeeaff;--line:#e9e7f5;--card:#fff;--bg:#f8f8ff;--green:#eaf8f1;--amber:#fff8e8}
.stApp{background:var(--bg)} [data-testid="stSidebar"]{background:#f4f3ff;border-right:1px solid var(--line)}
.block-container{max-width:1280px;padding-top:2rem;padding-bottom:4rem}
.hero{background:linear-gradient(135deg,#fff 0%,#f0edff 100%);border:1px solid #e3e0fa;border-radius:28px;padding:44px 52px;margin-bottom:24px;box-shadow:0 20px 60px rgba(82,71,160,.08)}
.hero-kicker{letter-spacing:.14em;text-transform:uppercase;font-weight:800;color:#6e60ef;font-size:.78rem}.hero h1{margin:.5rem 0 .8rem;color:var(--ink);font-size:3.3rem;line-height:1.03}.hero h1 span{color:#7567f4}.hero p{color:#666d98;font-size:1.05rem;line-height:1.72;max-width:1000px}
.metric{background:#fff;border:1px solid var(--line);border-radius:18px;padding:18px 20px;box-shadow:0 12px 35px rgba(77,72,140,.05)}.metric .label{color:#8589aa;font-size:.74rem;letter-spacing:.1em;text-transform:uppercase;font-weight:800}.metric .value{color:var(--ink);font-size:1.55rem;font-weight:850;margin-top:.2rem}.metric .sub{color:#8b8fab;font-size:.8rem}
.card,.topic-card,.config-card,.eq-card,.figure-card,.question{background:#fff;border:1px solid var(--line);border-radius:20px;box-shadow:0 12px 35px rgba(77,72,140,.05)}
.card{padding:22px}.card-title,.section-title{color:var(--ink);font-weight:850}.card-title{font-size:1.22rem}.section-title{font-size:1.34rem;margin:20px 0 12px}.lead,.card-copy,.note{color:#5f668e;line-height:1.72}.subhead{color:#2e3565;font-weight:850;font-size:1.02rem;margin:18px 0 9px}
.standard-answer{background:#fff;border:1px solid var(--line);border-radius:20px;padding:26px 28px;color:#424a72;line-height:1.9;font-size:1rem;white-space:normal}.standard-answer p{margin:0 0 14px}
.topic-card{padding:20px;margin-bottom:14px}.topic-title{font-size:1.08rem;font-weight:850;color:var(--ink)}.topic-overview{color:#5e6488;line-height:1.72;margin-top:8px}.pill{display:inline-block;background:#f1efff;border:1px solid #dedafb;color:#5148b0;border-radius:999px;padding:7px 11px;margin:4px 5px 4px 0;font-size:.82rem;font-weight:700}.small-pill{display:inline-block;background:#f7f7fd;border:1px solid #e6e6f1;color:#646a8f;border-radius:999px;padding:5px 9px;margin:3px 4px 3px 0;font-size:.77rem}
.config-card{padding:20px;margin-bottom:14px}.config-grid{display:grid;grid-template-columns:1.2fr .8fr;gap:18px}.config-title{font-size:1.08rem;font-weight:850;color:var(--ink)}.config-label{font-size:.75rem;text-transform:uppercase;letter-spacing:.08em;font-weight:800;color:#8b8fab;margin-top:10px}
.eq-card{padding:22px;margin-bottom:14px}.eq-label{font-size:.76rem;text-transform:uppercase;letter-spacing:.08em;color:#8a8eaa;font-weight:800}.eq-meaning{color:#5e6488;line-height:1.65}.eq-card .katex{font-size:1.2em}
.figure-card{padding:14px;margin-bottom:18px}.figure-title{font-size:1.05rem;font-weight:850;color:var(--ink)}.figure-meta{color:#8b8fab;font-size:.8rem;margin:4px 0 12px}
.question{padding:20px;margin-bottom:14px}.q-topic{font-size:.75rem;text-transform:uppercase;letter-spacing:.08em;color:#7369ea;font-weight:800}.q-text{font-size:1.04rem;font-weight:760;color:var(--ink);line-height:1.55;margin-top:8px}.option{border:1px solid #e4e4ef;border-radius:13px;padding:11px 13px;margin-top:8px;background:#fcfcff;color:#505673}.answer{background:var(--green);border-radius:15px;padding:13px 15px;color:#2e7257;line-height:1.62}.standard-university-answer{background:#fbfbff;border-left:4px solid #7567f4;border-radius:12px;padding:16px 18px;color:#4d547c;line-height:1.78;white-space:pre-wrap}.given{background:#fbf9ff;border:1px solid #e6e3f6;border-radius:14px;padding:12px 15px}.warning-box{background:var(--amber);border:1px solid #f0dfab;border-radius:15px;padding:14px;color:#7a632a}
.footer{color:#9699ad;text-align:center;font-size:.78rem;margin-top:30px}.status{padding:8px 11px;border-radius:999px;display:inline-block;font-size:.78rem;font-weight:750}.status-purple{background:#efedff;color:#5a50bf}.status-green{background:#eaf8f1;color:#317255}.status-amber{background:#fff4d9;color:#7b6123}
</style>
""", unsafe_allow_html=True)


def init_state():
    defaults = {
        "filename": None,
        "pdf_bytes": None,
        "file_obj": None,
        "analysis": None,
        "model": None,
        "practice": None,
        "practice_model": None,
        "mcqs": None,
        "numericals": None,
        "descriptive": None,
        "qa": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def metric(label, value, sub):
    st.markdown(f'<div class="metric"><div class="label">{html.escape(str(label))}</div><div class="value">{html.escape(str(value))}</div><div class="sub">{html.escape(str(sub))}</div></div>', unsafe_allow_html=True)


def clean_latex(value: str) -> str:
    s = str(value or "").strip()
    s = s.replace("```latex", "").replace("```", "").strip()
    s = s.replace("\\[", "").replace("\\]", "").replace("\\(", "").replace("\\)", "")
    s = s.replace("\\left", "").replace("\\right", "")
    s = s.replace("\\dfrac", "\\frac")
    s = s.replace("\\quad", " ").replace("\\qquad", " ")
    s = re.sub(r"\\text\{([^{}]*)\}", r"\\mathrm{\1}", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def render_formula(latex: str, fallback: str = ""):
    cleaned = clean_latex(latex)
    bad_tokens = ["\\begin", "\\end", "\\texttt", "\\mathrm{\n", "array", "aligned"]
    suspicious = (
        not cleaned
        or len(cleaned) > 280
        or cleaned.count("{") != cleaned.count("}")
        or any(tok.lower() in cleaned.lower() for tok in bad_tokens)
        or " " in cleaned and len(cleaned.split()) > 28
    )
    if suspicious:
        st.markdown(f"**Formula:** {html.escape(fallback or cleaned or 'Not safely renderable from the source.')}" )
        return
    try:
        st.latex(cleaned)
    except Exception:
        st.markdown(f"**Formula:** {html.escape(fallback or cleaned)}")


def render_equation_object(eq: dict):
    st.markdown('<div class="eq-card">', unsafe_allow_html=True)
    page = f" · Page {eq.get('page')}" if eq.get("page") else ""
    st.markdown(f'<div class="eq-label">Equation{html.escape(page)}</div>', unsafe_allow_html=True)
    render_formula(eq.get("latex", ""), eq.get("meaning", ""))
    if eq.get("meaning"):
        st.markdown(f'<div class="eq-meaning"><b>Interpretation:</b> {html.escape(str(eq["meaning"]))}</div>', unsafe_allow_html=True)
    if eq.get("variables"):
        st.markdown("**Variables / symbols**")
        for x in eq["variables"]:
            st.write("•", x)
    st.markdown('</div>', unsafe_allow_html=True)


def home():
    st.markdown('<div class="hero"><div class="hero-kicker">AI-powered university STEM study workspace</div><h1>Complex STEM.<br><span>Made Precise.</span></h1><p>Read the original PDF with native document vision, then build university-level explanations, standard topic notes, readable equations, source-figure references, and exam-ready practice.</p></div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    cards = [
        ("🧠", "Core Explanation", "Structured like an undergraduate lecture note: principle, mathematics, operation, practical behavior and applications."),
        ("🔬", "Deep Dive", "Detailed reasoning, derivations, assumptions, limitations and engineering interpretation."),
        ("📝", "Exam Practice", "Standard-topic MCQs, numericals and descriptive university questions."),
        ("◫", "Source Visuals", "Actual figures and page references from the uploaded PDF."),
    ]
    for col, (icon, title, desc) in zip((c1, c2, c3, c4), cards):
        with col:
            st.markdown(f'<div class="card" style="min-height:210px"><div style="font-size:1.8rem">{icon}</div><div class="card-title">{html.escape(title)}</div><p>{html.escape(desc)}</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Start studying</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload a STEM PDF", type=["pdf"], label_visibility="collapsed")
    if uploaded is not None:
        if st.session_state.get("filename") != uploaded.name:
            st.session_state.clear()
            init_state()
            st.session_state["filename"] = uploaded.name
            st.session_state["pdf_bytes"] = uploaded.getvalue()
            with st.status("Analyzing the original PDF…", expanded=True) as status:
                st.write("Uploading the PDF to the native document pipeline…")
                file_obj = prepare_pdf(st.session_state["pdf_bytes"])
                st.session_state["file_obj"] = file_obj
                st.write("Reading standard topics, equations, configurations and figures…")
                analysis, model, _ = analyze_pdf(file_obj)
                st.session_state["analysis"] = analysis.model_dump()
                st.session_state["model"] = model
                status.update(label="University-level study workspace ready", state="complete")
            st.rerun()


def render_topic_section(topic: dict, idx: int):
    st.markdown('<div class="topic-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="topic-title">{idx}. {html.escape(str(topic.get("title", "Topic")))}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="topic-overview">{html.escape(str(topic.get("overview", "")))}</div>', unsafe_allow_html=True)
    if topic.get("key_concepts"):
        st.markdown('<div class="config-label">Key concepts</div>', unsafe_allow_html=True)
        for x in topic["key_concepts"]:
            st.markdown(f'<span class="small-pill">{html.escape(str(x))}</span>', unsafe_allow_html=True)
    if topic.get("key_equations"):
        st.markdown('<div class="config-label">Key equations / results</div>', unsafe_allow_html=True)
        for x in topic["key_equations"]:
            st.markdown(f'<div class="card-copy">• {html.escape(str(x))}</div>', unsafe_allow_html=True)
    if topic.get("standard_results"):
        st.markdown('<div class="config-label">Standard results / conditions</div>', unsafe_allow_html=True)
        for x in topic["standard_results"]:
            st.write("•", x)
    if topic.get("exam_relevance"):
        st.markdown(f'<div class="warning-box"><b>Exam focus:</b> {html.escape(str(topic["exam_relevance"]))}</div>', unsafe_allow_html=True)
    if topic.get("pages"):
        st.caption("Source pages: " + ", ".join(map(str, topic["pages"])))
    st.markdown('</div>', unsafe_allow_html=True)


def render_configuration(cfg: dict, idx: int):
    st.markdown('<div class="config-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="config-title">{idx}. {html.escape(str(cfg.get("title", "Configuration")))}</div>', unsafe_allow_html=True)
    left, right = st.columns([1.15, .85])
    with left:
        st.markdown(f'<div class="lead">{html.escape(str(cfg.get("description", "")))}</div>', unsafe_allow_html=True)
        if cfg.get("purpose"):
            st.markdown(f'<div class="config-label">Purpose</div><div class="lead">{html.escape(str(cfg["purpose"]))}</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="config-label">Primary equation</div>', unsafe_allow_html=True)
        render_formula(cfg.get("equation_latex", ""), "Equation unavailable for safe rendering.")
        if cfg.get("conditions"):
            st.markdown('<div class="config-label">Conditions / assumptions</div>', unsafe_allow_html=True)
            for x in cfg["conditions"]: st.write("•", x)
        if cfg.get("practical_notes"):
            st.markdown('<div class="config-label">Practical notes</div>', unsafe_allow_html=True)
            for x in cfg["practical_notes"]: st.write("•", x)
    if cfg.get("pages"):
        st.caption("Source pages: " + ", ".join(map(str, cfg["pages"])))
    st.markdown('</div>', unsafe_allow_html=True)


def render_explanation_sections(sections: list[dict]):
    for idx, sec in enumerate(sections, 1):
        st.markdown(f'<div class="section-title" style="font-size:1.15rem">{idx}. {html.escape(str(sec.get("title", "Section")))}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="standard-answer">{html.escape(str(sec.get("content", ""))).replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
        for eq in sec.get("equations", []):
            render_equation_object(eq)
        if sec.get("key_points"):
            for x in sec["key_points"]:
                st.write("•", x)


def practice_ui(analysis):
    st.markdown('<div class="section-title">University examination practice</div>', unsafe_allow_html=True)
    st.write("The set is generated from the verified academic analysis already created from the original PDF. Each section is independent and has a bounded model timeout with fallbacks.")
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        if st.button("✦ Generate full set", type="primary"):
            with st.spinner("Building standard MCQs, numericals and descriptive answers…"):
                try:
                    p, model, _ = generate_practice(st.session_state["file_obj"], analysis=analysis)
                    st.session_state["practice"] = p.model_dump()
                    st.session_state["practice_model"] = model
                except Exception as exc:
                    st.error(f"Full practice generation failed: {exc}")
    with b2:
        if st.button("Generate MCQs"):
            with st.spinner("Generating MCQs…"):
                try:
                    out, model, _ = generate_mcqs(st.session_state["file_obj"], analysis)
                    st.session_state["mcqs"] = out.model_dump(); st.session_state["practice_model"] = model
                except Exception as exc:
                    st.error(f"MCQ generation failed: {exc}")
    with b3:
        if st.button("Generate numericals"):
            with st.spinner("Generating exam numericals…"):
                try:
                    out, model, _ = generate_numericals(st.session_state["file_obj"], analysis)
                    st.session_state["numericals"] = out.model_dump(); st.session_state["practice_model"] = model
                except Exception as exc:
                    st.error(f"Numerical generation failed: {exc}")
    with b4:
        if st.button("Generate descriptive"):
            with st.spinner("Generating university theory questions…"):
                try:
                    out, model, _ = generate_descriptive(st.session_state["file_obj"], analysis)
                    st.session_state["descriptive"] = out.model_dump(); st.session_state["practice_model"] = model
                except Exception as exc:
                    st.error(f"Descriptive generation failed: {exc}")

    p = st.session_state.get("practice")
    if p:
        st.markdown(f'<span class="status status-green">✓ Full set generated · {html.escape(str(st.session_state.get("practice_model", "Gemini")))}</span>', unsafe_allow_html=True)
        mcqs, nums, desc = p.get("mcqs", []), p.get("numericals", []), p.get("descriptive", [])
        topics = p.get("standard_topics", [])
        blueprint = p.get("exam_blueprint", [])
    else:
        mcqs = (st.session_state.get("mcqs") or {}).get("questions", [])
        nums = (st.session_state.get("numericals") or {}).get("questions", [])
        desc = (st.session_state.get("descriptive") or {}).get("questions", [])
        topics = list(dict.fromkeys(
            (st.session_state.get("mcqs") or {}).get("standard_topics", [])
            + (st.session_state.get("numericals") or {}).get("standard_topics", [])
            + (st.session_state.get("descriptive") or {}).get("standard_topics", [])
        ))
        blueprint = []
    if topics:
        st.markdown('<div class="section-title">Standard topics covered</div>', unsafe_allow_html=True)
        for t in topics: st.markdown(f'<span class="pill">{html.escape(str(t))}</span>', unsafe_allow_html=True)
    if blueprint:
        st.markdown('<div class="section-title">Exam blueprint</div>', unsafe_allow_html=True)
        for x in blueprint: st.write("•", x)
    ptabs = st.tabs([f"MCQs · {len(mcqs)}", f"Numericals · {len(nums)}", f"Descriptive · {len(desc)}"])
    with ptabs[0]:
        if not mcqs: st.info("Generate the MCQ section to begin.")
        for i, q in enumerate(mcqs, 1):
            st.markdown('<div class="question">', unsafe_allow_html=True)
            st.markdown(f'<div class="q-topic">{html.escape(str(q.get("topic", "Standard topic")))} · {html.escape(str(q.get("difficulty", "medium")).title())}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="q-text">{i}. {html.escape(str(q.get("question", "")))}</div>', unsafe_allow_html=True)
            for j, opt in enumerate(q.get("options", [])):
                st.markdown(f'<div class="option"><b>{chr(65+j)}.</b> {html.escape(str(opt))}</div>', unsafe_allow_html=True)
            with st.expander("Show answer & rationale"):
                idx = q.get("answer_index", 0); opts = q.get("options", [])
                if 0 <= idx < len(opts):
                    st.markdown(f'<div class="answer"><b>Correct answer:</b> {chr(65+idx)} — {html.escape(str(opts[idx]))}<br><br>{html.escape(str(q.get("explanation", "")))}</div>', unsafe_allow_html=True)
                if q.get("page"): st.caption(f"Source page: {q['page']}")
            st.markdown('</div>', unsafe_allow_html=True)
    with ptabs[1]:
        if not nums: st.info("Generate the numerical section to begin.")
        for i, q in enumerate(nums, 1):
            st.markdown(f"### {i}. {q.get('question','')}")
            st.caption(f"{q.get('topic','')} · {q.get('difficulty','medium').title()} · {q.get('marks',5)} marks")
            with st.expander("Given / Find", expanded=True):
                for x in q.get("given", []): st.write("•", x)
                for x in q.get("find", []): st.write("**Find:**", x)
            with st.expander("Show standard solution"):
                st.markdown("**Formula**")
                render_formula(q.get("formula_latex", ""), q.get("formula_text", ""))
                st.markdown("**Step-by-step calculation**")
                for n, step in enumerate(q.get("solution_steps", []), 1): st.write(f"{n}. {step}")
                if q.get("unit_check"): st.markdown(f'<div class="answer"><b>Unit check:</b> {html.escape(str(q["unit_check"]))}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="answer"><b>Final answer:</b> {html.escape(str(q.get("final_answer", "")))}</div>', unsafe_allow_html=True)
                if q.get("page"): st.caption(f"Source page: {q['page']}")
    with ptabs[2]:
        if not desc: st.info("Generate the descriptive section to begin.")
        for i, q in enumerate(desc, 1):
            st.markdown(f"### {i}. {q.get('question','')}")
            st.caption(f"{q.get('topic','')} · {q.get('difficulty','medium').title()} · {q.get('marks',5)} marks")
            with st.expander("Show model university answer"):
                st.markdown("**Key points expected**")
                for x in q.get("key_points", []): st.write("•", x)
                st.markdown("**Model answer**")
                st.markdown(f'<div class="standard-university-answer">{html.escape(str(q.get("model_answer", ""))).replace(chr(10),"<br>")}</div>', unsafe_allow_html=True)
                if q.get("page"): st.caption(f"Source page: {q['page']}")


def workspace():
    analysis = st.session_state.get("analysis")
    if not analysis:
        return home()
    pdf_bytes = st.session_state["pdf_bytes"]
    stats = pdf_stats(pdf_bytes)
    figures = analysis.get("figures", [])
    equations = analysis.get("equations", [])
    st.markdown(f'<div class="section-title">{html.escape(analysis.get("title", st.session_state.get("filename","Document")))}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="lead">{html.escape(analysis.get("subject", "STEM topic"))}</div>', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    with m1: metric("Source", f"{stats['pages']}", "pages")
    with m2: metric("Equations", len(equations), "structured formulas")
    with m3: metric("Source figures", len(figures), "identified in PDF")
    with m4: metric("AI engine", st.session_state.get("model", "Gemini"), "native PDF analysis")
    tabs = st.tabs(["Core Explanation", "Deep Dive", "Equations", "Visuals", "Practice", "Ask Doubts", "Verify"])

    with tabs[0]:
        st.markdown('<div class="section-title">Formal definition</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="standard-answer">{html.escape(str(analysis.get("definition", ""))).replace(chr(10),"<br>")}</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">University-level core treatment</div>', unsafe_allow_html=True)
        render_explanation_sections(analysis.get("core_sections", []))
        st.markdown('<div class="section-title">Standard configurations / variants</div>', unsafe_allow_html=True)
        for i, cfg in enumerate(analysis.get("standard_configurations", []), 1): render_configuration(cfg, i)
        st.markdown('<div class="section-title">Learning objectives</div>', unsafe_allow_html=True)
        for x in analysis.get("learning_objectives", []): st.write("•", x)
        st.markdown('<div class="section-title">Core principles</div>', unsafe_allow_html=True)
        for x in analysis.get("core_principles", []): st.write("•", x)

    with tabs[1]:
        st.markdown('<div class="section-title">Deep technical treatment</div>', unsafe_allow_html=True)
        render_explanation_sections(analysis.get("deep_sections", []))
        for title, key in [("Derivations / reasoning", "derivations"), ("Applications", "applications"), ("Assumptions", "assumptions"), ("Limitations / practical behavior", "limitations"), ("Exam focus", "exam_focus"), ("Common mistakes", "common_mistakes")]:
            vals = analysis.get(key, [])
            if vals:
                st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
                for x in vals: st.write("•", x)
        st.markdown('<div class="section-title">Detailed study outline</div>', unsafe_allow_html=True)
        for i, topic in enumerate(analysis.get("chapter_outline", []), 1): render_topic_section(topic, i)

    with tabs[2]:
        st.markdown('<div class="section-title">Readable mathematics</div>', unsafe_allow_html=True)
        st.markdown('<div class="note">Equations are rendered separately from explanatory prose. When a source equation cannot be safely reconstructed, the app falls back to a readable text representation instead of displaying broken LaTeX.</div>', unsafe_allow_html=True)
        for eq in equations: render_equation_object(eq)
        if not equations: st.info("No high-confidence equations were extracted from the PDF.")

    with tabs[3]:
        st.markdown('<div class="section-title">Source visuals</div>', unsafe_allow_html=True)
        st.markdown('<div class="note">These are the original PDF pages identified as containing useful circuits, graphs, block diagrams, tables or other figures. The app intentionally preserves the source visual instead of inventing a generic replacement.</div>', unsafe_allow_html=True)
        seen = set()
        for fig in figures:
            page = fig.get("page")
            if not page or page in seen: continue
            seen.add(page)
            st.markdown('<div class="figure-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="figure-title">{html.escape(str(fig.get("title","Source figure")))}</div><div class="figure-meta">Page {page} · {html.escape(str(fig.get("kind","diagram")))}</div>', unsafe_allow_html=True)
            st.image(render_page(pdf_bytes, int(page)), use_container_width=True)
            st.markdown(f'<div class="lead">{html.escape(str(fig.get("description","")))}</div>', unsafe_allow_html=True)
            if fig.get("why_useful"): st.caption(str(fig["why_useful"]))
            st.markdown('</div>', unsafe_allow_html=True)

    with tabs[4]:
        practice_ui(analysis)

    with tabs[5]:
        st.markdown('<div class="section-title">Ask a university-level doubt</div>', unsafe_allow_html=True)
        question = st.text_area("Your question", placeholder="Example: Derive the closed-loop gain of the inverting amplifier and state the assumptions used.", height=120)
        if st.button("Ask EduAccess AI", type="primary") and question.strip():
            with st.spinner("Reading the original PDF and constructing a technical answer…"):
                try:
                    ans, model, _ = answer_question(st.session_state["file_obj"], question.strip())
                    st.session_state["qa"] = ans.model_dump(); st.session_state["qa_model"] = model
                except Exception as exc:
                    st.error(f"The question could not be answered: {exc}")
        qa = st.session_state.get("qa")
        if qa:
            st.markdown('<div class="section-title">Answer</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="standard-answer">{html.escape(str(qa.get("answer", ""))).replace(chr(10),"<br>")}</div>', unsafe_allow_html=True)
            if qa.get("reasoning_steps"):
                st.markdown('<div class="section-title">Reasoning / derivation</div>', unsafe_allow_html=True)
                for i, x in enumerate(qa["reasoning_steps"], 1): st.write(f"{i}. {x}")
            if qa.get("equations"):
                st.markdown('<div class="section-title">Relevant equations</div>', unsafe_allow_html=True)
                for eq in qa["equations"]: render_formula(eq)
            if qa.get("key_points"):
                st.markdown('<div class="section-title">Key takeaways</div>', unsafe_allow_html=True)
                for x in qa["key_points"]: st.write("•", x)
            if qa.get("assumptions"):
                st.markdown('<div class="section-title">Assumptions</div>', unsafe_allow_html=True)
                for x in qa["assumptions"]: st.write("•", x)
            if qa.get("page_refs"): st.caption("Relevant pages: " + ", ".join(map(str, qa["page_refs"])))

    with tabs[6]:
        st.markdown('<div class="section-title">Preliminary technical review</div>', unsafe_allow_html=True)
        class Obj: pass
        obj = Obj(); obj.important_terms = analysis.get("important_terms", []); obj.equations = analysis.get("equations", []); obj.figures = analysis.get("figures", []); obj.definition = analysis.get("definition", ""); obj.deep_explanation = " ".join(s.get("content", "") for s in analysis.get("deep_sections", [])); obj.key_concepts = analysis.get("key_concepts", [])
        score, checks = preliminary_review(" ".join(analysis.get("source_facts", [])), obj)
        st.metric("Preliminary evidence coverage", f"{score}%")
        st.caption("Development-time heuristic only; it does not establish scientific correctness or validation.")
        for title, ok, msg in checks:
            (st.success if ok else st.warning)(f"{title}: {msg}")
        st.markdown('<div class="section-title">Source warnings</div>', unsafe_allow_html=True)
        for x in analysis.get("source_warnings", []) or ["No source warnings reported."]: st.write("•", x)

    with st.expander("View local extracted text (debug / fallback layer)"):
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf"); txt = "\n\n".join(page.get_text("text") for page in doc); doc.close(); st.text(txt[:20000])


init_state()
with st.sidebar:
    st.markdown("## ✦ EduAccess AI")
    st.caption("University-level STEM learning · native PDF vision · structured topics · equations · source figures · exam practice")
    if st.session_state.get("filename"):
        st.markdown("### Current document")
        st.write(st.session_state["filename"])
        if st.button("Clear document"):
            st.session_state.clear(); st.rerun()

if st.session_state.get("analysis"):
    workspace()
else:
    home()
