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
