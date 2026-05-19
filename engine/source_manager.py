"""
Source/document management for third-party content.
Maps Open5e v2 document__key values to human-readable names.
Default source: srd-2014 (classic D&D 5e 2014 rules, CC-BY licensed).
"""

# Default: classic 2014 SRD only
DEFAULT_SOURCES = ["srd-2014"]

# All known Open5e v2 document keys (from /v2/documents/)
KNOWN_SOURCES = {
    # Official WotC SRDs
    "srd-2014": "D&D 5e 2014 SRD (Wizards of the Coast) — Classic rules",
    "srd-2024": "D&D 5e 2024 SRD (Wizards of the Coast) — 2024 revised rules",
    # Level Up: Advanced 5th Edition (EN Publishing)
    "a5e-ag":   "Level Up: Adventurer's Guide (EN Publishing)",
    "a5e-ddg":  "Level Up: Dungeon Delver's Guide (EN Publishing)",
    "a5e-gpg":  "Level Up: Gate Pass Gazette (EN Publishing)",
    "a5e-mm":   "Level Up: Monstrous Menagerie (EN Publishing)",
    # Kobold Press
    "bfrd":     "Black Flag SRD (Kobold Press)",
    "kp":       "Kobold Press Compilation",
    "ccdx":     "Creature Codex (Kobold Press)",
    "tob":      "Tome of Beasts (Kobold Press)",
    "tob-2023": "Tome of Beasts 1 — 2023 Edition (Kobold Press)",
    "tob2":     "Tome of Beasts 2 (Kobold Press)",
    "deepm":    "Deep Magic for 5th Edition (Kobold Press)",
    # Critical Role
    "tdcs":     "Tal'Dorei Campaign Setting (Green Ronin)",
    # Open5e Originals
    "open5e":   "Open5e Originals (2014 rules)",
    "open5e-2024": "Open5e Originals (2024 rules)",
}

# Curated preset bundles for common use cases
PRESETS = {
    "srd_only":     ["srd-2014"],
    "srd_2024":     ["srd-2024"],
    "a5e":          ["srd-2014", "a5e-ag"],
    "kobold":       ["srd-2014", "bfrd", "kp"],
    "all_2014":     [k for k, v in KNOWN_SOURCES.items() if "2014" in v or "Classic" in v],
}


class SourceManager:
    """Manages which content sources are active for this character generation session."""

    def __init__(self, sources: list = None):
        self.active_sources = list(sources) if sources else list(DEFAULT_SOURCES)

    def add_source(self, key: str):
        if key in KNOWN_SOURCES and key not in self.active_sources:
            self.active_sources.append(key)
        elif key not in KNOWN_SOURCES:
            raise ValueError(f"Unknown source key: '{key}'. "
                             f"Known keys: {list(KNOWN_SOURCES.keys())}")

    def remove_source(self, key: str):
        self.active_sources = [s for s in self.active_sources if s != key]

    def use_preset(self, preset_name: str):
        """Switch to a named preset bundle."""
        if preset_name not in PRESETS:
            raise ValueError(f"Unknown preset: '{preset_name}'. "
                             f"Known presets: {list(PRESETS.keys())}")
        self.active_sources = list(PRESETS[preset_name])

    def get_filter_list(self) -> list:
        """Return the active sources list for API filtering."""
        return list(self.active_sources)

    def describe(self) -> str:
        """Human-readable description of active sources."""
        names = [KNOWN_SOURCES.get(k, k) for k in self.active_sources]
        return ", ".join(names)

    def list_known(self) -> dict:
        return dict(KNOWN_SOURCES)

    def list_presets(self) -> dict:
        return dict(PRESETS)
