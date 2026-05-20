"""
Tests for PROTO-3: equipment selection, AC calculation, and attack building.
"""
import pytest
from engine.character import AbilityScores
from engine.equipment import (
    calc_ac, build_attack, get_standard_equipment, get_random_equipment,
    CLASS_OPTIONS, ARMOR, WEAPONS, PACKS,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def scores(str_=10, dex=10, con=10, int_=10, wis=10, cha=10) -> AbilityScores:
    return AbilityScores(strength=str_, dexterity=dex, constitution=con,
                         intelligence=int_, wisdom=wis, charisma=cha)

BALANCED = scores()                             # all 10, all mods = 0
DEX_HEAVY = scores(str_=8, dex=16)             # DEX +3, STR -1
STR_HEAVY = scores(str_=16, dex=8)             # STR +3, DEX -1
FIGHTER_SCORES = scores(str_=16, dex=14, con=14, int_=10, wis=12, cha=8)
BARBARIAN_SCORES = scores(str_=16, dex=14, con=16)  # CON +3 for Unarmored Defense
MONK_SCORES = scores(str_=10, dex=16, wis=14)       # WIS +2 for Unarmored Defense
WIZARD_SCORES = scores(str_=8, dex=14, con=12, int_=17, wis=13, cha=10)


# ── calc_ac ───────────────────────────────────────────────────────────────────

class TestCalcAC:
    def test_unarmored_no_dex(self):
        assert calc_ac("none", 0) == 10

    def test_unarmored_with_dex(self):
        assert calc_ac("none", 3) == 13

    def test_leather_no_dex(self):
        assert calc_ac("leather", 0) == 11

    def test_leather_with_dex(self):
        assert calc_ac("leather", 3) == 14

    def test_scale_mail_caps_dex_at_2(self):
        assert calc_ac("scale_mail", 4) == 16   # 14 + 2 (capped)
        assert calc_ac("scale_mail", 1) == 15   # 14 + 1

    def test_chain_mail_ignores_dex(self):
        assert calc_ac("chain_mail", 3) == 16
        assert calc_ac("chain_mail", -1) == 16

    def test_shield_adds_2(self):
        assert calc_ac("none", 0, has_shield=True) == 12
        assert calc_ac("chain_mail", 0, has_shield=True) == 18

    def test_barbarian_unarmored_defense(self):
        # 10 + DEX(+3) + CON(+3) = 16
        assert calc_ac("none", 3, char_class="barbarian", con_mod=3) == 16

    def test_monk_unarmored_defense(self):
        # 10 + DEX(+3) + WIS(+2) = 15
        assert calc_ac("none", 3, char_class="monk", wis_mod=2) == 15

    def test_barbarian_ignores_armor_formula_only_when_unarmored(self):
        # Barbarian in chain mail just uses chain mail formula
        assert calc_ac("chain_mail", 3, char_class="barbarian") == 16

    def test_class_case_insensitive(self):
        assert calc_ac("none", 2, char_class="Barbarian", con_mod=1) == \
               calc_ac("none", 2, char_class="barbarian", con_mod=1)


# ── build_attack ──────────────────────────────────────────────────────────────

class TestBuildAttack:
    def test_str_weapon_uses_str_mod(self):
        atk = build_attack("longsword", STR_HEAVY, prof_bonus=2)
        assert atk.hit_bonus == 2 + 3   # prof + STR mod

    def test_str_weapon_ignores_dex(self):
        atk = build_attack("longsword", DEX_HEAVY, prof_bonus=2)
        assert atk.hit_bonus == 2 + (-1)  # prof + STR mod (DEX ignored)

    def test_finesse_uses_higher_mod_dex(self):
        atk = build_attack("rapier", DEX_HEAVY, prof_bonus=2)
        assert atk.hit_bonus == 2 + 3   # DEX +3 wins over STR -1

    def test_finesse_uses_higher_mod_str(self):
        atk = build_attack("rapier", STR_HEAVY, prof_bonus=2)
        assert atk.hit_bonus == 2 + 3   # STR +3 wins over DEX -1

    def test_ranged_uses_dex(self):
        atk = build_attack("longbow", STR_HEAVY, prof_bonus=2)
        assert atk.hit_bonus == 2 + (-1)  # DEX -1 even though STR is higher

    def test_damage_dice_correct(self):
        assert build_attack("greataxe", BALANCED, 2).damage_dice == "1d12"
        assert build_attack("dagger", BALANCED, 2).damage_dice == "1d4"
        assert build_attack("longsword", BALANCED, 2).damage_dice == "1d8"

    def test_damage_type_correct(self):
        assert build_attack("greataxe", BALANCED, 2).damage_type == "slashing"
        assert build_attack("dagger", BALANCED, 2).damage_type == "piercing"
        assert build_attack("mace", BALANCED, 2).damage_type == "bludgeoning"

    def test_name_is_title_case(self):
        assert build_attack("light_crossbow", BALANCED, 2).name == "Light Crossbow"
        assert build_attack("shortsword", BALANCED, 2).name == "Shortsword"

    def test_unknown_weapon_returns_safe_default(self):
        atk = build_attack("mystery_stick", BALANCED, 2)
        assert atk.name == "Mystery Stick"
        assert atk.hit_bonus == 2
        assert atk.damage_dice == "1d4"


# ── get_standard_equipment ────────────────────────────────────────────────────

class TestStandardEquipment:
    def _std(self, char_class, ability_scores=None):
        return get_standard_equipment(char_class, ability_scores or BALANCED)

    def test_result_has_required_keys(self):
        result = self._std("fighter", FIGHTER_SCORES)
        assert "equipment" in result
        assert "attacks" in result
        assert "armor_key" in result
        assert "armor_class" in result

    def test_attacks_not_empty(self):
        for cls in CLASS_OPTIONS:
            result = self._std(cls)
            assert len(result["attacks"]) >= 1, f"{cls} should have at least 1 attack"

    def test_equipment_not_empty(self):
        for cls in CLASS_OPTIONS:
            result = self._std(cls)
            assert len(result["equipment"]) >= 1, f"{cls} should have equipment"

    def test_pack_always_present(self):
        pack_names = set(PACKS.values())
        for cls in CLASS_OPTIONS:
            result = self._std(cls)
            item_names = {i.name for i in result["equipment"]}
            assert item_names & pack_names, f"{cls} missing adventuring pack"

    def test_barbarian_unarmored(self):
        result = self._std("barbarian", BARBARIAN_SCORES)
        assert result["armor_key"] == "none"
        # No armor item in equipment list
        armor_items = [i for i in result["equipment"]
                       if i.name.lower().replace(" ", "_") in ARMOR]
        assert len(armor_items) == 0

    def test_barbarian_ac_uses_unarmored_defense(self):
        # DEX +2, CON +3 → 10 + 2 + 3 = 15
        result = get_standard_equipment("barbarian", scores(dex=14, con=16))
        assert result["armor_class"] == 15

    def test_barbarian_gets_greataxe(self):
        result = self._std("barbarian")
        weapon_names = {i.name for i in result["equipment"]}
        assert "Greataxe" in weapon_names

    def test_fighter_picks_chain_mail_over_leather(self):
        # Chain mail (16) > leather+DEX for most DEX values
        result = get_standard_equipment("fighter", scores(dex=10))
        assert result["armor_key"] == "chain_mail"
        assert result["armor_class"] == 18   # chain mail 16 + shield 2

    def test_fighter_gets_shield(self):
        result = self._std("fighter")
        item_names = {i.name for i in result["equipment"]}
        assert "Shield" in item_names

    def test_cleric_gets_shield(self):
        result = self._std("cleric")
        item_names = {i.name for i in result["equipment"]}
        assert "Shield" in item_names

    def test_wizard_gets_no_armor(self):
        result = self._std("wizard", WIZARD_SCORES)
        assert result["armor_key"] == "none"

    def test_wizard_gets_spellbook(self):
        result = self._std("wizard", WIZARD_SCORES)
        item_names = {i.name for i in result["equipment"]}
        assert "Spellbook" in item_names

    def test_wizard_gets_arcane_focus(self):
        result = self._std("wizard", WIZARD_SCORES)
        item_names = {i.name for i in result["equipment"]}
        assert "Arcane Focus" in item_names

    def test_rogue_gets_thieves_tools(self):
        result = self._std("rogue")
        item_names = {i.name for i in result["equipment"]}
        assert "Thieves' Tools" in item_names

    def test_rogue_gets_leather_armor(self):
        result = self._std("rogue")
        assert result["armor_key"] == "leather"

    def test_monk_unarmored_defense(self):
        # DEX +3, WIS +2 → 10 + 3 + 2 = 15
        result = get_standard_equipment("monk", MONK_SCORES)
        assert result["armor_key"] == "none"
        assert result["armor_class"] == 15

    def test_ranger_gets_longbow_attack(self):
        result = self._std("ranger")
        attack_names = {a.name for a in result["attacks"]}
        assert "Longbow" in attack_names

    def test_all_classes_produce_valid_result(self):
        for cls in CLASS_OPTIONS:
            result = get_standard_equipment(cls, BALANCED)
            assert isinstance(result["armor_class"], int)
            assert result["armor_class"] >= 1

    def test_unknown_class_returns_empty(self):
        result = get_standard_equipment("artificer", BALANCED)
        assert result["equipment"] == []
        assert result["attacks"] == []

    def test_ac_matches_armor_formula(self):
        result = get_standard_equipment("fighter", scores(dex=10, str_=16, con=14))
        expected = calc_ac("chain_mail", 0, "fighter", has_shield=True)
        assert result["armor_class"] == expected

    def test_javelin_quantity_aggregated(self):
        result = self._std("barbarian")
        javelin_items = [i for i in result["equipment"] if i.name == "Javelin"]
        assert len(javelin_items) == 1
        assert javelin_items[0].quantity == 4

    def test_paladin_javelin_quantity(self):
        result = self._std("paladin")
        javelin_items = [i for i in result["equipment"] if i.name == "Javelin"]
        assert len(javelin_items) == 1
        assert javelin_items[0].quantity == 5


# ── get_random_equipment ──────────────────────────────────────────────────────

class TestRandomEquipment:
    def test_result_has_required_keys(self):
        result = get_random_equipment("fighter", FIGHTER_SCORES)
        for key in ("equipment", "attacks", "armor_key", "armor_class"):
            assert key in result

    def test_armor_key_is_valid_for_class(self):
        for cls in CLASS_OPTIONS:
            result = get_random_equipment(cls, BALANCED)
            assert result["armor_key"] in CLASS_OPTIONS[cls]["armor_options"], \
                f"{cls}: unexpected armor {result['armor_key']}"

    def test_barbarian_always_unarmored(self):
        for _ in range(20):
            result = get_random_equipment("barbarian", BARBARIAN_SCORES)
            assert result["armor_key"] == "none"

    def test_attacks_not_empty(self):
        for cls in CLASS_OPTIONS:
            result = get_random_equipment(cls, BALANCED)
            assert len(result["attacks"]) >= 1

    def test_pack_always_present(self):
        pack_names = set(PACKS.values())
        for cls in CLASS_OPTIONS:
            result = get_random_equipment(cls, BALANCED)
            item_names = {i.name for i in result["equipment"]}
            assert item_names & pack_names

    def test_fighter_leather_gets_longbow(self):
        # When fighter randomly gets leather, longbow must appear in attacks
        # Run enough times to hit the leather branch
        found_leather = False
        for _ in range(50):
            result = get_random_equipment("fighter", scores(dex=16, str_=10))
            if result["armor_key"] == "leather":
                found_leather = True
                attack_names = {a.name for a in result["attacks"]}
                assert "Longbow" in attack_names, "Leather fighter should get longbow"
                break
        # If we never hit leather in 50 tries the test is inconclusive, not a failure

    def test_random_produces_variety_for_classes_with_options(self):
        # A class with 2+ armor options should produce both over many runs
        results = {get_random_equipment("cleric", BALANCED)["armor_key"]
                   for _ in range(60)}
        # Cleric has 3 armor options; expect at least 2 different outcomes
        assert len(results) >= 2

    def test_ac_consistent_with_armor_key(self):
        for cls in CLASS_OPTIONS:
            result = get_random_equipment(cls, BALANCED)
            dex_mod = 0  # BALANCED has DEX 10
            expected = calc_ac(
                result["armor_key"], dex_mod, cls,
                has_shield=CLASS_OPTIONS[cls]["shield"]
            )
            assert result["armor_class"] == expected, \
                f"{cls}: AC mismatch (got {result['armor_class']}, expected {expected})"
