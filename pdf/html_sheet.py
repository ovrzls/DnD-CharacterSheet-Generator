"""
pdf/html_sheet.py — Accessible HTML character sheet output.
Generates a single self-contained HTML file (inline CSS, no external deps).
"""
from __future__ import annotations
from html import escape as h
from engine.character import Character
from engine.rules import derive_stats, xp_for_level, BACKGROUND_SKILLS, get_character_features


def _sign(n: int) -> str:
    return f"+{n}" if n >= 0 else str(n)


def _mod(score: int) -> int:
    return (score - 10) // 2


_CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;font-size:16px;line-height:1.6;
     color:#1a1a1a;background:#f0f4f4}
h1{font-size:1.8rem;margin-bottom:.25rem}
h2{font-size:1.15rem;margin:.75rem 0 .4rem;text-transform:uppercase;letter-spacing:.05em}
h3{font-size:1rem;margin:.5rem 0 .25rem}
main{max-width:960px;margin:0 auto;padding:1rem}
section{background:#fff;border-radius:8px;padding:1.25rem 1.5rem;margin-bottom:1.5rem}
dl{display:grid;grid-template-columns:auto 1fr;gap:.2rem .75rem}
dt{font-weight:bold;font-size:.8rem;text-transform:uppercase;letter-spacing:.05em;
   color:#555;align-self:center}
dd{font-size:1rem;margin:0}

/* Page 1 — teal */
.page-front{border-top:5px solid #00696A}
.page-front h2{color:#00696A}
.ability-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.6rem;margin:.5rem 0}
@media(min-width:600px){.ability-grid{grid-template-columns:repeat(6,1fr)}}
.ability-card{border:2px solid #00696A;border-radius:6px;padding:.4rem;text-align:center}
.ability-abbr{font-size:.7rem;font-weight:bold;color:#00696A;text-transform:uppercase}
.ability-score{font-size:1.6rem;font-weight:bold;line-height:1.2}
.ability-mod{font-size:.85rem;color:#444}
.skills-grid{display:grid;grid-template-columns:1fr 1fr;gap:.15rem .75rem}
.skill-row{display:flex;justify-content:space-between;font-size:.9rem;
           padding:.2rem .25rem;border-bottom:1px solid #e8f0f0}
.prof-mark{color:#00696A;font-weight:bold;margin-right:.2rem}

/* Page 2 — pink */
.page-back{border-top:5px solid #D4006A}
.page-back h2{color:#D4006A}
.combat-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:.6rem;margin:.5rem 0}
@media(min-width:500px){.combat-grid{grid-template-columns:repeat(4,1fr)}}
.combat-stat{border:2px solid #D4006A;border-radius:6px;padding:.4rem;text-align:center}
.stat-label{font-size:.7rem;font-weight:bold;text-transform:uppercase;
            letter-spacing:.05em;color:#D4006A}
.stat-big{font-size:1.6rem;font-weight:bold}
.saves-grid{display:grid;grid-template-columns:1fr 1fr;gap:.15rem .75rem}
.save-row{display:flex;justify-content:space-between;font-size:.9rem;
          padding:.2rem .25rem;border-bottom:1px solid #ffe8f2}
.save-mark{color:#D4006A;font-weight:bold;margin-right:.2rem}
table{width:100%;border-collapse:collapse;margin:.4rem 0;font-size:.9rem}
th{background:#D4006A;color:#fff;text-align:left;padding:.35rem .5rem}
td{border-bottom:1px solid #f0d0e0;padding:.35rem .5rem}
tr:nth-child(even) td{background:#fff0f7}
ul{padding-left:1.25rem}
li{margin:.2rem 0;font-size:.95rem}
.inventory-list{list-style:none;padding:0}
.inventory-list li{display:flex;align-items:center;gap:6px;margin-bottom:4px;font-size:.75rem}
.inventory-list input[type="checkbox"]{width:12px;height:12px;accent-color:#00696A;
  flex-shrink:0;background:#E8EAE7}

/* Spell grid */
.spell-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:.6rem;margin-top:.5rem}
@media(min-width:600px){.spell-grid{grid-template-columns:repeat(4,1fr)}}
.spell-col h3{font-size:.85rem;margin-bottom:.2rem}
.slot-row{font-size:.8rem;color:#555;margin-bottom:.2rem}

/* Features list */
.features-list{margin:.4rem 0 0}
.features-list dt{font-weight:500;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;margin-top:.5rem}
.features-list dd{font-size:.7rem;color:#444;margin-left:0;line-height:1.5}

/* Print */
@media print{
  body{background:#fff}
  section{box-shadow:none;page-break-inside:avoid}
  .page-back{page-break-before:always}
}
"""


def generate_html_sheet(char: Character) -> str:
    """Return a self-contained accessible HTML character sheet string."""
    derive_stats(char)

    ab   = char.ability_scores
    prof = char.proficiency_bonus

    ability_data = [
        ("STR", "Strength",     ab.strength),
        ("DEX", "Dexterity",    ab.dexterity),
        ("CON", "Constitution", ab.constitution),
        ("INT", "Intelligence", ab.intelligence),
        ("WIS", "Wisdom",       ab.wisdom),
        ("CHA", "Charisma",     ab.charisma),
    ]

    skill_data = [
        ("Acrobatics",      ab.dexterity),
        ("Animal Handling", ab.wisdom),
        ("Arcana",          ab.intelligence),
        ("Athletics",       ab.strength),
        ("Deception",       ab.charisma),
        ("History",         ab.intelligence),
        ("Insight",         ab.wisdom),
        ("Intimidation",    ab.charisma),
        ("Investigation",   ab.intelligence),
        ("Medicine",        ab.wisdom),
        ("Nature",          ab.intelligence),
        ("Perception",      ab.wisdom),
        ("Performance",     ab.charisma),
        ("Persuasion",      ab.charisma),
        ("Religion",        ab.intelligence),
        ("Sleight of Hand", ab.dexterity),
        ("Stealth",         ab.dexterity),
        ("Survival",        ab.wisdom),
    ]

    save_data = [
        ("Strength",     "strength",     ab.strength),
        ("Dexterity",    "dexterity",    ab.dexterity),
        ("Constitution", "constitution", ab.constitution),
        ("Intelligence", "intelligence", ab.intelligence),
        ("Wisdom",       "wisdom",       ab.wisdom),
        ("Charisma",     "charisma",     ab.charisma),
    ]

    def _skill_row(name: str, base_score: int) -> str:
        base = _mod(base_score)
        nm_lower = name.lower()
        if nm_lower in [s.lower() for s in char.skill_expertises]:
            total = base + 2 * prof
            mark = '<span class="prof-mark" aria-label="Expert">◆</span>'
        elif nm_lower in [s.lower() for s in char.skill_proficiencies]:
            total = base + prof
            mark = '<span class="prof-mark" aria-label="Proficient">●</span>'
        else:
            total = base
            mark = ''
        return (f'<div class="skill-row">'
                f'<span>{mark}{h(name)}</span>'
                f'<span aria-label="{_sign(total)}">{_sign(total)}</span>'
                f'</div>')

    def _save_row(label: str, ability: str, base_score: int) -> str:
        base = _mod(base_score)
        is_prof = ability.lower() in char.saving_throw_proficiencies
        total = base + (prof if is_prof else 0)
        mark = ('<span class="save-mark" aria-label="Proficient">●</span>'
                if is_prof else '')
        return (f'<div class="save-row">'
                f'<span>{mark}{h(label)}</span>'
                f'<span>{_sign(total)}</span>'
                f'</div>')

    # Ability cards
    ability_cards = "".join(
        f'<div class="ability-card">'
        f'<div class="ability-abbr">{abbr}</div>'
        f'<div class="ability-score" aria-label="{name} score {score}">{score}</div>'
        f'<div class="ability-mod" aria-label="modifier {_sign(_mod(score))}">{_sign(_mod(score))}</div>'
        f'</div>'
        for abbr, name, score in ability_data
    )

    # Skills
    skills_html = "".join(_skill_row(name, score) for name, score in skill_data)

    # Saves
    saves_html = "".join(_save_row(label, ability, score)
                         for label, ability, score in save_data)

    # Attacks table
    if char.attacks:
        def _dmg_str(a) -> str:
            dmg_mod = a.hit_bonus - prof
            return a.damage_dice if dmg_mod == 0 else f"{a.damage_dice} {_sign(dmg_mod)}"
        rows = "".join(
            f'<tr><td>{h(a.name)}</td><td>{_sign(a.hit_bonus)}</td>'
            f'<td>{h(_dmg_str(a))}</td><td>{h(a.damage_type)}</td></tr>'
            for a in char.attacks
        )
        attacks_html = (
            '<table aria-label="Attacks">'
            '<thead><tr><th>Weapon</th><th>+Hit</th><th>Damage</th><th>Type</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>'
        )
    else:
        attacks_html = '<p>No attacks recorded.</p>'

    # Equipment — checkbox list for marking items as equipped during play
    if char.equipment:
        items = "".join(
            f'<li>'
            f'<input type="checkbox" aria-label="Mark {h("" if item.quantity == 1 else str(item.quantity) + "× ")}{h(item.name)} as equipped">'
            f'<span>{"" if item.quantity == 1 else str(item.quantity) + "× "}{h(item.name)}</span>'
            f'</li>'
            for item in char.equipment
        )
        equipment_html = f'<ul class="inventory-list" aria-label="Equipment list">{items}</ul>'
    else:
        equipment_html = '<p>No equipment recorded.</p>'

    # Features (class + racial + background with descriptions)
    char_features = get_character_features(char)
    if char_features:
        _feat_dl_rows = "".join(
            f'<dt>{h(name)}</dt><dd>{h(desc)}</dd>'
            for name, desc in char_features
        )
        features_dl = (
            '<h3>Features &amp; Traits</h3>'
            '<dl class="features-list" aria-label="Features and traits">'
            + _feat_dl_rows +
            '</dl>'
        )
    else:
        features_dl = ""

    # Magic — structured spell layout
    def _ordinal_html(n: int) -> str:
        return f"{n}{({1:'st',2:'nd',3:'rd'}).get(n,'th')}"

    if char.sheet_variant == "caster":
        _ab_score_map = {
            "strength": ab.strength, "dexterity": ab.dexterity,
            "constitution": ab.constitution, "intelligence": ab.intelligence,
            "wisdom": ab.wisdom, "charisma": ab.charisma,
        }
        _spell_mod = _mod(_ab_score_map.get((char.spellcasting_ability or "").lower(), 10))
        spell_stats_html = (
            f'<p role="note" aria-label="Spellcasting stats">'
            f'Modifier: {_sign(_spell_mod)} &nbsp;|&nbsp; '
            f'Attack Bonus: {_sign(char.spell_attack_bonus)} &nbsp;|&nbsp; '
            f'Save DC: {char.spell_save_dc}'
            f'</p>'
        )
        # Cantrips column
        _cantrip_items = "".join(f'<li>{h(s.name)}</li>' for s in char.always_available)
        cantrips_col = (
            '<div class="spell-col">'
            '<h3>Cantrips (At Will)</h3>'
            f'<ul>{_cantrip_items if _cantrip_items else "<li>—</li>"}</ul>'
            '</div>'
        )
        # Spell level columns
        spell_level_cols = ""
        for _lvl, _slots in sorted(char.spell_slots.items()):
            if _slots <= 0:
                continue
            _boxes = " ".join("☐" for _ in range(min(int(_slots), 9)))
            _lvl_spells = [s for s in char.spells if s.level == _lvl]
            _items = "".join(f'<li>{h(s.name)}</li>' for s in _lvl_spells)
            spell_level_cols += (
                f'<div class="spell-col" aria-label="{_ordinal_html(_lvl)} level spells">'
                f'<h3>{h(_ordinal_html(_lvl))} Level</h3>'
                f'<p class="slot-row">Slots: {_boxes}</p>'
                f'<ul>{_items if _items else "<li>—</li>"}</ul>'
                '</div>'
            )
        magic_section = (
            '<section class="page-back" aria-labelledby="magic-heading">'
            '<h2 id="magic-heading">Magic &amp; Special Abilities</h2>'
            + spell_stats_html +
            '<div class="spell-grid">'
            + cantrips_col + spell_level_cols +
            '</div>'
            + features_dl +
            '</section>'
        )
    else:
        magic_section = (
            '<section class="page-back" aria-labelledby="magic-heading">'
            '<h2 id="magic-heading">Magic &amp; Special Abilities</h2>'
            '<p>No spellcasting.</p>'
            + features_dl +
            '</section>'
        )

    # Proficiencies — categorized sections
    _prof_rows: list[str] = []
    if char.armor_proficiencies:
        _prof_rows.append(f"<dt>Armor</dt><dd>{h(', '.join(char.armor_proficiencies))}</dd>")
    if char.weapon_proficiencies:
        _prof_rows.append(f"<dt>Weapons</dt><dd>{h(', '.join(char.weapon_proficiencies))}</dd>")
    if char.tool_proficiencies:
        _prof_rows.append(f"<dt>Tools</dt><dd>{h(', '.join(char.tool_proficiencies))}</dd>")
    _bg_key = (char.background or "").lower()
    _bg_skills = BACKGROUND_SKILLS.get(_bg_key, [])
    if _bg_skills:
        _bg_label = h((char.background or "").title())
        _prof_rows.append(f"<dt>Background ({_bg_label})</dt><dd>{h(', '.join(_bg_skills))}</dd>")
    if char.languages:
        _prof_rows.append(f"<dt>Languages</dt><dd>{h(', '.join(char.languages))}</dd>")
    _senses_html = getattr(char, 'senses', None)
    if _senses_html:
        _sv = ', '.join(_senses_html) if isinstance(_senses_html, list) else str(_senses_html)
        _prof_rows.append(f"<dt>Senses</dt><dd>{h(_sv)}</dd>")
    prof_dl = ('<dl aria-label="Proficiencies and languages">' + "".join(_prof_rows) + "</dl>"
               if _prof_rows else "<p>None listed.</p>")

    # Passive scores
    wis_mod = _mod(ab.wisdom)
    int_mod  = _mod(ab.intelligence)
    inv_prof = "Investigation" in char.skill_proficiencies
    ins_prof = "Insight"       in char.skill_proficiencies
    passive_inv = 10 + int_mod + (prof if inv_prof else 0)
    passive_ins = 10 + wis_mod + (prof if ins_prof else 0)

    char_name    = h(char.name)
    char_class   = h(char.char_class.title())
    race         = h(char.race.title() if char.race else "—")
    background   = h(char.background.title() if char.background else "—")
    gold_gp      = getattr(char, "gold", 0)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{char_name} — D&amp;D Character Sheet</title>
  <style>{_CSS}</style>
</head>
<body>
  <main>
    <section class="page-front" aria-labelledby="char-name">
      <h1 id="char-name">{char_name}</h1>

      <dl aria-label="Character identity">
        <dt>Class</dt>    <dd>{char_class} — Level {char.level}</dd>
        <dt>Species</dt>  <dd>{race}</dd>
        <dt>Background</dt><dd>{background}</dd>
        <dt>Hit Dice</dt> <dd>{char.level}{h(char.hit_dice)}</dd>
        <dt>Prof. Bonus</dt><dd>{_sign(prof)}</dd>
        <dt>XP</dt>       <dd>{getattr(char, 'experience_points', None) or xp_for_level(char.level)}</dd>
      </dl>

      <h2>Ability Scores</h2>
      <div class="ability-grid" role="group" aria-label="Ability scores">
        {ability_cards}
      </div>

      <h2>Skills</h2>
      <p style="font-size:.8rem;color:#555;margin-bottom:.4rem">
        ● proficient &nbsp; ◆ expert
      </p>
      <div class="skills-grid" role="list" aria-label="Skill modifiers">
        {skills_html}
      </div>

      <h2>Passive Scores</h2>
      <dl aria-label="Passive scores">
        <dt>Passive Perception</dt>    <dd>{char.passive_perception}</dd>
        <dt>Passive Investigation</dt> <dd>{passive_inv}</dd>
        <dt>Passive Insight</dt>       <dd>{passive_ins}</dd>
      </dl>

      <h2>Proficiencies &amp; Languages</h2>
      {prof_dl}
    </section>

    <section class="page-back" aria-labelledby="combat-heading">
      <h2 id="combat-heading">Combat Statistics</h2>
      <div class="combat-grid" role="group" aria-label="Core combat stats">
        <div class="combat-stat">
          <div class="stat-label">Initiative</div>
          <div class="stat-big">{_sign(char.initiative)}</div>
        </div>
        <div class="combat-stat">
          <div class="stat-label">Armor Class</div>
          <div class="stat-big">{char.armor_class}</div>
        </div>
        <div class="combat-stat">
          <div class="stat-label">Hit Points</div>
          <div class="stat-big">{char.max_hp}</div>
        </div>
        <div class="combat-stat">
          <div class="stat-label">Movement</div>
          <div class="stat-big">{char.speed} ft</div>
        </div>
      </div>

      <h2>Saving Throws</h2>
      <div class="saves-grid" role="list" aria-label="Saving throw modifiers">
        {saves_html}
      </div>

      <h2>Attacks</h2>
      {attacks_html}

      <h2>Equipment</h2>
      {equipment_html}
      <p><strong>Gold:</strong> {gold_gp} gp</p>
    </section>

    {magic_section}
  </main>
</body>
</html>"""
