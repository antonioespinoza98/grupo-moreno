import re
from pathlib import Path

import polars as pl
from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract

# 👉 CHANGE THIS to your Poppler bin folder on Windows
# or set to None if poppler is already on PATH.
POPLER_PATH = r"C:\Program Files\poppler-25.11.0\Library\bin"  # <- adjust if needed
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


# ---------- PDF TEXT EXTRACTION ----------

def extract_text_from_pdf(path: str) -> str:
    """Return all text from a PDF using pypdf (no OCR)."""
    reader = PdfReader(path)
    pages_text = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        pages_text.append(page_text)
    return "\n".join(pages_text).strip()


def extract_text_with_ocr(path: str) -> str:
    """Convert PDF pages to images and run OCR."""
    kwargs = {}
    if POPLER_PATH:
        kwargs["poppler_path"] = POPLER_PATH

    images = convert_from_path(path, **kwargs)
    text_chunks = []
    for img in images:
        # You can change lang to "eng+spa" if you have Spanish OCR data installed
        ocr_text = pytesseract.image_to_string(img)  # , lang="eng+spa"
        text_chunks.append(ocr_text)
    return "\n".join(text_chunks).strip()


# ---------- INLINE "INGREDIENTS:" PARSING ----------

STOP_MARKERS = [
    r"\nmanufactured by",
    r"\nmade in",
    r"\nwarning",
    r"\nwww\.",
    r"\nkeep out of reach",
    r"\nuso t[oó]pico",
    r"\nmodo de empleo",
    r"\nmode d'emploi",
    r"\nkey ingredients",
    r"\ningredientes principales",
]


def clean_ingredients_string(s: str) -> str:
    """Normalize whitespace and trailing punctuation."""
    s = re.sub(r"\s+", " ", s)
    return s.strip(" \t\n\r;,.")  # strip common trailing chars


def extract_inline_ingredients(text: str) -> str | None:
    """
    Extract ingredients from running text like:
    'Ingredients: ...' or 'INGREDIENTES: ...'
    (works for English, Spanish, FR mixed stuff).
    """
    if not text:
        return None

    patterns = [
        r"\bingredients?\b\s*[:\-]\s*(.+)",                  # Ingredients:
        r"\bingredients/ingr[ée]dients\b\s*[:\-]\s*(.+)",    # INGREDIENTS/INGRÉDIENTS :
        r"\bingredientes\b\s*[:\-]\s*(.+)",                  # Ingredientes:
        r"\bingredientes/ingredients\b\s*[:\-]\s*(.+)",      # INGREDIENTES/INGREDIENTS :
    ]

    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            continue

        after = m.group(1)

        # stop before other sections (warnings, manufacturer, etc.)
        cut_pos = len(after)
        for sm in STOP_MARKERS:
            ms = re.search(sm, after, flags=re.IGNORECASE)
            if ms and ms.start() < cut_pos:
                cut_pos = ms.start()

        ingredients = clean_ingredients_string(after[:cut_pos])
        if ingredients:
            return ingredients

    return None


# ---------- TABLE PARSING HELPERS ----------

def _extract_name_from_line(line: str) -> str | None:
    """Best-effort extraction of ingredient name from one table row line."""
    if not line.strip():
        return None

    # Drop index like "1." or "1 "
    line = re.sub(r"^\s*\d+[\.\-]?\s+", "", line)

    # If there's a CAS number, use the text before that
    m = re.search(r"\s\d{2,7}-\d{2}-\d\b", line)
    if m:
        return line[:m.start()].strip()

    # If there's a percentage (e.g. 4,32 or 0.099500), use text before that
    m = re.search(r"\s\d+[.,]\d+", line)
    if m:
        return line[:m.start()].strip()

    # If there's "c.s.p." (seen in Spanish formulas), use before that
    m = re.search(r"\sc\.s\.p\.", line, flags=re.IGNORECASE)
    if m:
        return line[:m.start()].strip()

    # Fallback: full line
    return line.strip()


def extract_table_ingredients(text: str) -> str | None:
    """
    Extract ingredients from tabular formulas, like:
    - 'INGREDIENTES/INGREDIENTS (INCI) ...'
    - 'Lista de ingredientes / Nombres INCI'
    - 'INGREDIENTE INCI %p/p FUNCIÓN'
    - 'Components / No. INCI name CAS No. ...'
    """
    if not text:
        return None

    headers = [
        r"INGREDIENTES/INGREDIENTS\s*\(INCI\)",
        r"INGREDIENTE\s+INCI",             # TBH TRUE BEAUTIFUL HONEST table :contentReference[oaicite:0]{index=0}
        r"Lista de ingredientes",          # laCabine formula :contentReference[oaicite:1]{index=1}
        r"No\.\s*INCI name\s*CAS No\.",    # COM-PURIFYING SCRUB components :contentReference[oaicite:2]{index=2}
    ]

    lower_text = text.lower()
    all_names: list[str] = []

    for hpat in headers:
        m = re.search(hpat, text, flags=re.IGNORECASE)
        if not m:
            continue

        start = m.end()
        block = text[start:]

        # Cut block at obvious end-markers of the ingredient table
        stop_pats = [
            r"\nTotal\b",
            r"\nTotal %",          # laCabine formula :contentReference[oaicite:3]{index=3}
            r"\nRangos de concentración",  # laCabine formula page 2
            r"\nREGULACI[ÓO]N COSMETICA",
            r"\nAN[ÁA]LISIS",      # TBH TRUE BEAUTIFUL HONEST :contentReference[oaicite:4]{index=4}
            r"\n2\.\s*Fragrance/Perfume",  # COM-PURIFYING SCRUB :contentReference[oaicite:5]{index=5}
        ]
        cut_pos = len(block)
        for sp in stop_pats:
            ms = re.search(sp, block, flags=re.IGNORECASE)
            if ms and ms.start() < cut_pos:
                cut_pos = ms.start()
        block = block[:cut_pos]

        # Process line by line
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            # Skip the header line itself and obvious non-rows
            if re.search(hpat, line, flags=re.IGNORECASE):
                continue
            if re.match(r"^%?\s*INCI\b", line, flags=re.IGNORECASE):
                continue

            name = _extract_name_from_line(line)
            if not name:
                continue

            # Skip very short / non-ingredient lines
            if len(name) < 3:
                continue

            all_names.append(name)

    # Deduplicate but preserve order
    if not all_names:
        return None

    seen = set()
    unique = []
    for n in all_names:
        if n not in seen:
            seen.add(n)
            unique.append(n)

    return ", ".join(unique)


# ---------- MAIN WRAPPER ----------

def extract_ingredients_from_pdf(path: str) -> str | None:
    """Full pipeline: pypdf → OCR fallback → inline → tables."""
    # 1) plain text
    text = extract_text_from_pdf(path)

    # If the PDF is mostly image, text will be tiny → OCR
    if len(text) < 40:
        text = extract_text_with_ocr(path)

    # 2) Try standard 'Ingredients/Ingredientes:' forms (labels, estuches, tubes)
    ingredients = extract_inline_ingredients(text)
    if ingredients:
        return ingredients

    # 3) Try tabular formulas (INCI lists)
    ingredients = extract_table_ingredients(text)
    if ingredients:
        return ingredients

    # Nothing found
    return None


def build_ingredients_df(pdf_paths: list[str | Path]) -> pl.DataFrame:
    records = []
    for pdf in pdf_paths:
        pdf = Path(pdf)
        print(f"Processing: {pdf.name}")
        ingredients = extract_ingredients_from_pdf(str(pdf))
        records.append(
            {
                "file_name": pdf.name,
                "ingredients": ingredients,
            }
        )
    return pl.DataFrame(records)


if __name__ == "__main__":
    # 🔁 Example with your files (adjust the folder as needed)
    pdfs = [
        "213089 TK COLOR STAY COND1000.pdf",
        "033465- OO BUTTERFLY 14 ml Etiqueta (v.0419).pdf",
        "2445311_30116710_2.pdf",
        "AAFF_ESTUCHE_LACABINE_AMPOLLAS_FACIALES_SUR_EUROPA_x10_EYE_CONTOUR_ES_EN_IT_PT.pdf",
        "COM-PURIFYING SCRUB-16JAN24.pdf",
        "FORM GO BUTTERFLY Cuantitativa (0419).pdf",
        "FORM_LACABINE AMPOLLA EYE CONTOUR.pdf",
        "FORMULA TK COLOR STAY CONDITIONER.pdf",
        "MO-Hair-Scalp-2024-PurifyingScrub-125ml-GL.pdf",
        "TBH Tone softener.pdf",
    ]

    df = build_ingredients_df(pdfs)
    print(df)
