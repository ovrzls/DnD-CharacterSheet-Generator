"""
Tests for pdf/filler.py — character_to_field_values and fill_otg_sheet.
All tests are pure-Python (no PDF file I/O) except TestFillOtgSheet which
exercises the full pipeline against the real blank sheet.
"""
import pytest
from pathlib import Path
from engine.character import (
    Character, AbilityScores, Attack, EquipmentItem,
    FeatureEntry, SpellEntry,
)
from engine.rules import derive_stats
from pdf.filler import character_to_field_values, fill_otg_sheet, SHEET_PDF


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fighter(level: int = 1) -> Character:
    char = Character(
        name="Aldric",
        char_class="fighter",
        level=level,
        ability_scores=AbilityScores(
            strength=16, dexterity=12, constitution=14,
            intelligence=10, wisdom=10, charisma=8,
        ),
    )
    derive_stats(char)
    return char


def _make_wizard(level: int = 3) -> Character:
    char = Character(
        name="Mira",
        char_class="wizard",
        level=level,
        ability_scores=AbilityScores(
            strength=8, dexterity=14, constitution=12,
            intelligence=16, wisdom=12, charisma=10,
        ),
    )
    derive_stats(char)
    return char


# ---------------------------------------------------------------------------
# character_to_field_values — page1
# ---------------------------------------------------------------------------

class TestPage1Identity:
    def test_name(self):
        v = character_to_field_values(_make_fighter())
        assert v["page1"]["name"] == "Aldric"

    def test_class_and_level(self):
        v = character_to_field_values(_make_fighter(level=3))
        assert v["page1"]["char_class"] == "Fighter"
        assert v["page1"]["level"] == "3"

    def test_inspiration_on(self):
        char = _make_fighter()
        char.inspiration = True
        v = character_to_field_values(char)
        assert v["page1"]["inspiration"] == "✓"

    def test_inspiration_off(self):
        char = _make_fighter()
        char.inspiration = False
        v = character_to_field_values(char)
        assert v["page1"]["inspiration"] == ""


class TestPage1AbilityScores:
    def test_str_score(self):
        v = character_to_field_values(_make_fighter())
        assert v["page1"]["str_score"] == "16"

    def test_int_score_wizard(self):
        v = character_to_field_values(_make_wizard())
        assert v["page1"]["int_score"] == "16"

    def test_all_six_present(self):
        v = character_to_field_values(_make_fighter())
        for key in ("str_score", "dex_score", "con_score", "int_score", "wis_score", "cha_score"):
            assert key in v["page1"]


class TestPage1Skills:
    def test_unskilled_acrobatics(self):
        # Fighter lv1, DEX 12 → mod +1, no proficiency
        v = character_to_field_values(_make_fighter())
        assert v["page1"]["skill_acrobatics"] == "+1"

    def test_proficient_athletics_fighter(self):
        # STR 16 → mod +3, prof +2 = +5 when proficiency is set
        char = _make_fighter()
        char.skill_proficiencies = list(set(char.skill_proficiencies) | {"Athletics"})
        v = character_to_field_values(char)
        assert v["page1"]["skill_athletics"] == "+5"

    def test_arcana_wizard_proficient(self):
        # INT 16 → mod +3, prof +2 = +5 when proficiency is set
        char = _make_wizard()
        char.skill_proficiencies = list(set(char.skill_proficiencies) | {"Arcana"})
        v = character_to_field_values(char)
        assert v["page1"]["skill_arcana"] == "+5"

    def test_expertise_doubles_prof(self):
        char = _make_fighter()
        char.skill_expertises = ["Athletics"]
        char.skill_proficiencies = list(set(char.skill_proficiencies) - {"Athletics"})
        v = character_to_field_values(char)
        # STR +3, expertise +4 = +7
        assert v["page1"]["skill_athletics"] == "+7"

    def test_negative_modifier_shown(self):
        char = _make_wizard()
        # CHA is 10 → mod 0; STR is 8 → mod -1
        v = character_to_field_values(char)
        assert v["page1"]["skill_athletics"] == "-1"

    def test_all_18_skills_present(self):
        v = character_to_field_values(_make_fighter())
        skills = [
            "skill_acrobatics", "skill_animal_handling", "skill_arcana",
            "skill_athletics", "skill_deception", "skill_history",
            "skill_insight", "skill_intimidation", "skill_investigation",
            "skill_medicine", "skill_nature", "skill_perception",
            "skill_performance", "skill_persuasion", "skill_religion",
            "skill_sleight_of_hand", "skill_stealth", "skill_survival",
        ]
        for s in skills:
            assert s in v["page1"], f"Missing {s}"


class TestPage1PassiveScores:
    def test_passive_perception_uses_char_field(self):
        char = _make_fighter()
        char.passive_perception = 13
        v = character_to_field_values(char)
        assert v["page1"]["passive_perception"] == "13"

    def test_passive_investigation_no_prof(self):
        char = _make_fighter()
        # INT 10 → mod 0, no Investigation proficiency → 10
        char.skill_proficiencies = [s for s in char.skill_proficiencies if s != "Investigation"]
        v = character_to_field_values(char)
        assert v["page1"]["passive_investigation"] == "10"

    def test_passive_investigation_with_prof(self):
        char = _make_fighter()
        char.skill_proficiencies = list(set(char.skill_proficiencies) | {"Investigation"})
        # INT 10 → 0 + prof 2 + 10 = 12
        v = character_to_field_values(char)
        assert v["page1"]["passive_investigation"] == "12"


class TestPage1Equipment:
    def test_inventory_single_item(self):
        char = _make_fighter()
        char.equipment = [EquipmentItem(name="Torch", quantity=1)]
        v = character_to_field_values(char)
        assert "Torch" in v["page1"]["inventory"]

    def test_inventory_quantity_shown(self):
        char = _make_fighter()
        char.equipment = [EquipmentItem(name="Arrow", quantity=20)]
        v = character_to_field_values(char)
        assert "20x Arrow" in v["page1"]["inventory"]

    def test_inventory_quantity_1_no_prefix(self):
        char = _make_fighter()
        char.equipment = [EquipmentItem(name="Shield", quantity=1)]
        v = character_to_field_values(char)
        assert "1x Shield" not in v["page1"]["inventory"]
        assert "Shield" in v["page1"]["inventory"]

    def test_empty_inventory(self):
        char = _make_fighter()
        char.equipment = []
        v = character_to_field_values(char)
        assert v["page1"]["inventory"] == []


class TestPage1Proficiencies:
    def test_proficiencies_text_includes_armor(self):
        char = _make_fighter()
        char.armor_proficiencies = ["Light Armor", "Heavy Armor"]
        v = character_to_field_values(char)
        assert "Light Armor" in v["page1"]["proficiencies_text"]
        assert "Heavy Armor" in v["page1"]["proficiencies_text"]

    def test_proficiencies_text_includes_languages(self):
        char = _make_fighter()
        char.languages = ["Common", "Dwarvish"]
        v = character_to_field_values(char)
        assert "Common" in v["page1"]["proficiencies_text"]

    def test_proficiencies_empty_when_nothing_set(self):
        char = _make_fighter()
        char.armor_proficiencies = []
        char.weapon_proficiencies = []
        char.tool_proficiencies = []
        char.languages = []
        v = character_to_field_values(char)
        assert v["page1"]["proficiencies_text"] == ""


# ---------------------------------------------------------------------------
# character_to_field_values — page2
# ---------------------------------------------------------------------------

class TestPage2CombatStats:
    def test_initiative_sign(self):
        # DEX 12 → mod +1
        v = character_to_field_values(_make_fighter())
        assert v["page2"]["initiative"] == "+1"

    def test_armor_class_present(self):
        v = character_to_field_values(_make_fighter())
        assert int(v["page2"]["armor_class"]) >= 10

    def test_hit_points_positive(self):
        v = character_to_field_values(_make_fighter())
        assert int(v["page2"]["hit_points"]) > 0

    def test_movement_format(self):
        v = character_to_field_values(_make_fighter())
        assert v["page2"]["movement"].endswith("ft")

    def test_negative_initiative(self):
        char = Character(
            name="Test", char_class="wizard", level=1,
            ability_scores=AbilityScores(dexterity=8),
        )
        derive_stats(char)
        v = character_to_field_values(char)
        assert v["page2"]["initiative"] == "-1"


class TestPage2SavingThrows:
    def test_proficient_save_adds_prof(self):
        # Fighter is proficient in STR and CON saves
        char = _make_fighter()
        v = character_to_field_values(char)
        str_save = int(v["page2"]["save_str"])
        str_mod  = (16 - 10) // 2   # +3
        assert str_save == str_mod + char.proficiency_bonus

    def test_non_proficient_save_no_bonus(self):
        char = _make_fighter()
        v = character_to_field_values(char)
        # Fighter is NOT proficient in INT saves; INT 10 → mod 0
        assert v["page2"]["save_int"] == "+0"

    def test_save_sign_positive(self):
        char = _make_wizard()
        v = character_to_field_values(char)
        assert v["page2"]["save_int"].startswith("+")

    def test_save_sign_negative(self):
        char = Character(
            name="T", char_class="fighter", level=1,
            ability_scores=AbilityScores(charisma=7),
        )
        derive_stats(char)
        v = character_to_field_values(char)
        assert v["page2"]["save_cha"].startswith("-")

    def test_all_six_saves_present(self):
        v = character_to_field_values(_make_fighter())
        for key in ("save_str", "save_dex", "save_con", "save_int", "save_wis", "save_cha"):
            assert key in v["page2"]


class TestPage2Attacks:
    def test_attack_fields_populated(self):
        char = _make_fighter()
        char.attacks = [Attack(name="Longsword", hit_bonus=5, damage_dice="1d8", damage_type="slashing")]
        v = character_to_field_values(char)
        assert v["page2"]["atk1_weapon"] == "Longsword"
        assert v["page2"]["atk1_hit"]    == "+5"
        assert v["page2"]["atk1_dmg"]    == "1d8 +3"
        assert v["page2"]["atk1_desc"]   == "slashing"

    def test_multiple_attacks(self):
        char = _make_fighter()
        char.attacks = [
            Attack(name="Longsword", hit_bonus=5, damage_dice="1d8", damage_type="slashing"),
            Attack(name="Dagger",    hit_bonus=3, damage_dice="1d4", damage_type="piercing"),
        ]
        v = character_to_field_values(char)
        assert v["page2"]["atk2_weapon"] == "Dagger"

    def test_max_five_attacks(self):
        char = _make_fighter()
        char.attacks = [Attack(name=f"Sword{i}", hit_bonus=i, damage_dice="1d6", damage_type="slashing")
                        for i in range(7)]
        v = character_to_field_values(char)
        assert "atk6_weapon" not in v["page2"]
        assert "atk5_weapon" in v["page2"]

    def test_no_attacks_no_atk_fields(self):
        char = _make_fighter()
        char.attacks = []
        v = character_to_field_values(char)
        assert "atk1_weapon" not in v["page2"]

    def test_negative_hit_bonus_sign(self):
        char = _make_fighter()
        char.attacks = [Attack(name="Rusty Dagger", hit_bonus=-1, damage_dice="1d4", damage_type="piercing")]
        v = character_to_field_values(char)
        assert v["page2"]["atk1_hit"] == "-1"


class TestPage2FeaturesAndMagic:
    def test_features_text(self):
        char = _make_fighter()
        char.features = [FeatureEntry(name="Second Wind"), FeatureEntry(name="Action Surge")]
        v = character_to_field_values(char)
        assert "Second Wind" in v["page2"]["features_traits"]
        assert "Action Surge" in v["page2"]["features_traits"]

    def test_features_empty_when_none(self):
        char = _make_fighter()
        char.features = []
        v = character_to_field_values(char)
        assert v["page2"]["features_traits"] == ""

    def test_non_caster_magic_shows_no_spellcasting(self):
        char = _make_fighter()
        v = character_to_field_values(char)
        assert v["page2"]["magic_abilities"] == "No spellcasting"

    def test_caster_has_spell_stats(self):
        char = _make_wizard()
        v = character_to_field_values(char)
        # Wizard lv3, INT 16 → mod +3, prof +2 → atk +5, dc 13
        assert "spell_stats" in v["page2"]
        assert "+5" in v["page2"]["spell_stats"]
        assert "13" in v["page2"]["spell_stats"]

    def test_caster_has_cantrips_header(self):
        char = _make_wizard()
        v = character_to_field_values(char)
        assert v["page2"]["cantrips_header"] == "Cantrips (At Will)"

    def test_caster_cantrips_list(self):
        char = _make_wizard()
        char.always_available = [
            SpellEntry(level=0, name="Fire Bolt"),
            SpellEntry(level=0, name="Prestidigitation"),
        ]
        v = character_to_field_values(char)
        assert "Fire Bolt" in v["page2"]["cantrips_list"]
        assert "Prestidigitation" in v["page2"]["cantrips_list"]

    def test_caster_level1_header_has_slots(self):
        char = _make_wizard()  # level 3 → 4 level-1 slots
        v = character_to_field_values(char)
        hdr = v["page2"]["spells_level_1_header"]
        assert "1st" in hdr
        assert hdr.count("[ ]") == 4

    def test_caster_level1_spell_list(self):
        char = _make_wizard()
        char.spells = [SpellEntry(level=1, name="Magic Missile")]
        v = character_to_field_values(char)
        assert "Magic Missile" in v["page2"]["spells_level_1_list"]

    def test_caster_level2_header_has_slots(self):
        char = _make_wizard()  # level 3 → 2 level-2 slots
        v = character_to_field_values(char)
        hdr = v["page2"]["spells_level_2_header"]
        assert "2nd" in hdr
        assert hdr.count("[ ]") == 2

    def test_caster_no_magic_abilities_key(self):
        char = _make_wizard()
        v = character_to_field_values(char)
        # Casters do NOT produce the magic_abilities key
        assert "magic_abilities" not in v["page2"]


class TestPronouns:
    def test_pronouns_passthrough(self):
        char = _make_fighter()
        char.pronouns = "he/him"
        v = character_to_field_values(char)
        assert v["page1"]["pronouns"] == "he/him"

    def test_pronouns_they_them(self):
        char = _make_fighter()
        char.pronouns = "they/them"
        v = character_to_field_values(char)
        assert v["page1"]["pronouns"] == "they/them"

    def test_pronouns_xe_xem(self):
        char = _make_fighter()
        char.pronouns = "xe/xem"
        v = character_to_field_values(char)
        assert v["page1"]["pronouns"] == "xe/xem"

    def test_pronouns_empty_by_default(self):
        char = _make_fighter()
        v = character_to_field_values(char)
        assert v["page1"]["pronouns"] == ""

    def test_pronouns_whitespace_stripped(self):
        char = _make_fighter()
        char.pronouns = "  she/her  "
        v = character_to_field_values(char)
        assert v["page1"]["pronouns"] == "she/her"


class TestProficienciesFormatted:
    def test_armor_category_label(self):
        char = _make_fighter()
        char.armor_proficiencies = ["Light", "Medium"]
        v = character_to_field_values(char)
        assert "Armor: Light, Medium" in v["page1"]["proficiencies_text"]

    def test_weapons_category_label(self):
        char = _make_fighter()
        char.weapon_proficiencies = ["Simple", "Martial"]
        v = character_to_field_values(char)
        assert "Weapons: Simple, Martial" in v["page1"]["proficiencies_text"]

    def test_languages_category_label(self):
        char = _make_fighter()
        char.languages = ["Common", "Dwarvish"]
        v = character_to_field_values(char)
        assert "Languages: Common, Dwarvish" in v["page1"]["proficiencies_text"]

    def test_each_category_on_own_line(self):
        char = _make_fighter()
        char.armor_proficiencies = ["Light"]
        char.languages = ["Common"]
        # Clear weapon/tool to keep it simple
        char.weapon_proficiencies = []
        char.tool_proficiencies = []
        v = character_to_field_values(char)
        txt = v["page1"]["proficiencies_text"]
        assert "\n" in txt
        lines = txt.split("\n")
        assert any("Armor" in l for l in lines)
        assert any("Languages" in l for l in lines)

    def test_empty_categories_omitted(self):
        char = _make_fighter()
        char.armor_proficiencies = []
        char.weapon_proficiencies = []
        char.tool_proficiencies = ["Herbalism Kit"]
        char.languages = []
        v = character_to_field_values(char)
        txt = v["page1"]["proficiencies_text"]
        assert "Tools: Herbalism Kit" in txt
        assert "Armor:" not in txt
        assert "Languages:" not in txt


# ---------------------------------------------------------------------------
# fill_otg_sheet — integration (requires real PDF)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not SHEET_PDF.exists(), reason="Blank sheet PDF not present")
class TestFillOtgSheet:
    def test_produces_pdf_file(self, tmp_path):
        char = _make_fighter()
        out = fill_otg_sheet(char, tmp_path / "test_output.pdf")
        assert out.exists()
        assert out.stat().st_size > 1000

    def test_output_path_returned(self, tmp_path):
        char = _make_fighter()
        expected = tmp_path / "char.pdf"
        result = fill_otg_sheet(char, expected)
        assert result == expected

    def test_creates_parent_dirs(self, tmp_path):
        char = _make_fighter()
        deep = tmp_path / "a" / "b" / "out.pdf"
        fill_otg_sheet(char, deep)
        assert deep.exists()

    def test_caster_character(self, tmp_path):
        char = _make_wizard()
        char.always_available = [SpellEntry(level=0, name="Ray of Frost")]
        char.spells = [SpellEntry(level=1, name="Thunderwave")]
        out = fill_otg_sheet(char, tmp_path / "wizard.pdf")
        assert out.exists()

    def test_missing_sheet_raises(self, tmp_path):
        import pdf.filler as filler_mod
        original = filler_mod.SHEET_PDF
        filler_mod.SHEET_PDF = Path("/nonexistent/sheet.pdf")
        try:
            with pytest.raises(FileNotFoundError):
                fill_otg_sheet(_make_fighter(), tmp_path / "out.pdf")
        finally:
            filler_mod.SHEET_PDF = original
