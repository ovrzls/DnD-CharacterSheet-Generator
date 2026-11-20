"""
pdf/field_report.py
Prints every field name and location from otg_fields.json and builds a
printable reference PDF.

Usage (from project root, with .venv active):
    python pdf/field_report.py
    python pdf/field_report.py --json pdf/field_maps/otg_fields.json --sheet pdf/OtG-Revised-Charactersheet.pdf

Outputs:
    Terminal table of all fields
    pdf/field_report.csv          (open in Excel / Numbers)
    pdf/field_reference.pdf       (sheet with labeled markers + coordinate grid,
                                   followed by table pages listing every field)
"""

import argparse
import csv
import io
import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

HERE = Path(__file__).parent
COLUMNS = ["page", "field", "x", "y", "font_size", "align", "type", "max_width", "line_height"]
MARK = HexColor("#e63946")
LABEL = HexColor("#1d3557")
GRID = HexColor("#9aa5b1")


def find_sheet() -> Path:
    for p in sorted(HERE.glob("*.pdf")):
        if "charactersheet" in p.name.lower().replace("-", "").replace("_", ""):
            return p
    raise FileNotFoundError("No character sheet PDF found in pdf/. Pass --sheet.")


def load_rows(json_path: Path) -> list[dict]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    rows = []
    for page, fields in data.items():
        if page.startswith("_") or not isinstance(fields, dict):
            continue
        for name, spec in fields.items():
            if name.startswith("_") or not isinstance(spec, dict):
                continue
            if "x" not in spec or "y" not in spec:
                continue
            row = {"page": page, "field": name}
            for col in COLUMNS[2:]:
                row[col] = spec.get(col, "")
            rows.append(row)
    rows.sort(key=lambda r: (r["page"], -float(r["y"]), float(r["x"])))
    return rows


def print_table(rows: list[dict]) -> None:
    widths = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in COLUMNS}
    header = "  ".join(c.ljust(widths[c]) for c in COLUMNS)
    current = None
    for r in rows:
        if r["page"] != current:
            current = r["page"]
            print(f"\n{current.upper()}  (sorted top-to-bottom, left-to-right)")
            print(header)
            print("-" * len(header))
        print("  ".join(str(r[c]).ljust(widths[c]) for c in COLUMNS))
    print(f"\n{len(rows)} fields total")


def write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)


def overlay_page(rows: list[dict]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter

    # Coordinate grid every 50 pts, labeled, so you can read positions by eye
    c.setStrokeColor(GRID)
    c.setLineWidth(0.25)
    c.setDash(1, 3)
    c.setFont("Helvetica", 5)
    c.setFillColor(GRID)
    for gx in range(0, int(w) + 1, 50):
        c.line(gx, 0, gx, h)
        c.drawString(gx + 1, 3, str(gx))
    for gy in range(0, int(h) + 1, 50):
        c.line(0, gy, w, gy)
        c.drawString(2, gy + 1, str(gy))
    c.setDash()

    for i, r in enumerate(rows):
        x, y = float(r["x"]), float(r["y"])
        c.setStrokeColor(MARK)
        c.setLineWidth(0.6)
        c.line(x - 4, y, x + 4, y)
        c.line(x, y - 4, x, y + 4)
        if r["max_width"] not in ("", None):
            c.setDash(2, 2)
            c.line(x, y - 2, x + float(r["max_width"]), y - 2)
            c.setDash()
        c.setFillColor(LABEL)
        c.setFont("Helvetica", 5)
        dy = 3 if i % 2 == 0 else -6  # alternate above/below to reduce overlap
        c.drawString(x + 5, y + dy, f"{r['field']} ({x:g},{y:g})")
    c.save()
    return buf.getvalue()


def table_pages(rows: list[dict]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter
    cols = [("page", 40), ("field", 200), ("x", 36), ("y", 36), ("font", 34),
            ("align", 44), ("type", 60), ("max_w", 44), ("line_h", 40)]
    keys = ["page", "field", "x", "y", "font_size", "align", "type", "max_width", "line_height"]

    def header(y):
        c.setFont("Helvetica-Bold", 7)
        x = 36
        for label, cw in cols:
            c.drawString(x, y, label)
            x += cw
        c.line(36, y - 3, w - 36, y - 3)
        return y - 12

    c.setFont("Helvetica-Bold", 11)
    c.drawString(36, h - 40, "OtG character sheet — field reference")
    y = header(h - 60)
    for r in rows:
        if y < 40:
            c.showPage()
            y = header(h - 40)
        c.setFont("Helvetica", 7)
        x = 36
        for (label, cw), k in zip(cols, keys):
            c.drawString(x, y, str(r[k])[:42])
            x += cw
        y -= 10
    c.save()
    return buf.getvalue()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(HERE / "field_maps" / "otg_fields.json"))
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--out", default=str(HERE / "field_reference.pdf"))
    args = ap.parse_args()

    rows = load_rows(Path(args.json))
    if not rows:
        raise SystemExit("No positioned fields found in the JSON.")
    print_table(rows)

    csv_path = Path(args.out).with_name("field_report.csv")
    write_csv(rows, csv_path)

    sheet = PdfReader(str(args.sheet or find_sheet()))
    writer = PdfWriter()
    pages = sorted({r["page"] for r in rows})
    for idx, page_key in enumerate(pages):
        if idx >= len(sheet.pages):
            break
        base = sheet.pages[idx]
        base.merge_page(PdfReader(io.BytesIO(
            overlay_page([r for r in rows if r["page"] == page_key]))).pages[0])
        writer.add_page(base)
    for p in PdfReader(io.BytesIO(table_pages(rows))).pages:
        writer.add_page(p)
    with open(args.out, "wb") as f:
        writer.write(f)

    print(f"\nCSV:  {csv_path}")
    print(f"PDF:  {args.out}")


if __name__ == "__main__":
    main()
