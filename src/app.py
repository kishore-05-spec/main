# app/docling_parser.py
from io import BytesIO
from typing import List, Dict, Any
from app.config import settings
from app.logger import logger
from app.heading_utils import determine_heading_level, headers_match
from app.utils_imports import safe_import_docling

DocumentConverter, InputFormat = safe_import_docling()

# OCR fallback
from pdf2image import convert_from_bytes
import pytesseract

# PyMuPDF for quick scanned detection
import fitz

def ocr_text_from_pdf_bytes(pdf_bytes: BytesIO) -> List[str]:
    pdf_bytes.seek(0)
    images = convert_from_bytes(pdf_bytes.read(), dpi=300)
    texts = []
    for img in images:
        texts.append(pytesseract.image_to_string(img))
    pdf_bytes.seek(0)
    return texts

def is_scanned_pdf(pdf_bytes: BytesIO) -> bool:
    pdf_bytes.seek(0)
    try:
        data = pdf_bytes.read()
        doc = fitz.open(stream=data, filetype="pdf")
        for p in doc:
            if p.get_text().strip():
                pdf_bytes.seek(0)
                return False
        pdf_bytes.seek(0)
        return True
    except Exception as e:
        logger.warning("fitz check failed: %s; treating as not scanned", e)
        pdf_bytes.seek(0)
        return False

def extract_structured(pdf_stream: BytesIO) -> Dict[str, Any]:
    """
    Returns JSON dict:
    {
      "file": null,
      "pages": [
         { "page_number":1, "structure":[{"type":"heading","level":1,"text":...}, ...], "tables":[...] },
         ...
      ],
      "merged_tables": [ {"start_page":1,"end_page":2,"rows":[...]} ]
    }
    """
    logger.info("Starting extraction (CPU mode)")

    # detect scanned
    if is_scanned_pdf(pdf_stream):
        logger.info("Scanned PDF detected -> OCRing each page")
        ocr_pages = ocr_text_from_pdf_bytes(pdf_stream)
        pages = []
        for i, t in enumerate(ocr_pages, start=1):
            pages.append({
                "page_number": i,
                "structure": [{"type":"paragraph", "text": t.strip()}],
                "tables": []
            })
        return {"file": None, "pages": pages, "merged_tables": []}

    # Use Docling converter (CPU only)
    converter = DocumentConverter()  # CPU mode by default
    pdf_stream.seek(0)
    try:
        result = converter.convert(pdf_stream)
    except Exception as e:
        logger.exception("Docling convert failed; falling back to OCR-only: %s", e)
        ocr_pages = ocr_text_from_pdf_bytes(pdf_stream)
        pages = []
        for i, t in enumerate(ocr_pages, start=1):
            pages.append({
                "page_number": i,
                "structure": [{"type":"paragraph", "text": t.strip()}],
                "tables": []
            })
        return {"file": None, "pages": pages, "merged_tables": []}

    # iterate pages
    pages_out = []
    all_tables = []
    for page in result.document.pages:
        page_num = getattr(page, "page_number", None) or (len(pages_out) + 1)
        structure = []
        page_tables = []

        # process text blocks in reading order
        for block in getattr(page, "blocks", []) or []:
            text = (block.text or "").strip()
            if not text:
                continue

            level = determine_heading_level(block)
            if level in (1,2):
                structure.append({"type":"heading", "level": level, "text": text})
            else:
                # detect bullets / points
                if text.lstrip().startswith(("- ", "* ", "•", "—")) or text.startswith(("•", "-", "*")):
                    structure.append({"type":"point", "text": text})
                else:
                    structure.append({"type":"paragraph", "text": text})

        # extract tables on this page
        for tbl in getattr(page, "tables", []) or []:
            rows = []
            for r in getattr(tbl, "rows", []) or []:
                cells = []
                for c in getattr(r, "cells", []) or []:
                    cells.append((c.text or "").strip())
                rows.append(cells)
            if rows:
                table_obj = {"page": page_num, "rows": rows}
                page_tables.append(table_obj)
                all_tables.append(table_obj)

        pages_out.append({"page_number": page_num, "structure": structure, "tables": page_tables})

    # merge consecutive tables with matching headers
    merged = []
    prev = None
    for t in all_tables:
        if not t["rows"]:
            continue
        header = t["rows"][0]
        if prev and headers_match(prev["rows"][0], header) and t["page"] == prev["end_page"] + 1:
            prev["rows"].extend(t["rows"][1:])
            prev["end_page"] = t["page"]
        else:
            if prev:
                merged.append(prev)
            prev = {"start_page": t["page"], "end_page": t["page"], "rows": [row[:] for row in t["rows"]]}
    if prev:
        merged.append(prev)

    merged_out = [{"start_page": m["start_page"], "end_page": m["end_page"], "rows": m["rows"]} for m in merged]

    return {"file": None, "pages": pages_out, "merged_tables": merged_out}
