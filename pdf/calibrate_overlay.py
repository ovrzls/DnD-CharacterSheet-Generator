"""
pdf/calibrate_overlay.py
Generates a test PDF with labelled dots at every field coordinate so you can
visually verify placement against the actual character sheet.

Usage (from project root):
    python pdf/calibrate_overlay.py

Outputs: pdf/calibration_test.pdf
Open it and check every dot lands on the right box/area.
Then adjust pdf/field_maps/otg_fields.json as needed.
"""

import io
import json
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from pypdf import PdfReader, PdfWriter

HERE      = Path(__file__).parent
SHEET_PDF = HERE / "field_maps" / "OtG-Revised-Charactersheet.pdf"
FIELD_MAP = HERE / "field_maps" / "otg_fields.json"
OUTPUT    = HERE / "calibration_test.pdf"

DOT_COLOR   = HexColor("#e63946")
LABEL_COLOR = HexColor("#1d3557")


def render_calibration_page(fields_data: dict) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    for field_name, spec in fields_data.items():
        if field_name.startswith("_"):
            continue
        x, y = spec["x"], spec["y"]

        c.setFillColor(DOT_COLOR)
        c.circle(x, y, 3, fill=1, stroke=0)

        c.setFillColor(LABEL_COLOR)
        c.setFont("Helvetica", 5)
        c.drawString(x + 4, y - 2, field_name)

    c.save()
    buf.seek(0)
    return buf.read()


def main():
    with open(FIELD_MAP, encoding="utf-8") as f:
        field_map = json.load(f)

    blank  = PdfReader(str(SHEET_PDF))
    writer = PdfWriter()

    for i, page_key in enumerate(["page1", "page2"]):
        fields_data = {k: v for k, v in field_map.get(page_key, {}).items()
                       if not k.startswith("_")}
        overlay_bytes = render_calibration_page(fields_data)
        overlay_page  = PdfReader(io.BytesIO(overlay_bytes)).pages[0]
        blank_page    = blank.pages[i]
        blank_page.merge_page(overlay_page)
        writer.add_page(blank_page)

    with open(OUTPUT, "wb") as f:
        writer.write(f)

    print(f"Calibration PDF written to: {OUTPUT}")
    print("Open it and verify every red dot lands on the correct field.")
    print("Adjust pdf/field_maps/otg_fields.json x/y values as needed, then re-run.")


if __name__ == "__main__":
    main()
