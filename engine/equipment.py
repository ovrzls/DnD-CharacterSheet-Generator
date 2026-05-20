"""
Equipment selection logic — PROTO-3 implementation.
Provides standard best-fit and randomized starting packages per class.
All data hardcoded from SRD (prototype scope, levels 1-5).
"""
from __future__ import annotations
import random
from engine.character import AbilityScores, Attack, EquipmentItem

# ── Weapon stats ───────────────────────────────────────────────────────────────

WEAPONS: dict[str, dict] = {
    "greataxe":        {"damage": "1d12", "type": "slashing",    "notes": "heavy, two-handed", "finesse": False, "ranged": False},
    "handaxe":         {"damage": "1d6",  "type": "slashing",    "notes": "light, thrown 20/60", "finesse": False, "ranged": False},
    "javelin":         {"damage": "1d6",  "type": "piercing",    "notes": "thrown 30/120",    "finesse": False, "ranged": False},
    "rapier":          {"damage": "1d8",  "type": "piercing",    "notes": "finesse",          "finesse": True,  "ranged": False},
    "longsword":       {"damage": "1d8",  "type": "slashing",    "notes": "versatile (1d10)", "finesse": False, "ranged": False},
    "dagger":          {"damage": "1d4",  "type": "piercing",    "notes": "finesse, light, thrown 20/60", "finesse": True, "ranged": False},
    "mace":            {"damage": "1d6",  "type": "bludgeoning", "notes": "",                 "finesse": False, "ranged": False},
    "warhammer":       {"damage": "1d8",  "type": "bludgeoning", "notes": "versatile (1d10)", "finesse": False, "ranged": False},
    "scimitar":        {"damage": "1d6",  "type": "slashing",    "notes": "finesse, light",   "finesse": True,  "ranged": False},
    "shortsword":      {"damage": "1d6",  "type": "piercing",    "notes": "finesse, light",   "finesse": True,  "ranged": False},
    "quarterstaff":    {"damage": "1d6",  "type": "bludgeoning", "notes": "versatile (1d8)",  "finesse": False, "ranged": False},
    "shortbow":        {"damage": "1d6",  "type": "piercing",    "notes": "80/320",           "finesse": False, "ranged": True},
    "longbow":         {"damage": "1d8",  "type": "piercing",    "notes": "150/600, heavy",   "finesse": False, "ranged": True},
    "light_crossbow":  {"damage": "1d8",  "type": "piercing",    "notes": "80/320, loading",  "finesse": False, "ranged": True},
    "spear":           {"damage": "1d6",  "type": "piercing",    "notes": "thrown 20/60, versatile (1d8)", "finesse": False, "ranged": False},
}

# ── Armor stats ────────────────────────────────────────────────────────────────
# dex_cap: max DEX mod added (None = unlimited, 0 = none added)

ARMOR: dict[str, dict] = {
    "none":            {"base_ac": 10, "dex_cap": None},
    "leather":         {"base_ac": 11, "dex_cap": None},
    "studded_leather": {"base_ac": 12, "dex_cap": None},
    "scale_mail":      {"base_ac": 14, "dex_cap": 2},
    "chain_mail":      {"base_ac": 16, "dex_cap": 0},
}

# ── Adventuring packs ──────────────────────────────────────────────────────────

PACKS: dict[str, str] = {
    "burglar":     "Burglar's Pack",
    "diplomat":    "Diplomat's Pack",
    "dungeoneer":  "Dungeoneer's Pack",
    "entertainer": "Entertainer's Pack",
    "explorer":    "Explorer's Pack",
    "priest":      "Priest's Pack",
    "scholar":     "Scholar's Pack",
}

# ── Per-class equipment option tables ─────────────────────────────────────────
# armor_options:   list of armor keys; best-fit picks highest AC, random picks one
# armor_extras:    {armor_key: [weapon_keys]} — bonus weapons when that armor is chosen
# shield:          whether the class always gets a shield
# weapon_options:  list of weapon-key lists; best-fit picks first, random picks one
# extra_weapons:   weapons always included (javelins, secondary ranged, etc.)
# pack_options:    list of pack keys; best-fit picks first, random picks one
# extras:          fixed EquipmentItem dicts always included

CLASS_OPTIONS: dict[str, dict] = {
    "barbarian": {
        "armor_options":  ["none"],
        "armor_extras":   {},
        "shield":         False,
        "weapon_options": [["greataxe"], ["handaxe", "handaxe"]],
        "extra_weapons":  ["javelin"] * 4,
        "pack_options":   ["explorer"],
        "extras":         [],
    },
    "bard": {
        "armor_options":  ["leather"],
        "armor_extras":   {},
        "shield":         False,
        "weapon_options": [["rapier"], ["longsword"], ["dagger"]],
        "extra_weapons":  ["dagger"],
        "pack_options":   ["diplomat", "entertainer"],
        "extras":         [{"name": "Lute", "quantity": 1}],
    },
    "cleric": {
        "armor_options":  ["chain_mail", "scale_mail", "leather"],
        "armor_extras":   {},
        "shield":         True,
        "weapon_options": [["mace"], ["warhammer"]],
        "extra_weapons":  [],
        "pack_options":   ["priest", "explorer"],
        "extras":         [],
    },
    "druid": {
        "armor_options":  ["leather"],
        "armor_extras":   {},
        "shield":         True,
        "weapon_options": [["scimitar"], ["dagger"]],
        "extra_weapons":  [],
        "pack_options":   ["explorer"],
        "extras":         [{"name": "Druidic Focus", "quantity": 1}],
    },
    "fighter": {
        "armor_options":  ["chain_mail", "leather"],
        # leather build gets a longbow instead of heavy armor
        "armor_extras":   {"leather": ["longbow"]},
        "shield":         True,
        "weapon_options": [["longsword"], ["shortsword", "shortsword"]],
        "extra_weapons":  [],
        "pack_options":   ["dungeoneer", "explorer"],
        "extras":         [],
    },
    "monk": {
        "armor_options":  ["none"],
        "armor_extras":   {},
        "shield":         False,
        "weapon_options": [["shortsword"], ["dagger"]],
        "extra_weapons":  [],
        "pack_options":   ["dungeoneer", "explorer"],
        "extras":         [{"name": "10 gp", "quantity": 1}],
    },
    "paladin": {
        "armor_options":  ["chain_mail"],
        "armor_extras":   {},
        "shield":         True,
        "weapon_options": [["longsword"], ["shortsword", "shortsword"]],
        "extra_weapons":  ["javelin"] * 5,
        "pack_options":   ["priest", "explorer"],
        "extras":         [],
    },
    "ranger": {
        "armor_options":  ["scale_mail", "leather"],
        "armor_extras":   {},
        "shield":         False,
        "weapon_options": [["shortsword", "shortsword"], ["dagger", "dagger"]],
        "extra_weapons":  ["longbow"],
        "pack_options":   ["dungeoneer", "explorer"],
        "extras":         [{"name": "20 Arrows", "quantity": 1}],
    },
    "rogue": {
        "armor_options":  ["leather"],
        "armor_extras":   {},
        "shield":         False,
        "weapon_options": [["rapier"], ["shortsword"]],
        "extra_weapons":  ["dagger", "dagger", "shortbow"],
        "pack_options":   ["burglar", "dungeoneer", "explorer"],
        "extras":         [
            {"name": "Thieves' Tools", "quantity": 1},
            {"name": "20 Arrows",      "quantity": 1},
        ],
    },
    "sorcerer": {
        "armor_options":  ["none"],
        "armor_extras":   {},
        "shield":         False,
        "weapon_options": [["light_crossbow"], ["dagger"]],
        "extra_weapons":  ["dagger"],
        "pack_options":   ["dungeoneer", "explorer"],
        "extras":         [{"name": "Arcane Focus", "quantity": 1}],
    },
    "warlock": {
        "armor_options":  ["leather"],
        "armor_extras":   {},
        "shield":         False,
        "weapon_options": [["light_crossbow"], ["dagger"]],
        "extra_weapons":  ["dagger", "dagger"],
        "pack_options":   ["scholar", "dungeoneer"],
        "extras":         [{"name": "Arcane Focus", "quantity": 1}],
    },
    "wizard": {
        "armor_options":  ["none"],
        "armor_extras":   {},
        "shield":         False,
        "weapon_options": [["quarterstaff"], ["dagger"]],
        "extra_weapons":  [],
        "pack_options":   ["scholar", "explorer"],
        "extras":         [
            {"name": "Arcane Focus", "quantity": 1},
            {"name": "Spellbook",    "quantity": 1},
        ],
    },
}

# ── AC calculation ─────────────────────────────────────────────────────────────

def calc_ac(armor_key: str, dex_mod: int, char_class: str = "",
            con_mod: int = 0, wis_mod: int = 0, has_shield: bool = False) -> int:
    """
    Calculate AC from equipped armor and class unarmored-defense features.
    Barbarian: 10 + DEX + CON when unarmored.
    Monk: 10 + DEX + WIS when unarmored.
    """
    cls = char_class.lower()
    a = ARMOR.get(armor_key, ARMOR["none"])

    if armor_key == "none":
        if cls == "barbarian":
            ac = 10 + dex_mod + con_mod
        elif cls == "monk":
            ac = 10 + dex_mod + wis_mod
        else:
            ac = 10 + dex_mod
    else:
        cap = a["dex_cap"]
        if cap is None:
            dex_contrib = dex_mod          # light armor: full DEX (positive or negative)
        elif cap == 0:
            dex_contrib = 0                # heavy armor: DEX never contributes
        else:
            dex_contrib = min(dex_mod, cap)  # medium armor: DEX up to cap
        ac = a["base_ac"] + dex_contrib

    return ac + (2 if has_shield else 0)


# ── Attack building ────────────────────────────────────────────────────────────

def _mod(score: int) -> int:
    return (score - 10) // 2


def build_attack(weapon_key: str, ability_scores: AbilityScores,
                 prof_bonus: int) -> Attack:
    """Build an Attack entry for a weapon given ability scores and proficiency."""
    w = WEAPONS.get(weapon_key)
    if not w:
        return Attack(name=weapon_key.replace("_", " ").title(),
                      hit_bonus=prof_bonus, damage_dice="1d4",
                      damage_type="bludgeoning")

    str_mod = _mod(ability_scores.strength)
    dex_mod = _mod(ability_scores.dexterity)

    if w["ranged"]:
        stat_mod = dex_mod
    elif w["finesse"]:
        stat_mod = max(str_mod, dex_mod)
    else:
        stat_mod = str_mod

    return Attack(
        name=weapon_key.replace("_", " ").title(),
        hit_bonus=prof_bonus + stat_mod,
        damage_dice=w["damage"],
        damage_type=w["type"],
        notes=w["notes"],
    )


# ── Internal best-armor helper ─────────────────────────────────────────────────

def _best_armor(armor_options: list[str], dex_mod: int, char_class: str,
                con_mod: int, wis_mod: int) -> str:
    return max(
        armor_options,
        key=lambda a: calc_ac(a, dex_mod, char_class, con_mod, wis_mod, False),
    )


# ── Public API ─────────────────────────────────────────────────────────────────

def get_standard_equipment(char_class: str, ability_scores: AbilityScores,
                            prof_bonus: int = 2) -> dict:
    """
    Return the best-fit starting equipment for the character.
    Picks the highest-AC armor and the first (strongest) weapon option.

    Returns:
        equipment:   list[EquipmentItem]
        attacks:     list[Attack]
        armor_key:   str
        armor_class: int
    """
    return _build_equipment(char_class, ability_scores, prof_bonus, mode="standard")


def get_random_equipment(char_class: str, ability_scores: AbilityScores,
                         prof_bonus: int = 2) -> dict:
    """
    Return a randomized but class-appropriate starting equipment package.
    Randomly selects from the valid options; never gives inappropriate gear.

    Returns same shape as get_standard_equipment.
    """
    return _build_equipment(char_class, ability_scores, prof_bonus, mode="random")


# ── Core builder ───────────────────────────────────────────────────────────────

def _build_equipment(char_class: str, ability_scores: AbilityScores,
                     prof_bonus: int, mode: str) -> dict:
    cls = char_class.lower()
    opts = CLASS_OPTIONS.get(cls)
    if opts is None:
        return {"equipment": [], "attacks": [], "armor_key": "none", "armor_class": 10}

    dex_mod = _mod(ability_scores.dexterity)
    con_mod = _mod(ability_scores.constitution)
    wis_mod = _mod(ability_scores.wisdom)

    # Armor
    if mode == "standard":
        armor_key = _best_armor(opts["armor_options"], dex_mod, cls, con_mod, wis_mod)
    else:
        armor_key = random.choice(opts["armor_options"])

    has_shield = opts["shield"]
    ac = calc_ac(armor_key, dex_mod, cls, con_mod, wis_mod, has_shield)

    # Weapon selection
    if mode == "standard":
        weapon_choice = opts["weapon_options"][0]
    else:
        weapon_choice = random.choice(opts["weapon_options"])

    # Gather all weapon keys (choice + armor-conditional extras + always-extras)
    armor_bonus_weapons = opts.get("armor_extras", {}).get(armor_key, [])
    all_weapon_keys = list(weapon_choice) + list(armor_bonus_weapons) + list(opts["extra_weapons"])

    # Pack
    if mode == "standard":
        pack_key = opts["pack_options"][0]
    else:
        pack_key = random.choice(opts["pack_options"])

    # Build EquipmentItem list
    items: list[EquipmentItem] = []

    if armor_key != "none":
        items.append(EquipmentItem(name=armor_key.replace("_", " ").title(), source="srd"))
    if has_shield:
        items.append(EquipmentItem(name="Shield", source="srd"))

    # Aggregate weapon quantities so e.g. 4 javelins → one item with qty=4
    weapon_counts: dict[str, int] = {}
    for wk in all_weapon_keys:
        weapon_counts[wk] = weapon_counts.get(wk, 0) + 1
    for wk, qty in weapon_counts.items():
        items.append(EquipmentItem(
            name=wk.replace("_", " ").title(),
            quantity=qty,
            source="srd",
        ))

    items.append(EquipmentItem(name=PACKS[pack_key], source="srd"))

    for extra in opts["extras"]:
        items.append(EquipmentItem(name=extra["name"], quantity=extra["quantity"], source="srd"))

    # Build Attack list: primary weapon choice + any ranged extras (deduped, ordered)
    attack_weapon_keys: list[str] = list(weapon_choice)
    for wk in armor_bonus_weapons + list(opts["extra_weapons"]):
        if wk in WEAPONS and (WEAPONS[wk]["ranged"] or wk == "javelin"):
            attack_weapon_keys.append(wk)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_attack_keys: list[str] = []
    for wk in attack_weapon_keys:
        if wk not in seen:
            seen.add(wk)
            unique_attack_keys.append(wk)

    attacks = [build_attack(wk, ability_scores, prof_bonus) for wk in unique_attack_keys]

    return {
        "equipment": items,
        "attacks": attacks,
        "armor_key": armor_key,
        "armor_class": ac,
    }
