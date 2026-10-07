import fitz
import io

from PIL import Image
import pytesseract


# Tell pytesseract exactly where Tesseract is installed.
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def ocr_page(page):
    """
    Render a PDF page as an image and extract text using OCR.
    """

    pix = page.get_pixmap(
        matrix=fitz.Matrix(2.5, 2.5),
        alpha=False
    )

    image_bytes = pix.tobytes("png")

    image = Image.open(
        io.BytesIO(image_bytes)
    )

    text = pytesseract.image_to_string(
        image,
        config="--psm 6"
    )

    return text.strip()


def extract_pdf(uploaded_file):
    """
    Extract text from a PDF.

    First tries normal PDF text extraction.
    If a page has little or no readable text,
    OCR is automatically used for that page.
    """

    pdf_bytes = uploaded_file.read()

    document = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    extracted_pages = []

    for page_number, page in enumerate(document):

        # Try normal text extraction first.
        normal_text = page.get_text("text").strip()

        # If sufficient text exists, use it.
        if len(normal_text) >= 80:
            extracted_pages.append(normal_text)

        # Otherwise fall back to OCR.
        else:
            try:
                ocr_text = ocr_page(page)

                if ocr_text:
                    extracted_pages.append(ocr_text)

            except Exception as e:
                extracted_pages.append(
                    f"[OCR failed on page {page_number + 1}: {e}]"
                )

    document.close()

    final_text = "\n\n".join(
        extracted_pages
    ).strip()

    return final_text