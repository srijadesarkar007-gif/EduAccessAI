# EduAccess AI — Proof-of-Concept

A research prototype for transforming STEM educational material into more accessible representations while checking whether important technical information may have been lost.

## Current prototype

1. Upload a text-based PDF.
2. Extract its text with PyMuPDF.
3. Generate:
   - simplified explanation
   - definition
   - how-it-works explanation
   - key concepts
4. Run a preliminary technical-fidelity check for:
   - numerical information
   - sampled technical terminology
   - unusually large content reduction

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

The app works in a transparent offline demonstration mode without an API key.

For full LLM transformation, set `OPENAI_API_KEY` in your environment before running.

## Research warning

The fidelity score in this prototype is a heuristic demonstration, NOT a validated scientific metric. For the research paper, the evaluation protocol should be refined and validated against expert annotations.

## Next modules

- image/diagram extraction and educational descriptions
- OCR for scanned PDFs
- text-to-speech
- stronger technical-fidelity evaluation
- baseline vs proposed-system experiments
- participant study and statistical analysis
