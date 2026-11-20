#!/usr/bin/env python3
"""
calibrate_page2.py — Dot markers at every field origin on page 2.

Places a small filled dot + field name at each (x, y) coordinate so you can
see exactly where each output block starts on the printed sheet.

Output: pdf/samples/calibrate_page2.pdf
"""
from pathlib import Path
import io, json

from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader, PdfWriter

HERE      = Path(__file__).parent
SHEET_PDF = HERE / "pdf" / "field_maps" / "OtG-Revised-Charactersheet.pdf"
FIELD_MAP = HERE / "pdf" / "field_maps" / "otg_fields.json"
OUTPUT    = HERE / "pdf" / "samples" / "calibrate_page2.pdf"
FONT_DIR  = HERE / "ui" / "static" / "fonts" / "barlow-condensed"

try:
    pdfmetrics.registerFont(TTFont("BC", str(FONT_DIR / "BarlowCondensed-Medium.ttf")))
    FONT = "BC"
except Exception:
    FONT = "Helvetica"

W, H = 612, 792

fields = json.loads(FIELD_MAP.read_text())["page2"]

buf = io.BytesIO()
c = canvas.Canvas(buf, pagesize=(W, H))

DOT_COLOR   = HexColor("#cc0000")
LABEL_COLOR = HexColor("#000000")
DOT_R       = 2.5
FONT_SIZE   = 6.5

for name, spec in fields.items():
    if name.startswith("_"):
        continue
    x = float(spec.get("x", 0))
    y = float(spec.get("y", 0))

    # dot
    c.setFillColor(DOT_COLOR)
    c.circle(x, y, DOT_R, fill=1, stroke=0)

    # label: name  (x, y)
    c.setFillColor(LABEL_COLOR)
    c.setFont(FONT, FONT_SIZE)
    c.drawString(x + DOT_R + 2, y - FONT_SIZE / 3, f"{name}  ({x:.0f}, {y:.0f})")

c.save()
overlay_bytes = buf.getvalue()

reader  = PdfReader(str(SHEET_PDF))
writer  = PdfWriter()
writer.add_page(reader.pages[0])

overlay_page = PdfReader(io.BytesIO(overlay_bytes)).pages[0]
p2 = writer.add_page(reader.pages[1])
p2.merge_page(overlay_page)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT, "wb") as f:
    writer.write(f)

print(f"→ {OUTPUT}")
