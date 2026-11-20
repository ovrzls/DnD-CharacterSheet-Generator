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
from pdf.filler import (
    character_to_field_values, fill_otg_sheet, SHEET_PDF,
    _spell_effect_summary, _build_spell_columns, _spell_entry_label,
    _fit_spell_entry, _load_field_map, FONT_REGULAR,
    _name_with_pronouns, _fit_single_line, _identify_sheet_pages, _draw_wrapped,
)


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
    def test_features_in_magic_abilities(self):
        # Features rendered on canvas via _draw_spell_section; verify source data is correct
        from engine.rules import get_character_features
        char = _make_fighter()
        feats = get_character_features(char)
        feat_names = [n for n, _ in feats]
        assert any("Fighting Style" in n for n in feat_names)
        assert any("Second Wind" in n for n in feat_names)

    def test_non_caster_magic_starts_with_no_spellcasting(self):
        # Canvas renderer draws "No spellcasting."; magic_abilities absent from field values
        char = _make_fighter()
        v = character_to_field_values(char)
        assert "magic_abilities" not in v["page2"]

    def test_non_caster_magic_has_features_after_divider(self):
        # Features list is non-empty; canvas renderer draws them below divider
        from engine.rules import get_character_features
        char = _make_fighter()
        feats = get_character_features(char)
        assert len(feats) > 0

    def test_caster_has_no_spell_fields_in_page2(self):
        # Caster spell content is drawn directly via _draw_spell_section(); not in the dict
        char = _make_wizard()
        v = character_to_field_values(char)
        for key in ("spell_stats", "cantrips_header", "cantrips_list",
                    "spells_level_1_header", "spells_level_1_list",
                    "spells_level_2_header", "spells_level_2_list",
                    "magic_abilities"):
            assert key not in v["page2"], f"Unexpected key in caster page2: {key}"


class TestSpellEffectSummary:
    def test_damage_effect(self):
        sp = SpellEntry(level=1, name="Scorching Ray", effect_dmg="2d6 fire")
        assert _spell_effect_summary(sp) == "2d6 fire"

    def test_concentration_flag(self):
        sp = SpellEntry(level=1, name="Hold Person", effect_dmg="Restrained", flags="C S")
        summary = _spell_effect_summary(sp)
        assert "Restrained" in summary
        assert "(C)" in summary

    def test_no_effect(self):
        sp = SpellEntry(level=0, name="Prestidigitation")
        assert _spell_effect_summary(sp) == ""

    def test_concentration_only(self):
        sp = SpellEntry(level=1, name="Bless", flags="C")
        assert _spell_effect_summary(sp) == "(C)"

    def test_truncation(self):
        sp = SpellEntry(level=1, name="X", effect_dmg="a" * 25)
        assert len(_spell_effect_summary(sp)) <= 20


class TestBuildSpellColumns:
    def test_cantrips_column_header(self):
        char = _make_wizard()
        char.always_available = [SpellEntry(level=0, name="Fire Bolt", effect_dmg="1d10 fire")]
        cols = _build_spell_columns(char)
        assert cols[0]["header"] == "CANTRIPS (AT WILL)"
        assert cols[0]["slots"] == 0
        assert any("Fire Bolt" in e for e in cols[0]["entries"])

    def test_cantrip_entry_includes_effect(self):
        char = _make_wizard()
        char.always_available = [SpellEntry(level=0, name="Fire Bolt", effect_dmg="1d10 fire")]
        cols = _build_spell_columns(char)
        assert "Fire Bolt — 1d10 fire" in cols[0]["entries"]

    def test_level1_header_has_slot_boxes(self):
        char = _make_wizard()  # level 3 → 4 level-1 slots
        cols = _build_spell_columns(char)
        lvl1 = next(c for c in cols if "1ST" in c["header"])
        assert lvl1["header"] == "1ST LEVEL"
        assert lvl1["slots"] == 4

    def test_level2_header_has_slot_boxes(self):
        char = _make_wizard()  # level 3 → 2 level-2 slots
        cols = _build_spell_columns(char)
        lvl2 = next(c for c in cols if "2ND" in c["header"])
        assert lvl2["header"] == "2ND LEVEL"
        assert lvl2["slots"] == 2

    def test_spell_entry_with_effect(self):
        char = _make_wizard()
        char.spells = [SpellEntry(level=1, name="Magic Missile", effect_dmg="3d4+3 force")]
        cols = _build_spell_columns(char)
        lvl1 = next(c for c in cols if "1ST" in c["header"])
        assert "Magic Missile — 3d4+3 force" in lvl1["entries"]

    def test_no_cantrips_column_when_empty(self):
        char = _make_wizard()
        char.always_available = []
        cols = _build_spell_columns(char)
        assert all("CANTRIPS" not in c["header"] for c in cols)


class TestPronouns:
    def test_species_shown_on_page1(self):
        char = _make_fighter()
        char.race = "half-elf"
        v = character_to_field_values(char)
        assert v["page1"]["species"] == "Half-Elf"

    def test_species_empty_by_default(self):
        v = character_to_field_values(_make_fighter())
        assert v["page1"]["species"] == ""

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


class TestSpellEntryFitting:
    def _canvas(self):
        import io
        from reportlab.pdfgen import canvas
        return canvas.Canvas(io.BytesIO())

    def test_label_joins_name_and_effect(self):
        assert _spell_entry_label("Fire Bolt", "2d10 fire") == "Fire Bolt — 2d10 fire"

    def test_label_concentration_only_has_no_dash(self):
        assert _spell_entry_label("Detect Magic", "(C)") == "Detect Magic (C)"

    def test_label_without_effect_is_just_the_name(self):
        assert _spell_entry_label("Mage Hand", "") == "Mage Hand"

    def test_entry_that_fits_is_unchanged(self):
        c = self._canvas()
        assert _fit_spell_entry(c, "Shield — +5 AC", FONT_REGULAR, 9.5, 122) == "Shield — +5 AC"

    def test_wide_entry_drops_effect_but_keeps_name_and_concentration(self):
        c = self._canvas()
        entry = "Protection from Evil and Good — Abjuration (C)"
        assert _fit_spell_entry(c, entry, FONT_REGULAR, 9.5, 122) == "Protection from Evil and Good (C)"

    def test_name_is_only_cut_as_a_last_resort(self):
        c = self._canvas()
        out = _fit_spell_entry(c, "An Extremely Long Spell Name That Cannot Fit — x", FONT_REGULAR, 9.5, 60)
        assert out.endswith("…")
        assert c.stringWidth(out, FONT_REGULAR, 9.5) <= 60


class TestFieldMapSpecies:
    def test_species_replaces_pronouns_slot(self):
        page1 = _load_field_map()["page1"]
        assert "species" in page1
        assert "pronouns" not in page1


class TestNameWithPronouns:
    def test_name_alone_when_no_pronouns(self):
        assert _name_with_pronouns("Mira", "") == "Mira"

    def test_pronouns_follow_name_in_brackets(self):
        assert _name_with_pronouns("Mira", " she/her ") == "Mira (she/her)"

    def test_name_field_carries_pronouns(self):
        char = _make_fighter()
        char.pronouns = "they/them"
        v = character_to_field_values(char)
        assert v["page1"]["name"] == "Aldric (they/them)"

    def test_long_name_shrinks_before_it_is_cut(self):
        import io
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(io.BytesIO())
        text, size = _fit_single_line(c, "Bartholomew Quill (they/them)", FONT_REGULAR, 11, 118)
        assert text == "Bartholomew Quill (they/them)"
        assert 8 <= size <= 11

    def test_very_long_name_is_cut_to_fit(self):
        import io
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(io.BytesIO())
        text, size = _fit_single_line(c, "Maximilian Thunderbrook-Ashenvale the Third (xe/xem)", FONT_REGULAR, 11, 118)
        assert size == 8
        assert text.endswith("…")
        assert c.stringWidth(text, FONT_REGULAR, size) <= 118


class TestIdentifySheetPages:
    IDENTITY = "NAME SPECIES CLASS ABILITIES SKILLS PROFICIENCIES INVENTORY"
    COMBAT = "INITIATIVE SAVING THROW BONUS ATTACKS MAGIC & SPECIAL ABILITIES"

    def test_identity_page_first(self):
        assert _identify_sheet_pages([self.IDENTITY, self.COMBAT]) == ["page1", "page2"]

    def test_combat_page_first(self):
        assert _identify_sheet_pages([self.COMBAT, self.IDENTITY]) == ["page2", "page1"]

    def test_unreadable_text_keeps_file_order(self):
        assert _identify_sheet_pages(["", ""]) == ["page1", "page2"]


class TestParagraphSpacing:
    def _end_y(self, text, spacing):
        import io
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(io.BytesIO())
        return _draw_wrapped(c, text, 0, 100, 10, FONT_REGULAR, 500, 12, spacing)

    def test_no_spacing_by_default(self):
        assert self._end_y("one\ntwo\nthree", 0) == 100 - 3 * 12

    def test_gap_added_between_paragraphs_only(self):
        # three paragraphs -> two gaps, none before the first or after the last
        assert self._end_y("one\ntwo\nthree", 10) == 100 - 3 * 12 - 2 * 10

    def test_single_paragraph_has_no_gap(self):
        assert self._end_y("one", 10) == 100 - 12

    def test_proficiencies_block_has_paragraph_spacing(self):
        spec = _load_field_map()["page1"]["proficiencies_text"]
        assert spec["paragraph_spacing_em"] > 0


class TestCalibrationProof:
    def test_page_overlay_renders_for_every_field(self):
        from pdf.calibrate_overlay import render_calibration_page
        fields = _load_field_map()["page1"]
        data = render_calibration_page(fields, "page1")
        assert data.startswith(b"%PDF")

    @pytest.mark.skipif(not SHEET_PDF.exists(), reason="blank sheet not present")
    def test_proof_has_both_pages(self, tmp_path):
        from pypdf import PdfReader
        from pdf.calibrate_overlay import build_proof
        out = build_proof(tmp_path / "proof.pdf")
        # two sheet pages, then at least one key page per sheet page
        assert len(PdfReader(str(out)).pages) >= 4


class TestFeaturesTraitsBox:
    def _canvas(self):
        import io
        from reportlab.pdfgen import canvas
        return canvas.Canvas(io.BytesIO())

    def _spec(self, **kw):
        spec = dict(_load_field_map()["page2"]["features_traits"])
        spec.update(kw)
        return spec

    def test_field_map_entry(self):
        spec = _load_field_map()["page2"]["features_traits"]
        assert (spec["x"], spec["y"], spec["max_width"]) == (432, 516, 136)
        assert spec["type"] == "titled_text"

    def test_value_leads_with_background_name(self):
        char = _make_fighter()
        char.background = "artisan"
        char.background_feature = "Trade Mark"
        char.background_feature_desc = "You have access to a workshop."
        v = character_to_field_values(char)["page2"]["features_traits"]
        assert v == {"title": "Artisan", "body": "You have access to a workshop."}

    def test_falls_back_to_built_in_table(self):
        from engine.rules import BACKGROUND_FEATURES
        char = _make_fighter()
        char.background = "Soldier"
        v = character_to_field_values(char)["page2"]["features_traits"]
        assert v["title"] == "Soldier"
        assert v["body"] == BACKGROUND_FEATURES["soldier"][1]

    def test_no_background_no_box(self):
        char = _make_fighter()
        char.background = ""
        assert character_to_field_values(char)["page2"]["features_traits"] is None

    def test_background_feature_left_out_of_magic_box(self):
        from engine.rules import get_character_features, BACKGROUND_FEATURES
        char = _make_fighter()
        char.background = "Soldier"
        assert BACKGROUND_FEATURES["soldier"] in get_character_features(char)
        assert BACKGROUND_FEATURES["soldier"] not in get_character_features(char, include_background=False)

    def test_short_text_keeps_full_size(self):
        from pdf.filler import _layout_titled_text
        size, title, body = _layout_titled_text(self._canvas(), "Artisan", "A short line.", self._spec())
        assert size == self._spec()["font_size"]
        assert title == ["Artisan"] and body == ["A short line."]

    def test_long_text_shrinks_then_is_cut_to_fit(self):
        from pdf.filler import _layout_titled_text
        spec = self._spec()
        size, title, body = _layout_titled_text(self._canvas(), "Innkeeper", "word " * 400, spec)
        assert size == spec["min_font_size"]
        assert body[-1].endswith("…")
        max_lines = int(spec["max_height"] // (size * spec["line_ratio"])) + 1
        assert len(title) + len(body) <= max_lines
        c = self._canvas()
        assert all(c.stringWidth(line, FONT_REGULAR, size) <= spec["max_width"] for line in body)


class TestMarkers:
    """Proficiency dots, expertise diamonds and the inspiration check are drawn as
    shapes because the sheet font has no glyphs for them."""

    def _overlay_ops(self, field, value, spec):
        import io
        from pypdf import PdfReader
        from pdf.filler import _render_page
        data = _render_page({field: spec}, {field: value})
        return PdfReader(io.BytesIO(data)).pages[0].get_contents().get_data()

    @pytest.mark.parametrize("value", ["●", "◆", "✓"])
    def test_marker_drawn_as_shape_not_text(self, value):
        ops = self._overlay_ops("skill_prof_x", value, {"x": 100, "y": 100, "font_size": 9, "align": "center"})
        assert b"Tj" not in ops          # no text drawn
        assert ops.strip()                # but something is

    def test_font_has_no_marker_glyphs(self):
        # If this ever fails, the font gained the glyphs and the shapes could go.
        from fontTools.ttLib import TTFont
        from pdf.filler import FONT_DIR
        cmap = TTFont(str(FONT_DIR / "BarlowCondensed-Medium.ttf")).getBestCmap()
        assert ord("●") not in cmap
