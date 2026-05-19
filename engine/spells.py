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
