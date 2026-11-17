#!/usr/bin/env python3
"""Generate OtG character sheet PDFs for all 12 premade Level-3 characters."""
from pathlib import Path

from data.premade_characters import get_premade_characters
from pdf.filler import fill_otg_sheet

OUTPUT_DIR = Path("pdf/samples/premade")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    characters = get_premade_characters()

    for char in characters:
        slug = char.char_class.lower().replace(" ", "_")
        out = OUTPUT_DIR / f"premade_{slug}_lv3.pdf"
        fill_otg_sheet(char, out, predefined=True)
        print(f"  ✓  {out.name}  (HP {char.max_hp}, AC {char.armor_class})")

    print(f"\nGenerated {len(characters)} sheets → {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
