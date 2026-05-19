"""
Tests for the rules engine and ability score assignment.
Run with: pytest tests/test_rules.py -v
"""
import pytest
from engine.character import Character, AbilityScores
from engine.ability_scores import (
    generate_scores, assign_scores_in_order, apply_racial_bonuses,
    validate_point_buy, STANDARD_ARRAY, ABILITIES
)
from engine.rules import (
    derive_stats, select_sheet_variant, proficiency_bonus,
    ability_modifier, get_spell_slots, calc_max_hp,
    get_hit_die, calc_spell_save_dc
)


# ── Ability modifier ──────────────────────────────────────────────────────────

class TestAbilityModifier:
    def test_score_10_is_zero(self):    assert ability_modifier(10) == 0
    def test_score_11_is_zero(self):    assert ability_modifier(11) == 0
    def test_score_12_is_plus1(self):   assert ability_modifier(12) == 1
    def test_score_8_is_minus1(self):   assert ability_modifier(8) == -1
    def test_score_18_is_plus4(self):   assert ability_modifier(18) == 4
    def test_score_20_is_plus5(self):   assert ability_modifier(20) == 5
    def test_score_1_is_minus5(self):   assert ability_modifier(1) == -5


# ── Proficiency bonus ─────────────────────────────────────────────────────────

class TestProficiencyBonus:
    def test_levels_1_to_4(self):
        for lvl in range(1, 5):
            assert proficiency_bonus(lvl) == 2
    def test_level_5(self):
        assert proficiency_bonus(5) == 3


# ── Sheet variant selection ───────────────────────────────────────────────────

class TestSheetVariant:
    def test_martial_classes(self):
        for cls in ["Barbarian", "Fighter", "Monk", "Rogue"]:
            assert select_sheet_variant(cls) == "martial", f"{cls} should be martial"

    def test_caster_classes(self):
        for cls in ["Wizard", "Sorcerer", "Bard", "Cleric",
                    "Druid", "Warlock", "Paladin", "Ranger"]:
            assert select_sheet_variant(cls) == "caster", f"{cls} should be caster"

    def test_case_insensitive(self):
        assert select_sheet_variant("WIZARD") == "caster"
        assert select_sheet_variant("fighter") == "martial"


# ── Hit die and HP ────────────────────────────────────────────────────────────

class TestHP:
    def test_fighter_hit_die(self):   assert get_hit_die("fighter") == 10
    def test_wizard_hit_die(self):    assert get_hit_die("wizard") == 6
    def test_barbarian_hit_die(self): assert get_hit_die("barbarian") == 12

    def test_fighter_level1_hp(self):
        # d10 + CON mod(0) = 10
        assert calc_max_hp("fighter", 1, 0) == 10

    def test_fighter_level1_con_bonus(self):
        # d10 + CON mod(+2) = 12
        assert calc_max_hp("fighter", 1, 2) == 12

    def test_wizard_level1_hp(self):
        # d6 + CON mod(0) = 6
        assert calc_max_hp("wizard", 1, 0) == 6

    def test_fighter_level5_hp(self):
        # Level 1: 10, Levels 2-5: (5+1+0)*4 = 24, Total = 34
        # avg per level for d10 = (10//2)+1 = 6
        assert calc_max_hp("fighter", 5, 0) == 10 + 6 * 4

    def test_minimum_hp_is_1(self):
        # Even with -5 CON modifier, HP should be at least 1
        assert calc_max_hp("wizard", 1, -5) == 1


# ── Spell slots ───────────────────────────────────────────────────────────────

class TestSpellSlots:
    def test_wizard_level1_slots(self):
        assert get_spell_slots("wizard", 1) == {1: 2}

    def test_wizard_level5_slots(self):
        slots = get_spell_slots("wizard", 5)
        assert slots[1] == 4
        assert slots[2] == 3
        assert slots[3] == 2

    def test_paladin_level1_no_slots(self):
        # Half-casters get no slots until level 2
        assert get_spell_slots("paladin", 1) == {}

    def test_paladin_level2_gets_slots(self):
        assert get_spell_slots("paladin", 2) == {1: 2}

    def test_fighter_no_slots(self):
        assert get_spell_slots("fighter", 5) == {}

    def test_warlock_pact_magic(self):
        # Warlocks use pact magic — 2 slots at level 2
        assert get_spell_slots("warlock", 2) == {1: 2}
        # Level 3: two 2nd-level slots
        assert get_spell_slots("warlock", 3) == {2: 2}


# ── Full derive_stats integration ─────────────────────────────────────────────

class TestDeriveStats:

    def _fighter(self, level=1, scores=None):
        char = Character()
        char.char_class = "Fighter"
        char.level = level
        char.ability_scores = scores or AbilityScores(
            strength=16, dexterity=14, constitution=14,
            intelligence=10, wisdom=12, charisma=8
        )
        return derive_stats(char)

    def _wizard(self, level=1, scores=None):
        char = Character()
        char.char_class = "Wizard"
        char.level = level
        char.ability_scores = scores or AbilityScores(
            strength=8, dexterity=14, constitution=12,
            intelligence=17, wisdom=13, charisma=10
        )
        return derive_stats(char)

    def test_fighter_sheet_variant(self):
        assert self._fighter().sheet_variant == "martial"

    def test_wizard_sheet_variant(self):
        assert self._wizard().sheet_variant == "caster"

    def test_fighter_proficiency_bonus(self):
        assert self._fighter(level=1).proficiency_bonus == 2
        assert self._fighter(level=5).proficiency_bonus == 3

    def test_fighter_hit_dice(self):
        assert self._fighter().hit_dice == "d10"

    def test_fighter_max_hp_level1(self):
        # STR16(+3) DEX14(+2) CON14(+2) — HP = 10 + 2 = 12
        char = self._fighter(level=1)
        assert char.max_hp == 12

    def test_fighter_initiative(self):
        # DEX 14 = +2 modifier
        assert self._fighter().initiative == 2

    def test_fighter_armor_class(self):
        # Base AC = 10 + DEX mod (2) = 12
        assert self._fighter().armor_class == 12

    def test_fighter_saving_throws(self):
        saves = self._fighter().saving_throw_proficiencies
        assert "constitution" in saves
        assert "strength" in saves

    def test_wizard_spellcasting_ability(self):
        assert self._wizard().spellcasting_ability == "Intelligence"

    def test_wizard_spell_save_dc_level1(self):
        # INT 17 = +3, prof = 2, DC = 8 + 2 + 3 = 13
        assert self._wizard(level=1).spell_save_dc == 13

    def test_wizard_spell_attack_bonus_level1(self):
        # INT 17 = +3, prof = 2, bonus = 5
        assert self._wizard(level=1).spell_attack_bonus == 5

    def test_wizard_has_spell_slots(self):
        assert self._wizard(level=1).spell_slots == {1: 2}
        assert self._wizard(level=5).spell_slots[3] == 2

    def test_fighter_no_spell_slots(self):
        assert self._fighter().spell_slots == {}

    def test_fighter_no_spellcasting_ability(self):
        assert self._fighter().spellcasting_ability == ""

    def test_passive_perception_no_prof(self):
        # WIS 12 = +1, no perception prof, passive = 11
        char = self._fighter()
        assert char.passive_perception == 11

    def test_passive_perception_with_prof(self):
        # WIS 12 = +1, prof bonus 2, with perception = 13
        char = self._fighter()
        char.skill_proficiencies = ["perception"]
        derive_stats(char)  # re-derive with skill set
        assert char.passive_perception == 13


# ── Ability score assignment ──────────────────────────────────────────────────

class TestAbilityScoreAssignment:

    def test_assign_in_order_default(self):
        scores = [15, 14, 13, 12, 10, 8]
        result = assign_scores_in_order(scores)
        assert result.strength == 15
        assert result.dexterity == 14
        assert result.charisma == 8

    def test_assign_in_order_custom(self):
        scores = [15, 14, 13, 12, 10, 8]
        order = ["intelligence", "dexterity", "constitution",
                 "strength", "wisdom", "charisma"]
        result = assign_scores_in_order(scores, order)
        assert result.intelligence == 15
        assert result.dexterity == 14

    def test_racial_bonus_applied(self):
        base = AbilityScores(dexterity=14, intelligence=10)
        bonuses = {"dexterity": 2, "intelligence": 1}
        result = apply_racial_bonuses(base, bonuses)
        assert result.dexterity == 16
        assert result.intelligence == 11

    def test_racial_bonus_caps_at_20(self):
        base = AbilityScores(strength=19)
        result = apply_racial_bonuses(base, {"strength": 3})
        assert result.strength == 20

    def test_point_buy_valid(self):
        # 15(9) + 14(7) + 13(5) + 8(0) + 8(0) + 8(0) = 21 points — valid
        scores = {"strength": 15, "dexterity": 14, "constitution": 13,
                  "intelligence": 8, "wisdom": 8, "charisma": 8}
        valid, cost, msg = validate_point_buy(scores)
        assert valid
        assert cost == 21

    def test_point_buy_exactly_at_budget(self):
        # 15(9) + 8(0)*5 = 9 points — valid
        scores = {"strength": 15, "dexterity": 8, "constitution": 8,
                  "intelligence": 8, "wisdom": 8, "charisma": 8}
        valid, cost, msg = validate_point_buy(scores)
        assert valid
        assert cost == 9

    def test_point_buy_over_max_score(self):
        scores = {a: 8 for a in ABILITIES}
        scores["strength"] = 16  # over the max of 15
        valid, cost, msg = validate_point_buy(scores)
        assert not valid

    def test_generate_standard_array(self):
        scores = generate_scores("standard_array")
        assert sorted(scores, reverse=True) == sorted(STANDARD_ARRAY, reverse=True)

    def test_generate_4d6_drop1_range(self):
        for _ in range(10):  # run multiple times for randomness coverage
            scores = generate_scores("random_4d6_drop1")
            assert len(scores) == 6
            assert all(3 <= s <= 18 for s in scores)
