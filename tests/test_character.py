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
