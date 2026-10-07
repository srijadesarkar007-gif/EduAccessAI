from __future__ import annotations

import os
import base64
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
MODEL_PRIORITY = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
]

class Equation(BaseModel):
    latex: str = Field(description="One mathematical equation only, in minimal valid LaTeX. No prose.")
    meaning: str = Field(description="Precise university-level interpretation of the equation.")
    variables: List[str] = Field(default_factory=list, description="Meaning of symbols and variables.")
    page: Optional[int] = None
    confidence: Literal["high", "medium", "low"] = "medium"


class FigureRef(BaseModel):
    page: int
    title: str
    kind: Literal["circuit", "block_diagram", "graph", "flowchart", "process", "table", "concept_map", "diagram", "photo", "other"] = "diagram"
    description: str
    why_useful: str
    confidence: Literal["high", "medium", "low"] = "medium"


class TopicSection(BaseModel):
    title: str = Field(description="Canonical university topic title.")
    overview: str = Field(description="A 2-4 sentence textbook-quality explanation of this topic, not merely a label.")
    key_concepts: List[str] = Field(default_factory=list)
    key_equations: List[str] = Field(default_factory=list, description="Equation identifiers or compact equations in plain text; no long prose.")
    standard_results: List[str] = Field(default_factory=list, description="Standard textbook results, conditions, or conclusions.")
    exam_relevance: str = Field(description="What an undergraduate student should be able to explain/derive/calculate for exams.")
    pages: List[int] = Field(default_factory=list)


class Configuration(BaseModel):
    title: str
    description: str = Field(description="Technically precise description of the configuration and signal path.")
    purpose: str = Field(description="What the configuration is used to accomplish.")
    equation_latex: str = Field(description="Primary equation only, as minimal valid LaTeX. No prose.")
    conditions: List[str] = Field(default_factory=list)
    practical_notes: List[str] = Field(default_factory=list)
    pages: List[int] = Field(default_factory=list)


class ExplanationSection(BaseModel):
    title: str
    content: str = Field(description="University-level paragraph(s), not bullet fragments.")
    equations: List[Equation] = Field(default_factory=list)
    key_points: List[str] = Field(default_factory=list)


class Analysis(BaseModel):
    title: str
    subject: str
    syllabus_topics: List[str] = Field(description="Canonical university-level topics actually supported by the PDF.")
    learning_objectives: List[str]
    chapter_outline: List[TopicSection]
    definition: str
    core_sections: List[ExplanationSection]
    deep_sections: List[ExplanationSection]
    core_principles: List[str]
    standard_configurations: List[Configuration]
    prerequisites: List[str]
    key_concepts: List[str]
    how_it_works: List[str]
    derivations: List[str]
    equations: List[Equation]
    figures: List[FigureRef]
    applications: List[str]
    assumptions: List[str]
    limitations: List[str]
    exam_focus: List[str]
    source_facts: List[str]
    important_terms: List[str]
    common_mistakes: List[str]
    study_strategy: List[str]
    source_warnings: List[str]


class MCQQuestion(BaseModel):
    topic: str
    question: str
    options: List[str] = Field(min_length=4, max_length=4)
    answer_index: int = Field(ge=0, le=3)
    explanation: str
    difficulty: Literal["easy", "medium", "hard"]
    marks: int = 1
    page: Optional[int] = None


class NumericalQuestion(BaseModel):
    topic: str
    question: str
    given: List[str]
    find: List[str]
    formula_latex: str = Field(description="Minimal valid LaTeX equation only. No prose or text commands.")
    formula_text: str
    solution_steps: List[str]
    final_answer: str
    unit_check: str = ""
    difficulty: Literal["easy", "medium", "hard"]
    marks: int = 5
    page: Optional[int] = None


class DescriptiveQuestion(BaseModel):
    topic: str
    question: str
    key_points: List[str]
    model_answer: str
    difficulty: Literal["easy", "medium", "hard"]
    marks: int = 5
    page: Optional[int] = None


class MCQSet(BaseModel):
    standard_topics: List[str]
    questions: List[MCQQuestion]


class NumericalSet(BaseModel):
    standard_topics: List[str]
    questions: List[NumericalQuestion]


class DescriptiveSet(BaseModel):
    standard_topics: List[str]
    questions: List[DescriptiveQuestion]


class PracticeSet(BaseModel):
    standard_topics: List[str]
    exam_blueprint: List[str]
    mcqs: List[MCQQuestion]
    numericals: List[NumericalQuestion]
    descriptive: List[DescriptiveQuestion]


class QAResponse(BaseModel):
    answer: str
    reasoning_steps: List[str]
    key_points: List[str]
    equations: List[str]
    assumptions: List[str]
    page_refs: List[int]
    confidence: Literal["high", "medium", "low"]


def _client() -> genai.Client:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set in this terminal.")
    return genai.Client(api_key=key)


def _temp_pdf(pdf_bytes: bytes) -> Path:
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    try:
        handle.write(pdf_bytes)
        handle.flush()
    finally:
        handle.close()
    return Path(handle.name)


def prepare_pdf(pdf_bytes: bytes):
    """Prepare a PDF as inline document data.

    Gemini supports inline PDF input for files below the documented PDF size
    limit. This avoids waiting on the Files API processing queue and is ideal
    for EduAccess AI's interactive single-document workflow.
    """
    if not pdf_bytes:
        raise ValueError("The uploaded PDF is empty.")
    if len(pdf_bytes) > 50 * 1024 * 1024:
        raise ValueError("This PDF is larger than the 50 MB inline-processing limit. Please use a smaller PDF.")
    return {
        "type": "document",
        "data": base64.b64encode(pdf_bytes).decode("ascii"),
        "mime_type": "application/pdf",
    }


def _response_format(model_cls):
    return {"type": "text", "mime_type": "application/json", "schema": model_cls.model_json_schema()}


def _call_with_document(file_obj, prompt: str, model_cls, thinking_level: str = "high", retries: int = 2):
    client = _client()
    models = MODEL_PRIORITY
    last_error = None
    for model in models:
        for attempt in range(retries):
            try:
                interaction = client.interactions.create(
                    model=model,
                    input=[
                        {"type": "text", "text": prompt},
                        file_obj,
                    ],
                    response_format=[_response_format(model_cls)],
                    generation_config={"thinking_level": thinking_level},
                    timeout=45,
                )
                raw = interaction.output_text or ""
                if not raw.strip():
                    raise RuntimeError(f"{model} returned an empty response.")
                parsed = model_cls.model_validate_json(raw)
                return parsed, model, interaction
            except Exception as exc:
                last_error = exc
                msg = str(exc)
                temporary = any(t in msg for t in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "INCOMPLETE", "deadline", "timed out"))
                if temporary and attempt < retries - 1:
                    time.sleep(2 + attempt * 2)
                    continue
                if temporary:
                    break
                raise
    raise last_error or RuntimeError("No Gemini model returned a response.")


def analyze_pdf(file_obj):
    prompt = r"""
You are EduAccess AI, a rigorous university STEM teaching and examination system.

Read the ORIGINAL PDF VISUALLY as the authoritative source. Inspect every page for:
- definitions, laws, principles, and conditions
- mathematical derivations and equations
- circuit schematics, graphs, block diagrams, tables and captions
- standard configurations and named textbook subtopics
- practical/non-ideal behavior and limitations

The final result must feel like a high-quality undergraduate engineering textbook
or professor-prepared lecture note, not a simplified chatbot summary.

ACADEMIC LEVEL
- Assume the learner is a university engineering/STEM student.
- Use canonical textbook terminology.
- Preserve mathematical and technical rigor.
- Do not use childish analogies, motivational filler, vague summaries, or conversational filler.
- Do not simply paraphrase the PDF. Reconstruct a coherent academic treatment.
- Separate ideal assumptions from practical behavior.
- Never invent a correction when the source is ambiguous; report uncertainty in source_warnings.

CORE TEACHING STRUCTURE
Build core_sections with 5-8 sections where appropriate. Prefer sections such as:
1. Definition and scope
2. Governing principle / physical basis
3. Mathematical model and important equations
4. Operation / signal path / mechanism
5. Standard configurations and their results
6. Practical behavior / non-idealities
7. Applications and limitations

Each section must contain paragraph-style teaching prose, not one-line bullets.

DEEP TEACHING STRUCTURE
Build deep_sections with 6-10 sections. Include detailed reasoning, derivation logic,
assumptions, parameter relationships, practical consequences, and engineering interpretation.
Do not merely repeat core_sections with different wording.

STUDY OUTLINE
Each chapter_outline item MUST be an actual mini-study section, not merely a topic name.
For each topic provide:
- overview: 2-4 explanatory sentences
- key concepts
- key equations
- standard results / conditions
- exam relevance: what a university student should know, derive, or calculate
- page references when identifiable
Use canonical names. Example: "Inverting Amplifier", not "Amplifier Topic 3".

STANDARD CONFIGURATIONS / VARIANTS

For electronics topics, identify canonical textbook-standard configurations, not arbitrary variants.

For OP-AMP topics specifically, when the source supports them, use these canonical configurations:
1. Inverting amplifier
2. Non-inverting amplifier
3. Voltage follower (unity-gain buffer)
4. Summing amplifier
5. Difference/subtractor amplifier
6. Integrator
7. Differentiator

Do not rename these into vague labels such as "amplifier circuit", "gain stage", or "signal conditioning configuration".
Do not invent a configuration that is not supported by the source PDF.
Do not treat a generic application, block diagram, or component arrangement as a standard configuration.
For each configuration, preserve the standard textbook topology, input/output relationship, polarity, gain relationship, assumptions, and governing equation exactly as supported by the source.

Each configuration must be structured and technically explicit. Provide:
- description of signal path and component relationships
- purpose
- ONE primary governing equation in clean minimal LaTeX only
- operating conditions / assumptions
- practical notes
- source pages
EQUATIONS
Only return equations you can identify confidently from the source PDF.
Each latex field MUST contain ONE equation only, in minimal renderable LaTeX.
Allowed constructs include: fractions, subscripts, superscripts, Greek symbols,
roots, parentheses, sums, integrals, and common operators.
DO NOT include \text{}, \quad, \left, \right, aligned, array, or prose inside latex.

FIGURES
Identify all materially useful source figures up to 15. Classify circuits, graphs,
block diagrams, tables, etc. Give exact page numbers where possible. Never replace a
source graph or circuit with a generic conceptual description when the source figure exists.

TECHNICAL QUALITY CONTROL
Cross-check topic names, equations, configurations, and standard results against one another.
Avoid generic facts not supported by the PDF unless they are clearly presented as background.
"""
    return _call_with_document(file_obj, prompt, Analysis, thinking_level="medium", retries=2)



def _analysis_practice_context(analysis: Optional[dict]) -> str:
    if not analysis:
        return ""
    chunks=[]
    topics=analysis.get("syllabus_topics", [])[:18]
    if topics:
        chunks.append("CANONICAL TOPICS:\n" + "\n".join(f"- {x}" for x in topics))
    cfgs=[]
    for cfg in analysis.get("standard_configurations", [])[:12]:
        title=cfg.get("title", "")
        desc=cfg.get("description", "")
        eq=cfg.get("equation_latex", "")
        cfgs.append(f"{title}: {desc}. Equation: {eq}")
    if cfgs:
        chunks.append("STANDARD CONFIGURATIONS:\n" + "\n".join(f"- {x}" for x in cfgs))
    eqs=[]
    for e in analysis.get("equations", [])[:18]:
        latex=e.get("latex", "")
        meaning=e.get("meaning", "")
        if latex or meaning:
            eqs.append(f"{latex} — {meaning}")
    if eqs:
        chunks.append("CORE EQUATIONS:\n" + "\n".join(f"- {x}" for x in eqs))
    facts=analysis.get("source_facts", [])[:16]
    if facts:
        chunks.append("SOURCE FACTS:\n" + "\n".join(f"- {x}" for x in facts))
    principles=analysis.get("core_principles", [])[:10]
    if principles:
        chunks.append("CORE PRINCIPLES:\n" + "\n".join(f"- {x}" for x in principles))
    exam=analysis.get("exam_focus", [])[:10]
    if exam:
        chunks.append("EXAM FOCUS:\n" + "\n".join(f"- {x}" for x in exam))
    return "\n\n".join(chunks)


def _practice_models(preferred: Optional[str] = None):
    """Fast, bounded model order for practice generation."""
    models = []
    # Use the analysis model first when available, then current stable/fast fallbacks.
    for model in [preferred, PRIMARY_MODEL, SECONDARY_MODEL, FALLBACK_MODEL]:
        if model and model not in models:
            models.append(model)
    return models


def _call_structured_from_analysis(
    prompt: str,
    model_cls,
    preferred: Optional[str] = None,
):
    """Generate compact structured practice output reliably.

    Practice is generated from the verified academic analysis, not by re-sending
    the PDF. We use the standard generate_content + Pydantic structured-output
    path, with medium reasoning and bounded output. Unlike the previous build,
    there is no 20-second thread timeout that could make valid requests look like
    failures while Gemini is still reasoning.
    """
    client = _client()
    last_error = None

    models = _practice_models(preferred)

    for model in models:
        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=model_cls,
                thinking_config=types.ThinkingConfig(
                    thinking_level="medium"
                ),
                max_output_tokens=12000,
            )

            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )

            raw = response.text or ""
            if not raw.strip():
                raise RuntimeError(
                    f"{model} returned an empty structured response."
                )

            parsed = model_cls.model_validate_json(raw)
            return parsed, model, response

        except Exception as exc:
            last_error = exc
            msg = str(exc)
            temporary = any(
                token in msg
                for token in (
                    "503",
                    "UNAVAILABLE",
                    "429",
                    "RESOURCE_EXHAUSTED",
                    "deadline",
                    "timed out",
                    "timeout",
                )
            )

            if temporary:
                time.sleep(3)
                continue

            raise

    raise last_error or RuntimeError(
        "No Gemini model returned a structured practice response."
    )

def _practice_context(analysis: Optional[dict]) -> str:
    """Build a compact, high-signal context for exam generation."""
    if not analysis:
        return "No academic analysis is available."

    chunks = []
    topics = analysis.get("syllabus_topics", [])[:14]
    if topics:
        chunks.append("STANDARD TOPICS:\n" + "\n".join(f"- {x}" for x in topics))

    outline = []
    for item in analysis.get("chapter_outline", [])[:10]:
        title = item.get("title", "")
        overview = item.get("overview", "")
        results = "; ".join(item.get("standard_results", [])[:3])
        if title:
            outline.append(f"{title}: {overview} Standard results: {results}")
    if outline:
        chunks.append("TOPIC COVERAGE:\n" + "\n".join(f"- {x}" for x in outline))

    configs = []
    for cfg in analysis.get("standard_configurations", [])[:10]:
        title = cfg.get("title", "")
        desc = cfg.get("description", "")
        eq = cfg.get("equation_latex", "")
        configs.append(f"{title}: {desc} Equation: {eq}")
    if configs:
        chunks.append("STANDARD CONFIGURATIONS:\n" + "\n".join(f"- {x}" for x in configs))

    eqs = []
    for eq in analysis.get("equations", [])[:14]:
        latex = eq.get("latex", "")
        meaning = eq.get("meaning", "")
        if latex or meaning:
            eqs.append(f"{latex} — {meaning}")
    if eqs:
        chunks.append("RELIABLE EQUATIONS:\n" + "\n".join(f"- {x}" for x in eqs))

    principles = analysis.get("core_principles", [])[:8]
    if principles:
        chunks.append("CORE PRINCIPLES:\n" + "\n".join(f"- {x}" for x in principles))

    exam = analysis.get("exam_focus", [])[:8]
    if exam:
        chunks.append("EXAM FOCUS:\n" + "\n".join(f"- {x}" for x in exam))

    facts = analysis.get("source_facts", [])[:10]
    if facts:
        chunks.append("SOURCE FACTS:\n" + "\n".join(f"- {x}" for x in facts))

    return "\n\n".join(chunks)[:14000]


def generate_mcqs(file_obj, analysis: Optional[dict] = None):
    del file_obj
    context = _practice_context(analysis)
    prompt = f"""
You are setting an undergraduate engineering university examination.
Generate exactly 4 MCQs from the verified academic analysis below.
Use canonical syllabus topics, standard definitions, principles, equations,
configuration behavior, assumptions, applications and common misconceptions.
Avoid incidental page trivia.
Each question must have exactly four plausible options and exactly one correct option.
Questions must test understanding or application, not memorization of wording.
Return only the requested structured JSON.

{context}
"""
    return _call_structured_from_analysis(
        prompt, MCQSet, preferred=(analysis or {}).get("model_used")
    )


def generate_numericals(file_obj, analysis: Optional[dict] = None):
    del file_obj
    context = _practice_context(analysis)
    prompt = rf"""
You are setting standard 5-mark undergraduate engineering numerical problems.
Generate exactly 2 fully solvable numericals from the verified academic analysis below.
Use only equations and relationships actually present in the analysis.
Each problem must contain realistic numerical data, Given, Find, one primary formula,
step-by-step substitution/calculation, unit check, and a final numerical answer.
Use a clean minimal LaTeX expression in formula_latex: ONE equation only, no prose,
no \text, no \quad, no aligned environment.
Do not create an artificial problem when the source lacks enough information.
Return only the requested structured JSON.

{context}
"""
    return _call_structured_from_analysis(
        prompt, NumericalSet, preferred=(analysis or {}).get("model_used")
    )


def generate_descriptive(file_obj, analysis: Optional[dict] = None):
    del file_obj
    context = _practice_context(analysis)
    prompt = f"""
You are setting a standard undergraduate engineering theory paper.
Generate exactly 3 descriptive questions from the verified academic analysis below.
Use canonical university prompts such as Define, Explain, Derive, Discuss, Compare,
Analyze, or Explain the operation of a standard circuit/configuration when supported.
Each model answer must be appropriate for 5-10 marks: formal definition/principle,
technical development, equations or derivation where relevant, and application,
assumption or limitation where appropriate. Avoid short generic chatbot answers.
Return only the requested structured JSON.

{context}
"""
    return _call_structured_from_analysis(
        prompt, DescriptiveSet, preferred=(analysis or {}).get("model_used")
    )


def generate_practice(file_obj, analysis: Optional[dict] = None, count: int = 9):
    # Each section is generated independently from the compact verified analysis.
    # This avoids resending the PDF and prevents one failure from blocking all sections.
    mcqs, m_model, _ = generate_mcqs(file_obj, analysis)
    nums, n_model, _ = generate_numericals(file_obj, analysis)
    desc, d_model, _ = generate_descriptive(file_obj, analysis)
    models = ", ".join(dict.fromkeys([m_model, n_model, d_model]))
    topics = list(dict.fromkeys(
        (mcqs.standard_topics or [])
        + (nums.standard_topics or [])
        + (desc.standard_topics or [])
    ))
    blueprint = [
        "MCQs: canonical definitions, principles, standard configurations, interpretation and misconceptions.",
        "Numericals: standard equation-based 5-mark applications with units and complete working.",
        "Descriptive: formal definitions, derivations, circuit/graph explanations and engineering interpretation.",
    ]
    return PracticeSet(
        standard_topics=topics,
        exam_blueprint=blueprint,
        mcqs=mcqs.questions,
        numericals=nums.questions,
        descriptive=desc.questions,
    ), models, None

def answer_question(file_obj, question: str):
    prompt = f"""
You are EduAccess AI, a rigorous university STEM tutor.

Answer the student's question using ONLY the uploaded PDF as primary evidence.
Your answer must be appropriate for an engineering university student.

Required structure:
1. Direct technical answer
2. Underlying principle
3. Detailed reasoning / derivation when relevant
4. Governing equation(s), rendered cleanly
5. Assumptions / idealizations
6. Practical implications or limitations
7. Source page references where identifiable

Do not dumb down terminology. Do not invent facts not supported by the source.

QUESTION:
{question}
"""
    return _call_with_document(file_obj, prompt, QAResponse, thinking_level="high", retries=2)
