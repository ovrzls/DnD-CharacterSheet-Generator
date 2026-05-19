"""
Ability score generation and assignment.
PROTO scope: standard array, point buy base, 4d6 drop lowest, straight 3d6.
Also handles assigning a list of scores to the six abilities,
and applying racial ability score bonuses.
"""
from __future__ import annotations
import random
from engine.character import AbilityScores

STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]
ABILITIES = ["strength", "dexterity", "constitution",
             "intelligence", "wisdom", "charisma"]

POINT_BUY_COSTS = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
POINT_BUY_BUDGET = 27
POINT_BUY_MIN = 8
POINT_BUY_MAX = 15


def roll_4d6_drop_lowest() -> int:
    """Roll 4d6, drop the lowest, return sum."""
    rolls = sorted([random.randint(1, 6) for _ in range(4)])
    return sum(rolls[1:])


def generate_scores(method: str) -> list:
    """
    Generate 6 unassigned ability scores using the chosen method.
    Returns a list of 6 ints sorted highest-first.
    """
    if method == "standard_array":
        return list(STANDARD_ARRAY)
    elif method == "random_4d6_drop1":
        return sorted([roll_4d6_drop_lowest() for _ in range(6)], reverse=True)
    elif method == "random_3d6":
        return sorted(
            [sum(random.randint(1, 6) for _ in range(3)) for _ in range(6)],
            reverse=True
        )
    elif method == "point_buy":
        # Returns minimums; wizard step handles player assignment up to budget
        return [POINT_BUY_MIN] * 6
    else:
        raise ValueError(f"Unknown ability score method: '{method}'")


def assign_scores(scores: list, assignment: dict) -> AbilityScores:
    """
    Assign a list of 6 scores to abilities based on an assignment mapping.

    assignment: dict mapping ability name -> index into scores list
    e.g. {"strength": 0, "dexterity": 1, ...} assigns scores[0] to STR etc.

    Or pass a simple ordered dict where values are the actual scores:
    e.g. {"strength": 15, "dexterity": 14, ...}
    """
    def _val(v):
        # If value is an index into scores list
        if isinstance(v, int) and v < len(scores) and max(assignment.values()) < len(scores):
            return scores[v]
        return v  # treat as direct score value

    # Detect if assignment values are indices or direct scores
    vals = list(assignment.values())
    use_indices = all(isinstance(v, int) for v in vals) and max(vals) < len(scores)

    result = {}
    for ability in ABILITIES:
        raw = assignment.get(ability, POINT_BUY_MIN)
        result[ability] = scores[raw] if use_indices else raw

    return AbilityScores(**result)


def assign_scores_in_order(scores: list,
                           order: list = None) -> AbilityScores:
    """
    Assign scores to abilities in a given order (highest score to first ability).
    Default order: STR, DEX, CON, INT, WIS, CHA.
    Useful for quick/random character generation.
    """
    order = order or ABILITIES
    if len(scores) < 6:
        raise ValueError(f"Need 6 scores, got {len(scores)}")
    mapping = {ability: scores[i] for i, ability in enumerate(order[:6])}
    return AbilityScores(**mapping)


def apply_racial_bonuses(base: AbilityScores,
                         bonuses: dict) -> AbilityScores:
    """
    Apply racial ability score bonuses to a base AbilityScores.
    bonuses: dict of {ability_name: bonus_value}
    e.g. {"dexterity": 2, "intelligence": 1} for High Elf
    Returns a new AbilityScores with bonuses applied (cap at 20).
    """
    result = {}
    for ability in ABILITIES:
        base_val = getattr(base, ability, 10)
        bonus = bonuses.get(ability, 0)
        result[ability] = min(20, base_val + bonus)
    return AbilityScores(**result)


def validate_point_buy(scores: dict) -> tuple:
    """
    Validate a point-buy assignment.
    scores: dict {ability: score_value}
    Returns (is_valid: bool, cost: int, message: str)
    """
    total_cost = 0
    for ability, score in scores.items():
        if score < POINT_BUY_MIN or score > POINT_BUY_MAX:
            return False, 0, (f"{ability} score {score} out of range "
                              f"({POINT_BUY_MIN}-{POINT_BUY_MAX})")
        total_cost += POINT_BUY_COSTS.get(score, 999)

    if total_cost > POINT_BUY_BUDGET:
        return False, total_cost, (f"Over budget: {total_cost} points used, "
                                   f"{POINT_BUY_BUDGET} allowed")
    return True, total_cost, f"Valid — {total_cost}/{POINT_BUY_BUDGET} points used"
