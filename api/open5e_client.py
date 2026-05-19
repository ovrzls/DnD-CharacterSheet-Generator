"""
Open5e API client.
Base URL: https://api.open5e.com/v2/
Supports document__key filtering for third-party source control.
All requests are cached locally in data/cache/ to reduce API calls.
"""
import json
import time
from pathlib import Path

# TODO (PROTO-1): implement full client with caching and pagination
# TODO (PROTO-1): add retry logic and error handling

BASE_URL = "https://api.open5e.com/v2"
CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
CACHE_TTL_SECONDS = 86400  # 24 hours


class Open5eClient:
    """
    Thin wrapper around the Open5e REST API.
    Handles caching, pagination, and source filtering.
    """

    def __init__(self, sources: list = None, cache_dir: Path = None):
        """
        sources: list of document__key values to filter by (e.g. ["wotc-srd", "a5e"])
        cache_dir: override the default cache directory
        """
        self.sources = sources or ["wotc-srd"]
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, endpoint: str, params: dict) -> Path:
        """Generate a deterministic cache file path for a request."""
        key = endpoint.replace("/", "_") + "_" + "_".join(
            f"{k}={v}" for k, v in sorted(params.items())
        )
        return self.cache_dir / f"{key}.json"

    def _is_cache_fresh(self, path: Path) -> bool:
        """Return True if cache file exists and is within TTL."""
        if not path.exists():
            return False
        age = time.time() - path.stat().st_mtime
        return age < CACHE_TTL_SECONDS

    def get(self, endpoint: str, params: dict = None) -> dict:
        """
        GET /v2/{endpoint} with optional query params.
        Automatically adds document__key__in filter if sources are set.
        Returns the full JSON response dict.
        """
        raise NotImplementedError("Open5eClient.get() not yet implemented — PROTO-1 task")

    def get_races(self) -> list:
        """Return list of available races filtered by active sources."""
        raise NotImplementedError("get_races() not yet implemented — PROTO-1 task")

    def get_classes(self) -> list:
        """Return list of available classes filtered by active sources."""
        raise NotImplementedError("get_classes() not yet implemented — PROTO-1 task")

    def get_backgrounds(self) -> list:
        """Return list of available backgrounds filtered by active sources."""
        raise NotImplementedError("get_backgrounds() not yet implemented — PROTO-1 task")

    def get_spells(self, char_class: str = None, level_max: int = 5) -> list:
        """Return spells filtered by class and level cap."""
        raise NotImplementedError("get_spells() not yet implemented — PROTO-4 task")

    def get_equipment(self) -> list:
        """Return equipment list filtered by active sources."""
        raise NotImplementedError("get_equipment() not yet implemented — PROTO-3 task")
