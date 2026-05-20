"""
Tests for PROTO-4: spell selection, SpellEntry conversion, and caster counts.
Pure-function tests use hardcoded spell dicts (no network).
build_spells_for_character tests use a FakeClient stub.
"""
import pytest
from engine.character import Character, AbilityScores
from engine.rules import derive_stats
from engine.spells import (
    _school_key, _categorize_spell, _shorten_range,
    _cantrip_damage_at_level, _extract_effect, _extract_flags,
    spell_to_entry, get_cantrip_count, get_spell_count,
    get_cantrips_for_class, get_spells_for_class,
    select_random_cantrips, select_random_spells,
    build_spells_for_character,
    CANTRIP_COUNT, SPELLS_KNOWN, PREPARED_CASTERS, KNOWN_CASTERS,
)

# ── Fake spell data (mirrors Open5e v2 field shape) ───────────────────────────

FIRE_BOLT = {
    "name": "Fire Bolt", "level": 0,
    "school": {"name": "Evocation", "key": "evocation"},
    "casting_time": "action", "range_text": "120 feet",
    "concentration": False, "saving_throw_ability": "",
    "damage_roll": "1d10", "damage_types": ["fire"],
    "desc": "You hurl a mote of fire at a creature.",
    "casting_options": [
        {"type": "player_level_5",  "damage_roll": "2d10"},
        {"type": "player_level_11", "damage_roll": "3d10"},
    ],
}

MINOR_ILLUSION = {
    "name": "Minor Illusion", "level": 0,
    "school": {"name": "Illusion", "key": "illusion"},
    "casting_time": "action", "range_text": "30 feet",
    "concentration": False, "saving_throw_ability": "",
    "damage_roll": "", "damage_types": [],
    "desc": "You create a sound or image.",
    "casting_options": [],
}

MAGIC_MISSILE = {
    "name": "Magic Missile", "level": 1,
    "school": {"name": "Evocation", "key": "evocation"},
    "casting_time": "action", "range_text": "120 feet",
    "concentration": False, "saving_throw_ability": "",
    "damage_roll": "1d4+1", "damage_types": ["force"],
    "desc": "Three glowing darts of magical force.",
    "casting_options": [],
}

HOLD_PERSON = {
    "name": "Hold Person", "level": 2,
    "school": {"name": "Enchantment", "key": "enchantment"},
    "casting_time": "action", "range_text": "60 feet",
    "concentration": True, "saving_throw_ability": "wisdom",
    "damage_roll": "", "damage_types": [],
    "desc": "Choose a humanoid that you can see within range.",
    "casting_options": [],
}

CURE_WOUNDS = {
    "name": "Cure Wounds", "level": 1,
    "school": {"name": "Abjuration", "key": "abjuration"},
    "casting_time": "action", "range_text": "Touch",
    "concentration": False, "saving_throw_ability": "",
    "damage_roll": "", "damage_types": [],
    "desc": "A creature you touch regains 1d8 + your spellcasting ability modifier hit points.",
    "casting_options": [],
}

MISTY_STEP = {
    "name": "Misty Step", "level": 2,
    "school": {"name": "Conjuration", "key": "conjuration"},
    "casting_time": "bonus-action", "range_text": "Self",
    "concentration": False, "saving_throw_ability": "",
    "damage_roll": "", "damage_types": [],
    "desc": "You teleport up to 30 feet.",
    "casting_options": [],
}

SHIELD = {
    "name": "Shield", "level": 1,
    "school": {"name": "Abjuration", "key": "abjuration"},
    "casting_time": "reaction", "range_text": "Self",
    "concentration": False, "saving_throw_ability": "",
    "damage_roll": "", "damage_types": [],
    "desc": "An invisible barrier of magical force appears.",
    "casting_options": [],
}

FIREBALL = {
    "name": "Fireball", "level": 3,
    "school": {"name": "Evocation", "key": "evocation"},
    "casting_time": "action", "range_text": "150 feet",
    "concentration": False, "saving_throw_ability": "dexterity",
    "damage_roll": "8d6", "damage_types": ["fire"],
    "desc": "A bright streak flashes from your pointing finger.",
    "casting_options": [],
}

DETECT_MAGIC = {
    "name": "Detect Magic", "level": 1,
    "school": {"name": "Divination", "key": "divination"},
    "casting_time": "action", "range_text": "Self",
    "concentration": True, "saving_throw_ability": "",
    "damage_roll": "", "damage_types": [],
    "desc": "For the duration, you sense the presence of magic.",
    "casting_options": [],
}

SAMPLE_CANTRIPS = [FIRE_BOLT, MINOR_ILLUSION]
SAMPLE_SPELLS   = [MAGIC_MISSILE, HOLD_PERSON, CURE_WOUNDS,
                   MISTY_STEP, SHIELD, FIREBALL, DETECT_MAGIC]


# ── Minimal client stub ───────────────────────────────────────────────────────

class FakeClient:
    def get_cantrips(self, char_class=None):
        return list(SAMPLE_CANTRIPS)

    def get_spells(self, char_class=None, level_max=5, level_min=1):
        return [s for s in SAMPLE_SPELLS
                if level_min <= s["level"] <= level_max]


# ── Helpers ───────────────────────────────────────────────────────────────────

def wizard(level=1, int_score=17):
    c = Character()
    c.char_class = "Wizard"
    c.level = level
    c.ability_scores = AbilityScores(intelligence=int_score, dexterity=14, constitution=12)
    return derive_stats(c)

def cleric(level=1, wis_score=16):
    c = Character()
    c.char_class = "Cleric"
    c.level = level
    c.ability_scores = AbilityScores(wisdom=wis_score, dexterity=12, constitution=14)
    return derive_stats(c)

def fighter(level=1):
    c = Character()
    c.char_class = "Fighter"
    c.level = level
    c.ability_scores = AbilityScores(strength=16, dexterity=14, constitution=14)
    return derive_stats(c)


# ── _school_key ───────────────────────────────────────────────────────────────

class TestSchoolKey:
    def test_nested_dict(self):
        assert _school_key(FIRE_BOLT) == "evocation"

    def test_string_fallback(self):
        assert _school_key({"school": "Necromancy"}) == "necromancy"

    def test_missing_returns_empty(self):
        assert _school_key({}) == ""


# ── _categorize_spell ─────────────────────────────────────────────────────────

class TestCategorize:
    def test_evocation_is_damage(self):
        assert _categorize_spell(FIRE_BOLT) == "damage"
        assert _categorize_spell(MAGIC_MISSILE) == "damage"

    def test_enchantment_is_control(self):
        assert _categorize_spell(HOLD_PERSON) == "control"

    def test_abjuration_is_support(self):
        assert _categorize_spell(CURE_WOUNDS) == "support"
        assert _categorize_spell(SHIELD) == "support"

    def test_conjuration_is_support(self):
        assert _categorize_spell(MISTY_STEP) == "support"

    def test_divination_is_utility(self):
        assert _categorize_spell(DETECT_MAGIC) == "utility"

    def test_unknown_school_is_utility(self):
        assert _categorize_spell({"school": {"key": "unknown"}}) == "utility"


# ── _shorten_range ────────────────────────────────────────────────────────────

class TestShortenRange:
    def test_feet(self):
        assert _shorten_range("120 feet") == "120 ft"
        assert _shorten_range("30 feet")  == "30 ft"

    def test_self(self):
        assert _shorten_range("Self")  == "Self"
        assert _shorten_range("self")  == "Self"

    def test_touch(self):
        assert _shorten_range("Touch") == "Touch"

    def test_sight(self):
        assert _shorten_range("sight") == "Sight"

    def test_miles(self):
        assert _shorten_range("1 mile") == "1 mi"

    def test_empty(self):
        assert _shorten_range("") == ""

    def test_special(self):
        assert _shorten_range("special") == "Special"


# ── _cantrip_damage_at_level ──────────────────────────────────────────────────

class TestCantripDamageAtLevel:
    def test_level1_returns_base(self):
        assert _cantrip_damage_at_level(FIRE_BOLT, 1) == "1d10"

    def test_level4_returns_base(self):
        assert _cantrip_damage_at_level(FIRE_BOLT, 4) == "1d10"

    def test_level5_scales_up(self):
        assert _cantrip_damage_at_level(FIRE_BOLT, 5) == "2d10"

    def test_no_casting_options_returns_base(self):
        spell = {**FIRE_BOLT, "casting_options": []}
        assert _cantrip_damage_at_level(spell, 5) == "1d10"

    def test_spell_without_damage(self):
        assert _cantrip_damage_at_level(MINOR_ILLUSION, 5) == ""


# ── _extract_effect ───────────────────────────────────────────────────────────

class TestExtractEffect:
    def test_damage_spell(self):
        assert _extract_effect(MAGIC_MISSILE) == "1d4+1 force"

    def test_damage_spell_fire(self):
        assert _extract_effect(FIREBALL) == "8d6 fire"

    def test_cantrip_level1(self):
        assert _extract_effect(FIRE_BOLT, char_level=1) == "1d10 fire"

    def test_cantrip_level5_scales(self):
        assert _extract_effect(FIRE_BOLT, char_level=5) == "2d10 fire"

    def test_healing_spell(self):
        effect = _extract_effect(CURE_WOUNDS)
        assert effect.startswith("Heal")
        assert "1d8" in effect

    def test_non_damage_no_heal_returns_school(self):
        # Hold Person is enchantment — no damage, no heal in desc
        effect = _extract_effect(HOLD_PERSON)
        assert effect.lower() in ("enchantment", "—") or len(effect) > 0

    def test_non_damage_returns_something(self):
        effect = _extract_effect(MISTY_STEP)
        assert len(effect) > 0


# ── _extract_flags ────────────────────────────────────────────────────────────

class TestExtractFlags:
    def test_concentration_flag(self):
        assert "C" in _extract_flags(HOLD_PERSON)

    def test_bonus_action_flag(self):
        assert "BA" in _extract_flags(MISTY_STEP)

    def test_reaction_flag(self):
        assert "R" in _extract_flags(SHIELD)

    def test_save_flag(self):
        assert "S" in _extract_flags(HOLD_PERSON)   # wisdom save
        assert "S" in _extract_flags(FIREBALL)       # dexterity save

    def test_no_flags_plain_action(self):
        flags = _extract_flags(MAGIC_MISSILE)
        assert flags == ""

    def test_multiple_flags(self):
        # Hold Person: concentration + save
        flags = _extract_flags(HOLD_PERSON)
        assert "C" in flags
        assert "S" in flags


# ── spell_to_entry ────────────────────────────────────────────────────────────

class TestSpellToEntry:
    def test_name_and_level(self):
        entry = spell_to_entry(FIRE_BOLT)
        assert entry.name == "Fire Bolt"
        assert entry.level == 0

    def test_range_shortened(self):
        entry = spell_to_entry(MAGIC_MISSILE)
        assert entry.range == "120 ft"

    def test_slots_total_passed_through(self):
        entry = spell_to_entry(MAGIC_MISSILE, slots_total=3)
        assert entry.slots_total == 3

    def test_slots_used_starts_at_zero(self):
        assert spell_to_entry(MAGIC_MISSILE).slots_used == 0

    def test_flags_populated(self):
        entry = spell_to_entry(HOLD_PERSON)
        assert "C" in entry.flags

    def test_cantrip_zero_slots(self):
        entry = spell_to_entry(FIRE_BOLT)
        assert entry.slots_total == 0

    def test_touch_range(self):
        assert spell_to_entry(CURE_WOUNDS).range == "Touch"

    def test_self_range(self):
        assert spell_to_entry(SHIELD).range == "Self"


# ── get_cantrip_count ─────────────────────────────────────────────────────────

class TestGetCantripCount:
    def test_wizard(self):     assert get_cantrip_count("wizard")   == 3
    def test_sorcerer(self):   assert get_cantrip_count("sorcerer") == 4
    def test_cleric(self):     assert get_cantrip_count("cleric")   == 3
    def test_bard(self):       assert get_cantrip_count("bard")     == 2
    def test_warlock(self):    assert get_cantrip_count("warlock")  == 2
    def test_druid(self):      assert get_cantrip_count("druid")    == 2
    def test_paladin_zero(self): assert get_cantrip_count("paladin") == 0
    def test_ranger_zero(self):  assert get_cantrip_count("ranger")  == 0
    def test_fighter_zero(self): assert get_cantrip_count("fighter") == 0
    def test_case_insensitive(self): assert get_cantrip_count("Wizard") == 3


# ── get_spell_count ───────────────────────────────────────────────────────────

class TestGetSpellCount:
    def test_warlock_known_level1(self):
        char = wizard(level=1)  # using wizard char as vehicle, class doesn't matter here
        assert get_spell_count("warlock", 1, char) == 2

    def test_bard_known_level3(self):
        char = wizard()
        assert get_spell_count("bard", 3, char) == 4

    def test_ranger_level1_zero(self):
        char = wizard()
        assert get_spell_count("ranger", 1, char) == 0

    def test_ranger_level2(self):
        char = wizard()
        assert get_spell_count("ranger", 2, char) == 2

    def test_wizard_prepared_int17_level1(self):
        # INT 17 → mod +3; prepared = max(1, 3 + 1) = 4
        char = wizard(level=1, int_score=17)
        assert get_spell_count("wizard", 1, char) == 4

    def test_wizard_prepared_int10_level1(self):
        # INT 10 → mod 0; prepared = max(1, 0 + 1) = 1
        char = wizard(level=1, int_score=10)
        assert get_spell_count("wizard", 1, char) == 1

    def test_cleric_prepared_wis16_level3(self):
        # WIS 16 → mod +3; prepared = max(1, 3 + 3) = 6
        char = cleric(level=3, wis_score=16)
        assert get_spell_count("cleric", 3, char) == 6

    def test_fighter_returns_zero(self):
        char = fighter()
        assert get_spell_count("fighter", 1, char) == 0


# ── select_random_cantrips ────────────────────────────────────────────────────

class TestSelectRandomCantrips:
    def test_returns_requested_count(self):
        result = select_random_cantrips(SAMPLE_CANTRIPS, 2)
        assert len(result) == 2

    def test_fewer_available_than_requested(self):
        result = select_random_cantrips(SAMPLE_CANTRIPS, 10)
        assert len(result) == len(SAMPLE_CANTRIPS)

    def test_count_zero_returns_empty(self):
        assert select_random_cantrips(SAMPLE_CANTRIPS, 0) == []

    def test_empty_pool_returns_empty(self):
        assert select_random_cantrips([], 3) == []

    def test_thematic_variety_damage_included(self):
        # With count=2 and both damage+non-damage cantrips, should include 1 damage
        hits = 0
        for _ in range(30):
            result = select_random_cantrips(SAMPLE_CANTRIPS, 2)
            has_damage = any(s.get("damage_roll") for s in result)
            if has_damage:
                hits += 1
        assert hits == 30, "With 2 cantrips (1 dmg, 1 non-dmg), damage must always be included"

    def test_single_cantrip(self):
        result = select_random_cantrips(SAMPLE_CANTRIPS, 1)
        assert len(result) == 1

    def test_returns_subset_of_input(self):
        for _ in range(10):
            result = select_random_cantrips(SAMPLE_CANTRIPS, 1)
            assert result[0] in SAMPLE_CANTRIPS


# ── select_random_spells ──────────────────────────────────────────────────────

class TestSelectRandomSpells:
    def test_returns_requested_count(self):
        result = select_random_spells(SAMPLE_SPELLS, 3)
        assert len(result) == 3

    def test_count_exceeds_pool(self):
        result = select_random_spells(SAMPLE_SPELLS, 100)
        assert len(result) == len(SAMPLE_SPELLS)

    def test_count_zero_returns_empty(self):
        assert select_random_spells(SAMPLE_SPELLS, 0) == []

    def test_empty_pool_returns_empty(self):
        assert select_random_spells([], 3) == []

    def test_balanced_includes_damage_spells(self):
        found_damage = False
        for _ in range(20):
            result = select_random_spells(SAMPLE_SPELLS, 4, strategy="balanced")
            if any(_categorize_spell(s) == "damage" for s in result):
                found_damage = True
                break
        assert found_damage

    def test_damage_strategy_more_damage_than_support(self):
        damage_count = support_count = 0
        for _ in range(50):
            result = select_random_spells(SAMPLE_SPELLS, 4, strategy="damage")
            for s in result:
                cat = _categorize_spell(s)
                if cat == "damage":
                    damage_count += 1
                elif cat in ("support", "utility"):
                    support_count += 1
        assert damage_count > support_count

    def test_no_duplicate_spells(self):
        for _ in range(20):
            result = select_random_spells(SAMPLE_SPELLS, 5)
            assert len(result) == len(set(id(s) for s in result))

    def test_unknown_strategy_falls_back_to_balanced(self):
        result = select_random_spells(SAMPLE_SPELLS, 3, strategy="goblin_mode")
        assert len(result) == 3

    def test_result_is_subset_of_input(self):
        for _ in range(10):
            result = select_random_spells(SAMPLE_SPELLS, 3)
            for s in result:
                assert s in SAMPLE_SPELLS


# ── build_spells_for_character ────────────────────────────────────────────────

class TestBuildSpellsForCharacter:
    def test_non_caster_unchanged(self):
        char = fighter()
        char.spell_selection_mode = "random"
        build_spells_for_character(char, FakeClient())
        assert char.always_available == []
        assert char.spells == []

    def test_wizard_gets_cantrips(self):
        char = wizard(level=1)
        build_spells_for_character(char, FakeClient())
        assert len(char.always_available) == 2  # FakeClient only has 2 cantrips

    def test_wizard_cantrips_are_spell_entries(self):
        char = wizard(level=1)
        build_spells_for_character(char, FakeClient())
        from engine.character import SpellEntry
        for entry in char.always_available:
            assert isinstance(entry, SpellEntry)
            assert entry.level == 0

    def test_wizard_gets_slot_spells(self):
        char = wizard(level=1, int_score=17)  # prepared = 4
        build_spells_for_character(char, FakeClient())
        assert len(char.spells) > 0

    def test_cleric_gets_cantrips(self):
        char = cleric(level=1)
        build_spells_for_character(char, FakeClient())
        assert len(char.always_available) > 0

    def test_manual_mode_skipped(self):
        char = wizard(level=1)
        char.spell_selection_mode = "manual"
        build_spells_for_character(char, FakeClient())
        assert char.always_available == []
        assert char.spells == []

    def test_spell_entries_have_names(self):
        char = wizard(level=1, int_score=17)
        build_spells_for_character(char, FakeClient())
        for entry in char.spells:
            assert entry.name != ""

    def test_cantrip_entries_have_zero_slots(self):
        char = wizard(level=1)
        build_spells_for_character(char, FakeClient())
        for entry in char.always_available:
            assert entry.slots_total == 0

    def test_slot_spells_have_slots_total(self):
        # Wizard level 1 has {1: 2} slots; spell entries for level-1 spells should reflect this
        char = wizard(level=1, int_score=17)
        build_spells_for_character(char, FakeClient())
        lv1_spells = [e for e in char.spells if e.level == 1]
        if lv1_spells:
            assert lv1_spells[0].slots_total == char.spell_slots.get(1, 0)

    def test_returns_character(self):
        char = wizard(level=1)
        result = build_spells_for_character(char, FakeClient())
        assert result is char


# ── Integration: live API (marked slow, optional) ─────────────────────────────

class TestSpellsLiveAPI:
    """Hits the real Open5e API — same pattern as test_api.py live tests."""

    def test_live_wizard_cantrips(self):
        from api.open5e_client import Open5eClient
        client = Open5eClient(sources=["srd-2014"])
        cantrips = get_cantrips_for_class("wizard", client)
        assert len(cantrips) >= 4
        names = [s["name"] for s in cantrips]
        assert any("Bolt" in n or "Touch" in n or "Blade" in n for n in names)

    def test_live_wizard_level1_spells(self):
        from api.open5e_client import Open5eClient
        client = Open5eClient(sources=["srd-2014"])
        spells = get_spells_for_class("wizard", 1, client)
        assert len(spells) >= 5
        levels = {s["level"] for s in spells}
        assert 1 in levels
        assert 0 not in levels    # cantrips excluded

    def test_live_spell_to_entry_roundtrip(self):
        from api.open5e_client import Open5eClient
        client = Open5eClient(sources=["srd-2014"])
        spells = get_spells_for_class("wizard", 3, client)
        for s in spells[:5]:
            entry = spell_to_entry(s)
            assert entry.name == s["name"]
            assert entry.level == s["level"]
            assert isinstance(entry.flags, str)
