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
class Attack:
    """One row in the Attacks & Spellcasting section of the sheet."""
    name: str = ""
    hit_bonus: int = 0
    damage_dice: str = ""
    damage_type: str = ""
    notes: str = ""


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

    # Attacks (populated by equipment step)
    attacks: list[Attack] = field(default_factory=list)

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
