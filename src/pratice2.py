import json
import torch
from pathlib import Path
from typing import List, Dict, Any
from docling.document_converter import DocumentConverter


# --------------------------
# Helper functions
# --------------------------

def is_heading(block: dict) -> bool:
    """Detects a level 1 heading based on font size, bold, or semantic role."""
    text = (block.get("text") or "").strip()
    if not text:
        return False

    role = str(block.get("role") or block.get("semantic_role") or "").lower()
    if "heading" in role:
        return True

    font_size = block.get("font_size") or block.get("style", {}).get("font_size", 12)
    weight = str(block.get("font_weight") or block.get("style", {}).get("font_weight", "")).lower()

    return (font_size >= 16 or "bold" in weight) and len(text) < 120


def is_subheading(block: dict) -> bool:
    """Detects a level 2 heading."""
    text = (block.get("text") or "").strip()
    if not text:
        return False

    font_size = block.get("font_size") or block.get("style", {}).get("font_size", 12)
    if 13 <= font_size < 16:
        return True

    # Detect things like "1.1 Title"
    first_word = text.split()[0].rstrip(".").replace(")", "")
    if first_word.replace(".", "").isdigit() and len(text) < 100:
        return True
    return False


def extract_points(text: str) -> List[str]:
    """Extract bullet or numbered points from a paragraph."""
    points = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(("-", "•", "*")) or line.split()[0].rstrip(".").isdigit():
            points.append(line)
    return points


def normalize_header(headers: List[str]) -> List[str]:
    return [h.strip().lower() for h in headers if h.strip()]


def merge_tables_across_pages(tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merges tables if headers match (table continues on next page)."""
    merged = []
    used = [False] * len(tables)

    for i, t1 in enumerate(tables):
        if used[i]:
            continue
        cur = {
            "start_page": t1["page"],
            "end_page": t1["page"],
            "rows": t1["rows"].copy()
        }
        used[i] = True

        for j, t2 in enumerate(tables[i + 1:], start=i + 1):
            if used[j]:
                continue
            h1 = normalize_header(t1["rows"][0]) if t1["rows"] else []
            h2 = normalize_header(t2["rows"][0]) if t2["rows"] else []

            # Similar headers -> same table continuation
            if h1 and h2 and (h1 == h2 or len(set(h1).intersection(h2)) / len(h1) > 0.7):
                cur["rows"].extend(t2["rows"][1:])  # skip repeated header
                cur["end_page"] = t2["page"]
                used[j] = True
        merged.append(cur)
    return merged


# --------------------------
# Main PDF extraction logic
# --------------------------

def extract_pdf_structure(pdf_path: str) -> Dict[str, Any]:
    """Extract headings, subheadings, points, paragraphs, and tables from PDF."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🔹 Using device: {device}")

    converter = DocumentConverter()
    print(f"🔹 Processing PDF: {pdf_path}")
    result = converter.convert(pdf_path)
    doc = getattr(result, "document", result)
    doc_dict = doc.to_dict() if hasattr(doc, "to_dict") else doc

    output = {"pages": [], "merged_tables": []}
    all_tables = []

    for page_index, page in enumerate(doc_dict.get("pages", []), start=1):
        page_data = {"page_number": page_index, "structure": [], "tables": []}
        blocks = page.get("blocks", [])

        for block in blocks:
            text = (block.get("text") or "").strip()
            if not text:
                continue

            # ----- Table Handling -----
            if block.get("type") == "table" or block.get("role") == "table":
                rows = []
                if block.get("cells"):
                    for row in block["cells"]:
                        rows.append([
                            c.get("text", "") if isinstance(c, dict) else str(c)
                            for c in row
                        ])
                else:
                    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
                    for ln in lines:
                        rows.append(ln.split())

                table_data = {"page": page_index, "rows": rows}
                page_data["tables"].append(table_data)
                all_tables.append(table_data)
                continue

            # ----- Text Handling -----
            if is_heading(block):
                page_data["structure"].append({"type": "heading", "level": 1, "text": text})
            elif is_subheading(block):
                page_data["structure"].append({"type": "heading", "level": 2, "text": text})
            else:
                pts = extract_points(text)
                if pts:
                    for pt in pts:
                        page_data["structure"].append({"type": "point", "text": pt})
                else:
                    page_data["structure"].append({"type": "paragraph", "text": text})

        output["pages"].append(page_data)

    # Merge tables across pages
    output["merged_tables"] = merge_tables_across_pages(all_tables)
    return output


# --------------------------
# Main entry
# --------------------------

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pdf_extractor_docling.py <pdf_file_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    result = extract_pdf_structure(pdf_path)

    output_json = Path(pdf_path).stem + "_output.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Extraction complete! Output saved to: {output_json}")

