#!/usr/bin/env bash
# setup_proto0.sh — Creates all PROTO-0 scaffold files for the OtG Character Generator
# Run from inside the DnD-CharacterSheet-Generator directory:
#   chmod +x setup_proto0.sh && ./setup_proto0.sh

set -e  # Stop on any error

echo "=== PROTO-0: Creating folder structure ==="
mkdir -p engine api pdf/field_maps ui data/cache tests
echo "✓ Folders created"

# ─── engine/__init__.py ────────────────────────────────────────────────────────
cat > engine/__init__.py << 'EOF'
"""Engine package: character rules, ability scores, equipment, spells, sources."""
EOF

# ─── engine/character.py ──────────────────────────────────────────────────────
cat > engine/character.py << 'EOF'
"""
Character dataclass — central data model for the OtG character generator.
All fields map to the OtG accessible character sheet (martial or caster variant).
Sheet variant is auto-selected based on class; player never chooses it.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AbilityScores:
    """The six core D&D ability scores."""
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10


@dataclass
class SpellEntry:
    """
    One row in the spellcasting shorthand table.
    Columns: Lvl | slots_total | slots_used | name | range | effect_dmg | flags
    flags: BA = bonus action, C = concentration, R = reaction, S = save required
    """
    level: int                   # 0 = cantrip / always-available
    name: str = ""
    range: str = ""              # e.g. "60 ft", "Touch", "Self"
    effect_dmg: str = ""         # e.g. "2d6 fire", "Restrained", "Heal 1d8"
    flags: str = ""              # e.g. "C", "BA", "R", "S"
    slots_total: int = 0         # 0 for cantrips
    slots_used: int = 0


@dataclass
class EquipmentItem:
    """One item in the character's equipment list."""
    name: str = ""
    quantity: int = 1
    source: str = "srd"          # "srd" or document__key from Open5e


@dataclass
class FeatureEntry:
    """
    One entry in the Features & Traits card-reference list.
    Displayed as: "Name — card" or "Name — <brief note>"
    DM handles full description; sheet is quick-reference only.
    """
    name: str = ""
    source_card: str = ""        # e.g. "card" or very short reminder note
    source: str = "srd"


@dataclass
class Character:
    """
    Central data model for a D&D 5e character.
    Prototype scope: levels 1-5, SRD + Open5e third-party sources.
    """

    # Identity
    name: str = "Unnamed Hero"
    player_name: str = ""
    level: int = 1               # 1-5 for prototype

    # Core choices
    race: str = ""
    race_source: str = "srd"
    char_class: str = ""
    class_source: str = "srd"
    background: str = ""
    background_source: str = "srd"

    # Sheet variant (auto-selected, never player-facing)
    # "martial" -> OtG martial sheet  |  "caster" -> OtG caster sheet
    sheet_variant: str = "martial"

    # Ability scores
    ability_scores: AbilityScores = field(default_factory=AbilityScores)
    ability_score_method: str = "standard_array"
    # Methods: "standard_array" | "point_buy" | "random_4d6_drop1" | "random_3d6"

    # Derived stats (computed by rules engine, stored here for PDF export)
    proficiency_bonus: int = 2
    initiative: int = 0
    armor_class: int = 10
    speed: int = 30
    max_hp: int = 0
    current_hp: int = 0
    hit_dice: str = ""           # e.g. "1d10"

    saving_throw_proficiencies: list[str] = field(default_factory=list)
    skill_proficiencies: list[str] = field(default_factory=list)
    skill_expertises: list[str] = field(default_factory=list)

    # Equipment
    equipment: list[EquipmentItem] = field(default_factory=list)
    equipment_selection_mode: str = "standard"
    # Modes: "standard" (system assigns best-fit) | "random" (randomized appropriate)

    # Spellcasting (caster sheet only)
    spellcasting_ability: str = ""
    spell_save_dc: int = 0
    spell_attack_bonus: int = 0

    # "Always Available": cantrips + racial at-will abilities (no slot cost)
    always_available: list[SpellEntry] = field(default_factory=list)

    # Slot-based spells (level 1-5 for prototype)
    spells: list[SpellEntry] = field(default_factory=list)
    spell_slots: dict[int, int] = field(default_factory=dict)  # {1: 2, 2: 1, ...}

    spell_selection_mode: str = "random"
    # Modes: "random" (appropriate for build) | "manual" (select from list)

    # Features & Traits (card-reference list — name + brief note, not prose)
    features: list[FeatureEntry] = field(default_factory=list)

    # Personality / backstory
    personality_traits: str = ""
    ideals: str = ""
    bonds: str = ""
    flaws: str = ""
    alignment: str = ""

    # Languages & proficiencies
    languages: list[str] = field(default_factory=list)
    tool_proficiencies: list[str] = field(default_factory=list)
    weapon_proficiencies: list[str] = field(default_factory=list)
    armor_proficiencies: list[str] = field(default_factory=list)

    # Passive perception
    passive_perception: int = 10

    # Meta
    experience_points: int = 0
    inspiration: bool = False

    def is_caster(self) -> bool:
        """Return True if this character uses the caster sheet variant."""
        return self.sheet_variant == "caster"

    def modifier(self, score: int) -> int:
        """Standard D&D ability score modifier formula."""
        return (score - 10) // 2

    def ability_modifier(self, ability: str) -> int:
        """Return the modifier for a named ability (e.g. 'strength')."""
        score = getattr(self.ability_scores, ability.lower(), 10)
        return self.modifier(score)
EOF

# ─── engine/rules.py ──────────────────────────────────────────────────────────
cat > engine/rules.py << 'EOF'
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
EOF

# ─── engine/ability_scores.py ────────────────────────────────────────────────
cat > engine/ability_scores.py << 'EOF'
"""
Ability score generation methods.
PROTO scope: standard array, point buy, 4d6 drop lowest, straight 3d6.
"""
import random
from typing import List

STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]

POINT_BUY_COSTS = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
POINT_BUY_BUDGET = 27
POINT_BUY_MIN = 8
POINT_BUY_MAX = 15


def roll_4d6_drop_lowest() -> int:
    """Roll 4d6, drop the lowest die, return the sum."""
    rolls = sorted([random.randint(1, 6) for _ in range(4)])
    return sum(rolls[1:])


def generate_scores(method: str) -> List[int]:
    """
    Generate 6 ability scores using the specified method.
    Returns a list of 6 integers (unassigned to abilities yet).
    """
    if method == "standard_array":
        return list(STANDARD_ARRAY)
    elif method == "random_4d6_drop1":
        return sorted([roll_4d6_drop_lowest() for _ in range(6)], reverse=True)
    elif method == "random_3d6":
        return sorted(
            [sum(random.randint(1, 6) for _ in range(3)) for _ in range(6)],
            reverse=True
        )
    elif method == "point_buy":
        # Returns base values; UI wizard handles player assignment
        return [POINT_BUY_MIN] * 6
    else:
        raise ValueError(f"Unknown ability score method: {method}")
EOF

# ─── engine/equipment.py ─────────────────────────────────────────────────────
cat > engine/equipment.py << 'EOF'
"""
Equipment selection logic.
PROTO scope: standard starting packs (by class) or randomized appropriate gear.
Data sourced from Open5e API (equipment endpoint) or local fallback.
"""
# TODO (PROTO-3): implement get_standard_equipment(char_class, background)
# TODO (PROTO-3): implement get_random_equipment(char_class, background)


def get_equipment(char_class: str, background: str, mode: str = "standard"):
    """
    Return appropriate starting equipment for the character.
    mode: "standard" = best-fit class pack | "random" = randomized but appropriate
    """
    raise NotImplementedError("Equipment selection not yet implemented — PROTO-3 task")
EOF

# ─── engine/spells.py ────────────────────────────────────────────────────────
cat > engine/spells.py << 'EOF'
"""
Spell selection logic.
PROTO scope: cantrips + level 1-3 spells (levels 1-5 cap).
Data sourced from Open5e API with document__key filtering for sources.
"""
# TODO (PROTO-4): implement get_spells_for_class(char_class, level, sources, mode)
# TODO (PROTO-4): implement get_cantrips(char_class, sources)
# TODO (PROTO-4): implement spell_slots_for_class(char_class, level) -> dict[int, int]
# TODO (PROTO-4): implement build_always_available(character) -> list[SpellEntry]


def get_spells(char_class: str, level: int, sources: list, mode: str = "random"):
    """
    Return appropriate spells for a caster character.
    mode: "random" = appropriate assortment | "manual" = returns list for selection
    sources: list of Open5e document__key values e.g. ["wotc-srd", "a5e"]
    """
    raise NotImplementedError("Spell selection not yet implemented — PROTO-4 task")
EOF

# ─── engine/source_manager.py ────────────────────────────────────────────────
cat > engine/source_manager.py << 'EOF'
"""
Source/document management for third-party content.
Maps Open5e document__key values to human-readable names.
Allows filtering API calls to specific sources (e.g. SRD only, or SRD + a5e).
"""
# Default: SRD only
DEFAULT_SOURCES = ["wotc-srd"]

# Known Open5e document keys (expand as needed)
KNOWN_SOURCES = {
    "wotc-srd": "D&D 5e SRD (Wizards of the Coast)",
    "a5e": "Level Up: Advanced 5th Edition (EN Publishing)",
    "menagerie": "Level Up Monstrous Menagerie",
    "taldorei": "Critical Role: Tal'Dorei Campaign Setting",
    "kp": "Kobold Press (various)",
    "cc": "Creature Codex",
    "tob": "Tome of Beasts",
    "tob2": "Tome of Beasts 2",
}


class SourceManager:
    """Manages which content sources are active for this character generation session."""

    def __init__(self, sources: list = None):
        self.active_sources = sources if sources is not None else list(DEFAULT_SOURCES)

    def add_source(self, key: str):
        if key not in self.active_sources:
            self.active_sources.append(key)

    def remove_source(self, key: str):
        self.active_sources = [s for s in self.active_sources if s != key]

    def get_filter_param(self) -> str:
        """Return Open5e API filter string for document__key__in."""
        return ",".join(self.active_sources)

    def list_known(self) -> dict:
        return dict(KNOWN_SOURCES)
EOF

# ─── api/__init__.py ─────────────────────────────────────────────────────────
cat > api/__init__.py << 'EOF'
"""API package: clients for Open5e and dnd5eapi.co."""
EOF

# ─── api/open5e_client.py ────────────────────────────────────────────────────
cat > api/open5e_client.py << 'EOF'
"""
Open5e API client.
Base URL: https://api.open5e.com/v2/
Supports document__key filtering for third-party source control.
All requests are cached locally in data/cache/ to reduce API calls.
"""
import json
import time
from pathlib import Path

# TODO (PROTO-1): implement full client with caching and pagination
# TODO (PROTO-1): add retry logic and error handling

BASE_URL = "https://api.open5e.com/v2"
CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
CACHE_TTL_SECONDS = 86400  # 24 hours


class Open5eClient:
    """
    Thin wrapper around the Open5e REST API.
    Handles caching, pagination, and source filtering.
    """

    def __init__(self, sources: list = None, cache_dir: Path = None):
        """
        sources: list of document__key values to filter by (e.g. ["wotc-srd", "a5e"])
        cache_dir: override the default cache directory
        """
        self.sources = sources or ["wotc-srd"]
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, endpoint: str, params: dict) -> Path:
        """Generate a deterministic cache file path for a request."""
        key = endpoint.replace("/", "_") + "_" + "_".join(
            f"{k}={v}" for k, v in sorted(params.items())
        )
        return self.cache_dir / f"{key}.json"

    def _is_cache_fresh(self, path: Path) -> bool:
        """Return True if cache file exists and is within TTL."""
        if not path.exists():
            return False
        age = time.time() - path.stat().st_mtime
        return age < CACHE_TTL_SECONDS

    def get(self, endpoint: str, params: dict = None) -> dict:
        """
        GET /v2/{endpoint} with optional query params.
        Automatically adds document__key__in filter if sources are set.
        Returns the full JSON response dict.
        """
        raise NotImplementedError("Open5eClient.get() not yet implemented — PROTO-1 task")

    def get_races(self) -> list:
        """Return list of available races filtered by active sources."""
        raise NotImplementedError("get_races() not yet implemented — PROTO-1 task")

    def get_classes(self) -> list:
        """Return list of available classes filtered by active sources."""
        raise NotImplementedError("get_classes() not yet implemented — PROTO-1 task")

    def get_backgrounds(self) -> list:
        """Return list of available backgrounds filtered by active sources."""
        raise NotImplementedError("get_backgrounds() not yet implemented — PROTO-1 task")

    def get_spells(self, char_class: str = None, level_max: int = 5) -> list:
        """Return spells filtered by class and level cap."""
        raise NotImplementedError("get_spells() not yet implemented — PROTO-4 task")

    def get_equipment(self) -> list:
        """Return equipment list filtered by active sources."""
        raise NotImplementedError("get_equipment() not yet implemented — PROTO-3 task")
EOF

# ─── pdf/__init__.py ─────────────────────────────────────────────────────────
cat > pdf/__init__.py << 'EOF'
"""PDF package: OtG character sheet field mapping and form filling."""
EOF

# ─── pdf/filler.py ───────────────────────────────────────────────────────────
cat > pdf/filler.py << 'EOF'
"""
OtG PDF filler — wraps the existing fill_character_sheet.py logic.
Accepts a Character dataclass and outputs a filled OtG PDF.
Auto-selects the correct sheet variant (martial or caster) based on character.sheet_variant.

Sheet PDFs should be placed in:
  pdf/field_maps/otg_martial.pdf   -- OtG martial sheet (pages 1-2)
  pdf/field_maps/otg_caster.pdf    -- OtG caster sheet  (pages 1-4, with spellcasting)
"""
from pathlib import Path
from engine.character import Character

# TODO (Milestone 4): implement full OtG field mapping
# TODO: map Character fields to OtG PDF field names using field_maps/otg_field_map.json

FIELD_MAPS_DIR = Path(__file__).parent / "field_maps"


def character_to_field_values(character: Character) -> dict:
    """
    Convert a Character dataclass to a flat dict of {pdf_field_name: value}.
    This is the bridge between the rules engine and the existing PDF filler.
    """
    raise NotImplementedError(
        "character_to_field_values() not yet implemented — Milestone 4 task"
    )


def fill_otg_sheet(character: Character, output_path: Path) -> Path:
    """
    Fill the appropriate OtG sheet PDF for the given character.
    Auto-selects martial or caster variant based on character.sheet_variant.
    Returns the path to the filled PDF.
    """
    raise NotImplementedError(
        "fill_otg_sheet() not yet implemented — Milestone 4 task"
    )
EOF

# ─── ui/__init__.py ──────────────────────────────────────────────────────────
cat > ui/__init__.py << 'EOF'
"""UI package: step-by-step character creation wizard."""
EOF

# ─── ui/wizard.py ────────────────────────────────────────────────────────────
cat > ui/wizard.py << 'EOF'
"""
Character creation wizard -- guides player through the 7-step flow.

Step 1: Select race         (from Open5e, filtered by active sources)
Step 2: Select class        (from Open5e, filtered by active sources)
Step 3: Select background   (from Open5e, filtered by active sources)
Step 4: Ability scores      (standard array / point buy / random roll)
Step 5: Choose level        (1-5 for prototype)
Step 6: Equipment           (standard best-fit OR randomized appropriate)
Step 7: Spells              (random OR select from list -- skipped for non-casters)

Target deployment: Apache server (GoDaddy) -> Flask web UI is the end goal.
Desktop tkinter build available for local testing.
"""
# TODO (Milestone 5): implement wizard UI


class CharacterWizard:
    """
    Step-by-step character creation wizard.
    Drives the full 7-step flow and returns a completed Character.
    """

    def __init__(self, source_manager=None):
        raise NotImplementedError("CharacterWizard not yet implemented — Milestone 5 task")

    def run(self):
        """Execute the full wizard flow and return a completed Character."""
        raise NotImplementedError("CharacterWizard.run() not yet implemented")
EOF

# ─── tests/__init__.py ───────────────────────────────────────────────────────
cat > tests/__init__.py << 'EOF'
"""Test suite for the OtG D&D Character Generator."""
EOF

# ─── tests/test_character.py ─────────────────────────────────────────────────
cat > tests/test_character.py << 'EOF'
"""
Basic smoke tests for the Character dataclass and ability score generator.
Run with: pytest tests/
"""
import pytest
from engine.character import Character, AbilityScores, SpellEntry, FeatureEntry
from engine.ability_scores import generate_scores, STANDARD_ARRAY
from engine.rules import select_sheet_variant, proficiency_bonus


class TestCharacterDataclass:

    def test_default_character(self):
        char = Character()
        assert char.name == "Unnamed Hero"
        assert char.level == 1
        assert char.sheet_variant == "martial"
        assert char.is_caster() is False

    def test_modifier_calculation(self):
        char = Character()
        assert char.modifier(10) == 0
        assert char.modifier(18) == 4
        assert char.modifier(8) == -1
        assert char.modifier(20) == 5

    def test_ability_modifier(self):
        char = Character()
        char.ability_scores = AbilityScores(strength=16)
        assert char.ability_modifier("strength") == 3

    def test_spell_entry_defaults(self):
        spell = SpellEntry(level=1, name="Magic Missile")
        assert spell.slots_used == 0
        assert spell.flags == ""

    def test_feature_entry(self):
        feat = FeatureEntry(name="Second Wind", source_card="card")
        assert feat.source == "srd"


class TestAbilityScores:

    def test_standard_array_length(self):
        scores = generate_scores("standard_array")
        assert len(scores) == 6

    def test_standard_array_values(self):
        scores = generate_scores("standard_array")
        assert sorted(scores, reverse=True) == sorted(STANDARD_ARRAY, reverse=True)

    def test_random_4d6_drop1(self):
        scores = generate_scores("random_4d6_drop1")
        assert len(scores) == 6
        assert all(3 <= s <= 18 for s in scores)

    def test_random_3d6(self):
        scores = generate_scores("random_3d6")
        assert len(scores) == 6
        assert all(3 <= s <= 18 for s in scores)

    def test_unknown_method_raises(self):
        with pytest.raises(ValueError):
            generate_scores("made_up_method")


class TestRulesEngine:

    def test_sheet_variant_caster(self):
        assert select_sheet_variant("Wizard") == "caster"
        assert select_sheet_variant("wizard") == "caster"
        assert select_sheet_variant("Bard") == "caster"
        assert select_sheet_variant("Cleric") == "caster"

    def test_sheet_variant_martial(self):
        assert select_sheet_variant("Fighter") == "martial"
        assert select_sheet_variant("Barbarian") == "martial"
        assert select_sheet_variant("Rogue") == "martial"

    def test_proficiency_bonus(self):
        assert proficiency_bonus(1) == 2
        assert proficiency_bonus(4) == 2
        assert proficiency_bonus(5) == 3
EOF

# ─── data/cache/.gitkeep ─────────────────────────────────────────────────────
cat > data/cache/.gitkeep << 'EOF'
# Cache directory for Open5e API responses (24-hour TTL)
# This directory is tracked in git but its contents are gitignored
EOF

# ─── Update requirements.txt ─────────────────────────────────────────────────
cat > requirements.txt << 'EOF'
pypdf>=5.1.0
pyinstaller>=6.0.0
requests>=2.32.0
pytest>=8.0.0
EOF

# ─── Append to .gitignore ─────────────────────────────────────────────────────
cat >> .gitignore << 'EOF'

# API cache
data/cache/*.json

# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
EOF

echo ""
echo "=== PROTO-0: All files created successfully! ==="
echo ""
echo "Next steps:"
echo "  1. pip install -r requirements.txt"
echo "  2. pytest tests/ -v"
echo "  3. git add ."
echo '  4. git commit -m "PROTO-0: Scaffold engine/, api/, pdf/, ui/, tests/ packages"'
echo "  5. git push origin master"