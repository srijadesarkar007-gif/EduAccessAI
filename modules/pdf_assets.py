from __future__ import annotations

import io
from typing import Iterable, List

import fitz
from PIL import Image


def pdf_stats(pdf_bytes: bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = len(doc)
    text = "\n".join(page.get_text("text") for page in doc)
    words = len(text.split())
    doc.close()
    return {"pages": pages, "words": words}


def render_page(pdf_bytes: bytes, page_number: int, scale: float = 1.55) -> Image.Image:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    idx = max(0, min(len(doc) - 1, page_number - 1))
    page = doc[idx]
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    doc.close()
    return image


def render_pages(pdf_bytes: bytes, page_numbers: Iterable[int], scale: float = 1.25) -> List[Image.Image]:
    return [render_page(pdf_bytes, p, scale=scale) for p in page_numbers]
