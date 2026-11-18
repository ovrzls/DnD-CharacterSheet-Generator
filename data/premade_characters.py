"""
Premade character data for OtG character sheets — all Level 3.
Source: Open the Gates Gaming premade character PDF (Examples/otg-premade-characters.pdf).

Each character is built, run through derive_stats, and corrected via SKILL_CORRECTIONS /
AC_OVERRIDES / HP_BONUSES before the sheet is generated.
"""
from __future__ import annotations
from engine.character import (
    Character, AbilityScores, SpellEntry, EquipmentItem, FeatureEntry, Attack,
)
from engine.rules import derive_stats


# ── Shorthand helpers ────────────────────────────────────────────────────────

def _ei(name: str, qty: int = 1, armor_type: str = "",
        ac_base: int = 0, is_shield: bool = False) -> EquipmentItem:
    return EquipmentItem(name=name, quantity=qty, armor_type=armor_type,
                         ac_base=ac_base, is_shield=is_shield)

def _sp(level: int, name: str, range_: str = "",
        effect_dmg: str = "", flags: str = "") -> SpellEntry:
    return SpellEntry(level=level, name=name, range=range_,
                      effect_dmg=effect_dmg, flags=flags)

def _atk(name: str, hit: int, dice: str, dmg_type: str) -> Attack:
    return Attack(name=name, hit_bonus=hit, damage_dice=dice, damage_type=dmg_type)

def _feat(name: str, card: str = "card") -> FeatureEntry:
    return FeatureEntry(name=name, source_card=card)


# ── Per-class corrections applied AFTER derive_stats ─────────────────────────

# Exact skill proficiencies shown on the OtG premade sheet.
SKILL_CORRECTIONS: dict[str, dict] = {
    "barbarian": {
        "proficiencies": ["Athletics", "Insight", "Perception", "Survival"],
        "expertises": [],
    },
    "bard": {
        "proficiencies": ["Acrobatics", "Arcana", "Deception", "Nature",
                          "Perception", "Sleight of Hand", "Stealth"],
        "expertises": ["Performance", "Persuasion"],
    },
    "cleric": {
        "proficiencies": ["Insight", "Medicine", "Religion", "Survival"],
        "expertises": [],
    },
    "druid": {
        "proficiencies": ["Animal Handling", "Medicine", "Religion", "Survival"],
        "expertises": [],
    },
    "fighter": {
        "proficiencies": ["Acrobatics", "Athletics", "Insight", "Intimidation"],
        "expertises": [],
    },
    "monk": {
        "proficiencies": ["Acrobatics", "Athletics", "Medicine", "Religion"],
        "expertises": [],
    },
    "paladin": {
        "proficiencies": ["Insight", "Intimidation", "Persuasion"],
        "expertises": [],
    },
    "ranger": {
        "proficiencies": ["Animal Handling", "Insight", "Stealth", "Survival"],
        "expertises": [],
    },
    "rogue": {
        "proficiencies": ["Deception", "History", "Insight", "Sleight of Hand"],
        "expertises": ["Investigation", "Stealth"],
    },
    "sorcerer": {
        "proficiencies": ["Arcana", "Deception", "Insight", "Persuasion"],
        "expertises": [],
    },
    "warlock": {
        "proficiencies": ["Deception", "Nature", "Persuasion", "Sleight of Hand"],
        "expertises": [],
    },
    "wizard": {
        "proficiencies": ["Arcana", "History", "Investigation", "Nature"],
        "expertises": [],
    },
}

# AC values that require a post-derive override.
# Paladin: Defense style +1; Sorcerer: Draconic Resilience (13+DEX).
AC_OVERRIDES: dict[str, int] = {
    "paladin": 19,
    "sorcerer": 14,
}

# Extra HP added after derive_stats (Sorcerer Draconic Resilience +1/level × 3).
HP_BONUSES: dict[str, int] = {
    "sorcerer": 3,
}


# ── Character factory functions ───────────────────────────────────────────────

def _make_barbarian() -> Character:
    return Character(
        name="",
        char_class="barbarian",
        level=3,
        ability_scores=AbilityScores(strength=16, dexterity=14, constitution=15,
                                     intelligence=9, wisdom=13, charisma=11),
        equipment=[
            _ei("Greataxe"), _ei("Handaxe", 2), _ei("Javelin"),
            _ei("Hunting Trap"), _ei("Horn"), _ei("Bedroll"), _ei("Mess Kit"),
            _ei("Rations", 1), _ei("Quarterstaff"), _ei("Hempen Rope (50ft)"),
            _ei("Tinderbox"), _ei("Waterskin"), _ei("Torch"), _ei("Clothes"),
        ],
        attacks=[
            _atk("Greataxe",       5, "1d12",   "slash, heavy/two-hand"),
            _atk("Handaxe",        5, "1d6",    "slash, 20/60 light"),
            _atk("Javelin",        5, "1d6",    "pierce, 30/120"),
            _atk("Unarmed Strike", 5, "4",      "bludgeoning"),
        ],
        features=[
            _feat("Unarmored Defense"),
            _feat("Danger Sense"),
            _feat("Rage"),
            _feat("Reckless Attack"),
            _feat("Frenzy"),
        ],
        languages=["Common", "Orc", "Sylvan"],
        weapon_proficiencies=["Simple weapons", "Martial weapons"],
        armor_proficiencies=["Light armor", "Medium armor", "Shields"],
        tool_proficiencies=["Horn"],
        gold=25, speed=30,
    )


def _make_bard() -> Character:
    return Character(
        name="",
        char_class="bard",
        level=3,
        ability_scores=AbilityScores(strength=9, dexterity=14, constitution=15,
                                     intelligence=11, wisdom=13, charisma=16),
        equipment=[
            _ei("Bagpipes"), _ei("Costume"), _ei("Drum"), _ei("Flute"), _ei("Lute"),
            _ei("Bedroll"), _ei("Candle"), _ei("Disguise Kit"), _ei("Rations", 1),
            _ei("Waterskin"), _ei("Dagger"),
            _ei("Rapier"), _ei("Leather Armor", armor_type="light", ac_base=11),
        ],
        attacks=[
            _atk("Rapier",         4, "1d8",   "pierce, finesse"),
            _atk("Dagger",         4, "1d4",   "pierce, 20/60 light,fin"),
            _atk("Unarmed Strike", 1, "0",     "bludgeoning"),
        ],
        features=[
            _feat("Jack of All Trades"),
            _feat("Bardic Inspiration"),
            _feat("Song of Rest"),
            _feat("Cutting Words"),
        ],
        always_available=[
            _sp(0, "Message",        "120 ft", "whisper"),
            _sp(0, "Vicious Mockery","60 ft",  "1d4 psy",  "S"),
        ],
        spells=[
            _sp(1, "Faerie Fire",       "60 ft",      "Outlined",    "C S"),
            _sp(1, "Healing Word",      "60 ft",      "Heal 1d4+3",  "BA"),
            _sp(1, "Hideous Laughter",  "30 ft",      "Prone",       "C S"),
            _sp(1, "Thunderwave",       "Self 15ft",  "2d8 thd",     "S"),
            _sp(2, "Detect Thoughts",   "Self",       "Read mind",   "C S"),
            _sp(2, "Suggestion",        "30 ft",      "Command",     "C S"),
        ],
        languages=["Common", "Elvish"],
        weapon_proficiencies=["Simple weapons", "Hand crossbows",
                              "Longswords", "Rapiers", "Shortswords"],
        armor_proficiencies=["Light armor"],
        tool_proficiencies=["Bagpipes", "Disguise Kit", "Drum", "Flute", "Lute"],
        gold=25,
    )


def _make_cleric() -> Character:
    return Character(
        name="",
        char_class="cleric",
        level=3,
        ability_scores=AbilityScores(strength=14, dexterity=9, constitution=15,
                                     intelligence=11, wisdom=16, charisma=13),
        equipment=[
            _ei("Clothes"), _ei("Vestments"), _ei("Blankets"), _ei("Block of Incense"),
            _ei("Candle"), _ei("Censer"), _ei("Rations", 1), _ei("Tinderbox"),
            _ei("Waterskin"), _ei("Mace"), _ei("Holy Symbol"),
            _ei("Chain Mail", armor_type="heavy", ac_base=16),
            _ei("Shield", is_shield=True),
        ],
        attacks=[
            _atk("Mace",           4, "1d6",   "bludg"),
            _atk("Unarmed Strike", 4, "3",     "bludgeoning"),
        ],
        features=[
            _feat("Disciple of Life"),
            _feat("Channel Divinity"),
            _feat("Preserve Life"),
        ],
        always_available=[
            _sp(0, "Guidance",       "Touch",  "+1d4 check", "C"),
            _sp(0, "Sacred Flame",   "60 ft",  "1d8 rad",    "S"),
            _sp(0, "Spare the Dying","Touch",  "Stabilize"),
        ],
        spells=[
            _sp(1, "Bless",                   "30 ft",     "+1d4 atk/save", "C"),
            _sp(1, "Cure Wounds",             "Touch",     "Heal 1d8+3"),
            _sp(1, "Detect Evil & Good",      "Self 30ft", "Detect",        "C"),
            _sp(1, "Guiding Bolt",            "120 ft",    "4d6 rad"),
            _sp(1, "Inflict Wounds",          "Touch",     "3d10 nec"),
            _sp(1, "Shield of Faith",         "60 ft",     "+2 AC",         "C"),
            _sp(2, "Aid",                     "30 ft",     "+5 max HP"),
            _sp(2, "Lesser Restoration",      "Touch",     "Remove cond"),
            _sp(2, "Spiritual Weapon",        "60 ft",     "1d8+3 force",   "BA"),
            _sp(2, "Warding Bond",            "Touch",     "Resistance"),
        ],
        languages=["Celestial", "Common", "Dwarvish", "Infernal"],
        weapon_proficiencies=["Simple weapons"],
        armor_proficiencies=["Light armor", "Medium armor", "Heavy armor", "Shields"],
        tool_proficiencies=[],
        gold=25,
    )


def _make_druid() -> Character:
    return Character(
        name="",
        char_class="druid",
        level=3,
        ability_scores=AbilityScores(strength=11, dexterity=14, constitution=15,
                                     intelligence=13, wisdom=16, charisma=9),
        equipment=[
            _ei("Blanket"), _ei("Clothes"), _ei("Herbalism Kit"),
            _ei("Woodcarver's Tools"), _ei("Bedroll"), _ei("Mess Kit"),
            _ei("Rations", 1), _ei("Hempen Rope (50ft)"), _ei("Tinderbox"),
            _ei("Torch"), _ei("Waterskin"), _ei("Quarterstaff"),
            _ei("Sprig of Mistletoe"),
            _ei("Hide Armor", armor_type="medium", ac_base=12),
            _ei("Shield", is_shield=True),
        ],
        attacks=[
            _atk("Quarterstaff",   2, "1d6",   "bludg, versatile 1d8"),
            _atk("Unarmed Strike", 2, "1",     "bludgeoning"),
        ],
        features=[
            _feat("Circle of Land — Mountain"),
            _feat("Wildshape"),
            _feat("Natural Recovery"),
        ],
        always_available=[
            _sp(0, "Druidcraft",    "30 ft", "Nature effect"),
            _sp(0, "Guidance",      "Touch", "+1d4 check",   "C"),
            _sp(0, "Produce Flame", "30 ft", "1d8 fire"),
        ],
        spells=[
            _sp(1, "Detect Magic",       "Self 30ft", "Detect magic",  "C"),
            _sp(1, "Faerie Fire",        "60 ft",     "Outlined",      "C S"),
            _sp(1, "Goodberry",          "Touch",     "10 berries"),
            _sp(1, "Speak with Animals", "Self",      "Talk animals",  "C"),
            _sp(2, "Heat Metal",         "60 ft",     "2d8 fire",      "C"),
            _sp(2, "Moonbeam",           "150 ft",    "2d10 rad",      "C S"),
            _sp(2, "Spider Climb",       "Touch",     "Climb walls",   "C"),
            _sp(2, "Spike Growth",       "150 ft",    "2d4 pierce",    "C S"),
        ],
        languages=["Common", "Druidic", "Primordial", "Sylvan"],
        weapon_proficiencies=["Clubs", "Daggers", "Javelins", "Maces",
                              "Quarterstaffs", "Scimitars", "Slings", "Spears"],
        armor_proficiencies=["Light armor", "Medium armor", "Shields"],
        tool_proficiencies=["Herbalism Kit", "Woodcarver's Tools"],
        gold=25,
    )


def _make_fighter() -> Character:
    return Character(
        name="",
        char_class="fighter",
        level=3,
        ability_scores=AbilityScores(strength=16, dexterity=13, constitution=15,
                                     intelligence=9, wisdom=14, charisma=11),
        equipment=[
            _ei("Clothes"), _ei("Crossbow Bolts"), _ei("Dragonchess Set"),
            _ei("Playing Card Set"), _ei("Bedroll"), _ei("Mess Kit"),
            _ei("Ration", 1), _ei("Hempen Rope (50ft)"), _ei("Tinderbox"),
            _ei("Torch"), _ei("Waterskin"),
            _ei("Light Crossbow"), _ei("Longsword"), _ei("Trident"),
            _ei("Chain Mail", armor_type="heavy", ac_base=16),
            _ei("Shield", is_shield=True),
        ],
        attacks=[
            # Dueling style: +2 damage one-handed melee; already in dice expression
            _atk("Longsword",      5, "1d8+5",  "slash, versatile 1d10"),
            _atk("Light Crossbow", 5, "1d8",    "pierce, 80/320 loading"),
            _atk("Trident",        5, "1d8+5",  "pierce, 20/60 versatile"),
            _atk("Unarmed Strike", 5, "4",      "bludgeoning"),
        ],
        features=[
            _feat("Fighting Style — Dueling"),
            _feat("Improved Critical"),
            _feat("Second Wind"),
            _feat("Action Surge"),
        ],
        languages=["Common", "Goblin"],
        weapon_proficiencies=["Simple weapons", "Martial weapons"],
        armor_proficiencies=["Light armor", "Medium armor", "Heavy armor", "Shields"],
        tool_proficiencies=["Playing Card Set", "Vehicles (Land)"],
        gold=25,
    )


def _make_monk() -> Character:
    return Character(
        name="",
        char_class="monk",
        level=3,
        ability_scores=AbilityScores(strength=11, dexterity=16, constitution=14,
                                     intelligence=13, wisdom=15, charisma=9),
        equipment=[
            _ei("Blanket"), _ei("Herbalism Kit"), _ei("Viol"), _ei("Bedroll"),
            _ei("Mess Kit"), _ei("Rations", 1), _ei("Hempen Rope (50ft)"),
            _ei("Tinderbox"), _ei("Torch"), _ei("Waterskin"),
            _ei("Dart"), _ei("Quarterstaff"), _ei("Clothes"),
        ],
        attacks=[
            _atk("Quarterstaff",   5, "1d6",   "bludg, versatile 1d8"),
            _atk("Dart",           5, "1d4",   "pierce, 20/60 finesse"),
            _atk("Unarmed Strike", 5, "1d4",   "bludgeoning"),
        ],
        features=[
            _feat("Unarmored Defense"),
            _feat("Unarmored Movement"),
            _feat("Martial Arts"),
            _feat("Ki"),
            _feat("Deflect Missiles"),
            _feat("Open Hand Technique"),
        ],
        languages=["Common", "Infernal", "Primordial"],
        weapon_proficiencies=["Simple weapons", "Shortswords"],
        armor_proficiencies=[],
        tool_proficiencies=["Flute", "Herbalism Kit"],
        gold=25,
        speed=40,  # Unarmored Movement +10ft at level 3
    )


def _make_paladin() -> Character:
    return Character(
        name="",
        char_class="paladin",
        level=3,
        ability_scores=AbilityScores(strength=15, dexterity=11, constitution=16,
                                     intelligence=9, wisdom=13, charisma=14),
        equipment=[
            _ei("Clothes"), _ei("Dragonchess Set"), _ei("Signet Ring"),
            _ei("Bedroll"), _ei("Mess Kit"), _ei("Rations", 1),
            _ei("Hempen Rope (50ft)"), _ei("Tinderbox"), _ei("Torch"),
            _ei("Waterskin"), _ei("Holy Symbol"), _ei("Javelin"), _ei("Longsword"),
            _ei("Chain Mail", armor_type="heavy", ac_base=16),
            _ei("Shield", is_shield=True),
        ],
        attacks=[
            _atk("Longsword",      4, "1d8",   "slash, versatile 1d10"),
            _atk("Javelin",        4, "1d6",   "pierce, 30/120"),
            _atk("Unarmed Strike", 4, "3",     "bludgeoning"),
        ],
        features=[
            _feat("Fighting Style — Defense"),
            _feat("Divine Health"),
            _feat("Divine Sense"),
            _feat("Lay on Hands"),
            _feat("Divine Smite"),
            _feat("Channel Divinity"),
        ],
        spells=[
            _sp(1, "Bless",                       "30 ft",  "+1d4 atk/save",  "C"),
            _sp(1, "Divine Favor",                "Self",   "+1d4 rad dmg",   "C"),
            _sp(1, "Protection from Evil & Good", "Touch",  "Protection",     "C"),
            _sp(1, "Sanctuary",                   "30 ft",  "Protection"),
            _sp(1, "Shield of Faith",             "60 ft",  "+2 AC",          "C"),
        ],
        languages=["Celestial", "Common", "Elvish"],
        weapon_proficiencies=["Simple weapons", "Martial weapons"],
        armor_proficiencies=["Light armor", "Medium armor", "Heavy armor", "Shields"],
        tool_proficiencies=["Dragonchess Set"],
        gold=25,
    )


def _make_ranger() -> Character:
    return Character(
        name="",
        char_class="ranger",
        level=3,
        ability_scores=AbilityScores(strength=9, dexterity=16, constitution=15,
                                     intelligence=13, wisdom=14, charisma=11),
        equipment=[
            _ei("Arrows"), _ei("Clothes"), _ei("Hunting Trap"), _ei("Pan Flute"),
            _ei("Quarterstaff"), _ei("Bedroll"), _ei("Mess Kit"), _ei("Rations", 1),
            _ei("Hempen Rope (50ft)"), _ei("Tinderbox"), _ei("Torch"),
            _ei("Waterskin"), _ei("Dagger"), _ei("Longbow"), _ei("Shortsword"),
            _ei("Leather Armor", armor_type="light", ac_base=11),
        ],
        attacks=[
            # Archery style: +2 to ranged hit; already in hit_bonus=7
            _atk("Longbow",        7, "1d8+3",  "pierce, 150/600 heavy"),
            _atk("Shortsword",     5, "1d6",    "pierce, light finesse"),
            _atk("Dagger",         5, "1d4",    "pierce, 20/60 light,fin"),
            _atk("Unarmed Strike", 1, "0",      "bludgeoning"),
        ],
        features=[
            _feat("Fighting Style — Archery"),
            _feat("Favored Enemy — Monstrosities"),
            _feat("Natural Explorer — Forest"),
            _feat("Primeval Awareness"),
            _feat("Hunter's Prey — Colossus Slayer"),
        ],
        spells=[
            _sp(1, "Animal Friendship", "30 ft",  "Charm beast",  "S"),
            _sp(1, "Goodberry",         "Touch",  "10 berries"),
            _sp(1, "Hunter's Mark",     "90 ft",  "+1d6 dmg",     "C"),
        ],
        languages=["Common", "Dwarvish", "Primordial", "Sylvan"],
        weapon_proficiencies=["Simple weapons", "Martial weapons"],
        armor_proficiencies=["Light armor", "Medium armor", "Shields"],
        tool_proficiencies=["Pan Flute"],
        gold=25,
    )


def _make_rogue() -> Character:
    return Character(
        name="",
        char_class="rogue",
        level=3,
        ability_scores=AbilityScores(strength=9, dexterity=16, constitution=15,
                                     intelligence=14, wisdom=11, charisma=13),
        equipment=[
            _ei("Clothes"), _ei("Crowbar"), _ei("Bell"), _ei("Candle"),
            _ei("Hammer"), _ei("Hooded Lantern"), _ei("Oil (flask)"), _ei("Piton"),
            _ei("Rations", 1), _ei("Hempen Rope (50ft)"), _ei("String"),
            _ei("Tinderbox"), _ei("Waterskin"), _ei("Dagger", 2),
            _ei("Rapier"), _ei("Shortbow"), _ei("Arrows", 20),
            _ei("Leather Armor", armor_type="light", ac_base=11),
            _ei("Forgery Kit"), _ei("Three-Dragon Ante Set"),
            _ei("Thieves' Tools"), _ei("Ball Bearings"),
        ],
        attacks=[
            _atk("Shortbow",       5, "1d6",   "pierce, 80/320"),
            _atk("Rapier",         5, "1d8",   "pierce, finesse"),
            _atk("Dagger",         5, "1d4",   "pierce, 20/60 light,fin"),
            _atk("Unarmed Strike", 1, "0",     "bludgeoning"),
        ],
        features=[
            _feat("Sneak Attack"),
            _feat("Cunning Action"),
            _feat("Fast Hands"),
            _feat("Second-Story Work"),
        ],
        languages=["Common", "Goblin", "Thieves' Cant"],
        weapon_proficiencies=["Simple weapons", "Hand crossbows",
                              "Longswords", "Rapiers", "Shortswords"],
        armor_proficiencies=["Light armor"],
        tool_proficiencies=["Forgery Kit", "Thieves' Tools",
                             "Three-Dragon Ante Set"],
        gold=25,
    )


def _make_sorcerer() -> Character:
    return Character(
        name="",
        char_class="sorcerer",
        level=3,
        ability_scores=AbilityScores(strength=9, dexterity=13, constitution=15,
                                     intelligence=11, wisdom=14, charisma=16),
        equipment=[
            _ei("Crossbow Bolts", 20), _ei("Three-Dragon Ante Set"),
            _ei("Bedroll"), _ei("Mess Kit"), _ei("Rations", 1),
            _ei("Hempen Rope (50ft)"), _ei("Tinderbox"), _ei("Torch"),
            _ei("Waterskin"), _ei("Light Crossbow"), _ei("Dagger", 2),
            _ei("Crystal"), _ei("Clothes"),
        ],
        attacks=[
            _atk("Light Crossbow", 3, "1d8",   "pierce, 80/320 loading"),
            _atk("Dagger",         3, "1d4",   "pierce, 20/60 light,fin"),
            _atk("Unarmed Strike", 1, "0",     "bludgeoning"),
        ],
        features=[
            _feat("Draconic Ancestry — Brass"),
            _feat("Draconic Resilience"),
            _feat("Font of Magic"),
            _feat("Metamagic — Twinned Spell"),
            _feat("Metamagic — Subtle Spell"),
        ],
        always_available=[
            _sp(0, "Fire Bolt",   "120 ft", "1d10 fire"),
            _sp(0, "Message",     "120 ft", "whisper"),
            _sp(0, "Ray of Frost","60 ft",  "1d8 cold,-10ft"),
            _sp(0, "Light",       "Touch",  "20ft radius"),
        ],
        spells=[
            _sp(1, "Fog Cloud",   "120 ft", "Obscured",  "C"),
            _sp(1, "Magic Missile","120 ft","3×1d4+1 frc"),
            _sp(1, "Shield",      "Self",   "+5 AC",     "R"),
            _sp(2, "Invisibility","Touch",  "Invisible", "C"),
        ],
        languages=["Common", "Draconic", "Elvish", "Goblin"],
        weapon_proficiencies=["Daggers", "Darts", "Slings",
                              "Quarterstaffs", "Light crossbows"],
        armor_proficiencies=[],
        tool_proficiencies=["Three-Dragon Ante Set"],
        gold=25,
    )


def _make_warlock() -> Character:
    return Character(
        name="",
        char_class="warlock",
        level=3,
        ability_scores=AbilityScores(strength=9, dexterity=14, constitution=15,
                                     intelligence=13, wisdom=11, charisma=16),
        equipment=[
            _ei("Iron Pot"), _ei("Shovel"), _ei("Book"), _ei("Ink (1oz)"),
            _ei("Ink Pen"), _ei("Little Bag of Sand"), _ei("Parchment", 1),
            _ei("Small Knife"), _ei("Clothes"), _ei("Cook's Utensils"),
            _ei("Light Crossbow"), _ei("Dagger", 2), _ei("Sickle"), _ei("Staff"),
            _ei("Leather Armor", armor_type="light", ac_base=11),
        ],
        attacks=[
            _atk("Light Crossbow", 4, "1d8",   "pierce, 80/320 loading"),
            _atk("Dagger",         4, "1d4",   "pierce, 20/60 light,fin"),
            _atk("Sickle",         1, "1d4",   "slash, light"),
            _atk("Unarmed Strike", 1, "0",     "bludgeoning"),
        ],
        features=[
            _feat("Eldritch Invocation — Agonizing Blast"),
            _feat("Eldritch Invocation — Repelling Blast"),
            _feat("Pact of the Tome"),
            _feat("Dark One's Blessing"),
        ],
        always_available=[
            _sp(0, "Guidance",      "Touch",  "+1d4 check",  "C"),
            _sp(0, "Message",       "120 ft", "whisper"),
            _sp(0, "Acid Splash",   "60 ft",  "1d6 acid",    "S"),
            _sp(0, "Eldritch Blast","120 ft", "1d10+3 force"),
            _sp(0, "Minor Illusion","30 ft",  "Sound/image", "C"),
        ],
        # Pact magic: all cast at 2nd-level slots
        spells=[
            _sp(2, "Protection from Evil & Good", "Touch", "Protection", "C"),
            _sp(2, "Charm Person",   "30 ft",  "Charmed",   "S"),
            _sp(2, "Hold Person",    "60 ft",  "Paralyzed", "C S"),
            _sp(2, "Shatter",        "60 ft",  "3d8 thd",   "S"),
        ],
        languages=["Common", "Infernal"],
        weapon_proficiencies=["Simple weapons"],
        armor_proficiencies=["Light armor"],
        tool_proficiencies=["Disguise Kit", "Forgery Kit"],
        gold=25,
    )


def _make_wizard() -> Character:
    return Character(
        name="",
        char_class="wizard",
        level=3,
        ability_scores=AbilityScores(strength=9, dexterity=14, constitution=15,
                                     intelligence=16, wisdom=13, charisma=11),
        equipment=[
            _ei("Ink (2oz)"), _ei("Small Knife", 2), _ei("Spellbook"),
            _ei("Book"), _ei("Ink Pen"), _ei("Little Bag of Sand"),
            _ei("Parchment", 1), _ei("Light Crossbow"),
            _ei("Staff"), _ei("Dagger"), _ei("Clothes"),
        ],
        attacks=[
            _atk("Dagger",         4, "1d4",   "pierce, 20/60 light,fin"),
            _atk("Staff",          1, "1d6",   "bludg, versatile 1d8"),
            _atk("Unarmed Strike", 1, "0",     "bludgeoning"),
        ],
        features=[
            _feat("Arcane Recovery"),
            _feat("Evocation Savant"),
            _feat("Sculpt Spells"),
        ],
        always_available=[
            _sp(0, "Fire Bolt",       "120 ft", "1d10 fire"),
            _sp(0, "Prestidigitation","10 ft",  "Minor effect"),
            _sp(0, "Shocking Grasp",  "Touch",  "1d8 light"),
        ],
        spells=[
            _sp(1, "Burning Hands",        "Self 15ft", "3d6 fire",      "S"),
            _sp(1, "Comprehend Languages", "Self",      "Understand"),
            _sp(1, "Detect Magic",         "Self 30ft", "Detect magic",  "C"),
            _sp(1, "Feather Fall",         "60 ft",     "Slow fall",     "R"),
            _sp(1, "Identify",             "Touch",     "ID magic"),
            _sp(1, "Magic Missile",        "120 ft",    "3×1d4+1 frc"),
            _sp(1, "Shield",               "Self",      "+5 AC",         "R"),
            _sp(2, "Shatter",              "60 ft",     "3d8 thd",       "S"),
            _sp(2, "Web",                  "60 ft",     "Restrained",    "C S"),
        ],
        languages=["Celestial", "Common", "Infernal", "Primordial"],
        weapon_proficiencies=["Daggers", "Darts", "Slings",
                              "Quarterstaffs", "Light crossbows"],
        armor_proficiencies=[],
        tool_proficiencies=[],
        gold=25,
    )


# ── Ordered list of all factory functions ────────────────────────────────────

_FACTORIES = [
    _make_barbarian, _make_bard, _make_cleric, _make_druid,
    _make_fighter, _make_monk, _make_paladin, _make_ranger,
    _make_rogue, _make_sorcerer, _make_warlock, _make_wizard,
]


def get_premade_characters() -> list[Character]:
    """
    Return all 12 premade Level-3 characters, fully derived and corrected,
    ready for fill_otg_sheet(..., predefined=True).
    """
    characters = []
    for factory in _FACTORIES:
        char = factory()
        cls = char.char_class.lower()

        # Standard derivation (HP, initiative, AC, spell stats, etc.)
        derive_stats(char)

        # Skill corrections: replace auto-derived skills with the exact PDF values
        corrections = SKILL_CORRECTIONS.get(cls, {})
        char.skill_proficiencies = list(corrections.get("proficiencies", []))
        char.skill_expertises    = list(corrections.get("expertises", []))

        # Recompute passive perception with corrected skill list
        wis_mod = (char.ability_scores.wisdom - 10) // 2
        has_perc = "Perception" in char.skill_proficiencies
        char.passive_perception = 10 + wis_mod + (char.proficiency_bonus if has_perc else 0)

        # AC overrides (Paladin Defense style +1; Sorcerer Draconic Resilience)
        if cls in AC_OVERRIDES:
            char.armor_class = AC_OVERRIDES[cls]

        # HP bonuses (Sorcerer Draconic Resilience +1/level)
        if cls in HP_BONUSES:
            char.max_hp      += HP_BONUSES[cls]
            char.current_hp   = char.max_hp

        characters.append(char)

    return characters
