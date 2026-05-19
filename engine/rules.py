"""
Rules engine — derives all stats from a Character's core choices.
PROTO scope: levels 1-5, all 12 SRD classes.

Call derive_stats(character) after setting:
  race, char_class, background, ability_scores, level
It fills in all derived fields in-place and returns the Character.
"""
from __future__ import annotations
from engine.character import Character, AbilityScores

# ── Class data tables ────────────────────────────────────────────────────────

# Classes that use the caster sheet variant
CASTER_CLASSES = {
    "bard", "cleric", "druid", "paladin", "ranger",
    "sorcerer", "warlock", "wizard",
}

# Hit die size per class (integer)
HIT_DIE = {
    "barbarian": 12,
    "fighter":   10,
    "paladin":   10,
    "ranger":    10,
    "bard":       8,
    "cleric":     8,
    "druid":      8,
    "monk":       8,
    "rogue":      8,
    "warlock":    8,
    "sorcerer":   6,
    "wizard":     6,
}

# Saving throw proficiencies per class
SAVING_THROWS = {
    "barbarian": ["constitution", "strength"],
    "bard":      ["charisma", "dexterity"],
    "cleric":    ["charisma", "wisdom"],
    "druid":     ["intelligence", "wisdom"],
    "fighter":   ["constitution", "strength"],
    "monk":      ["dexterity", "strength"],
    "paladin":   ["charisma", "wisdom"],
    "ranger":    ["dexterity", "strength"],
    "rogue":     ["dexterity", "intelligence"],
    "sorcerer":  ["charisma", "constitution"],
    "warlock":   ["charisma", "wisdom"],
    "wizard":    ["intelligence", "wisdom"],
}

# Spellcasting ability per class
SPELLCASTING_ABILITY = {
    "bard":     "charisma",
    "cleric":   "wisdom",
    "druid":    "wisdom",
    "paladin":  "charisma",
    "ranger":   "wisdom",
    "sorcerer": "charisma",
    "warlock":  "charisma",
    "wizard":   "intelligence",
}

# Spell slots by class type and level {level: {slot_level: count}}
# Full casters (wizard, sorcerer, bard, cleric, druid)
FULL_CASTER_SLOTS = {
    1: {1: 2},
    2: {1: 3},
    3: {1: 4, 2: 2},
    4: {1: 4, 2: 3},
    5: {1: 4, 2: 3, 3: 2},
}

# Half casters (paladin, ranger) — gain slots at level 2
HALF_CASTER_SLOTS = {
    1: {},
    2: {1: 2},
    3: {1: 3},
    4: {1: 3},
    5: {1: 4, 2: 2},
}

# Warlocks use Pact Magic (short-rest slots, all same level)
WARLOCK_SLOTS = {
    1: {1: 1},
    2: {1: 2},
    3: {2: 2},
    4: {2: 2},
    5: {3: 2},
}

HALF_CASTERS = {"paladin", "ranger"}
PACT_CASTERS = {"warlock"}

# Proficiency bonus by level
PROFICIENCY_BY_LEVEL = {1: 2, 2: 2, 3: 2, 4: 2, 5: 3}

# All skills and their governing ability
SKILL_ABILITIES = {
    "acrobatics":      "dexterity",
    "animal handling": "wisdom",
    "arcana":          "intelligence",
    "athletics":       "strength",
    "deception":       "charisma",
    "history":         "intelligence",
    "insight":         "wisdom",
    "intimidation":    "charisma",
    "investigation":   "intelligence",
    "medicine":        "wisdom",
    "nature":          "intelligence",
    "perception":      "wisdom",
    "performance":     "charisma",
    "persuasion":      "charisma",
    "religion":        "intelligence",
    "sleight of hand": "dexterity",
    "stealth":         "dexterity",
    "survival":        "wisdom",
}


# ── Public helpers ────────────────────────────────────────────────────────────

def select_sheet_variant(char_class: str) -> str:
    """Auto-select OtG sheet variant based on class. Never shown to player."""
    return "caster" if char_class.lower() in CASTER_CLASSES else "martial"


def proficiency_bonus(level: int) -> int:
    return PROFICIENCY_BY_LEVEL.get(level, 2)


def ability_modifier(score: int) -> int:
    return (score - 10) // 2


def get_spell_slots(char_class: str, level: int) -> dict:
    """Return spell slot dict {slot_level: count} for class at given level."""
    cls = char_class.lower()
    if cls in PACT_CASTERS:
        return dict(WARLOCK_SLOTS.get(level, {}))
    elif cls in HALF_CASTERS:
        return dict(HALF_CASTER_SLOTS.get(level, {}))
    elif cls in CASTER_CLASSES:
        return dict(FULL_CASTER_SLOTS.get(level, {}))
    return {}


def get_hit_die(char_class: str) -> int:
    """Return the hit die size (integer) for a class."""
    return HIT_DIE.get(char_class.lower(), 8)


def calc_max_hp(char_class: str, level: int, con_modifier: int) -> int:
    """
    Calculate max HP using standard rule:
    Level 1: max hit die + CON mod
    Each additional level: average of hit die (rounded up) + CON mod
    Average = (hit_die / 2) + 1
    """
    hit_die = get_hit_die(char_class)
    avg_per_level = (hit_die // 2) + 1
    hp = hit_die + con_modifier                          # level 1: max
    hp += (avg_per_level + con_modifier) * (level - 1)  # levels 2+: average
    return max(1, hp)  # minimum 1 HP


def calc_initiative(dex_modifier: int) -> int:
    return dex_modifier


def calc_passive_perception(wis_modifier: int, prof_bonus: int,
                            has_perception_prof: bool) -> int:
    base = 10 + wis_modifier
    return base + prof_bonus if has_perception_prof else base


def calc_spell_save_dc(spellcasting_mod: int, prof_bonus: int) -> int:
    return 8 + prof_bonus + spellcasting_mod


def calc_spell_attack_bonus(spellcasting_mod: int, prof_bonus: int) -> int:
    return prof_bonus + spellcasting_mod


# ── Main derive function ──────────────────────────────────────────────────────

def derive_stats(character: Character) -> Character:
    """
    Populate all derived fields on a Character from its core choices.
    Mutates character in place AND returns it.

    Requires: char_class, level, ability_scores to be set.
    """
    cls = character.char_class.lower()
    lvl = character.level
    scores = character.ability_scores

    # Ability modifiers
    str_mod = ability_modifier(scores.strength)
    dex_mod = ability_modifier(scores.dexterity)
    con_mod = ability_modifier(scores.constitution)
    int_mod = ability_modifier(scores.intelligence)
    wis_mod = ability_modifier(scores.wisdom)
    cha_mod = ability_modifier(scores.charisma)

    # Sheet variant (auto)
    character.sheet_variant = select_sheet_variant(cls)

    # Proficiency bonus
    prof = proficiency_bonus(lvl)
    character.proficiency_bonus = prof

    # Hit dice string
    character.hit_dice = f"d{get_hit_die(cls)}"

    # Max HP
    character.max_hp = calc_max_hp(cls, lvl, con_mod)
    character.current_hp = character.max_hp

    # Initiative
    character.initiative = calc_initiative(dex_mod)

    # Armor class (base: 10 + DEX — no armor assumed; equipment step adds armor)
    character.armor_class = 10 + dex_mod

    # Speed (default 30 — racial overrides handled in PROTO-1 race step)
    if not character.speed:
        character.speed = 30

    # Saving throw proficiencies
    character.saving_throw_proficiencies = list(
        SAVING_THROWS.get(cls, [])
    )

    # Passive perception
    has_perc = "perception" in [s.lower() for s in character.skill_proficiencies]
    character.passive_perception = calc_passive_perception(wis_mod, prof, has_perc)

    # Spellcasting stats (casters only)
    if character.sheet_variant == "caster":
        spell_ability = SPELLCASTING_ABILITY.get(cls, "intelligence")
        character.spellcasting_ability = spell_ability.capitalize()

        mod_map = {
            "strength": str_mod, "dexterity": dex_mod,
            "constitution": con_mod, "intelligence": int_mod,
            "wisdom": wis_mod, "charisma": cha_mod,
        }
        spell_mod = mod_map.get(spell_ability, int_mod)
        character.spell_save_dc = calc_spell_save_dc(spell_mod, prof)
        character.spell_attack_bonus = calc_spell_attack_bonus(spell_mod, prof)
        character.spell_slots = get_spell_slots(cls, lvl)
    else:
        character.spellcasting_ability = ""
        character.spell_save_dc = 0
        character.spell_attack_bonus = 0
        character.spell_slots = {}

    return character
