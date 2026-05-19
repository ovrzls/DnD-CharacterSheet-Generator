"""
Rules engine — derives stats from Character choices.
Implements: HP, AC, modifiers, proficiency bonus, spell slots, sheet variant.
PROTO scope: levels 1-5, core classes only (expanded via Open5e).
"""
# TODO (PROTO-2): implement derive_stats(character) -> Character

CASTER_CLASSES = {
    # Full casters -> caster sheet
    "wizard", "sorcerer", "bard", "cleric", "druid",
    # Half-casters use caster sheet at level 3+; prototype treats as caster
    "paladin", "ranger",
    # Warlocks use caster sheet
    "warlock",
}

PROFICIENCY_BY_LEVEL = {
    1: 2, 2: 2, 3: 2, 4: 2,
    5: 3, 6: 3, 7: 3, 8: 3,
    9: 4, 10: 4, 11: 4, 12: 4,
}

HIT_DICE = {
    "barbarian": "d12",
    "fighter": "d10", "paladin": "d10", "ranger": "d10",
    "bard": "d8", "cleric": "d8", "druid": "d8",
    "monk": "d8", "rogue": "d8", "warlock": "d8",
    "sorcerer": "d6", "wizard": "d6",
}


def select_sheet_variant(char_class: str) -> str:
    """Auto-select OtG sheet variant. Players never see this choice."""
    return "caster" if char_class.lower() in CASTER_CLASSES else "martial"


def proficiency_bonus(level: int) -> int:
    return PROFICIENCY_BY_LEVEL.get(level, 2)


def derive_stats(character):
    """
    Populate all derived fields on a Character from its core choices.
    Called after race/class/background/scores/level are set.
    Returns the mutated Character (also mutates in place).
    """
    raise NotImplementedError("derive_stats not yet implemented — PROTO-2 task")
