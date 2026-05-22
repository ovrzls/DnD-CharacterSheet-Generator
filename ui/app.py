"""
ui/app.py — Flask wizard for the OtG D&D character generator.
Run from project root:  flask --app ui/app run --debug

Routes:
  GET/POST /            → step 1 (character basics)
  GET/POST /step/<n>    → steps 2-7
  POST     /generate/pdf  → graphic PDF download
  POST     /generate/html → accessible HTML download
  POST     /generate/txt  → plain text download
  GET      /restart       → clear session and restart
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

# Ensure project root is importable regardless of working directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import (Flask, redirect, render_template, request,
                   send_file, session, url_for)

from api.open5e_client import Open5eClient
from engine.ability_scores import (POINT_BUY_BUDGET, POINT_BUY_COSTS,
                                   POINT_BUY_MAX, POINT_BUY_MIN,
                                   STANDARD_ARRAY, generate_scores,
                                   validate_point_buy)
from engine.character import AbilityScores, Character
from engine.equipment import get_standard_equipment
from engine.rules import (CASTER_CLASSES, SPELLCASTING_ABILITY, derive_stats)
from engine.spells import build_spells_for_character
from pdf.filler import fill_otg_sheet
from pdf.html_sheet import generate_html_sheet
from pdf.text_sheet import generate_text_sheet

_HERE = Path(__file__).parent

app = Flask(
    __name__,
    template_folder=str(_HERE / "templates"),
    static_folder=str(_HERE / "static"),
)
app.secret_key = "otg-dev-change-in-production"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

_client = Open5eClient(sources=["srd-2014"])

TOTAL_STEPS = 7

STEP_NAMES = {
    1: "Character Basics",
    2: "Species",
    3: "Class and Level",
    4: "Background",
    5: "Ability Scores",
    6: "Equipment and Spells",
    7: "Review and Download",
}

ABILITIES = ["str", "dex", "con", "int", "wis", "cha"]
ABILITY_LABELS = {
    "str": "Strength",
    "dex": "Dexterity",
    "con": "Constitution",
    "int": "Intelligence",
    "wis": "Wisdom",
    "cha": "Charisma",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _sign(n: int) -> str:
    return f"+{n}" if n >= 0 else str(n)


def _mod(score: int) -> int:
    return (score - 10) // 2


def _strip_md(text: str) -> str:
    """Remove basic markdown for plain-language display."""
    if not text:
        return ""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*",     r"\1", text)
    text = re.sub(r"#+\s*",          "",    text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    return text.strip()


def _first_para(text: str, max_chars: int = 260) -> str:
    text = _strip_md(text or "")
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    para  = paras[0] if paras else text
    if len(para) > max_chars:
        para = para[:max_chars].rsplit(" ", 1)[0] + "…"
    return para


def _char_data() -> dict:
    return dict(session.get("character", {}))


def _save(updates: dict) -> None:
    data = dict(session.get("character", {}))
    data.update(updates)
    session["character"] = data
    session.modified = True


def _build_char(*, equipment: bool = True, spells: bool = True) -> Character:
    """Reconstruct a Character from session data."""
    data  = _char_data()
    sc    = data.get("ability_scores", {})
    ab = AbilityScores(
        strength=int(sc.get("str", 10)),
        dexterity=int(sc.get("dex", 10)),
        constitution=int(sc.get("con", 10)),
        intelligence=int(sc.get("int", 10)),
        wisdom=int(sc.get("wis", 10)),
        charisma=int(sc.get("cha", 10)),
    )
    char = Character(
        name=data.get("name", "Unnamed Hero"),
        player_name=data.get("player_name", ""),
        char_class=data.get("char_class", "fighter").lower(),
        race=data.get("species", ""),
        background=data.get("background", ""),
        level=int(data.get("level", 1)),
        ability_scores=ab,
    )
    derive_stats(char)
    if equipment:
        try:
            eq = get_standard_equipment(
                char.char_class, char.ability_scores, char.proficiency_bonus
            )
            char.equipment   = eq.get("equipment", [])
            char.attacks     = eq.get("attacks", [])
            char.armor_class = eq.get("armor_class", char.armor_class)
        except Exception:
            pass
    if spells:
        try:
            build_spells_for_character(char, _client)
        except Exception:
            pass
    return char


def _step_ctx(n: int) -> dict:
    return {
        "current_step": n,
        "total_steps":  TOTAL_STEPS,
        "step_name":    STEP_NAMES[n],
        "char":         _char_data(),
        "prev_url": (
            url_for("index")         if n == 2 else
            url_for("step", n=n - 1) if n > 2  else None
        ),
    }


# ── API data (cached at module level after first call) ────────────────────────

_species_cache:     list | None = None
_classes_cache:     list | None = None
_backgrounds_cache: list | None = None


def _get_species() -> list[dict]:
    global _species_cache
    if _species_cache is not None:
        return _species_cache
    try:
        raw = _client.get_species()
        _species_cache = sorted([
            {
                "name":  s.get("name", ""),
                "desc":  _first_para(s.get("desc", "")),
                "size":  s.get("size", ""),
                "speed": s.get("speed", 30),
            }
            for s in raw if s.get("name")
        ], key=lambda x: x["name"])
    except Exception:
        _species_cache = [
            {"name": "Human",    "desc": "A versatile and adaptable people.",  "size": "Medium", "speed": 30},
            {"name": "Elf",      "desc": "A graceful and long-lived people.",   "size": "Medium", "speed": 30},
            {"name": "Dwarf",    "desc": "A sturdy and resilient mountain folk.", "size": "Medium", "speed": 25},
            {"name": "Halfling", "desc": "A small but courageous people.",      "size": "Small",  "speed": 25},
        ]
    return _species_cache


def _get_classes() -> list[dict]:
    global _classes_cache
    if _classes_cache is not None:
        return _classes_cache
    try:
        raw = _client.get_classes()
        _classes_cache = sorted([
            {
                "name":         c.get("name", ""),
                "key":          c.get("name", "").lower(),
                "desc":         _first_para(c.get("desc", "")),
                "hit_die":      c.get("hit_die", 8),
                "is_caster":    c.get("name", "").lower() in CASTER_CLASSES,
                "spell_ability": SPELLCASTING_ABILITY.get(
                    c.get("name", "").lower(), ""
                ).title(),
            }
            for c in raw if c.get("name")
        ], key=lambda x: x["name"])
    except Exception:
        _classes_cache = [
            {
                "name": cls.title(), "key": cls,
                "desc": "", "hit_die": 8,
                "is_caster": cls in CASTER_CLASSES,
                "spell_ability": SPELLCASTING_ABILITY.get(cls, "").title(),
            }
            for cls in sorted([
                "barbarian","bard","cleric","druid","fighter","monk",
                "paladin","ranger","rogue","sorcerer","warlock","wizard",
            ])
        ]
    return _classes_cache


def _get_backgrounds() -> list[dict]:
    global _backgrounds_cache
    if _backgrounds_cache is not None:
        return _backgrounds_cache
    try:
        raw = _client.get_backgrounds()
        _backgrounds_cache = sorted([
            {
                "name":         b.get("name", ""),
                "desc":         _first_para(b.get("desc", "")),
                "feature":      b.get("feature_name", ""),
                "feature_desc": _first_para(b.get("feature_desc", "")),
            }
            for b in raw if b.get("name")
        ], key=lambda x: x["name"])
    except Exception:
        _backgrounds_cache = [
            {"name": "Acolyte",  "desc": "You grew up in a religious community.", "feature": "Shelter of the Faithful", "feature_desc": ""},
            {"name": "Criminal", "desc": "You have a history outside the law.",   "feature": "Criminal Contact",        "feature_desc": ""},
            {"name": "Folk Hero","desc": "You rose from humble origins.",         "feature": "Rustic Hospitality",      "feature_desc": ""},
            {"name": "Soldier",  "desc": "You trained as a professional warrior.", "feature": "Military Rank",          "feature_desc": ""},
        ]
    return _backgrounds_cache


# ── Step 1: Character Basics ──────────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
def index():
    errors = {}
    if request.method == "POST":
        name      = request.form.get("name", "").strip()
        player    = request.form.get("player_name", "").strip()
        facilitator = request.form.get("facilitator_name", "").strip()
        pronouns  = request.form.get("pronouns", "").strip()

        if not name:
            errors["name"] = "Please enter a character name."
        if not player:
            errors["player_name"] = "Please enter the player's name."

        if not errors:
            _save({"name": name, "player_name": player,
                   "facilitator_name": facilitator, "pronouns": pronouns})
            return redirect(url_for("step", n=2))

    ctx = _step_ctx(1)
    ctx["errors"] = errors
    return render_template("step1_basics.html", **ctx)


# ── Steps 2-7 dispatcher ─────────────────────────────────────────────────────

@app.route("/step/<int:n>", methods=["GET", "POST"])
def step(n: int):
    if not 2 <= n <= TOTAL_STEPS:
        return redirect(url_for("index"))

    data = _char_data()
    # Guard: must have completed each prior step
    guards = [
        (2, "name"),
        (3, "species"),
        (4, "char_class"),
        (5, "background"),
        (6, "ability_scores"),
        (7, "ability_scores"),   # step 6 sets nothing new in session
    ]
    for req_step, req_key in guards:
        if n >= req_step and not data.get(req_key):
            return redirect(url_for("index" if req_step == 2 else "step",
                                    **({} if req_step == 2 else {"n": req_step - 1})))

    handlers = {2: _step2, 3: _step3, 4: _step4,
                5: _step5, 6: _step6, 7: _step7}
    return handlers[n](data)


# ── Step 2: Species ───────────────────────────────────────────────────────────

def _step2(data: dict):
    errors = {}
    species_list = _get_species()

    if request.method == "POST":
        chosen = request.form.get("species", "").strip()
        if not chosen:
            errors["species"] = "Please select a species."
        if not errors:
            _save({"species": chosen})
            return redirect(url_for("step", n=3))

    ctx = _step_ctx(2)
    ctx.update({
        "errors":       errors,
        "species_list": species_list,
        "species_json": json.dumps({s["name"]: s for s in species_list}),
        "selected":     data.get("species", ""),
    })
    return render_template("step2_species.html", **ctx)


# ── Step 3: Class and Level ───────────────────────────────────────────────────

def _step3(data: dict):
    errors = {}
    classes_list = _get_classes()

    if request.method == "POST":
        cls   = request.form.get("char_class", "").strip()
        level = request.form.get("level", "1").strip()

        if not cls:
            errors["char_class"] = "Please select a class."
        try:
            level_int = int(level)
            if not 1 <= level_int <= 5:
                errors["level"] = "Level must be 1–5 for this prototype."
        except (ValueError, TypeError):
            errors["level"] = "Please enter a valid level (1–5)."
            level_int = 1

        if not errors:
            _save({"char_class": cls.lower(), "level": level_int})
            return redirect(url_for("step", n=4))

    ctx = _step_ctx(3)
    ctx.update({
        "errors":       errors,
        "classes_list": classes_list,
        "classes_json": json.dumps({c["key"]: c for c in classes_list}),
        "selected":     data.get("char_class", ""),
        "sel_level":    data.get("level", 1),
        "level_range":  range(1, 6),
    })
    return render_template("step3_class.html", **ctx)


# ── Step 4: Background ────────────────────────────────────────────────────────

def _step4(data: dict):
    errors = {}
    bg_list = _get_backgrounds()

    if request.method == "POST":
        chosen = request.form.get("background", "").strip()
        if not chosen:
            errors["background"] = "Please select a background."
        if not errors:
            _save({"background": chosen})
            return redirect(url_for("step", n=5))

    ctx = _step_ctx(4)
    ctx.update({
        "errors":    errors,
        "bg_list":   bg_list,
        "bg_json":   json.dumps({b["name"]: b for b in bg_list}),
        "selected":  data.get("background", ""),
    })
    return render_template("step4_background.html", **ctx)


# ── Step 5: Ability Scores ────────────────────────────────────────────────────

def _step5(data: dict):
    errors: dict = {}
    method = data.get("ability_method", "standard_array")

    if request.method == "POST":
        action = request.form.get("action", "save")
        method = request.form.get("ability_method", "standard_array")

        if action == "roll":
            rolled = sorted(generate_scores("random_4d6_drop1"), reverse=True)
            session["rolled_scores"] = rolled
            session["pending_method"] = method
            session.modified = True
            return redirect(url_for("step", n=5))

        # Parse submitted scores
        raw: dict[str, int] = {}
        for ab in ABILITIES:
            try:
                raw[ab] = int(request.form.get(f"score_{ab}", 0))
            except (ValueError, TypeError):
                errors[f"score_{ab}"] = "Please enter a number."
                raw[ab] = 10

        if not errors:
            if method == "standard_array":
                if sorted(raw.values()) != sorted(STANDARD_ARRAY):
                    errors["scores"] = (
                        "Please assign each Standard Array value exactly once: "
                        + ", ".join(str(s) for s in sorted(STANDARD_ARRAY, reverse=True))
                    )
            elif method == "random_roll":
                rolled = session.get("rolled_scores", list(STANDARD_ARRAY))
                if sorted(raw.values()) != sorted(rolled):
                    errors["scores"] = "Please assign each rolled score exactly once."
            elif method == "point_buy":
                valid, _, msg = validate_point_buy({
                    "strength":     raw["str"],
                    "dexterity":    raw["dex"],
                    "constitution": raw["con"],
                    "intelligence": raw["int"],
                    "wisdom":       raw["wis"],
                    "charisma":     raw["cha"],
                })
                if not valid:
                    errors["scores"] = msg

        if not errors:
            _save({"ability_scores": raw, "ability_method": method})
            session.pop("rolled_scores", None)
            session.pop("pending_method", None)
            return redirect(url_for("step", n=6))
    else:
        # GET: restore pending method if set
        method = session.get("pending_method", method)

    rolled = session.get("rolled_scores")
    if method == "random_roll" and rolled:
        pool = rolled
    elif method == "standard_array":
        pool = list(STANDARD_ARRAY)
    else:
        pool = None

    saved_scores = data.get("ability_scores", {})

    ctx = _step_ctx(5)
    ctx.update({
        "errors":         errors,
        "method":         method,
        "pool":           pool,
        "rolled_scores":  rolled,
        "standard_array": list(STANDARD_ARRAY),
        "pb_budget":      POINT_BUY_BUDGET,
        "pb_min":         POINT_BUY_MIN,
        "pb_max":         POINT_BUY_MAX,
        "pb_costs_json":  json.dumps(POINT_BUY_COSTS),
        "abilities":      ABILITIES,
        "ability_labels": ABILITY_LABELS,
        "saved_scores":   saved_scores,
        "sign":           _sign,
        "mod":            _mod,
    })
    return render_template("step5_abilities.html", **ctx)


# ── Step 6: Equipment and Spells ──────────────────────────────────────────────

def _step6(data: dict):
    if request.method == "POST":
        return redirect(url_for("step", n=7))

    char_obj  = None
    error_msg = None
    eq_items: list[str] = []
    attacks:  list      = []
    cantrips: list[str] = []
    spells:   list[str] = []
    spell_slots: dict   = {}

    try:
        char_obj = _build_char(equipment=True, spells=True)
        for item in char_obj.equipment:
            qty = f"{item.quantity}× " if item.quantity > 1 else ""
            eq_items.append(f"{qty}{item.name}")
        attacks = [
            (a.name, _sign(a.hit_bonus), a.damage_dice, a.damage_type)
            for a in char_obj.attacks
        ]
        cantrips    = [s.name for s in char_obj.always_available]
        spells      = [s.name for s in char_obj.spells]
        spell_slots = char_obj.spell_slots
    except Exception as exc:
        error_msg = str(exc)

    is_caster = data.get("char_class", "").lower() in CASTER_CLASSES

    ctx = _step_ctx(6)
    ctx.update({
        "error_msg":  error_msg,
        "eq_items":   eq_items,
        "attacks":    attacks,
        "cantrips":   cantrips,
        "spells":     spells,
        "spell_slots": spell_slots,
        "spell_ability": getattr(char_obj, "spellcasting_ability", ""),
        "spell_save_dc":  getattr(char_obj, "spell_save_dc",  0),
        "spell_attack":   getattr(char_obj, "spell_attack_bonus", 0),
        "is_caster":  is_caster,
    })
    return render_template("step6_equipment.html", **ctx)


# ── Step 7: Review and Download ───────────────────────────────────────────────

def _step7(data: dict):
    char_obj  = None
    stats     = {}
    error_msg = None

    try:
        char_obj = _build_char(equipment=True, spells=True)
        ab = char_obj.ability_scores
        stats = {
            "hp":           char_obj.max_hp,
            "ac":           char_obj.armor_class,
            "initiative":   char_obj.initiative,
            "speed":        char_obj.speed,
            "hit_dice":     char_obj.hit_dice,
            "prof_bonus":   char_obj.proficiency_bonus,
            "saves_prof":   char_obj.saving_throw_proficiencies,
            "spell_dc":     char_obj.spell_save_dc,
            "spell_atk":    char_obj.spell_attack_bonus,
            "spell_ability": char_obj.spellcasting_ability,
            "scores": {
                "str": (ab.strength,     _sign(_mod(ab.strength))),
                "dex": (ab.dexterity,    _sign(_mod(ab.dexterity))),
                "con": (ab.constitution, _sign(_mod(ab.constitution))),
                "int": (ab.intelligence, _sign(_mod(ab.intelligence))),
                "wis": (ab.wisdom,       _sign(_mod(ab.wisdom))),
                "cha": (ab.charisma,     _sign(_mod(ab.charisma))),
            },
        }
    except Exception as exc:
        error_msg = str(exc)

    is_caster = data.get("char_class", "").lower() in CASTER_CLASSES

    ctx = _step_ctx(7)
    ctx.update({
        "stats":     stats,
        "is_caster": is_caster,
        "error_msg": error_msg,
        "ability_labels": ABILITY_LABELS,
    })
    return render_template("step7_review.html", **ctx)


# ── Download routes ───────────────────────────────────────────────────────────

@app.route("/generate/pdf", methods=["POST"])
def generate_pdf():
    try:
        char = _build_char()
        tmp  = Path("/tmp") / f"{char.name.replace(' ', '_')}_otg.pdf"
        fill_otg_sheet(char, tmp)
        safe_name = re.sub(r"[^\w\-. ]", "_", char.name)
        return send_file(str(tmp), as_attachment=True,
                         download_name=f"{safe_name}_character_sheet.pdf",
                         mimetype="application/pdf")
    except Exception as exc:
        return f"Error generating PDF: {exc}", 500


@app.route("/generate/html", methods=["POST"])
def generate_html():
    try:
        char = _build_char()
        html = generate_html_sheet(char)
        buf  = io.BytesIO(html.encode("utf-8"))
        safe_name = re.sub(r"[^\w\-. ]", "_", char.name)
        return send_file(buf, as_attachment=True,
                         download_name=f"{safe_name}_character_sheet.html",
                         mimetype="text/html")
    except Exception as exc:
        return f"Error generating HTML sheet: {exc}", 500


@app.route("/generate/txt", methods=["POST"])
def generate_txt():
    try:
        char = _build_char()
        txt  = generate_text_sheet(char)
        buf  = io.BytesIO(txt.encode("utf-8"))
        safe_name = re.sub(r"[^\w\-. ]", "_", char.name)
        return send_file(buf, as_attachment=True,
                         download_name=f"{safe_name}_character_sheet.txt",
                         mimetype="text/plain; charset=utf-8")
    except Exception as exc:
        return f"Error generating text sheet: {exc}", 500


@app.route("/restart")
def restart():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
