"""
pdf/calibrate_overlay.py
Generates a proof PDF of the field map on top of the blank character sheet,
for checking placement by eye or on paper.

Each field in pdf/field_maps/otg_fields.json gets:
  - a crosshair registration mark at its (x, y) anchor — the text baseline
  - a short field-name label (e.g. "acrobatics" for skill_acrobatics)
  - a bar showing max_width, where the field has one
  - a box showing the field's font size (cap height) at the anchor

Each page also gets corner registration marks and a light 36-pt grid with
coordinates in reportlab points (origin bottom-left), the same units as the
field map. The Magic & Special Abilities column guides are drawn from
spell_columns_start and magic_abilities.max_width. Two key pages at the end list
every field with its full name, x, y, size, alignment and width.

Usage (from project root):
    python pdf/calibrate_overlay.py                 # writes pdf/calibration_test.pdf
    python pdf/calibrate_overlay.py proof.pdf       # writes to a path of your choice
    python pdf/calibrate_overlay.py --no-grid       # marks and labels only

Print at 100% / "Actual size" (not "Fit to page"), or the grid will not
measure true points.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Run as a script from the project root: make `pdf.filler` importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pdf.filler import (  # noqa: E402
    FIELD_MAP, SHEET_PDF, _identify_sheet_pages, _load_field_map,
)

HERE   = Path(__file__).parent
OUTPUT = HERE / "calibration_test.pdf"

PAGE_W, PAGE_H = letter

MARK_COLOR   = HexColor("#E6007E")   # registration magenta — stands out on teal and pink
WIDTH_COLOR  = HexColor("#0077CC")
LABEL_COLOR  = HexColor("#111111")
GRID_COLOR   = HexColor("#00A0A0")
GUIDE_COLOR  = HexColor("#FF8C00")

MARK_ARM   = 6.0    # crosshair arm length (pt)
LABEL_SIZE = 4.5
# Field-map entries the renderer does not draw from. The old per-level spell
# fields were replaced by the flow layout, and magic_abilities supplies only
# width and font size (the flow starts at spell_columns_start). They are left
# off the sheet pages so the proof shows only live positions, and are marked
# "not drawn" on the key pages.
def _not_drawn(name: str) -> bool:
    return (name.startswith("spells_level_") or name.startswith("cantrips_")
            or name == "magic_abilities")


PAGE_NAMES = {"page1": "Identity page (page1)", "page2": "Combat page (page2)"}


def _crosshair(c: canvas.Canvas, x: float, y: float, arm: float = MARK_ARM) -> None:
    c.setStrokeColor(MARK_COLOR)
    c.setLineWidth(0.5)
    c.line(x - arm, y, x + arm, y)
    c.line(x, y - arm, x, y + arm)
    c.circle(x, y, arm * 0.45, fill=0, stroke=1)


def _corner_marks(c: canvas.Canvas, inset: float = 18.0) -> None:
    """Registration targets inset from each corner, plus centre marks on each edge."""
    for x, y in [(inset, inset), (PAGE_W - inset, inset),
                 (inset, PAGE_H - inset), (PAGE_W - inset, PAGE_H - inset),
                 (PAGE_W / 2, inset), (PAGE_W / 2, PAGE_H - inset),
                 (inset, PAGE_H / 2), (PAGE_W - inset, PAGE_H / 2)]:
        c.setStrokeColor(HexColor("#000000"))
        c.setLineWidth(0.4)
        c.line(x - 10, y, x + 10, y)
        c.line(x, y - 10, x, y + 10)
        c.circle(x, y, 5, fill=0, stroke=1)


def _grid(c: canvas.Canvas, step: float = 36.0) -> None:
    c.setStrokeColor(GRID_COLOR)
    c.setStrokeAlpha(0.35)
    c.setLineWidth(0.25)
    c.setFont("Helvetica", 4.5)
    c.setFillColor(GRID_COLOR)
    x = step
    while x < PAGE_W:
        c.line(x, 0, x, PAGE_H)
        c.drawString(x + 1, 3, f"{x:g}")
        c.drawString(x + 1, PAGE_H - 8, f"{x:g}")
        x += step
    y = step
    while y < PAGE_H:
        c.line(0, y, PAGE_W, y)
        c.drawString(2, y + 1, f"{y:g}")
        c.drawRightString(PAGE_W - 2, y + 1, f"{y:g}")
        y += step
    c.setStrokeAlpha(1)


def _short_name(name: str) -> str:
    """Label text drawn at the mark; the key pages carry the full name."""
    if name.startswith("skill_prof_"):
        return "prof"
    if name.startswith("save_prof_"):
        return "prof"
    if name.startswith("skill_"):
        return name[len("skill_"):]
    return name


def _label(c: canvas.Canvas, x: float, y: float, text: str,
           backing: float = 0.6, size: float = LABEL_SIZE) -> None:
    """Small label with a translucent white backing so it reads over the artwork."""
    c.setFont("Helvetica", size)
    w = c.stringWidth(text, "Helvetica", size)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFillAlpha(backing)
    c.rect(x - 0.8, y - 1.4, w + 1.6, size + 1.6, fill=1, stroke=0)
    c.setFillAlpha(1)
    c.setFillColor(LABEL_COLOR)
    c.drawString(x, y, text)


def _field_mark(c: canvas.Canvas, name: str, spec: dict) -> None:
    x, y = float(spec["x"]), float(spec["y"])
    size = float(spec.get("font_size", 9))
    align = spec.get("align", "left")
    max_w = spec.get("max_width")

    # Font-size box: one em wide, cap height (~0.7 em) tall, sitting on the baseline.
    box_w = size
    box_x = {"center": x - box_w / 2, "right": x - box_w}.get(align, x)
    c.setStrokeColor(MARK_COLOR)
    c.setLineWidth(0.3)
    c.setDash(1, 1)
    c.rect(box_x, y, box_w, size * 0.7, fill=0, stroke=1)
    c.setDash()

    # max_width bar just under the baseline.
    if max_w:
        start = {"center": x - max_w / 2, "right": x - max_w}.get(align, x)
        c.setStrokeColor(WIDTH_COLOR)
        c.setLineWidth(0.8)
        c.line(start, y - 2, start + max_w, y - 2)
        c.line(start, y - 4, start, y)
        c.line(start + max_w, y - 4, start + max_w, y)

    _crosshair(c, x, y)

    _label(c, x + MARK_ARM + 1.5, y + 2.5, _short_name(name))


def _magic_guides(c: canvas.Canvas, fields: dict) -> None:
    """Column guides for the spell section flow layout."""
    start = fields.get("spell_columns_start")
    magic = fields.get("magic_abilities")
    if not start or not magic:
        return
    x, y = float(start["x"]), float(start["y"])
    max_w = float(magic.get("max_width", 540))
    gap = 8.0
    col_w = (max_w - 3 * gap) / 4
    c.setStrokeColor(GUIDE_COLOR)
    c.setLineWidth(0.4)
    c.setDash(3, 2)
    for i in range(4):
        cx = x + i * (col_w + gap)
        c.rect(cx, y - 80, col_w, 80 + float(magic.get("font_size", 9.5)), fill=0, stroke=1)
    c.setDash()
    _label(c, x, y - 88, f"spell columns: 4 × {col_w:g} pt, gap {gap:g} · "
                          f"flow starts y{y:g}, width {max_w:g}")


def render_calibration_page(fields_data: dict, page_key: str, grid: bool = True) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    if grid:
        _grid(c)
    _corner_marks(c)

    for name, spec in fields_data.items():
        if name.startswith("_") or not isinstance(spec, dict) or "x" not in spec:
            continue
        if _not_drawn(name):
            continue
        if name == "spell_columns_start":
            _crosshair(c, float(spec["x"]), float(spec["y"]))
            _label(c, float(spec["x"]) + MARK_ARM + 1.5, float(spec["y"]) + 2.5,
                   "spell_columns_start")
            continue
        _field_mark(c, name, spec)

    _magic_guides(c, fields_data)

    # Footer legend, on a white strip so it reads over dark artwork
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFillAlpha(0.9)
    c.rect(28, 20, 470, 17, fill=1, stroke=0)
    c.setFillAlpha(1)
    c.setFont("Helvetica-Bold", 6)
    c.setFillColor(LABEL_COLOR)
    c.drawString(30, 30, f"FIELD MAP PROOF — {PAGE_NAMES.get(page_key, page_key)}")
    c.setFont("Helvetica", 5.5)
    c.drawString(30, 23, "Crosshair = text anchor (baseline). Dashed box = font size. "
                         "Blue bar = max_width. Orange = spell column guides. "
                         "Grid every 36 pt (½ in), origin bottom-left. Print at 100%.")
    c.save()
    buf.seek(0)
    return buf.read()


def _field_rows(fields: dict) -> list[list[str]]:
    rows = []
    for name, spec in fields.items():
        if name.startswith("_") or not isinstance(spec, dict) or "x" not in spec:
            continue
        rows.append([
            name, f"{float(spec['x']):g}", f"{float(spec['y']):g}",
            f"{float(spec['font_size']):g}" if "font_size" in spec else "",
            spec.get("align", "left") if "font_size" in spec else "",
            f"{float(spec['max_width']):g}" if spec.get("max_width") else "",
            f"{float(spec['line_height']):g}" if spec.get("multiline") or spec.get("type") == "inventory" else "",
            ", ".join([k for k in ("bold", "multiline") if spec.get(k)]
                      + (["list"] if spec.get("type") == "inventory" else [])
                      + (["not drawn"] if _not_drawn(name) else [])),
        ])
    return sorted(rows, key=lambda r: (-float(r[2]), float(r[1])))   # top to bottom, left to right


def render_key_page(fields: dict, page_key: str) -> bytes:
    """A plain table of every field on one sheet page, top of page first."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    rows = _field_rows(fields)
    head = ["Field", "x", "y", "Size", "Align", "Width", "Line ht", "Other"]
    cols = [36, 196, 236, 276, 316, 366, 411, 461]
    size, lh = 7.0, 9.6
    y = PAGE_H - 48

    def header(y0: float) -> float:
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(LABEL_COLOR)
        c.drawString(36, y0, f"Field map key — {PAGE_NAMES.get(page_key, page_key)}")
        c.setFont("Helvetica", 7)
        c.drawString(36, y0 - 12, "Units are reportlab points (1/72 in), origin bottom-left. "
                                   "Sorted top of page first. Source: pdf/field_maps/otg_fields.json")
        c.drawString(36, y0 - 21, "\u201cnot drawn\u201d = in the field map but not used for placement "
                                   "(old spell fields; magic_abilities gives width and size only).")
        y0 -= 38
        c.setFont("Helvetica-Bold", size)
        for x, h in zip(cols, head):
            c.drawString(x, y0, h)
        c.setStrokeColor(HexColor("#999999"))
        c.setLineWidth(0.4)
        c.line(36, y0 - 3, PAGE_W - 36, y0 - 3)
        return y0 - lh - 2

    y = header(y)
    c.setFont("Helvetica", size)
    for i, row in enumerate(rows):
        if y < 40:
            c.showPage()
            y = header(PAGE_H - 48)
            c.setFont("Helvetica", size)
        if i % 2:
            c.setFillColor(HexColor("#F1F4F4"))
            c.rect(34, y - 2.6, PAGE_W - 68, lh, fill=1, stroke=0)
        c.setFillColor(LABEL_COLOR)
        for x, cell in zip(cols, row):
            c.drawString(x, y, cell)
        y -= lh
    c.save()
    buf.seek(0)
    return buf.read()


def build_proof(output: Path = OUTPUT, grid: bool = True) -> Path:
    field_map = _load_field_map()
    blank = PdfReader(str(SHEET_PDF))
    writer = PdfWriter()
    page_keys = _identify_sheet_pages([pg.extract_text() or "" for pg in blank.pages])

    for blank_page, key in zip(blank.pages, page_keys):
        overlay = PdfReader(io.BytesIO(
            render_calibration_page(field_map.get(key, {}), key, grid))).pages[0]
        page = writer.add_page(blank_page)
        page.merge_page(overlay)

    for key in page_keys:
        for key_page in PdfReader(io.BytesIO(render_key_page(field_map.get(key, {}), key))).pages:
            writer.add_page(key_page)

    writer.add_metadata({"/Title": "OtG character sheet — field map proof", "/Lang": "en"})
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "wb") as f:
        writer.write(f)
    return output


def main(argv: list[str]) -> None:
    grid = "--no-grid" not in argv
    paths = [a for a in argv if not a.startswith("--")]
    out = build_proof(Path(paths[0]) if paths else OUTPUT, grid=grid)
    print(f"Proof PDF written to: {out}")
    print(f"Field map: {FIELD_MAP}")
    print("Print at 100% (Actual size). Check each crosshair sits where its text should start.")


if __name__ == "__main__":
    main(sys.argv[1:])
