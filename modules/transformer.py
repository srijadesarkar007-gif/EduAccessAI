import os
import json
import time

from google import genai
from google.genai import types


MODEL_ORDER = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
]


def _empty_result(message="AI transformation failed."):
    return {
        "mode": "error",
        "error": message,
        "definition": "",
        "explanation": "",
        "deep_explanation": "",
        "prerequisites": [],
        "how_it_works": [],
        "key_concepts": [],
        "equations": [],
        "worked_examples": [],
        "common_mistakes": [],
        "diagrams": [],
        "technical_facts": {
            "terms": [],
            "numbers": [],
            "equations": [],
            "units": [],
            "relationships": [],
        },
    }


def transform_text(text: str):
    """Transform STEM notes into a structured learning representation."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _empty_result("GEMINI_API_KEY is not set.")

    try:
        client = genai.Client(api_key=api_key)

        schema = {
            "type": "object",
            "properties": {
                "definition": {"type": "string"},
                "explanation": {"type": "string"},
                "deep_explanation": {"type": "string"},
                "prerequisites": {
                    "type": "array", "items": {"type": "string"}
                },
                "how_it_works": {
                    "type": "array", "items": {"type": "string"}
                },
                "key_concepts": {
                    "type": "array", "items": {"type": "string"}
                },
                "equations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "latex": {"type": "string"},
                            "meaning": {"type": "string"},
                            "variables": {
                                "type": "array", "items": {"type": "string"}
                            },
                        },
                        "required": ["latex", "meaning", "variables"],
                    },
                },
                "worked_examples": {
                    "type": "array", "items": {"type": "string"}
                },
                "common_mistakes": {
                    "type": "array", "items": {"type": "string"}
                },
                "diagrams": {
                    "type": "array",
                    "description": "Distinct, source-grounded diagrams worth rendering.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "needed": {"type": "boolean"},
                            "type": {"type": "string"},
                            "title": {"type": "string"},
                            "source_basis": {"type": "string"},
                            "elements": {
                                "type": "array", "items": {"type": "string"}
                            },
                            "relationships": {
                                "type": "array", "items": {"type": "string"}
                            },
                        },
                        "required": [
                            "needed", "type", "title", "source_basis",
                            "elements", "relationships"
                        ],
                    },
                },
                "technical_facts": {
                    "type": "object",
                    "properties": {
                        "terms": {"type": "array", "items": {"type": "string"}},
                        "numbers": {"type": "array", "items": {"type": "string"}},
                        "equations": {"type": "array", "items": {"type": "string"}},
                        "units": {"type": "array", "items": {"type": "string"}},
                        "relationships": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["terms", "numbers", "equations", "units", "relationships"],
                },
            },
            "required": [
                "definition", "explanation", "deep_explanation", "prerequisites",
                "how_it_works", "key_concepts", "equations", "worked_examples",
                "common_mistakes", "diagrams", "technical_facts"
            ],
        }

        prompt = f"""
You are EduAccess-AI, an advanced STEM learning system for university students.

The SOURCE MATERIAL is authoritative. Transform it without losing technical
meaning. This input may contain OCR errors from scanned notes.

RULES
1. Preserve technical terms, values, units, equations, definitions,
   constraints, relationships, and cause/effect statements.
2. Correct obvious OCR corruption only when the intended STEM term is strongly
   supported by context. Do not invent uncertain corrections.
3. Provide both an accessible explanation and a deeper technical explanation.
4. Explain mechanisms, derivations, processes, algorithms, and procedures step-by-step.
5. For important mathematics/electronics equations, output valid LaTeX.
6. Explain important variables in equations.
7. Give worked examples only when supported by the source.
8. Identify common mistakes only when grounded in the topic/source.

DIAGRAM RULES
- Identify ALL DISTINCT CONCEPTS in the source that would benefit materially
  from a technical visual.
- Return up to 8 diagrams, not just one.
- Only include a diagram when it is supported by the source material.
- For electronics, prefer circuit/block diagrams.
- For processes/algorithms, prefer flowcharts or process diagrams.
- For relationships among concepts, prefer concept maps.
- For mathematical ideas, prefer graphs or geometric sketches when supported.
- Each diagram must have a distinct title, exact elements, and exact relationships.
- Do not create decorative or invented diagrams.

The output is intended to be rendered as a polished STEM study workspace.

SOURCE MATERIAL:
{text[:50000]}
"""

        last_error = None

        for model_name in MODEL_ORDER:
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
                                thinking_level="high"
                            ),
                        )

                    print(f"Trying model: {model_name} (attempt {attempt + 1})")
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=config,
                    )

                    if not response.text:
                        raise RuntimeError(f"{model_name} returned an empty response.")

                    result = json.loads(response.text)
                    result["mode"] = "gemini"
                    result["model_used"] = model_name

                    # Normalize legacy singular diagram responses if returned.
                    if "diagrams" not in result:
                        legacy = result.get("diagram", {})
                        result["diagrams"] = [legacy] if legacy else []

                    result.pop("diagram", None)
                    return result

                except Exception as exc:
                    last_error = exc
                    msg = str(exc)
                    temporary = any(
                        token in msg
                        for token in ["503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED"]
                    )
                    if temporary and attempt == 0:
                        time.sleep(4)
                        continue
                    if temporary:
                        break
                    raise

        raise last_error or RuntimeError("No Gemini model returned a response.")

    except Exception as exc:
        print("\n=== GEMINI ERROR ===")
        print(str(exc))
        print("====================\n")
        return _empty_result(str(exc))
