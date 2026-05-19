"""
OtG PDF filler — wraps the existing fill_character_sheet.py logic.
Accepts a Character dataclass and outputs a filled OtG PDF.
Auto-selects the correct sheet variant (martial or caster) based on character.sheet_variant.

Sheet PDFs should be placed in:
  pdf/field_maps/otg_martial.pdf   -- OtG martial sheet (pages 1-2)
  pdf/field_maps/otg_caster.pdf    -- OtG caster sheet  (pages 1-4, with spellcasting)
"""
from pathlib import Path
from engine.character import Character

# TODO (Milestone 4): implement full OtG field mapping
# TODO: map Character fields to OtG PDF field names using field_maps/otg_field_map.json

FIELD_MAPS_DIR = Path(__file__).parent / "field_maps"


def character_to_field_values(character: Character) -> dict:
    """
    Convert a Character dataclass to a flat dict of {pdf_field_name: value}.
    This is the bridge between the rules engine and the existing PDF filler.
    """
    raise NotImplementedError(
        "character_to_field_values() not yet implemented — Milestone 4 task"
    )


def fill_otg_sheet(character: Character, output_path: Path) -> Path:
    """
    Fill the appropriate OtG sheet PDF for the given character.
    Auto-selects martial or caster variant based on character.sheet_variant.
    Returns the path to the filled PDF.
    """
    raise NotImplementedError(
        "fill_otg_sheet() not yet implemented — Milestone 4 task"
    )
