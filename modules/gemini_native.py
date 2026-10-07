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


# ============================================================
# MODEL CONFIGURATION
# ============================================================

# Start with the fast Flash-Lite models.
# If one is temporarily unavailable/overloaded, automatically
# try the next model instead of stopping the application.
MODEL_PRIORITY = [
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
]


# ============================================================
# DATA MODELS
# ============================================================

class Equation(BaseModel):
    latex: str = Field(
        description="One mathematical equation only, in minimal valid LaTeX. No prose."
    )
    meaning: str = Field(
        description="Precise university-level interpretation of the equation."
    )
    variables: List[str] = Field(
        default_factory=list,
        description="Meaning of symbols and variables."
    )
    page: Optional[int] = None
    confidence: Literal["high", "medium", "low"] = "medium"


class FigureRef(BaseModel):
    page: int
    title: str
    kind: Literal[
        "circuit",
        "block_diagram",
        "graph",
        "flowchart",
        "process",
        "table",
        "concept_map",
        "diagram",
        "photo",
        "other",
    ] = "diagram"
    description: str
    why_useful: str
    confidence: Literal["high", "medium", "low"] = "medium"


class TopicSection(BaseModel):
    title: str = Field(
        description="Canonical university topic title."
    )
    overview: str = Field(
        description="A 2-4 sentence textbook-quality explanation."
    )
    key_concepts: List[str] = Field(default_factory=list)
    key_equations: List[str] = Field(default_factory=list)
    standard_results: List[str] = Field(default_factory=list)
    exam_relevance: str = Field(
        description="What an undergraduate student should explain, derive, or calculate."
    )
    pages: List[int] = Field(default_factory=list)


class Configuration(BaseModel):
    title: str
    description: str = Field(
        description="Technically precise description of the configuration and signal path."
    )
    purpose: str = Field(
        description="What the configuration is used to accomplish."
    )
    equation_latex: str = Field(
        description="Primary equation only, as minimal valid LaTeX."
    )
    conditions: List[str] = Field(default_factory=list)
    practical_notes: List[str] = Field(default_factory=list)
    pages: List[int] = Field(default_factory=list)


class ExplanationSection(BaseModel):
    title: str
    content: str = Field(
        description="University-level paragraph(s), not bullet fragments."
    )
    equations: List[Equation] = Field(default_factory=list)
    key_points: List[str] = Field(default_factory=list)


class Analysis(BaseModel):
    title: str
    subject: str

    syllabus_topics: List[str]
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

    formula_latex: str = Field(
        description="Minimal valid LaTeX equation only."
    )

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


# ============================================================
# GEMINI CLIENT
# ============================================================

def _client() -> genai.Client:
    key = os.getenv("GEMINI_API_KEY")

    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set in this terminal."
        )

    return genai.Client(api_key=key)


# ============================================================
# PDF HELPERS
# ============================================================

def _temp_pdf(pdf_bytes: bytes) -> Path:
    handle = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf",
    )

    try:
        handle.write(pdf_bytes)
        handle.flush()
    finally:
        handle.close()

    return Path(handle.name)


def prepare_pdf(pdf_bytes: bytes):
    """
    Prepare uploaded PDF as inline Gemini document data.
    """

    if not pdf_bytes:
        raise ValueError(
            "The uploaded PDF is empty."
        )

    if len(pdf_bytes) > 50 * 1024 * 1024:
        raise ValueError(
            "This PDF is larger than the 50 MB inline-processing limit. "
            "Please use a smaller PDF."
        )

    return {
        "type": "document",
        "data": base64.b64encode(
            pdf_bytes
        ).decode("ascii"),
        "mime_type": "application/pdf",
    }


def _response_format(model_cls):
    return {
        "type": "text",
        "mime_type": "application/json",
        "schema": model_cls.model_json_schema(),
    }


# ============================================================
# MAIN GEMINI PDF REQUEST
# ============================================================

def _call_with_document(
    file_obj,
    prompt: str,
    model_cls,
    thinking_level: str = "high",
    retries: int = 0,
):
    """
    Send the PDF directly to Gemini.

    Important:
    - No background interaction polling.
    - No long retry loops.
    - Automatically tries another model if Gemini returns
      503 / 429 / temporary capacity errors.
    """

    client = _client()

    # We keep this parameter because existing callers pass it.
    # Flash-Lite supports thinking, but for PDF analysis we want
    # predictable latency, so we use low thinking where supported.
    del thinking_level
    del retries

    if not isinstance(file_obj, dict):
        raise TypeError(
            "Invalid PDF input."
        )

    encoded_pdf = file_obj.get("data")

    mime_type = file_obj.get(
        "mime_type",
        "application/pdf",
    )

    if not encoded_pdf:
        raise ValueError(
            "The PDF data is empty."
        )

    try:
        pdf_bytes = base64.b64decode(
            encoded_pdf
        )
    except Exception as exc:
        raise ValueError(
            "The PDF data could not be decoded."
        ) from exc

    pdf_part = types.Part.from_bytes(
        data=pdf_bytes,
        mime_type=mime_type,
    )

    errors = []

    # --------------------------------------------------------
    # Try models one by one.
    # --------------------------------------------------------

    for model in MODEL_PRIORITY:

        try:

            # Use low thinking for the first analysis request.
            # This reduces latency considerably.
            try:

                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=model_cls,
                    thinking_config=types.ThinkingConfig(
                        thinking_level="low"
                    ),
                )

            except Exception:

                # Compatibility fallback for older SDK versions.
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=model_cls,
                )

            response = client.models.generate_content(
                model=model,
                contents=[
                    prompt,
                    pdf_part,
                ],
                config=config,
            )

            raw = response.text or ""

            if not raw.strip():
                raise RuntimeError(
                    f"{model} returned an empty response."
                )

            parsed = model_cls.model_validate_json(
                raw
            )

            # SUCCESS
            return (
                parsed,
                model,
                response,
            )

        except Exception as exc:

            message = str(exc)

            errors.append(
                f"{model}: {message}"
            )

            upper_message = message.upper()

            # ------------------------------------------------
            # Temporary capacity / rate-limit errors.
            # Try the next model immediately.
            # ------------------------------------------------

            temporary = (
                "503" in upper_message
                or "UNAVAILABLE" in upper_message
                or "429" in upper_message
                or "RESOURCE_EXHAUSTED" in upper_message
                or "DEADLINE" in upper_message
                or "TIMEOUT" in upper_message
                or "TIMED OUT" in upper_message
                or "INTERNAL" in upper_message
                or "SERVER ERROR" in upper_message
            )

            if temporary:

                # Very short pause before trying next model.
                time.sleep(1)

                continue

            # ------------------------------------------------
            # Authentication errors, invalid requests,
            # schema errors, etc. should NOT be hidden.
            # ------------------------------------------------

            raise RuntimeError(
                f"Gemini request failed on {model}:\n\n"
                f"{message}"
            ) from exc

    # --------------------------------------------------------
    # Nothing worked.
    # --------------------------------------------------------

    raise RuntimeError(
        "All Gemini models were temporarily unavailable.\n\n"
        + "\n".join(errors)
    )


# ============================================================
# PDF ANALYSIS
# ============================================================

def analyze_pdf(file_obj):

    prompt = r"""
You are EduAccess AI, a rigorous university STEM teaching
and examination system.

Read the ORIGINAL PDF VISUALLY as the authoritative source.

Inspect every page for:

- definitions
- laws
- principles
- conditions
- mathematical derivations
- equations
- circuit schematics
- graphs
- block diagrams
- tables
- captions
- standard configurations
- named textbook subtopics
- practical behavior
- limitations

The final result must feel like a high-quality undergraduate
engineering textbook or professor-prepared lecture note.

Do NOT produce a childish summary.

============================================================
ACADEMIC LEVEL
============================================================

- Assume the learner is a university engineering/STEM student.
- Use canonical textbook terminology.
- Preserve mathematical and technical rigor.
- Do not use childish analogies.
- Do not use motivational filler.
- Do not use vague chatbot language.
- Do not invent information.
- Separate ideal assumptions from practical behavior.
- If something is unclear, report it in source_warnings.

============================================================
CORE TEACHING STRUCTURE
============================================================

Build core_sections with approximately 5-8 sections.

Useful sections include:

1. Definition and scope
2. Governing principle / physical basis
3. Mathematical model
4. Important equations
5. Operation / mechanism
6. Standard configurations
7. Practical behavior
8. Applications and limitations

Each section should contain proper university-level
teaching prose.

============================================================
DEEP TEACHING STRUCTURE
============================================================

Build deep_sections with approximately 6-10 sections.

Include:

- detailed reasoning
- derivation logic
- assumptions
- parameter relationships
- practical consequences
- engineering interpretation

Do not simply repeat core_sections.

============================================================
STUDY OUTLINE
============================================================

Each chapter_outline item must be a genuine study section.

For every topic provide:

- canonical title
- overview
- key concepts
- key equations
- standard results
- exam relevance
- page references when possible

Use proper university terminology.

============================================================
STANDARD CONFIGURATIONS
============================================================

For electronics topics identify canonical textbook
configurations.

For OP-AMP topics, when supported by the PDF, use:

1. Inverting amplifier
2. Non-inverting amplifier
3. Voltage follower
4. Summing amplifier
5. Difference/subtractor amplifier
6. Integrator
7. Differentiator

Do NOT invent configurations that are not supported
by the PDF.

For every configuration provide:

- description
- signal path
- purpose
- primary governing equation
- operating conditions
- assumptions
- practical notes
- page references

============================================================
EQUATIONS
============================================================

Only return equations confidently identified from
the source.

Each latex field must contain ONE equation only.

Use minimal valid LaTeX.

Do NOT include:

\text{}
\quad
\left
\right
aligned
array

Do not put prose inside equation fields.

============================================================
FIGURES
============================================================

Identify materially useful source figures.

Classify:

- circuits
- graphs
- block diagrams
- tables
- flowcharts
- diagrams
- photographs

Give exact page numbers where possible.

============================================================
TECHNICAL QUALITY CONTROL
============================================================

Cross-check:

- topic names
- equations
- configurations
- standard results
- assumptions

Do not invent unsupported information.

If the PDF does not provide enough evidence,
record the limitation in source_warnings.
"""


    return _call_with_document(
        file_obj,
        prompt,
        Analysis,
        thinking_level="low",
        retries=0,
    )


# ============================================================
# PRACTICE CONTEXT
# ============================================================

def _practice_context(
    analysis: Optional[dict],
) -> str:

    if not analysis:
        return (
            "No academic analysis is available."
        )

    chunks = []

    topics = analysis.get(
        "syllabus_topics",
        [],
    )[:14]

    if topics:

        chunks.append(
            "STANDARD TOPICS:\n"
            + "\n".join(
                f"- {x}"
                for x in topics
            )
        )

    outline = []

    for item in analysis.get(
        "chapter_outline",
        [],
    )[:10]:

        title = item.get(
            "title",
            "",
        )

        overview = item.get(
            "overview",
            "",
        )

        results = "; ".join(
            item.get(
                "standard_results",
                [],
            )[:3]
        )

        if title:

            outline.append(
                f"{title}: {overview} "
                f"Standard results: {results}"
            )

    if outline:

        chunks.append(
            "TOPIC COVERAGE:\n"
            + "\n".join(
                f"- {x}"
                for x in outline
            )
        )

    configs = []

    for cfg in analysis.get(
        "standard_configurations",
        [],
    )[:10]:

        title = cfg.get(
            "title",
            "",
        )

        desc = cfg.get(
            "description",
            "",
        )

        eq = cfg.get(
            "equation_latex",
            "",
        )

        configs.append(
            f"{title}: {desc} "
            f"Equation: {eq}"
        )

    if configs:

        chunks.append(
            "STANDARD CONFIGURATIONS:\n"
            + "\n".join(
                f"- {x}"
                for x in configs
            )
        )

    equations = []

    for eq in analysis.get(
        "equations",
        [],
    )[:14]:

        latex = eq.get(
            "latex",
            "",
        )

        meaning = eq.get(
            "meaning",
            "",
        )

        if latex or meaning:

            equations.append(
                f"{latex} — {meaning}"
            )

    if equations:

        chunks.append(
            "RELIABLE EQUATIONS:\n"
            + "\n".join(
                f"- {x}"
                for x in equations
            )
        )

    principles = analysis.get(
        "core_principles",
        [],
    )[:8]

    if principles:

        chunks.append(
            "CORE PRINCIPLES:\n"
            + "\n".join(
                f"- {x}"
                for x in principles
            )
        )

    exam = analysis.get(
        "exam_focus",
        [],
    )[:8]

    if exam:

        chunks.append(
            "EXAM FOCUS:\n"
            + "\n".join(
                f"- {x}"
                for x in exam
            )
        )

    facts = analysis.get(
        "source_facts",
        [],
    )[:10]

    if facts:

        chunks.append(
            "SOURCE FACTS:\n"
            + "\n".join(
                f"- {x}"
                for x in facts
            )
        )

    return "\n\n".join(
        chunks
    )[:14000]


# ============================================================
# STRUCTURED PRACTICE GENERATION
# ============================================================

def _call_structured_from_analysis(
    prompt: str,
    model_cls,
    preferred: Optional[str] = None,
):

    client = _client()

    models = []

    if preferred:
        models.append(preferred)

    for model in MODEL_PRIORITY:

        if model not in models:
            models.append(model)

    errors = []

    for model in models:

        try:

            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=model_cls,
            )

            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )

            raw = response.text or ""

            if not raw.strip():
                raise RuntimeError(
                    f"{model} returned an empty response."
                )

            parsed = model_cls.model_validate_json(
                raw
            )

            return (
                parsed,
                model,
                response,
            )

        except Exception as exc:

            message = str(exc)

            errors.append(
                f"{model}: {message}"
            )

            upper_message = message.upper()

            temporary = (
                "503" in upper_message
                or "UNAVAILABLE" in upper_message
                or "429" in upper_message
                or "RESOURCE_EXHAUSTED" in upper_message
                or "TIMEOUT" in upper_message
                or "TIMED OUT" in upper_message
            )

            if temporary:

                time.sleep(1)
                continue

            raise RuntimeError(
                f"Practice generation failed on "
                f"{model}:\n\n{message}"
            ) from exc

    raise RuntimeError(
        "All Gemini models were temporarily unavailable.\n\n"
        + "\n".join(errors)
    )


# ============================================================
# MCQs
# ============================================================

def generate_mcqs(
    file_obj,
    analysis: Optional[dict] = None,
):

    del file_obj

    context = _practice_context(
        analysis
    )

    prompt = f"""
You are setting an undergraduate engineering
university examination.

Generate exactly 4 MCQs from the verified
academic analysis below.

Use:

- canonical syllabus topics
- standard definitions
- principles
- equations
- configuration behavior
- assumptions
- applications
- common misconceptions

Avoid page trivia.

Each question must have exactly four
plausible options and exactly one correct answer.

Questions should test understanding or application,
not memorization.

Return only structured JSON.

{context}
"""

    return _call_structured_from_analysis(
        prompt,
        MCQSet,
        preferred=(analysis or {}).get(
            "model_used"
        ),
    )


# ============================================================
# NUMERICALS
# ============================================================

def generate_numericals(
    file_obj,
    analysis: Optional[dict] = None,
):

    del file_obj

    context = _practice_context(
        analysis
    )

    prompt = rf"""
You are setting standard 5-mark undergraduate
engineering numerical problems.

Generate exactly 2 fully solvable numericals
from the verified academic analysis below.

Use only equations and relationships actually
present in the analysis.

Each problem must contain:

- realistic numerical data
- Given
- Find
- formula
- step-by-step calculation
- unit check
- final numerical answer

formula_latex must contain ONE equation only.

Do not use:

\text
\quad
aligned

Do not create an artificial problem when
the source lacks enough information.

Return only structured JSON.

{context}
"""

    return _call_structured_from_analysis(
        prompt,
        NumericalSet,
        preferred=(analysis or {}).get(
            "model_used"
        ),
    )


# ============================================================
# DESCRIPTIVE QUESTIONS
# ============================================================

def generate_descriptive(
    file_obj,
    analysis: Optional[dict] = None,
):

    del file_obj

    context = _practice_context(
        analysis
    )

    prompt = f"""
You are setting a standard undergraduate
engineering theory paper.

Generate exactly 3 descriptive questions
from the verified academic analysis below.

Use canonical university prompts such as:

- Define
- Explain
- Derive
- Discuss
- Compare
- Analyze

When supported, ask about standard
circuits/configurations.

Each model answer must be appropriate
for 5-10 marks.

Include:

- formal definition
- principle
- technical development
- equations or derivation where relevant
- application
- assumptions or limitations where relevant

Avoid short generic chatbot answers.

Return only structured JSON.

{context}
"""

    return _call_structured_from_analysis(
        prompt,
        DescriptiveSet,
        preferred=(analysis or {}).get(
            "model_used"
        ),
    )


# ============================================================
# COMPLETE PRACTICE SET
# ============================================================

def generate_practice(
    file_obj,
    analysis: Optional[dict] = None,
    count: int = 9,
):

    del count

    mcqs, m_model, _ = generate_mcqs(
        file_obj,
        analysis,
    )

    nums, n_model, _ = generate_numericals(
        file_obj,
        analysis,
    )

    desc, d_model, _ = generate_descriptive(
        file_obj,
        analysis,
    )

    topics = list(
        dict.fromkeys(
            (mcqs.standard_topics or [])
            + (nums.standard_topics or [])
            + (desc.standard_topics or [])
        )
    )

    blueprint = [
        "MCQs: definitions, principles, configurations, interpretation and misconceptions.",
        "Numericals: equation-based applications with units and complete working.",
        "Descriptive: definitions, derivations, circuit/graph explanations and engineering interpretation.",
    ]

    models = ", ".join(
        dict.fromkeys(
            [
                m_model,
                n_model,
                d_model,
            ]
        )
    )

    return (
        PracticeSet(
            standard_topics=topics,
            exam_blueprint=blueprint,
            mcqs=mcqs.questions,
            numericals=nums.questions,
            descriptive=desc.questions,
        ),
        models,
        None,
    )


# ============================================================
# QUESTION ANSWERING
# ============================================================

def answer_question(
    file_obj,
    question: str,
):

    prompt = f"""
You are EduAccess AI, a rigorous university
STEM tutor.

Answer the student's question using ONLY
the uploaded PDF as primary evidence.

Your answer must be appropriate for an
engineering university student.

Required structure:

1. Direct technical answer
2. Underlying principle
3. Detailed reasoning / derivation when relevant
4. Governing equation(s)
5. Assumptions / idealizations
6. Practical implications or limitations
7. Source page references where identifiable

Do not dumb down terminology.

Do not invent facts not supported by the source.

QUESTION:

{question}
"""

    return _call_with_document(
        file_obj,
        prompt,
        QAResponse,
        thinking_level="low",
        retries=0,
    )
