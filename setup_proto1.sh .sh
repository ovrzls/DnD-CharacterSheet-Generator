#!/usr/bin/env bash
# setup_proto1.sh — PROTO-1: Live Open5e API client + updated source manager
set -e

echo "=== PROTO-1: Writing api/open5e_client.py ==="

cat > api/open5e_client.py << 'EOF'
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

    def get_species_names(self) -> list[str]:
        """Return sorted list of species names for UI display."""
        return sorted(s["name"] for s in self.get_species())

    def get_classes(self) -> list:
        """
        Return all base classes (not subclasses) filtered by active sources.
        """
        all_classes = self.get_all("classes")
        # Exclude subclasses — they have a non-null subclass_of field
        return [c for c in all_classes if c.get("subclass_of") is None]

    def get_class_names(self) -> list[str]:
        """Return sorted list of class names for UI display."""
        return sorted(c["name"] for c in self.get_classes())

    def get_class_by_name(self, name: str) -> dict | None:
        """Return the full class dict for a given class name (case-insensitive)."""
        for c in self.get_classes():
            if c["name"].lower() == name.lower():
                return c
        return None

    def get_backgrounds(self) -> list:
        """Return all backgrounds filtered by active sources."""
        return self.get_all("backgrounds")

    def get_background_names(self) -> list[str]:
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
EOF

echo "✓ api/open5e_client.py written"

# ── Update engine/source_manager.py with correct document keys ────────────────
echo "=== PROTO-1: Updating engine/source_manager.py with correct document keys ==="

cat > engine/source_manager.py << 'EOF'
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
EOF

echo "✓ engine/source_manager.py updated"

# ── Add PROTO-1 tests ─────────────────────────────────────────────────────────
echo "=== PROTO-1: Writing tests/test_api.py ==="

cat > tests/test_api.py << 'EOF'
"""
PROTO-1 tests for Open5eClient and SourceManager.
Live API tests are marked with @pytest.mark.live and skipped by default.
Run live tests with: pytest tests/test_api.py -m live -v
"""
import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from engine.source_manager import SourceManager, KNOWN_SOURCES, PRESETS
from api.open5e_client import Open5eClient


# ── SourceManager tests ───────────────────────────────────────────────────────

class TestSourceManager:

    def test_default_source(self):
        sm = SourceManager()
        assert sm.active_sources == ["srd-2014"]

    def test_add_known_source(self):
        sm = SourceManager()
        sm.add_source("a5e-ag")
        assert "a5e-ag" in sm.active_sources

    def test_add_unknown_source_raises(self):
        sm = SourceManager()
        with pytest.raises(ValueError, match="Unknown source key"):
            sm.add_source("totally-fake-source")

    def test_remove_source(self):
        sm = SourceManager(["srd-2014", "a5e-ag"])
        sm.remove_source("a5e-ag")
        assert sm.active_sources == ["srd-2014"]

    def test_use_preset_srd_only(self):
        sm = SourceManager(["a5e-ag"])
        sm.use_preset("srd_only")
        assert sm.active_sources == ["srd-2014"]

    def test_use_unknown_preset_raises(self):
        sm = SourceManager()
        with pytest.raises(ValueError, match="Unknown preset"):
            sm.use_preset("made_up_preset")

    def test_describe(self):
        sm = SourceManager(["srd-2014"])
        desc = sm.describe()
        assert "2014" in desc or "SRD" in desc

    def test_filter_list(self):
        sm = SourceManager(["srd-2014", "a5e-ag"])
        assert sm.get_filter_list() == ["srd-2014", "a5e-ag"]


# ── Open5eClient unit tests (mocked) ─────────────────────────────────────────

class TestOpen5eClientMocked:

    def _make_client(self, tmp_path):
        return Open5eClient(sources=["srd-2014"], cache_dir=tmp_path)

    def test_cache_miss_then_hit(self, tmp_path):
        client = self._make_client(tmp_path)
        fake_response = {"count": 1, "next": None, "previous": None,
                         "results": [{"name": "Human", "is_subspecies": False}]}

        with patch.object(client, "_http_get", return_value=fake_response) as mock_get:
            # First call — cache miss, hits HTTP
            result1 = client.get("species")
            assert mock_get.call_count == 1

            # Second call — cache hit, no HTTP
            result2 = client.get("species")
            assert mock_get.call_count == 1  # still 1, used cache

        assert result1 == result2

    def test_get_all_single_page(self, tmp_path):
        client = self._make_client(tmp_path)
        fake_response = {"count": 2, "next": None, "previous": None,
                         "results": [{"name": "Human"}, {"name": "Elf"}]}

        with patch.object(client, "_http_get", return_value=fake_response):
            results = client.get_all("species")

        assert len(results) == 2
        assert results[0]["name"] == "Human"

    def test_get_all_multiple_pages(self, tmp_path):
        client = self._make_client(tmp_path)
        page1 = {"count": 4, "next": "http://next", "previous": None,
                 "results": [{"name": "Human"}, {"name": "Elf"}]}
        page2 = {"count": 4, "next": None, "previous": "http://prev",
                 "results": [{"name": "Dwarf"}, {"name": "Halfling"}]}

        with patch.object(client, "_http_get", side_effect=[page1, page2]):
            results = client.get_all("species")

        assert len(results) == 4
        assert {r["name"] for r in results} == {"Human", "Elf", "Dwarf", "Halfling"}

    def test_get_species_excludes_subspecies(self, tmp_path):
        client = self._make_client(tmp_path)
        fake_all = [
            {"name": "Halfling", "is_subspecies": False},
            {"name": "Lightfoot Halfling", "is_subspecies": True},
            {"name": "Stoor Halfling", "is_subspecies": True},
        ]
        with patch.object(client, "get_all", return_value=fake_all):
            species = client.get_species()
        assert len(species) == 1
        assert species[0]["name"] == "Halfling"

    def test_get_classes_excludes_subclasses(self, tmp_path):
        client = self._make_client(tmp_path)
        fake_all = [
            {"name": "Fighter", "subclass_of": None},
            {"name": "Champion", "subclass_of": {"name": "Fighter"}},
            {"name": "Wizard", "subclass_of": None},
        ]
        with patch.object(client, "get_all", return_value=fake_all):
            classes = client.get_classes()
        assert len(classes) == 2
        assert {c["name"] for c in classes} == {"Fighter", "Wizard"}

    def test_source_filter_applied(self, tmp_path):
        client = Open5eClient(sources=["srd-2014", "a5e-ag"], cache_dir=tmp_path)
        fake_response = {"count": 0, "next": None, "previous": None, "results": []}

        captured_urls = []
        def fake_http_get(url):
            captured_urls.append(url)
            return fake_response

        with patch.object(client, "_http_get", side_effect=fake_http_get):
            client.get("species")

        assert len(captured_urls) == 1
        assert "document__key__in" in captured_urls[0]


# ── Live API tests (require internet, skipped by default) ────────────────────

@pytest.mark.live
class TestOpen5eClientLive:
    """Live integration tests — run with: pytest -m live"""

    def test_live_species_returns_results(self, tmp_path):
        client = Open5eClient(sources=["srd-2014"], cache_dir=tmp_path)
        species = client.get_species()
        assert len(species) > 0
        assert all("name" in s for s in species)

    def test_live_class_names_includes_fighter(self, tmp_path):
        client = Open5eClient(sources=["srd-2014"], cache_dir=tmp_path)
        names = client.get_class_names()
        assert len(names) > 0
        # srd-2014 should have standard classes
        print(f"\nFound {len(names)} classes: {names[:10]}")

    def test_live_backgrounds_returns_results(self, tmp_path):
        client = Open5eClient(sources=["srd-2014"], cache_dir=tmp_path)
        backgrounds = client.get_backgrounds()
        assert len(backgrounds) > 0
        print(f"\nFound {len(backgrounds)} backgrounds")

    def test_live_all_documents(self, tmp_path):
        client = Open5eClient(cache_dir=tmp_path)
        docs = client.list_documents()
        keys = [d["key"] for d in docs]
        assert "srd-2014" in keys
        assert "srd-2024" in keys
        print(f"\nAvailable document keys: {keys}")
EOF

echo "✓ tests/test_api.py written"

echo ""
echo "=== PROTO-1 complete! ==="
echo ""
echo "Next steps:"
echo "  1. source .venv/bin/activate   (if not already active)"
echo "  2. pytest tests/ -v            (run all tests including new ones)"
echo "  3. pytest tests/test_api.py -m live -v   (run live API tests — needs internet)"
echo "  4. git add . && git commit -m 'PROTO-1: Live Open5e API client with caching and source filtering' && git push origin master"