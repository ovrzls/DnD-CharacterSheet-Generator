from __future__ import annotations
"""
Open5e API client — PROTO-1 implementation.
Base URL: https://api.open5e.com/v2/
- Handles pagination automatically (fetches all pages)
- Caches responses as JSON files in data/cache/ (24-hour TTL)
- Filters by document__key for source control
- Returns plain dicts; callers parse into dataclasses
"""
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

BASE_URL = "https://api.open5e.com/v2"
CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
CACHE_TTL_SECONDS = 86400  # 24 hours


class Open5eClient:
    """
    Thin wrapper around the Open5e v2 REST API.
    Uses only stdlib (urllib) — no requests dependency needed at this stage.
    """

    def __init__(self, sources: list = None, cache_dir: Path = None):
        """
        sources: list of document__key values e.g. ["srd-2014", "a5e-ag"]
                 None or empty = all sources
        """
        self.sources = sources if sources else []
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ── Cache helpers ────────────────────────────────────────────────────────

    def _cache_key(self, endpoint: str, params: dict) -> str:
        """Generate a safe filename from endpoint + params."""
        param_str = "_".join(f"{k}-{v}" for k, v in sorted(params.items()))
        safe = (endpoint + "_" + param_str).replace("/", "_").replace("?", "_")
        return safe[:180]  # keep filenames short

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def _is_fresh(self, path: Path) -> bool:
        if not path.exists():
            return False
        return (time.time() - path.stat().st_mtime) < CACHE_TTL_SECONDS

    def _read_cache(self, path: Path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_cache(self, path: Path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    # ── HTTP ─────────────────────────────────────────────────────────────────

    def _http_get(self, url: str) -> dict:
        """Perform a single GET request, return parsed JSON."""
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "OtG-CharGen/0.1"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # ── Core fetch (single page) ─────────────────────────────────────────────

    def get(self, endpoint: str, params: dict = None) -> dict:
        """
        GET /v2/{endpoint} with optional params.
        Adds document__key filter automatically if sources are set.
        Returns the raw API response dict (single page).
        Uses cache when fresh.
        """
        params = dict(params or {})
        if self.sources:
            params["document__key__in"] = ",".join(self.sources)

        cache_key = self._cache_key(endpoint, params)
        cache_path = self._cache_path(cache_key)

        if self._is_fresh(cache_path):
            return self._read_cache(cache_path)

        query = urllib.parse.urlencode(params)
        url = f"{BASE_URL}/{endpoint.strip('/')}/?{query}" if query else \
              f"{BASE_URL}/{endpoint.strip('/')}/"

        data = self._http_get(url)
        self._write_cache(cache_path, data)
        return data

    # ── Paginated fetch (all results) ────────────────────────────────────────

    def get_all(self, endpoint: str, params: dict = None) -> list:
        """
        Fetch ALL results for an endpoint, handling pagination automatically.
        Returns a flat list of result dicts.
        Uses a combined cache for the full result set.
        """
        params = dict(params or {})
        if self.sources:
            params["document__key__in"] = ",".join(self.sources)
        params["limit"] = 100  # max per page

        cache_key = self._cache_key(endpoint + "_ALL", params)
        cache_path = self._cache_path(cache_key)

        if self._is_fresh(cache_path):
            return self._read_cache(cache_path)

        results = []
        page = 1
        while True:
            paged_params = dict(params)
            paged_params["page"] = page
            query = urllib.parse.urlencode(paged_params)
            url = f"{BASE_URL}/{endpoint.strip('/')}/?{query}"

            data = self._http_get(url)
            results.extend(data.get("results", []))

            if not data.get("next"):
                break
            page += 1

        self._write_cache(cache_path, results)
        return results

    # ── Domain methods ───────────────────────────────────────────────────────

    def get_species(self) -> list:
        """
        Return all species (races) filtered by active sources.
        Excludes subspecies by default for the top-level selection list.
        """
        all_species = self.get_all("species")
        # Filter out subspecies for the main selection list
        return [s for s in all_species if not s.get("is_subspecies", False)]

    def get_species_names(self) -> list:
        """Return sorted list of species names for UI display."""
        return sorted(s["name"] for s in self.get_species())

    def get_classes(self) -> list:
        """
        Return all base classes (not subclasses) filtered by active sources.
        """
        all_classes = self.get_all("classes")
        # Exclude subclasses — they have a non-null subclass_of field
        return [c for c in all_classes if c.get("subclass_of") is None]

    def get_class_names(self) -> list:
        """Return sorted list of class names for UI display."""
        return sorted(c["name"] for c in self.get_classes())

    def get_class_by_name(self, name: str) -> dict:
        """Return the full class dict for a given class name (case-insensitive)."""
        for c in self.get_classes():
            if c["name"].lower() == name.lower():
                return c
        return None

    def get_backgrounds(self) -> list:
        """Return all backgrounds filtered by active sources."""
        return self.get_all("backgrounds")

    def get_background_names(self) -> list:
        """Return sorted list of background names for UI display."""
        return sorted(b["name"] for b in self.get_backgrounds())

    def get_spells(self, char_class: str = None, level_max: int = 5,
                   level_min: int = 0) -> list:
        """
        Return spells filtered by active sources.
        Optionally filter by class name and level range.
        level 0 = cantrips.
        """
        params = {}
        if level_max is not None:
            params["level__lte"] = level_max
        if level_min is not None:
            params["level__gte"] = level_min

        spells = self.get_all("spells", params)

        if char_class:
            # Filter by class name in the classes list
            char_class_lower = char_class.lower()
            spells = [
                s for s in spells
                if any(char_class_lower in cls.get("name", "").lower()
                       for cls in s.get("classes", []))
            ]
        return spells

    def get_cantrips(self, char_class: str = None) -> list:
        """Return cantrips (level 0) optionally filtered by class."""
        return self.get_spells(char_class=char_class, level_min=0, level_max=0)

    def list_documents(self) -> list:
        """Return all available source documents with their keys and names."""
        return self.get_all("documents")
