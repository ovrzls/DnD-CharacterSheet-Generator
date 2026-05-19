"""
Ability score generation methods.
PROTO scope: standard array, point buy, 4d6 drop lowest, straight 3d6.
"""
import random
from typing import List

STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]

POINT_BUY_COSTS = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
POINT_BUY_BUDGET = 27
POINT_BUY_MIN = 8
POINT_BUY_MAX = 15


def roll_4d6_drop_lowest() -> int:
    """Roll 4d6, drop the lowest die, return the sum."""
    rolls = sorted([random.randint(1, 6) for _ in range(4)])
    return sum(rolls[1:])


def generate_scores(method: str) -> List[int]:
    """
    Generate 6 ability scores using the specified method.
    Returns a list of 6 integers (unassigned to abilities yet).
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
        # Returns base values; UI wizard handles player assignment
        return [POINT_BUY_MIN] * 6
    else:
        raise ValueError(f"Unknown ability score method: {method}")
