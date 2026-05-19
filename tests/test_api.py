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
