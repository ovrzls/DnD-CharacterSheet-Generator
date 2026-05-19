"""
Source/document management for third-party content.
Maps Open5e document__key values to human-readable names.
Allows filtering API calls to specific sources (e.g. SRD only, or SRD + a5e).
"""
# Default: SRD only
DEFAULT_SOURCES = ["wotc-srd"]

# Known Open5e document keys (expand as needed)
KNOWN_SOURCES = {
    "wotc-srd": "D&D 5e SRD (Wizards of the Coast)",
    "a5e": "Level Up: Advanced 5th Edition (EN Publishing)",
    "menagerie": "Level Up Monstrous Menagerie",
    "taldorei": "Critical Role: Tal'Dorei Campaign Setting",
    "kp": "Kobold Press (various)",
    "cc": "Creature Codex",
    "tob": "Tome of Beasts",
    "tob2": "Tome of Beasts 2",
}


class SourceManager:
    """Manages which content sources are active for this character generation session."""

    def __init__(self, sources: list = None):
        self.active_sources = sources if sources is not None else list(DEFAULT_SOURCES)

    def add_source(self, key: str):
        if key not in self.active_sources:
            self.active_sources.append(key)

    def remove_source(self, key: str):
        self.active_sources = [s for s in self.active_sources if s != key]

    def get_filter_param(self) -> str:
        """Return Open5e API filter string for document__key__in."""
        return ",".join(self.active_sources)

    def list_known(self) -> dict:
        return dict(KNOWN_SOURCES)
