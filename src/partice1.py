config.py
# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
    S3_BUCKET = os.getenv("S3_BUCKET", None)
    ENV = os.getenv("ENV", "local")
    DEVICE = "cpu"  # CPU mode only

settings = Settings()    

# s3 utils.py    --------------------------->
# app/s3_utils.py
import boto3
import requests
from urllib.parse import urlparse
from io import BytesIO
from app.config import settings

def get_pdf_stream(file_uri: str) -> BytesIO:
    """
    Returns a BytesIO stream from:
      - s3://bucket/key
      - https://... (URL)
      - key (using default S3 bucket)
    """
    pdf_stream = BytesIO()

    if file_uri.startswith("s3://"):
        parsed = urlparse(file_uri)
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY,
            aws_secret_access_key=settings.AWS_SECRET_KEY,
            region_name=settings.AWS_REGION,
        )
        s3.download_fileobj(bucket, key, pdf_stream)

    elif file_uri.startswith("http://") or file_uri.startswith("https://"):
        r = requests.get(file_uri, stream=True)
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                pdf_stream.write(chunk)

    else:
        if not settings.S3_BUCKET:
            raise ValueError("S3_BUCKET not configured for plain key access")
        key = file_uri
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY,
            aws_secret_access_key=settings.AWS_SECRET_KEY,
            region_name=settings.AWS_REGION,
        )
        s3.download_fileobj(settings.S3_BUCKET, key, pdf_stream)

    pdf_stream.seek(0)
    return pdf_stream


# -------heading_utils.py
# app/heading_utils.py
import re
from typing import List
from difflib import SequenceMatcher

def normalize_text(t: str) -> str:
    return " ".join(t.strip().split()).lower()

def is_numbering_heading(text: str):
    text = text.strip()
    m = re.match(r"^(\d+(\.\d+)*)\s+", text)
    if m:
        level = m.group(1).count(".") + 1
        return True, level
    m2 = re.match(r"^[A-Z]\.\s+", text)
    if m2:
        return True, 1
    return False, None

def determine_heading_level(block) -> int:
    text = (block.text or "").strip()
    if not text:
        return 0

    num, lvl = is_numbering_heading(text)
    if num:
        return min(lvl, 3)

    words = text.split()
    if text.isupper() and len(words) <= 8:
        return 1
    if text.istitle() and len(words) <= 10:
        return 2

    try:
        spans = getattr(block, "spans", None)
        if spans and len(spans) > 0:
            size = spans[0].size
            font = spans[0].font or ""
            bold = "Bold" in font
            if size >= 18 or (bold and size >= 14):
                return 1
            if 14 <= size < 18:
                return 2
            return 3
    except Exception:
        pass

    try:
        bbox = getattr(block, "bbox", None)
        if bbox:
            x0 = bbox[0]
            if x0 < 40:
                return 1
            elif x0 < 90:
                return 2
            else:
                return 3
    except Exception:
        pass

    return 3

def headers_match(h1: List[str], h2: List[str]) -> bool:
    if not h1 or not h2 or len(h1) != len(h2):
        return False
    for a, b in zip(h1, h2):
        na, nb = normalize_text(a), normalize_text(b)
        if SequenceMatcher(None, na, nb).ratio() < 0.75:
            return False
    return True


# utils imports.py
# app/utils_imports.py
def safe_import_docling():
    try:
        from docling.document_converter import DocumentConverter
        from docling.datamodel import InputFormat
        return DocumentConverter, InputFormat
    except Exception as e:
        raise ImportError("Docling not found. Run `pip install docling`.") from e
  #   docling parser .py 
# app/docling_parser.py
from io import BytesIO
from typing import List, Dict, Any
from app.config import settings
from app.heading_utils import determine_heading_level, headers_match
from app.utils_imports import safe_import_docling
from pdf2image import convert_from_bytes
import pytesseract
import fitz

DocumentConverter, InputFormat = safe_import_docling()

def ocr_text_from_pdf_bytes(pdf_bytes: BytesIO) -> List[str]:
    pdf_bytes.seek(0)
    images = convert_from_bytes(pdf_bytes.read(), dpi=300)
    texts = [pytesseract.image_to_string(img) for img in images]
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
    except Exception:
        pdf_bytes.seek(0)
        return False

def extract_structured(pdf_stream: BytesIO) -> Dict[str, Any]:
    if is_scanned_pdf(pdf_stream):
        ocr_pages = ocr_text_from_pdf_bytes(pdf_stream)
        pages = []
        for i, t in enumerate(ocr_pages, start=1):
            pages.append({
                "page_number": i,
                "structure": [{"type": "paragraph", "text": t.strip()}],
                "tables": []
            })
        return {"pages": pages, "merged_tables": []}

    converter = DocumentConverter()
    pdf_stream.seek(0)
    result = converter.convert(pdf_stream)

    pages_out = []
    all_tables = []
    for page in result.document.pages:
        page_num = getattr(page, "page_number", None) or (len(pages_out) + 1)
        structure = []
        page_tables = []

        for block in getattr(page, "blocks", []) or []:
            text = (block.text or "").strip()
            if not text:
                continue

            level = determine_heading_level(block)
            if level in (1, 2):
                structure.append({"type": "heading", "level": level, "text": text})
            else:
                if text.lstrip().startswith(("- ", "* ", "•", "—")):
                    structure.append({"type": "point", "text": text})
                else:
                    structure.append({"type": "paragraph", "text": text})

        for tbl in getattr(page, "tables", []) or []:
            rows = []
            for r in getattr(tbl, "rows", []) or []:
                cells = [(c.text or "").strip() for c in getattr(r, "cells", []) or []]
                rows.append(cells)
            if rows:
                table_obj = {"page": page_num, "rows": rows}
                page_tables.append(table_obj)
                all_tables.append(table_obj)

        pages_out.append({
            "page_number": page_num,
            "structure": structure,
            "tables": page_tables
        })

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

    return {"pages": pages_out, "merged_tables": merged_out}
# main.py

# app/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from app.s3_utils import get_pdf_stream
from app.docling_parser import extract_structured

app = FastAPI(title="Docling PDF Form Recognizer (CPU - Simple)")

class ExtractRequest(BaseModel):
    file_uri: str  # e.g., "s3://bucket/file.pdf"

@app.post("/extract")
def extract_pdf(req: ExtractRequest):
    pdf_stream = get_pdf_stream(req.file_uri)
    result = extract_structured(pdf_stream)
    return result










