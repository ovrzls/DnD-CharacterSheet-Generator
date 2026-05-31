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
from engine.rules import derive_stats, xp_for_level

_HERE = Path(__file__).parent
SHEET_PDF = _HERE / "field_maps" / "OtG-Revised-Charactersheet.pdf"
FIELD_MAP = _HERE / "field_maps" / "otg_fields.json"

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
) -> None:
    cur_y = y
    for paragraph in str(text).split("\n"):
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
    bold: bool = False,
    color: Any | None = None,
) -> None:
    if not text:
        return
    font_name = "Helvetica-Bold" if bold else "Helvetica"
    c.setFont(font_name, font_size)
    c.setFillColor(color if color is not None else _DEFAULT_COLOR)
    if multiline and max_width:
        _draw_wrapped(c, str(text), x, y, font_size, font_name, max_width, line_height)
    elif align == "center":
        c.drawCentredString(x, y, str(text))
    elif align == "right":
        c.drawRightString(x, y, str(text))
    else:
        c.drawString(x, y, str(text))


def _render_page(fields_data: dict, values: dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    for field_name, spec in fields_data.items():
        value = values.get(field_name)
        if value is None:
            continue
        raw_color = spec.get("color")
        field_color = HexColor(raw_color) if raw_color else None
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
            bold=spec.get("bold", False),
            color=field_color,
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

    # Proficiencies text block — categorized
    _cat: list[str] = []
    if char.armor_proficiencies:
        _cat.append("Armor: " + ", ".join(char.armor_proficiencies))
    if char.weapon_proficiencies:
        _cat.append("Weapons: " + ", ".join(char.weapon_proficiencies))
    if char.tool_proficiencies:
        _cat.append("Tools: " + ", ".join(char.tool_proficiencies))
    if char.languages:
        _cat.append("Languages: " + ", ".join(char.languages))
    _senses = getattr(char, 'senses', None)
    if _senses:
        _senses_str = ", ".join(_senses) if isinstance(_senses, list) else str(_senses)
        _cat.append("Senses: " + _senses_str)
    proficiencies_text = "\n".join(_cat)

    # Equipment list — EquipmentItem has only name/quantity/source, no equipped flag
    inventory_lines = []
    for item in char.equipment:
        qty = f"{item.quantity}x " if item.quantity > 1 else ""
        inventory_lines.append(f"• {qty}{item.name}")
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
        "pronouns":   char.pronouns.strip(),
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

        "inventory": inventory_text,
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

    # Features & Traits
    page2["features_traits"] = "\n".join(f.name for f in char.features)

    # Magic & Special Abilities — spells added for casters
    def _ordinal(n: int) -> str:
        return f"{n}{({1:'st',2:'nd',3:'rd'}).get(n,'th')}"

    if char.sheet_variant != "caster":
        page2["magic_abilities"] = "No spellcasting"
    else:
        ab_score_map = {
            "strength": scores["str"], "dexterity": scores["dex"],
            "constitution": scores["con"], "intelligence": scores["int"],
            "wisdom": scores["wis"], "charisma": scores["cha"],
        }
        _spell_ability = (char.spellcasting_ability or "").lower()
        _spell_mod = mod(ab_score_map.get(_spell_ability, 10))
        page2["spell_stats"] = (
            f"Modifier: {_sign(_spell_mod)}  |  "
            f"Attack Bonus: {_sign(char.spell_attack_bonus)}  |  "
            f"Save DC: {char.spell_save_dc}"
        )
        page2["cantrips_header"] = "Cantrips (At Will)"
        page2["cantrips_list"] = "\n".join(
            s.name for s in char.always_available
        ) if char.always_available else ""

        for _lvl, _slots in sorted(char.spell_slots.items()):
            if _slots <= 0:
                continue
            _boxes = " ".join("[ ]" for _ in range(min(int(_slots), 9)))
            page2[f"spells_level_{_lvl}_header"] = f"{_ordinal(_lvl)} Level  {_boxes}"
            page2[f"spells_level_{_lvl}_list"] = "\n".join(
                s.name for s in char.spells if s.level == _lvl
            )

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
