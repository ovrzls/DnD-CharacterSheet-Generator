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

# Standard D&D 5e XP thresholds (minimum XP per level)
XP_THRESHOLDS: dict[int, int] = {
    1:       0,
    2:     300,
    3:     900,
    4:   2_700,
    5:   6_500,
    6:  14_000,
    7:  23_000,
    8:  34_000,
    9:  48_000,
    10: 64_000,
    11: 85_000,
    12: 100_000,
    13: 120_000,
    14: 140_000,
    15: 165_000,
    16: 195_000,
    17: 225_000,
    18: 265_000,
    19: 305_000,
    20: 355_000,
}


def xp_for_level(level: int) -> int:
    """Return minimum XP needed to reach the given level."""
    return XP_THRESHOLDS.get(max(1, min(20, level)), 0)

# Starting gold (GP) per class — PHB average
STARTING_GOLD: dict[str, int] = {
    "barbarian": 25,
    "bard":      125,
    "cleric":    125,
    "druid":     25,
    "fighter":   125,
    "monk":      12,
    "paladin":   125,
    "ranger":    125,
    "rogue":     100,
    "sorcerer":  75,
    "warlock":   100,
    "wizard":    100,
}

# Armor proficiencies per class
CLASS_ARMOR_PROFICIENCIES: dict[str, list[str]] = {
    "barbarian": ["Light armor", "Medium armor", "Shields"],
    "bard":      ["Light armor"],
    "cleric":    ["Light armor", "Medium armor", "Shields"],
    "druid":     ["Light armor", "Medium armor", "Shields"],
    "fighter":   ["Light armor", "Medium armor", "Heavy armor", "Shields"],
    "monk":      [],
    "paladin":   ["Light armor", "Medium armor", "Heavy armor", "Shields"],
    "ranger":    ["Light armor", "Medium armor", "Shields"],
    "rogue":     ["Light armor"],
    "sorcerer":  [],
    "warlock":   ["Light armor"],
    "wizard":    [],
}

# Weapon proficiencies per class
CLASS_WEAPON_PROFICIENCIES: dict[str, list[str]] = {
    "barbarian": ["Simple weapons", "Martial weapons"],
    "bard":      ["Simple weapons", "Hand crossbows", "Longswords", "Rapiers", "Shortswords"],
    "cleric":    ["Simple weapons"],
    "druid":     ["Clubs", "Daggers", "Javelins", "Maces", "Quarterstaffs", "Scimitars", "Slings", "Spears"],
    "fighter":   ["Simple weapons", "Martial weapons"],
    "monk":      ["Simple weapons", "Shortswords"],
    "paladin":   ["Simple weapons", "Martial weapons"],
    "ranger":    ["Simple weapons", "Martial weapons"],
    "rogue":     ["Simple weapons", "Hand crossbows", "Longswords", "Rapiers", "Shortswords"],
    "sorcerer":  ["Daggers", "Darts", "Slings", "Quarterstaffs", "Light crossbows"],
    "warlock":   ["Simple weapons"],
    "wizard":    ["Daggers", "Darts", "Slings", "Quarterstaffs", "Light crossbows"],
}

# Tool proficiencies per class
CLASS_TOOL_PROFICIENCIES: dict[str, list[str]] = {
    "barbarian": [],
    "bard":      ["Three musical instruments of your choice"],
    "cleric":    [],
    "druid":     ["Herbalism kit"],
    "fighter":   [],
    "monk":      ["One artisan's tool or musical instrument"],
    "paladin":   [],
    "ranger":    [],
    "rogue":     ["Thieves' tools"],
    "sorcerer":  [],
    "warlock":   [],
    "wizard":    [],
}

# Languages granted by background
BACKGROUND_LANGUAGES: dict[str, list[str]] = {
    "acolyte":       ["Two of your choice"],
    "charlatan":     [],
    "criminal":      [],
    "entertainer":   [],
    "folk hero":     [],
    "guild artisan": ["One of your choice"],
    "hermit":        ["One of your choice"],
    "noble":         ["One of your choice"],
    "outlander":     ["One of your choice"],
    "sage":          ["Two of your choice"],
    "sailor":        [],
    "soldier":       [],
    "spy":           [],
    "urchin":        [],
    "haunted one":   ["Two exotic languages of your choice"],
    "far traveler":  ["One of your choice"],
    "city watch":    ["Two of your choice"],
    "mercenary veteran": [],
    "urban bounty hunter": [],
    "uthgardt tribe member": ["One of your choice"],
}

# Class features by level (name only — sheet is quick-reference)
CLASS_FEATURES: dict[str, dict[int, list[str]]] = {
    "barbarian": {
        1: ["Rage (2/long rest)", "Unarmored Defense (CON)"],
        2: ["Reckless Attack", "Danger Sense"],
        3: ["Primal Path"],
        4: ["Ability Score Improvement"],
        5: ["Extra Attack", "Fast Movement"],
    },
    "bard": {
        1: ["Bardic Inspiration (d6)", "Spellcasting"],
        2: ["Jack of All Trades", "Song of Rest (d6)"],
        3: ["Bard College", "Expertise"],
        4: ["Ability Score Improvement"],
        5: ["Bardic Inspiration (d8)", "Font of Inspiration"],
    },
    "cleric": {
        1: ["Spellcasting", "Divine Domain"],
        2: ["Channel Divinity (1/rest)", "Divine Domain Feature"],
        3: [],
        4: ["Ability Score Improvement"],
        5: ["Destroy Undead (CR 1/2)"],
    },
    "druid": {
        1: ["Druidic", "Spellcasting"],
        2: ["Wild Shape (CR 1/4)", "Druid Circle"],
        3: [],
        4: ["Ability Score Improvement", "Wild Shape (CR 1/2)"],
        5: ["Wild Shape (CR 1)"],
    },
    "fighter": {
        1: ["Fighting Style", "Second Wind"],
        2: ["Action Surge (1/rest)"],
        3: ["Martial Archetype"],
        4: ["Ability Score Improvement"],
        5: ["Extra Attack"],
    },
    "monk": {
        1: ["Unarmored Defense (WIS)", "Martial Arts"],
        2: ["Ki (2 points/short rest)", "Unarmored Movement", "Flurry of Blows", "Patient Defense", "Step of the Wind"],
        3: ["Monastic Tradition", "Deflect Missiles"],
        4: ["Ability Score Improvement", "Slow Fall"],
        5: ["Extra Attack", "Stunning Strike"],
    },
    "paladin": {
        1: ["Divine Sense", "Lay on Hands (5 HP/long rest)"],
        2: ["Fighting Style", "Spellcasting", "Divine Smite"],
        3: ["Sacred Oath", "Divine Health"],
        4: ["Ability Score Improvement"],
        5: ["Extra Attack"],
    },
    "ranger": {
        1: ["Favored Enemy", "Natural Explorer"],
        2: ["Fighting Style", "Spellcasting"],
        3: ["Ranger Archetype", "Primeval Awareness"],
        4: ["Ability Score Improvement"],
        5: ["Extra Attack"],
    },
    "rogue": {
        1: ["Expertise", "Sneak Attack (1d6)", "Thieves' Cant"],
        2: ["Cunning Action"],
        3: ["Roguish Archetype", "Sneak Attack (2d6)"],
        4: ["Ability Score Improvement"],
        5: ["Uncanny Dodge", "Sneak Attack (3d6)"],
    },
    "sorcerer": {
        1: ["Spellcasting", "Sorcerous Origin"],
        2: ["Font of Magic", "Sorcery Points (2)"],
        3: ["Metamagic (2 options)", "Sorcery Points (3)"],
        4: ["Ability Score Improvement", "Sorcery Points (4)"],
        5: ["Sorcery Points (5)"],
    },
    "warlock": {
        1: ["Otherworldly Patron", "Pact Magic", "Eldritch Invocations (1)"],
        2: ["Eldritch Invocations (2)"],
        3: ["Pact Boon", "Eldritch Invocations (2)"],
        4: ["Ability Score Improvement"],
        5: ["Eldritch Invocations (3)"],
    },
    "wizard": {
        1: ["Spellcasting", "Arcane Recovery"],
        2: ["Arcane Tradition"],
        3: [],
        4: ["Ability Score Improvement"],
        5: [],
    },
}

# Class features with short descriptions for sheet output.
# Tuple: (min_level, name, description).
# Description may be a plain str or Callable[[int], str] for level-scaled text.
CLASS_FEATURE_DETAILS = {
    "barbarian": [
        (1, "Rage",
         lambda lvl: (
             f"Advantage on STR checks/saves, +2 damage, resistance to physical damage. "
             f"{max(2, min(6, lvl // 4 * 2 + 2))} rages/long rest."
         )),
        (2, "Reckless Attack",
         "Advantage on first STR attack, attackers have advantage against you until your next turn."),
        (3, "Danger Sense",
         "Advantage on DEX saves against visible effects."),
    ],
    "bard": [
        (1, "Bardic Inspiration",
         "Give a creature a d6 to add to one ability check, attack, or save. CHA mod uses/rest."),
        (2, "Jack of All Trades",
         "Add half proficiency to ability checks you are not proficient in."),
        (3, "Expertise",
         "Double proficiency on two chosen skills."),
    ],
    "cleric": [
        (1, "Divine Domain",
         "Chosen domain grants bonus spells and features."),
        (2, "Channel Divinity",
         "Turn Undead or domain effect once/short rest."),
    ],
    "druid": [
        (1, "Druidic",
         "Secret language known only to druids."),
        (2, "Wild Shape",
         "Transform into a beast you have seen. CR 1/4 (no swim/fly) at level 2."),
    ],
    "fighter": [
        (1, "Fighting Style",
         "Chosen combat style grants a passive bonus."),
        (1, "Second Wind",
         "Bonus action: regain 1d10 + level HP once/rest."),
        (2, "Action Surge",
         "Take one additional action once/rest."),
        (3, "Martial Archetype",
         "Chosen archetype grants subclass features."),
    ],
    "monk": [
        (1, "Unarmored Defense",
         "AC = 10 + DEX mod + WIS mod without armor."),
        (1, "Martial Arts",
         "Use DEX for monk weapons, bonus unarmed strike."),
        (2, "Ki",
         lambda lvl: (
             f"Spend ki points for Flurry, Patient Defense, or Step of the Wind. {lvl} ki points."
         )),
        (3, "Deflect Missiles",
         "Reduce ranged hit damage by 1d10 + DEX mod + level."),
    ],
    "paladin": [
        (1, "Divine Sense",
         "Detect celestials, fiends, undead within 60 ft. 1 + CHA mod uses/long rest."),
        (1, "Lay on Hands",
         lambda lvl: f"Healing pool of {lvl * 5} HP. Cure disease/poison for 5 HP."),
        (2, "Fighting Style",
         "Chosen combat style grants a passive bonus."),
        (2, "Divine Smite",
         "Expend spell slot on hit: +2d8 radiant per slot level (max 5d8). +1d8 vs undead/fiends."),
        (3, "Sacred Oath",
         "Chosen oath grants Channel Divinity options and bonus spells."),
    ],
    "ranger": [
        (1, "Favored Enemy",
         "Advantage to track, recall info, learn language of chosen enemy type."),
        (1, "Natural Explorer",
         "Chosen terrain grants travel and tracking benefits."),
        (2, "Fighting Style",
         "Chosen combat style grants a passive bonus."),
        (3, "Primeval Awareness",
         "Expend spell slot to sense enemy types within 1 mile (6 miles in favored terrain)."),
    ],
    "rogue": [
        (1, "Expertise",
         "Double proficiency on two chosen skills."),
        (1, "Sneak Attack",
         lambda lvl: (
             f"{(lvl + 1) // 2}d6 extra damage when you have advantage "
             f"or an ally is adjacent to target."
         )),
        (1, "Thieves' Cant",
         "Secret rogue language and signs."),
        (2, "Cunning Action",
         "Bonus action: Dash, Disengage, or Hide."),
        (3, "Roguish Archetype",
         "Chosen archetype grants subclass features."),
    ],
    "sorcerer": [
        (1, "Sorcerous Origin",
         "Chosen origin grants bonus spells and features."),
        (2, "Font of Magic",
         lambda lvl: (
             f"{lvl * 2} sorcery points. Convert to spell slots or fuel metamagic."
         )),
        (3, "Metamagic",
         "Choose 2 metamagic options to modify spells."),
    ],
    "warlock": [
        (1, "Otherworldly Patron",
         "Patron grants expanded spell list and features."),
        (1, "Pact Magic",
         lambda lvl: (
             f"{min(2, 1 + lvl // 2)} spell slot(s), always highest level. Regain on short rest."
         )),
        (2, "Eldritch Invocations",
         lambda lvl: f"Choose {(lvl + 1) // 2} invocations for permanent magical abilities."),
    ],
    "wizard": [
        (1, "Spellbook",
         "Contains your spells. Add 2 spells per level plus found scrolls."),
        (1, "Arcane Recovery",
         lambda lvl: (
             f"Once/day after short rest: recover spell slots totaling up to "
             f"{(lvl + 1) // 2} levels (max 5th level)."
         )),
        (2, "Arcane Tradition",
         "Chosen tradition grants subclass features."),
    ],
}

# Racial features: {race_lower: [(name, description), ...]}
RACIAL_FEATURES = {
    "elf": [
        ("Darkvision", "See in dim light 60 ft as bright, darkness as dim."),
        ("Fey Ancestry", "Advantage vs charm, immune to magic sleep."),
        ("Trance", "4 hours meditative rest equals 8 hours sleep."),
    ],
    "high elf": [
        ("Darkvision", "See in dim light 60 ft as bright, darkness as dim."),
        ("Fey Ancestry", "Advantage vs charm, immune to magic sleep."),
        ("Cantrip", "Know one wizard cantrip of your choice."),
    ],
    "wood elf": [
        ("Darkvision", "See in dim light 60 ft as bright, darkness as dim."),
        ("Fey Ancestry", "Advantage vs charm, immune to magic sleep."),
        ("Mask of the Wild", "Hide when lightly obscured by natural phenomena."),
    ],
    "dark elf": [
        ("Superior Darkvision", "See in dim light 120 ft as bright, darkness as dim."),
        ("Fey Ancestry", "Advantage vs charm, immune to magic sleep."),
        ("Sunlight Sensitivity", "Disadvantage on attack rolls and Perception in direct sunlight."),
    ],
    "dwarf": [
        ("Darkvision", "See in dim light 60 ft as bright, darkness as dim."),
        ("Dwarven Resilience", "Advantage on saves vs poison, resistance to poison damage."),
        ("Stonecunning", "Double proficiency on History checks related to stonework."),
    ],
    "hill dwarf": [
        ("Darkvision", "See in dim light 60 ft as bright, darkness as dim."),
        ("Dwarven Resilience", "Advantage on saves vs poison, resistance to poison damage."),
        ("Dwarven Toughness", "+1 HP per level."),
    ],
    "mountain dwarf": [
        ("Darkvision", "See in dim light 60 ft as bright, darkness as dim."),
        ("Dwarven Resilience", "Advantage on saves vs poison, resistance to poison damage."),
        ("Dwarven Armor Training", "Proficiency with light and medium armor."),
    ],
    "halfling": [
        ("Lucky", "Reroll 1s on attack rolls, ability checks, or saves."),
        ("Brave", "Advantage on saves vs being frightened."),
        ("Halfling Nimbleness", "Move through the space of any creature larger than you."),
    ],
    "lightfoot halfling": [
        ("Lucky", "Reroll 1s on attack rolls, ability checks, or saves."),
        ("Brave", "Advantage on saves vs being frightened."),
        ("Naturally Stealthy", "Hide behind creatures larger than you."),
    ],
    "gnome": [
        ("Darkvision", "See in dim light 60 ft as bright, darkness as dim."),
        ("Gnome Cunning", "Advantage on INT/WIS/CHA saves vs magic."),
    ],
    "forest gnome": [
        ("Darkvision", "See in dim light 60 ft as bright, darkness as dim."),
        ("Gnome Cunning", "Advantage on INT/WIS/CHA saves vs magic."),
        ("Natural Illusionist", "Know Minor Illusion cantrip (INT)."),
    ],
    "rock gnome": [
        ("Darkvision", "See in dim light 60 ft as bright, darkness as dim."),
        ("Gnome Cunning", "Advantage on INT/WIS/CHA saves vs magic."),
        ("Artificer's Lore", "Double proficiency on History checks about magic items."),
    ],
    "half-elf": [
        ("Darkvision", "See in dim light 60 ft as bright, darkness as dim."),
        ("Fey Ancestry", "Advantage vs charm, immune to magic sleep."),
        ("Skill Versatility", "Proficiency in two skills of your choice."),
    ],
    "half-orc": [
        ("Darkvision", "See in dim light 60 ft as bright, darkness as dim."),
        ("Relentless Endurance", "Once per long rest: drop to 1 HP instead of 0."),
        ("Savage Attacks", "On a critical hit, roll one weapon die extra."),
    ],
    "tiefling": [
        ("Darkvision", "See in dim light 60 ft as bright, darkness as dim."),
        ("Hellish Resistance", "Resistance to fire damage."),
        ("Infernal Legacy", "Know Thaumaturgy. Hellish Rebuke at level 3."),
    ],
    "dragonborn": [
        ("Breath Weapon",
         "Exhale destructive energy: 2d6 damage in a 15-ft cone or 30-ft line. DEX or CON save."),
        ("Damage Resistance", "Resistance to your draconic ancestry damage type."),
    ],
    "human": [
        ("Extra Language", "Speak one additional language of your choice."),
    ],
}

# Background features: {background_lower: (feature_name, description)}
BACKGROUND_FEATURES = {
    "acolyte": (
        "Shelter of the Faithful",
        "Command respect of your faith, perform religious ceremonies, "
        "receive free healing at temples.",
    ),
    "charlatan": (
        "False Identity",
        "Forged documents and alternate identity. Can forge documents and duplicate handwriting.",
    ),
    "criminal": (
        "Criminal Contact",
        "Reliable contact in the criminal underworld for passing messages and finding local contacts.",
    ),
    "entertainer": (
        "By Popular Demand",
        "Always find a place to perform. Free lodging and modest lifestyle in exchange.",
    ),
    "folk hero": (
        "Rustic Hospitality",
        "Common folk shelter and feed you, hide you from authorities if needed.",
    ),
    "guild artisan": (
        "Guild Membership",
        "Guild provides lodging, legal aid, and contacts. You pay 5 gp/month dues.",
    ),
    "hermit": (
        "Discovery",
        "Uncovered a unique and powerful discovery — work with DM on what this is.",
    ),
    "noble": (
        "Position of Privilege",
        "Welcome in high society, people assume the best of you, access to high society events.",
    ),
    "outlander": (
        "Wanderer",
        "Excellent memory for maps and geography. Can find food/water for up to 6 people.",
    ),
    "sage": (
        "Researcher",
        "Know where to find information. If you don't know it, know who or where to ask.",
    ),
    "sailor": (
        "Ship's Passage",
        "Free passage on sailing ships for you and party. May require helping with ship duties.",
    ),
    "soldier": (
        "Military Rank",
        "Soldiers loyal to your old faction recognize rank, may defer to you or provide resources.",
    ),
    "urchin": (
        "City Secrets",
        "Know secret passages through cities. Travel between locations at double normal pace.",
    ),
}


def get_character_features(char: "Character") -> list[tuple[str, str]]:
    """Return all features for a character as (name, description) tuples."""
    features: list[tuple[str, str]] = []

    # Class features at or below character level
    cls = (char.char_class or "").lower()
    for min_lvl, name, desc in CLASS_FEATURE_DETAILS.get(cls, []):
        if char.level >= min_lvl:
            resolved = desc(char.level) if callable(desc) else desc
            features.append((name, resolved))

    # Racial features
    species = (getattr(char, "race", "") or "").lower()
    for name, desc in RACIAL_FEATURES.get(species, []):
        features.append((name, desc))

    # Background feature
    bg = (char.background or "").lower()
    if bg in BACKGROUND_FEATURES:
        features.append(BACKGROUND_FEATURES[bg])

    return features


# Optimal ability score order per class (highest first = best stat → gets 15)
# Maps class → ordered list of ability keys matching STANDARD_ARRAY order
OPTIMAL_ABILITY_ORDER: dict[str, list[str]] = {
    "barbarian": ["str", "con", "dex", "wis", "cha", "int"],
    "bard":      ["cha", "dex", "con", "int", "wis", "str"],
    "cleric":    ["wis", "con", "str", "cha", "dex", "int"],
    "druid":     ["wis", "con", "dex", "int", "cha", "str"],
    "fighter":   ["str", "con", "dex", "wis", "cha", "int"],
    "monk":      ["dex", "wis", "con", "str", "int", "cha"],
    "paladin":   ["str", "cha", "con", "wis", "dex", "int"],
    "ranger":    ["dex", "str", "wis", "con", "int", "cha"],
    "rogue":     ["dex", "cha", "con", "int", "wis", "str"],
    "sorcerer":  ["cha", "con", "dex", "int", "wis", "str"],
    "warlock":   ["cha", "con", "dex", "int", "wis", "str"],
    "wizard":    ["int", "con", "dex", "wis", "cha", "str"],
}

# Racial ability score bonuses {race_lower: {ability_key: bonus}}
# Keys may include short ability keys (str/dex/etc.) and metadata keys
# (flexible, flexible_amount).  Only short ability keys are used by _build_char.
RACE_ABILITY_BONUSES: dict[str, dict] = {
    "human":      {"flexible": 2, "flexible_amount": 1},
    "elf":        {"dex": 2, "int": 1},
    "high elf":   {"dex": 2, "int": 1},
    "wood elf":   {"dex": 2, "wis": 1},
    "dark elf":   {"dex": 2, "cha": 1},
    "dwarf":      {"con": 2},
    "hill dwarf": {"con": 2, "wis": 1},
    "mountain dwarf": {"con": 2, "str": 2},
    "halfling":   {"dex": 2},
    "lightfoot halfling": {"dex": 2, "cha": 1},
    "stout halfling": {"dex": 2, "con": 1},
    "gnome":      {"int": 2},
    "forest gnome": {"int": 2, "dex": 1},
    "rock gnome": {"int": 2, "con": 1},
    "half-elf":   {"cha": 2, "flexible": 2, "flexible_amount": 1},
    "half-orc":   {"str": 2, "con": 1},
    "tiefling":   {"int": 1, "cha": 2},
    "dragonborn": {"str": 2, "cha": 1},
}

# Races that allow flexible bonus allocation (+N to player-chosen abilities)
FLEXIBLE_BONUS_COUNTS: dict[str, int] = {
    "human":    2,
    "half-elf": 2,
}

# Bonus amount per flexible slot (always +1 in 5e SRD)
FLEXIBLE_BONUS_AMOUNT: dict[str, int] = {
    "human":    1,
    "half-elf": 1,
}

# Abilities that already receive a fixed bonus and cannot also receive a flex slot
FIXED_BONUS_ABILITIES: dict[str, list[str]] = {
    "half-elf": ["cha"],
}

# Levels at which most classes gain an Ability Score Improvement
ASI_LEVELS: list[int] = [4, 8, 12, 16, 19]

# Fighter gains ASIs more frequently than other classes
FIGHTER_ASI_LEVELS: list[int] = [4, 6, 8, 12, 14, 16, 19]

# Rogue gains an additional ASI at level 10
ROGUE_ASI_LEVELS: list[int] = [4, 8, 10, 12, 16, 18]

# Default skill proficiencies granted by each class (2 iconic picks)
CLASS_SKILLS: dict[str, list[str]] = {
    "barbarian": ["Athletics", "Intimidation"],
    "bard":      ["Deception", "Performance"],
    "cleric":    ["History", "Religion"],
    "druid":     ["Animal Handling", "Nature"],
    "fighter":   ["Athletics", "Intimidation"],
    "monk":      ["Acrobatics", "Stealth"],
    "paladin":   ["Athletics", "Religion"],
    "ranger":    ["Animal Handling", "Survival"],
    "rogue":     ["Deception", "Stealth"],
    "sorcerer":  ["Arcana", "Intimidation"],
    "warlock":   ["Arcana", "Deception"],
    "wizard":    ["Arcana", "History"],
}

# Fixed skill proficiencies granted by each background
BACKGROUND_SKILLS: dict[str, list[str]] = {
    "acolyte":            ["Insight", "Religion"],
    "charlatan":          ["Deception", "Sleight of Hand"],
    "criminal":           ["Deception", "Stealth"],
    "entertainer":        ["Acrobatics", "Performance"],
    "folk hero":          ["Animal Handling", "Survival"],
    "guild artisan":      ["Insight", "Persuasion"],
    "hermit":             ["Medicine", "Religion"],
    "noble":              ["History", "Persuasion"],
    "outlander":          ["Athletics", "Survival"],
    "sage":               ["Arcana", "History"],
    "sailor":             ["Athletics", "Perception"],
    "soldier":            ["Athletics", "Intimidation"],
    "spy":                ["Deception", "Stealth"],
    "urchin":             ["Sleight of Hand", "Stealth"],
    "haunted one":        ["Arcana", "Investigation"],
    "far traveler":       ["Insight", "Perception"],
    "city watch":         ["Athletics", "Insight"],
    "mercenary veteran":  ["Athletics", "Persuasion"],
    "urban bounty hunter":["Deception", "Stealth"],
    "uthgardt tribe member": ["Athletics", "Survival"],
}

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


# ── AC calculation ───────────────────────────────────────────────────────────

def _compute_ac(char: "Character") -> int:
    """
    Compute AC from equipped armor and class unarmored-defense features.
    Reads armor_type/ac_base/is_shield from EquipmentItem fields.
    Falls back to 10 + DEX when no armor is present.
    """
    scores = char.ability_scores
    dex_mod = (scores.dexterity   - 10) // 2
    con_mod = (scores.constitution - 10) // 2
    wis_mod = (scores.wisdom      - 10) // 2

    armor = None
    has_shield = False
    for item in char.equipment:
        if getattr(item, "is_shield", False):
            has_shield = True
        elif getattr(item, "armor_type", "") in ("light", "medium", "heavy"):
            armor = item

    shield_bonus = 2 if has_shield else 0

    if armor is None:
        cls = (char.char_class or "").lower()
        if cls == "barbarian":
            base = 10 + dex_mod + con_mod
        elif cls == "monk":
            base = 10 + dex_mod + wis_mod
        else:
            base = 10 + dex_mod
    else:
        armor_type = armor.armor_type
        ac_base    = armor.ac_base
        if armor_type == "light":
            base = ac_base + dex_mod
        elif armor_type == "medium":
            base = ac_base + min(dex_mod, 2)
        else:  # heavy
            base = ac_base  # DEX never contributes

    return base + shield_bonus


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

    # Armor class — reads EquipmentItem metadata when equipment is present
    character.armor_class = _compute_ac(character)

    # Speed (default 30 — racial overrides handled in PROTO-1 race step)
    if not character.speed:
        character.speed = 30

    # Saving throw proficiencies
    character.saving_throw_proficiencies = list(
        SAVING_THROWS.get(cls, [])
    )

    # Skill proficiencies from class + background (merge, deduplicate, preserve any
    # proficiencies already set on the character — e.g. from the wizard flow)
    bg_key = (character.background or "").lower().strip()
    auto_skills = (
        CLASS_SKILLS.get(cls, [])
        + BACKGROUND_SKILLS.get(bg_key, [])
    )
    existing = set(character.skill_proficiencies)
    for skill in auto_skills:
        if skill not in existing:
            character.skill_proficiencies.append(skill)
            existing.add(skill)

    # Armor proficiencies
    if not character.armor_proficiencies:
        character.armor_proficiencies = list(CLASS_ARMOR_PROFICIENCIES.get(cls, []))

    # Weapon proficiencies
    if not character.weapon_proficiencies:
        character.weapon_proficiencies = list(CLASS_WEAPON_PROFICIENCIES.get(cls, []))

    # Tool proficiencies
    if not character.tool_proficiencies:
        character.tool_proficiencies = list(CLASS_TOOL_PROFICIENCIES.get(cls, []))

    # Languages from background
    if not character.languages:
        character.languages = list(BACKGROUND_LANGUAGES.get(bg_key, []))

    # Starting gold
    if not getattr(character, "gold", 0):
        character.gold = STARTING_GOLD.get(cls, 0)

    # Features & traits — collect all levels up to current
    if not character.features:
        from engine.character import FeatureEntry
        for lvl in range(1, lvl + 1):
            for feat_name in CLASS_FEATURES.get(cls, {}).get(lvl, []):
                character.features.append(FeatureEntry(name=feat_name))

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
