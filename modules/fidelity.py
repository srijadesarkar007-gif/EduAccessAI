from __future__ import annotations

import re
from difflib import SequenceMatcher


def _clean_tokens(text: str):
    return re.findall(r"[A-Za-z][A-Za-z0-9-]{4,}", text.lower())


def preliminary_review(source_text: str, analysis):
    """Preliminary coverage signal, not a scientific correctness score."""
    checks = []

    source_tokens = set(_clean_tokens(source_text))
    generated_terms = {t.lower() for t in analysis.important_terms}
    if source_tokens and generated_terms:
        coverage = max((SequenceMatcher(None, s, g).ratio() for s in source_tokens for g in generated_terms), default=0)
        checks.append(("Terminology coverage", coverage >= 0.55, "Sampled source terminology is represented in the structured analysis."))
    else:
        checks.append(("Terminology coverage", False, "Insufficient source text for a meaningful terminology comparison."))

    checks.append((
        "Equations",
        len(analysis.equations) > 0,
        f"{len(analysis.equations)} structured equations were extracted from the native PDF view."
    ))
    checks.append((
        "Figures",
        len(analysis.figures) > 0,
        f"{len(analysis.figures)} source figures were identified."
    ))
    checks.append((
        "Structured coverage",
        all(bool(getattr(analysis, field, None)) for field in ["definition", "deep_explanation", "key_concepts"]),
        "Core learning sections were generated."
    ))

    passed = sum(1 for _, ok, _ in checks if ok)
    score = round(100 * passed / len(checks)) if checks else 0
    return score, checks
