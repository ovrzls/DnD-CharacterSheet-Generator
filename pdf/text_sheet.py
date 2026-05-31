"""
pdf/text_sheet.py — Plain text character sheet output.
Generates an ASCII-art layout using box-drawing characters.
"""
from __future__ import annotations
from engine.character import Character
from engine.rules import derive_stats

W = 66  # page width in characters


def _sign(n: int) -> str:
    return f"+{n}" if n >= 0 else str(n)


def _mod(score: int) -> int:
    return (score - 10) // 2


def _box(lines: list[str]) -> str:
    inner = W - 2
    rows = ["┌" + "─" * inner + "┐"]
    for line in lines:
        line = line[:inner] if len(line) > inner else line
        rows.append("│" + line.ljust(inner) + "│")
    rows.append("└" + "─" * inner + "┘")
    return "\n".join(rows)


def _banner(title: str) -> str:
    inner = W - 2
    title_padded = f"  {title}  "
    return (f"╔{'═' * inner}╗\n"
            f"║{title_padded.center(inner)}║\n"
            f"╚{'═' * inner}╝")


def _section_head(title: str) -> str:
    line = f"  {title.upper()}  "
    filler = "─" * max(0, W - len(line) - 2)
    return f"\n  ╌{'─' * (W - 4)}╌\n  {title.upper()}\n  {'─' * (W - 4)}"


def _two_col(pairs: list[tuple[str, str]]) -> list[str]:
    col = (W - 4) // 2
    out = []
    for i in range(0, len(pairs), 2):
        l_k, l_v = pairs[i]
        r_k, r_v = pairs[i + 1] if i + 1 < len(pairs) else ("", "")
        left  = f"{l_k}: {l_v}"
        right = f"{r_k}: {r_v}" if r_k else ""
        out.append("  " + left.ljust(col) + right)
    return out


def _wrap(text: str, indent: int = 2) -> list[str]:
    """Word-wrap text to page width."""
    pad = " " * indent
    avail = W - indent
    words = text.split()
    lines = []
    cur = ""
    for word in words:
        if cur and len(cur) + 1 + len(word) > avail:
            lines.append(pad + cur)
            cur = word
        else:
            cur = (cur + " " + word).strip()
    if cur:
        lines.append(pad + cur)
    return lines


def generate_text_sheet(char: Character) -> str:
    """Return a plain-text character sheet string."""
    derive_stats(char)

    ab   = char.ability_scores
    prof = char.proficiency_bonus

    def skill_val(name: str, base_score: int) -> str:
        base = _mod(base_score)
        nm = name.lower()
        if nm in [s.lower() for s in char.skill_expertises]:
            return _sign(base + 2 * prof) + " ◆"
        if nm in [s.lower() for s in char.skill_proficiencies]:
            return _sign(base + prof) + " ●"
        return _sign(base)

    def save_val(ability: str, base_score: int) -> str:
        base = _mod(base_score)
        if ability.lower() in char.saving_throw_proficiencies:
            return _sign(base + prof) + " ●"
        return _sign(base)

    lines: list[str] = []

    # ── PAGE 1 ───────────────────────────────────────────────────────────────
    lines.append(_banner(f"{char.name.upper()} — D&D CHARACTER SHEET"))
    lines.append("")

    lines.append(_box([
        f"  NAME:    {char.name:<26} LEVEL: {char.level}",
        f"  CLASS:   {char.char_class.title():<26} HIT DIE: {char.level}{char.hit_dice}",
        f"  SPECIES: {(char.race or '—').title():<26} PROF BONUS: {_sign(prof)}",
        f"  BACKGROUND: {(char.background or '—').title()}",
    ]))
    lines.append("")

    # Ability scores
    lines.append("  ABILITY SCORES")
    col_w = 9
    abbrs  = ["STR",      "DEX",       "CON",           "INT",           "WIS",    "CHA"]
    scores = [ab.strength, ab.dexterity, ab.constitution, ab.intelligence, ab.wisdom, ab.charisma]
    lines.append("  " + "".join(a.center(col_w) for a in abbrs))
    lines.append("  " + "".join(str(s).center(col_w) for s in scores))
    lines.append("  " + "".join(_sign(_mod(s)).center(col_w) for s in scores))
    lines.append("  " + ("─" * col_w * 6))
    lines.append("")

    # Skills
    lines.append("  SKILLS  (● proficient  ◆ expert)")
    skills = [
        ("Acrobatics (DEX)",      skill_val("Acrobatics",      ab.dexterity)),
        ("Medicine (WIS)",        skill_val("Medicine",        ab.wisdom)),
        ("Animal Handling (WIS)", skill_val("Animal Handling", ab.wisdom)),
        ("Nature (INT)",          skill_val("Nature",          ab.intelligence)),
        ("Arcana (INT)",          skill_val("Arcana",          ab.intelligence)),
        ("Perception (WIS)",      skill_val("Perception",      ab.wisdom)),
        ("Athletics (STR)",       skill_val("Athletics",       ab.strength)),
        ("Performance (CHA)",     skill_val("Performance",     ab.charisma)),
        ("Deception (CHA)",       skill_val("Deception",       ab.charisma)),
        ("Persuasion (CHA)",      skill_val("Persuasion",      ab.charisma)),
        ("History (INT)",         skill_val("History",         ab.intelligence)),
        ("Religion (INT)",        skill_val("Religion",        ab.intelligence)),
        ("Insight (WIS)",         skill_val("Insight",         ab.wisdom)),
        ("Sleight of Hand (DEX)", skill_val("Sleight of Hand", ab.dexterity)),
        ("Intimidation (CHA)",    skill_val("Intimidation",    ab.charisma)),
        ("Stealth (DEX)",         skill_val("Stealth",         ab.dexterity)),
        ("Investigation (INT)",   skill_val("Investigation",   ab.intelligence)),
        ("Survival (WIS)",        skill_val("Survival",        ab.wisdom)),
    ]
    col = (W - 4) // 2
    for i in range(0, len(skills), 2):
        lk, lv = skills[i]
        rk, rv = skills[i + 1] if i + 1 < len(skills) else ("", "")
        left  = f"{lk}: {lv}"
        right = f"{rk}: {rv}" if rk else ""
        lines.append("  " + left.ljust(col) + right)
    lines.append("")

    # Passives
    wis_mod = _mod(ab.wisdom)
    int_mod  = _mod(ab.intelligence)
    passive_inv = 10 + int_mod + (prof if "Investigation" in char.skill_proficiencies else 0)
    passive_ins = 10 + wis_mod + (prof if "Insight"       in char.skill_proficiencies else 0)
    lines.append("  PASSIVES")
    lines += _two_col([
        ("Passive Perception",    str(char.passive_perception)),
        ("Passive Investigation", str(passive_inv)),
        ("Passive Insight",       str(passive_ins)),
    ])
    lines.append("")

    # Proficiencies — categorized
    _txt_cats: list[str] = []
    if char.armor_proficiencies:
        _txt_cats += _wrap("Armor: " + ", ".join(char.armor_proficiencies), indent=4)
    if char.weapon_proficiencies:
        _txt_cats += _wrap("Weapons: " + ", ".join(char.weapon_proficiencies), indent=4)
    if char.tool_proficiencies:
        _txt_cats += _wrap("Tools: " + ", ".join(char.tool_proficiencies), indent=4)
    if char.languages:
        _txt_cats += _wrap("Languages: " + ", ".join(char.languages), indent=4)
    _senses_txt = getattr(char, 'senses', None)
    if _senses_txt:
        _sv = ", ".join(_senses_txt) if isinstance(_senses_txt, list) else str(_senses_txt)
        _txt_cats += _wrap("Senses: " + _sv, indent=4)
    if _txt_cats:
        lines.append("  PROFICIENCIES & LANGUAGES")
        lines += _txt_cats
        lines.append("")

    # Inventory
    if char.equipment:
        lines.append("  INVENTORY")
        for item in char.equipment:
            qty = f"{item.quantity}× " if item.quantity > 1 else ""
            lines.append(f"  • {qty}{item.name}")
        gold_val = getattr(char, "gold", 0)
        if gold_val:
            lines.append(f"  Gold: {gold_val} gp")
        lines.append("")

    # ── PAGE 2 ───────────────────────────────────────────────────────────────
    lines.append("═" * W)
    lines.append(f"{'  PAGE 2 — COMBAT & ABILITIES':^{W}}")
    lines.append("═" * W)
    lines.append("")

    lines.append("  COMBAT STATISTICS")
    lines += _two_col([
        ("Initiative", _sign(char.initiative)),
        ("Armor Class", str(char.armor_class)),
        ("Hit Points",  str(char.max_hp)),
        ("Movement",    f"{char.speed} ft"),
    ])
    lines.append("")

    lines.append("  SAVING THROWS  (● proficient)")
    lines += _two_col([
        ("STR", save_val("strength",     ab.strength)),
        ("DEX", save_val("dexterity",    ab.dexterity)),
        ("CON", save_val("constitution", ab.constitution)),
        ("INT", save_val("intelligence", ab.intelligence)),
        ("WIS", save_val("wisdom",       ab.wisdom)),
        ("CHA", save_val("charisma",     ab.charisma)),
    ])
    lines.append("")

    if char.attacks:
        lines.append("  ATTACKS")
        lines.append(f"  {'WEAPON':<22} {'HIT':>4}  {'DAMAGE':<10} TYPE")
        lines.append(f"  {'─'*22} {'─'*4}  {'─'*10} {'─'*12}")
        for atk in char.attacks[:5]:
            name = atk.name[:22]
            dmg_mod = atk.hit_bonus - prof
            dmg_str = atk.damage_dice if dmg_mod == 0 else f"{atk.damage_dice} {_sign(dmg_mod)}"
            lines.append(
                f"  {name:<22} {_sign(atk.hit_bonus):>4}  "
                f"{dmg_str:<10} {atk.damage_type}"
            )
        lines.append("")

    if char.features:
        lines.append("  FEATURES & TRAITS")
        for feat in char.features:
            lines.append(f"  • {feat.name}")
        lines.append("")

    lines.append("  MAGIC & SPECIAL ABILITIES")
    if char.sheet_variant != "caster":
        lines.append("  No spellcasting.")
        if char.features:
            lines.append("  CLASS FEATURES")
            for feat in char.features:
                lines.append(f"  • {feat.name}")
        lines.append("")
    else:
        # Spell stats header
        _ab_score_map_txt = {
            "strength": ab.strength, "dexterity": ab.dexterity,
            "constitution": ab.constitution, "intelligence": ab.intelligence,
            "wisdom": ab.wisdom, "charisma": ab.charisma,
        }
        _spell_mod_txt = _mod(_ab_score_map_txt.get((char.spellcasting_ability or "").lower(), 10))
        lines.append(
            f"  Modifier: {_sign(_spell_mod_txt)}  |  "
            f"Attack Bonus: {_sign(char.spell_attack_bonus)}  |  "
            f"Save DC: {char.spell_save_dc}"
        )
        lines.append("")

        # Build 4-column layout: cantrips | lvl1 | lvl2 | lvl3 (etc.)
        COL_W = 22
        INDENT = "  "

        def _ordinal_txt(n: int) -> str:
            return f"{n}{({1:'st',2:'nd',3:'rd'}).get(n,'th')}"

        # Collect columns: each is (header_line, [spell_names])
        _cols: list[tuple[str, list[str]]] = []

        # Cantrips
        _cantrip_names = [s.name for s in char.always_available]
        _cols.append(("CANTRIPS (AT WILL)", _cantrip_names))

        # Spell levels
        for _lvl, _slots in sorted(char.spell_slots.items()):
            if _slots <= 0:
                continue
            _boxes = " ".join("[ ]" for _ in range(min(int(_slots), 9)))
            _hdr = f"{_ordinal_txt(_lvl).upper()} LEVEL {_boxes}"
            _level_spells = [s.name for s in char.spells if s.level == _lvl]
            _cols.append((_hdr, _level_spells))

        # Render columns in rows of 4
        for _row_start in range(0, len(_cols), 4):
            _row_cols = _cols[_row_start:_row_start + 4]
            # Header row
            hdr_line = INDENT + "".join(
                _col_hdr.ljust(COL_W) for _col_hdr, _ in _row_cols
            )
            lines.append(hdr_line)
            # Spell rows
            _max_spells = max((len(_sp) for _, _sp in _row_cols), default=0)
            for _si in range(_max_spells):
                row_line = INDENT + "".join(
                    (_sp[_si] if _si < len(_sp) else "").ljust(COL_W)
                    for _, _sp in _row_cols
                )
                lines.append(row_line)
            lines.append("")

    lines.append("─" * W)
    lines.append("  Generated by Open the Gates Character Generator")

    return "\n".join(lines)
