"""
pdf/filler.py — Milestone 4
Fills the Open the Gates character sheet (non-fillable PDF) by rendering
a text overlay with reportlab and merging it onto each page with pypdf.

Coordinate system: reportlab origin = bottom-left corner.
All x,y values in the field map are in points (1 pt = 1/72 inch).
Page size: 612 x 792 pts (US Letter).
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader, PdfWriter
import pypdf.generic

from engine.character import Character
from engine.rules import derive_stats, xp_for_level, BACKGROUND_SKILLS, get_character_features

_HERE = Path(__file__).parent
SHEET_PDF = _HERE / "field_maps" / "OtG-Revised-Charactersheet.pdf"
FIELD_MAP = _HERE / "field_maps" / "otg_fields.json"

# Sheet typeface. The font files live with the web assets so the wizard and the
# PDF share one copy. If they are missing, fall back to the built-in Helvetica
# so the sheet still renders.
FONT_DIR = _HERE.parent / "ui" / "static" / "fonts" / "barlow-condensed"


def _register_fonts() -> tuple[str, str]:
    """Register Barlow Condensed with reportlab. Returns (regular, bold) font names."""
    regular = FONT_DIR / "BarlowCondensed-Medium.ttf"
    bold = FONT_DIR / "BarlowCondensed-Bold.ttf"
    try:
        pdfmetrics.registerFont(TTFont("BarlowCondensed", str(regular)))
        pdfmetrics.registerFont(TTFont("BarlowCondensed-Bold", str(bold)))
    except Exception:
        return "Helvetica", "Helvetica-Bold"
    return "BarlowCondensed", "BarlowCondensed-Bold"


FONT_REGULAR, FONT_BOLD = _register_fonts()

# Body text size for the Magic & Special Abilities box when the field map
# does not set one (magic_abilities.font_size).
MAGIC_BODY_FONT = 9.5

_DEFAULT_COLOR = HexColor("#1a1a1a")


def _load_field_map() -> dict:
    with open(FIELD_MAP, encoding="utf-8") as f:
        data = json.load(f)
    return {
        page: {k: v for k, v in fields.items() if not k.startswith("_")}
        for page, fields in data.items()
        if not page.startswith("_")
    }


def _sign(n: int | float) -> str:
    return f"+{int(n)}" if n >= 0 else str(int(n))


def _draw_wrapped(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    font_size: int,
    font_name: str,
    max_width: float,
    line_height: int,
    paragraph_spacing: float = 0.0,
) -> float:
    """Draw word-wrapped text. Returns the y coordinate after the last line.

    Each "\n" starts a new paragraph; paragraph_spacing (points) is the extra
    gap left between one paragraph and the next.
    """
    cur_y = y
    for i, paragraph in enumerate(str(text).split("\n")):
        if i > 0:
            cur_y -= paragraph_spacing
        words = paragraph.split()
        if not words:
            cur_y -= line_height
            continue
        line: list[str] = []
        for word in words:
            test = " ".join(line + [word])
            if c.stringWidth(test, font_name, font_size) <= max_width:
                line.append(word)
            else:
                if line:
                    c.drawString(x, cur_y, " ".join(line))
                    cur_y -= line_height
                line = [word]
        if line:
            c.drawString(x, cur_y, " ".join(line))
            cur_y -= line_height
    return cur_y


def _draw_text(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    font_size: float = 9,
    align: str = "left",
    max_width: float | None = None,
    multiline: bool = False,
    line_height: float = 11,
    bold: bool = False,
    color: Any | None = None,
    paragraph_spacing: float = 0.0,
) -> float:
    """Draw text. Returns y after the last drawn line (useful for multiline)."""
    if not text:
        return y
    font_name = FONT_BOLD if bold else FONT_REGULAR
    c.setFont(font_name, font_size)
    c.setFillColor(color if color is not None else _DEFAULT_COLOR)
    if multiline and max_width:
        return _draw_wrapped(c, str(text), x, y, font_size, font_name, max_width,
                             line_height, paragraph_spacing)
    elif align == "center":
        c.drawCentredString(x, y, str(text))
    elif align == "right":
        c.drawRightString(x, y, str(text))
    else:
        c.drawString(x, y, str(text))
    return y


def _draw_inventory_with_checkboxes(
    c: canvas.Canvas,
    items: list,
    x: float,
    y: float,
    font_size: int,
    line_height: int,
    max_width: float | None = None,
) -> None:
    """Draw each item preceded by a small filled checkbox square.

    max_width is the width of the whole row including the checkbox. An item too
    long for one line wraps, with the following lines aligned under its text.
    """
    checkbox_color = HexColor("#E8EAE7")
    stroke_color   = HexColor("#AAAAAA")
    text_color     = HexColor("#1a1a1a")
    checkbox_size  = 8
    gap            = 4

    cur_y = y
    for item_text in items:
        c.setFillColor(checkbox_color)
        c.setStrokeColor(stroke_color)
        c.setLineWidth(0.5)
        c.rect(x, cur_y - 1, checkbox_size, checkbox_size, fill=1, stroke=1)
        c.setFillColor(text_color)
        c.setFont(FONT_REGULAR, font_size)
        text_x = x + checkbox_size + gap
        if max_width:
            cur_y = _draw_wrapped(c, str(item_text), text_x, cur_y, font_size,
                                  FONT_REGULAR, max_width - checkbox_size - gap, line_height)
        else:
            c.drawString(text_x, cur_y, str(item_text))
            cur_y -= line_height


def _spell_effect_summary(sp) -> str:
    """Extract a brief effect summary (≤20 chars) from a SpellEntry."""
    flags = (getattr(sp, "flags", "") or "").split()
    conc = " (C)" if "C" in flags else ""
    effect_dmg = (getattr(sp, "effect_dmg", "") or "").strip()
    if effect_dmg:
        return (effect_dmg[:18 - len(conc)] + conc)[:20]
    return conc.strip()


def _spell_entry_label(name: str, eff: str) -> str:
    """Join spell name and effect; a bare "(C)" flag gets a space, not a dash."""
    if not eff:
        return name
    return f"{name} {eff}" if eff.startswith("(") else f"{name} — {eff}"


def _build_spell_columns(char: Character) -> list[dict]:
    """Return column data for the spell layout (cantrips + one column per slot level)."""
    columns: list[dict] = []
    ordinals = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th"]

    if char.always_available:
        entries = []
        for sp in char.always_available:
            eff = _spell_effect_summary(sp)
            entries.append(_spell_entry_label(sp.name, eff))
        columns.append({"header": "CANTRIPS (AT WILL)", "entries": entries, "slots": 0})

    spells_by_level: dict[int, list] = {}
    for sp in char.spells:
        spells_by_level.setdefault(sp.level, []).append(sp)

    for lvl, slots in sorted(char.spell_slots.items()):
        if slots <= 0:
            continue
        ord_str = ordinals[min(lvl - 1, 8)]
        header = f"{ord_str.upper()} LEVEL"
        entries = []
        for sp in spells_by_level.get(lvl, []):
            eff = _spell_effect_summary(sp)
            entries.append(_spell_entry_label(sp.name, eff))
        columns.append({"header": header, "entries": entries, "slots": slots})

    return columns


def _trunc_to_width(c: canvas.Canvas, text: str, font: str, size: float, max_w: float) -> str:
    """Truncate text with ellipsis to fit within max_w points."""
    if c.stringWidth(text, font, size) <= max_w:
        return text
    while text and c.stringWidth(text.rstrip() + "…", font, size) > max_w:
        text = text[:-1]
    return text.rstrip() + "…"


def _fit_spell_entry(c: canvas.Canvas, entry: str, font: str, size: float, max_w: float) -> str:
    """Fit a "Name — effect" label into a column.

    The spell name matters most, so when the full label is too wide the effect
    is dropped (keeping the concentration flag) before the name is ever cut.
    """
    if c.stringWidth(entry, font, size) <= max_w:
        return entry
    if " — " in entry:
        name, eff = entry.split(" — ", 1)
        short = name + (" (C)" if eff.endswith("(C)") else "")
        if c.stringWidth(short, font, size) <= max_w:
            return short
        entry = short
    return _trunc_to_width(c, entry, font, size, max_w)


def _draw_slot_boxes(c: canvas.Canvas, x: float, y: float, count: int,
                     size: float = 7.0, gap: float = 3.0) -> float:
    """Draw `count` empty slot boxes; returns x after the last box."""
    c.setFillColor(HexColor("#FFFFFF"))
    c.setStrokeColor(HexColor("#1a1a1a"))
    c.setLineWidth(0.5)
    for _ in range(min(count, 9)):
        c.rect(x, y, size, size, fill=1, stroke=1)
        x += size + gap
    return x


def _draw_one_column_row(
    c: canvas.Canvas,
    x: float,
    y: float,
    columns: list[dict],
    col_width: float,
    col_gap: float,
    header_font: float,
    entry_font: float,
) -> float:
    """Draw one row of up to 4 spell columns at (x, y). Returns row height in pts."""
    header_h = header_font + 6.0
    entry_h = entry_font + 2.0
    max_entries = max((len(col["entries"]) for col in columns), default=0)

    for i, col in enumerate(columns):
        cx = x + i * (col_width + col_gap)
        _draw_text(c, col["header"], cx, y, font_size=header_font, bold=True)
        if col["slots"] > 0:
            hdr_w = c.stringWidth(col["header"], FONT_BOLD, header_font)
            _draw_slot_boxes(c, cx + hdr_w + 4, y - 1, col["slots"],
                             size=header_font - 2, gap=2)
        entry_y = y - header_h
        for entry in col["entries"]:
            entry = _fit_spell_entry(c, entry, FONT_REGULAR, entry_font, col_width)
            _draw_text(c, entry, cx, entry_y, font_size=entry_font)
            entry_y -= entry_h

    return header_h + max_entries * entry_h


def _draw_spell_columns_block(
    c: canvas.Canvas,
    x: float,
    y: float,
    columns: list[dict],
    col_width: float = 130.0,
    col_gap: float = 8.0,
    header_font: float = 7.0,
    entry_font: float = 6.5,
) -> float:
    """Draw spell columns 4-per-row, stacking rows downward. Returns total height used."""
    total_height = 0.0
    for row_start in range(0, len(columns), 4):
        row_cols = columns[row_start:row_start + 4]
        row_h = _draw_one_column_row(
            c, x, y - total_height,
            row_cols, col_width, col_gap, header_font, entry_font,
        )
        total_height += row_h + 6.0
    return total_height


def _draw_divider_block(
    c: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    color: str = "#CCCCCC",
    pad: float = 8.0,
) -> float:
    """Draw a horizontal rule at (x, y). Returns height consumed (line + padding)."""
    c.setStrokeColor(HexColor(color))
    c.setLineWidth(0.3)
    c.line(x, y, x + width, y)
    return pad


def _draw_features_block(
    c: canvas.Canvas,
    x: float,
    y: float,
    features: list[tuple[str, str]],
    max_width: float = 540.0,
    font_size: float = 6.0,
    line_height: float = 9.0,
) -> float:
    """Draw feature list (NAME: description) flowing downward. Returns total height used."""
    total_height = 0.0
    for name, desc in features:
        text = f"{name.upper()}: {desc}"
        start_y = y - total_height
        c.setFont(FONT_REGULAR, font_size)
        c.setFillColor(_DEFAULT_COLOR)
        final_y = _draw_wrapped(c, text, x, start_y, font_size, FONT_REGULAR,
                                max_width, line_height)
        total_height += (start_y - final_y) + 2.0
    return total_height


def _draw_spell_section(
    c: canvas.Canvas,
    char: Character,
    magic_spec: dict,
    spell_stats_spec: dict | None = None,
    col_spec: dict | None = None,
) -> None:
    """Draw magic & special abilities using a vertical flow layout."""
    eff = col_spec or magic_spec
    x = float(eff.get("x", 50))
    y = float(eff.get("y", 230))
    max_width = float(magic_spec.get("max_width", 540))
    body = float(magic_spec.get("font_size", MAGIC_BODY_FONT))

    # Spell stats drawn at its own fixed coordinates — outside the flow
    if spell_stats_spec and char.sheet_variant == "caster":
        ab = char.ability_scores
        ab_map = {
            "strength": ab.strength, "dexterity": ab.dexterity,
            "constitution": ab.constitution, "intelligence": ab.intelligence,
            "wisdom": ab.wisdom, "charisma": ab.charisma,
        }
        spell_mod = (ab_map.get((char.spellcasting_ability or "").lower(), 10) - 10) // 2
        stats_text = (
            f"Spell Mod: {_sign(spell_mod)}  |  "
            f"Attack: {_sign(char.spell_attack_bonus)}  |  "
            f"Save DC: {char.spell_save_dc}"
        )
        _draw_text(c, stats_text,
                   float(spell_stats_spec.get("x", x)),
                   float(spell_stats_spec.get("y", y)),
                   font_size=float(spell_stats_spec.get("font_size", 7)))

    cur_y = y

    if char.sheet_variant == "caster":
        columns = _build_spell_columns(char)
        if columns:
            col_gap = 8.0
            col_width = (max_width - 3 * col_gap) / 4
            cur_y -= _draw_spell_columns_block(c, x, cur_y, columns,
                                               col_width=col_width, col_gap=col_gap,
                                               header_font=body, entry_font=body)
    else:
        _draw_text(c, "No spellcasting.", x, cur_y, font_size=body)
        cur_y -= body + 7.0

    features = get_character_features(char)
    if features:
        cur_y -= _draw_divider_block(c, x, cur_y, max_width, pad=body + 4.0)
        _draw_features_block(c, x, cur_y, features, max_width=max_width,
                             font_size=body, line_height=body + 2.0)


def _name_with_pronouns(name: str, pronouns: str) -> str:
    """Combine name and pronouns for the name slot, e.g. "Mira (she/her)"."""
    name = (name or "").strip()
    pronouns = (pronouns or "").strip()
    if not pronouns:
        return name
    return f"{name} ({pronouns})" if name else pronouns


def _fit_single_line(c: canvas.Canvas, text: str, font: str, size: float,
                     max_w: float, min_size: float = 8.0) -> tuple[str, float]:
    """Fit one line into max_w: shrink the font to min_size first, then cut with "…"."""
    while size > min_size and c.stringWidth(text, font, size) > max_w:
        size -= 0.5
    return _trunc_to_width(c, text, font, size, max_w), size


def _render_page(fields_data: dict, values: dict[str, Any],
                 extra_draw=None) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    for field_name, spec in fields_data.items():
        if spec.get("type") == "label":
            # Fixed label: optionally paint over printed artwork, then draw text.
            cover = spec.get("cover")
            if cover:
                c.setFillColor(HexColor(spec.get("cover_color", "#FFFFFF")))
                c.rect(*cover, fill=1, stroke=0)
            _draw_text(
                c, spec.get("text", ""), spec["x"], spec["y"],
                font_size=spec.get("font_size", 9),
                align=spec.get("align", "left"),
                bold=spec.get("bold", False),
                color=HexColor(spec["color"]) if spec.get("color") else None,
            )
            continue
        value = values.get(field_name)
        if value is None:
            continue
        if spec.get("type") == "inventory" and isinstance(value, list):
            if value:
                _draw_inventory_with_checkboxes(
                    c, value,
                    x=spec["x"],
                    y=spec["y"],
                    font_size=spec.get("font_size", 9),
                    line_height=spec.get("line_height", 11),
                    max_width=spec.get("max_width"),
                )
            continue
        raw_color = spec.get("color")
        field_color = HexColor(raw_color) if raw_color else None
        text = str(value)
        font_size = spec.get("font_size", 9)
        if spec.get("max_width") and not spec.get("multiline", False):
            font = FONT_BOLD if spec.get("bold", False) else FONT_REGULAR
            text, font_size = _fit_single_line(c, text, font, font_size, spec["max_width"])
        _draw_text(
            c,
            text=text,
            x=spec["x"],
            y=spec["y"],
            font_size=font_size,
            align=spec.get("align", "left"),
            max_width=spec.get("max_width"),
            multiline=spec.get("multiline", False),
            line_height=spec.get("line_height", 11),
            bold=spec.get("bold", False),
            color=field_color,
            # paragraph_spacing_em is in ems: 1 = one font-size of extra space
            paragraph_spacing=float(spec.get("paragraph_spacing_em", 0)) * font_size,
        )

    if extra_draw is not None:
        extra_draw(c)

    c.save()
    buf.seek(0)
    return buf.read()


def character_to_field_values(char: Character) -> dict[str, dict[str, Any]]:
    """
    Convert a Character (after derive_stats) into field-value dicts for page1 and page2.
    Returns: {"page1": {...}, "page2": {...}}
    """
    ab = char.ability_scores
    scores = {
        "str": ab.strength,
        "dex": ab.dexterity,
        "con": ab.constitution,
        "int": ab.intelligence,
        "wis": ab.wisdom,
        "cha": ab.charisma,
    }

    def mod(score: int) -> int:
        return (score - 10) // 2

    prof = char.proficiency_bonus

    # Skill: proficient gets +prof, expert gets +2*prof
    def skill_total(ability: str, skill_name: str) -> str:
        base = mod(scores[ability])
        if skill_name in char.skill_expertises:
            total = base + 2 * prof
        elif skill_name in char.skill_proficiencies:
            total = base + prof
        else:
            total = base
        return _sign(total)

    skill_map = {
        "skill_acrobatics":      ("dex", "Acrobatics"),
        "skill_animal_handling": ("wis", "Animal Handling"),
        "skill_arcana":          ("int", "Arcana"),
        "skill_athletics":       ("str", "Athletics"),
        "skill_deception":       ("cha", "Deception"),
        "skill_history":         ("int", "History"),
        "skill_insight":         ("wis", "Insight"),
        "skill_intimidation":    ("cha", "Intimidation"),
        "skill_investigation":   ("int", "Investigation"),
        "skill_medicine":        ("wis", "Medicine"),
        "skill_nature":          ("int", "Nature"),
        "skill_perception":      ("wis", "Perception"),
        "skill_performance":     ("cha", "Performance"),
        "skill_persuasion":      ("cha", "Persuasion"),
        "skill_religion":        ("int", "Religion"),
        "skill_sleight_of_hand": ("dex", "Sleight of Hand"),
        "skill_stealth":         ("dex", "Stealth"),
        "skill_survival":        ("wis", "Survival"),
    }

    # Passive scores
    inv_prof = "Investigation" in char.skill_proficiencies
    inv_exp  = "Investigation" in char.skill_expertises
    ins_prof = "Insight" in char.skill_proficiencies
    ins_exp  = "Insight" in char.skill_expertises
    passive_investigation = 10 + mod(scores["int"]) + (2 * prof if inv_exp else prof if inv_prof else 0)
    passive_insight       = 10 + mod(scores["wis"]) + (2 * prof if ins_exp else prof if ins_prof else 0)

    # Proficiencies text block — categorized sections
    _cat: list[str] = []
    if char.armor_proficiencies:
        _cat.append("Armor: " + ", ".join(char.armor_proficiencies))
    if char.weapon_proficiencies:
        _cat.append("Weapons: " + ", ".join(char.weapon_proficiencies))
    if char.tool_proficiencies:
        _cat.append("Tools: " + ", ".join(char.tool_proficiencies))
    _bg_key = (char.background or "").lower()
    _bg_skills = BACKGROUND_SKILLS.get(_bg_key, [])
    if _bg_skills:
        _cat.append(f"Background ({(char.background or '').title()}): " + ", ".join(_bg_skills))
    if char.languages:
        _cat.append("Languages: " + ", ".join(char.languages))
    _senses = getattr(char, 'senses', None)
    if _senses:
        _senses_str = ", ".join(_senses) if isinstance(_senses, list) else str(_senses)
        _cat.append("Senses: " + _senses_str)
    proficiencies_text = "\n".join(_cat)

    # Equipment list — build as a list so _render_page can draw per-item checkboxes
    inventory_items = [
        f"{item.quantity}x {item.name}" if item.quantity > 1 else item.name
        for item in char.equipment
    ]

    # Proficiency indicator: ◆ expertise, ● proficient, blank otherwise
    def prof_marker(skill_name: str) -> str:
        if skill_name in char.skill_expertises:
            return "◆"
        if skill_name in char.skill_proficiencies:
            return "●"
        return ""

    page1: dict[str, Any] = {
        "name":       _name_with_pronouns(char.name, char.pronouns),
        "pronouns":   char.pronouns.strip(),
        "species":    (char.race or "").title(),
        "char_class": char.char_class.title(),
        "level":      str(char.level),
        "xp":         str(getattr(char, "experience_points", None) or xp_for_level(char.level)),
        "inspiration": "✓" if char.inspiration else "",

        "str_score":  str(scores["str"]),
        "str_bonus":  _sign(mod(scores["str"])),
        "dex_score":  str(scores["dex"]),
        "dex_bonus":  _sign(mod(scores["dex"])),
        "con_score":  str(scores["con"]),
        "con_bonus":  _sign(mod(scores["con"])),
        "int_score":  str(scores["int"]),
        "int_bonus":  _sign(mod(scores["int"])),
        "wis_score":  str(scores["wis"]),
        "wis_bonus":  _sign(mod(scores["wis"])),
        "cha_score":  str(scores["cha"]),
        "cha_bonus":  _sign(mod(scores["cha"])),
        "prof_bonus": _sign(prof),

        "passive_perception":    str(char.passive_perception),
        "passive_investigation": str(passive_investigation),
        "passive_insight":       str(passive_insight),

        "proficiencies_text": proficiencies_text,

        "inventory": inventory_items,
        "money":     f"{char.gold} gp",
    }

    for field_name, (ability, skill_name) in skill_map.items():
        page1[field_name] = skill_total(ability, skill_name)
        page1[f"skill_prof_{field_name[len('skill_'):]}"] = prof_marker(skill_name)

    # ---- page 2 ----
    # Saving throws: saving_throw_proficiencies is list of ability names e.g. ["strength","constitution"]
    def save_val(ability_key: str, ability_name: str) -> str:
        base = mod(scores[ability_key])
        bonus = prof if ability_name in char.saving_throw_proficiencies else 0
        return _sign(base + bonus)

    def save_prof_marker(ability_name: str) -> str:
        return "●" if ability_name in char.saving_throw_proficiencies else ""

    # Extra Attack: barbarian/fighter/monk/paladin/ranger get 2 attacks at level 5
    _extra_attack_classes = {"barbarian", "fighter", "monk", "paladin", "ranger"}
    num_attacks = 2 if char.char_class.lower() in _extra_attack_classes and char.level >= 5 else 1

    page2: dict[str, Any] = {
        "initiative":   _sign(char.initiative),
        "armor_class":  str(char.armor_class),
        "hit_points":   str(char.max_hp),
        "movement":     f"{char.speed}ft",
        "num_attacks":  str(num_attacks),

        "save_prof_str": save_prof_marker("strength"),
        "save_str":      save_val("str", "strength"),
        "save_prof_dex": save_prof_marker("dexterity"),
        "save_dex":      save_val("dex", "dexterity"),
        "save_prof_con": save_prof_marker("constitution"),
        "save_con":      save_val("con", "constitution"),
        "save_prof_int": save_prof_marker("intelligence"),
        "save_int":      save_val("int", "intelligence"),
        "save_prof_wis": save_prof_marker("wisdom"),
        "save_wis":      save_val("wis", "wisdom"),
        "save_prof_cha": save_prof_marker("charisma"),
        "save_cha":      save_val("cha", "charisma"),
    }

    # Attacks (char.attacks is a list[Attack] built by equipment step)
    for i, atk in enumerate(char.attacks[:5], start=1):
        dmg_mod = atk.hit_bonus - prof
        dmg_str = atk.damage_dice if dmg_mod == 0 else f"{atk.damage_dice} {_sign(dmg_mod)}"
        page2[f"atk{i}_weapon"] = atk.name
        page2[f"atk{i}_hit"]    = _sign(atk.hit_bonus)
        page2[f"atk{i}_dmg"]    = dmg_str
        page2[f"atk{i}_desc"]   = atk.damage_type

    # Magic & Special Abilities: drawn on canvas via _draw_spell_section() for all characters.

    return {"page1": page1, "page2": page2}


def _identify_sheet_pages(page_texts: list[str]) -> list[str]:
    """Work out which field-map page ("page1" / "page2") each sheet page is.

    The field map calls the identity side (abilities, skills, inventory) "page1"
    and the combat side (saving throws, attacks, magic) "page2". The artwork can
    be exported with its two pages in either order, so match on the printed
    headings instead of trusting the order. Falls back to file order if the
    headings cannot be read.
    """
    default = ["page1", "page2"][:len(page_texts)]
    if len(page_texts) != 2:
        return default

    def is_identity(text: str) -> bool:
        t = text.upper()
        return "SKILLS" in t or "INVENTORY" in t

    def is_combat(text: str) -> bool:
        t = text.upper()
        return "ATTACKS" in t or "SAVING" in t

    first, second = page_texts
    if is_combat(first) and is_identity(second) and not is_identity(first):
        return ["page2", "page1"]
    return default


def fill_otg_sheet(char: Character, output_path: str | Path) -> Path:
    """
    Fill the OtG character sheet PDF for *char* and write to *output_path*.
    Returns the resolved output path.
    """
    if not SHEET_PDF.exists():
        raise FileNotFoundError(
            f"Blank sheet not found at {SHEET_PDF}. "
            "Place OtG-Revised-Charactersheet.pdf in pdf/field_maps/."
        )

    derive_stats(char)

    field_map = _load_field_map()
    values    = character_to_field_values(char)

    magic_spec = field_map.get("page2", {}).get("magic_abilities", {})
    spell_stats_spec = field_map.get("page2", {}).get("spell_stats") or None
    col_spec = field_map.get("page2", {}).get("spell_columns_start") or None
    _char_ref = char

    def page2_extra(c: canvas.Canvas, _c=_char_ref, _s=magic_spec,
                    _ss=spell_stats_spec, _cs=col_spec) -> None:
        _draw_spell_section(c, _c, _s, _ss, _cs)

    overlays: dict[str, bytes] = {
        "page1": _render_page(field_map.get("page1", {}), values.get("page1", {})),
        "page2": _render_page(field_map.get("page2", {}), values.get("page2", {}),
                              extra_draw=page2_extra),
    }

    blank  = PdfReader(str(SHEET_PDF))
    writer = PdfWriter()
    page_keys = _identify_sheet_pages([pg.extract_text() or "" for pg in blank.pages])

    for blank_page, key in zip(blank.pages, page_keys):
        overlay_bytes = overlays[key]
        overlay_page = PdfReader(io.BytesIO(overlay_bytes)).pages[0]
        page = writer.add_page(blank_page)
        page.merge_page(overlay_page)

    # Accessibility metadata
    writer.add_metadata({
        "/Title":   f"{char.name} — D&D Character Sheet",
        "/Subject": "Dungeons & Dragons Character Sheet",
        "/Lang":    "en",
    })
    writer._root_object.update({
        pypdf.generic.NameObject("/MarkInfo"):
            pypdf.generic.ArrayObject([
                pypdf.generic.DictionaryObject({
                    pypdf.generic.NameObject("/Marked"):
                        pypdf.generic.BooleanObject(True)
                })
            ])
    })

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path
