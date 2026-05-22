"""
pdf/html_sheet.py — Accessible HTML character sheet output.
Generates a single self-contained HTML file (inline CSS, no external deps).
"""
from __future__ import annotations
from html import escape as h
from engine.character import Character
from engine.rules import derive_stats


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
        rows = "".join(
            f'<tr><td>{h(a.name)}</td><td>{_sign(a.hit_bonus)}</td>'
            f'<td>{h(a.damage_dice)}</td><td>{h(a.damage_type)}</td></tr>'
            for a in char.attacks
        )
        attacks_html = (
            '<table aria-label="Attacks">'
            '<thead><tr><th>Weapon</th><th>+Hit</th><th>Damage</th><th>Type</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>'
        )
    else:
        attacks_html = '<p>No attacks recorded.</p>'

    # Equipment
    if char.equipment:
        items = "".join(
            f'<li>{"" if item.quantity == 1 else str(item.quantity) + "× "}'
            f'{h(item.name)}</li>'
            for item in char.equipment
        )
        equipment_html = f'<ul aria-label="Equipment list">{items}</ul>'
    else:
        equipment_html = '<p>No equipment recorded.</p>'

    # Features
    if char.features:
        feat_items = "".join(f'<li>{h(f.name)}</li>' for f in char.features)
        features_html = f'<ul aria-label="Features and traits">{feat_items}</ul>'
    else:
        features_html = '<p>No features recorded.</p>'

    # Magic
    magic_parts = []
    if char.always_available:
        names = ", ".join(h(s.name) for s in char.always_available)
        magic_parts.append(f'<p><strong>Cantrips (always available):</strong> {names}</p>')
    if char.spells:
        names = ", ".join(h(s.name) for s in char.spells)
        magic_parts.append(f'<p><strong>Spells:</strong> {names}</p>')
    if char.spell_attack_bonus:
        magic_parts.append(
            f'<p><strong>Spell Attack Bonus:</strong> {_sign(char.spell_attack_bonus)}'
            f'&nbsp;&nbsp;<strong>Spell Save DC:</strong> {char.spell_save_dc}</p>'
        )
    if char.spell_slots:
        slots = ", ".join(f'Level {k}: {v}' for k, v in sorted(char.spell_slots.items()))
        magic_parts.append(f'<p><strong>Spell Slots:</strong> {slots}</p>')
    magic_section = (
        f'<section class="page-back" aria-labelledby="magic-heading">'
        f'<h2 id="magic-heading">Magic &amp; Special Abilities</h2>'
        + "".join(magic_parts) +
        '</section>'
    ) if magic_parts else ''

    # Proficiencies text
    prof_parts = (char.armor_proficiencies + char.weapon_proficiencies
                  + char.tool_proficiencies + char.languages)
    prof_text = h(", ".join(prof_parts)) if prof_parts else "None listed."

    # Passive scores
    wis_mod = _mod(ab.wisdom)
    int_mod  = _mod(ab.intelligence)
    inv_prof = "Investigation" in char.skill_proficiencies
    ins_prof = "Insight"       in char.skill_proficiencies
    passive_inv = 10 + int_mod + (prof if inv_prof else 0)
    passive_ins = 10 + wis_mod + (prof if ins_prof else 0)

    char_name    = h(char.name)
    player_name  = h(char.player_name or "—")
    char_class   = h(char.char_class.title())
    race         = h(char.race.title() if char.race else "—")
    background   = h(char.background.title() if char.background else "—")

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
        <dt>Player</dt>   <dd>{player_name}</dd>
        <dt>Class</dt>    <dd>{char_class} — Level {char.level}</dd>
        <dt>Species</dt>  <dd>{race}</dd>
        <dt>Background</dt><dd>{background}</dd>
        <dt>Hit Dice</dt> <dd>{char.level}{h(char.hit_dice)}</dd>
        <dt>Prof. Bonus</dt><dd>{_sign(prof)}</dd>
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
      <p>{prof_text}</p>
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

      <h2>Features &amp; Traits</h2>
      {features_html}
    </section>

    {magic_section}
  </main>
</body>
</html>"""
