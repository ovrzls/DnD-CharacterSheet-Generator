"""
Spell selection logic — PROTO-4 implementation.
Provides random and manual spell selection for caster characters.
Data sourced from the Open5e v2 API via Open5eClient.

Open5e v2 spell field notes (schema verified against live API):
  school:               {"name": "...", "key": "evocation"} — use .key for category
  damage_roll:          "1d10" at base level, "" for non-damage spells
  damage_types:         ["fire"] — list of lowercase strings
  casting_options:      [{type: "player_level_5", damage_roll: "2d10"}, ...] for cantrip scaling
  casting_time:         "action" | "bonus-action" | "reaction" | "1minute" | ...
  concentration:        bool
  saving_throw_ability: non-empty string when a save is required
  range_text:           "120 feet" | "Touch" | "Self" | ...
"""
from __future__ import annotations
import re
import random
from engine.character import Character, SpellEntry
from engine.rules import CASTER_CLASSES, SPELLCASTING_ABILITY

# ── Caster tables ──────────────────────────────────────────────────────────────

# Fixed cantrip counts for prototype scope (levels 1-5)
CANTRIP_COUNT: dict[str, int] = {
    "bard":     2,
    "cleric":   3,
    "druid":    2,
    "sorcerer": 4,
    "warlock":  2,
    "wizard":   3,
    "paladin":  0,
    "ranger":   0,
}

# Spells known per level for "known" casters (spells selected at level-up, kept until replaced)
SPELLS_KNOWN: dict[str, dict[int, int]] = {
    "bard":     {1: 2, 2: 3, 3: 4, 4: 5, 5: 6},
    "ranger":   {1: 0, 2: 2, 3: 3, 4: 3, 5: 4},
    "sorcerer": {1: 2, 2: 3, 3: 4, 4: 5, 5: 6},
    "warlock":  {1: 2, 2: 3, 3: 4, 4: 5, 5: 6},
}

# Prepared casters select spells each long rest (spell_mod + level spells)
PREPARED_CASTERS = frozenset({"cleric", "druid", "paladin", "wizard"})
KNOWN_CASTERS    = frozenset({"bard", "ranger", "sorcerer", "warlock"})

# Open5e school key → selection category
SCHOOL_CATEGORIES: dict[str, str] = {
    "evocation":    "damage",
    "necromancy":   "damage",
    "enchantment":  "control",
    "illusion":     "control",
    "conjuration":  "support",
    "abjuration":   "support",
    "transmutation":"utility",
    "divination":   "utility",
}

# ── Internal field helpers ─────────────────────────────────────────────────────

def _school_key(spell: dict) -> str:
    """Return lowercase school key from an Open5e v2 spell dict."""
    school = spell.get("school", {})
    if isinstance(school, dict):
        return school.get("key", "").lower()
    return str(school).lower()


def _categorize_spell(spell: dict) -> str:
    """Return 'damage', 'control', 'support', or 'utility' based on school."""
    return SCHOOL_CATEGORIES.get(_school_key(spell), "utility")


def _shorten_range(range_text: str) -> str:
    """Convert Open5e range_text to compact sheet notation."""
    if not range_text:
        return ""
    lower = range_text.lower().strip()
    if lower in ("self", "touch", "sight", "special", "unlimited"):
        return lower.title()
    if "self" in lower:
        return "Self"
    if "touch" in lower:
        return "Touch"
    m = re.search(r"(\d+)\s*feet", lower)
    if m:
        return f"{m.group(1)} ft"
    m = re.search(r"(\d+)\s*mile", lower)
    if m:
        return f"{m.group(1)} mi"
    return range_text[:12]


def _cantrip_damage_at_level(spell: dict, char_level: int) -> str:
    """
    Return the cantrip's damage dice string for the given character level.
    Checks casting_options for player_level_N entries; falls back to base damage_roll.
    """
    base = spell.get("damage_roll", "")
    best_roll = base
    best_threshold = 0
    for opt in spell.get("casting_options", []):
        roll = opt.get("damage_roll") or ""
        if not roll:
            continue
        m = re.match(r"player_level_(\d+)", opt.get("type", ""))
        if m:
            threshold = int(m.group(1))
            if threshold <= char_level and threshold > best_threshold:
                best_threshold = threshold
                best_roll = roll
    return best_roll or base


def _extract_effect(spell: dict, char_level: int = 1) -> str:
    """
    Extract a short effect string for the sheet.
    Damage spell → "{dice} {type}" e.g. "1d10 fire".
    Healing spell → "Heal 1d8" (parsed from description).
    Fallback → school name.
    """
    dmg_roll  = spell.get("damage_roll", "") or ""
    dmg_types = spell.get("damage_types", []) or []

    if dmg_roll:
        is_cantrip = spell.get("level", 1) == 0
        dice  = _cantrip_damage_at_level(spell, char_level) if is_cantrip else dmg_roll
        dtype = dmg_types[0] if dmg_types else ""
        return f"{dice} {dtype}" if dtype else dice

    desc = spell.get("desc", "") or ""
    if re.search(r"\bregains?\b", desc.lower()) or (
        "heal" in desc.lower() and "hit point" in desc.lower()
    ):
        m = re.search(r"(\d+d\d+(?:\s*\+\s*\d+)?)", desc)
        return f"Heal {m.group(1)}" if m else "Heal"

    school = _school_key(spell)
    return school.title()[:12] if school else "—"


def _extract_flags(spell: dict) -> str:
    """
    Build compact flags string: C (concentration), BA (bonus action),
    R (reaction), S (saving throw required).
    """
    flags = []
    if spell.get("concentration"):
        flags.append("C")
    ct = spell.get("casting_time", "").lower()
    if "bonus" in ct:
        flags.append("BA")
    elif "reaction" in ct:
        flags.append("R")
    if spell.get("saving_throw_ability", ""):
        flags.append("S")
    return ", ".join(flags)


# ── Spell entry conversion ─────────────────────────────────────────────────────

def spell_to_entry(spell: dict, char_level: int = 1,
                   slots_total: int = 0) -> SpellEntry:
    """Convert an Open5e v2 spell dict to a SpellEntry for the character sheet."""
    return SpellEntry(
        level=spell.get("level", 0),
        name=spell.get("name", ""),
        range=_shorten_range(spell.get("range_text", "")),
        effect_dmg=_extract_effect(spell, char_level),
        flags=_extract_flags(spell),
        slots_total=slots_total,
        slots_used=0,
    )


# ── Cantrip / spell counts ─────────────────────────────────────────────────────

def get_cantrip_count(class_key: str) -> int:
    """Return the number of cantrips known for prototype scope (levels 1-5)."""
    return CANTRIP_COUNT.get(class_key.lower(), 0)


def get_spell_count(class_key: str, level: int, character: Character) -> int:
    """
    Return how many slot-based spells to select.
    Known casters (bard, sorcerer, warlock, ranger): lookup SPELLS_KNOWN table.
    Prepared casters (cleric, druid, paladin, wizard): spell_mod + character level.
    """
    cls = class_key.lower()
    if cls in KNOWN_CASTERS:
        return SPELLS_KNOWN.get(cls, {}).get(level, 0)
    if cls in PREPARED_CASTERS:
        spell_ability = SPELLCASTING_ABILITY.get(cls, "intelligence")
        spell_mod = character.ability_modifier(spell_ability)
        return max(1, spell_mod + level)
    return 0


# ── Cantrip selection ──────────────────────────────────────────────────────────

def get_cantrips_for_class(class_key: str, client) -> list[dict]:
    """Fetch all cantrips for a class from Open5e."""
    return client.get_cantrips(char_class=class_key)


def select_random_cantrips(cantrips: list[dict], count: int) -> list[dict]:
    """
    Pick a thematically varied cantrip set.
    When count >= 2 and both damage and non-damage cantrips exist,
    guarantees at least 1 damage cantrip and at least 1 non-damage cantrip.
    """
    if not cantrips or count <= 0:
        return []
    if len(cantrips) <= count:
        return list(cantrips)

    damage = [s for s in cantrips if s.get("damage_roll")]
    other  = [s for s in cantrips if not s.get("damage_roll")]

    if count >= 2 and damage and other:
        anchor   = random.choice(damage)
        rest     = [s for s in cantrips if s is not anchor]
        selected = [anchor] + random.sample(rest, min(count - 1, len(rest)))
        return selected[:count]

    return random.sample(cantrips, count)


def present_cantrip_list(class_key: str, client) -> list[dict]:
    """Return the full cantrip list for manual selection (Milestone 5 wizard UI)."""
    return get_cantrips_for_class(class_key, client)


# ── Spell selection ────────────────────────────────────────────────────────────

def get_spells_for_class(class_key: str, max_level: int, client) -> list[dict]:
    """Fetch all slot-based spells (level 1–max_level) for a class from Open5e."""
    return client.get_spells(char_class=class_key, level_max=max_level, level_min=1)


def select_random_spells(spells: list[dict], count: int,
                          strategy: str = "balanced") -> list[dict]:
    """
    Select spells by strategy:
      "balanced" / "default" — ~50% damage, ~25% control, ~25% support
      "damage"               — ~70% damage, ~20% control, ~10% support
      "support"              — ~20% damage, ~20% control, ~60% support
    Fills any remainder from the uncategorized pool so the result is always
    exactly min(count, len(spells)) spells.
    """
    if not spells or count <= 0:
        return []
    if len(spells) <= count:
        return list(spells)

    RATIOS: dict[str, dict[str, float]] = {
        "balanced": {"damage": 0.50, "control": 0.25, "support": 0.25},
        "default":  {"damage": 0.50, "control": 0.25, "support": 0.25},
        "damage":   {"damage": 0.70, "control": 0.20, "support": 0.10},
        "support":  {"damage": 0.20, "control": 0.20, "support": 0.60},
    }
    ratios = RATIOS.get(strategy, RATIOS["balanced"])

    by_cat: dict[str, list[dict]] = {"damage": [], "control": [], "support": [], "utility": []}
    for s in spells:
        by_cat[_categorize_spell(s)].append(s)
    # Utility folds into the support pool for selection purposes
    support_pool = by_cat["support"] + by_cat["utility"]

    pools = {"damage": by_cat["damage"], "control": by_cat["control"], "support": support_pool}
    selected: list[dict] = []

    for cat, ratio in ratios.items():
        pool = [s for s in pools[cat] if s not in selected]
        n = min(int(count * ratio), len(pool))
        if n > 0:
            selected += random.sample(pool, n)

    # Fill any remaining slots from whatever is left
    needed = count - len(selected)
    if needed > 0:
        remainder = [s for s in spells if s not in selected]
        selected += random.sample(remainder, min(needed, len(remainder)))

    return selected[:count]


def present_spell_list(class_key: str, max_level: int, client) -> list[dict]:
    """Return the full spell list up to max_level for manual selection."""
    return get_spells_for_class(class_key, max_level, client)


# ── Main integration function ──────────────────────────────────────────────────

def build_spells_for_character(character: Character, client,
                                strategy: str = "balanced") -> Character:
    """
    Populate character.always_available (cantrips) and character.spells
    for caster characters. Non-casters are returned unchanged.

    Reads character.spell_selection_mode:
      "random"  — auto-selects spells (default, used until Milestone 5 wizard exists)
      "manual"  — leaves lists empty; wizard UI calls present_cantrip_list /
                  present_spell_list and populates the character itself

    Mutates and returns the character.
    """
    cls = character.char_class.lower()
    if cls not in CASTER_CLASSES:
        return character
    if character.spell_selection_mode != "random":
        return character

    lvl = character.level

    # Cantrips → always_available
    n_cantrips = get_cantrip_count(cls)
    if n_cantrips > 0:
        raw = get_cantrips_for_class(cls, client)
        chosen = select_random_cantrips(raw, n_cantrips)
        character.always_available = [spell_to_entry(s, char_level=lvl) for s in chosen]

    # Slot-based spells → spells
    max_slot = max(character.spell_slots.keys(), default=0)
    if max_slot > 0:
        raw = get_spells_for_class(cls, max_slot, client)
        n = get_spell_count(cls, lvl, character)
        chosen = select_random_spells(raw, n, strategy)
        character.spells = [
            spell_to_entry(
                s,
                char_level=lvl,
                slots_total=character.spell_slots.get(s.get("level", 1), 0),
            )
            for s in chosen
        ]

    return character
