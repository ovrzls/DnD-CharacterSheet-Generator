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
from pypdf import PdfReader, PdfWriter
import pypdf.generic

from engine.character import Character
from engine.rules import derive_stats

_HERE = Path(__file__).parent
SHEET_PDF = _HERE / "field_maps" / "OtG-Revised-Charactersheet.pdf"
FIELD_MAP = _HERE / "field_maps" / "otg_fields.json"

_TEXT_COLOR = HexColor("#1a1a1a")


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
    max_width: float,
    line_height: int,
) -> None:
    words = text.split()
    line: list[str] = []
    cur_y = y
    for word in words:
        test = " ".join(line + [word])
        if c.stringWidth(test, "Helvetica", font_size) <= max_width:
            line.append(word)
        else:
            if line:
                c.drawString(x, cur_y, " ".join(line))
                cur_y -= line_height
            line = [word]
    if line:
        c.drawString(x, cur_y, " ".join(line))


def _draw_text(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    font_size: int = 9,
    align: str = "left",
    max_width: float | None = None,
    multiline: bool = False,
    line_height: int = 11,
) -> None:
    if not text:
        return
    c.setFont("Helvetica", font_size)
    c.setFillColor(_TEXT_COLOR)
    if multiline and max_width:
        _draw_wrapped(c, str(text), x, y, font_size, max_width, line_height)
    elif align == "center":
        c.drawCentredString(x, y, str(text))
    else:
        c.drawString(x, y, str(text))


def _render_page(fields_data: dict, values: dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFillColor(_TEXT_COLOR)

    for field_name, spec in fields_data.items():
        value = values.get(field_name)
        if value is None:
            continue
        _draw_text(
            c,
            text=str(value),
            x=spec["x"],
            y=spec["y"],
            font_size=spec.get("font_size", 9),
            align=spec.get("align", "left"),
            max_width=spec.get("max_width"),
            multiline=spec.get("multiline", False),
            line_height=spec.get("line_height", 11),
        )

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

    # Proficiencies text block
    prof_parts = (
        char.armor_proficiencies
        + char.weapon_proficiencies
        + char.tool_proficiencies
        + char.languages
    )
    proficiencies_text = ", ".join(prof_parts)

    # Equipment list — EquipmentItem has only name/quantity/source, no equipped flag
    inventory_lines = []
    for item in char.equipment:
        line = f"{item.quantity}x {item.name}" if item.quantity > 1 else item.name
        inventory_lines.append(line)
    inventory_text = "\n".join(inventory_lines)

    # Proficiency indicator: ◆ expertise, ● proficient, blank otherwise
    def prof_marker(skill_name: str) -> str:
        if skill_name in char.skill_expertises:
            return "◆"
        if skill_name in char.skill_proficiencies:
            return "●"
        return ""

    page1: dict[str, Any] = {
        "name":       char.name,
        "char_class": char.char_class,
        "level":      str(char.level),
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

        "inventory": inventory_text,
        "money":     "",   # no gold field on Character yet
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

    page2: dict[str, Any] = {
        "initiative":  _sign(char.initiative),
        "armor_class": str(char.armor_class),
        "hit_points":  str(char.max_hp),
        "movement":    f"{char.speed} ft",

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
        page2[f"atk{i}_weapon"] = atk.name
        page2[f"atk{i}_hit"]    = _sign(atk.hit_bonus)
        page2[f"atk{i}_dmg"]    = atk.damage_dice
        page2[f"atk{i}_desc"]   = atk.damage_type

    # Features & Traits
    page2["features_traits"] = "\n".join(f.name for f in char.features)

    # Magic — cantrips + slot spells
    magic_lines = []
    if char.always_available:
        magic_lines.append("Cantrips: " + ", ".join(s.name for s in char.always_available))
    if char.spells:
        magic_lines.append("Spells: " + ", ".join(s.name for s in char.spells))
    if char.spell_attack_bonus:
        magic_lines.append(f"Spell Attack: {_sign(char.spell_attack_bonus)}  Save DC: {char.spell_save_dc}")
    page2["magic_abilities"] = "\n".join(magic_lines)

    return {"page1": page1, "page2": page2}


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

    overlays: list[bytes] = []
    for page_key in ("page1", "page2"):
        overlays.append(_render_page(field_map.get(page_key, {}), values.get(page_key, {})))

    blank  = PdfReader(str(SHEET_PDF))
    writer = PdfWriter()

    for blank_page, overlay_bytes in zip(blank.pages, overlays):
        overlay_page = PdfReader(io.BytesIO(overlay_bytes)).pages[0]
        blank_page.merge_page(overlay_page)
        writer.add_page(blank_page)

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
